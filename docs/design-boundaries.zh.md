# 设计边界

`taffish-report-render` 的目标不是让每个 flow 更自由地写 HTML，而是让它们少写 HTML。
它应该成为 TAFFISH flow 报告的固定组件编译器：输入结构化 spec，输出统一风格的单文件报告。

## 三层职责

| 层级 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| Flow | 运行分析、整理结果、生成 summary 表、选择哪些内容进入报告。 | 不手写报告外壳、sidebar、语言切换、子报告运行时。 |
| Spec | 声明章节、组件、标题、说明和本地文件路径。 | 不保存图片 base64、HTML payload、大矩阵或分析逻辑。 |
| Renderer | 校验 spec、读取本地资产、生成固定组件、内嵌资源、输出 standalone HTML 和索引。 | 不做生物学分析、不联网抓数据、不替用户解释结果。 |

这个分层的好处是：flow 保留领域表达力，renderer 保持样式和交付稳定。

## 为什么不用 raw HTML

raw HTML 会让报告能力重新分叉：

- 每个 flow 会复制一套不同的卡片、按钮、目录和语言切换；
- 图片是否内嵌、表格是否能横向滚动、子报告是否能打开会反复出错；
- 后续修复模板时无法统一迁移旧报告；
- 安全边界和路径边界更难检查。

因此 publish-ready 报告应由固定组件构建。若某个新展示需求确实无法表达，应先把它抽象成
新的稳定组件，并补 fixture、文档和 checklist，而不是在某个 flow 中开 raw HTML 后门。

结构化说明同样遵守这条边界。`note_items` 只接收固定 kind、双语 label、纯文本 paragraph
和等长双语列表；renderer 负责转义和语义化 DOM。它不是 Markdown、HTML 或样式注入口，
也不允许报告自行声明 class、style、event、JavaScript 或 URL 行为。

## Standalone HTML 规则

最终报告的主 HTML 应尽量做到：

- 单文件离线打开；
- 真实 TAFFISH logo 内嵌；
- 主 CSS/JS 内嵌；
- 主图片以内嵌 data URI 交付；
- 支持的原生 HTML/QC 子报告作为 payload 存在同一个 HTML 中；
- 报告目录中保留 spec、normalized JSON、文件索引和子报告索引。

`report.toml` 或 canonical JSON manifest 是唯一的结构配置入口。结果目录里的图片、表格、
PDB、HTML/QC 报告是被 spec 引用的数据资产，不是额外配置。最终阅读和交付应以单个 HTML
为准；spec、normalized JSON 和索引文件用于审计、复现和调试，不允许成为打开报告的依赖。
默认策略是内嵌可安全内嵌的资产；非内嵌模式必须由 spec 显式选择，或由 renderer 的体积/
安全边界触发，并在报告中说清楚。

这不等于所有原始结果都必须塞进 HTML。大型矩阵、PDF、BAM、reads、完整日志和大型中间目录
仍应保留在结果目录中，由报告索引或源文件链接指向。

## 原生 HTML 子报告策略

MultiQC、FastQC、fastp、Qualimap 等报告本身就是用户熟悉的交互页面。
renderer 的目标是“打包真实页面”，不是重写一个看起来相似的页面。

原则：

- 优先嵌入原程序生成的 HTML；
- 本地 CSS、JS、图片、CSS `url(...)`、`srcset`、`poster` 尽量内联；
- 子报告在独立本地页面上下文中打开；
- JavaScript-heavy 报告的脚本不应在主报告上下文提前执行；
- 已知 legacy fastp 远程 Plotly loader 在 renderer 层统一替换为本地 runtime；
- 无法可靠嵌入的服务器型或网络型页面应标记为 linked/skipped/warn，而不是假装成功。

## 表格策略

表格是报告中最容易破坏布局的元素。renderer 的默认策略是：

- 默认只预览前若干行；
- 在体积边界内提供同一张表的原地完整查看器；
- 支持横向滚动到最右列；
- 支持搜索、排序、单元格展开和完整值复制；
- 对超长单元格做紧凑显示，但完整值仍可访问；
- 超过行数或字节边界时，不强行内嵌。

这比“默认完整铺开所有表格”更稳，也比“隐藏信息”更可审计。

## 布局策略

同类组件的相对布局应由 renderer 固定，而不是由每个 TOML 临时调参：

- 标题、路径、状态放在卡片上方；
- 主要数据、表格、图像或结构摘要放在中部；
- 主要操作按钮默认靠卡片左下角；
- 长路径、长 ID、长表格值在卡片内安全换行或滚动；
- 动态 viewer 与静态图并排时各自按内容高度对齐，不互相拉伸出大空白。

如果一个布局问题能在 renderer 层普适解决，就不应通过某个 flow 的 spec 临时规避。

响应式治理必须覆盖整个 shell，而不只是正文图片。hero、sidebar、目录层级、语言切换、
section 标题、结构化说明、card header、badge、action row、workflow、宽表、代码区和 viewer
都要显式处理 `min-width: 0`、最大内联尺寸和长字符串换行。页面级横向溢出视为失败；表格、
代码、比对和 viewer 的有意内部滚动仍应保留，不能用全局 `overflow: hidden` 掩盖问题。

固定视觉矩阵至少覆盖 `1600x1000`、`1280x800`、`390x844`，中英文、200% 缩放和
print/PDF；media 组件宽度还要精确覆盖 `901px`、`900px`、`621px`、`620px`。
`901px` 保持图文双栏，`900px` 及以下图片在前、说明在后；compact 说明在 `621px`
保持两列，在 `620px` 及以下折为单列。上述边界使用 component-width container query，
同时保留同边界 viewport fallback。

## 多语言策略

renderer 可以翻译自己拥有的 UI 文案，例如按钮、状态、表头和空状态。
它不应该机器翻译业务数据。

应该显式提供双语的内容：

- 报告标题；
- section/component 标题；
- 解释性 note；
- 质量门控说明；
- summary 表中的解释字段。

不应自动翻译的内容：

- 基因名、蛋白名、样本 ID；
- p 值、counts、ratio；
- 原始工具输出；
- 文件路径；
- 原生 HTML 子报告内部内容。

如果表格需要双语解释，推荐使用 `note_en`/`note_zh`、`criterion_en`/`criterion_zh` 等成对列。

## 依赖策略

当前 renderer 尽量只依赖 Python 标准库。保持镜像小有三个好处：

- flow 调用成本低；
- 发布和多架构构建更稳；
- 未来多个 flow 共同依赖时不会把报告工具变成重量级运行环境。

可以考虑新增依赖的情况：

- 新的固定组件确实需要解析复杂格式；
- 某类原生报告无法用标准库可靠内嵌；
- 可视化 runtime 能明显提升多个 flow 的报告能力；
- 依赖 license 清楚、体积可控、离线可打包。

不应为了单个项目的一次性展示加入大型依赖。

对于 JavaScript 可视化能力，应优先使用 runtime pack 模式：镜像可以携带经过版本、license
和体积记录的可选 runtime，但最终 HTML 只有在对应组件实际使用时才嵌入。PDB/结构查看、
基因组轨道、网络或交互图表都应走这种模式，而不是让每个 flow 自己复制 JS 或手写 viewer。
详细规则见 [runtime-packs.md](runtime-packs.md)。

测试 shim 只能用于离线 smoke 或接口测试。`tests/test-real-run.sh`、公开示例报告和最终视觉验收
必须使用真实 runtime pack；如果真实 runtime 不存在，应该明确失败，而不是生成一个看起来
“有组件”但无法动态显示的假报告。

## TOML 长度和生成方式

复杂报告的 TOML 可能很长，这是可接受的。它比手写 HTML 更稳定，因为每一段都只是：

```text
组件类型 + 本地文件路径 + 标题/说明 + 少量组件参数
```

推荐 flow 自动生成 TOML，而不是让维护者手写所有重复 block。

例如：

- 根据 `html_reports.tsv` 生成多个 `native_subreport`；
- 根据 `plot_files.tsv` 生成多个 `plot_card`；
- 根据 `report_tables.tsv` 生成多个 `table_preview`；
- 根据 flow summary 生成 `workflow_diagram` 和 `status_grid`。

只要最终 `report.spec.toml` 被保留，自动生成并不会降低可审计性。

## 编译器诊断和 Collection

renderer 的长期形态是严格的小 DSL 编译器，而不是宽松模板引擎。开发者应把这条链路作为
默认工作方式：

```text
report.toml -> validate/lint/explain -> normalized JSON -> standalone HTML -> inspect/list-assets
```

其中：

- `schema` 给编辑器、CI 和外部生成器提供机器契约；
- `validate-spec` 保证基本结构正确；
- `lint` 在 `--root` 下检查路径、collection 展开、双语覆盖和体积边界；
- `explain` 让维护者在渲染前审查组件和资产；
- `migrate` 生成 canonical JSON，尤其用于展开 collection 组件；
- `inspect-html` 和 `list-assets` 检查渲染后报告的 standalone 状态和索引。

collection 组件是为了减少重复 TOML，而不是增加新的视觉自由度。它只能把 TSV 行展开为已有
稳定组件，例如 `plot_card`、`table_preview`、`code_file` 和 `native_subreport`。如果一个
需求无法通过 collection 展开为固定组件，就应该先讨论是否新增稳定组件。

测试链路也必须遵守同一个边界。`tests/smoke.sh` 只做快速契约检查；
`tests/test-real-run.sh` 是唯一真实报告回归入口，负责在清理旧 `tests/test-real-run-out/`
产物后，用本 renderer CLI 和对应 `report.toml` / canonical manifest 重新生成各 fixture
报告。测试可以生成或保留 spec 作为输入证据，但不能在测试脚本中手写、拼接、复制或 patch
最终 HTML；否则测试验证的是临时页面，而不是 renderer。

`tests/smoke.sh` 的输出根目录固定为 `tests/smoke-out/`，不能和 full real-run 共用目录；
`tests/test-real-run.sh` 结束前必须检查每个输出单元的固定目录结构和关键 sidecar 文件。
输出树按用途分成两类：

- `tests/test-real-run-out/flow-reports/`：复现当前维护的全部真实 flow 报告，包括
  NGS QC、BAM QC、phylogeny、RNA-seq 有参、RNA-seq 无参和 Chengdu Yuanda report 12；
- `tests/test-real-run-out/component-regression/`：用真实报告风格的领域 fixture 覆盖
  renderer 组件/runtime 能力，包括基础组件、ECharts、tree/alignment、IGV 和
  NGL/native HTML。

phylogeny fixture 必须覆盖 `tree_viewer` 和 `sequence_alignment`，因为系统发育报告需要
同时查看 Newick 树和多序列比对。Chengdu Yuanda report 12 是
`structure_viewer runtime="ngl"` 的真实结构报告，必须进入默认全量回归；源码树没有真实
NGL runtime 时应明确失败并提示使用已打包 runtime 的发布镜像或先准备源码树
vendored runtime pack。JavaScript 路径不是普通用户报告参数，real-run 不联网补包。
test shim 只能用于显式 smoke/interface 测试，不能进入 full real-run，也不能替代动态结构
视觉验收。

结构查看组件的验收不是只看见一个空白 viewer 框。最终 HTML 必须同时内嵌结构 payload
JSON、每个模型的 PDB 文本、真实 NGL runtime 和静态结构图；静态图必须走共享大图
lightbox。结构卡片和前后组件之间的间距由 renderer CSS 统一保证，不允许通过 TOML
插入空白组件来弥补布局问题。

`genome_browser runtime="igv"` 必须以真实或由真实数据派生的基因组数据进入
component-regression 覆盖。小型 FASTA/FAI/BED/bedGraph 可通过 renderer 统一内嵌成
data URI；大型 FASTA/BAM/VCF/BigWig 仍默认外部化。源码树缺少真实 IGV runtime 时，
real-run 应明确失败并提示使用发布镜像或准备源码树 vendored runtime pack；只有
smoke/interface 测试可以显式使用 shim。IGV fixture 不能使用 `example.org`、空白 viewer
或假 genome 配置作为通过证据。

IGV 视觉验收必须覆盖原生交互可达性，而不只是 viewer 非空。至少要抽查搜索/缩放工具栏、
track 齿轮菜单或等价原生弹层不会被报告卡片裁切，也不会让 viewer 主体越界覆盖右侧
说明卡或后续组件；此类布局问题应在 renderer CSS/JS 统一修复，不能要求每个 TOML
fixture 用额外空白或手写 HTML 规避。

组件回归不等于 demo。即使某个组件暂时没有上游 flow 消费，也应构造小而真实的领域报告：
使用真实格式数据、真实 runtime、真实章节结构和 `04_reports/` 输出 sidecar。测试脚本不得
生成“组件展示页”、假 runtime、测试版 Python 行为或测试专用 HTML 作为 publish-ready 证据。

## 组件扩展流程

新增组件前应回答：

1. 是否已有组件可以表达？
2. 是否至少两个 flow 会复用？
3. 是否有真实 fixture 可以覆盖？
4. 是否会破坏 standalone HTML 规则？
5. 是否能用固定 schema 描述，而不是 raw HTML？
6. 是否已补 README/docs/checklist/help 中的必要说明？
7. 是否通过 `tests/smoke.sh` 和相关 real-run 测试？

组件一旦进入 stable registry，就应尽量向后兼容。

## 和 flow-report 模板的关系

`repos/apps/templates/flow-report/` 是视觉和 DOM contract 基线。
`taffish-report-render` 应复用其硬外壳思想：

- 真实 logo；
- 左侧目录；
- 语言切换；
- consistent cards；
- standalone HTML；
- 子报告打开模型；
- 渲染后 checker。

renderer 可以把这些能力产品化，但不应另起一套视觉语言。
