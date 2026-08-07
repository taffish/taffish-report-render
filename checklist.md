# taffish-report-render 开发检查清单

这个清单比通用 TAFFISH app checklist 更严格，因为本 app 会成为多个 flow 共用的报告基础设施。
在递归开发过程中，每次声称 renderer 变更已经可用前，都应按本文核对。

通用 TAFFISH app 检查仍然适用：

- `docs-for-codex/TAF-APP-RULES.md`
- `docs-for-codex/TAF-APP-CHECKLIST.md`
- `docs-for-codex/TAF-APP-SMOKE-GUIDE.md`
- `repos/apps/templates/flow-report/checklist.md`

## 高频 real-run 硬规则

这些规则优先级最高，用来避免长期迭代后把接口测试、demo 和真实报告验收混在一起：

- [ ] `tests/test-real-run.sh` 是真实报告回归入口，不是 demo 入口；必须按真实 flow
      输出、真实 runtime、真实报告结构渲染并检查。
- [ ] 无参数运行 `tests/test-real-run.sh` 默认必须清理旧 `tests/test-real-run-out/`，
      重新生成全部维护中的真实报告和真实风格组件回归报告；不能只留下某一个场景。
- [ ] 全部已注册且维护中的 runtime/component 库都必须进入默认 real-run。缺真实数据时，
      脚本应从项目真实测试数据或已 vendored 的固定 runtime pack 读取；获取不到时必须硬失败并
      说明准备方式，不能联网补 runtime、静默跳过、降级成 demo，或用 `example.org`
      这类假 URL 通过。
- [ ] 默认 real-run 应在渲染前预检本轮选中 fixture 需要的全部 runtime pack；例如同一轮
      同时需要 NGL 和 IGV 时，两个 runtime 都必须尝试真实来源获取并报告缺口，不能因为
      第一个缺失 runtime 提前停止而掩盖后续库没有被检查的问题。
- [ ] runtime 预检失败不能破坏已有成功 real-run 输出；`rendered_reports.tsv` 等索引文件
      只能在预检通过、即将开始新一轮渲染时重写，不能在缺 runtime 的失败路径上清空。
- [ ] `tests/test-real-run.sh` 不允许使用 NGL/IGV 或其它 viewer 的 test shim；
      如果真实 runtime 缺失，real-run 应失败并给出准备方式。shim 只能属于
      `tests/smoke.sh` 这类接口/契约测试，不能作为 publish-ready 证据。
- [ ] 组件回归报告也必须像真实报告：使用真实生信语义数据、真实组件参数、
      真实 runtime 和 `04_reports/` 输出结构。不能为了证明组件存在而生成 toy/demo
      页面、假 viewer、测试专用 HTML 或“测试版 Python 行为”。
- [ ] test-real-run 只允许通过本 tool CLI 加 TOML/JSON spec 生成 HTML；不得在测试脚本里
      手写、拼接、复制、patch 最终 HTML。
- [ ] 每次修改 renderer、组件、runtime pack、TOML 生成逻辑或测试 fixture 后，必须清理旧
      `tests/test-real-run-out/` 并重新运行 real-run，随后检查固定输出目录和可视结果。

## 0. 边界检查

- [ ] 本 app 保持为 `tool`，不是 flow。
- [ ] 本 app 从本地结构化输入渲染报告，不运行生物学分析工具。
- [ ] renderer 不变成通用网站构建器。
- [ ] renderer 以 `repos/apps/templates/flow-report/` 作为视觉和 DOM contract 基线。
- [ ] renderer 在新增高级组件前，先覆盖现有报告能力。
- [ ] 每个新增组件都必须由至少一个真实报告 fixture 或有文档记录的未来 flow 需求支撑。
- [ ] 能在 renderer 层普适解决的问题，不通过单个 flow 的 TOML 临时绕过；例如多语言表格列、
      legacy fastp runtime、超长表格单元格、可复制文本产物和 reading guide 布局。
- [ ] 报告结构配置只有一个入口：`report.toml` 或 canonical JSON manifest。其它 HTML、
      CSS、JS、layout 配置文件不得成为渲染必需输入；结果目录中的图片、表格、PDB、
      原生 HTML 子报告是数据资产，不是额外配置。
- [ ] GitHub-facing `README.md` 和 `docs/help.md` 必须保持英文，和其它 taf-app 一致；
      详细使用文档必须提供明确的中英文成对入口，例如 `docs/components.en.md` /
      `docs/components.zh.md`。终端 help 只保留基本用法和文档 URL，不塞长篇背景。
- [ ] 最终交付阅读产物是单个 standalone HTML。`report.spec.toml`、
      `report.normalized.json`、索引 TSV 等 sidecar 只用于审计、复现和调试，不允许成为
      打开或阅读报告的依赖。
- [ ] 默认策略是内嵌可内嵌的数据资产：图片、摘要表、小中型 TSV、PDB、支持的原生
      HTML 子报告和必要 runtime pack 都应进入主 HTML。非内嵌或 linked-only 模式必须
      由 spec 参数显式选择，并在报告和索引中记录原因。
- [ ] 本 app 是 TAFFISH 原生稳定领域 CLI，不是第三方上游 wrapper；`src/main.taf`
      必须直接使用 `<container:...>` 加统一内部入口，不能使用 `<taf-app:...>`。
- [ ] 容器内部只暴露一个统一入口 `report-render`；`render`、`init`、`new`、
      `validate-spec` 等都是该入口的子命令，不分别做独立 bin。
- [ ] `taf-taffish-report-render render ...`、`taf-taffish-report-render init ...`
      和 `taf-taffish-report-render new ...` 必须进入 `report-render ::*ARGV*::`；
      不得被 `<taf-app:...>` command mode 截走当成容器内 executable。
- [ ] `[runtime].command_mode = false` 作为 index/runtime 描述保留，但不要把它当成
      关闭 `<taf-app:...>` command mode 的语言开关。

## 1. 真实 Fixture 和测试数据检查

- [ ] `testdata/README.md` 说明 fixture 覆盖什么，以及为什么不完整复制上游 flow 输出。
- [ ] 每个 fixture 都有 `report.toml` 草案或 canonical `report.manifest.json` 输入。
- [ ] 每个 fixture 都在 `testdata/fixtures.tsv` 中记录来源 flow 和来源路径。
- [ ] fixture 文件体量适合进入 app 仓库，不包含大矩阵、raw reads、BAM 或完整分析目录。
- [ ] 计划提交到 GitHub 的仓库只保留安装和使用必需的源代码、文档、schema、示例 TOML、
      小型必要资产和 runtime pack；本地真实 `testdata/fixtures/`、`testdata/runtime/`
      payload、`tests/test-real-run-out/`、`tests/smoke-out/` 和 `target/` 产物必须在
      `.gitignore` 中忽略，不能随 app 发布提交。
- [ ] fixture 内部路径应相对于 fixture root；renderer 测试不依赖维护者本机绝对路径。
- [ ] 真实 flow fixture 至少覆盖当前维护的全部 flow 报告家族：NGS QC、BAM QC、
      phylogeny、RNA-seq 有参、RNA-seq 无参和 Chengdu Yuanda report 12；
      不能因为最近只修改了某个组件就只保留其中一个真实报告输出。
- [ ] 组件回归 fixture 单独覆盖 renderer 能力面，但仍必须是“真实报告风格”：
      基础卡片/表格/图片/原生 HTML、ECharts 交互图、Newick 树与多序列比对、
      IGV genome browser、NGL/PDB 结构查看和 native HTML 子报告都应嵌入到有
      生信含义的报告章节里，而不是孤立 demo 页。
- [ ] 如果某个组件暂时没有现有 flow 使用，应准备一个小而真实的领域 fixture，例如
      小型真实/仿真但语义完整的 genome locus、PDB 结构、Newick 树或表达结果；
      不得使用假 runtime、空白 viewer 或测试专用页面替代真实报告表现。
- [ ] fixture 包含 MultiQC、FastQC、fastp、Qualimap 的代表性 HTML 子报告；
      如果某类暂缺，必须说明原因。
- [ ] fixture 至少覆盖一个含 `*_en`/`*_zh` 语言成对列的表格，并验证英文/中文模式不会
      暴露错误语言列。
- [ ] fixture 至少覆盖一个包含超长单元格的表格，例如富集分析 `geneID` 列，确认不会撑出
      大面积空白。
- [ ] fixture 至少覆盖一个 `code_file` 文本产物，例如 Newick 树文件，并验证复制按钮存在。
- [ ] fixture 至少覆盖一个 `structure_viewer runtime="ngl"` 真实结构报告，确认 NGL runtime
      只在该报告中内嵌，普通报告不包含 NGL。
- [ ] NGL fixture 必须检查 `runtime="ngl"` payload 同时包含 `pdbText` 和解析后的
      `atoms`；真实 NGL 可用时走 WebGL，不可用或加载失败时必须自动
      降级到同一卡片里的内置 canvas 结构 viewer，不能只显示空白或一句失败提示。
- [ ] NGL 降级 viewer 仍要尊重模型开关、site/motif marker 开关、marker 大小和透明度
      控制；Chengdu Yuanda report 12 这类结构叠合 fixture 必须在真实 runtime 或真实
      fallback payload 下看到多模型 trace 和位点球标记。
- [ ] fixture 至少覆盖一个 `genome_browser runtime="igv"` 的 embedded 模式和一个
      `viewer_mode="linked"` 的 linked 模式。embedded 模式在真实 runtime 缺失时必须
      显示可审查 fallback 面板；linked 模式不能强制要求本地 IGV runtime。
- [ ] IGV fixture 必须使用真实或由真实数据派生的 genome/reference/track 数据。
      小型 FASTA/FAI/BED/bedGraph 可通过 renderer 统一内嵌；大型 BAM/VCF/BigWig/CRAM
      可外部化，但必须是可审计的真实 URL/路径，不能使用 `hg38 + example.org`
      这类仅为展示组件存在的伪配置。
- [ ] smoke 临时输出固定写入已忽略目录 `tests/smoke-out/`；真实报告回归输出固定写入
      已忽略目录 `tests/test-real-run-out/`，并按用途分成
      `flow-reports/` 和 `component-regression/` 两个子目录，不混入
      `testdata/` fixture 输入目录。

## 1.5 测试入口和真实报告回归检查

- [ ] 除 `tests/smoke.sh` 外，本 app 只保留一个真实回归测试入口：
      `tests/test-real-run.sh`。无参数运行即为全量清理并渲染；如需 helper，必须由这个脚本内部调用，不能新增多个
      `test-*.sh` / `render-*.sh` / 临时 HTML 生成入口。
- [ ] `tests/smoke.sh` 只负责小型自包含 fixture、CLI contract、组件接口和快速
      standalone 检查；不替代真实报告视觉/能力回归。
- [ ] `tests/test-real-run.sh` 负责生成所有真实报告 fixture。默认或正式回归时应无参数运行，
      自动清理旧 `tests/test-real-run-out/` 产物，再重新渲染所有需要检查的报告，
      避免旧 HTML 掩盖新代码问题。
- [ ] `tests/test-real-run.sh` 的输出目录固定为 ignored 产物目录，并按类型分组：
      真实 flow 报告写入 `tests/test-real-run-out/flow-reports/<fixture>/04_reports/`，
      真实风格组件回归报告写入
      `tests/test-real-run-out/component-regression/<case>/04_reports/`；
      用户显式传入 `--outdir DIR` 时也必须保留同样的 `flow-reports/` 和
      `component-regression/` 两级结构。每个 fixture/case 生成的 HTML、manifest、
      normalized JSON 和索引文件应在对应子目录下成组出现。
- [ ] `tests/smoke.sh` 和 `tests/test-real-run.sh` 不得共用输出根目录；smoke 不能删除或覆盖
      full real-run 结果。修改任一脚本后必须检查这两个默认输出目录仍然分离。
- [ ] `tests/test-real-run.sh` 结束前必须自动检查输出目录结构：默认全量运行时全部
      flow fixture 目录和全部 component-regression 目录都存在；每个输出单元至少包含
      `report.full.toml`、`04_reports/taffish_report.html`、`report.spec.toml`、
      `report.normalized.json`、`report.manifest.json`、`report_files.tsv` 和
      `embedded_html_reports.tsv`。缺失任一关键文件必须失败。
- [ ] `tests/test-real-run-out/rendered_reports.tsv` 必须汇总全部输出；同时分别生成
      `flow-reports/rendered_reports.tsv` 和
      `component-regression/rendered_reports.tsv`，方便维护者快速检查哪一类报告缺失。
- [ ] 真实回归测试只能调用本 tool 的 CLI 入口和对应的 TOML/JSON spec 来生成报告；
      不允许在 test 脚本中手写、拼接或复制最终 HTML 作为测试产物，也不允许用专门的
      fixture 私有 HTML 生成代码绕过 renderer。
- [ ] `test-real-run.sh` 可以根据真实结果树生成或复制 `report.toml` / canonical manifest，
      但这些配置必须作为 renderer 输入被保留下来；所有可见 HTML 仍必须由 renderer 统一生成。
- [ ] 默认无参数 `tests/test-real-run.sh` 必须覆盖当前维护的全部真实报告 fixture：
      `ngs-qc`、`bam-qc`、`phylogeny`、`rnaseq-reference`、`rnaseq-denovo` 和
      `chengdu-yuanda-report12`。其中 Chengdu Yuanda report 12 是结构查看/NGL
      组件的真实回归用例，不能从默认集静默跳过。
- [ ] 默认无参数 `tests/test-real-run.sh` 还必须覆盖当前维护的真实风格组件回归报告：
      基础组件、ECharts 交互图、tree/alignment、IGV 和 NGL/native HTML。它们用于证明
      每个 runtime pack 和 TOML 接口能在真实报告语境里独立渲染，而不是生成 demo 页。
- [ ] 需要可选 runtime pack 的 fixture，例如 `structure_viewer runtime="ngl"`，默认
      real-run 必须使用发布镜像内 runtime 或源码树已 vendored runtime pack；
      源码树缺少真实 runtime 时必须明确失败并提示需要先完成 maintainer vendoring。
      `test-real-run.sh` 不联网下载 runtime，不提供 shim 通过路径；
      shim 只能在 smoke/interface 测试中显式使用。
- [ ] 运行默认全量 real-run 时，NGL、IGV 等浏览器 runtime 缺失属于发布阻塞；如果源码树
      没有对应 runtime pack，应使用已打包 runtime 的正式镜像，或在源码树开发环境中
      先准备对应 runtime pack 后重新运行；JavaScript 路径不是普通用户报告参数。
- [ ] Dockerfile 构建必须离线检查 vendored runtime pack 是否存在，不在 build 阶段联网
      `npm install` / `curl` / 读取代理来补包；runtime 更新属于单独 maintainer vendoring
      步骤，必须记录版本、来源、checksum 和 license。
- [ ] 每次修改 renderer、模板、组件、runtime pack 或 fixture TOML 后，必须清理旧 real-run
      输出、重新运行无参数 `tests/test-real-run.sh` 或明确说明跳过原因，并人工或自动检查新
      `tests/test-real-run-out/` 中的报告没有空白图片、布局错位、外部依赖或子报告打不开问题。

## 2. Schema 和编译器检查

- [ ] TOML 只是人类友好的前端；JSON manifest 是 canonical normalized IR。
- [ ] schema 显式包含 `schema_version`、`template`、`template_version`、`project`、
      `sections` 和 `provenance` 字段。
- [ ] 所有可见文本使用结构化 `zh` 和 `en` 字段。
- [ ] 每个 section 有稳定且唯一的 `id`。
- [ ] 用户 section id 不占用 renderer 自动章节保留 ID：`report-guide`、`deliverables`、
      `provenance`。
- [ ] 每个需要链接、检查或被验证输出引用的 component 有稳定且唯一的 `id`。
- [ ] 每个 component 都有已注册的 `type`。
- [ ] 未知 component type 默认验证失败。
- [ ] 未知 component 字段在 `--strict` 下失败或警告；publish-ready 模式不能静默忽略。
- [ ] 重复 section id 或 component id 必须验证失败。
- [ ] 必需文件资产缺失时验证失败，除非 component 明确标记该资产为 optional。
- [ ] 每次 render 都输出 `report.manifest.json`、原始配置副本 `report.spec.toml`
      或 `report.spec.json`，以及 normalized `report.normalized.json`。
- [ ] 编译器诊断尽量包含 fixture 名称、section ID、component ID 和字段路径。

## 3. 固定组件注册表检查

- [ ] publish-ready 报告由已注册组件构建，不使用任意 raw HTML。
- [ ] 如果未来加入 `raw_html`，它只能是 experimental，并且默认不允许通过 publish-ready 验证；
      例外必须有文档说明。
- [ ] 当前 stable render component 至少覆盖：
      `dashboard_cards`、`status_grid`、`quality_gate_table`、`table_preview`、
      `code_file`、`workflow_diagram`、`plot_card`、`interactive_plot`、
      `structure_viewer`、`tree_viewer`、`sequence_alignment`、`genome_browser`
      和 `native_subreport`。
- [ ] `tree_viewer` 和 `sequence_alignment` 不是只读死样式组件；常见报告级样式参数
      如树枝颜色/宽度、标签颜色/字号、MSA 色板、标签列宽和残基颜色必须能通过 TOML
      声明，并在组件库 fixture 中检查这些参数确实进入 standalone HTML。
- [ ] `genome_browser` 的 TOML 只负责声明接口：runtime、viewer mode、locus、reference
      和 tracks。runtime 检测、linked/embedded 分支、runtime 失败降级、轨道配置展示和
      fallback 布局必须由 renderer 层统一实现，不能要求每个 flow 写私有 workaround。
- [ ] 当前 compile-time collection component 至少覆盖：
      `plot_collection`、`table_collection`、`code_file_collection` 和
      `native_subreport_collection`，并能在 `--root` 下展开为对应 render component。
- [ ] component 输出使用 `repos/apps/templates/flow-report/docs/component-contract.md`
      中的 canonical class vocabulary。
- [ ] component 输出不引入一次性 layout shell、sidebar、language switch、palette 或 footer model。
- [ ] 长标签、路径、文件名、warning 和 status tag 必须在卡片内换行；
      `WARN` 等状态词不能被拆成逐字母换行。
- [ ] workflow connector 使用模板 connector 样式，不使用原始文本箭头。

## 4. Standalone HTML 检查

- [ ] 生成的主 HTML 可作为单文件离线打开。
- [ ] 生成的 HTML 包含 `data-template="taffish-flow-report"`。
- [ ] 生产报告中真实 TAFFISH logo 以非空 data URI 嵌入。
- [ ] 主 CSS 已内联。
- [ ] 导航、语言切换和子报告打开所需的主 JavaScript 已内联。
- [ ] 主 PNG/SVG 图以非空 data URI 嵌入。
- [ ] 空图片 payload，例如 `data:image/...;base64,`，必须验证失败。
- [ ] 必需外部 CSS、JavaScript、图片或字体 URL 必须 standalone 验证失败；
      除非它们明确标记为非必需 external link。
- [ ] 主报告中出现真实 `<script src=...>`、外部 stylesheet、空 data URI 或测试用
      runtime shim marker 时，`validate-html` 必须失败；内嵌原生 HTML 子报告里的脚本
      只能作为 JSON payload 字符串存在，不能污染主文档。
- [ ] standalone 检查必须区分主文档中的真实资源标签和 runtime JavaScript/JSON payload
      字符串里的 HTML 片段；例如 ECharts 等 runtime 内部可能包含 `<img src=...>` 字符串，
      不能被误判为主报告未内嵌图片。
- [ ] 主报告 head 中必须先注入 TAFFISH shell 自己的普通 inline bootstrap `<script>...</script>`，
      再注入 ECharts/NGL/IGV 等大型第三方 runtime pack；大型 runtime 内部可能包含
      `</head>`、`</script>`、`<img src=...>` 等字符串，不能让它们破坏模板检查或主 shell
      结构识别。
- [ ] 报告中可见 renderer version、template version 和生成时间。
- [ ] public example 模式下，报告不得泄露维护者本机绝对路径。
- [ ] `04_reports/` 同时保留生成该 HTML 所用的原始 spec 副本和 normalized JSON，
      便于复现、审阅和调试。

## 5. 原生 HTML 子报告检查

- [ ] native HTML 子报告尽量使用原程序生成的 HTML，不用手写 proxy page 替代。
- [ ] bundler 在 `embedded_html_reports.tsv` 或等价 validation JSON 中记录每个 native HTML 子报告。
- [ ] 单文件 MultiQC/FastQC 风格报告在 payload capture 后应保持 byte-identical 或 hash-identical；
      除非有文档说明必要转换。
- [ ] HTML bundle 目录会内联离线阅读必需的本地 CSS、CSS `url(...)`、图片、`srcset`、
      `poster` 和本地脚本。
- [ ] 已知 legacy fastp HTML 中的远程 `plotly-1.2.0.min.js` loader 被替换为 renderer
      打包的本地 runtime，原始远程 fallback loader 被移除，报告可离线打开。
- [ ] 子报告从单文件主报告中以独立本地页面打开；普通左键点击应立即打开新本地页面并显示
      loading 状态，再注入已内嵌 payload，避免大报告重新加载整份主 HTML 后才显示子报告。
      same-file hash route 作为中键、复制链接、无 JS 或回退路径保留。
- [ ] 嵌入成功或 warning 状态的 native HTML 子报告在同一张 `subreport-card` 内同时提供
      same-file embedded 打开入口和源 HTML 相对链接；不能拆成两个卡片，也不能只保留其中一个。
- [ ] 源 HTML、plot raw 等源文件链接按最终报告 HTML 所在目录计算相对路径，例如
      `04_reports/report.html` 指向 `../03_results/...`；不能把 spec 中相对 root 的路径
      直接原样写进 `href`。
- [ ] 子报告脚本在子报告 document 中执行，不在主报告 document 中执行。
- [ ] JavaScript-heavy QC 报告默认打开策略不使用顶层 `blob:`、iframe 或 `srcdoc`；
      如需例外，必须有文档和测试。
- [ ] fastp/Plotly 类 fixture 不能只因页面非空就算通过；需要检查 modebar 位置、
      hover layer 是否存在，以及普通浏览器或记录过的视觉 QA 中至少一个 hover label。
- [ ] smoke 必须直接解析 `embedded-subreports-data` payload，确认 MultiQC/FastQC/fastp 等
      payload 非空且 fastp payload 不含远程 `<script src=...>` 或 `document.write` fallback。
- [ ] 巨大或浏览器不兼容 HTML 报告标记为 `warn`、`skipped` 或 `linked`；
      renderer 不能假装不完整嵌入已经成功。

## 6. 视觉 QA 检查

- [ ] 渲染输出使用 `repos/apps/templates/flow-report/scripts/check-rendered-report.py` 检查。
- [ ] publish-ready 前，每个 fixture family 至少打开一个生成报告进行人工或浏览器自动化检查。
- [ ] 左侧 sidebar 顺序与右侧 section 自上而下顺序一致。
- [ ] 嵌套 sidebar group 只展开当前 active major section。
- [ ] sidebar active state 随阅读顺序向前推进，不跳回旧 parent section。
- [ ] 语言切换无需刷新即可工作。
- [ ] 语言切换控件只包住中英两个按钮，不横向撑满一整行。
- [ ] reading guide / 如何阅读本报告的左右两栏以内容高度对齐，不允许左侧卡片被右侧状态列
      强行拉伸出大面积空白；四个快速阅读步骤应跟 review-first 卡片同属左侧语义列，
      不应被放到左右两栏下方形成额外空白。
- [ ] plot card、table card、warning card 和 subreport card 与模板风格一致。
- [ ] 子报告打开按钮是紧凑的内容宽度控件。
- [ ] 同类 card 的内部相对布局由 renderer 统一固定：标题/路径/状态在上方，主要数据在中部，
      操作按钮默认贴近卡片左下角；按钮不得因为路径长短、表格行数或模型数量漂移到中间或右侧。
- [ ] 窄视口下移动端布局仍可阅读。
- [ ] print/PDF 样式在可行时避免把主要 card 生硬切开。

## 7. 真实报告回归矩阵

- [ ] `ngs-qc` fixture 可渲染包含 MultiQC、fastp、FastQC native subreport 入口的报告。
- [ ] `bam-qc` fixture 可渲染包含 samtools/mosdepth 摘要和 native MultiQC 入口的报告。
- [ ] `phylogeny` fixture 可从 PNG 和 SVG 输入渲染树图卡片。
- [ ] `rnaseq-reference` fixture 可渲染 RNA-seq dashboard、DE 图、富集图、
      interpretation companion link、MultiQC/FastQC 和 Qualimap bundle。
- [ ] `rnaseq-denovo` fixture 可渲染 de novo assembly/expression/annotation section，
      且仍支持 DE/enrichment section。
- [ ] `chengdu-yuanda-report12` fixture 可渲染真实结构比较报告，包含 3D/NGL viewer、
      PDB payload、motif/site marker、静态结构图 lightbox 和模型/位点控制。
- [ ] `component-basic-report` 可在真实报告外壳中渲染 dashboard、status、quality gate、
      plot、table、code file 和 native HTML 子报告；不能退化为孤立组件 demo。
- [ ] `component-echarts-report` 可在真实表达/富集结果语境中渲染 volcano、MA、PCA 和
      ORA dotplot 四类交互图，且 ECharts runtime 只在该报告中按需内嵌。
- [ ] `component-tree-alignment-report` 可在系统发育语境中渲染 Newick 树、可复制树文件和
      FASTA/CLUSTAL 比对查看器。
- [ ] `component-igv-report` 可在基因组位点审阅语境中渲染 genome browser 配置和真实
      IGV runtime payload；如果只有 linked 模式，应清楚说明外部轨道审阅边界。
- [ ] `component-ngl-native-report` 可在结构生物学语境中复用真实 target/reference
      PDB 叠合、静态结构图、motif/site table 和相似性表，渲染 NGL/PDB 结构查看、
      完整 PDB `pdbText` payload、内置 fallback atoms、位点 marker 和静态图 lightbox。
- [ ] `component-media-layout-report` 使用真实横图、竖图和透明背景图覆盖 `plot_card`
      的 `layout="media"`，包含左右图片、`0.30/0.42/0.50/0.70` 比例、start/center、
      compact/normal/relaxed、长中英文说明、连续三张以上 media 卡片和
      media/grid/wide 混排。
- [ ] 生成的 fixture 报告在视觉和能力上不低于复制来的 baseline 或来源路径中记录的现有报告。
- [ ] 记录回归输出体量；接近 GitHub 50 MB 建议线的报告需要显式 review。

## 7.5 组件抽象回归检查

- [ ] renderer 自己生成的按钮、表头、状态、空数据、提示说明和 provenance 文案支持
      `languages` / `language_default` 声明式多语言；默认中英双语，额外语言缺失翻译时
      可回退到默认语言、英文或中文。
- [ ] 原始表格值、文件路径、工具输出值不做自动机器翻译；需要多语言解释时由 spec 或
      上游 summary 提供。
- [ ] 同一 section 中连续 `plot_card` 自动形成图片网格，但 `table_preview`、
      `native_subreport` 等不同组件不能被混进同一个 plot grid。
- [ ] `plot_card` 图片保持稳定比例和合理最大高度，按钮不因卡片宽度变窄而折成竖排。
- [ ] `plot_card` 默认可打开大图 lightbox；lightbox 打开时整图先适配当前窗口，
      并支持关闭、Esc、放大、缩小、回到适配窗口，且图片仍以内嵌 data URI 交付。
- [ ] `plot_card layout="media"` 每张卡片独占一行并由 renderer 的 CSS Grid 实现；
      `image_position` 只允许 left/right，`media_vertical_align` 只允许 start/center，
      `media_gap` 只允许 compact/normal/relaxed；不能把 media 卡片塞入普通 plot grid。
- [ ] `media_image_ratio` 默认 `0.42`，只接受 `0.25–0.70` 内的有限数值；字符串、NaN、
      无穷值和越界值必须 lint 失败，renderer 只能把校验后的数值转换为 CSS Grid 比例，
      TOML 不接受任意 CSS 表达式。
- [ ] media 两栏都必须 `min-width: 0`，图片必须保持原始比例、`object-fit: contain` 且不裁切；
      长中英文标题、连续英文字符串、长链接和操作按钮必须留在卡片内并可合理换行。
- [ ] media 响应式视觉检查固定覆盖 `1440/1280/820/768/390px`：`820px` 及以下始终
      图片在前、文字在后，忽略桌面比例，不得出现横向滚动、文字重叠、图片裁切或按钮丢失；
      `grid`、`wide` 历史 fixture 必须同时回归，打印样式不得切断单张 media 卡片。
- [ ] 大图 lightbox 打开时必须锁住背后报告页面滚动；在弹层、图片或已适配窗口状态下滚轮
      不应导致背景页面上下滚动，放大后滚轮只作用于弹层内图片滚动区域。
- [ ] `interactive_plot` 只能用固定组件和 TOML 字段声明，不允许 flow 私自写 Plotly/ECharts
      HTML 或自带 JS；源 TSV/CSV、图形类型和默认阈值必须进入 spec。
- [ ] `interactive_plot` 前端控件只筛选、分组、着色和调整显示数量，不能重新计算 DE、ORA、
      PCA、聚类或其它统计结果；文档中必须说明这些控件是查看层语义。
- [ ] `interactive_plot` 的最终 HTML 必须内嵌 ECharts runtime 和 compact JSON payload；
      不使用该组件的普通报告不得携带 ECharts runtime；Plotly 只用于 legacy fastp HTML
      远程 loader 的离线兼容替换。
- [ ] `interactive_plot` 的控制面板、图例和统计摘要必须由 renderer 分区布局；展开控制面板
      不得改变 ECharts canvas 高度，不得把右侧栏拉成需要滚动才能读完的长柱；展开控件
      必须使用紧凑多列布局，不能变成长侧栏或单列长表单。
- [ ] `interactive_plot` 阈值变化只允许改变分类、颜色、大小或过滤后的显示集合；
      火山图/MA 图点坐标不能因为跨 series 动画、progressive 重绘或缺少稳定点 ID
      出现“绕圈”“转向”式移动。
- [ ] `interactive_plot` 视觉检查至少覆盖火山图/MA、PCA scatter 和 ORA dotplot：
      坐标轴标签不能被截断，长 term 名称应短标签显示并在 hover 中保留完整文本，
      PCA 必须来自已计算坐标表，控件、图例、固定坐标范围和统计摘要应可用。
- [ ] `table_preview` 支持 `preview_rows`、`default_state`、`embed_full`、
      `max_embed_rows` 和 `max_embed_bytes`；表格以正文内可折叠卡片呈现，先显示紧凑
      预览，边界内再提供同卡片、同一张表的完整表格查看器；展开按钮只能在原表中显示/
      隐藏预览外的行，不能生成第二张 full table、modal 表格、remaining-row 表格或
      detached widget；完整查看器必须支持上下滚动、宽表横向滚动到最右列、行搜索、表头
      排序、单元格展开和完整值复制；宽表还应显示紧凑的左/右滚动按钮，不能只依赖用户设备
      支持横向滚轮或触控板手势；`default_state` 控制卡片初始打开/收起以及完整表是否默认
      展开，`preview_rows` 作为预览行数和不可内嵌时的 fallback 行数。
- [ ] `table_preview` 和 `quality_gate_table` 把 `note_en`/`note_zh`、
      `criterion_en`/`criterion_zh`、`body.en`/`body.zh` 等语言成对列折叠成一个
      多语言逻辑列；英文模式不能显示中文-only 表格内容，中文模式也不能显示英文-only
      表格内容。
- [ ] `table_preview` 对超长单元格使用紧凑预览和可展开完整查看器，避免 ORA `geneID`
      等长值把一行撑成大空白；省略号只能作为紧凑显示，完整值必须可通过原地完整表格、
      单元格展开、双击复制或源文件链接访问。
- [ ] `smoke.sh` / `test-real-run.sh` 必须强制检查 table 组件回归：存在横向滚动约束
      `overflow-x:auto` / `max-inline-size:100%` / `min-inline-size:0`，存在
      `data-preview-hidden` 原地隐藏行，且不存在旧的 `full-table-scroll`、
      `table-full-panel`、`table-remaining-toggle`、`table-expand-bar`、
      `table-expand-control-row` 或 `data-table-modal` 结构，并检查宽表存在
      `data-table-scroll-controls` / `data-table-scroll-right`。
- [ ] `code_file` 组件可用于 Newick 树、短配置、命令片段、小 JSON 等文本产物；需要复制
      复用的短文本应直接展示并提供 copy 按钮。
- [ ] 基础卡片、文件类别、路径、表格单元格、callout、子报告资源等底层组件必须默认
      安全换行；长文件名、长路径、长 ID 或长表格值不能溢出卡片或页面边界。
- [ ] 超过体积或行数边界的大表格不会被强行内嵌，必须显示 linked/truncated 边界说明。
- [ ] `native_subreport` 卡片采用统一结构，按钮固定在卡片底部左侧，不随路径长短乱跳。
- [ ] `native_subreport` 的内嵌入口和源 HTML 链接共享同一个底部动作区；
      `embed_policy=never` 时只显示源/外部链接，但仍沿用同一张卡片结构。
- [ ] `native_subreport` 的普通点击路径会使用即时 blank/loading 页面打开内嵌 payload；
      大型 standalone 报告不能因为新标签页重复载入主报告而出现明显空白等待。
- [ ] `native_subreport.embed_policy` 支持并测试 `auto`、`always` 和 `never` 的语义：
      `auto` 尽量内嵌，`always` 对未解析本地资源失败，`never` 只保留外部链接和索引。
- [ ] 多页本地 HTML 报告可通过 `embed_linked_pages=true` 或 `pages=[...]` 嵌入子页面；
      内部本地 HTML 链接会改写为同一个 HTML 文件内的 subreport hash。
- [ ] 左侧目录使用 section 作为父级、component 作为子级；滚动时只展开当前父级，
      active 状态按右侧内容顺序平滑推进。

## 8. Runtime 和 Docker 检查

- [ ] Docker image 只包含报告渲染依赖，不包含无关生物学分析工具。
- [ ] 镜像中的 `report-render render`、`report-render validate-*`、
      `report-render init`、`report-render new` 和 `report-render components` 可离线工作。
- [ ] Plotly、NGL、3Dmol.js、ECharts、Mol*、Cytoscape.js、IGV.js 等 runtime pack
      有版本、来源、license、checksum、体积和支持组件记录，并且只在组件需要时嵌入。
- [ ] 第三方 JavaScript/CSS/runtime license 已记录。
- [ ] Docker 镜像可以携带可选 runtime pack，但普通报告不使用对应组件时，最终 HTML
      不得嵌入这些 runtime。
- [ ] PDB/结构查看、基因组轨道、网络图等高级查看能力必须作为固定组件实现，不能通过
      raw HTML 或 flow 私有 JS 绕过 renderer 组件契约。
- [ ] `tree_viewer` 必须从 Newick 源文件生成内联 SVG 树图，并保留可复制 Newick 文本；
      真实 phylogeny fixture 必须覆盖该组件，不能只用静态 PNG/SVG 树图替代。
- [ ] `sequence_alignment` 必须从 FASTA/CLUSTAL 源文件生成多序列比对查看器，并保留
      源比对文本；真实 phylogeny fixture 必须覆盖该组件，不能只用表格或截图替代。
- [ ] `tree_viewer` 和 `sequence_alignment` 只展示已有结果，不运行 MAFFT、trimAl、
      IQ-TREE、FastTree 或其它分析工具。
- [ ] `genome_browser runtime="igv"` 必须内嵌 IGV runtime 和固定 JSON 配置；大型
      FASTA/BAM/VCF/BigWig/CRAM 及其索引默认不内嵌，需通过外部 URL 或用户环境提供。
- [ ] `genome_browser` 支持小型本地 reference/track 资产内嵌：`embed_reference = true`
      会把本地 FASTA/FAI 记录到资产索引并编译成 data URI；`embed_tracks = true` 或
      track 级 `embed = true` 会把本地 BED/GFF/bedGraph 等小轨道内嵌。大轨道默认外部化。
- [ ] `genome_browser` 如需同时提供 embedded 和 linked 审阅，必须使用同一个组件的
      `viewer_modes = ["embedded", "linked"]` 并在报告内切换；不得把同一组轨道拆成
      两个重复卡片。如果只声明一个模式，则不显示切换按钮，只说明当前模式。
- [ ] `genome_browser` 的初始 HTML 必须先显示可审计配置面板；JS/IGV 可用时再升级为
      交互式浏览器。最终报告不能长期停留在“正在加载基因组浏览器”的空白框。
- [ ] `genome_browser` embedded 模式尝试启动 IGV 时，必须保留超时/失败 fallback；
      `createBrowser` 抛错、promise reject 或 runtime 缺失都必须回到同卡片
      配置面板，不能留下空白 stage。
- [ ] IGV 源码树 test shim 只能用于 smoke/interface 测试；真实视觉验收和
      `tests/test-real-run.sh` 需要发布镜像内 runtime 或源码树 vendored runtime pack，
      不能用 shim 通过，也不能在 real-run 中联网补 JS。
- [ ] `genome_browser` 不负责 read mapping、variant calling、coverage 计算或 genome
      indexing；报告必须保留关键静态图/表或文件索引作为可审计兜底。
- [ ] `structure_viewer` 的 PDB 坐标 payload 只在组件被使用时嵌入；普通报告不得嵌入
      PDB 文本或第三方 3D runtime。
- [ ] `structure_viewer` 组件的最终 HTML 必须包含可解析的结构 payload JSON；
      `runtime="ngl"` 时 payload 中必须包含 `models` 和每个可加载模型的 `pdbText`，
      浏览器查看时不得再依赖外部 PDB 文件或额外 JSON 配置文件。
- [ ] `structure_viewer runtime="ngl"` 的 per-model 颜色必须由 TOML/manifest 显式声明并
      编译成 NGL uniform color representation；不能依赖 PDB 文件、静态图或浏览器默认配色。
- [ ] 如果 `structure_viewer` 声明 `site_groups` 或 `site_table`，最终 HTML payload 必须包含
      `siteGroups`，浏览器中应在指定 model 上显示 motif/活性位点/结构残基 marker；
      位点 marker 不能只存在于静态图中。
- [ ] `structure_viewer runtime="ngl"` 必须提供单 HTML 内的交互控制面板，至少支持模型显示
      开关、site group 显示开关、site marker 球大小和透明度调节；这些控件只能改变浏览器
      查看状态，不能修改 payload、源文件或 provenance。
- [ ] NGL 不可用或初始化失败时，fallback viewer 必须明确标注为
      内置 trace/fallback；不能继续显示 `cartoon`、`surface` 等 NGL representation 选项，
      以免把轻量 CA trace 误认为真实 NGL/PyMOL cartoon。
- [ ] NGL 交互控制面板默认收起；如需默认展开，只能通过组件级 TOML 字段
      `controls_open = true` 显式开启。
- [ ] `structure_viewer` 的可视顺序必须稳定：模型/分数/来源摘要在上方，3D viewer 和静态图在
      中间，viewer 控制面板紧贴 3D viewer 下方；不能让摘要卡片隔在 3D 图和控制参数之间。
- [ ] motif/位点表驱动的结构报告必须检查 `site_table` 已作为 table asset 记录；
      不允许最终 HTML 运行时再读取外部 TSV/JSON/PDB 配置。
- [ ] `structure_viewer` 和表格、图片网格、子报告网格等相邻组件之间的距离由 renderer
      CSS 统一控制；不能要求每个 TOML 手动插入空白组件、额外 section 或私有样式。
- [ ] `structure_viewer runtime="ngl"` 使用镜像内固定版本 NGL runtime；源码本地 smoke
      如用 shim，必须明确只用于离线接口测试，不能把 shim 当生产 runtime。
- [ ] `test-real-run.sh` / 正式视觉验收不得使用 NGL shim。若源码树没有真实
      `ngl.js`，真实结构 fixture 必须硬失败并提示使用发布镜像或准备源码树 runtime pack。
      只有 smoke/interface 测试才能显式使用 shim。
- [ ] NGL 生产 runtime 必须是 standalone browser bundle（当前为 `dist/ngl.js`）；
      `dist/ngl.umd.js` 这类外置 `three/chroma/signals/sprintf` 的包必须被 renderer 和
      real-run 测试拒绝，不能生成会显示 “NGL runtime unavailable” 的假阳性报告。
- [ ] 含 `runtime="ngl"` 的最终报告必须能证明真实 NGL runtime 已内嵌，而不是只出现
      `TAFFISH_NGL_TEST_SHIM` 文案；普通报告不得携带 NGL runtime。
- [ ] `runtime="ngl"` 报告保留静态结构图和源 PDB 链接作为 WebGL/runtime 失败时的可读兜底；
      静态结构图必须走与 `plot_card` 一致的大图 lightbox，而不是裸 `<img>`。
- [ ] NGL viewer 初始化后必须主动处理 stage resize/render/autoView；视觉验收需要确认
      左侧动态 viewer 显示真实结构而不是空白框或 test shim 文案。
- [ ] 新增 runtime pack 前必须有真实 fixture 或明确的多 flow 复用需求；license 不完整时
      不能进入发布镜像。
- [ ] tool 不通过 TAFFISH command-mode 暴露 helper 命令；如未来需要 helper，
      也应先判断是否属于 `report-render` 子命令。
- [ ] smoke 使用小型自包含 fixture，不需要网络。
- [ ] formal 或 real-run test 可以把较大的 fixture 报告渲染到 ignored 输出目录供人工检查。

## 9. 发布就绪检查

- [ ] `taf check` 通过。
- [ ] Docker build 在声明平台上通过。
- [ ] `taf build` 通过。
- [ ] wrapper `--help` 和 `--version` 可用。
- [ ] `taf build` 后至少测试一个非 `-` 开头子命令，例如
      `target/taf-taffish-report-render-v... components`，确认没有被 command mode 截走。
- [ ] renderer 的 `schema`、`components`、`validate-spec`、`validate-html`、`init`、
      `new`、`render`、`component-doc`、`lint`、`explain`、`migrate`、
      `inspect-html` 和 `list-assets` 命令在实现后由 smoke 或 formal 覆盖。
- [ ] README 说明 fixed-component model、TOML/JSON 输入、standalone 输出和非目标。
- [ ] `docs/help.md` 保持终端手册风格且简洁。
- [ ] `release.md` 说明 schema/component/template 兼容等级。
- [ ] testdata fixture set 与当前报告 contract 保持同步。
- [ ] 交还前清理临时生成报告、`.taf-*` 目录和 `target/` wrapper artifact。
