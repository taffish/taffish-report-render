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
title.en = "Project Overview"
title.zh = "项目总览"
text.en = "Review the report status and main outputs first."
text.zh = "先查看报告状态和主要输出。"

[[sections.components]]
id = "summary"
type = "dashboard_cards"
source = "03_results/tables/summary.tsv"
```

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
