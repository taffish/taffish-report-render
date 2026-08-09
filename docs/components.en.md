# Component Reference

`taffish-report-render` uses fixed components. A report spec chooses components
and points them at result assets; it does not provide custom HTML, JavaScript,
or CSS.

For concise CLI field documentation:

```sh
taf-taffish-report-render components
taf-taffish-report-render component-doc all
taf-taffish-report-render component-doc interactive_plot
```

## Shared Rules

Every component has:

- `id`: stable unique ID within the report;
- `type`: registered component type;
- optional localized `title`, `text`, `caption`, or similar visible labels.
- ordered `note_items`, using the shared strict, localized, plain-text contract
  documented in [the report spec](report-spec.en.md#structured-explanations-with-note_items).

All asset paths are relative to `--root`. Components must not require extra
configuration files outside TOML/JSON. Browser runtimes are packaged by the
tool and are embedded only when the component requests them.

Use this shared field instead of component-specific question/reading fields,
HTML callouts, or custom CSS:

```toml
[[sections.components.note_items]]
kind = "reading"
label.en = "How to read"
label.zh = "如何阅读"
body.en = "Check the legend first, then map each item to the source table."
body.zh = "先核对图例，再与源表逐项对应。"
```

Collection components copy their ordered `note_items` into every expanded
fixed component and normalized JSON. The renderer still owns layout, wrapping,
and responsive behavior.

## Overview Components

### `dashboard_cards`

Render metric cards from a TSV file.

Common fields:

- `source`: TSV/CSV file.
- `title`: localized component title.
- `columns`: optional column selection.

Typical input columns:

- `metric`
- `value`
- `label_en` / `label_zh`
- `note_en` / `note_zh`
- `status`

Use this for project summaries, sample counts, read counts, module counts, or
small quality summaries.

### `status_grid`

Render module status cards.

Common fields:

- `source`: TSV/CSV file.
- `status_column`: column containing `OK`, `WARN`, `FAIL`, or similar values.
- `title`: localized title.

Use this for report-level checks and module completion summaries.

### `quality_gate_table`

Render PASS/WARN/FAIL quality criteria.

Common fields:

- `source`: TSV/CSV file.
- `status_column`: status column.
- `title`: localized title.

The component preserves full values and wraps long text. It should not hide
scientific evidence to make the layout prettier.

## Tables and Text

### `table_preview`

Render a TSV/CSV preview with an embedded full table viewer.

Common fields:

- `source`: TSV/CSV file.
- `title`: localized title.
- `preview_rows`: number of rows shown before expansion.
- `max_rows`: maximum embedded rows; use carefully for huge matrices.
- `fold_i18n_columns`: whether to fold `*_en` / `*_zh` language pairs.
- `allow_full_table`: whether the report can expand the full embedded table.
- `note`: localized interpretation text displayed above the table.

Behavior:

- wide tables must remain horizontally scrollable;
- long cell values must wrap or expand without breaking the card;
- full-table expansion happens in place, not as a separate duplicate table;
- users can inspect, search, sort, copy, and scroll within the embedded table.

### `code_file`

Render a short text artifact with copy support.

Common fields:

- `path`: text file path under `--root`.
- `language`: optional display language such as `text`, `json`, `newick`.
- `title`: localized title.

Use this for Newick trees, short JSON snippets, command fragments, small
configuration files, or method text.

## Diagrams and Images

### `workflow_diagram`

Render a structured workflow diagram from nodes declared in TOML.

Common fields:

- `source`: TSV file containing ordered workflow rows.
- paired `step_en` / `step_zh`, `note_en` / `note_zh`, and optional
  `status_en` / `status_zh` columns are rendered in the active report language.
- legacy `step`, `flow`, `status`, and `outdir` columns remain supported.

Use this for high-level report route diagrams, not for arbitrary SVG drawing.

### `plot_card`

Render an embedded image card.

Common fields:

- `image`: PNG/JPEG/WebP/SVG path under `--root`.
- `title`: localized title.
- `note`: localized interpretation or explanation.
- `caption`: localized caption.
- `layout`: `grid` (default), `wide`, or `media`.
- `note_position`: `bottom` (default) or `top` for `grid`/`wide`.
- `image_position`: `left` (default) or `right` for `media`.
- `media_image_ratio`: image-column share for `media`; default `0.42`, valid
  range `0.25` through `0.70`.
- `media_vertical_align`: `start` (default) or `center`.
- `media_gap`: `compact`, `normal` (default), or `relaxed`.
- `media_note_layout`: `auto` (default), `stack`, or `compact`.
- `zoom`: enable the large-image viewer; default `true`.
- `default_fit`: `contain` (default) or `original` in the viewer.

Behavior:

- images are embedded as data URIs when allowed;
- clicking opens a fit-to-window lightbox;
- modal scroll/zoom should not scroll the underlying page;
- the original file can be opened when the report preserves a source link;
- each `media` card owns one row and is never merged into the ordinary plot
  grid;
- desktop `media` cards use validated CSS Grid tracks; the ratio is interpreted
  within the two-column space and does not include the predefined gap;
- `auto` resolves from valid structured items: zero through three use `stack`,
  while four or more use `compact`; an explicit empty `compact` request safely
  resolves to `stack`;
- `compact` places the centered title/action header above the image and copy,
  then uses a two-column note grid; each note label and body remains one
  internal reading column, while `boundary`, `limitation`, and `next` span the
  note grid;
- media behavior responds to the component width: at `900px` and below the
  image precedes the copy even when `image_position = "right"`; at `620px` and
  below compact notes become one column. Equivalent viewport-query fallbacks
  cover browsers without container-query support;
- long titles, links, and uninterrupted identifiers wrap inside the copy
  column; images retain their full aspect ratio with `object-fit: contain`;
- compact image and copy columns stretch to the same row height without fixed
  card heights, cropping, absolute positioning, or overflow clipping;
- PNG, JPEG, WebP, and SVG use renderer-owned deterministic MIME mappings and
  the same embedding and lightbox behavior; their exact data URI prefixes do
  not depend on the host or container MIME database.

Example:

```toml
[[sections.components]]
type = "plot_card"
id = "effector-concept-figure"
image = "03_results/figures/effector-concept.png"
layout = "media"
image_position = "left"
media_image_ratio = 0.42
media_vertical_align = "start"
media_gap = "normal"
media_note_layout = "auto"
zoom = true
default_fit = "contain"
title.en = "Fungal infection and effector action sites"
title.zh = "病原真菌侵染与效应子作用位置"
note.en = "The figure and its interpretation remain adjacent on wide screens."
note.zh = "图片与解释在宽屏中保持相邻。"

[[sections.components.note_items]]
kind = "reading"
label.en = "How to read"
label.zh = "如何阅读"
body.en = "Read the title first, then compare the figure and structured notes."
body.zh = "先读标题，再对照图片与结构化说明。"
```

Use `media` for literature figures, conceptual models, background diagrams, or
simple input schematics with substantial explanatory text. Keep dense
axis-heavy scientific results in `layout = "wide"` with
`note_position = "top"`. The renderer never converts `wide` into `media`
automatically. Media-only fields on other layouts and unknown or out-of-range
values fail validation; arbitrary CSS strings are not accepted.

### `plot_collection`

Expand a TSV image index into multiple `plot_card` components.

The TSV should contain at least an image path and a stable ID/title. This is a
compile-time helper; expanded cards appear in `report.normalized.json`.

## Interactive Results

### `interactive_plot`

Render an ECharts-based browser view from already-computed TSV/CSV rows.

Supported `kind` values:

- `volcano`
- `ma`
- `pca`
- `ora_dotplot`

Common fields:

- `kind`: plot kind.
- `source`: TSV/CSV file.
- `title`: localized title.
- column mapping fields, depending on plot kind.
- threshold defaults, such as adjusted p-value or log2 fold-change cutoffs.
- display defaults such as colors, opacity, point size, and top-N limits.

Important boundary:

The browser only filters, recolors, and browses existing rows. It does not
re-run DESeq2, enrichment, PCA, or any statistical model. Threshold controls
change the view of precomputed results, not the underlying analysis.

Use this for volcano plots, MA plots, PCA scatter plots, and ORA/GSEA-style
dotplots when the source table is already finalized.

## Native HTML/QC Reports

### `native_subreport`

Embed or link a native HTML report generated by an upstream tool, such as
MultiQC, FastQC, fastp, or Qualimap.

Common fields:

- `source`: HTML file under `--root`.
- `kind`: `multiqc`, `fastqc`, `fastp`, `qualimap`, or another documented kind.
- `embed_policy`: `embed`, `link`, or `auto`.
- `title`: localized title.

Behavior:

- embedded native reports open in an isolated local subpage;
- heavy JS reports must run inside their own document, not inside the top-level
  report JavaScript context;
- linked mode is allowed when a native report is too large or intentionally
  external.

### `native_subreport_collection`

Expand a TSV index of native HTML reports into `native_subreport` components.

Use this for many FastQC reports, per-sample Qualimap reports, and other
repeated upstream HTML outputs.

## Structure and Genome Components

### `structure_viewer`

Render PDB or structure-overlay evidence.

Common fields:

- `pdb`: primary PDB path.
- `pdbs`: optional multiple models with labels and colors.
- `runtime`: `builtin` or `ngl`.
- `image`: optional static structure image.
- `sites` or marker table: optional motif/site marker data.
- display controls such as style, marker visibility, model visibility, opacity,
  and marker size.

Behavior:

- the built-in viewer gives a lightweight offline fallback;
- `runtime = "ngl"` embeds the packaged NGL runtime only for reports that need
  it;
- PDB text and parsed atom payloads must be embedded so fallback remains useful;
- static structure images should use the same image-card/lightbox behavior as
  other report images.

### `genome_browser`

Render an IGV-based genome browser component.

Common fields:

- `runtime`: `igv` for embedded IGV runtime.
- `viewer_mode`: `embedded`, `linked`, or a mode selector when both are
  available.
- `reference`: FASTA/FAI or reference configuration.
- `tracks`: BED, bedGraph, BAM/BAI, VCF/TBI, BigWig, or other IGV-supported
  tracks.
- `locus`: initial locus.

Boundary:

Small reference and track files can be embedded. Large genome tracks may remain
external URLs or user-served files, but this must be explicit and auditable in
the report. TOML controls report-level configuration; IGV's own menus and
session behavior remain inside the IGV viewer.

## Phylogeny and Alignment

### `tree_viewer`

Render a Newick tree as inline SVG and keep the original tree file copyable.

Common fields:

- `path`: Newick file.
- `layout`: rectangular or radial when supported.
- display options such as colors, label size, branch width, and support labels.

Use this for small-to-medium phylogeny trees in TAFFISH flow reports.

### `sequence_alignment`

Render FASTA or CLUSTAL alignments.

Common fields:

- `path`: alignment file.
- `format`: `fasta` or `clustal`.
- `palette`: residue coloring palette.
- display options such as line width, consensus row, and label width.

Use this for report-level review of compact alignments. Very large alignments
should stay as downloadable/source files.

## Collection Components

Collection components are TOML convenience helpers. They are expanded before
HTML rendering:

- `plot_collection` -> `plot_card`
- `table_collection` -> `table_preview`
- `code_file_collection` -> `code_file`
- `native_subreport_collection` -> `native_subreport`

The expanded result is written to `report.normalized.json`.

## Layout Contract

Components must follow the shared TAFFISH report layout:

- titles and source paths stay at the top;
- primary evidence stays in the middle;
- action buttons align consistently, usually near the lower left of cards;
- same-type cards keep consistent relative element positions;
- wide tables scroll horizontally;
- sections and subsections have visible spacing;
- report navigation order matches right-side content order.

If a new result type needs a new layout, add a renderer component and document
its TOML contract instead of writing one-off HTML.
