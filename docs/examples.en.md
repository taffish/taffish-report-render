# Examples and Flow Integration

This document shows how to use `taffish-report-render` from the command line
and from a TAFFISH flow.

## Create a Starter Workspace

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

The starter workspace contains a small TOML spec and tiny local assets. It is
for learning the structure, not for scientific interpretation.

## Minimal TOML

```toml
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "en"

[project]
flow_name = "my-flow"
flow_version = "0.1.0-r1"
analysis_mode = "standard"
title.en = "My TAFFISH report"
title.zh = "我的 TAFFISH 报告"
subtitle.en = "Generated from TOML and local result assets."
subtitle.zh = "由 TOML 和本地结果资产生成。"

[[sections]]
id = "overview"
kicker.en = "Overview"
kicker.zh = "总览"
title.en = "0. Project Overview"
title.zh = "0. 项目总览"
text.en = "Review the report status and main outputs first."
text.zh = "先查看报告状态和主要输出。"

[[sections.components]]
id = "summary"
type = "dashboard_cards"
source = "03_results/tables/summary.tsv"
title.en = "0.1 Inputs, Outputs, and Headline Results"
title.zh = "0.1 输入、输出与核心结果"
```

For a long report, continue with `1.`, `2.`, and `1.1`, `1.2`; an independent
technical appendix may use `A.` / `A.1`. Put the same number in every localized
title, while keeping semantic IDs stable and unnumbered. The renderer preserves
author-provided numbering but does not generate it automatically. Reordering a
chapter may change its visible number without changing anchors, asset paths, or
provenance identity.

Do not keep growing one long `note`. Retain a one- or two-sentence lead and
split the explanation into structured items:

```toml
[[sections.note_items]]
kind = "question"
label.en = "Question"
label.zh = "问题"
body.en = "Are the inputs sufficient for downstream interpretation?"
body.zh = "输入数据是否足以支持后续判读？"

[[sections.components.note_items]]
kind = "reading"
label.en = "How to read"
label.zh = "如何阅读"
items.en = ["Read the quality-gate status first.", "Then compare observations with thresholds."]
items.zh = ["先看质量门状态。", "再核对观察值与阈值。"]
```

Sections and all fixed components use the same `note_items` contract. Localized
lists have equal counts and values remain escaped plain text. See the
[report-spec manual](report-spec.en.md#structured-explanations-with-note_items)
for the complete field and kind contract.

## Flow Integration

A flow should write result assets into its output directory and write a report
spec under `04_reports/`.

Recommended flow-side rendering sequence:

```sh
report_spec="${outdir}/04_reports/report.toml"
report_html="${outdir}/04_reports/taffish_report.html"

taf-taffish-report-render lint --spec "$report_spec" --root "$outdir"
taf-taffish-report-render explain --spec "$report_spec" --root "$outdir"
taf-taffish-report-render render \
  --spec "$report_spec" \
  --root "$outdir" \
  --out "$report_html" \
  --force \
  --validate
taf-taffish-report-render inspect-html "$report_html" --validate
```

The flow may generate `report.toml` dynamically from its own manifest and result
indexes, but the final HTML must still be created by `taffish-report-render`.
Tests should not hand-write or patch final HTML.

## Interactive Plot Example

```toml
[[sections.components]]
id = "de_volcano"
type = "interactive_plot"
kind = "volcano"
source = "03_results/tables/de.results.tsv"
title.en = "Interactive volcano plot"
title.zh = "交互火山图"
x_column = "log2FoldChange"
p_column = "padj"
label_column = "gene_id"
default_padj = 0.05
default_abs_log2fc = 1.0
```

The browser-side controls only filter and recolor existing rows. They do not
re-run differential expression.

## Replace a Project-Specific Side-by-Side Patch

Before `layout = "media"`, a flow might render a normal plot card and then add
private HTML/CSS to place a literature or concept figure beside a long note.
Replace that patch with the renderer-owned TOML contract:

```toml
[[sections.components]]
type = "plot_card"
id = "infection-model"
image = "03_results/figures/infection-model.webp"
layout = "media"
image_position = "right"
media_image_ratio = 0.35
media_vertical_align = "center"
media_gap = "relaxed"
media_note_layout = "auto"
zoom = true
default_fit = "contain"
title.en = "Infection model"
title.zh = "侵染模型"
note.en = "Interpretation stays beside the complete uncropped figure on desktop."
note.zh = "桌面端解释与完整、未裁切的图片保持相邻。"

[[sections.components.note_items]]
kind = "reading"
label.en = "How to read"
label.zh = "如何阅读"
body.en = "Read the title, then compare the complete figure with the explanation."
body.zh = "先读标题，再把完整图片与解释对照阅读。"
```

No post-render HTML, JavaScript, or CSS modification is needed. `auto` uses the
compact composition when a card has at least four valid structured note items.
At a component width of `900px` and below the renderer puts the image above the
text; at `620px` and below compact notes become one column. Dense
axis-heavy result plots should continue to use `layout = "wide"` and
`note_position = "top"`.

## Structure Viewer Example

```toml
[[sections.components]]
id = "structure_overlay"
type = "structure_viewer"
runtime = "ngl"
title.en = "Target/reference structure overlay"
title.zh = "靶标/参考结构叠合"

[[sections.components.pdbs]]
label = "target"
path = "03_results/structures/target.pdb"
color = "#1f2933"

[[sections.components.pdbs]]
label = "reference"
path = "03_results/structures/reference_aligned.pdb"
color = "#0e8a96"
```

NGL is embedded only when requested. The component also embeds parsed structure
payloads for fallback review.

## Genome Browser Example

```toml
[[sections.components]]
id = "genome_locus"
type = "genome_browser"
runtime = "igv"
viewer_mode = "embedded"
title.en = "Genome locus browser"
title.zh = "基因组位点浏览器"
locus = "chrI:1-5000"

[sections.components.reference]
name = "SGD_R64_chrI_slice"
fasta = "03_results/igv/chrI.fa"
fai = "03_results/igv/chrI.fa.fai"

[[sections.components.tracks]]
name = "Genes"
format = "bed"
path = "03_results/igv/genes.bed"
```

Small tracks can be embedded. Large tracks can be linked, but that choice must
be explicit and auditable.

## Native QC Subreports

```toml
[[sections.components]]
id = "multiqc"
type = "native_subreport"
kind = "multiqc"
source = "04_reports/multiqc/index.html"
title.en = "MultiQC report"
title.zh = "MultiQC 报告"
embed_policy = "embed"
```

Native subreports are opened as isolated local subpages inside the standalone
report package.

## Maintainer Real-Run Test

For this app, the maintainer regression test is:

```sh
tests/test-real-run.sh
```

The script must:

- clean old `tests/test-real-run-out/` output by default;
- render all maintained real flow report fixtures;
- render all component regression reports;
- use the tool CLI plus TOML/JSON specs only;
- generate fixed `flow-reports/` and `component-regression/` output trees;
- fail when required real runtime packs or fixture data are missing.

Generated real-run output is ignored by Git.
