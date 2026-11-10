"""Regression checks for navigation and content in the offline manual."""

import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup, Tag

spec = importlib.util.spec_from_file_location(
    "manual_pdf", Path(__file__).parents[1] / "pdf.py"
)
assert spec is not None and spec.loader is not None
pdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf)


class PdfDocumentTest(unittest.TestCase):
    def element(self, root: Tag, selector: str) -> Tag:
        node = root.select_one(selector)
        if node is None:
            self.fail(f"Missing expected element: {selector}")
        return node

    def document(self, *sources) -> BeautifulSoup:
        articles = [
            {"url": url, "article": BeautifulSoup(source, "html.parser").article}
            for url, source in sources
        ]
        return BeautifulSoup(
            pdf._document(
                articles,
                "http://127.0.0.1:1234/",
                "https://example.org/manual/dev/",
                "Development edition",
            ),
            "html.parser",
        )

    def test_contents_distinguish_sections_from_chapters_using_site_navigation(self):
        section = SimpleNamespace(
            title="Extend", children=[], is_section=True, is_page=False
        )

        def page(url, title, is_index):
            return SimpleNamespace(
                url=url,
                title=title,
                ancestors=[section],
                file=SimpleNamespace(dest_uri=url + "index.html"),
                is_page=True,
                is_index=is_index,
            )

        overview = page("extend/", "Extend", True)
        chapter = page("extend/libraries/", "Creating test libraries", False)
        nested_index = page("extend/libdoc/", "Libdoc", True)
        section.children = [overview, chapter, nested_index]
        self.addCleanup(pdf._pages.clear)
        pdf.on_nav(
            SimpleNamespace(pages=section.children),
            SimpleNamespace(extra={"manual_pdf": {"enabled": True}}),
        )
        navigation = list(pdf._pages)
        self.assertTrue(navigation[0]["section_index"])
        self.assertFalse(navigation[2]["section_index"])

        articles = [
            {
                **entry,
                "article": BeautifulSoup(
                    f"<article><h1>{item.title}</h1><h2>Details</h2></article>",
                    "html.parser",
                ).article,
            }
            for item, entry in zip(section.children, navigation, strict=True)
        ]
        document = BeautifulSoup(
            pdf._document(articles, "http://localhost/", "https://example.org/", "dev"),
            "html.parser",
        )
        groups = document.select(".pdf-contents > ol > .pdf-toc-section")
        self.assertEqual(len(groups), 1)
        section_link = self.element(groups[0], ":scope > a")
        self.assertEqual(section_link.get_text(), "Extend")
        self.assertEqual(section_link["href"], "#chapter-0")
        self.assertEqual(
            [a.get_text() for a in groups[0].select(":scope > ol a")],
            ["Creating test libraries", "Libdoc"],
        )
        self.assertEqual(
            [a["href"] for a in groups[0].select(":scope > ol a")],
            ["#chapter-1", "#chapter-2"],
        )
        self.assertFalse(self.element(document, "#article-0 h1").has_attr("aria-level"))
        self.assertEqual(self.element(document, "#article-1 h1")["aria-level"], "2")
        self.assertEqual(self.element(document, "#article-1 h2")["aria-level"], "3")
        self.assertTrue(
            all(
                document.select_one(str(a["href"]))
                for a in document.select(".pdf-contents a")
            )
        )

    def test_merged_section_overview_is_not_duplicated_or_replaced_by_a_child_index(
        self,
    ):
        overview = SimpleNamespace(
            title="Extend",
            url="extend/",
            ancestors=[],
            file=SimpleNamespace(dest_uri="extend/index.html"),
            is_page=True,
            is_index=True,
            is_section=True,
            children=[],
        )
        child = SimpleNamespace(
            title="Libdoc",
            url="extend/libdoc/",
            ancestors=[overview],
            file=SimpleNamespace(dest_uri="extend/libdoc/index.html"),
            is_page=True,
            is_index=True,
            is_section=False,
        )
        overview.children = [child]
        self.addCleanup(pdf._pages.clear)
        pdf.on_nav(
            SimpleNamespace(pages=[overview, child]),
            SimpleNamespace(extra={"manual_pdf": {"enabled": True}}),
        )
        self.assertEqual([p["section"] for p in pdf._pages], ["Extend", "Extend"])
        self.assertEqual([p["section_index"] for p in pdf._pages], [True, False])
        articles = [
            {
                **entry,
                "article": BeautifulSoup(
                    f"<article><h1>{p.title}</h1></article>", "html.parser"
                ).article,
            }
            for p, entry in zip([overview, child], pdf._pages, strict=True)
        ]
        contents = BeautifulSoup(pdf._contents(articles), "html.parser")
        self.assertEqual(
            [a.get_text() for a in contents.select(".pdf-toc-section > a")], ["Extend"]
        )
        self.assertEqual(
            [a.get_text() for a in contents.select(".pdf-toc-chapter > a")], ["Libdoc"]
        )

    def test_cross_chapter_fragments_and_duplicate_ids(self):
        document = self.document(
            (
                "syntax/",
                """<article><h1 id="overview">Syntax</h1>
             <a href="../api/index.html#same">API heading</a>
             <a href="#overview">This chapter</a></article>""",
            ),
            (
                "api/",
                """<article><h1 id="same">API</h1><p id="same">Repeated ID</p>
             <a href="../syntax/">Syntax chapter</a></article>""",
            ),
        )
        ids = [node["id"] for node in document.select("[id]")]
        self.assertEqual(len(ids), len(set(ids)))
        links = {
            link.get_text(): str(link["href"]) for link in document.select("a[href]")
        }
        self.assertEqual(links["API heading"], "#chapter-1")
        self.assertEqual(links["This chapter"], "#chapter-0")
        self.assertEqual(links["Syntax chapter"], "#chapter-0")
        self.assertEqual(self.element(document, links["API heading"]).name, "h1")
        self.assertTrue(
            all(
                document.select_one(str(link["href"]))
                for link in document.select('a[href^="#"]')
            )
        )

    def test_collects_article_with_multiple_material_classes(self):
        with TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "index.html").write_text(
                "<nav>Website navigation</nav>"
                '<article class="md-content__inner md-typeset">'
                "<h1>Manual</h1><p>Article content</p></article>",
                encoding="utf-8",
            )
            pages = [
                {"url": "", "file": "index.html"},
                {"url": "api/", "file": "api/index.html"},
                {"url": "api/robot/api/", "file": "api/robot/api/index.html"},
            ]
            articles = pdf._articles(site, pages)
            self.assertEqual(len(articles), 1)
            self.assertIn("Article content", articles[0]["article"].get_text())
            self.assertNotIn("Website navigation", articles[0]["article"].get_text())

    def test_library_overview_is_included_without_keyword_reference_pages(self):
        with TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "libraries").mkdir()
            (site / "libraries/index.html").write_text(
                '<article class="md-content__inner"><h1>Libraries</h1>'
                '<a href="BuiltIn.html#Log">BuiltIn</a></article>',
                encoding="utf-8",
            )
            pages = [
                {"url": "libraries/", "file": "libraries/index.html"},
                {"url": "libraries/BuiltIn.html", "file": "libraries/BuiltIn.html"},
            ]
            articles = pdf._articles(site, pages)
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0]["url"], "libraries/")
            document = BeautifulSoup(
                pdf._document(
                    articles,
                    "http://localhost/",
                    "https://example.org/manual/dev/",
                    "dev",
                ),
                "html.parser",
            )
            link = next(
                a for a in document.select("a[href]") if a.get_text() == "BuiltIn"
            )
            self.assertEqual(
                link["href"],
                "https://example.org/manual/dev/libraries/BuiltIn.html#Log",
            )

    def test_hidden_content_images_and_external_resources(self):
        document = self.document(
            (
                "extend/libdoc/",
                """<article><h1>Libdoc</h1>
          <details><summary>Details</summary><p hidden>Essential content</p></details>
          <img src="example.png" loading="lazy">
          <img class="twemoji" src="https://cdn.example/flag.svg"
            title=":py:" alt="flag">
          <a href="ExampleLibrary.py#example">Source</a>
          <a href="https://python.org/">Python</a>
          <a class="headerlink" href="#missing">Permalink</a></article>""",
            )
        )
        self.assertTrue(self.element(document, "details").has_attr("open"))
        self.assertFalse(document.select("[hidden]"))
        image = self.element(document, "img")
        self.assertEqual(
            image["src"], "http://127.0.0.1:1234/extend/libdoc/example.png"
        )
        self.assertNotIn("loading", image.attrs)
        self.assertIn(":py:", document.get_text())
        self.assertEqual(len(document.select("img")), 1)
        links = {link.get_text(): link["href"] for link in document.select("a[href]")}
        self.assertEqual(
            links["Source"],
            "https://example.org/manual/dev/extend/libdoc/ExampleLibrary.py#example",
        )
        self.assertEqual(links["Python"], "https://python.org/")
        self.assertNotIn("Permalink", links)

    def test_all_tabs_and_accessibility_references_survive(self):
        document = self.document(
            (
                "",
                """<article><h1>Manual</h1>
          <table><tr><th id="argument">Argument</th>
            <td headers="argument">value</td></tr></table>
          <div class="tabbed-set"><input type="radio">
            <div class="tabbed-labels"><label>Python</label><label>Robot</label></div>
            <div class="tabbed-content">
              <div class="tabbed-block"><pre>    Python code</pre></div>
            <div class="tabbed-block"><pre>    Robot code</pre></div></div></div>
          </article>""",
            )
        )
        self.assertEqual(
            [p.get_text() for p in document.select(".pdf-tab-title")],
            ["Python", "Robot"],
        )
        self.assertEqual(
            self.element(document, "td")["headers"], ["chapter-0--argument"]
        )
        self.assertEqual(
            [p.get_text() for p in document.select("pre")],
            ["    Python code", "    Robot code"],
        )
        self.assertFalse(document.select("input, .tabbed-labels"))

    def test_normal_previews_do_not_generate_or_link_a_pdf(self):
        config = SimpleNamespace(extra={})
        with patch.dict("os.environ", {}, clear=True):
            pdf.on_config(config)
            pdf.on_nav(SimpleNamespace(pages=[object()]), config)
            pdf.on_post_build(config)
        self.assertFalse(config.extra["manual_pdf"]["enabled"])

    def test_pdf_can_be_generated_independently_of_website_api_pages(self):
        for environment in (
            {"GENERATE_PDF": "1"},
            {
                "GENERATE_API_DOCS": "1",
                "GENERATE_PDF": "1",
                "DO_NOT_GENERATE_API_DOCS": "1",
            },
        ):
            with (
                self.subTest(environment=environment),
                patch.dict("os.environ", environment, clear=True),
            ):
                config = SimpleNamespace(extra={})
                pdf.on_config(config)
                self.assertTrue(config.extra["manual_pdf"]["enabled"])

    def test_mismatched_tab_labels_and_content_fail_instead_of_losing_content(self):
        for label_count, block_count in ((1, 2), (2, 1)):
            with self.subTest(labels=label_count, blocks=block_count):
                labels = "<label>Example</label>" * label_count
                blocks = (
                    '<div class="tabbed-block">Essential content</div>' * block_count
                )
                source = (
                    '<article><h1>Manual</h1><div class="tabbed-set">'
                    f'<div class="tabbed-labels">{labels}</div>'
                    f'<div class="tabbed-content">{blocks}</div></div></article>'
                )
                with self.assertRaises(ValueError):
                    self.document(("", source))

    def test_omitted_api_links_point_to_online_reference(self):
        document = self.document(
            (
                "syntax/",
                """<article><h1>Syntax</h1>
          <a href="../api/robot/api/#robot.api">Python API</a></article>""",
            )
        )
        link = next(
            a for a in document.select("a[href]") if a.get_text() == "Python API"
        )
        self.assertEqual(
            link["href"], "https://example.org/manual/dev/api/robot/api/#robot.api"
        )
        self.assertEqual(
            self.element(document, ".pdf-online-reference a:last-child")["href"],
            "https://example.org/manual/dev/api/",
        )

    def test_version_and_reference_links_use_deployment_instead_of_bundled_source(self):
        with TemporaryDirectory() as directory:
            config = SimpleNamespace(
                site_dir=directory,
                site_url="https://example.org/manual/latest",
                extra={},
            )

            def write_pdf(site, pages, output, version, online_url):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"PDF fixture")

            pdf._pages.clear()
            for deployment, label in (
                (None, "Development edition"),
                ("dev", "Development edition"),
                ("7.5", "Version 7.5"),
            ):
                with self.subTest(deployment=deployment):
                    config.site_url = (
                        "https://example.org/manual/latest"
                        if deployment
                        else "https://example.org/manual/"
                    )
                    environment = {"GENERATE_PDF": "1"}
                    if deployment:
                        environment["MIKE_DOCS_VERSION"] = deployment
                    with patch.dict("os.environ", environment, clear=True):
                        pdf.on_config(config)
                        with patch.object(
                            pdf, "generate_pdf", side_effect=write_pdf
                        ) as generate:
                            pdf.on_post_build(config)
                    self.assertEqual(generate.call_args.args[-2], label)
                    filename = f"robot-framework-manual-{deployment or 'dev'}.pdf"
                    self.assertEqual(
                        config.extra["manual_pdf"]["url"], f"downloads/{filename}"
                    )
                    self.assertEqual(
                        generate.call_args.args[2],
                        Path(directory) / "downloads" / filename,
                    )
                    expected = (
                        f"https://example.org/manual/{deployment}/"
                        if deployment
                        else config.site_url
                    )
                    self.assertEqual(generate.call_args.args[-1], expected)


if __name__ == "__main__":
    unittest.main()
