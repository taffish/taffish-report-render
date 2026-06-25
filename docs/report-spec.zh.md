# Report Spec 结构

`taffish-report-render` 的输入是一个结构化 spec，通常写成 `report.toml`。
TOML 是人类友好的前端；renderer 会把它归一化成 canonical JSON，并和最终 HTML 一起保存。

核心输入三件套：

```text
--spec report.toml
--root <flow-output-directory>
--out  <flow-output-directory>/04_reports/report.html
```

`--spec` 声明报告结构，`--root` 提供本地资产根目录，`--out` 是最终 standalone HTML。

## 顶层字段

最小 spec 形状如下：

```toml
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "0.1"
languages = ["zh", "en"]
language_default = "zh"

[project]
flow_name = "example-flow"
flow_version = "0.2.0-r1"
analysis_mode = "example"
title.zh = "示例报告"
title.en = "Example Report"
subtitle.zh = "示例报告说明。"
subtitle.en = "Example report subtitle."

[provenance]
versions = "04_reports/versions.tsv"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Project Overview"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/key_metrics.tsv"
```

字段说明：

| 字段 | 必需 | 含义 |
| --- | --- | --- |
| `schema_version` | 是 | spec 结构版本。当前为 `"0.1"`。 |
| `template` | 是 | 必须是 `"taffish-flow-report"`。 |
| `template_version` | 建议 | 记录目标模板版本；fixture 可用 `"fixture-current"`。 |
| `languages` | 建议 | 报告语言列表。当前常用 `["zh", "en"]`。 |
| `language_default` | 是 | 默认显示语言，例如 `"zh"`。 |
| `[project]` | 是 | 项目标题、flow 名称、版本、分析模式等。 |
| `[provenance]` | 建议 | 版本、manifest、解释报告、模板版本等溯源文件。 |
| `[[sections]]` | 是 | 报告主章节。 |
| `[[sections.components]]` | 是 | 每个章节中的固定组件。 |

## Schema、Lint 和 Normalize

当前 spec 结构版本仍是：

```toml
schema_version = "0.1"
```

`taffish-report-render` 自身的发布版本可以推进，但只要 spec 结构仍向后兼容，
`schema_version` 不需要随 app release 同步跳号。renderer 会在渲染时生成 canonical
`report.normalized.json`，它是更适合机器审计和回归比较的中间表示。

开发时推荐这样检查：

```sh
taf-taffish-report-render schema > report.spec.schema.json
taf-taffish-report-render validate-spec --spec report.toml --root OUTDIR
taf-taffish-report-render lint --spec report.toml --root OUTDIR
taf-taffish-report-render explain --spec report.toml --root OUTDIR
taf-taffish-report-render migrate --spec report.toml --root OUTDIR --format json > report.normalized.json
```

命令差异：

| 命令 | 作用 |
| --- | --- |
| `schema` | 输出机器可读 JSON schema。 |
| `validate-spec` | 检查结构、必填字段、重复 ID 和组件类型。 |
| `lint` | 在 `--root` 下检查路径、collection 展开、双语覆盖和内嵌边界。 |
| `explain` | 渲染前摘要章节、组件和引用资产。 |
| `migrate` | 输出归一化 TOML/JSON；带 `--root` 时会展开 collection 组件。 |

## Project 字段

`[project]` 面向报告首页和 metadata：

```toml
[project]
flow_name = "rnaseq-standard-flow"
flow_version = "0.3.0-r1"
analysis_mode = "reference"
title.zh = "TAFFISH RNA-seq 项目报告"
title.en = "TAFFISH RNA-seq project report"
subtitle.zh = "有参 RNA-seq 标准分析。"
subtitle.en = "Reference-guided RNA-seq standard analysis."
```

常用字段：

| 字段 | 含义 |
| --- | --- |
| `flow_name` | 生成报告的 flow 名称。 |
| `flow_version` | flow 版本；用于报告溯源，不替代 `versions.tsv`。 |
| `analysis_mode` | 分析路线，例如 `reference`、`denovo`、`quality-control`。 |
| `title.<lang>` | 报告标题。 |
| `subtitle.<lang>` | 报告副标题。 |

`title` 和 `subtitle` 推荐提供中英双语。缺失语言会按默认语言、英文、中文的顺序回退。

## Section 和 Component

`section` 是左侧目录的一级项，也是右侧报告的大章节：

```toml
[[sections]]
id = "de"
kind = "analysis"
title.zh = "差异表达"
title.en = "Differential Expression"
note.zh = "展示条件间表达变化和样本结构。"
note.en = "Shows expression changes and sample structure."
```

`component` 是章节内的固定模块，也是左侧目录的子项：

```toml
[[sections.components]]
type = "plot_card"
id = "de-volcano"
image = "03_results/plots/de.volcano_plot.png"
title.zh = "火山图"
title.en = "Volcano plot"
```

规则：

- 每个 `section.id` 必须稳定且唯一；
- 每个 `component.id` 必须稳定且唯一；
- `component.type` 必须来自已注册组件；
- 未知组件类型应验证失败；
- 左侧目录顺序必须和 TOML 中的章节、组件顺序一致；
- component 只描述展示方式，不应包含执行命令或分析逻辑。

## Collection Components

collection 组件是编译期辅助写法，用于把一个 TSV 索引批量展开成普通稳定组件。它们不会改变
最终报告的运行时组件模型。

当前支持：

| Collection | 展开为 | 主要路径列 |
| --- | --- | --- |
| `plot_collection` | `plot_card` | `image`、`plot`、`path`、`source` 或 `file` |
| `table_collection` | `table_preview` | `source`、`table`、`path` 或 `file` |
| `code_file_collection` | `code_file` | `source`、`code`、`path` 或 `file` |
| `native_subreport_collection` | `native_subreport` | `path`、`html`、`source` 或 `file` |

示例：

```toml
[[sections.components]]
type = "plot_collection"
id = "de-plots"
source = "04_reports/plot_files.tsv"
default_fit = "contain"
zoom = true
```

TSV 示例：

```text
id	image	title_zh	title_en	note_zh	note_en	enabled
pca	03_results/plots/de.pca_plot.png	PCA 图	PCA plot	样本整体结构。	Global sample structure.	true
volcano	03_results/plots/de.volcano_plot.png	火山图	Volcano plot	差异基因分布。	Differential-gene distribution.	true
```

展开规则：

- `enabled=false`、`include=false` 或 `selected=false` 的行会被跳过；
- 行内 `id` 会生成稳定 component id；否则使用 collection id 和行号；
- 行内 `title_zh/title_en`、`note_zh/note_en` 会变成组件双语字段；
- collection block 上的通用参数会作为默认值，例如 `embed_policy`、`preview_rows`；
- 行内字段优先级高于 collection block 默认值；
- `report.normalized.json` 保存展开后的普通组件，便于审计。

collection 适合批量结果，不适合绕过固定组件契约。如果某一行需要完全不同的展示方式，
应单独写普通 component。

## 路径规则

所有组件中的 `source`、`image`、`path`、`pages` 都相对 `--root` 解析。

允许：

```toml
source = "03_results/tables/de.summary.tsv"
image = "03_results/plots/de.volcano_plot.png"
path = "03_results/html/multiqc_report.html"
```

不允许：

```toml
source = "/Users/me/project/de.summary.tsv"
image = "../outside/plot.png"
path = "https://example.org/report.html"
```

原因：

- 最终报告不能泄露维护者本机绝对路径；
- renderer 不能把结果目录外的文件意外打包进去；
- renderer 不负责联网抓取资源；
- flow 的可复现边界应该是 `<outdir>`。

## 多语言规则

解释性文本推荐写成结构化语言字段：

```toml
title.zh = "项目总览"
title.en = "Project Overview"
note.zh = "展示关键指标。"
note.en = "Shows key metrics."
```

表格中也可以使用语言成对列：

```text
criterion_en    criterion_zh    status    note_en    note_zh
Read quality    读长质量        OK        Passed     通过
```

renderer 会把 `criterion_en`/`criterion_zh`、`note_en`/`note_zh`、
`body.en`/`body.zh` 等折叠成一个逻辑多语言列。

不会自动翻译的内容：

- 基因 ID；
- p 值、fold change、counts；
- 文件路径；
- 工具原始输出；
- 原生 HTML 子报告内部已有内容。

如果需要解释性双语内容，应由 spec 或上游 summary 文件显式提供。

## Provenance 字段

`[provenance]` 用于告诉 renderer 哪些文件是溯源材料：

```toml
[provenance]
manifest = "04_reports/run.manifest.json"
versions = "04_reports/versions.tsv"
commands = "04_reports/commands.sh"
methods = "04_reports/methods.txt"
template_version = "04_reports/report_template_version.txt"
interpretation_report = "04_reports/report_interpretation.html"
```

这些字段不会替代正式组件。若希望在正文中展示某个文件，应同时添加合适组件，例如：

```toml
[[sections.components]]
type = "code_file"
id = "methods"
source = "04_reports/methods.txt"
title.zh = "方法摘要"
title.en = "Methods summary"
```

## 自动章节

renderer 会自动补充一些报告级结构，例如：

- reading guide / 如何阅读本报告；
- deliverables / 交付文件；
- provenance / 溯源信息；
- template/runtime metadata。

这些内容由 renderer 统一生成，flow 不应临场复制一套相似 HTML。flow 只需要提供输入文件和
组件声明。

`report-guide`、`deliverables` 和 `provenance` 是自动章节保留 ID。用户 spec 中不要把
普通 section 写成这些 ID；需要展示交付文件时可使用 `source-deliverables`、
`workflow-provenance` 等业务含义更明确的 ID。

## 输出索引

每次渲染都会在输出 HTML 旁边写入：

```text
report.spec.toml 或 report.spec.json
report.normalized.json
report.manifest.json
report_files.tsv
embedded_html_reports.tsv
report_template_version.txt
```

这些文件是调试和审计入口。`report_files.tsv` 记录打包或引用过的资产；
`embedded_html_reports.tsv` 记录原生 HTML 子报告的嵌入状态、体积和策略。

## 验证建议

flow 调用 renderer 时建议始终使用：

```sh
taf-taffish-report-render render \
  --spec "${outdir}/04_reports/report.toml" \
  --root "${outdir}" \
  --out "${outdir}/04_reports/report.html" \
  --force \
  --validate
```

开发中也可以单独验证：

```sh
taf-taffish-report-render validate-spec --spec report.toml
taf-taffish-report-render validate-html 04_reports/report.html
```

`validate-html` 是轻量 standalone 合同检查，不替代真实浏览器视觉 QA。
