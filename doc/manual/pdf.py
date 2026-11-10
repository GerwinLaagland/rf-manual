"""Export the manual articles as a single PDF with Chromium.

Print styles live in assets/pdf.css. Dependencies are loaded only for PDF builds.
"""

import html
import logging
import os
import posixpath
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.parse import quote, unquote, urljoin, urlsplit

log = logging.getLogger("properdocs.manual_pdf")
SIZE_TOKEN = "__MANUAL_PDF_SIZE__"
_pages = []


def on_config(config):
    enabled = os.environ.get("GENERATE_PDF") == "1"
    version = os.environ.get("MIKE_DOCS_VERSION") or "dev"
    config.extra["manual_pdf"] = {
        "enabled": enabled,
        "url": f"downloads/robot-framework-manual-{version}.pdf",
    }
    if enabled:
        log.info("Manual PDF generation: enabled")
    else:
        log.info("Manual PDF generation: disabled (set GENERATE_PDF=1 to enable)")


def on_nav(nav, config, **kwargs):
    _pages.clear()
    if not config.extra["manual_pdf"]["enabled"]:
        return
    for page in nav.pages:
        ancestors = list(page.ancestors)
        top = ancestors[-1] if ancestors else page
        section = top if top.is_section else None
        # section-index merges each overview page with its parent section.
        # The overview is then the section itself, not its first child bundle.
        overview = section
        if section and not section.is_page:
            overview = next(
                (
                    child
                    for child in section.children
                    if child.is_page and child.is_index
                ),
                None,
            )
        _pages.append(
            {
                "url": page.url,
                "file": page.file.dest_uri,
                "section": section.title if section else None,
                "section_index": page is overview,
                "label": page.title if section is None else None,
            }
        )


def on_post_build(config):
    if not config.extra["manual_pdf"]["enabled"]:
        return
    started = perf_counter()
    site = Path(config.site_dir)
    deployment = os.environ.get("MIKE_DOCS_VERSION")
    version = (
        f"Version {deployment}"
        if deployment and deployment != "dev"
        else "Development edition"
    )
    online_url = config.site_url.rstrip("/") + "/"
    if deployment:
        # mike's canonical_version may point at latest even in a dev build.
        online_url = urljoin(online_url, "../" + quote(deployment, safe="") + "/")
    output = site / config.extra["manual_pdf"]["url"]
    generate_pdf(site, list(_pages), output, version, online_url)
    size = f"{output.stat().st_size / (1024 * 1024):.1f} MB"
    for item in _pages:
        path = site / item["file"]
        rendered = path.read_text(encoding="utf-8")
        path.write_text(rendered.replace(SIZE_TOKEN, size), encoding="utf-8")
    log.info(
        "Manual PDF: %s, %s, generated in %.1f s",
        output,
        size,
        perf_counter() - started,
    )


def _path(url):
    """Normalize directory and index.html links to the same document."""
    path = posixpath.normpath(unquote(urlsplit(url).path)).lstrip("/")
    if path == ".":
        return ""
    if path == "index.html":
        return ""
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    return path.rstrip("/")


def _articles(site, pages):
    from bs4 import BeautifulSoup
    from bs4.filter import SoupStrainer

    articles = []
    # Reference documentation stays online. Include the Libraries overview,
    # whose links lead readers to each library's generated keyword reference.
    pages = [
        entry
        for entry in pages
        if _path(entry["url"]).split("/", 1)[0] != "api"
        and not _path(entry["url"]).startswith("libraries/")
    ]
    log.info("Collecting %s manual articles", len(pages))
    for entry in pages:
        soup = BeautifulSoup(
            (site / entry["file"]).read_text(encoding="utf-8"),
            "html.parser",
            parse_only=SoupStrainer("article"),
        )
        article = soup.select_one("article.md-content__inner")
        if article is None:
            raise ValueError(f"Missing manual article: {entry['file']}")
        articles.append({**entry, "article": article})
    return articles


def _contents(articles):
    """Follow the site's sections, with chapter links nested under each one."""
    groups = []
    for index, entry in enumerate(articles):
        title = entry["article"].find("h1").get_text(" ", strip=True)
        section = entry.get("section")
        key = ("section", section) if section else ("page", index)
        if not groups or groups[-1]["key"] != key:
            groups.append(
                {
                    "key": key,
                    "title": section or entry.get("label") or title,
                    "target": index,
                    "chapters": [],
                }
            )
        if section and not entry.get("section_index"):
            groups[-1]["chapters"].append((index, title))

    rendered = []
    for group in groups:
        children = "".join(
            f'<li class="pdf-toc-chapter"><a href="#chapter-{index}">'
            f"{html.escape(title)}</a></li>"
            for index, title in group["chapters"]
        )
        nested = f"<ol>{children}</ol>" if children else ""
        rendered.append(
            f'<li class="pdf-toc-section"><a href="#chapter-{group["target"]}">'
            f'{html.escape(group["title"])}</a>{nested}</li>'
        )
    return "".join(rendered)


def _document(articles, base_url, online_url, version):
    """Namespace IDs and map cross-page links to in-document destinations."""
    from bs4 import BeautifulSoup

    online_url = online_url.rstrip("/") + "/"
    destinations = {}
    for index, entry in enumerate(articles):
        url, article = entry["url"], entry["article"]
        key = _path(url)
        destinations[key, ""] = f"chapter-{index}"
        title_node = article.find("h1")
        seen = {}
        for element in article.select("[id]"):
            old_id = element["id"]
            seen[old_id] = seen.get(old_id, 0) + 1
            new_id = f"chapter-{index}--{old_id}"
            if seen[old_id] > 1:
                new_id += f"--{seen[old_id]}"
            if element is title_node:
                new_id = f"chapter-{index}"
            destinations.setdefault((key, old_id), new_id)
            element["id"] = new_id
        if title_node is not None and not title_node.has_attr("id"):
            title_node["id"] = f"chapter-{index}"

    chapters = []
    for index, entry in enumerate(articles):
        url, article = entry["url"], entry["article"]
        key = _path(url)
        if entry.get("section") and not entry.get("section_index"):
            # Chromium uses the accessibility heading levels for bookmarks.
            # Keep the printed heading styles while nesting each chapter and
            # its subheadings beneath the section overview in the PDF outline.
            for heading in article.select("h1, h2, h3, h4, h5, h6"):
                heading["aria-level"] = str(int(heading.name[1]) + 1)
        for node in article.select(
            "script, .headerlink, .md-content__button, .rf-page-toc, " ".md-clipboard"
        ):
            node.decompose()
        for details in article.select("details"):
            details["open"] = ""
        for node in article.select("[hidden]"):
            del node["hidden"]
        for node in article.find_all(True):
            for attribute in ("aria-labelledby", "aria-describedby", "headers", "for"):
                if attribute in node.attrs:
                    value = node[attribute]
                    values = value if isinstance(value, list) else value.split()
                    node[attribute] = " ".join(
                        destinations.get((key, value), value) for value in values
                    )
        # The line-number column cannot stay aligned when long code lines wrap.
        # Keep source IDs in the code; omit the decorative gutter in print.
        for node in article.select("td.linenos"):
            node.decompose()
        for node in article.select(".tabbed-set"):
            labels = node.select(":scope > .tabbed-labels label")
            blocks = node.select(":scope > .tabbed-content > .tabbed-block")
            for label, block in zip(labels, blocks, strict=True):
                heading = BeautifulSoup("", "html.parser").new_tag(
                    "p", attrs={"class": "pdf-tab-title"}
                )
                heading.string = label.get_text(" ", strip=True)
                block.insert(0, heading)
            for label in node.select(":scope > .tabbed-labels, :scope > input"):
                label.decompose()
        for anchor in article.select("a[href]"):
            href = anchor["href"]
            resolved = urlsplit(urljoin("https://manual.invalid/" + url, href))
            if resolved.netloc != "manual.invalid":
                continue
            target = destinations.get(
                (_path(resolved.path), unquote(resolved.fragment))
            )
            if target:
                anchor["href"] = "#" + target
            else:
                anchor["href"] = urljoin(online_url, resolved.path.lstrip("/"))
                if resolved.query:
                    anchor["href"] += "?" + resolved.query
                if resolved.fragment:
                    anchor["href"] += "#" + resolved.fragment
        for image in article.select("img[src]"):
            if "twemoji" in image.get("class", []):
                # Use the original shortcode rather than a remote emoji asset.
                # API notation such as :py: and :mm: otherwise becomes a flag.
                image.replace_with(image.get("title") or image.get("alt", ""))
                continue
            image["src"] = urljoin(base_url + url, image["src"])
            image.attrs.pop("loading", None)
        title_node = article.find("h1")
        if title_node is None:
            raise ValueError(f"Missing chapter heading: {url}")
        article["class"] = ["pdf-chapter", "md-typeset"]
        article["id"] = f"article-{index}"
        chapters.append(str(article))

    safe_version = html.escape(version)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Robot Framework Manual — {safe_version}</title>
<link rel="stylesheet" href="{base_url}assets/fonts.css">
<link rel="stylesheet" href="{base_url}assets/highlight-light.css">
<link rel="stylesheet" href="{base_url}assets/pdf.css">
</head><body data-md-color-scheme="default">
<section class="pdf-cover">
  <p class="pdf-brand">Robot Framework®</p>
  <h1>Reference Manual</h1><p class="pdf-version">{safe_version}</p>
  <p class="pdf-rule"></p>
  <p>Installation · Syntax · Execution · Libraries · Extension interfaces</p>
  <p class="pdf-online-reference">
    <a href="{html.escape(urljoin(online_url, 'libraries/'))}">
      Library keyword reference (online)</a> ·
    <a href="{html.escape(urljoin(online_url, 'api/'))}">
      Python API reference (online)</a>
  </p>
  <p class="pdf-copyright">© Robot Framework Foundation</p>
</section>
<nav class="pdf-contents" aria-label="Table of contents">
  <h1>Table of contents</h1><ol>{_contents(articles)}</ol>
</nav>
<main>{''.join(chapters)}</main></body></html>"""


def _prepare_tables(page):
    """Keep short rows intact while allowing long descriptions to paginate."""
    return page.evaluate("""() => {
        const tables = [...document.querySelectorAll('table:not(.highlighttable)')];
        for (const table of tables) {
            const columns = Math.max(1, ...[...table.rows].map(row =>
                [...row.cells].reduce((sum, cell) => sum + cell.colSpan, 0)));
            // Content-based sizing alone can squeeze a short label down to a
            // single letter when another cell contains a long description.
            const width = Math.min(table.getBoundingClientRect().width,
                document.documentElement.clientWidth);
            table.style.setProperty('--pdf-column-min',
                `${Math.min(96, width / (columns * 2))}px`);
            for (const row of table.rows) {
                row.classList.toggle('pdf-short-row',
                    row.getBoundingClientRect().height <= 96);
            }
        }
        return tables.length;
    }""")


def generate_pdf(site, pages, output, version, online_url):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Install requirements.txt and run "
            "'python -m playwright install --only-shell chromium'."
        ) from error

    base_url = site.resolve().as_uri() + "/"
    articles = _articles(site, pages)
    with TemporaryDirectory(prefix="manual-pdf-") as directory:
        document = Path(directory) / "manual.html"
        document.write_text(
            _document(articles, base_url, online_url, version), encoding="utf-8"
        )
        with sync_playwright() as playwright:
            # Default to Playwright's Chromium; allow an installed browser override.
            channel = os.environ.get("MANUAL_PDF_BROWSER_CHANNEL") or None
            browser = playwright.chromium.launch(channel=channel)
            try:
                # Match the printable width of A4 with 18 mm side margins so
                # row heights are measured at the same width as the PDF.
                page = browser.new_page(
                    color_scheme="light", viewport={"width": 658, "height": 979}
                )
                page.set_default_timeout(120_000)
                log.info("Printing %s manual articles", len(articles))
                page.goto(document.as_uri())
                page.emulate_media(media="print")
                page.evaluate("document.fonts.ready")
                _prepare_tables(page)
                broken = page.evaluate("""() => [...document.images]
                    .filter(image => !image.complete || !image.naturalWidth)
                    .map(image => image.src)""")
                if broken:
                    raise ValueError(f"Missing PDF images: {broken}")
                output.parent.mkdir(parents=True, exist_ok=True)
                safe_version = html.escape(version)
                footer = f"""<div style="font:8pt sans-serif;color:#444;width:100%;
                    margin:0 18mm;border-top:1px solid #008682;padding-top:6px;
                    display:flex;justify-content:space-between">
                    <span>Robot Framework Manual · {safe_version}</span>
                    <span><span class="pageNumber"></span> /
                    <span class="totalPages"></span></span>
                    </div>"""
                page.pdf(
                    path=str(output),
                    format="A4",
                    print_background=True,
                    outline=True,
                    tagged=True,
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template=footer,
                    margin={
                        "top": "18mm",
                        "bottom": "20mm",
                        "left": "18mm",
                        "right": "18mm",
                    },
                )
            finally:
                browser.close()
