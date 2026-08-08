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
- TAFFISH version: `0.3.1-r1`
- kind: `tool`
- image candidate: `ghcr.io/taffish/taffish-report-render:0.3.1-r1`
- runtime identity: `taffish-report-render 0.3.1-r1`
- native platforms: `linux/amd64`, `linux/arm64`

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
renderer-defined spacing; report specs never inject arbitrary CSS.

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
surfaces keep intentional internal scrolling. Media plots fold at `820px`,
structured label/body rows fold at `680px`, and narrow navigation becomes a
single readable column.

Use `taf-taffish-report-render component-doc COMPONENT` for concise CLI field
documentation, or read the full
[component reference](docs/components.en.md).

## Output Contract

The primary deliverable is one standalone HTML file. The renderer also writes
audit sidecars next to the report, including:

- `report.spec.toml`
- `report.full.toml`
- `report.normalized.json`
- `report.manifest.json`
- `report_files.tsv`
- `embedded_html_reports.tsv`
- `report_template_version.txt`

These sidecars are useful for review, reproducibility, and debugging. They are
not required to open the final HTML report.

For image-bearing reports, successful file records in `report_files.tsv` prove
that the source assets were read, but do not by themselves prove the embedded
MIME. Release validation therefore checks the rendered HTML data URI prefixes
and `inspect-html` counts as separate contracts.

## Testing Contract

Maintainer regression tests generate reports from TOML specs through the tool
CLI only. Test scripts must not hand-write, patch, or copy final HTML. Generated
test output directories are ignored by Git.

Large real-flow fixtures and local regression outputs are development assets,
not user-installation requirements. The repository should retain source code,
documentation, schemas, examples, and small required assets; local `testdata`
payloads and generated `tests/*-out/` directories are ignored.

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
