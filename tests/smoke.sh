#!/usr/bin/env bash
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
app_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
hub_root=$(CDPATH= cd -- "$app_root/../../../../.." && pwd)

export PYTHONPATH="$app_root/python"
renderer="$app_root/bin/report-render"
render_root="$app_root/tests/smoke-out"
outdir="$render_root/ngs-qc"
report="$outdir/04_reports/taffish_report.html"

rm -rf "$render_root"
mkdir -p "$render_root"

echo "[SMOKE] version and components"
"$renderer" --version | grep -Fx "taffish-report-render 0.3.0-r1" >/dev/null
"$renderer" components | grep -F "native_subreport" >/dev/null
"$renderer" components | grep -F "code_file" >/dev/null
"$renderer" components | grep -F "structure_viewer" >/dev/null
"$renderer" components | grep -F "interactive_plot" >/dev/null
"$renderer" components | grep -F "native_subreport_collection" >/dev/null
"$renderer" schema | grep -F '"native_subreport_collection"' >/dev/null
"$renderer" schema | grep -F '"structure_viewer"' >/dev/null
"$renderer" schema | grep -F '"interactive_plot"' >/dev/null
"$renderer" component-doc table_preview | grep -F "table_preview renders" >/dev/null
"$renderer" component-doc structure_viewer | grep -F "structure_viewer embeds" >/dev/null
"$renderer" component-doc interactive_plot | grep -F "interactive_plot embeds" >/dev/null
"$renderer" component-doc plot_card | grep -F "layout supports grid, wide, and media" >/dev/null
"$renderer" component-doc plot_card | grep -F "note_items" >/dev/null
"$renderer" schema | grep -F '"media_image_ratio"' >/dev/null
"$renderer" schema | grep -F '"note_items"' >/dev/null
"$renderer" schema | grep -F '"boundary"' >/dev/null

echo "[SMOKE] structured-note unit and round-trip contract"
python3 "$app_root/tests/test_structured_notes.py"

echo "[SMOKE] init stdout and demo workspace"
"$renderer" init > "$render_root/report.template.toml"
grep -F 'template = "taffish-flow-report"' "$render_root/report.template.toml" >/dev/null
grep -F '[[sections.note_items]]' "$render_root/report.template.toml" >/dev/null
"$renderer" new --outdir "$render_root/demo" --force >/dev/null
"$renderer" validate-spec --spec "$render_root/demo/report.toml"
"$renderer" lint --spec "$render_root/demo/report.toml" --root "$render_root/demo"
"$renderer" explain --spec "$render_root/demo/report.toml" --root "$render_root/demo" | grep -F "components:" >/dev/null
"$renderer" explain --spec "$render_root/demo/report.toml" --root "$render_root/demo" | grep -F "note_items=1 kinds=boundary" >/dev/null
"$renderer" migrate --spec "$render_root/demo/report.toml" --root "$render_root/demo" --format json > "$render_root/demo/report.normalized.preflight.json"
grep -F '"type": "plot_card"' "$render_root/demo/report.normalized.preflight.json" >/dev/null
"$renderer" render \
  --spec "$render_root/demo/report.toml" \
  --root "$render_root/demo" \
  --out "$render_root/demo/04_reports/report.html" \
  --force \
  --validate
grep -F "data-open-image" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "data-image-modal" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F 'data-structured-note-count="1"' "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "standalone_html" "$render_root/demo/04_reports/report.html" >/dev/null
"$renderer" inspect-html "$render_root/demo/04_reports/report.html" --validate | grep -F "template: taffish-flow-report" >/dev/null
"$renderer" list-assets "$render_root/demo/04_reports" | grep -F "renderer-html" >/dev/null
grep -F "table-expandable-scroll" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "data-table-scroll-controls" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "data-table-scroll-right" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "data-table-toolbar" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "is-table-expanded" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "overflow-x: auto;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "overflow-y: auto;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "min-inline-size: 0;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "max-inline-size: 100%;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "width: max-content;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "min-width: 100%;" "$render_root/demo/04_reports/report.html" >/dev/null
grep -F "white-space: nowrap;" "$render_root/demo/04_reports/report.html" >/dev/null
if grep -F "Show remaining" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected remaining-row expansion label in demo report" >&2
  exit 1
fi
if grep -F "展开剩余" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected remaining-row expansion label in demo report" >&2
  exit 1
fi
if grep -F "table-remaining-toggle" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected remaining-row toggle in demo report" >&2
  exit 1
fi
if grep -F "table-expand-bar" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected table expand bar in demo report" >&2
  exit 1
fi
if grep -F "table-expand-control-row" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected table-row expand control in demo report" >&2
  exit 1
fi
if grep -F "full-table-scroll" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected duplicate full-table scroll pane in demo report" >&2
  exit 1
fi
if grep -F "table-full-panel" "$render_root/demo/04_reports/report.html" >/dev/null; then
  echo "unexpected second-table full panel in demo report" >&2
  exit 1
fi

echo "[SMOKE] collection components"
mkdir -p "$render_root/collection/03_results/plots" "$render_root/collection/03_results/tables" "$render_root/collection/03_results/html" "$render_root/collection/04_reports"
cat > "$render_root/collection/04_reports/key_metrics.tsv" <<'TSV'
metric	value
items	3
TSV
cat > "$render_root/collection/04_reports/plots.tsv" <<'TSV'
id	image	title_en	title_zh	note_en	note_zh
plot1	03_results/plots/plot1.svg	Plot One	图一	Demo plot	示例图片
TSV
cat > "$render_root/collection/04_reports/tables.tsv" <<'TSV'
id	source	title_en	title_zh
small	03_results/tables/small.tsv	Small table	小表格
TSV
cat > "$render_root/collection/04_reports/workflow.tsv" <<'TSV'
step_en	step_zh	status_en	status_zh	note_en	note_zh
Input control	输入控制	PASS	通过	Freeze the input identity	冻结输入身份
Report	报告生成	PASS	通过	Render a standalone report	生成单文件报告
TSV
cat > "$render_root/collection/04_reports/html.tsv" <<'TSV'
id	path	kind	title_en	title_zh
html1	03_results/html/native.html	html	Native page	原生页面
TSV
cat > "$render_root/collection/03_results/tables/small.tsv" <<'TSV'
a	b
1	2
3	4
TSV
cat > "$render_root/collection/03_results/plots/plot1.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#098"/></svg>
SVG
cat > "$render_root/collection/03_results/html/native.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>Native</title></head><body><h1>Native</h1></body></html>
HTML
cat > "$render_root/collection/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "collection-demo"
flow_version = "0.1.0"
analysis_mode = "demo"
title.en = "Collection Demo"
title.zh = "集合示例"

[[sections]]
id = "overview"
kind = "overview"
title.en = "Overview"
title.zh = "概览"

[[sections.components]]
type = "dashboard_cards"
id = "cards"
source = "04_reports/key_metrics.tsv"

[[sections]]
id = "collections"
kind = "overview"
title.en = "Collections"
title.zh = "集合"

[[sections.components]]
type = "plot_collection"
id = "plots"
source = "04_reports/plots.tsv"

[[sections.components]]
type = "table_collection"
id = "tables"
source = "04_reports/tables.tsv"
preview_rows = 1
embed_full = true

[[sections.components]]
type = "native_subreport_collection"
id = "html"
source = "04_reports/html.tsv"
embed_policy = "auto"

[[sections.components]]
type = "workflow_diagram"
id = "localized-workflow"
source = "04_reports/workflow.tsv"
note.en = "Localized workflow component explanation."
note.zh = "双语流程组件说明。"

[[sections.components]]
type = "table_preview"
id = "explained-table"
source = "03_results/tables/small.tsv"
preview_rows = 1
embed_full = true
note.en = "Column a is the record identifier; column b is its value."
note.zh = "a 列是记录编号；b 列是对应数值。"

[[sections.components]]
type = "plot_card"
id = "wide-top-plot"
image = "03_results/plots/plot1.svg"
layout = "wide"
note_position = "top"
title.en = "Wide plot"
title.zh = "全宽图片"
note.en = "The explanation is shown above the image."
note.zh = "解释文字显示在图片上方。"
TOML
"$renderer" validate-spec --spec "$render_root/collection/report.toml" --root "$render_root/collection"
"$renderer" lint --spec "$render_root/collection/report.toml" --root "$render_root/collection"
"$renderer" migrate --spec "$render_root/collection/report.toml" --root "$render_root/collection" --format json > "$render_root/collection/expanded.json"
grep -F '"type": "plot_card"' "$render_root/collection/expanded.json" >/dev/null
grep -F '"type": "table_preview"' "$render_root/collection/expanded.json" >/dev/null
grep -F '"type": "native_subreport"' "$render_root/collection/expanded.json" >/dev/null
"$renderer" render \
  --spec "$render_root/collection/report.toml" \
  --root "$render_root/collection" \
  --out "$render_root/collection/04_reports/report.html" \
  --force \
  --validate
grep -F "plots-plot1" "$render_root/collection/04_reports/report.normalized.json" >/dev/null
grep -F 'class="component-intro"' "$render_root/collection/04_reports/report.html" >/dev/null
grep -F 'class="plot-grid plot-grid-wide"' "$render_root/collection/04_reports/report.html" >/dev/null
grep -F 'plot-note-top' "$render_root/collection/04_reports/report.html" >/dev/null
grep -F 'data-i18n-lang="zh">输入控制<' "$render_root/collection/04_reports/report.html" >/dev/null
grep -F 'data-i18n-lang="en">Input control<' "$render_root/collection/04_reports/report.html" >/dev/null
grep -F "tables-small" "$render_root/collection/04_reports/report.normalized.json" >/dev/null
grep -F "html-html1" "$render_root/collection/04_reports/report.normalized.json" >/dev/null

echo "[SMOKE] plot_card media layout"
mkdir -p "$render_root/media/03_results/figures" "$render_root/media/04_reports"
cat > "$render_root/media/03_results/figures/horizontal.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 240"><rect width="640" height="240" fill="#eef8f6"/><circle cx="150" cy="120" r="72" fill="#0b8f82"/><path d="M260 70h300v28H260zm0 58h220v28H260z" fill="#17343c"/></svg>
SVG
cat > "$render_root/media/03_results/figures/portrait.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 520"><rect width="260" height="520" fill="#f8f4e8"/><path d="M40 450L130 60l90 390z" fill="#315b9b"/><circle cx="130" cy="255" r="42" fill="#d18b00"/></svg>
SVG
cat > "$render_root/media/03_results/figures/transparent.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 300"><g fill="none" stroke-width="18"><path d="M50 240C120 40 220 40 270 150s110 90 160-80" stroke="#0b8f82"/><circle cx="270" cy="150" r="62" stroke="#8b5cf6"/></g></svg>
SVG
cat > "$render_root/media/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
languages = ["en", "zh"]
language_default = "zh"

[project]
flow_name = "media-layout-regression"
flow_version = "0.3.0-r1"
analysis_mode = "component-regression"
title.en = "Media Layout Regression"
title.zh = "媒体布局回归测试"

[[sections]]
id = "media"
kind = "analysis"
title.en = "Responsive media cards"
title.zh = "响应式媒体卡"

[[sections.components]]
type = "plot_card"
id = "media-default"
image = "03_results/figures/horizontal.svg"
layout = "media"
title.en = "Default 0.42 image ratio"
title.zh = "默认 0.42 图片比例"
note.en = "The default media card keeps the figure next to its explanation."
note.zh = "默认媒体卡让图片与解释保持相邻。"
zoom = true
default_fit = "contain"

[[sections.components]]
type = "plot_card"
id = "media-ratio-030"
image = "03_results/figures/portrait.svg"
layout = "media"
image_position = "right"
media_image_ratio = 0.30
media_vertical_align = "center"
media_gap = "compact"
title.en = "Portrait figure on the right"
title.zh = "右侧竖版图片"
note.en = "A portrait image uses a narrow image track and vertically centered alignment."
note.zh = "竖版图片使用较窄图片栏，并在纵向居中对齐。"

[[sections.components]]
type = "plot_card"
id = "media-ratio-050"
image = "03_results/figures/transparent.svg"
layout = "media"
media_image_ratio = 0.50
media_gap = "relaxed"
title.en = "Transparent figure with a deliberately long explanatory title that must wrap inside the copy column"
title.zh = "带有较长说明标题且必须在文字栏内安全换行的透明背景图片"
note.en = "Long links and continuous strings must remain inside the card: https://taffish.github.io/reports/a/very/long/scientific/background/reference and ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ."
note.zh = "长链接和连续字符串必须留在卡片内部：https://taffish.github.io/reports/a/very/long/scientific/background/reference。"
caption.en = "Optional caption details appear after the main explanation."
caption.zh = "可选 caption 细节显示在主要说明之后。"

[[sections.components]]
type = "plot_card"
id = "media-ratio-070"
image = "03_results/figures/horizontal.svg"
layout = "media"
image_position = "right"
media_image_ratio = 0.70
media_vertical_align = "start"
media_gap = "normal"
title.en = "Wide image track boundary"
title.zh = "宽图片栏边界"
note.en = "The maximum supported image ratio remains within the parent width."
note.zh = "允许的最大图片比例仍保持在父容器宽度内。"

[[sections.components]]
type = "plot_card"
id = "legacy-grid"
image = "03_results/figures/horizontal.svg"
layout = "grid"
title.en = "Legacy grid card"
title.zh = "历史 grid 卡片"

[[sections.components]]
type = "plot_card"
id = "legacy-wide"
image = "03_results/figures/horizontal.svg"
layout = "wide"
note_position = "top"
title.en = "Legacy wide card"
title.zh = "历史 wide 卡片"
note.en = "The established wide layout remains unchanged."
note.zh = "既有 wide 布局保持不变。"
TOML
"$renderer" validate-spec --spec "$render_root/media/report.toml" --root "$render_root/media"
"$renderer" lint --spec "$render_root/media/report.toml" --root "$render_root/media" --strict --fail-on-warn
"$renderer" render \
  --spec "$render_root/media/report.toml" \
  --root "$render_root/media" \
  --out "$render_root/media/04_reports/report.html" \
  --force \
  --validate
media_report="$render_root/media/04_reports/report.html"
test "$(grep -o 'class="plot-media-stack"' "$media_report" | wc -l | tr -d ' ')" = "1"
test "$(grep -o 'class="plot-card plot-card-media' "$media_report" | wc -l | tr -d ' ')" = "4"
grep -F 'data-media-image-ratio="0.42"' "$media_report" >/dev/null
grep -F 'data-media-image-ratio="0.3"' "$media_report" >/dev/null
grep -F 'data-media-image-ratio="0.5"' "$media_report" >/dev/null
grep -F 'data-media-image-ratio="0.7"' "$media_report" >/dev/null
grep -F 'plot-media-image-right' "$media_report" >/dev/null
grep -F 'plot-media-align-center' "$media_report" >/dev/null
grep -F 'plot-media-gap-compact' "$media_report" >/dev/null
grep -F 'plot-media-gap-relaxed' "$media_report" >/dev/null
grep -F 'grid-template-areas: "image copy";' "$media_report" >/dev/null
grep -F '@media (max-width: 820px)' "$media_report" >/dev/null
grep -F 'grid-template-areas:' "$media_report" >/dev/null
grep -F 'data-i18n-lang="en">Default 0.42 image ratio<' "$media_report" >/dev/null
grep -F 'data-i18n-lang="zh">默认 0.42 图片比例<' "$media_report" >/dev/null
grep -F 'data-open-image="media-default"' "$media_report" >/dev/null
grep -F 'class="plot-grid"' "$media_report" >/dev/null
grep -F 'class="plot-grid plot-grid-wide"' "$media_report" >/dev/null
grep -F 'data:image/svg+xml;base64,' "$media_report" >/dev/null

make_invalid_media_spec() {
  local name="$1"
  local assignment="$2"
  local spec="$render_root/media/invalid-$name.toml"
  cat > "$spec" <<TOML
schema_version = "0.1"
template = "taffish-flow-report"
[project]
title.en = "Invalid media"
title.zh = "非法媒体参数"
[[sections]]
id = "invalid"
title.en = "Invalid"
title.zh = "非法"
[[sections.components]]
type = "plot_card"
id = "invalid-$name"
image = "03_results/figures/horizontal.svg"
layout = "media"
$assignment
TOML
  if "$renderer" lint --spec "$spec" --root "$render_root/media" > "$render_root/media/invalid-$name.log" 2>&1; then
    echo "expected media lint failure: $name" >&2
    exit 1
  fi
  grep -F "ERROR" "$render_root/media/invalid-$name.log" >/dev/null
}

make_invalid_media_spec "ratio-low" "media_image_ratio = 0.24"
make_invalid_media_spec "ratio-high" "media_image_ratio = 0.71"
make_invalid_media_spec "ratio-nan" "media_image_ratio = nan"
make_invalid_media_spec "ratio-inf" "media_image_ratio = inf"
make_invalid_media_spec "ratio-string" 'media_image_ratio = "0.42"'
make_invalid_media_spec "position" 'image_position = "middle"'
make_invalid_media_spec "vertical-align" 'media_vertical_align = "end"'
make_invalid_media_spec "gap" 'media_gap = "wide"'

cat > "$render_root/media/invalid-layout.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
[project]
title.en = "Invalid layout"
title.zh = "非法布局"
[[sections]]
id = "invalid"
title.en = "Invalid"
title.zh = "非法"
[[sections.components]]
type = "plot_card"
id = "invalid-layout"
image = "03_results/figures/horizontal.svg"
layout = "side-by-side"
TOML
if "$renderer" lint --spec "$render_root/media/invalid-layout.toml" --root "$render_root/media" > "$render_root/media/invalid-layout.log" 2>&1; then
  echo "expected unknown plot_card layout lint failure" >&2
  exit 1
fi
grep -F "layout must be one of: grid, wide, media" "$render_root/media/invalid-layout.log" >/dev/null

cat > "$render_root/media/invalid-media-field-on-grid.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
[project]
title.en = "Invalid grid"
title.zh = "非法 grid"
[[sections]]
id = "invalid"
title.en = "Invalid"
title.zh = "非法"
[[sections.components]]
type = "plot_card"
id = "invalid-grid"
image = "03_results/figures/horizontal.svg"
layout = "grid"
media_image_ratio = 0.42
TOML
if "$renderer" lint --spec "$render_root/media/invalid-media-field-on-grid.toml" --root "$render_root/media" > "$render_root/media/invalid-media-field-on-grid.log" 2>&1; then
  echo "expected media-only field lint failure on grid layout" >&2
  exit 1
fi
grep -F "media-only fields require layout=media" "$render_root/media/invalid-media-field-on-grid.log" >/dev/null

echo "[SMOKE] manifest-declared multilingual shell"
mkdir -p "$render_root/multilang/03_results" "$render_root/multilang/04_reports"
cat > "$render_root/multilang/03_results/metrics.tsv" <<'TSV'
metric	value
samples	3
TSV
cat > "$render_root/multilang/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
languages = ["en", "zh", "ja"]
language_default = "ja"

[project]
flow_name = "multilang-demo"
flow_version = "0.1.0"
analysis_mode = "demo"
title.en = "Multilingual report"
title.zh = "多语言报告"
title.ja = "多言語レポート"
subtitle.en = "Language switch smoke."
subtitle.zh = "语言切换 smoke。"
subtitle.ja = "言語切替 smoke。"

[[sections]]
id = "overview"
kind = "overview"
title.en = "Overview"
title.zh = "概览"
title.ja = "概要"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "03_results/metrics.tsv"
title.en = "Summary"
title.zh = "摘要"
title.ja = "要約"
TOML
"$renderer" validate-spec --spec "$render_root/multilang/report.toml"
"$renderer" render \
  --spec "$render_root/multilang/report.toml" \
  --root "$render_root/multilang" \
  --out "$render_root/multilang/04_reports/report.html" \
  --force \
  --validate
grep -F 'data-lang-toggle="ja"' "$render_root/multilang/04_reports/report.html" >/dev/null
grep -F 'html[data-lang="ja"] .report-i18n[data-i18n-lang="ja"]' "$render_root/multilang/04_reports/report.html" >/dev/null
grep -F 'data-i18n-lang="ja">多言語レポート' "$render_root/multilang/04_reports/report.html" >/dev/null
grep -F '<html lang="ja" data-lang="ja"' "$render_root/multilang/04_reports/report.html" >/dev/null
if grep -F 'if (lang !== "zh") lang = "en";' "$render_root/multilang/04_reports/report.html" >/dev/null; then
  echo "unexpected hard-coded en/zh language clamp in multilingual report" >&2
  exit 1
fi

echo "[SMOKE] interactive_plot component"
mkdir -p "$render_root/interactive/03_results/tables" "$render_root/interactive/04_reports"
cat > "$render_root/interactive/03_results/tables/de.tsv" <<'TSV'
gene_id	baseMean	log2FoldChange	pvalue	padj
geneA	100	2.5	0.0001	0.001
geneB	80	-2.1	0.0002	0.002
geneC	30	0.2	0.5	0.8
TSV
cat > "$render_root/interactive/03_results/tables/pca.tsv" <<'TSV'
sample	condition	PC1	PC2
WT_01	WT	-2.1	0.4
WT_02	WT	-1.8	-0.2
SNF2KO_01	SNF2KO	2.2	0.6
SNF2KO_02	SNF2KO	1.9	-0.5
TSV
cat > "$render_root/interactive/03_results/tables/ora.tsv" <<'TSV'
ID	Description	GeneRatio	BgRatio	pvalue	p.adjust	Count
GO:0001	rRNA processing [biological_process]	3/20	40/500	0.0001	0.001	3
GO:0002	cell wall organization [biological_process]	2/20	30/500	0.004	0.02	2
GO:0003	oxidative stress response [biological_process]	1/20	20/500	0.2	0.4	1
TSV
cat > "$render_root/interactive/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "interactive-demo"
flow_version = "0.1.0"
analysis_mode = "demo"
title.en = "Interactive plot demo"
title.zh = "交互图示例"

[[sections]]
id = "plots"
kind = "differential_expression"
title.en = "Interactive plots"
title.zh = "交互图"

[[sections.components]]
type = "interactive_plot"
id = "volcano"
kind = "volcano"
source = "03_results/tables/de.tsv"
default_padj = 0.05
default_log2fc = 1
point_size = 8
opacity = 0.8
color_up = "#d95f02"
color_down = "#2b8cbe"
color_ns = "#9aa8ad"
title.en = "Interactive volcano"
title.zh = "交互火山图"

[[sections.components]]
type = "interactive_plot"
id = "ma"
kind = "ma"
source = "03_results/tables/de.tsv"
default_padj = 0.05
default_log2fc = 1
point_size = 8
opacity = 0.8
title.en = "Interactive MA"
title.zh = "交互 MA 图"

[[sections.components]]
type = "interactive_plot"
id = "pca"
kind = "pca"
source = "03_results/tables/pca.tsv"
sample = "sample"
group = "condition"
pc1 = "PC1"
pc2 = "PC2"
point_size = 10
opacity = 0.86
title.en = "Interactive PCA"
title.zh = "交互 PCA 图"

[[sections.components]]
type = "interactive_plot"
id = "ora"
kind = "ora_dotplot"
source = "03_results/tables/ora.tsv"
default_padj = 0.05
top_n = 10
point_size = 9
opacity = 0.86
title.en = "Interactive ORA"
title.zh = "交互 ORA 图"
TOML
"$renderer" validate-spec --spec "$render_root/interactive/report.toml" --root "$render_root/interactive"
"$renderer" render \
  --spec "$render_root/interactive/report.toml" \
  --root "$render_root/interactive" \
  --out "$render_root/interactive/04_reports/report.html" \
  --force \
  --validate
grep -F "data-interactive-plot" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "data-interactive-plot-payload" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "data-taffish-runtime=\"echarts-6.1.0\"" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "window.echarts.init" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "data-plot-point-size" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "interactive-plot-legend" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "interactive-plot-stats" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F '"kind":"volcano"' "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F '"kind":"ma"' "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F '"kind":"pca"' "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F '"kind":"ora_dotplot"' "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "renderPcaPlot" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "Interactive PCA" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "animation: false" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "animationDurationUpdate: 0" "$render_root/interactive/04_reports/report.html" >/dev/null
grep -F "progressive: 0" "$render_root/interactive/04_reports/report.html" >/dev/null
python3 - "$render_root/interactive/04_reports/report.html" <<'PY'
from pathlib import Path
import sys
html = Path(sys.argv[1]).read_text()
start = html.index('<article class="interactive-plot-card"')
body = html[start:]
controls = body.index("interactive-plot-controls")
layout = body.index("interactive-plot-layout")
stats = body.index("interactive-plot-stats")
if not (controls < layout < stats):
    raise SystemExit("interactive_plot layout order must be controls -> chart layout -> stats")
if "interactive-plot-side\"><details" in body:
    raise SystemExit("interactive_plot controls must not live inside the side column")
PY

echo "[SMOKE] structure_viewer PDB component"
mkdir -p "$render_root/structure/03_results/pdb" "$render_root/structure/03_results/figures" "$render_root/structure/04_reports"
cat > "$render_root/structure/03_results/pdb/tiny.pdb" <<'PDB'
ATOM      1  N   ALA A   1      -3.000  -1.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1      -2.000   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1      -1.000   0.300   1.000  1.00 20.00           C
ATOM      4  O   ALA A   1      -0.600   1.400   1.100  1.00 20.00           O
ATOM      5  N   GLY A   2      -0.500  -0.700   1.700  1.00 20.00           N
ATOM      6  CA  GLY A   2       0.500  -0.500   2.700  1.00 20.00           C
ATOM      7  C   GLY A   2       1.800  -0.200   2.000  1.00 20.00           C
ATOM      8  O   GLY A   2       2.300   0.900   2.200  1.00 20.00           O
ATOM      9  N   SER A   3       2.300  -1.200   1.200  1.00 20.00           N
ATOM     10  CA  SER A   3       3.500  -1.100   0.400  1.00 20.00           C
TER
END
PDB
cat > "$render_root/structure/03_results/figures/tiny.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 160">
  <rect width="260" height="160" rx="12" fill="#f4f8f7"/>
  <path d="M36 110 C70 35 112 130 148 56 S212 92 230 38" fill="none" stroke="#087f74" stroke-width="10" stroke-linecap="round"/>
  <circle cx="36" cy="110" r="10" fill="#1d5fd7"/>
  <circle cx="230" cy="38" r="10" fill="#b7791f"/>
</svg>
SVG
cat > "$render_root/structure/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "structure-demo"
flow_version = "0.1.0"
analysis_mode = "structure"
title.en = "Structure viewer demo"
title.zh = "结构查看器示例"

[[sections]]
id = "structure"
kind = "structure"
title.en = "Structure Evidence"
title.zh = "结构证据"

[[sections.components]]
type = "structure_viewer"
id = "tiny-structure"
static_image = "03_results/figures/tiny.svg"
runtime = "builtin"
atom_filter = "ca"
height = 360
title.en = "Tiny PDB trace"
title.zh = "Tiny PDB 轨迹"
note.en = "A minimal PDB fixture rendered through the built-in lightweight viewer."
note.zh = "使用内置轻量查看器渲染的最小 PDB fixture。"

[[sections.components.models]]
id = "tiny"
pdb = "03_results/pdb/tiny.pdb"
color = "#087f74"
label.en = "Tiny model"
label.zh = "Tiny 模型"
TOML
"$renderer" validate-spec --spec "$render_root/structure/report.toml" --root "$render_root/structure"
"$renderer" lint --spec "$render_root/structure/report.toml" --root "$render_root/structure"
"$renderer" render \
  --spec "$render_root/structure/report.toml" \
  --root "$render_root/structure" \
  --out "$render_root/structure/04_reports/report.html" \
  --force \
  --validate
grep -F "data-structure-viewer" "$render_root/structure/04_reports/report.html" >/dev/null
grep -F "data-structure-payload" "$render_root/structure/04_reports/report.html" >/dev/null
grep -F "setupStructureViewers" "$render_root/structure/04_reports/report.html" >/dev/null
grep -F "03_results/pdb/tiny.pdb" "$render_root/structure/04_reports/report_files.tsv" >/dev/null
if grep -F 'data-taffish-runtime="ngl"' "$render_root/structure/04_reports/report.html" >/dev/null; then
  echo "unexpected NGL runtime in builtin structure report" >&2
  exit 1
fi
cat > "$render_root/structure/report-ngl.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "structure-ngl-demo"
flow_version = "0.1.0"
analysis_mode = "structure"
title.en = "NGL structure viewer demo"
title.zh = "NGL 结构查看器示例"

[[sections]]
id = "structure"
kind = "structure"
title.en = "NGL Structure Evidence"
title.zh = "NGL 结构证据"

[[sections.components]]
type = "structure_viewer"
id = "tiny-structure-ngl"
static_image = "03_results/figures/tiny.svg"
runtime = "ngl"
representation = "cartoon"
atom_filter = "ca"
height = 360
controls_open = true
title.en = "Tiny PDB NGL"
title.zh = "Tiny PDB NGL"

[[sections.components.models]]
id = "tiny"
pdb = "03_results/pdb/tiny.pdb"
color = "#087f74"
label.en = "Tiny model"
label.zh = "Tiny 模型"
TOML
"$renderer" validate-spec --spec "$render_root/structure/report-ngl.toml" --root "$render_root/structure"
TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS=1 \
TAFFISH_REPORT_RENDER_NGL_JS="$app_root/testdata/runtime/ngl-test-shim.js" \
"$renderer" render \
  --spec "$render_root/structure/report-ngl.toml" \
  --root "$render_root/structure" \
  --out "$render_root/structure/04_reports/report-ngl.html" \
  --force \
  --validate
grep -F 'data-taffish-runtime="ngl"' "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "TAFFISH_NGL_TEST_SHIM" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "data-structure-ngl-stage" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F '<details class="structure-controls" data-structure-controls open>' "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "pdbText" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "body.report-modal-open" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "syncModalScrollLock" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "overscroll-behavior: contain;" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F $'runtime\ttiny-structure-ngl\truntime-packs/ngl/ngl-test-shim.js' "$render_root/structure/04_reports/report_files.tsv" >/dev/null
grep -F ".structure-card + .structure-card" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "align-items: start;" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F ".structure-model-card > div" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
grep -F "margin-top: auto;" "$render_root/structure/04_reports/report-ngl.html" >/dev/null
if "$renderer" validate-html "$render_root/structure/04_reports/report-ngl.html" >/dev/null 2>&1; then
  echo "test-only NGL shim unexpectedly passed non-test HTML validation" >&2
  exit 1
fi
TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS=1 \
"$renderer" validate-html "$render_root/structure/04_reports/report-ngl.html"

echo "[SMOKE] bio viewer components"
mkdir -p "$render_root/bio/03_results/tree" "$render_root/bio/03_results/alignment" "$render_root/bio/04_reports"
cat > "$render_root/bio/03_results/tree/smoke.nwk" <<'NEWICK'
((sample_A:0.0123,sample_B:0.0188)node1:0.04,(sample_C:0.02,sample_D:0.031)node2:0.05)root;
NEWICK
cat > "$render_root/bio/03_results/alignment/smoke.fa" <<'FASTA'
>sample_A
ATGCCGTTAACCGGTTAA--
>sample_B
ATGCCGTTAACTGGTTAA--
>sample_C
ATGTCGTTAACTGGCTAA--
>sample_D
ATGTCGTTAACCGGCTAA--
FASTA
cat > "$render_root/bio/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "smoke"
language_default = "zh"

[project]
flow_name = "bio-viewer-smoke"
flow_version = "0.3.0-r1"
analysis_mode = "bio-viewers"
title.zh = "生信浏览器组件测试"
title.en = "Bio Viewer Component Smoke"
subtitle.zh = "测试 tree_viewer、sequence_alignment 和 genome_browser。"
subtitle.en = "Test tree_viewer, sequence_alignment, and genome_browser."

[[sections]]
id = "bio"
kind = "phylogeny"
title.zh = "生信浏览组件"
title.en = "Bioinformatics viewers"

[[sections.components]]
type = "tree_viewer"
id = "smoke-tree"
source = "03_results/tree/smoke.nwk"
height = 300
title.zh = "内嵌 Newick 树"
title.en = "Embedded Newick tree"

[[sections.components]]
type = "sequence_alignment"
id = "smoke-alignment"
source = "03_results/alignment/smoke.fa"
format = "fasta"
alphabet = "dna"
max_columns = 80
title.zh = "内嵌 FASTA 比对"
title.en = "Embedded FASTA alignment"

[[sections.components]]
type = "genome_browser"
id = "smoke-igv"
runtime = "igv"
data_mode = "external"
genome = "hg38"
locus = "chr1:1-1000"
height = 320
title.zh = "IGV 外部数据浏览器"
title.en = "IGV external-data browser"

[[sections.components.tracks]]
name = "Example BED"
type = "annotation"
format = "bed"
url = "https://example.invalid/tracks/example.bed"
TOML
"$renderer" validate-spec --spec "$render_root/bio/report.toml" --root "$render_root/bio"
TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS=1 \
TAFFISH_REPORT_RENDER_IGV_JS="$app_root/testdata/runtime/igv-test-shim.js" \
"$renderer" render \
  --spec "$render_root/bio/report.toml" \
  --root "$render_root/bio" \
  --out "$render_root/bio/04_reports/report.html" \
  --force \
  --validate
bio_report="$render_root/bio/04_reports/report.html"
grep -F 'data-tree-viewer' "$bio_report" >/dev/null
grep -F 'class="tree-viewer-svg"' "$bio_report" >/dev/null
grep -F 'data-sequence-alignment' "$bio_report" >/dev/null
grep -F 'class="alignment-row alignment-consensus"' "$bio_report" >/dev/null
grep -F 'data-genome-browser' "$bio_report" >/dev/null
grep -F 'data-taffish-runtime="igv"' "$bio_report" >/dev/null
grep -F "TAFFISH_IGV_TEST_SHIM" "$bio_report" >/dev/null
grep -F $'runtime\tsmoke-igv\truntime-packs/igv/igv-test-shim.js' "$render_root/bio/04_reports/report_files.tsv" >/dev/null
if "$renderer" validate-html "$bio_report" >/dev/null 2>&1; then
  echo "test-only IGV shim unexpectedly passed non-test HTML validation" >&2
  exit 1
fi
TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS=1 \
"$renderer" validate-html "$bio_report"

echo "[SMOKE] native_subreport embed policies"
mkdir -p "$render_root/policy/03_results/html" "$render_root/policy/04_reports"
cat > "$render_root/policy/03_results/html/native.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>Native payload</title></head><body><h1>Native payload</h1><a href="page2.html">open page 2</a></body></html>
HTML
cat > "$render_root/policy/03_results/html/page2.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>Native page 2</title></head><body><h1>Native page 2</h1><a href="native.html">back</a></body></html>
HTML
cat > "$render_root/policy/report.toml" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "smoke"
language_default = "zh"

[project]
flow_name = "policy-smoke"
flow_version = "0.3.0-r1"
analysis_mode = "native-subreport-policy"
title.zh = "子报告策略测试"
title.en = "Subreport Policy Smoke"
subtitle.zh = "测试 native_subreport embed_policy。"
subtitle.en = "Test native_subreport embed_policy."

[[sections]]
id = "native"
kind = "native_reports"
title.zh = "原生报告"
title.en = "Native reports"

[[sections.components]]
type = "native_subreport"
id = "always"
kind = "html"
path = "03_results/html/native.html"
embed_policy = "always"
embed_linked_pages = true
title.zh = "必须内嵌"
title.en = "Must embed"

[[sections.components]]
type = "native_subreport"
id = "never"
kind = "html"
path = "03_results/html/native.html"
embed_policy = "never"
title.zh = "仅链接"
title.en = "Linked only"
TOML
"$renderer" render \
  --spec "$render_root/policy/report.toml" \
  --root "$render_root/policy" \
  --out "$render_root/policy/04_reports/report.html" \
  --force \
  --validate
grep -F $'always\thtml\t03_results/html/native.html\tembedded' "$render_root/policy/04_reports/embedded_html_reports.tsv" >/dev/null
grep -F "always--03_results-html-page2.html" "$render_root/policy/04_reports/embedded_html_reports.tsv" >/dev/null
grep -F "#taffish-subreport=always--03_results-html-page2.html" "$render_root/policy/04_reports/report.html" >/dev/null
grep -F $'never\thtml\t03_results/html/native.html\tlinked' "$render_root/policy/04_reports/embedded_html_reports.tsv" >/dev/null
grep -F 'class="subreport-actions"' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'data-open-subreport="always"' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'href="../03_results/html/native.html"' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'subreport-source-link primary' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'openEmbeddedSubreportWindow' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'window.open("about:blank", "_blank")' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F 'data-subreport-loading' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F '打开内嵌报告' "$render_root/policy/04_reports/report.html" >/dev/null
grep -F '打开源 HTML' "$render_root/policy/04_reports/report.html" >/dev/null

echo "[SMOKE] validate fixture spec"
"$renderer" validate-spec --spec "$app_root/testdata/fixtures/ngs-qc/report.toml"
"$renderer" validate-spec --spec "$app_root/testdata/fixtures/phylogeny/report.toml"

echo "[SMOKE] render NGS QC fixture"
"$renderer" render \
  --spec "$app_root/testdata/fixtures/ngs-qc/report.toml" \
  --root "$app_root/testdata/fixtures/ngs-qc" \
  --out "$report" \
  --force \
  --validate

echo "[SMOKE] shared template checker"
python3 "$hub_root/repos/apps/templates/flow-report/scripts/check-rendered-report.py" \
  --require-logo-data-uri \
  "$report"

echo "[SMOKE] output indexes"
test -s "$outdir/04_reports/report.manifest.json"
test -s "$outdir/04_reports/report.spec.toml"
test -s "$outdir/04_reports/report.normalized.json"
test -s "$outdir/04_reports/report_files.tsv"
test -s "$outdir/04_reports/embedded_html_reports.tsv"
grep -F "multiqc" "$outdir/04_reports/embedded_html_reports.tsv" >/dev/null
grep -F "data:image/" "$report" >/dev/null
grep -F "embedded-subreports-data" "$report" >/dev/null
grep -F "data-image-zoom-in" "$report" >/dev/null
grep -F "data-image-fit-reset" "$report" >/dev/null
grep -F 'class="subreport-actions"' "$report" >/dev/null
grep -F 'data-open-subreport="multiqc"' "$report" >/dev/null
grep -F 'openEmbeddedSubreportWindow' "$report" >/dev/null
grep -F 'window.open("about:blank", "_blank")' "$report" >/dev/null
grep -F 'data-subreport-loading' "$report" >/dev/null
grep -F 'href="../../../../testdata/fixtures/ngs-qc/03_results/html/multiqc_report.html"' "$report" >/dev/null
grep -F 'href="../../../../testdata/fixtures/ngs-qc/03_results/seqkit/clean_fastq_stats.tsv"' "$report" >/dev/null
grep -F '打开内嵌报告' "$report" >/dev/null
grep -F '打开源 HTML' "$report" >/dev/null
grep -F "table-card table-preview-card" "$report" >/dev/null
grep -F "data-table-toggle" "$report" >/dev/null
grep -F "data-table-scope" "$report" >/dev/null
grep -F "data-table-toolbar" "$report" >/dev/null
grep -F "data-table-usage" "$report" >/dev/null
grep -F "data-table-search" "$report" >/dev/null
grep -F "data-table-scroll-controls" "$report" >/dev/null
grep -F "data-table-scroll-right" "$report" >/dev/null
grep -F "data-table-sort" "$report" >/dev/null
grep -F "data-preview-hidden=\"true\"" "$report" >/dev/null
grep -F "table-expandable-scroll" "$report" >/dev/null
grep -F "data-cell-value=" "$report" >/dev/null
grep -F "reading-guide-primary" "$report" >/dev/null
grep -F "reading-guide-steps" "$report" >/dev/null
grep -F 'data-i18n-lang="en">Criterion' "$report" >/dev/null
grep -F 'data-i18n-lang="zh">判定标准' "$report" >/dev/null
grep -F 'data-i18n-lang="en">Every declared FASTQ is readable' "$report" >/dev/null
grep -F 'data-i18n-lang="zh">所有声明的 FASTQ 可读取' "$report" >/dev/null
if grep -F "criterion_en" "$report" >/dev/null; then
  echo "unexpected raw language-specific table column in report: criterion_en" >&2
  exit 1
fi
if grep -F "criterion_zh" "$report" >/dev/null; then
  echo "unexpected raw language-specific table column in report: criterion_zh" >&2
  exit 1
fi
grep -F 'data-taffish-runtime=\"plotly-1.2.0\"' "$report" >/dev/null
if grep -F 'src=\"https://opengene.org/plotly-1.2.0.min.js' "$report" >/dev/null; then
  echo "unexpected remote fastp Plotly runtime in standalone report" >&2
  exit 1
fi
if grep -F 'src=\"https://cdn.plot.ly/plotly-1.2.0.min.js' "$report" >/dev/null; then
  echo "unexpected remote fastp Plotly fallback runtime in standalone report" >&2
  exit 1
fi
if grep -F "window.Plotly || document.write" "$report" >/dev/null; then
  echo "unexpected fastp remote fallback loader in standalone report" >&2
  exit 1
fi
python3 - "$report" <<'PY'
from pathlib import Path
import html
import json
import re
import sys

report = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r'<script[^>]+id="embedded-subreports-data"[^>]*>(.*?)</script>', report, re.S)
if not match:
    raise SystemExit("missing embedded-subreports-data payload")
payload = json.loads(html.unescape(match.group(1)))
by_id = {item["id"]: item.get("html", "") for item in payload}
for key, min_bytes in {"multiqc": 100000, "fastp": 100000, "fastqc": 100000}.items():
    if key not in by_id:
        raise SystemExit(f"missing embedded payload: {key}")
    if len(by_id[key].encode("utf-8")) < min_bytes:
        raise SystemExit(f"embedded payload too small: {key}")
fastp = by_id["fastp"]
if 'data-taffish-runtime="plotly-1.2.0"' not in fastp:
    raise SystemExit("fastp payload does not include local plotly runtime")
if re.search(r"<script\\b[^>]*\\bsrc\\s*=\\s*['\\\"]https?://", fastp, re.I):
    raise SystemExit("fastp payload still contains remote script src")
if "window.Plotly || document.write" in fastp or "document.write" in fastp:
    raise SystemExit("fastp payload still contains remote fallback loader")
PY
grep -F "flex-wrap: nowrap;" "$report" >/dev/null
grep -F "status-card-content" "$report" >/dev/null
grep -F "grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));" "$report" >/dev/null
grep -F ".table-preview-card.is-table-expanded .table-expandable-scroll" "$report" >/dev/null
grep -F "max-height: min(420px, 52vh);" "$report" >/dev/null
grep -F "min-inline-size: 0;" "$report" >/dev/null
grep -F "max-inline-size: 100%;" "$report" >/dev/null
grep -F ".file-category span {" "$report" >/dev/null
grep -F "white-space: normal;" "$report" >/dev/null
grep -F "This is one table: the button expands or collapses hidden rows in place" "$report" >/dev/null
if grep -F "full-table-scroll" "$report" >/dev/null; then
  echo "unexpected duplicate full-table scroll pane in standalone report" >&2
  exit 1
fi
if grep -F "table-full-panel" "$report" >/dev/null; then
  echo "unexpected second-table full panel in standalone report" >&2
  exit 1
fi
if grep -F "table-remaining-toggle" "$report" >/dev/null; then
  echo "unexpected remaining-row toggle in standalone report" >&2
  exit 1
fi
if grep -F "table-expand-bar" "$report" >/dev/null; then
  echo "unexpected table expand bar in standalone report" >&2
  exit 1
fi
if grep -F "table-expand-control-row" "$report" >/dev/null; then
  echo "unexpected table-row expand control in standalone report" >&2
  exit 1
fi
if grep -F "data-table-modal" "$report" >/dev/null; then
  echo "unexpected table modal payload in standalone report" >&2
  exit 1
fi
if grep -F "table-remaining-details" "$report" >/dev/null; then
  echo "unexpected second-table remaining-row details block in standalone report" >&2
  exit 1
fi

echo "[SMOKE] render phylogeny fixture with tree and alignment viewers"
phylo_out="$render_root/phylogeny"
phylo_report="$phylo_out/04_reports/taffish_report.html"
"$renderer" render \
  --spec "$app_root/testdata/fixtures/phylogeny/report.toml" \
  --root "$app_root/testdata/fixtures/phylogeny" \
  --out "$phylo_report" \
  --force \
  --validate
python3 "$hub_root/repos/apps/templates/flow-report/scripts/check-rendered-report.py" \
  --require-logo-data-uri \
  "$phylo_report"
grep -F 'class="code-file-card" id="tree-newick"' "$phylo_report" >/dev/null
grep -F 'data-tree-viewer' "$phylo_report" >/dev/null
grep -F 'id="tree-inline"' "$phylo_report" >/dev/null
grep -F 'data-sequence-alignment' "$phylo_report" >/dev/null
grep -F 'id="trimmed-alignment"' "$phylo_report" >/dev/null
grep -F 'data-copy-code' "$phylo_report" >/dev/null
grep -F 'sample_A:0.0123' "$phylo_report" >/dev/null
grep -F 'human_P99999_Homo' "$phylo_report" >/dev/null
grep -F 'href="../../../../testdata/fixtures/phylogeny/03_results/tree/plots/tree.png"' "$phylo_report" >/dev/null
grep -F $'newick\ttree-inline\t03_results/tree/tree.nwk' "$phylo_out/04_reports/report_files.tsv" >/dev/null
grep -F $'alignment\ttrimmed-alignment\t03_results/alignment/trimmed.fa' "$phylo_out/04_reports/report_files.tsv" >/dev/null
grep -F $'text\ttree-newick\t03_results/tree/tree.nwk' "$phylo_out/04_reports/report_files.tsv" >/dev/null

python3 - "$render_root" <<'PY'
from pathlib import Path
import html
import json
import re
import sys

root = Path(sys.argv[1])
reports = sorted(root.glob("*/04_reports/*.html"))
if not reports:
    raise SystemExit("no smoke reports found")
for report in reports:
    text = report.read_text(encoding="utf-8")
    leaked = re.findall(r'href="(?:03_results|00_reports|04_reports)/[^"]+"', text)
    if leaked:
        raise SystemExit(f"{report}: root-relative href leaked: {leaked[:5]}")
    cards = text.count('class="subreport-card"')
    if cards and text.count('class="subreport-actions"') != cards:
        raise SystemExit(f"{report}: subreport card/action mismatch")
    payload_match = re.search(r'<script[^>]+id="embedded-subreports-data"[^>]*>(.*?)</script>', text, re.S)
    if payload_match:
        payload = json.loads(html.unescape(payload_match.group(1)))
        ids = [item["id"] for item in payload]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"{report}: duplicate embedded subreport payload ids")
PY

echo "[SMOKE] ok"
