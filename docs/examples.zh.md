# 示例与集成方式

本文件展示 `taffish-report-render` 的常见使用路线：最小入门示例、flow 集成、真实 fixture 测试
以及不同类型 flow 的推荐写法。

## 最小入门示例

生成本地示例目录：

```sh
taf-taffish-report-render new --outdir report-example
```

渲染：

```sh
taf-taffish-report-render lint --spec report-example/report.toml --root report-example
taf-taffish-report-render explain --spec report-example/report.toml --root report-example
taf-taffish-report-render render \
  --spec report-example/report.toml \
  --root report-example \
  --out report-example/04_reports/report.html \
  --force \
  --validate
```

打开：

```sh
open report-example/04_reports/report.html
```

这个入门示例只用于理解 spec、root、output 的关系，不是发布级测试。真实 flow 应该由自己的
步骤产生 summary 表、图片和 HTML 子报告，再写出 `report.toml`。`tests/test-real-run.sh`
必须使用真实报告输出和真实 runtime，不使用 demo、假 viewer 或 test shim 作为通过依据。

## 长报告的编号结构

正式报告建议先按读者问题组织，再给可见标题加层级编号。编号写在 `title.<lang>`，稳定
`id` 不带编号：

```toml
[[sections]]
id = "overview"
title.zh = "0. 项目总览"
title.en = "0. Project Overview"
note.zh = "先回答项目目的、输入、已完成工作、主要输出和当前结论。"
note.en = "Start with the purpose, inputs, completed work, outputs and current conclusion."

[[sections.components]]
type = "dashboard_cards"
id = "overview_headline"
title.zh = "0.1 输入、输出与核心结果"
title.en = "0.1 Inputs, Outputs and Headline Results"
source = "04_reports/project_summary_cards.tsv"

[[sections]]
id = "input_quality"
title.zh = "1. 输入数据是否可信"
title.en = "1. Can the Input Data Be Trusted?"

[[sections.components]]
type = "quality_gate_table"
id = "input_quality_gates"
title.zh = "1.1 输入质量门禁"
title.en = "1.1 Input Quality Gates"
source = "04_reports/input_quality_gates.tsv"
```

项目总览通常使用 `0.`，正文使用 `1.`、`2.`，组件使用 `1.1`、`1.2`。技术附录可以使用
`A.` / `A.1`。所有语言使用相同编号；章节重排只更新可见标题，不修改语义 ID、文件路径和
provenance 身份。renderer 当前不会自动编号。

长说明不要继续堆进一个 `note`。保留一两句导语，再用结构化条目：

```toml
[[sections.note_items]]
kind = "question"
label.zh = "问题"
label.en = "Question"
body.zh = "输入数据是否足以支持后续判读？"
body.en = "Are the inputs sufficient for downstream interpretation?"

[[sections.components.note_items]]
kind = "reading"
label.zh = "如何阅读"
label.en = "How to read"
items.zh = ["先看质量门状态。", "再核对观察值与阈值。"]
items.en = ["Read the quality-gate status first.", "Then compare observations with thresholds."]
```

section 与所有固定组件使用同一 `note_items` 契约；双语列表条数必须一致，内容只按纯文本
处理。完整字段和 kind 见 [Report Spec 结构](report-spec.zh.md#结构化说明-note_items)。

## Flow 中的推荐调用

flow 的标准做法：

1. 分析步骤把结果写入 `<outdir>/03_results/`、`<outdir>/04_reports/` 等目录；
2. flow 自己整理 summary TSV、版本表、参数表、HTML 子报告索引；
3. flow 生成 `<outdir>/04_reports/report.toml`；
4. flow 调用 `taf-taffish-report-render render`；
5. flow 检查最终 HTML 和索引文件存在。

示例：

```sh
report_spec="${outdir}/04_reports/report.toml"
report_html="${outdir}/04_reports/report.html"

taf-taffish-report-render lint \
  --spec "$report_spec" \
  --root "$outdir"

taf-taffish-report-render render \
  --spec "$report_spec" \
  --root "$outdir" \
  --out "$report_html" \
  --force \
  --validate
```

在 taf-flow 中，真实调用应写在实际执行位置的 `[[taf: ...]]` 里，并按 flow 规范提供
高级参数槽。例如：

```taf
[[taf: taf-taffish-report-render-v0.4.1-r1 render \
  --spec '"$report_spec"' \
  --root '"$outdir"' \
  --out '"$report_html"' \
  --force \
  --validate \
  ::(@:)report-render-step:: ]] </dev/null
```

这里的 `::(@:)report-render-step::` 默认必须为空，只为高级用户保留额外 renderer 参数接口。

## 从项目私有横向补丁迁移到 media

过去 flow 可能先生成普通图片卡，再注入私有 HTML/CSS，把文献图或概念图放在长说明旁边。
现在应直接改用 renderer 的 TOML 契约：

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
title.zh = "侵染模型"
title.en = "Infection model"
note.zh = "桌面端解释与完整、未裁切的图片保持相邻。"
note.en = "Interpretation stays beside the complete uncropped figure on desktop."

[[sections.components.note_items]]
kind = "reading"
label.zh = "如何阅读"
label.en = "How to read"
body.zh = "先读标题，再把完整图片与解释对照阅读。"
body.en = "Read the title, then compare the complete figure with the explanation."
```

不再需要渲染后修改 HTML、JavaScript 或 CSS。`auto` 在有效结构化条目达到 4 条时使用
compact；组件宽度 `900px` 及以下变成图片在前的单栏，`620px` 及以下 compact 条目也变成
单列。
坐标轴和标签密集的正式结果图仍应使用 `layout = "wide"` 与
`note_position = "top"`。

## NGS QC 模式

NGS QC 报告通常包含：

- `dashboard_cards`：样本数、输入 FASTQ 数、过滤状态；
- `quality_gate_table`：Q30、GC、reads 数等阈值；
- `table_preview`：seqkit raw/clean FASTQ 统计；
- `native_subreport`：MultiQC、fastp、FastQC。

可参考：

```text
testdata/fixtures/ngs-qc/report.toml
```

渲染 fixture：

```sh
tests/test-real-run.sh ngs-qc
```

## BAM QC 模式

BAM QC 报告通常包含：

- `dashboard_cards`：BAM 数、mapped reads、coverage 概览；
- `quality_gate_table`：mapping rate、duplication、depth 等判断；
- `table_preview`：samtools flagstat/stats/idxstats、mosdepth summary；
- `native_subreport`：MultiQC。

可参考：

```text
testdata/fixtures/bam-qc/report.toml
```

渲染 fixture：

```sh
tests/test-real-run.sh bam-qc
```

## Phylogeny 模式

Phylogeny 报告通常包含：

- `workflow_diagram`：alignment、trimming、model、tree；
- `table_preview`：alignment stats、model summary、support summary；
- `plot_card`：树图 PNG/SVG；
- `code_file`：Newick 树文件，方便复制到 iTOL、FigTree 等工具。

可参考：

```text
testdata/fixtures/phylogeny/report.toml
```

渲染 fixture：

```sh
tests/test-real-run.sh phylogeny
```

## RNA-seq 模式

RNA-seq 是当前最复杂的报告家族，通常包含：

- 项目总览；
- 分析路线图；
- 有参或无参路线说明；
- 表达定量与 QC；
- 比对/计数证据层；
- 差异表达图表；
- 富集图表；
- 原生 MultiQC/FastQC/Qualimap 子报告；
- interpretation companion HTML；
- 工具版本、参数和文件索引。

完整真实示例：

```sh
tests/test-real-run.sh rnaseq-reference rnaseq-denovo
```

默认读取：

```text
repos/apps/bio/flows/rna-seq/example-reports/yeast-standard-report/
repos/apps/bio/flows/rna-seq/example-reports/yeast-denovo-standard-report/
```

如果要用其他真实结果树：

```sh
TAFFISH_REPORT_RENDER_RNASEQ_REFERENCE_ROOT=/path/to/yeast-standard-report \
TAFFISH_REPORT_RENDER_RNASEQ_DENOVO_ROOT=/path/to/yeast-denovo-standard-report \
  tests/test-real-run.sh rnaseq-reference rnaseq-denovo
```

## TOML 很长怎么办

复杂报告的 TOML 变长是正常的。它只是把“展示哪些结果文件”显式列出来，比手写 HTML 更可审计。

推荐做法：

- flow 先生成机器可读的 summary/index TSV；
- 用 flow 内部小脚本根据 index 生成 `report.toml`；
- TOML 中只保存路径、标题、说明和组件参数；
- 不要把图片 base64、HTML payload 或大表格全文提前写进 TOML；
- 保留生成后的 `report.spec.toml` 和 `report.normalized.json`。

如果同一类组件重复非常多，例如 24 个 FastQC 子报告，flow 可以用脚本生成多个
`[[sections.components]]` block。renderer 负责统一布局和行为。

也可以使用 collection 组件，把重复组件先写进 TSV 索引：

```toml
[[sections.components]]
type = "native_subreport_collection"
id = "fastqc-reports"
source = "04_reports/html_reports.tsv"
kind = "fastqc"
embed_policy = "auto"
```

然后在渲染前检查并展开：

```sh
taf-taffish-report-render lint --spec report.toml --root "$outdir"
taf-taffish-report-render migrate --spec report.toml --root "$outdir" --format json > report.normalized.json
```

这种方式能把 TOML 长度压下来，同时仍然让最终 `report.normalized.json` 保留完整展开结果。

## 结构报告组件

PDB 结构、结构叠合或 docking pose 应使用 `structure_viewer`，不要在 flow 里临时复制
私有 3D viewer HTML。默认 `runtime = "builtin"` 使用轻量 trace viewer；需要更专业的
蛋白结构交互时可使用 `runtime = "ngl"`，报告会按需内嵌 NGL WebGL runtime。
正式报告和真实视觉检查必须使用真实 NGL bundle（发布镜像内置，或源码树已 vendored
runtime pack）。源码树中的 NGL test shim
只允许用于显式的 smoke/interface 测试，不能进入 `tests/test-real-run.sh`，也不能作为
最终结构交互效果的验收依据。

```toml
[[sections.components]]
type = "structure_viewer"
id = "domain-overlay"
static_image = "03_results/figures/domain_overlay.png"
runtime = "ngl"
representation = "cartoon"
show_surface = false
atom_filter = "ca"
height = 420
title.zh = "结构叠合"
title.en = "Structure overlay"

[[sections.components.models]]
id = "target"
pdb = "03_results/pdb/target.pdb"
color = "#087f74"
label.zh = "目标结构"
label.en = "Target"

[[sections.components.models]]
id = "reference"
pdb = "03_results/pdb/reference.pdb"
color = "#b7791f"
label.zh = "参考结构"
label.en = "Reference"
```

## 系统发育树和多序列比对

系统发育报告通常同时需要三个层次的证据：构树结果、树文件本身、以及构树前的多序列比对。
推荐组合是：

- `tree_viewer` 展示 Newick 树并保留复制入口；
- `sequence_alignment` 展示 FASTA/CLUSTAL 多序列比对；
- `code_file` 可作为额外的原始 Newick 或参数文件入口；
- `plot_card` 可展示单独绘制的出版级树图。

```toml
[[sections.components]]
type = "tree_viewer"
id = "tree-inline"
source = "03_results/tree/tree.nwk"
layout = "rectangular"
height = 460
title.zh = "系统发育树"
title.en = "Phylogenetic tree"
note.zh = "树图用于快速审阅；原始 Newick 可复制到专业绘图工具。"
note.en = "Use this tree for review; copy the Newick into a dedicated tree editor if needed."

[[sections.components]]
type = "sequence_alignment"
id = "trimmed-alignment"
source = "03_results/alignment/trimmed.fa"
format = "fasta"
alphabet = "protein"
show_consensus = true
max_sequences = 80
max_columns = 300
title.zh = "修剪后的多序列比对"
title.en = "Trimmed multiple sequence alignment"
```

`tree_viewer` 和 `sequence_alignment` 都只展示已有结果，不负责 MAFFT、trimAl、IQ-TREE、
FastTree 或其它计算。它们适合放入 phylogeny-flow 的最终报告，也适合其它需要审阅
树和比对证据的 flow。

## IGV 基因组浏览器

`genome_browser` 用于把已有 genome tracks 放进报告阅读路径。由于 BAM/VCF/BigWig
通常很大，当前稳定模式是外部数据：HTML 内嵌 IGV runtime 和配置，轨道数据由 HTTP(S)
或用户本地服务提供。小型审稿片段或组件回归 fixture 可把 FASTA/FAI/BED/bedGraph
作为 data URI 内嵌。报告仍应保留关键静态图和结果表，IGV 只是可浏览补充证据。

```toml
[[sections.components]]
type = "genome_browser"
id = "variant-locus"
runtime = "igv"
data_mode = "external"
genome = "hg38"
locus = "chr1:155,000,000-155,020,000"
height = 520
title.zh = "IGV 位点浏览"
title.en = "IGV locus browser"

[[sections.components.tracks]]
name = "RNA-seq coverage"
url = "https://example.org/sample.bw"
type = "wig"
format = "bigwig"
color = "#0f766e"

[[sections.components.tracks]]
name = "Variants"
url = "https://example.org/sample.vcf.gz"
index_url = "https://example.org/sample.vcf.gz.tbi"
type = "variant"
format = "vcf"
```

源码 smoke 可以用 IGV test shim 验证组件接口；真实 `tests/test-real-run.sh` 和视觉验收
需要发布镜像内置 runtime 或源码树已 vendored runtime pack。真实回归不能用 `example.org`
伪 URL；若没有现成大轨道，应从真实参考或测试数据派生一个小型 locus fixture。

小型内嵌轨道示例：

```toml
[[sections.components]]
type = "genome_browser"
id = "yeast-mini-locus"
runtime = "igv"
viewer_mode = "embedded"
viewer_modes = ["embedded", "linked"]
data_mode = "embedded-small-assets"
reference_name = "SGD_R64_chrI_slice"
reference_fasta = "03_results/genome/yeast_sgd_chrI_1_5000.fa"
reference_index = "03_results/genome/yeast_sgd_chrI_1_5000.fa.fai"
embed_reference = true
locus = "chrI:1-5000"

[[sections.components.tracks]]
name = "SGD genes"
type = "annotation"
format = "bed"
source = "03_results/tracks/yeast_sgd_chrI_1_5000_genes.bed"
embed = true
```

## 发布前建议检查

对一个使用 report renderer 的 flow，建议至少检查：

```sh
taf check
tests/smoke.sh
tests/formal.sh      # 如果该 flow 有正式测试
```

并人工打开最终 HTML，确认：

- 真实 TAFFISH logo 存在；
- 左侧目录顺序和右侧章节顺序一致；
- 语言切换正常；
- 主图片能放大查看；
- 表格能横向滚动到最右列；
- 原生 HTML 子报告能打开且不是空白；
- 主 HTML 可在无网络环境下打开。

若报告生成后包含 `embedded_html_reports.tsv`，还应检查每个子报告的 `status` 和 `bytes`。

## 交互图：差异表达和富集结果

`interactive_plot` 适合把已经计算好的差异表达或富集结果做成报告内交互视图。它不替代
DESeq2、edgeR、clusterProfiler 或其它分析工具；TOML 只声明源表、图形类型和默认查看阈值。

火山图示例：

```toml
[[sections.components]]
type = "interactive_plot"
id = "de-volcano"
kind = "volcano"
source = "03_results/tables/de.results.tsv"
title.zh = "交互式火山图"
title.en = "Interactive volcano plot"
default_padj = 0.05
default_log2fc = 1.0
max_points = 10000
```

MA 图示例：

```toml
[[sections.components]]
type = "interactive_plot"
id = "de-ma"
kind = "ma"
source = "03_results/tables/de.results.tsv"
title.zh = "交互式 MA 图"
title.en = "Interactive MA plot"
default_padj = 0.05
default_log2fc = 1.0
base_mean = "baseMean"
max_points = 10000
```

PCA 示例要求上游已经输出 PCA 坐标表；renderer 不从表达矩阵重新计算 PCA：

```toml
[[sections.components]]
type = "interactive_plot"
id = "de-pca"
kind = "pca"
source = "03_results/tables/pca_scores.tsv"
sample = "sample"
group = "condition"
pc1 = "PC1"
pc2 = "PC2"
x_label = "PC1"
y_label = "PC2"
title.zh = "交互式 PCA 图"
title.en = "Interactive PCA plot"
```

ORA dotplot 示例：

```toml
[[sections.components]]
type = "interactive_plot"
id = "ora-dotplot"
kind = "ora_dotplot"
source = "03_results/tables/enrichment.ora_results.tsv"
title.zh = "交互式 ORA dotplot"
title.en = "Interactive ORA dotplot"
default_padj = 0.05
top_n = 20
```

如果源表列名不符合默认识别规则，可以在 TOML 中显式指定 `gene`、`log2fc`、`padj`、
`pvalue`、`base_mean`、`sample`、`group`、`pc1`、`pc2`、`description`、`count`
或 `gene_ratio`。最终 HTML 会内嵌必要 payload 和 ECharts runtime，用户离线打开时
不需要源表文件。
