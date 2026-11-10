# Manual theme maintenance

The manual uses Material for MkDocs through ProperDocs. Styles and scripts live
in `docs/assets/`; template overrides live in `overrides/`.

## Stylesheets

`properdocs.yml` loads the stylesheets in this order:

1. `fonts.css`: self-hosted fonts.
2. `theme.css`: color ramp and Material palette variables.
3. `highlight-light.css` and `highlight-dark.css`: syntax colors.
4. `navigation.css`: header, tabs, sidebars, drawer and search.
5. `extra.css`: article layout, typography, examples and footer.
6. `page-toc.css`: mobile page TOC.

Keep `page-toc.css` after `extra.css` to override shared disclosure styles.

## Navigation

Match Material's breakpoints: `60em` for the right TOC and `76.25em` for the
primary sidebar; use `59.9375em` and `76.1875em` for maximum-width queries.

- Place the version selector between the tabs and theme toggle, following the
  [RFCP syllabus](https://robotframework.org/robotframework-RFCP-syllabus/docs/overview).
  Its host must be the first `.md-header__topic` for Material's mike integration.
- Select the bundled Octicons theme icons in `properdocs.yml`. Material handles
  system preference and saved choices.
- Reinitialize page controls through `document$` after instant navigation.
  Keep labels and the native mobile TOC usable without JavaScript.
- Contain focus only in the open drawer, restore changed `inert` states, and use
  `preventScroll` when focusing drawer panes.
- Focus the destination heading or fragment after instant navigation, preserving
  scroll position. Do not force focus on initial load. After a mobile TOC jump,
  focus the heading before collapsing the TOC.
- Keep `search.highlight` disabled; highlight result previews only. Support Tab
  and arrows through results. Escape returns focus to the search opener or input;
  Tab at either end closes search. Clearing collapsed desktop search must not
  open results.
- Hide closed search controls and results with `visibility`; opacity and size
  alone leave them accessible.

## Rendered log examples

HTML log tables in `execution/basics.md` and `extend/libraries.md` need both
Material wrappers (`md-typeset__scrollwrap` and `md-typeset__table`), a region name,
and `tabindex="0"` on the scroll wrapper. Leave a blank line after HTML blocks.

## Build options

API and PDF generation are opt-in for fast local previews. Each generator logs
its setting:

| Environment variable | Default | Effect when set to `1` |
| --- | --- | --- |
| `GENERATE_API_DOCS` | Disabled | Generate Python API pages and their navigation. |
| `GENERATE_PDF` | Disabled | Export the manual as a PDF, with links to online reference documentation. |

Both publishing workflows enable both options. The legacy
`DO_NOT_GENERATE_API_DOCS` override still disables API generation when non-empty.
Fast previews show the API overview without links to omitted pages.
See [the main README](../../README.md#optional-generate-api-documentation-and-pdf)
for commands in Bash, PowerShell and Command Prompt. Restart `properdocs serve`
after changing environment variables or the cached Python hook (`pdf.py`).

## Manual PDF

`pdf.py` exports the manual articles to `downloads/robot-framework-manual-<version>.pdf`
in the version's site directory, for example `robot-framework-manual-7.5.pdf`.
Local and `dev` builds use `robot-framework-manual-dev.pdf`.
Python API and library keyword references stay
online; their links remain in the PDF. Release labels follow the mike deployment
version. Local and `dev` exports are labeled "Development edition".

Publishing builds show one compact link in the left navigation with a download
icon and file size. It has no `download` attribute, allowing browser PDF viewers
to open it. Builds without a PDF hide the link.

PDF export works on Windows, macOS and [Playwright-supported Linux distributions](https://playwright.dev/python/docs/intro#system-requirements).
Python dependencies are included in the root `requirements.txt`. Before enabling
export, install the PDF browser with the same command on each platform:

```console
python -m playwright install --only-shell chromium
```

On Linux, add `--with-deps` to install Chromium's system libraries as well, as the
publishing workflows do. Ordinary documentation previews do not need Chromium.

For a PDF-only build in PowerShell:

```powershell
$env:GENERATE_PDF = '1'
properdocs build
```

In Bash, use `GENERATE_PDF=1 properdocs build`. Unset the variable for normal
previews. Chromium is the default. Optionally, set `MANUAL_PDF_BROWSER_CHANNEL`
to `chrome` or `msedge` to use an installed browser instead.

Chromium prints one local HTML document using self-hosted fonts and
`docs/assets/pdf.css`. The design follows the [RFCP syllabus](https://github.com/robotframework/robotframework-RFCP-syllabus/blob/main/tools/gen_pdf.robot):
A4 paper, light colors, teal accents, OCR-A headings, a cover, linked contents and
numbered footers. Contents and bookmarks follow the site's section hierarchy.
Print rules expand tabs and disclosures, wrap examples, repeat table headings
and allow long rows to continue across pages. Line-number gutters are omitted
so wrapped code stays aligned.

Run `python -m unittest discover -s doc/manual/tests -v` and check the exported
contents, bookmarks, links, tables, examples and images after changes. Chromium
adds accessibility tags; review reading order separately for PDF/UA conformance.
Export time and file size are logged after each build.

Publishing workflows run the regression tests before installing the PDF browser.
They use setup-python's pip cache and install only Chromium's headless shell.

## Upgrading Material

Last compatibility review: Material **9.8.1**. See the
[header layout decision](https://github.com/pekkaklarck/manual/issues/30).

Compare `partials/header.html`, `partials/nav.html` and
`partials/javascripts/outdated.html` with the installed templates. Preserve the
outdated banner's URL base. Check DOM assumptions in `navigation.js` and selectors
and offsets in `navigation.css`.

Run `properdocs build` with API generation enabled. Use a mike preview with
`versions.json` to check version controls and the outdated banner.
Update the reviewed version above after completing these checks.

## Verification

Check both palettes at mobile, tablet and desktop widths, including long articles
and nested API pages:

- Header controls, version menu, long titles and resizing across breakpoints.
- Keyboard order, visible focus, drawer exits and search navigation.
- Current-page markers, TOC jumps and focus after instant navigation.
- Example scrolling and code/line-number alignment at larger text sizes.
- With NVDA or VoiceOver: landmarks, control names, roles, expanded states and
  reading order. Hidden controls must be unavailable; Skip to content must reach
  the article. Material places the desktop right TOC before the article in the DOM.

Lighthouse and browser checks do not replace screen reader testing.
