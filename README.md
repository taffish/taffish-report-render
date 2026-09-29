# taffish-report-render

`taffish-report-render` is a TAFFISH-native report compiler. It turns one
structured report specification plus one local result directory into a
standalone TAFFISH HTML report.

It does not run biological analysis, re-compute statistics, or decide scientific
interpretation. Flows remain responsible for producing results and writing a
report spec. The renderer is responsible for the shared TAFFISH report shell,
fixed components, asset embedding, language switching, navigation, native
subreport packaging, provenance sidecars, and final standalone HTML validation.

Core model:

```text
report.toml or report.manifest.json + local result root -> standalone HTML report
```

Package identity:

- name: `taffish-report-render`
- command: `taf-taffish-report-render`
- TAFFISH version: `0.4.1-r1`
- kind: `tool`
- image candidate: `ghcr.io/taffish/taffish-report-render:0.4.1-r1`
- runtime identity: `taffish-report-render 0.4.1-r1`
- native platforms: `linux/amd64`, `linux/arm64`

This is an unpublished successor candidate. Publication and system installation
remain maintainer-controlled; use the release validation receipt for readiness,
not the version number alone.

## Container Backends

Use one installed, fixed-version wrapper from a directory containing your input
and output paths. The same report arguments apply on each backend:

```sh
TAFFISH_CONTAINER_BACKEND=docker taf-taffish-report-render -- --version
TAFFISH_CONTAINER_BACKEND=podman taf-taffish-report-render -- --version
TAFFISH_CONTAINER_BACKEND=apptainer taf-taffish-report-render -- --version
```

Docker and Podman require a working engine; Apptainer requires a compatible
Linux host and a writable personal SIF cache or an administrator-prepared SIF.
Image acquisition is a setup step; report rendering itself is offline. Linux
amd64 native Docker/Podman/Apptainer and arm64 native Docker are this candidate's
validation targets. Other low-risk backend/platform combinations must not be
inferred to have been separately tested; consult the validation matrix.

On Linux, Docker's default container root can create root-owned output
directories. Select the host UID/GID as a local runtime policy when outputs
must remain writable/removable by the ordinary host user:

```sh
TAFFISH_CONTAINER_BACKEND=docker \
TAFFISH_DOCKER_RUN_ARGS="--user $(id -u):$(id -g)" \
  taf-taffish-report-render render --spec my-run/report.toml --root my-run \
  --out my-run/new-report/report.html --validate
```

Rootless Podman and Apptainer use the normal user on the validated Linux host.
The renderer requires no root-only writes; it does not chmod/chown user inputs
or output trees at startup. The UID/GID choice is a site policy, not a new app
requirement or permission escalation.

The wrapper deliberately exposes a stable renderer subcommand interface
(`command_mode = false`), not arbitrary automatic executable dispatch. `--help`
and `--version` refer to the wrapper; `-- --help` and `-- --version` query the
container's renderer. The two-line TAF entry uses the native quoted container
heredoc switch (`<'container:...>`) and bundled Bash. This prevents the host shell
from expanding dollar signs or substitutions when TAFFISH selects heredoc mode.
No extra entrypoint script or service is introduced. The CLI uses file arguments,
not stdin for report specs/assets.

### Paths containing spaces or shell punctuation

TAFFISH 0.11.0 expands `*ARGV*` as shell text, so ordinary single-layer shell
quoting does not preserve wrapper argument boundaries. Keep one literal quoting
layer in each affected argument (same workaround on all three backends):

```sh
taf-taffish-report-render new --outdir '"report with spaces"'
taf-taffish-report-render render --spec '"report with spaces/report.toml"' \
  --root '"report with spaces"' --out '"report with spaces/04_reports/report.html"' --validate
```

For single-line paths (including apostrophes, `$`, semicolons and Unicode), call the
wrapper from Python with `subprocess.run([wrapper, *map(shlex.quote, args)], check=True)`.
Do not interpolate untrusted filenames into a shell string. This is the narrow
workaround for the current TAFFISH core, not a claim that plain quoted argv was
fixed. Wrapper paths containing newlines/heredoc delimiters are not supported;
use ordinary single-line paths or direct container argv for those cases.
Direct container `report-render` takes normal argv and needs no extra layer.
`new` prints a wrapper command escaped for both layers. Keep free-text titles
inside TOML/JSON; there are no `new --title-en/--title-zh` options.

Runtime writes: explicit HTML/sidecar output paths and temporary scratch only.
No project input, installation tree, bundled runtime, system cache or model/database
root needs modification. Python bytecode writes are disabled. Large scientific
inputs remain user-owned; the renderer does not download or select them.

The report spec is the only structural configuration input. Users do not write
custom HTML, JavaScript, CSS, or per-report code. The result root provides data
assets such as tables, plots, PDB files, Newick trees, alignments, text files,
and native HTML/QC reports. Optional browser runtimes such as ECharts, NGL, and
IGV are managed by the tool/image and are activated by TOML components.

## Directory Model

The three render arguments have different jobs:

- `--spec` points to the report structure file.
- `--root` points to the result directory that contains real assets.
- `--out` points to the final standalone HTML file to write.

A typical flow output directory looks like this:

```text
my-run/
  00_inputs/
  01_logs/
  02_intermediate/
  03_results/
    tables/
      summary.tsv
    plots/
      pca.png
  04_reports/
    report.toml
    taffish_report.html
```

Render it with:

```sh
taf-taffish-report-render render \
  --spec my-run/04_reports/report.toml \
  --root my-run \
  --out my-run/04_reports/taffish_report.html \
  --force \
  --validate
```

Inside `report.toml`, paths are written relative to `--root`, not relative to
the TOML file:

```toml
source = "03_results/tables/summary.tsv"
image = "03_results/plots/pca.png"
```

That means the renderer reads:

```text
my-run/03_results/tables/summary.tsv
my-run/03_results/plots/pca.png
```

The final HTML is the file to share with readers. The copied spec, normalized
manifest, and asset indexes written next to it are audit/debug sidecars.

## Quick Start

List available components:

```sh
taf-taffish-report-render components
```

Create a minimal starter spec:

```sh
taf-taffish-report-render init > report.toml
```

Create and render a runnable local starter workspace:

```sh
taf-taffish-report-render new --outdir report-example
taf-taffish-report-render lint --spec report-example/report.toml --root report-example
taf-taffish-report-render render \
  --spec report-example/report.toml \
  --root report-example \
  --out report-example/04_reports/taffish_report.html \
  --force \
  --validate
```

In a TAFFISH flow, the usual pattern is to write `report.toml` under
`<outdir>/04_reports/` and render against the flow output root:

```sh
taf-taffish-report-render render \
  --spec "${outdir}/04_reports/report.toml" \
  --root "${outdir}" \
  --out "${outdir}/04_reports/taffish_report.html" \
  --force \
  --validate
```

All `source`, `image`, `path`, and similar asset fields are resolved relative to
`--root`. Absolute paths and path traversal outside the result root are rejected
so reports do not accidentally embed maintainer-local files.

## Documentation

User-facing documentation is split by language:

- Report spec manual:
  [English](docs/report-spec.en.md) / [中文](docs/report-spec.zh.md)
- Component reference:
  [English](docs/components.en.md) / [中文](docs/components.zh.md)
- Examples and flow integration:
  [English](docs/examples.en.md) / [中文](docs/examples.zh.md)
- Runtime packs:
  [English](docs/runtime-packs.en.md) / [中文](docs/runtime-packs.zh.md)
- Design boundaries:
  [English](docs/design-boundaries.en.md) / [中文](docs/design-boundaries.zh.md)
- Terminal help source:
  [docs/help.md](docs/help.md)

The command-line help is intentionally concise and terminal-oriented. Detailed
field explanations live in the manuals above.

## Stable Components

Current stable components include:

- `dashboard_cards`
- `status_grid`
- `quality_gate_table`
- `table_preview`
- `code_file`
- `workflow_diagram`
- `plot_card`
- `interactive_plot`
- `structure_viewer`
- `tree_viewer`
- `sequence_alignment`
- `genome_browser`
- `native_subreport`
- `plot_collection`
- `table_collection`
- `code_file_collection`
- `native_subreport_collection`

`table_preview` and `quality_gate_table` place interpretation text above the
table. `workflow_diagram` supports paired `step_en` / `step_zh`, `note_en` /
`note_zh`, and `status_en` / `status_zh` fields. `plot_card` supports the
historical `grid` and `wide` layouts plus a responsive `media` layout for a
side-by-side figure and explanation. Media cards use validated ratios and
renderer-defined spacing; report specs never inject arbitrary CSS. For media
cards, `media_note_layout = "auto"` is the default: zero through three valid
structured items retain the established stacked copy, while four or more use a
compact title-above, image-and-notes-below composition. Authors can request
`stack` or `compact` explicitly; an empty compact request safely falls back to
stack.

PNG, JPEG, WebP, and SVG assets use renderer-owned MIME mappings, so the same
input produces the same data URI on every supported host and container. The
host `/etc/mime.types` database is used only as a fallback for formats outside
this core set. `validate-html` rejects an actual `<img>` whose data URI has a
non-image MIME, and `inspect-html` reports
`non_image_img_data_uri_count` alongside the existing `data_image_count`.

For long reports, author visible hierarchical numbers in localized titles,
such as `0. Project Overview`, `2. Results`, and `2.1 Headline Evidence`.
Use the same number in every language, while keeping section and component IDs
semantic, stable, and unnumbered. The renderer preserves title order and text;
it does not auto-number reports. See the report-spec manual for the full
reader-first structure and numbering rules.

Sections and every fixed component also support ordered `note_items`. A short
localized `note` can remain as a lead, while structured items express questions,
inputs, methods, elements, reading guidance, observations, meaning, boundaries,
limitations, next actions, and provenance. Each item is strictly typed and
localized. Paragraphs and real plain-text lists render as escaped semantic HTML;
Markdown, raw HTML, classes, style, script, URLs, and event attributes are not
accepted as item fields.

The shared shell uses component-aware responsive containment rather than global
content clipping. Long titles, run IDs, SHA-256 values, labels, notes, and action
rows wrap inside their owners. Tables, code blocks, alignments, and viewer
surfaces keep intentional internal scrolling. Media layout responds to the
component width, not only the viewport: compact cards fold their image/copy
columns at `900px`, compact note items become one column at `620px`, and narrow
navigation becomes a single readable column. Viewport-query fallbacks preserve
the same boundaries where container queries are unavailable. Once a compact
card folds, its image keeps natural width, remains centered, and is capped at
`min(720px, 85vh)` rather than stretching a portrait figure to the full content
column. Two-column structured-note cards align within each row, and print uses
a stable natural-width `180mm` image cap.

Use `taf-taffish-report-render component-doc COMPONENT` for concise CLI field
documentation, or read the full
[component reference](docs/components.en.md).

## Reading-Follow and Hierarchical Navigation (0.4.1)

Sections can declare `toc.parent`, `toc.collapsed`, and localized `toc.title`.
Every component can declare `toc.visible` and `toc.title`. Hiding a TOC entry
preserves its full body, anchor, downloads, and asset records. Ordinary scrolling
now follows the active chapter and its ancestors, closing unrelated branches,
with no separate triangle buttons or bulk toolbar by default. Structural fields
never implicitly switch interaction modes. No node `toc` retains the legacy look.
Report-level `[toc] interaction = "manual"` explicitly restores 0.4.0 independent
collapse controls. `collapsed` controls initial/manual state; the active reading
path takes precedence in follow mode. Focused navigation branches remain open
until focus leaves, without stealing keyboard focus or moving the reading viewport.
Existing 0.4.0 TOML remains valid, but the default interaction intentionally changes.
This is a new unpublished candidate, not an
instruction to replace installed renderers. See [English](docs/toc.en.md) /
[中文](docs/toc.zh.md) and [minimal example](examples/toc-minimal/report.toml).

## Output Contract

The primary deliverable is one standalone HTML file. The renderer also writes
audit sidecars next to the report, including:

- `report.spec.toml`
- `report.normalized.json`
- `report.manifest.json`
- `report_files.tsv`
- `report_layouts.tsv`
- `report_toc.json`
- `embedded_html_reports.tsv`
- `report_template_version.txt`

These sidecars are useful for review, reproducibility, and debugging. They are
not required to open the final HTML report.

For image-bearing reports, successful file records in `report_files.tsv` prove
that the source assets were read, but do not by themselves prove the embedded
MIME. Release validation therefore checks the rendered HTML data URI prefixes
and `inspect-html` counts as separate contracts.

`report_layouts.tsv` records each media card's declared, requested, and
effective note layout plus the valid structured-item count. This makes the
default `auto` decision auditable without rewriting the normalized spec.

## Testing Contract

Maintainer regression tests generate reports from TOML specs through the tool
CLI only. Test scripts must not hand-write, patch, or copy final HTML. Generated
test output directories are ignored by Git.

Large real-flow fixtures and local regression outputs are development assets,
not user-installation requirements. The repository should retain source code,
documentation, schemas, examples, and small required assets; local `testdata`
payloads and generated `tests/*-out/` directories are ignored.

The two orchestrators remain `tests/smoke.sh` and `tests/test-real-run.sh`.
`toc_fixture.py`, `toc-offline-smoke.py`, `image-offline-smoke.py` and
`browser-toc.cjs`, `browser-follow.cjs` and `prepare-toc-browser.py` are focused
fixtures/checkers, not alternative renderers.
Smoke requires a fresh output directory; it does not delete an existing path.

## Reproducible Candidate Build

Run from the app root, matching canonical Action `context: .` and
`file: docker/Dockerfile`:

```sh
docker build --platform linux/amd64 -f docker/Dockerfile -t taffish-report-render:0.4.1-r1-amd64 .
docker build --platform linux/arm64 -f docker/Dockerfile -t taffish-report-render:0.4.1-r1-arm64 .
docker run --rm --network none --read-only --tmpfs /tmp:rw,exec,nosuid,nodev \
  taffish-report-render:0.4.1-r1-arm64 python3 /opt/taffish-report-render/tests/toc-offline-smoke.py
docker run --rm --network none --read-only --tmpfs /tmp:rw,exec,nosuid,nodev \
  taffish-report-render:0.4.1-r1-arm64 python3 /opt/taffish-report-render/tests/image-offline-smoke.py
```

Use the matching tag/platform on an amd64 host. A cross-architecture build can
use local emulation, but that is not native runtime evidence. The canonical
Action builds on native runners; local success does not claim that unpublished
GitHub Actions have run. Base-image digest and bundled runtime checksums are
fixed in the Dockerfile; generated image IDs can differ with builder metadata.

The final image copies the cleaned Python/Alpine runtime from a pinned seed
stage: no pip/ensurepip or Python development headers are shipped. The supported
runtime remains Python standard library plus the packaged renderer and browser
assets, with pinned Alpine Bash 5.3.9-r1 for TAFFISH's quoted heredoc path.
Installing packages inside a running report image is not supported. The pinned
Alpine branch must still serve that exact Bash revision for a fresh build;
retain the OCI archive/digest when reproducing this tested candidate.

Source tests and browser QA (Node.js, Playwright and a local browser are
maintainer tools, not runtime image dependencies):

```sh
PYTHONDONTWRITEBYTECODE=1 TAFFISH_REPORT_RENDER_SMOKE_OUT=/path/to/new-smoke bash tests/smoke.sh
bash tests/test-real-run.sh --outdir /path/to/new-real-run
PYTHONPATH=python python3 tests/prepare-toc-browser.py --renderer "$PWD/bin/report-render" \
  --outdir /path/to/new-toc-cases
TAFFISH_TEST_BROWSER=/path/to/chrome node tests/browser-follow.cjs \
  /path/to/new-toc-cases /path/to/new-follow-receipt
TAFFISH_TEST_BROWSER=/path/to/chrome node tests/browser-toc.cjs \
  /path/to/new-toc-cases/manual/report.html /path/to/new-manual-receipt
```

Real-run fixture preparation and source-data requirements are documented in
`testdata/README.md`; missing real data is not replaced with fake scientific data.
Do not publish automatically. See the [release checklist](validation/0.4.1-r1-checklist.md)
and [machine receipt](validation/0.4.1-r1-validation-receipt.json).

## Boundaries

Use this renderer when a flow already has result assets and needs a stable
TAFFISH report. Do not use it as:

- a workflow engine;
- a statistics engine;
- a general website builder;
- a place to inject arbitrary raw HTML/JS into TAFFISH reports;
- a mechanism for runtime network downloads during normal report generation.

When a report needs new visual behavior, add or extend a fixed renderer
component and document its TOML contract instead of writing one-off report code.

## License

The TAFFISH app, renderer source, Dockerfile, documentation, and report shell are
licensed under Apache-2.0. Bundled browser runtimes retain their upstream
licenses and provenance: ECharts is Apache-2.0; legacy Plotly.js, NGL, and IGV.js
are MIT-licensed. Exact versions, source URLs, checksums, and notices are recorded
under `python/taffish_report_render/assets/` and
`python/taffish_report_render/runtime_packs/`.

The container also includes unmodified Alpine GNU Bash 5.3.9-r1 under
GPL-3.0-or-later, not Apache-2.0. Its upstream is
https://www.gnu.org/software/bash/bash.html and its Alpine packaging source is
`main/bash` at aports commit `1522c3193610902d8493f9790a2755c11f21f26d`.
The image's `/lib/apk/db/installed` retains package identity/source metadata;
`bash --version` exposes the upstream copyright/license notice. The distribution's
base-runtime licenses remain separate from the renderer and report data.
