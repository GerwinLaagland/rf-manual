# Robot Framework Manual

:construction: Under development!

Robot Framework Manual is planned to replace the current
[Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
and also current [API docs](https://robot-framework.readthedocs.org/)
will be migrated into it.

Robot Framework Manual pages in this repository are written in Markdown, and the
website is built with
[ProperDocs](https://properdocs.org/), using [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
for visual design.

See the [generated manual](https://pekkaklarck.github.io/manual/).

## Contribution guidelines

Contributions are welcome, from typo fixes to corrections and additions.

Use American English for documentation prose, headings, and navigation labels.

Pages with related attachments use a page bundle: a folder containing `index.md`
and the page's images, downloadable examples, or sample HTML files. For example,
`doc/manual/docs/extend/libdoc/` contains the Libdoc page and its examples.
Pages without attachments remain standalone Markdown files. Keep shared styling
and branding in `doc/manual/docs/assets/`.

When moving a page, update its entry in `properdocs.yml` and all links to it.
Use relative paths for links and images; snippet includes use paths relative to
`doc/manual/docs/`, as configured in `properdocs.yml`.

To contribute, fork the repository, make your changes, and open a
[pull request](https://github.com/robotframework/robotframework/blob/master/CONTRIBUTING.rst#pull-requests).

## Setting up development environment

### Prerequisites

- **Python 3.13** or higher

### Installing dependencies

Create a Python virtual environment (with `venv`, `uv`, or another tool of your
choice) and run the commands below within it. Before installation, make sure your
working directory is the repository root containing `requirements.txt`.

#### Install dependencies

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

#### Verify the ProPerdocs installation

    properdocs --version

### Previewing the Manual

#### Start the development server

    properdocs serve

Example output:

    INFO    -  Building documentation...
    INFO    -  Manual PDF generation: disabled (set GENERATE_PDF=1 to enable)
    INFO    -  Cleaning site directory
    INFO    -  API documentation generation: disabled (set GENERATE_API_DOCS=1 to enable)
    INFO    -  Documentation built in 11.84 seconds
    INFO    -  [22:03:18] Watching paths for changes: 'doc/manual/docs', 'properdocs.yml', 'INSTALL.md', 'src/robot',
            'doc/manual/overrides'
    INFO    -  [22:03:18] Serving on http://127.0.0.1:8000/manual/

Open the [local preview](http://127.0.0.1:8000/manual/) in your browser.
The preview updates as you modify the pages.

#### Optional: generate API documentation and PDF

API and PDF generation are both disabled by default to keep local builds fast.
Each build logs whether they are enabled and how to turn them on.
To preview the generated API documentation:

Linux/macOS (Bash)

    GENERATE_API_DOCS=1 properdocs serve

Windows (PowerShell)

    $env:GENERATE_API_DOCS = '1'
    properdocs serve

Windows (Command Prompt)

    set "GENERATE_API_DOCS=1" && properdocs serve

To preview both the generated API documentation and the manual PDF, first
[install the PDF browser](doc/manual/README.md#manual-pdf), then enable both:

Linux/macOS (Bash)

    GENERATE_API_DOCS=1 GENERATE_PDF=1 properdocs serve

Windows (PowerShell)

    $env:GENERATE_API_DOCS = '1'
    $env:GENERATE_PDF = '1'
    properdocs serve

Windows (Command Prompt)

    set "GENERATE_API_DOCS=1" && set "GENERATE_PDF=1" && properdocs serve

Replace `properdocs serve` with `properdocs build` to build without starting the
preview server. Restart an existing preview server after changing these variables.

Both publishing workflows explicitly enable both options. The PDF links to online
library keyword documentation and the Python API reference; it does not require
API generation. Unset the variables to return to fast local
builds. The older `DO_NOT_GENERATE_API_DOCS` variable is still honored: any
non-empty value overrides `GENERATE_API_DOCS` and disables API generation.

### Stopping the preview server

To stop the development server, use the key combination:

    Ctrl + C

## Getting help

For help or to share ideas about the Manual, join us in the
[#manual](https://robotframework.slack.com/archives/C063Y9GEMUP) channel on Slack.
