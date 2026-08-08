# taffish-report-render 测试数据

本目录描述 `taffish-report-render` 使用的维护者本地真实报告渲染 fixture。它们不是重新运行
生物学分析流程，而是从已经完成的真实 flow/report 结果树中抽取报告编译器需要的
表格、图片、PDB、manifest/report metadata 和 native HTML/QC 报告，用于对标正式报告。
真实 fixture payload 默认属于本地开发资产，已通过 `.gitignore` 忽略；发布到 GitHub
的仓库只应保留源代码、文档、schema、示例 TOML、小型必要资产和安装/运行所需内容。

目标是做保守的回归测试。未来 renderer 在迁移旧报告生成逻辑前，必须能用这些 fixture
生成至少不低于现有 TAFFISH 报告能力的结果。

## Fixture 家族

```text
fixtures/              本地忽略目录；维护者真实 fixture payload
  ngs-qc/             NGS QC 报告 fixture，包含 MultiQC、fastp 和 FastQC
  bam-qc/             BAM QC 报告 fixture，包含 samtools/mosdepth 和 MultiQC
  phylogeny/          phylogeny 报告 fixture，包含 PNG/SVG/PDF 树图
  rnaseq-reference/   RNA-seq 有参模式报告 fixture
  rnaseq-denovo/      RNA-seq 无参模式报告 fixture
  chengdu-yuanda-report12/
                      成都圆大 PUFA 第 12 步结构比较真实报告 fixture
```

每个 fixture 使用这个形状：

```text
<fixture>/
  report.toml         未来 renderer 实现使用的输入草案
  00_reports/         报告级 summary/provenance 文件和小型 baseline
  03_results/         真实报告所需图片、表格、PDB 或 native HTML report 输入
```

`fixtures.tsv` 可记录本 fixture 集合的来源 flow 输出；如果真实 payload 不提交，文档中
应说明对应真实结果树的准备方式。

## 有意排除的内容

fixture 不复制 raw reads、BAM 文件、完整 count matrix、完整日志、大型中间目录，
也不复制 50 MB 以上的最终 RNA-seq HTML 报告。大文件应留在来源 flow example 中。
renderer 测试只需要足够数据证明固定报告组件、资产嵌入、native HTML 子报告打包、
结构查看器、声明式多语言、导航和 standalone HTML 行为正确。`tests/smoke.sh`
只做快速契约检查；`tests/test-real-run.sh` 同时跑真实 flow 报告复现和真实报告风格的
组件回归报告。`test-real-run` 不使用 demo、假 viewer 或测试 shim 作为通过依据。

这些 fixture 还用于回归检查报告组件抽象本身：

- section 生成一级目录，component 生成子目录，并能随滚动自动展开；
- plot、table、native subreport 等不同组件各自使用固定布局，不能互相拉伸；
- collection 组件只作为编译期便利写法，必须在测试中展开为普通 `plot_card`、
  `table_preview`、`code_file` 或 `native_subreport`，并写入 `report.normalized.json`；
- `chengdu-yuanda-report12` 使用真实结构比较报告数据验证 `structure_viewer` 的 PDB asset
  记录、内置轻量 3D trace viewer payload、静态 PyMOL 图和普通报告不默认嵌入重型 runtime
  的边界；
- plot 图片可在单文件报告内放大查看，默认整图可见并可手动缩放；table preview
  使用页面内可折叠表格卡，完整表格在边界内直接进入固定高度二维滚动窗口；
- 文件名、路径、长 ID 和表格值必须在底层组件内安全换行，不能溢出卡片边界；
- renderer 固定 UI 文案按声明语言输出，原始业务数据值保持原样且不做机器翻译；
- native HTML/QC 子报告按 `embed_policy` 打包或链接，多页静态 HTML 可通过
  `embed_linked_pages` 或 `pages` 一并打包，并在 `embedded_html_reports.tsv` 中记录状态。

## 生成输出

`testdata/` 只保存 fixture 输入。真实渲染测试的输出应写入 `tests/` 下的已忽略目录，
并分成两个子目录：

```text
tests/test-real-run-out/
  flow-reports/            现有真实 flow 报告复现
  component-regression/    真实报告风格的组件/runtime/TOML 回归报告
```

不要把生成出来的 HTML 输出混回 fixture 输入目录。

本 app 只保留一个真实渲染测试脚本，用于把维护中的完整真实报告和组件回归报告生成成本地
可打开的 standalone HTML。这个脚本不再区分普通版和 full 版；每个场景都从真实 flow 输出、
公开 example report 目录或小而真实的领域 fixture 动态生成 `report.full.toml`：

```sh
tests/test-real-run.sh
tests/test-real-run.sh --clean
tests/test-real-run.sh ngs-qc rnaseq-reference rnaseq-denovo
```

默认运行包含两组场景。第一组是当前全部真实 flow 报告复现：

```text
ngs-qc
bam-qc
phylogeny
rnaseq-reference
rnaseq-denovo
chengdu-yuanda-report12
```

第二组是 7 个真实报告风格的组件回归报告，每个报告用小而真实的领域数据验证一种 runtime
或组件接口：

```text
component-basic-report
component-media-layout-report
component-structured-notes-report
component-echarts-report
component-tree-alignment-report
component-igv-report
component-ngl-native-report
```

这些组件回归场景不是 demo。即使数据量很小，也必须有真实生信语义、真实 runtime、
真实报告章节、固定 `04_reports/` sidecar 和可审计来源；不能用假 HTML、测试版 Python
行为、空白 viewer 或 NGL/IGV shim 通过 `test-real-run`。

`component-media-layout-report` 使用真实系统发育树、RNA-seq 热图和蛋白结构置信度图片，
覆盖横图、竖图、透明背景图、左右换位、`0.30/0.42/0.50/0.70` 比例、顶部/居中对齐、
三种预定义间距、长中英文说明、连续 media 卡片以及 media/grid/wide 混排。
`component-structured-notes-report` 使用长双语科研叙述、六项双语列表、SHA-256、accession、
run ID、URL 样式与无空格长串，覆盖全部 14 种固定 `note_items.kind`、恶意文本转义、
normalize/migrate/explain 保留，以及 wide/media/table/workflow/技术附录的响应式和打印边界。
默认 full real-run 会在渲染前预检本轮选中场景需要的全部浏览器 runtime；如果 NGL 和
IGV 同时缺失，脚本应同时报告这两个真实 runtime 缺口，不能只在第一个缺口处停止而让
后续组件没有被检查。

`component-igv-report` 依赖中央 yeast reference fixture，并从真实 SGD FASTA/GFF3 派生
`chrI:1-5000` 的 mini FASTA、FAI、gene BED 和 GC bedGraph。这个组件回归同时覆盖
embedded 与 linked 模式，并把小型 reference/track 作为 data URI 内嵌进主 HTML。
如果中央 yeast reference 缺失，`test-real-run` 必须失败并提示先用
`taf-rnaseq-yeast-get-data` 获取 reference 数据；不能回退到 `hg38`、`example.org`
或其它伪数据。源码树没有 IGV runtime 时，`test-real-run` 必须硬失败，并提示使用
已 vendored 的源码树 runtime pack、正式发布镜像中的 runtime pack，或显式维护者
环境变量指向的真实 runtime；不能在测试中联网下载 npm/CDN JavaScript 来补齐缺口。

RNA-seq 场景不把 100 MB 级 `collected_html/` bundle 复制进 `testdata/fixtures/`，
而是直接从 `repos/apps/bio/flows/rna-seq/example-reports/` 下维护的真实 24 样本
示例结果读取全量资源。`rnaseq-reference` 会声明并检查全部 DE/富集 PNG 图、
expression/alignment/count/alignment_qc MultiQC、24 个 FastQC、24 个 Qualimap 和
interpretation companion HTML；`rnaseq-denovo` 会声明并检查真实无参组装、表达、
注释、DE/富集图、MultiQC、FastQC 和 interpretation companion HTML。

如果需要用别的真实结果树测试，可设置：

```sh
TAFFISH_REPORT_RENDER_RNASEQ_REFERENCE_ROOT=/path/to/yeast-standard-report \
  tests/test-real-run.sh --clean rnaseq-reference

TAFFISH_REPORT_RENDER_RNASEQ_DENOVO_ROOT=/path/to/yeast-denovo-standard-report \
  tests/test-real-run.sh --clean rnaseq-denovo

TAFFISH_REPORT_RENDER_CHENGDU_YUANDA_REPORT12_ROOT=/path/to/report12-fixture \
  tests/test-real-run.sh --clean chengdu-yuanda-report12
```

默认输出：

```text
tests/test-real-run-out/flow-reports/<fixture>/report.full.toml
tests/test-real-run-out/flow-reports/<fixture>/04_reports/taffish_report.html
tests/test-real-run-out/flow-reports/<fixture>/04_reports/report.spec.toml
tests/test-real-run-out/flow-reports/<fixture>/04_reports/report.normalized.json
tests/test-real-run-out/flow-reports/<fixture>/04_reports/report.manifest.json
tests/test-real-run-out/flow-reports/<fixture>/04_reports/report_files.tsv
tests/test-real-run-out/flow-reports/<fixture>/04_reports/embedded_html_reports.tsv
tests/test-real-run-out/component-regression/<case>/report.full.toml
tests/test-real-run-out/component-regression/<case>/04_reports/taffish_report.html
tests/test-real-run-out/rendered_reports.tsv
tests/test-real-run-out/flow-reports/rendered_reports.tsv
tests/test-real-run-out/component-regression/rendered_reports.tsv
```

`tests/test-real-run-out/` 已在 `.gitignore` 中忽略，只用于维护者本地人工视觉检查和回归对比。
`tests/smoke.sh` 的临时输出固定写入 `tests/smoke-out/`，不能和真实报告回归共用目录，
避免快速 smoke 清理时误删 full real-run 报告。

## Fixture 覆盖能力

- `ngs-qc` 在 real-run 中直接读取 `ngs-qc-flow/tests/test-real-run-out`，覆盖
  status/quality 表、真实参数、raw/clean seqkit 表、MultiQC、两个 fastp/Plotly HTML、
  raw FastQC 和 clean FastQC HTML。
- `bam-qc` 在 real-run 中直接读取 `bam-qc-flow/tests/test-real-run-out`，覆盖
  samtools flagstat/stats/idxstats/coverage、mosdepth 表和 MultiQC HTML。
- `phylogeny` 在 real-run 中直接读取 `phylogeny-flow/tests/test-real-run-out`，覆盖
  输入统计、参数、alignment/trimming 表、PNG/SVG/PDF 矩形/环形树图、`tree_viewer`
  Newick 树、`sequence_alignment` 多序列比对、Newick 文本和 tree model/support 表。
- `rnaseq-reference` 覆盖当前最复杂的报告家族，并以官网 yeast reference 示例为
  结构目标：dashboard/project 表、workflow/reference/QC/alignment/DE/enrichment/
  tools 章节、DE 图、enrichment 图、summary 表、interpretation companion HTML、
  MultiQC、FastQC 和 Qualimap HTML bundle。
- `rnaseq-denovo` 以官网 yeast de novo 示例为结构目标，覆盖 reference 分支缺席说明、
  无参 assembly/expression/annotation 章节、DE/enrichment、tools/source links、
  MultiQC/FastQC bundle 和 interpretation report 输入。
- `chengdu-yuanda-report12` 使用成都圆大 EPA 项目第 12 步结构比较真实结果，覆盖
  summary/quality/similarity/motif 表、9 张统计图、22 张 PyMOL 结构图，以及 11 组
  target/EPA/DHA 三模型 PDB `structure_viewer`。它用于证明复杂结构报告可以通过
  TOML 低代码配置和本地结果文件重建正式报告级阅读体验；为控制仓库体量，当前只复制
  overlay 所需 33 个 PDB，暂不复制 98 个单模型 PDB。
- `component-basic-report` 使用真实报告风格的 summary、status、quality gate、长表格、
  SVG 图、文本和 native HTML，覆盖基础组件、语言列折叠、图片 lightbox、表格原地展开和
  子报告 payload。
- `component-media-layout-report` 使用真实系统发育树、RNA-seq 热图和蛋白结构置信度图片，
  覆盖 media/grid/wide 混排、固定比例、左右位置、长双语说明及 820/821 px 折叠边界。
- `component-structured-notes-report` 覆盖全部 14 种固定说明 kind、长双语段落与列表、
  恶意文本安全转义、TOML/JSON 往返保留、collection 展开和页面级响应式溢出治理。
- `component-echarts-report` 使用真实表达/富集结果语境的 DE、PCA 和 ORA 表，覆盖
  volcano、MA、PCA、ORA dotplot 四类 ECharts 交互图以及控件布局。
- `component-tree-alignment-report` 使用系统发育语境的 Newick 和 FASTA，覆盖
  `tree_viewer`、`sequence_alignment` 和可复制树文件。
- `component-igv-report` 用真实 genome-locus 审阅语境覆盖 `genome_browser runtime="igv"`
  的 TOML、payload 和 standalone 边界；`test-real-run` 需要真实 IGV runtime 或明确的
  linked-only 审阅模式，不能用 shim 通过。
- `component-ngl-native-report` 复用 Chengdu Yuanda report 12 的真实 target/EPA/DHA
  PDB 叠合、静态结构图、motif 位点表和 Foldseek 表，覆盖
  `structure_viewer runtime="ngl"`、完整 PDB `pdbText` payload、内置 fallback atoms、
  位点 marker、静态图 lightbox 和真实 NGL runtime 边界；`test-real-run` 需要真实
  NGL runtime 或明确失败提示。

`tests/test-real-run.sh` 会为每个场景动态生成对应的
`tests/test-real-run-out/.../report.full.toml`，再用
`report-render render --root <source-root>` 生成报告，并检查关键标记、图、表、原生 HTML
payload、表格交互、图片放大、语言列折叠、runtime payload 和 template checker。

部分 fixture 包含 `00_reports/existing_*_report.html` 作为历史内容/视觉 baseline。
这些文件不自动等同于合格 renderer 输出。例如，复制来的旧报告可能保留了有价值的内容覆盖，
但仍缺少当前模板 marker。新 renderer 输出必须通过当前模板检查器和本 app 的 checklist，
即使历史 baseline 本身没有完全通过。

fixture 只应在新增报告组件或真实 bug 需要代表性输入时增长。保持它们小而有目的。
