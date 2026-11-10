"""Generate API documentation.

API docs are part of the source code. This script generates references to
them as well as navigation.

Based on a `mkdocstrings` [recipe][] and a [script][] they use themselves.

[recipe]: https://mkdocstrings.github.io/recipes/#automatic-code-reference-pages
[script]: https://github.com/mkdocstrings/mkdocstrings/blob/main/scripts/gen_ref_nav.py

Enable generation with `GENERATE_API_DOCS=1`; a non-empty
`DO_NOT_GENERATE_API_DOCS` overrides it. Read these settings here so API builds
and live rebuilds do not depend on the optional PDF hook.
"""

import logging
import os
import re
from pathlib import Path

import mkdocs_gen_files
from mkdocs_gen_files.nav import Nav

root = Path(__file__).resolve().parents[4]
nav = Nav()


def generate_api_docs(root: Path):
    """Generates page references and navigation entries."""
    src = root / "src"
    for path in sorted(src.rglob("*.py")):
        module = path.relative_to(src).with_suffix("").parts
        doc_path = path.relative_to(src).with_suffix(".md")
        full_doc_path = "api" / doc_path

        if module[-1] == "__init__":
            module = module[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
        elif module[-1][0] == "_":
            continue

        # Add navigation entry for each module with decoration.
        nav_parts = tuple(
            f'<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code> {part}'
            for part in module
        )
        nav[nav_parts] = doc_path.as_posix()

        # Generate page with a reference.
        with mkdocs_gen_files.open(full_doc_path, "w") as file:
            ident = ".".join(module)
            file.write(f"---\ntitle: {ident}\n---\n\n# ::: {ident}")

        # Set correct edit path.
        mkdocs_gen_files.set_edit_path(
            full_doc_path, "../../.." / path.relative_to(root)
        )


def generate_preview_overview(root: Path):
    """Keep the local overview useful without references to ungenerated pages."""
    source = (root / "doc/manual/docs/api/index.md").read_text(encoding="utf-8")
    source = re.sub(r"\[(robot(?:\.[A-Za-z_]\w*)+)\]\[\]", r"`\1`", source)
    heading, body = source.split("\n", 1)
    note = (
        '\n!!! note "Local preview"\n\n'
        "    Generated Python API pages are disabled in this preview. "
        "Set `GENERATE_API_DOCS=1` and restart the preview server to include them.\n"
    )
    with mkdocs_gen_files.open("api/index.md", "w") as file:
        file.write(heading + "\n" + note + body)
    mkdocs_gen_files.set_edit_path("api/index.md", "api/index.md")


# Add a navigation entry to the static `docs/api/index.md`.
nav["API"] = "index.md"

if os.getenv("GENERATE_API_DOCS") == "1" and not os.getenv("DO_NOT_GENERATE_API_DOCS"):
    logging.getLogger("properdocs.api").info("API documentation generation: enabled")
    generate_api_docs(root)
else:
    logging.getLogger("properdocs.api").info(
        "API documentation generation: disabled (set GENERATE_API_DOCS=1 to enable)"
    )
    generate_preview_overview(root)

# Generate navigation file for `literal-nav`.
with mkdocs_gen_files.open("api/nav.md", "w") as file:
    file.writelines(nav.build_literate_nav())
