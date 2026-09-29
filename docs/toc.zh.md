# 0.4.1 目录配置与阅读兼容性

适用候选：`taffish-report-render 0.4.1-r1`。本页不表示该候选已发布。
Flow 必须固定完整 renderer 身份并检查实际 `--version`；0.3.3 不理解这些新字段。

## 接口

正文仍是扁平 `[[sections]]`，顺序、标题、编号、科学数据、组件及资产不因目录配置改变。
默认延续 0.3 的随读目录：普通滚动会展开当前章及完整祖先路径，收起无关分支。
`parent`、`visible`、`title`、`collapsed`（包括空 `toc` 表）只描述节点，不再切换交互模式。
无节点配置时仍保留旧版两层目录外观；使用新字段后支持任意合法层级，默认无独立三角按钮
及“全部展开/收起”工具栏。一级节点始终存在。

| 位置 | 字段 | 默认及含义 |
| --- | --- | --- |
| 报告根 `[toc]` | `interaction` | `"follow"`（默认）或 `"manual"`；不是 `[sections.toc]` 字段 |
| `sections.toc` | `parent` | 无；引用规范化后的稳定章节 ID，不解析标题编号 |
| `sections.toc` | `collapsed` | `false`；初始 HTML/手动模式状态；follow 定位后以当前阅读路径为准 |
| `sections.toc` | `title` | 未设则使用正文标题；语言表，包含全部声明语言的非空纯文本 |
| `sections.components.toc` | `visible` | `true`；`false` 只移除目录项，保留正文和原锚点 |
| `sections.components.toc` | `title` | 未设则沿用原组件标题或内建名称；语言规则同上 |

本版不支持隐藏章节。`sections.toc.visible` 明确报错，不静默提升子节点；组件不接受
`parent` 或 `collapsed`。所有 `toc` 未知字段和类型错误都会被拒绝，布尔值不能写成字符串。
collection 的 `toc` 原样复制给所有展开组件；本版不支持 TSV 行级目录覆盖。

## 最小示例

```toml
template = "taffish-flow-report"
[project]
title.zh = "示例报告"
title.en = "Example report"

[[sections]]
id = "positions"
title.zh = "4. 候选差异具体在哪里"
title.en = "4. Candidate differences"
toc.collapsed = true

[[sections]]
id = "candidate_a"
title.zh = "4.1 目标 A 的完整说明"
title.en = "4.1 Full description of target A"
toc.parent = "positions"
toc.title.zh = "4.1 目标 A"
toc.title.en = "4.1 Target A"

[[sections.components]]
id = "candidate_a_window_01"
type = "plot_card"
image = "score.svg"
title.zh = "评分示意图"
title.en = "Illustrative score"
toc.visible = false
```

可运行素材在 `examples/toc-minimal/`。嵌套表语法 `[sections.toc]`、
`[sections.components.toc]` 与上述 dotted keys 等价；放在所属最近的 array-table 下。
`migrate` 导出 dotted keys，保留完整语言表，不将嵌套对象转换成字符串。

## 层级和锚点规则

- `parent` 只能引用存在的章节；不接受组件或 renderer 自动章节作为父节点。
- 缺父节点、自引用、循环、保留 ID 和全局 ID 冲突均为错误；collection 展开后再查一次。
- 旧版 ID 归一化规则保持不变，引用时必须使用规范化 ID；推荐 `[A-Za-z0-9_.-]` 稳定语义 ID。
- `top`、`report-guide`、`deliverables`、`provenance`、`embedded-subreports-data`、
  `report-toc-data`、`image-modal-title` 和 `toc-branch-` 前缀保留。不得使用编号重写旧 ID。
- 声明 ID 与实际内部 DOM ID 共用唯一性空间：code_file 的 `ID-code`、tree_viewer 的
  `ID-newick`、sequence_alignment 的 `ID-alignment`、interactive_plot 的
  `ID-point-size-output`/`ID-opacity-output`，以及设置 static_image 时 structure_viewer
  的 `ID-static`。validate-spec/lint 在读取资产/渲染前拒绝冲突，collection 展开后再查；
  未使用的后缀不会被全局禁用。
- 章节目录深度最多 64；其组件可再下一层。深层缩进会限制，避免窄侧栏被缩进挤出。
- 同级按正文顺序；允许父节点在正文较后出现，也允许不同树分支的正文交错。
  目录树遍历顺序因此不一定等于完整正文顺序，renderer 不重排正文；作者应优先让子章节连续。
- 仅有子章节的分组可通过 strict lint；真正没有组件和子章节的空章仍保留旧 lint 警告。

## 阅读行为

默认 follow 模式中，节点文字是正文定位链接，Tab/Enter 可导航；当前项使用 aria-current，
有子节点的链接有 aria-expanded/aria-controls。普通滚动只跟随阅读，不跳转正文、不改 hash、
不抢焦点。正在键盘访问的分支暂缓收起，焦点离开后再与阅读位置同步。
桌面 sticky 侧栏会在必要时仅滚动自身以露出当前项；窄屏正文及目录内的键盘焦点不被此机制滚动。
窄屏目录位于正文上方；定位使用正文内相对坐标和正文实时位置，目录开合改变高度后仍能正确跟随。
原生滚动锚定不足时，仅按开合造成的残余位移即时补偿一次文档滚动偏移，保持屏幕中的正文不动；
不按章节跳转、不平滑滚动或循环纠偏，也不依赖正文尺寸观察器捕获纯位置变化。
当前条目、所属可见章节及其祖先路径优先于 collapsed 初始状态，不会让当前路径长期藏起。
这不是“初始全部展开”，也不是只在点击后展开。目录树由 ID 决定，不解析标题编号。

显式 manual 模式保留 0.4.0 的独立折叠和批量按钮；文字定位与按钮折叠分开，按钮可用
Tab/Enter/Space。普通滚动只高亮，不改变手动开合状态。即使没有任何节点 toc 字段也能选 manual。
两种模式的初始深层 hash、点击链接和浏览器前进/后退都会展开全部祖先。
阅读高亮用正文位置计算：被排除组件映射到所属可见章节，不重新生成隐藏项；祖先另有路径提示。
语言切换和正文尺寸变化更新定位。原生子报告的 `#taffish-subreport=` 路由不被目录占用。
不使用 CDN、目录搜索或 localStorage 折叠状态，不增加服务端依赖。

新目录不会折叠正文，也不改变打印正文；完整 PDF 分页、字体、表格裁切仍需独立视觉验收。

## 从 0.4.0 升级

原有 parent/visible/title/collapsed 配置原样可用，不需重写层级。0.4.1 默认恢复自动跟随，
这是有意的默认行为修正；需要维持 0.4.0 手动体验时，在报告根添加：

```toml
[toc]
interaction = "manual"
```

需要显式固定默认行为时使用 `interaction = "follow"`。本表与 `[project]`、`[[sections]]`
同级。未知字段/非法枚举明确报错；没有自动编号、目录搜索、持久折叠记忆或项目 HTML 后处理。

## 诊断与验收

`explain --json` 和 `inspect-html --json` 的 `toc` 包含 version=2、mode、interaction、visible_count、hidden_count
及 nodes：id、kind、parent、section_id、anchor、body_order、visible、hidden_reason、title、
title_source、collapsed、ancestors、depth、active_id。索引包含自动章节和隐藏组件，计数不是
科学章节数或正文组件数。组件没有显式标题时，title 可以为空，UI 仍用内建组件名称。
mode 仍是结构分类 legacy/tree，不再代指交互；interaction 才是 follow/manual。
inspect 仍接受 0.4.0 的 v1 索引和更早的 HTML，不给旧文件伪造新配置。v2 同时校验 HTML 与索引的交互身份。

相同索引写入 `report_toc.json` 并内嵌最终 HTML；单文件阅读和 inspect 不依赖 sidecar。
`inspect-html --validate` 检查锚点存在且唯一、层级、计数及新模式目录可见链接集合。
索引自检不替代 Flow 独立预期表、资产 hash 或真实浏览器 QA。

维护者人工长报告生成（源码 checkout，不是已安装 Flow 依赖）：

```sh
PYTHONPATH=python python3 tests/toc_fixture.py --outdir NEW_FIXTURE_DIR
PYTHONPATH=python bin/report-render render --spec NEW_FIXTURE_DIR/report.toml \
  --root NEW_FIXTURE_DIR --out NEW_FIXTURE_DIR/output/report.html --validate
```

默认 19 个目标、190 个比对窗口，无客户数据。覆盖 strict lint、TOML/JSON 语义往返、
旧目录回归、负例、正文与资产不变、深链、双语桌面/窄屏、键盘、历史和打印正文保留。
`tests/prepare-toc-browser.py` 生成独立 follow/manual、旧目录、仅隐藏/短标题/空表等案例；
`tests/browser-follow.cjs` 检查普通滚轮路径，`tests/browser-toc.cjs` 专测显式 manual。
