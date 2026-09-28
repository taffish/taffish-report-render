# 固定组件注册表

本文件说明当前 `taffish-report-render` 支持的稳定组件。组件是报告 DSL 的边界：
flow 作者只能用这些固定元素组织报告，不能临场手写 raw HTML 来绕过统一风格。

所有组件共享这些规则：

- 0.4.0 起，所有组件（包括 collection）可用 `toc.visible` 隐藏目录项、
  用 `toc.title` 指定双语短标题；正文、锚点和文件索引不受影响。
  详见 [目录合同](toc.zh.md)，不要用正文标题数字推导目录父子关系。

- `type` 必须是已注册组件名；
- `id` 必须稳定且唯一；
- `title.<lang>` 和 `note.<lang>` 推荐提供中英双语；
- section 与每个固定组件都支持有序 `note_items`；其 kind、字段、语言完整性和纯文本边界
  统一按 [Report Spec 结构](report-spec.zh.md#结构化说明-note_items) 校验；
- 路径字段相对 `--root`；
- 组件只展示已有结果，不运行分析；
- 长路径、长 ID、长表格值必须由组件安全换行或提供完整值访问方式。

`note_items` 是共享字段，不需要每个组件各自发明 `question_en`、`reading_zh`、HTML callout
或私有 CSS。例如：

```toml
[[sections.components.note_items]]
kind = "reading"
label.zh = "如何阅读"
label.en = "How to read"
body.zh = "先核对图例，再与源表逐项对应。"
body.en = "Check the legend first, then map each item to the source table."
```

collection 组件上的 `note_items` 会按原顺序复制到每个展开后的固定组件，并进入 normalized
JSON；最终布局与换行仍由 renderer 统一控制。

## dashboard_cards

用途：生成首页或章节总览指标卡。

典型输入是 TSV：

```text
metric    value    note_en    note_zh
samples   24       biological samples    生物学样本
mode      reference reference-guided      有参路线
```

TOML：

```toml
[[sections.components]]
type = "dashboard_cards"
id = "overview-key-metrics"
source = "04_reports/key_metrics.tsv"
```

适合展示样本数、分析模式、差异基因数量、报告嵌入数量等少量关键指标。

## status_grid

用途：展示模块、步骤或子流程状态。

典型输入：

```text
module    status    note_en    note_zh
fastp     OK        finished   已完成
multiqc   WARN      partial    部分指标需复核
```

TOML：

```toml
[[sections.components]]
type = "status_grid"
id = "module-status"
source = "04_reports/module_status.tsv"
```

状态词应保持短小，例如 `OK`、`WARN`、`FAIL`、`SKIP`。组件必须保证 `WARN` 等状态词不会
被拆成逐字母换行。

## quality_gate_table

用途：展示质量门控、阈值和判定。

典型输入：

```text
criterion_en    criterion_zh    observed    threshold    status    note_en    note_zh
Q30 rate        Q30比例         91.2%       >=85%        OK        Passed     通过
```

TOML：

```toml
[[sections.components]]
type = "quality_gate_table"
id = "quality-gates"
source = "04_reports/quality_gates.tsv"
```

语言成对列会折叠成当前语言列；英文模式不应显示中文-only 解释列，中文模式不应显示英文-only
解释列。

## table_preview

用途：展示 TSV/CSV 表格。默认先显示紧凑预览，必要时在同一张表中原地展开更多行。

TOML：

```toml
[[sections.components]]
type = "table_preview"
id = "de-summary"
source = "03_results/tables/de.summary.tsv"
preview_rows = 8
embed_full = true
default_state = "preview"   # preview | collapsed | full
max_embed_rows = 5000
max_embed_bytes = 5000000
title.zh = "差异表达摘要"
title.en = "DE summary"
```

字段：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `source` | 必需 | TSV/CSV 文件路径。 |
| `preview_rows` | `10` | 默认预览行数。 |
| `embed_full` | `false` 或组件默认 | 是否尝试嵌入完整表格。 |
| `default_state` | `preview` | 初始状态：预览、收起或完整打开。 |
| `max_embed_rows` | renderer 默认 | 完整嵌入的最大行数。 |
| `max_embed_bytes` | renderer 默认 | 完整嵌入的最大字节数。 |

组件行为：

- 同一个表格容器支持上下滚动和横向滚动；
- 宽表必须能到达最右列；
- 有搜索、表头排序、单元格展开和完整值复制；
- 展开完整表格时是在原表中显示隐藏行，不生成第二张 full table 或 modal；
- 超过体积边界时显示边界说明和源文件链接，不强行嵌入；
- 超长单元格可视觉紧凑，但完整值必须可访问。

适合展示差异表达结果、富集结果、样本摘要、工具版本、参数表等。

## code_file

用途：展示短文本产物，并提供复制按钮。

TOML：

```toml
[[sections.components]]
type = "code_file"
id = "tree-newick"
source = "03_results/tree/tree.nwk"
language = "newick"
copy = true
max_embed_bytes = 200000
title.zh = "Newick 树文件"
title.en = "Newick tree file"
note.zh = "可复制到 iTOL、FigTree 或其他绘图工具。"
note.en = "Can be copied into iTOL, FigTree, or other plotting tools."
```

适合：

- Newick 树；
- 短配置；
- 命令片段；
- 小 JSON；
- 短日志摘录。

不适合把大型日志或大型矩阵塞进报告；这类文件应作为源文件保留并由表格/文件索引引用。

## tree_viewer

用途：把已有 Newick 树以内联 SVG 形式展示在报告中，同时保留可复制的原始树文件。

TOML：

```toml
[[sections.components]]
type = "tree_viewer"
id = "phylogeny-tree"
source = "03_results/tree/tree.nwk"
layout = "rectangular"
height = 460
show_labels = true
show_branch_lengths = true
copy = true
title.zh = "系统发育树"
title.en = "Phylogenetic tree"
```

字段：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `source` | 必需 | Newick 文件路径。 |
| `layout` | `rectangular` | 当前稳定支持矩形树图。 |
| `height` | 自动 | 画布高度。 |
| `show_labels` | `true` | 是否显示 tip label。 |
| `show_branch_lengths` | `true` | 是否使用分支长度；缺少长度时自动退化为拓扑间距。 |
| `copy` | `true` | 是否提供复制 Newick 按钮。 |
| `max_tips` | `500` | 防止超大树挤爆报告的保守边界。 |
| `branch_color` | `#0b6f67` | 树枝主色，十六进制颜色。 |
| `branch_width` | `2.2` | 树枝宽度，单位 px。 |
| `label_color` | 模板深色 | tip label 颜色。 |
| `label_size` | `12` | tip label 字号，单位 px。 |
| `scale_color` | 模板 muted 色 | scale axis 颜色。 |
| `background` | `transparent` | SVG 背景色，推荐透明或浅色十六进制。 |

组件行为：

- Newick 文本会进入单 HTML，用户可以复制到 iTOL、FigTree、MEGA 等专业工具；
- 树图用于报告内快速审阅，不替代专业树编辑器；
- 超过 `max_tips` 或 Newick 解析失败时应清楚报错，而不是生成空白树；
- 如果 flow 同时有静态树图，可用 `plot_card` 展示出版图，用 `tree_viewer` 展示可复制拓扑。

## sequence_alignment

用途：展示已有多序列比对文件，并提供 residue-level 的紧凑浏览、共识行和复制入口。

TOML：

```toml
[[sections.components]]
type = "sequence_alignment"
id = "trimmed-alignment"
source = "03_results/alignment/trimmed.fa"
format = "fasta"        # auto | fasta | clustal
alphabet = "protein"   # auto | dna | rna | protein
show_consensus = true
copy = true
max_sequences = 80
max_columns = 300
title.zh = "修剪后的多序列比对"
title.en = "Trimmed multiple sequence alignment"
```

字段：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `source` | 必需 | FASTA 或 CLUSTAL 比对文件路径。 |
| `format` | `auto` | 自动识别或显式声明 `fasta` / `clustal`。 |
| `alphabet` | `auto` | 自动识别或显式声明 DNA/RNA/protein。 |
| `show_consensus` | `true` | 是否显示简单共识行。 |
| `copy` | `true` | 是否提供复制原始比对按钮。 |
| `max_sequences` | `80` | 默认最多内联展示的序列数。 |
| `max_columns` | `300` | 默认最多内联展示的列数。 |
| `color_scheme` | `taffish` | `taffish`、`classic` 或 `mono`。 |
| `font_size` | `13` | 比对区字号，单位 px。 |
| `label_width` | `240` | 序列名列宽，单位 px。 |
| `residue_a` / `residue_c` / `residue_g` / `residue_t` / `residue_u` / `residue_n` | 固定色板 | DNA/RNA 残基背景色。 |
| `residue_hydrophobic` / `residue_positive` / `residue_negative` / `residue_polar` / `residue_special` / `gap_color` | 固定色板 | 蛋白和 gap 色板。 |

组件行为：

- 比对本身会内嵌进 HTML，报告可离线交付；
- 核苷酸和蛋白残基使用保守固定色板，帮助快速识别 gap、保守位点和差异区域；
- 超过边界的序列或列会明确提示截断，源文件仍可打开/复制；
- 它只展示已有 MSA，不负责 MAFFT/MUSCLE/Clustal Omega 等比对计算，也不做 trimming。

## genome_browser

用途：为已有基因组坐标和 track 提供 IGV.js 浏览入口。默认推荐大数据外部化：
报告内嵌 IGV browser runtime 和轨道配置，但大型 FASTA/BAM/VCF/BigWig 等数据仍由用户通过
HTTP(S) 或本地服务提供。小型 FASTA/FAI/BED/GFF/bedGraph fixture 或审稿用片段可以通过
`embed_reference`、`embed_tracks` 或 track 级 `embed` 内嵌进单 HTML。

TOML：

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
title.zh = "IGV 基因组浏览器"
title.en = "IGV genome browser"

[[sections.components.tracks]]
name = "RNA-seq coverage"
url = "https://example.org/sample.bw"
type = "wig"
format = "bigwig"
color = "#0f766e"
```

字段：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `runtime` | `igv` | 当前稳定 runtime。 |
| `viewer_mode` | `embedded` | `embedded` 尝试加载内嵌 IGV runtime；`linked` 只展示可复用配置、轨道链接和审计信息，不要求 runtime。 |
| `viewer_modes` | `[viewer_mode]` | 可选模式列表。设置为 `["embedded", "linked"]` 时，同一个组件内提供切换按钮；如果只有一个模式，不显示切换按钮，只说明当前模式。 |
| `data_mode` | `external` | 推荐外部数据模式；大文件不强行内嵌。 |
| `genome` | 可选 | IGV 已知 genome ID，如 `hg38`。 |
| `locus` | 必需 | 初始浏览坐标。 |
| `reference_fasta` / `reference_index` | 可选 | 自定义参考时的 FASTA 和 FAI URL/路径。 |
| `embed_reference` | `false` | 当 `reference_fasta/reference_index` 是 `--root` 下小文件时，将其记录并内嵌为 data URI。 |
| `embed_tracks` | `false` | 对所有本地 `tracks.source` 小文件启用 data URI 内嵌；track 级 `embed` 可覆盖。 |
| `tracks` | 可选 | 轨道数组，支持 `url/source`、`format`、`type`、`index_url` 等固定字段。 |
| `height` | `520` | 浏览器高度。 |

组件行为：

- 最终 HTML 内嵌 IGV runtime 和 JSON 配置，但不会默认内嵌大 FASTA、BAM、VCF、BigWig；
- `embedded` 模式加载的是真实 IGV.js 浏览器，因此搜索、缩放、齿轮菜单、轨道菜单等
  IGV 原生交互应保持可用；renderer 外层 CSS 不得裁切这些原生弹层，也不能让整个
  viewer 越界覆盖相邻报告卡片，必要时应在 IGV 自己的 viewport 内滚动查看；
- TOML 不是 IGV.js 全量 API 的一比一镜像。当前稳定桥接 genome/locus/reference、
  track URL/type/format/index、`height`、`color`、`display_mode` 和
  `visibility_window` 等常用字段；更复杂的 IGV option 应在真实需求出现时进入
  renderer 白名单，而不是让用户传 JavaScript；
- 小型本地 reference/track 可通过 `embed_reference = true` 和 `embed_tracks = true`
  内嵌，renderer 会把这些文件写入资产索引并把 IGV 配置改成 data URI；
- 如果需要同时提供内嵌审阅和链接审阅，必须在同一个 `genome_browser` 组件中设置
  `viewer_modes = ["embedded", "linked"]`，由报告内按钮切换；不要把 embedded 和 linked
  拆成两张重复卡片；
- 如果只声明一个模式，报告不显示切换按钮，只显示当前模式和可审计配置；
- 即使浏览器 JS 尚未执行，组件初始 HTML 也必须显示 genome/locus/reference/tracks 和
  JSON 配置审阅面板，不能只显示“正在加载”空白框；
- `viewer_mode = "embedded"` 会尝试启动 IGV；如果真实 runtime 不存在或浏览器阻止执行，
  renderer 会在同一卡片中显示 genome/locus/reference/tracks 和完整
  JSON 配置的 fallback 面板，不能留空白；
- `viewer_mode = "linked"` 不要求 runtime，适合只想在报告中交付可审计轨道配置和外部链接的场景；
- 外部 URL 由用户/服务器负责可访问性、CORS 和权限；
- 报告应同时保留关键结果表或静态图，IGV 作为浏览补充，不作为唯一证据；
- 源码 smoke 可以使用 IGV test shim 检查接口，但真实 `tests/test-real-run.sh` 和视觉验收
  需要发布镜像内 runtime 或源码树已 vendored runtime pack。
  JavaScript 路径不是普通报告参数。IGV real-run fixture 必须
  使用真实或由真实数据派生的 reference/track，不能使用 `example.org` 伪 URL。

## workflow_diagram

用途：根据 TSV 生成流程节点图，展示步骤顺序、状态和输出。

典型输入：

```text
step    status    outdir    note_en    note_zh
index   OK        ref-out   reference built    参考构建完成
expr    OK        expr-out  expression quantified 表达定量完成
```

TOML：

```toml
[[sections.components]]
type = "workflow_diagram"
id = "workflow-route"
source = "03_results/tables/standard.subflows.subflows.tsv"
```

它适合展示标准路线，不适合复杂条件分支或交互式 DAG。若流程非常复杂，应先在 flow 侧输出
清晰的 summary TSV。

流程表可使用 `step_en` / `step_zh`、`note_en` / `note_zh` 和可选的
`status_en` / `status_zh` 成对字段，渲染器会按当前报告语言显示；旧的 `step`、`flow`、
`status`、`outdir` 字段仍然兼容。

## plot_card

用途：展示主图片。图片会转成 data URI 内嵌到主 HTML。

TOML：

```toml
[[sections.components]]
type = "plot_card"
id = "de-pca"
image = "03_results/plots/de.pca_plot.png"
zoom = true
default_fit = "contain"  # contain | original
layout = "wide"          # grid | wide | media
note_position = "top"    # bottom | top
title.zh = "PCA 图"
title.en = "PCA plot"
note.zh = "展示样本整体表达结构。"
note.en = "Shows global sample expression structure."
```

组件行为：

- 默认支持大图 lightbox；
- 大图打开时先完整适配当前窗口；
- 用户可放大、缩小、回到适配窗口；
- 图片仍然是内嵌 payload，不依赖外部文件；
- PNG、JPEG、WebP 和 SVG 使用 renderer 内部的确定性 MIME 映射，不依赖宿主机或
  容器的 `/etc/mime.types`；WebP 必须稳定生成 `data:image/webp;base64,`；
- 连续 `plot_card` 会自动形成图片网格；
- `layout = "wide"` 可让主图独占一行，`note_position = "top"` 可把解释放到图片上方；
- 不同类型组件不会混进 plot grid。

### media 横向图文布局

`layout = "media"` 用于文献图、背景图、概念模型、原理图和输入数据示意图。每张 media
卡片独占一行，图片和对应解释在桌面端并排，在窄屏自动改成“图片在前、文字在后”的单栏。

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
title.zh = "病原真菌侵染与效应子作用位置"
title.en = "Fungal Infection and Effector Action Sites"
note.zh = "图片与解释在宽屏中保持相邻。"
note.en = "The figure and its interpretation remain adjacent on wide screens."

[[sections.components.note_items]]
kind = "reading"
label.zh = "如何阅读"
label.en = "How to read"
body.zh = "先读标题，再对照图片与结构化说明。"
body.en = "Read the title first, then compare the figure and structured notes."
```

media 专用字段：

- `image_position = "left" | "right"`：桌面端图片位于左侧或右侧，默认 `left`；
- `media_image_ratio = 0.42`：图片栏占两栏可用空间的比例，默认 `0.42`，允许范围
  `0.25–0.70`；renderer 会转换为安全 CSS Grid 比例，不接受任意 CSS 字符串；
- `media_vertical_align = "start" | "center"`：两栏顶部或居中对齐，默认 `start`；
- `media_gap = "compact" | "normal" | "relaxed"`：使用 renderer 固定间距等级，
  默认 `normal`；
- `media_note_layout = "auto" | "stack" | "compact"`：说明区布局，默认 `auto`；
  有效 `note_items` 为 0–3 条时使用 `stack`，4 条及以上自动使用 `compact`；显式请求
  `compact` 但没有有效条目时安全退化为 `stack`；
- `title`、`note`、`caption`、`zoom` 和 `default_fit` 继续复用既有字段。

响应式契约：

- `compact` 把居中的标题/操作区放在整卡顶部，下一行图片与说明并排；说明条目外层可两列，
  但每个 label/body 始终保持单个内部阅读列，`boundary`、`limitation`、`next` 跨满说明区；
- 断点按组件宽度而非只按 viewport 判断：`900px` 以上保持图文双栏，`900px` 及以下
  始终先图后文；`620px` 及以下 compact 条目改为单列；不支持 container query 的浏览器
  使用同边界 viewport fallback；
- compact 卡片在 `900px` 折叠后，图片按自然宽度居中并限制在组件内，屏幕最大高度为
  `min(720px, 85vh)`；纵图不会被放大到占满正文列宽；
- 窄屏忽略桌面比例，不产生横向滚动；图片保持原始比例并使用 `object-fit: contain`；
- compact 的图片栏和说明栏在同一行自然等高，但不使用固定卡片高度、裁切、绝对定位或
  `overflow: hidden`；`media_vertical_align` 继续控制 `stack`，compact 由等高契约接管；
- compact 两列结构化说明卡只在各自所在行内等高；打印时图片保持自然宽度、居中，并使用
  确定的 `180mm` 上限，不依赖 viewport 高度；
- 长中英文标题、长链接和连续英文标识符必须在文字栏内换行；
- 未识别枚举、字符串/NaN/非有限比例、越界比例或在非 media 布局中声明 media 专用字段，
  都会在验证/lint 阶段失败。

坐标轴、标签和数据点密集的正式科学结果图仍建议使用 `layout = "wide"` 和
`note_position = "top"`。renderer 不会自动把 `wide` 转成 `media`，历史 `grid`、`wide`
和未声明 layout 的 TOML 行为保持不变。

建议 flow 同时保留 PNG 和 PDF 原始文件；报告中通常用 PNG/SVG 作为主图，PDF 作为源文件或
文件索引的一部分。

## interactive_plot

用途：把已有结果表转换成紧凑 JSON payload，并在报告浏览器端生成可筛选、可悬停查看的
交互图。它适合 RNA-seq 差异表达和富集结果这类“科学结果已经由上游工具计算完成，
报告只需要更友好查看”的场景。

当前稳定图形：

- `kind = "volcano"`：从差异表达结果表读取 gene、log2FC、padj/pvalue，生成火山图；
- `kind = "ma"`：从差异表达结果表读取 baseMean、log2FC、padj/pvalue，生成 MA 图；
- `kind = "pca"`：从已计算 PCA 坐标表读取 sample、PC1、PC2、group/condition，生成样本 PCA
  scatter 图；
- `kind = "ora_dotplot"`：从 ORA/富集结果读取 Description、GeneRatio、Count、padj/pvalue，
  生成 dotplot。

TOML：

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
controls_open = false
```

可选字段：

- `gene`、`log2fc`、`padj`、`pvalue`、`base_mean` 用于覆盖差异表达表列名；
- `description`、`count`、`gene_ratio` 用于覆盖 ORA 表列名；
- `sample`、`group`、`pc1`、`pc2`、`x_label`、`y_label` 用于覆盖 PCA 坐标表列名和坐标轴名；
- `default_padj`、`default_log2fc`、`top_n`、`max_points`、`height` 控制默认视图；
- `point_size`、`opacity`、`color_up`、`color_down`、`color_ns`、`color_low`、
  `color_high` 控制 ECharts 默认视觉样式；
- `fixed_range` 默认保持全数据坐标范围，避免阈值调整时坐标轴跳变；
- `show_threshold_lines` 控制火山图/MA 图阈值参考线；
- `label_max_chars` 控制 ORA dotplot 坐标轴短标签长度；
- `controls_open = true` 可让控制面板默认展开；默认应保持收起。

组件边界：

- 前端只筛选、分组、着色和重绘已经内嵌的结果行；
- 不重新运行 DESeq2、edgeR、tximport、ORA、GSEA、PCA、聚类或其它统计模型；
- PCA 图必须由上游 flow 输出已计算坐标表；renderer 不从表达矩阵临时计算 PCA；
- 阈值变化只用于报告查看，不会修改源表、payload、manifest 或 provenance；
- 长 term 名称会在坐标轴上缩短，完整名称保留在 hover 文本中；
- 源 TSV/CSV 表会记录进 `report_files.tsv`，最终 HTML 不需要运行时再读取源文件；
- ECharts runtime 只在使用该组件时内嵌；普通报告不因此变大。

## structure_viewer

用途：展示 PDB 结构证据，把静态结构图、一个或多个 PDB 文件、交互式结构 viewer 和
源文件链接放在同一张卡片中。

当前稳定能力：

- 支持一个或多个本地 PDB 文件；
- 支持每个 model 在 TOML 中声明统一颜色；`runtime = "ngl"` 会用 NGL uniform color
  representation 应用这些颜色，不依赖 PDB 文件自带颜色；
- 支持 `atom_filter = "ca" | "backbone" | "all"`；
- `runtime = "builtin"` 使用内置轻量 canvas trace viewer，可拖拽旋转、按钮/滚轮缩放、重置视角；
- `runtime = "ngl"` 使用镜像内固定版本的 NGL WebGL runtime，可展示 cartoon、backbone、
  licorice、ball+stick、spacefill 或 surface 视图；
- 支持可选 `static_image`，适合放 PyMOL、ChimeraX 或 docking pose 静态图；
- PDB 文件会随结构 payload JSON 内嵌进单 HTML；`runtime = "ngl"` 时每个可加载模型必须
  同时以 `pdbText` 和解析后的 `atoms` 形式进入 payload。真实 NGL 可用时使用 `pdbText`
  交给 WebGL viewer；NGL 不可用或加载失败时，renderer 使用同一 payload
  自动降级到内置 canvas trace viewer；
- 内置 canvas fallback 只能表示轻量 trace/marker 审阅，不等同于 NGL/PyMOL 的真实
  cartoon/surface 表示；fallback 激活时 UI 必须明确显示为 fallback trace，并禁用 NGL
  representation 下拉，不能继续显示 `cartoon` 造成误导；
- PDB 文件和 runtime pack 记录进 `report_files.tsv`，同时保留源文件链接；
- `static_image` 使用与 `plot_card` 相同的大图 lightbox，默认适配当前窗口并可继续放大；
- 结构卡片与表格、图片网格、子报告网格之间的间距由 renderer 统一处理，不需要 TOML
  插入空白章节或私有样式；
- 支持 `site_groups` 或 `site_table` 声明 motif/活性位点/结构残基分组；
  `runtime = "ngl"` 会把这些位点作为额外 `spacefill` 球标记叠加到指定模型上；
- `runtime = "ngl"` 会自动生成内嵌交互控制面板；用户可以在单 HTML 内开关模型、
  开关不同 site group，并调整位点球大小和透明度，这些操作只改变当前浏览器视图；
- 交互控制面板默认收起；如需某个结构组件打开报告时默认展开，可在 TOML 中设置
  `controls_open = true`；
- renderer 会固定结构组件顺序：model/score/source 摘要在上方，3D viewer 与静态图在
  中间，交互控制面板紧贴 3D viewer 下方；TOML 不需要、也不应该通过空白组件或私有
  样式手动调整这个顺序；
- 未使用 `structure_viewer` 的普通报告不会嵌入 PDB payload 或重型 3D runtime。

TOML：

```toml
[[sections.components]]
type = "structure_viewer"
id = "ks-overlay"
static_image = "03_results/structure_figures/ks_overlay.png"
runtime = "builtin"
representation = "cartoon"   # runtime="ngl" 时使用
show_surface = false
spin = false
controls_open = false
atom_filter = "ca"
height = 420
max_atoms = 2500
site_table = "03_results/tables/motif_sites_on_target.tsv"
site_structure_id = "target-domain-1"
site_model = "target"
site_chain = "A"
site_residue_column = "structure_residue"
site_group_column = "target_state"
site_label_column = "target_residue_label"
site_max_sites = 80
title.zh = "KS 结构叠合"
title.en = "KS structural overlay"
note.zh = "展示目标结构与参考结构的局部空间关系。"
note.en = "Shows local spatial relationships between target and reference structures."

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

[[sections.components.site_groups]]
id = "target_matches_reference"
color = "#8b5cf6"
label.zh = "target 匹配 reference motif"
label.en = "Target matches reference motif"
```

常用字段：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `site_table` | 可选 | TSV 位点表，用于从真实结果表生成 marker。 |
| `site_structure_id` | 可选 | 过滤 `site_table` 中某个结构/域的行。 |
| `site_structure_column` | `structure_id` | `site_table` 中用于匹配结构 ID 的列。 |
| `site_model` | 第一个 model | 位点 marker 应叠加到哪个 model。 |
| `site_chain` | 空 | 位点 marker 的 PDB chain；为空时不限制 chain。 |
| `site_residue_column` | `structure_residue` | `site_table` 中结构残基编号列。 |
| `site_group_column` | `target_state` | `site_table` 中位点分组列，不同分组可用不同颜色。 |
| `site_label_column` | `target_residue_label` | `site_table` 中位点标签列。 |
| `site_max_sites` | `80` | 单个组件最多嵌入的位点数，防止大表过重。 |
| `controls_open` | `false` | NGL 交互控制面板是否默认展开；默认收起，避免长报告页面一开始过重。 |
| `site_groups[].id` | 可选 | 分组 ID；可作为 `site_table` 中 group 值的样式定义。 |
| `site_groups[].residues` | 可选 | 不使用 `site_table` 时直接声明残基列表。 |
| `site_groups[].selection` | 可选 | 高级 NGL selection；优先级高于 `residues`。 |
| `site_groups[].color` | 自动 | marker 颜色。 |
| `site_groups[].model` | `site_model` | marker 叠加到哪个 model。 |
| `site_groups[].chain` | `site_chain` | marker chain。 |

边界：

- 这是报告查看组件，不负责结构预测、比对、docking 或 RMSD 计算；
- 内置 viewer 是轻量审阅工具，不替代 PyMOL、ChimeraX、UCSF Chimera 或专业结构分析软件；
- NGL runtime 是报告查看 runtime，不改变输入 PDB、不做结构叠合、不计算结构指标；真实
  `tests/test-real-run.sh` 与视觉验收必须使用真实 NGL bundle，test shim 只能用于显式
  smoke/interface 测试；
- 即使用 test shim 做源码树 smoke/interface 测试，结构组件也不能空白；必须能看到
  内置降级 viewer、多模型 trace、site/motif marker 和静态图大图入口；
- 若浏览器中看到的是内置降级 viewer，它应标注为 trace/fallback，而不是 `cartoon`；
  真实 cartoon、surface、licorice 等表示只属于真实 NGL runtime；
- motif/活性位点等 marker 必须来自 TOML 的 `site_groups` 或明确的 `site_table`，renderer
  不会从 PDB 或静态图里自动推断；
- 交互控制面板是 viewer 状态控制，不是数据编辑器；它不修改 PDB、TSV、payload 或报告
  provenance，也不替代上游结构分析；
- 3Dmol.js、Mol* 等其它第三方 runtime 如果后续接入，也必须先补齐来源、版本、license、
  checksum、体积和测试，并保持“只在组件需要时内嵌”的规则。

## native_subreport

用途：嵌入上游程序生成的本地 HTML/QC 子报告。

TOML：

```toml
[[sections.components]]
type = "native_subreport"
id = "fastp"
kind = "fastp"
path = "03_results/html/P1.fastp.html"
embed_policy = "auto"       # auto | always | never
embed_linked_pages = false
title.zh = "fastp 报告"
title.en = "fastp report"
```

字段：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `path` | 必需 | 主 HTML 文件。 |
| `kind` | `html` | 子报告类型，例如 `multiqc`、`fastqc`、`fastp`、`qualimap`。 |
| `embed_policy` | `auto` | 嵌入策略。 |
| `embed_linked_pages` | `false` | 是否递归嵌入主页面链接到的本地 HTML。 |
| `linked_page_limit` | renderer 默认 | 自动收集的本地子页面数量上限。 |
| `pages` | 空 | 显式额外本地 HTML 页面列表。 |

`embed_policy`：

- `auto`：尽量内联本地 CSS、JS、图片、CSS `url(...)`、`srcset` 和 `poster`；
- `always`：要求嵌入完整，无法解析本地资源时失败；
- `never`：只保留链接和索引记录，不打包 payload。

重要边界：

- 子报告应尽量保留原程序生成的 HTML，不要用手写 proxy page 替代；
- 子报告在独立本地页面上下文中打开，避免 MultiQC/Plotly 等重型 JS 在主报告上下文提前执行；
- 普通左键点击“打开内嵌报告”时，renderer 应先同步打开一个轻量本地 loading 页，再把已内嵌
  payload 写入该页面，避免大体积主报告在新标签页中重新加载几秒后才显示子报告；
- same-file hash route 仍作为中键打开、复制链接、无 JS 或浏览器阻止弹窗时的回退路径；
- 对 legacy fastp 远程 Plotly loader，renderer 会替换为本地 runtime；
- 嵌入成功或 warning 状态下，同一张子报告卡片应同时提供“打开内嵌报告”和“打开源 HTML”
  两个紧凑按钮；不要把同一个子报告拆成两个卡片；
- 源 HTML 链接必须按最终 HTML 所在目录计算相对路径，例如从 `04_reports/report.html`
  指向 `../03_results/html/report.html`；
- 任意服务器型或网络型 web app 不保证无损嵌入；
- 是否成功嵌入会记录在 `embedded_html_reports.tsv`。

## plot_collection

用途：从 TSV 图片索引批量生成多个 `plot_card`。

TOML：

```toml
[[sections.components]]
type = "plot_collection"
id = "de-plots"
source = "04_reports/plot_files.tsv"
zoom = true
default_fit = "contain"
```

TSV 常用列：

```text
id    image    title_zh    title_en    note_zh    note_en    enabled
pca   03_results/plots/de.pca_plot.png    PCA 图    PCA plot    样本整体结构。    Global sample structure.    true
```

路径列按优先级读取 `image`、`plot`、`path`、`source`、`file`。collection block 上的
`zoom`、`default_fit`、`caption` 等字段会作为每一行的默认值；行内同名字段优先。

## table_collection

用途：从 TSV 表格索引批量生成多个 `table_preview`。

TOML：

```toml
[[sections.components]]
type = "table_collection"
id = "result-tables"
source = "04_reports/table_files.tsv"
preview_rows = 8
embed_full = true
default_state = "preview"
```

TSV 常用列：

```text
id    source    title_zh    title_en    preview_rows    enabled
de_summary    03_results/tables/de.summary.tsv    差异表达摘要    DE summary    8    true
```

路径列按优先级读取 `source`、`table`、`path`、`file`。collection 只负责展开组件，
表格如何预览、展开、滚动和复制仍由 `table_preview` 统一负责。

## code_file_collection

用途：从 TSV 文本索引批量生成多个 `code_file`，适合多个 Newick、命令片段、小配置或小 JSON。

TOML：

```toml
[[sections.components]]
type = "code_file_collection"
id = "text-artifacts"
source = "04_reports/code_files.tsv"
copy = true
max_embed_bytes = 200000
```

TSV 常用列：

```text
id    source    language    title_zh    title_en
tree_newick    03_results/tree/tree.nwk    newick    Newick 树文件    Newick tree file
```

路径列按优先级读取 `source`、`code`、`path`、`file`。

## native_subreport_collection

用途：从 TSV HTML/QC 报告索引批量生成多个 `native_subreport`，适合 FastQC、MultiQC、
fastp、Qualimap 等大量 HTML 子报告。

TOML：

```toml
[[sections.components]]
type = "native_subreport_collection"
id = "fastqc-reports"
source = "04_reports/html_reports.tsv"
kind = "fastqc"
embed_policy = "auto"
embed_linked_pages = false
```

TSV 常用列：

```text
id    path    kind    title_zh    title_en    embed_policy    enabled
fastqc_S1    03_results/html/S1_fastqc.html    fastqc    S1 FastQC 报告    S1 FastQC report    auto    true
```

路径列按优先级读取 `path`、`html`、`source`、`file`。行内可覆盖 `kind`、
`embed_policy`、`embed_linked_pages`、`linked_page_limit` 等字段。

collection 组件的共同规则：

- `enabled=false`、`include=false` 或 `selected=false` 的行会被跳过；
- 行内 `id` 或 `component_id` 决定展开后组件 ID；
- `title_zh/title_en`、`note_zh/note_en` 会转成结构化多语言字段；
- collection block 上的字段是默认值，行内字段优先；
- 展开后的普通组件写入 `report.normalized.json`；
- collection 不能绕过目标组件的路径、体积和 standalone HTML 检查。

## 组件选择建议

| 数据类型 | 推荐组件 |
| --- | --- |
| 少量关键指标 | `dashboard_cards` |
| 模块状态 | `status_grid` |
| 质量阈值与判定 | `quality_gate_table` |
| TSV/CSV 结果表 | `table_preview` |
| 表格索引 TSV | `table_collection` |
| PNG/SVG 主图 | `plot_card` |
| 差异表达/富集交互查看 | `interactive_plot` |
| 图片索引 TSV | `plot_collection` |
| PDB/mmCIF 结构查看 | `structure_viewer` |
| Newick 树内联查看 | `tree_viewer` |
| FASTA/CLUSTAL 多序列比对 | `sequence_alignment` |
| IGV 外部基因组轨道浏览 | `genome_browser` |
| Newick/短配置/命令片段 | `code_file` |
| 文本产物索引 TSV | `code_file_collection` |
| MultiQC/FastQC/fastp/Qualimap HTML | `native_subreport` |
| HTML/QC 索引 TSV | `native_subreport_collection` |
| 流程步骤表 | `workflow_diagram` + `table_preview` |

如果一个新需求无法用这些组件表达，先判断它是否是多个 flow 都会复用的通用报告能力。
若只是某个 flow 的临时展示偏好，应优先调整 summary 表或选择已有组件，而不是新增组件。
