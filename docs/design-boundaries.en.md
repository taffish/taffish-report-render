# Design Boundaries

`taffish-report-render` is a report compiler for TAFFISH flow outputs. Its
design goal is consistency, auditability, and standalone delivery.

## What the Renderer Does

The renderer:

- validates TOML/JSON report specs;
- resolves result assets relative to `--root`;
- compiles fixed components into a shared TAFFISH report shell;
- embeds supported images, tables, text, PDB payloads, runtime packs, and native
  HTML/QC reports;
- writes provenance sidecars;
- validates the final standalone HTML contract.

## What the Renderer Does Not Do

The renderer does not:

- run biological analysis;
- run statistical models;
- download data during normal rendering;
- decide scientific interpretation;
- act as a general website builder;
- allow arbitrary per-report raw HTML/JS/CSS;
- replace upstream native QC tools.

## TOML-Only Report Structure

Report authors should express report structure in TOML or canonical JSON. A
report can reference result assets, but should not depend on extra layout files,
external JavaScript, or hand-written HTML fragments.

If a report needs new behavior, add a fixed renderer component with a documented
TOML contract.

Structured explanations follow the same boundary. `note_items` accepts only
fixed kinds, localized labels, escaped plain-text paragraphs, and equal-length
localized lists. It is not a Markdown, HTML, CSS, class/style/event,
JavaScript, or URL-behavior escape hatch.

## Standalone HTML

The final report should be readable as one HTML file. Sidecars are retained for
audit and debugging, not for opening the report.

Supported assets should be embedded by default unless:

- they are too large for the report boundary;
- they are intentionally external, such as large genome tracks;
- a component explicitly requests linked mode.

## Runtime Packs

Optional browser runtimes are packaged by the renderer tool/image and embedded
only when requested. Normal users configure runtime-backed components in TOML;
they do not pass JavaScript files to the renderer.

## Native Subreports

Native HTML/QC reports should preserve upstream behavior as much as possible.
They are opened as isolated subpages so MultiQC, FastQC, fastp, Qualimap, and
similar outputs can run their own JavaScript without colliding with the top-level
TAFFISH report.

## Testing Boundary

`tests/test-real-run.sh` is the real report regression entrypoint. It must use
the tool CLI plus TOML/JSON specs only. It must not hand-write, copy, or patch
final HTML. Generated outputs are local regression artifacts and are ignored by
Git.

Responsive validation applies to the entire shell: hero, sidebar, nested
navigation, language controls, section headings, structured notes, card
headers, badges, action rows, workflow, tables, code, alignments, and viewers.
Page-level horizontal overflow is a failure. Intentional internal scrolling for
tables, code, alignments, and viewer surfaces must remain available; do not hide
defects with global overflow clipping.

The fixed visual matrix covers `1600x1000`, `1280x900`, `390x844`, both
languages, 200% zoom, and print/PDF. Media component widths additionally cover
`901px`, `900px`, `621px`, and `620px`: image/copy remains two-column at
`901px` and folds image-first at `900px`; compact notes remain two-column at
`621px` and fold to one column at `620px`. These boundaries are component-width
container queries with equivalent viewport fallbacks. The folded image remains
centered at natural width, capped by `min(720px, 85vh)` instead of being enlarged
to the content width. Print/PDF uses a stable `180mm` image cap, and paired
structured-note cards align only within their own row.

## Repository Boundary

The published repository should contain the tool source, small required assets,
schemas, examples, and documentation. Large local fixtures, generated reports,
and test output directories should remain ignored development artifacts.
