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

## Repository Boundary

The published repository should contain the tool source, small required assets,
schemas, examples, and documentation. Large local fixtures, generated reports,
and test output directories should remain ignored development artifacts.
