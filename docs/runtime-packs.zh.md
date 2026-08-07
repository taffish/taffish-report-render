# Runtime Pack 设计

`taffish-report-render` 的核心仍然是固定组件编译器。Runtime pack 是为少数交互组件准备的
离线前端能力包，例如结构查看、基因组轨道查看、网络查看或通用交互图表。

## 基本原则

- Runtime pack 可以放进 Docker 镜像，供 renderer 离线读取。
- Runtime pack 不等于默认 HTML 依赖；最终报告只有在组件实际使用它时才内嵌。
- Runtime pack 不能从 CDN 加载，也不能要求用户打开报告时联网。
- Runtime pack 不能让 spec 执行任意 JavaScript；spec 只能选择已注册组件和组件参数。
- 每个 runtime pack 必须记录版本、来源、license、文件体积、checksum 和支持的组件。
- 每个使用 runtime pack 的组件都必须有真实 fixture、smoke/real-run 覆盖和视觉检查记录。
- 如果 runtime license 或来源不清楚，不能进入发布镜像。

这条规则允许镜像具备更多报告能力，同时保持普通报告轻量、稳定、可审计。

## 当前 runtime

| runtime | 状态 | 用途 | 嵌入策略 |
| --- | --- | --- | --- |
| `echarts-6.1.0` | 已随包携带 | `interactive_plot` 的火山图、MA 图和 ORA dotplot | 只在报告声明 `interactive_plot` 时内嵌 |
| `plotly-1.2.0` | 已随包携带 | 修复 legacy fastp HTML 中的远程 Plotly loader | 只在相关 `native_subreport` 需要替换历史 fastp loader 时内嵌 |
| `builtin-structure-trace` | 已随 renderer CSS/JS 携带 | `structure_viewer` 的轻量 PDB trace 旋转/缩放 | 普通报告只有少量 renderer 基础 JS；PDB 坐标 payload 只在使用 `structure_viewer` 时嵌入 |
| `ngl@2.4.0` | 发布前必须随 renderer 源码/镜像 vendored，并记录实际版本和来源 | `structure_viewer runtime="ngl"` 的 WebGL 蛋白结构查看 | 只在 `structure_viewer` 显式声明 `runtime = "ngl"` 时内嵌；普通报告不携带 NGL |
| `igv.js` | 发布前必须随 renderer 源码/镜像 vendored，并记录实际版本和来源 | `genome_browser runtime="igv"` 的基因组轨道浏览 | 只在 `genome_browser` 显式声明 `runtime = "igv"` 时内嵌；轨道数据默认外部化 |

### ECharts / `interactive_plot`

ECharts 是当前 `interactive_plot` 的固定交互图 runtime。它用于把已经计算完成的结果表做成可缩放、可悬停、
可按阈值筛选的浏览器视图，例如 RNA-seq 的火山图、MA 图和 ORA dotplot。

当前固定版本为 `6.1.0`，来源为官方 npm 包 `echarts@6.1.0` 的
`dist/echarts.min.js`，许可证为 Apache-2.0，SHA-256 为
`b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0`。
源码记录保存在 `assets/SOURCE.json`，bundle 内保留上游许可证声明。

实现边界：

- `interactive_plot` 从本地 TSV/CSV 读取必要列，并只把需要展示的字段编译成 JSON payload；
- ECharts runtime 只在报告声明 `interactive_plot` 时写入最终 HTML；
- 控件只改变前端分类、颜色、显示数量和摘要数，不重新运行统计模型；
- 火山图/MA 图默认保持全数据坐标范围，避免调整阈值时坐标轴跳变；
- 所有源表和 runtime pack 都记录进报告资产索引；
- 真实回归必须至少覆盖差异表达和富集两类图，视觉检查包括坐标轴标签不溢出、hover 可读、
  控件可用和普通报告不携带 ECharts runtime。

TOML 示例：

```toml
[[sections.components]]
type = "interactive_plot"
id = "de-volcano"
kind = "volcano"
source = "03_results/tables/de.results.tsv"
default_padj = 0.05
default_log2fc = 1.0
controls_open = false
```

### Plotly / legacy fastp

Plotly 1.2.0 只保留用于兼容历史 fastp HTML 报告中的远程 loader。renderer 会把已知远程
`plotly-1.2.0.min.js` URL 替换成内嵌本地 runtime，让 fastp 原生页面在 standalone
主报告中离线打开。新的 `interactive_plot` 不再使用 Plotly。

当前 bundle 来源为 Plotly 官方 CDN 的 `plotly-1.2.0.min.js`，许可证为 MIT，
SHA-256 为 `60169d9df25530f1d5e29c663ceb18ea7492862acb308800fc5ab0f0bf31a41e`。
来源记录和完整许可证分别保存在 `assets/SOURCE.json` 与
`assets/LICENSE.plotly.txt`。

### NGL / `structure_viewer`

NGL 是当前优先支持的专业 3D 结构 runtime。它适合 Chengdu Yuanda 这类结构比较报告：
报告同时保留静态 PyMOL/ChimeraX 图片和一个可旋转、可缩放的 PDB overlay 查看器。

实现边界：

- renderer 源码和发布镜像携带已 vendored 的 `dist/ngl.js` standalone browser bundle、
  `VERSION`、`SOURCE.json` 和 license；Docker build 只做离线存在性与版本检查，不联网下载；
- 更新 NGL runtime 是独立 maintainer vendoring 步骤：获取官方 npm tarball、抽取
  `dist/ngl.js`、校验内容、记录来源/checksum/license 后再进入源码树；
- 普通报告使用不需要提供 JavaScript 路径，接口仍是 TOML/JSON spec 加结果根目录；
  发布镜像和源码树开发测试都应使用已 vendored runtime pack；
- 不要把 `dist/ngl.umd.js` 当成生产 runtime；该包外置 `three/chroma/signals/sprintf`
  等依赖，在 standalone HTML 中会导致 `window.NGL.Stage` 不可用；
- 源码树中的 NGL test shim 只用于 smoke/offline 接口测试。`tests/test-real-run.sh`
  不允许使用 shim；如果没有真实 `ngl.js`，含 `runtime = "ngl"` 的真实结构
  fixture 必须硬失败并提示使用发布镜像或准备源码树 runtime pack。shim 报告不能作为真实报告回归、
  最终视觉验收或 publish-ready 证据；
- `runtime = "ngl"` 会把 PDB 文本、解析后的 `atoms`、结构 payload JSON 和 NGL runtime
  内嵌进单个 HTML；`pdbText` 用于真实 NGL，`atoms` 用于内置降级 viewer；
- NGL stage 初始化后需要主动 resize/render/autoView，避免首次布局尺寸未稳定时出现空白 canvas；
- 如果浏览器没有 WebGL、NGL 初始化失败或 NGL 依赖不完整，
  报告必须自动切换到同一卡片内置 canvas trace viewer，仍可查看多模型 trace、
  site/motif marker、模型开关和位点显示控制；静态结构图和源 PDB 链接继续保留；
  静态结构图使用与普通 plot 相同的大图 lightbox，默认完整适配当前窗口；
- NGL 只负责查看已有结构，不负责预测、叠合、docking、RMSD 或其它科学计算。

TOML 示例：

```toml
[[sections.components]]
type = "structure_viewer"
id = "ks-overlay"
title.zh = "KS 结构叠合"
title.en = "KS structural overlay"
static_image = "03_results/structure_figures/ks_overlay.png"
runtime = "ngl"
representation = "cartoon"  # cartoon | backbone | licorice | ball+stick | spacefill | surface
show_surface = false
spin = false
height = 460

[[sections.components.models]]
id = "target"
pdb = "03_results/pdb/target.pdb"
label.zh = "目标结构"
label.en = "Target"
color = "#2563eb"
```

### IGV.js / `genome_browser`

IGV.js 是当前优先支持的基因组轨道浏览 runtime。它适合把 flow 已经产生或用户已经发布的
BED/GFF/BAM/VCF/BigWig 等轨道放在同一个 locus 下审阅。和表格、图片、结构 payload 不同，
基因组浏览器常常依赖大型索引文件和随机访问，因此当前稳定策略是：

- `viewer_mode = "embedded"` 时，最终 HTML 内嵌 IGV runtime 和固定 JSON 配置；
- `viewer_mode = "linked"` 时，最终 HTML 只展示可审查配置、reference/track 链接和 JSON，
  不要求 IGV runtime；
- 如需同时提供两种审阅方式，使用同一个组件的 `viewer_modes = ["embedded", "linked"]`
  生成内嵌/链接切换按钮；不要把同一组轨道拆成两个并列 `genome_browser` 卡片；
- 只有一个可用模式时不显示切换按钮，只在卡片中说明当前模式和可复用配置；
- 组件的初始 HTML 必须先呈现可审计配置面板，JS 和 IGV runtime 可用时再升级为交互式浏览器，
  因此不能出现长期停留在“正在加载”的空白面板；
- `embedded` 模式中的 IGV 是原生 IGV.js viewer，报告外层容器必须让齿轮菜单、
  track menu、搜索建议等原生浮层完整显示或在 IGV viewport 内可达；不能用
  `overflow:hidden` 裁切菜单，也不能用无限制 `overflow:visible` 让 viewer 覆盖相邻
  报告卡片；
- 小型本地 FASTA/FAI/BED/GFF/bedGraph 可以通过 `embed_reference = true`、
  `embed_tracks = true` 或 track 级 `embed = true` 内嵌成 data URI，并记录到
  `report_files.tsv`；
- 大型 FASTA、BAM、VCF、BigWig、CRAM 及其索引默认不内嵌；
- 轨道通过 HTTP(S)、本地静态服务或用户明确配置的 URL 提供；
- 报告仍应保留关键静态图、统计表或文件索引，IGV viewer 作为可浏览证据补充；
- renderer 源码和发布镜像携带已 vendored 的 `dist/igv.min.js` 或 `dist/igv.js`，
  并记录 VERSION、SOURCE.json 和 LICENSE；Docker build 只做离线存在性与版本检查；
- 更新 IGV runtime 是独立 maintainer vendoring 步骤：获取官方 npm tarball、抽取
  standalone browser bundle、校验内容、记录来源/checksum/license 后再进入源码树；
- 普通报告使用不需要提供 IGV JavaScript 路径；发布镜像和源码树 real-run 都使用固定
  runtime pack。
- 源码树中的 IGV test shim 只用于 smoke/interface 测试，不能作为真实 genome browser
  视觉验收结果，也不能进入 `tests/test-real-run.sh`；真实回归需要发布镜像内 runtime
  或源码树 vendored runtime pack。renderer 会识别 test shim 并展示
  fallback 配置面板，避免把“非空 shim 占位图”误判为真实 IGV 成功加载；
- embedded 模式下如果 IGV runtime 不可用或初始化失败，报告必须展示 genome/locus/reference、
  track 链接和完整 IGV JSON 配置，不能留空白；
- `genome_browser` 只负责查看已有 tracks，不负责 read mapping、variant calling、
  coverage 计算或 genome indexing。

TOML 示例：

```toml
[[sections.components]]
type = "genome_browser"
id = "igv-locus"
runtime = "igv"
viewer_mode = "embedded"
viewer_modes = ["embedded", "linked"]
data_mode = "external"
genome = "hg38"
locus = "chr1:155,000,000-155,020,000"
height = 520

[[sections.components.tracks]]
name = "RNA-seq coverage"
url = "https://example.org/sample.bw"
type = "wig"
format = "bigwig"
color = "#0f766e"
```

小型内嵌 reference/track 示例：

```toml
[[sections.components]]
type = "genome_browser"
id = "igv-mini-locus"
runtime = "igv"
viewer_mode = "embedded"
viewer_modes = ["embedded", "linked"]
data_mode = "embedded-small-assets"
reference_name = "mini-reference"
reference_fasta = "03_results/genome/mini.fa"
reference_index = "03_results/genome/mini.fa.fai"
embed_reference = true
locus = "chrI:1-5000"

[[sections.components.tracks]]
name = "Gene annotation"
type = "annotation"
format = "bed"
source = "03_results/tracks/genes.bed"
embed = true
```

## 候选 runtime

### 3Dmol.js / Mol* / 其它结构 runtime

蛋白结构和 docking 报告经常需要同时展示静态图和可旋转 3D 结构。该需求适合抽象成
`structure_viewer` 组件，而不是让每个 flow 复制一套私有 viewer HTML。当前稳定方案是
`runtime = "builtin"` 和 `runtime = "ngl"`。如果后续 3Dmol.js、Mol* 或其它 runtime 在多个
flow 中反复需要，可以作为新的 runtime pack 接入，但不能绕过同一组件契约。

建议能力：

- 读取一个或多个本地 PDB 文件；
- 支持单结构查看和多模型叠合查看；
- 支持 cartoon、stick、sphere 等固定 style；
- 支持 residue/site group 高亮；
- 支持与静态 PyMOL/ChimeraX 图片放在同一卡片中；
- PDB 文本可内嵌进 standalone HTML；
- 结构文件过大时可降级为源文件链接和静态图。

进入 stable 前的硬要求：

- 补齐 runtime 的 license 文件和版本来源；
- 将 runtime asset 放入 renderer 自己的 asset 目录；
- 保留并扩展最小 PDB fixture；
- 保持 `structure_viewer` schema、component-doc、lint 和 render 逻辑兼容；
- 检查普通报告不使用该 runtime 时不嵌入对应 JS；
- 检查使用该组件时最终 HTML 可离线旋转、缩放、显示高亮位点。

### Network / pathway viewer

通路、PPI、gene set overlap 或候选基因网络可以考虑 Cytoscape.js 一类 runtime。
该组件应从节点/边 TSV 或 JSON 读取，不接受任意 JS。

### Sequence / MSA viewer runtime

当前 `sequence_alignment` 组件已经能用 renderer 自带 CSS/JS 展示 FASTA/CLUSTAL 比对、
共识行和残基颜色，不需要额外大型 runtime。如果未来需要 Jalview/msa.js 级别的复杂
交互，应先证明多个 flow 都需要，再作为独立 runtime pack 评估 license、体积和离线能力。

## 不做什么

- 不把所有可能用到的 JS 库都默认嵌入每份报告。
- 不把 runtime pack 当成生信分析工具；它只负责查看已有结果。
- 不为单个项目的一次性页面加入大型 runtime。
- 不通过 raw HTML 让 flow 自己绕过 renderer 的组件契约。
