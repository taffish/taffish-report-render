#!/usr/bin/env bash
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
app_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
hub_root=$(CDPATH= cd -- "$app_root/../../../../.." && pwd)

export PYTHONPATH="$app_root/python"
renderer="$app_root/bin/report-render"
checker="$hub_root/repos/apps/templates/flow-report/scripts/check-rendered-report.py"
out_root="${TAFFISH_REPORT_RENDER_TEST_OUT:-$app_root/tests/test-real-run-out}"
flow_out_root="$out_root/flow-reports"
component_out_root="$out_root/component-regression"

ngs_qc_source="${TAFFISH_REPORT_RENDER_NGS_QC_ROOT:-$hub_root/repos/apps/bio/flows/ngs-qc-flow/tests/test-real-run-out}"
bam_qc_source="${TAFFISH_REPORT_RENDER_BAM_QC_ROOT:-$hub_root/repos/apps/bio/flows/bam-qc-flow/tests/test-real-run-out}"
phylogeny_source="${TAFFISH_REPORT_RENDER_PHYLOGENY_ROOT:-$hub_root/repos/apps/bio/flows/phylogeny-flow/tests/test-real-run-out}"
rnaseq_reference_source="${TAFFISH_REPORT_RENDER_RNASEQ_REFERENCE_ROOT:-$hub_root/repos/apps/bio/flows/rna-seq/example-reports/yeast-standard-report}"
rnaseq_denovo_source="${TAFFISH_REPORT_RENDER_RNASEQ_DENOVO_ROOT:-$hub_root/repos/apps/bio/flows/rna-seq/example-reports/yeast-denovo-standard-report}"
chengdu_yuanda_report12_source="${TAFFISH_REPORT_RENDER_CHENGDU_YUANDA_REPORT12_ROOT:-$app_root/testdata/fixtures/chengdu-yuanda-report12}"

clean=false
run_checker=true
run_validate=true
default_run=false
fixtures=()

flow_fixtures=(ngs-qc bam-qc phylogeny rnaseq-reference rnaseq-denovo chengdu-yuanda-report12)
component_fixtures=(component-basic-report component-media-layout-report component-echarts-report component-tree-alignment-report component-igv-report component-ngl-native-report)

usage() {
    cat <<'EOF'
Usage:
  tests/test-real-run.sh [options] [fixture ...]

Render maintained taffish-report-render full real-report scenarios and
real-style component regression scenarios into ignored local outputs. The
no-argument default cleans the previous output directory and renders:

  ngs-qc bam-qc phylogeny rnaseq-reference rnaseq-denovo chengdu-yuanda-report12
  component-basic-report component-media-layout-report component-echarts-report component-tree-alignment-report component-igv-report component-ngl-native-report

The first group renders from corresponding real flow output trees, not from a
trimmed "normal" fixture. RNA-seq reference and de novo scenarios use the public
yeast example report trees and embed the full declared HTML/QC payload set.
The Chengdu Yuanda report-12 structure fixture is part of the default regression
set. Browser runtimes such as NGL and IGV must already be vendored in the
renderer package/image. The normal report interface is still TOML plus a
results root; test-real-run never downloads JavaScript runtime files and never
uses NGL/IGV test shims. Missing real runtime is a hard failure.

The component-* scenarios are local TOML-only reports that exercise renderer
component/runtime interfaces with real-style biological inputs independently
from large real flow outputs.

Options:
  --clean                         Remove the output directory before rendering.
                                  This is implicit when no fixture is specified.
  --outdir DIR                    Write rendered reports to DIR. Default: tests/test-real-run-out.
  --ngs-qc-source DIR             Source root for the NGS QC full report.
  --bam-qc-source DIR             Source root for the BAM QC full report.
  --phylogeny-source DIR          Source root for the phylogeny full report.
  --rnaseq-reference-source DIR   Source root for the RNA-seq reference full report.
  --rnaseq-denovo-source DIR      Source root for the RNA-seq de novo full report.
  --chengdu-yuanda-report12-source DIR
                                  Source root for the Chengdu Yuanda report-12 full structure report fixture.
  --no-checker                    Skip the shared flow-report structural checker.
  --no-validate                   Skip renderer --validate after render.
  -h, --help                      Show this help.

Examples:
  tests/test-real-run.sh
  tests/test-real-run.sh ngs-qc rnaseq-reference
  TAFFISH_REPORT_RENDER_TEST_OUT=/tmp/report-rendered tests/test-real-run.sh phylogeny

Outputs:
  <outdir>/flow-reports/<fixture>/04_reports/taffish_report.html
  <outdir>/flow-reports/<fixture>/report.full.toml
  <outdir>/component-regression/<component-case>/04_reports/taffish_report.html
  <outdir>/component-regression/<component-case>/report.full.toml
  <outdir>/rendered_reports.tsv
  <outdir>/flow-reports/rendered_reports.tsv
  <outdir>/component-regression/rendered_reports.tsv
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --clean)
            clean=true
            shift
            ;;
        --outdir)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --outdir requires a directory" >&2
                exit 2
            fi
            out_root="$2"
            shift 2
            ;;
        --ngs-qc-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --ngs-qc-source requires a directory" >&2
                exit 2
            fi
            ngs_qc_source="$2"
            shift 2
            ;;
        --bam-qc-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --bam-qc-source requires a directory" >&2
                exit 2
            fi
            bam_qc_source="$2"
            shift 2
            ;;
        --phylogeny-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --phylogeny-source requires a directory" >&2
                exit 2
            fi
            phylogeny_source="$2"
            shift 2
            ;;
        --rnaseq-reference-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --rnaseq-reference-source requires a directory" >&2
                exit 2
            fi
            rnaseq_reference_source="$2"
            shift 2
            ;;
        --rnaseq-denovo-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --rnaseq-denovo-source requires a directory" >&2
                exit 2
            fi
            rnaseq_denovo_source="$2"
            shift 2
            ;;
        --chengdu-yuanda-report12-source)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --chengdu-yuanda-report12-source requires a directory" >&2
                exit 2
            fi
            chengdu_yuanda_report12_source="$2"
            shift 2
            ;;
        --no-checker)
            run_checker=false
            shift
            ;;
        --no-validate)
            run_validate=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            echo "ERROR: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            fixtures+=("$1")
            shift
            ;;
    esac
done

if [ "${#fixtures[@]}" -eq 0 ]; then
    default_run=true
    clean=true
    fixtures=("${flow_fixtures[@]}" "${component_fixtures[@]}")
fi

flow_out_root="$out_root/flow-reports"
component_out_root="$out_root/component-regression"

find_runtime_pack() {
    local relative="$1"
    shift
    local candidate
    for candidate in "$app_root/python/taffish_report_render/runtime_packs/$relative" "$@"; do
        if [ -s "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

ensure_ngl_runtime_for_real_run() {
    local runtime_js
    if runtime_js=$(find_runtime_pack "ngl/ngl.js" \
        "/opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/ngl.js" \
        "/usr/local/share/taffish-report-render/runtime-packs/ngl/ngl.js"); then
        echo "[REAL] runtime NGL: $runtime_js"
        return
    fi
    cat >&2 <<'EOF'
ERROR: real-run needs a vendored NGL runtime pack, but none was found.

Normal report generation uses only TOML/JSON plus a results root. Browser
runtime files are renderer package/image assets and must be vendored before
real-run starts; test-real-run never downloads JavaScript runtime files.

Expected source-tree path:
  python/taffish_report_render/runtime_packs/ngl/ngl.js

Maintainer preparation:
  tools/vendor-runtime-packs.sh --runtime ngl
EOF
    return 1
}

ensure_igv_runtime_for_real_run() {
    local runtime_js
    if runtime_js=$(find_runtime_pack "igv/igv.min.js" \
        "/opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/igv.min.js" \
        "/usr/local/share/taffish-report-render/runtime-packs/igv/igv.min.js"); then
        echo "[REAL] runtime IGV: $runtime_js"
        return
    fi
    cat >&2 <<'EOF'
ERROR: real-run needs a vendored IGV runtime pack, but none was found.

Normal report generation uses only TOML/JSON plus a results root. Browser
runtime files are renderer package/image assets and must be vendored before
real-run starts; test-real-run never downloads JavaScript runtime files.

Expected source-tree path:
  python/taffish_report_render/runtime_packs/igv/igv.min.js

Maintainer preparation:
  tools/vendor-runtime-packs.sh --runtime igv
EOF
    return 1
}

preflight_runtime_packs() {
    local needs_ngl=false
    local needs_igv=false
    local fixture
    for fixture in "${fixtures[@]}"; do
        case "$fixture" in
            chengdu-yuanda-report12|component-ngl-native-report)
                needs_ngl=true
                ;;
            component-igv-report)
                needs_igv=true
                ;;
        esac
    done

    local failed=false
    if [ "$needs_ngl" = true ]; then
        echo "[REAL] preflight runtime: NGL"
        if ! ensure_ngl_runtime_for_real_run; then
            failed=true
        fi
    fi
    if [ "$needs_igv" = true ]; then
        echo "[REAL] preflight runtime: IGV"
        if ! ensure_igv_runtime_for_real_run; then
            failed=true
        fi
    fi
    if [ "$failed" = true ]; then
        cat >&2 <<'EOF'
ERROR: one or more real browser runtime packs are unavailable.

Real-run checks every maintained runtime/component library with real runtime
code. It does not continue with partial reports when required runtime packs are
missing, because that would hide later component failures.
EOF
        exit 1
    fi
}

index="$out_root/rendered_reports.tsv"
flow_index="$flow_out_root/rendered_reports.tsv"
component_index="$component_out_root/rendered_reports.tsv"

echo "[REAL] renderer: $renderer"
echo "[REAL] fixtures: ${fixtures[*]}"
echo "[REAL] output  : $out_root"
echo "[REAL] flows   : $flow_out_root"
echo "[REAL] components: $component_out_root"
preflight_runtime_packs

if [ "$clean" = true ]; then
    rm -rf "$out_root"
fi
mkdir -p "$flow_out_root" "$component_out_root"

printf 'category\tfixture\tsource_root\treport\tmanifest\tfiles_index\tembedded_html_index\n' > "$index"
printf 'fixture\tsource_root\treport\tmanifest\tfiles_index\tembedded_html_index\n' > "$flow_index"
printf 'fixture\tsource_root\treport\tmanifest\tfiles_index\tembedded_html_index\n' > "$component_index"

require_file() {
    local path="$1"
    if [ ! -s "$path" ]; then
        echo "ERROR: missing required full-report input: $path" >&2
        exit 1
    fi
}

require_root() {
    local root="$1"
    local label="$2"
    if [ ! -d "$root" ]; then
        echo "ERROR: missing source root for $label: $root" >&2
        exit 1
    fi
    CDPATH= cd -- "$root" && pwd
}

safe_id() {
    printf '%s' "$1" | tr '[:upper:]_ .' '[:lower:]---' | tr -cs 'a-z0-9.-' '-'
}

fixture_category() {
    case "$1" in
        component-*) printf '%s\n' "component-regression" ;;
        *) printf '%s\n' "flow-reports" ;;
    esac
}

category_out_root() {
    case "$1" in
        component-regression) printf '%s\n' "$component_out_root" ;;
        flow-reports) printf '%s\n' "$flow_out_root" ;;
        *)
            echo "ERROR: unknown output category: $1" >&2
            exit 2
            ;;
    esac
}

category_index() {
    case "$1" in
        component-regression) printf '%s\n' "$component_index" ;;
        flow-reports) printf '%s\n' "$flow_index" ;;
        *)
            echo "ERROR: unknown output category: $1" >&2
            exit 2
            ;;
    esac
}

fixture_work_dir() {
    local fixture="$1"
    local category
    category=$(fixture_category "$fixture")
    printf '%s/%s\n' "$(category_out_root "$category")" "$fixture"
}

assert_interactive_plot_layout() {
    local report="$1"
    grep -F "interactive-plot-stats" "$report" >/dev/null
    grep -F "grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));" "$report" >/dev/null
    grep -F "height:500px;min-height:500px" "$report" >/dev/null
    grep -F "animation: false" "$report" >/dev/null
    grep -F "animationDurationUpdate: 0" "$report" >/dev/null
    grep -F "progressive: 0" "$report" >/dev/null
    python3 - "$report" <<'PY'
from pathlib import Path
import sys

html = Path(sys.argv[1]).read_text()
if "data-interactive-plot" not in html:
    raise SystemExit("missing interactive plot")
start = html.index('<article class="interactive-plot-card"')
body = html[start:]
controls = body.index("interactive-plot-controls")
layout = body.index("interactive-plot-layout")
stats = body.index("interactive-plot-stats")
if not (controls < layout < stats):
    raise SystemExit("interactive_plot order must be controls -> chart layout -> stats")
if 'interactive-plot-side"><details' in body:
    raise SystemExit("interactive_plot controls must not live inside the side column")
PY
}

emit_plot_card() {
    local id="$1"
    local image="$2"
    local title_en="$3"
    local title_zh="$4"
    local caption_en="$5"
    local caption_zh="$6"
    local pdf="${image%.*}.pdf"
    cat <<TOML
[[sections.components]]
type = "plot_card"
id = "$id"
image = "$image"
pdf = "$pdf"
title.en = "$title_en"
title.zh = "$title_zh"
caption.en = "$caption_en"
caption.zh = "$caption_zh"

TOML
}

emit_table_preview() {
    local id="$1"
    local source="$2"
    local title_en="$3"
    local title_zh="$4"
    local preview_rows="${5:-10}"
    local max_rows="${6:-5000}"
    local max_bytes="${7:-5000000}"
    cat <<TOML
[[sections.components]]
type = "table_preview"
id = "$id"
source = "$source"
title.en = "$title_en"
title.zh = "$title_zh"
preview_rows = $preview_rows
embed_full = true
max_embed_rows = $max_rows
max_embed_bytes = $max_bytes

TOML
}

emit_interactive_plot() {
    local id="$1"
    local kind="$2"
    local source="$3"
    local title_en="$4"
    local title_zh="$5"
    local note_en="$6"
    local note_zh="$7"
    local top_n="${8:-20}"
    cat <<TOML
[[sections.components]]
type = "interactive_plot"
id = "$id"
kind = "$kind"
source = "$source"
default_padj = 0.05
default_log2fc = 1
top_n = $top_n
max_points = 12000
height = 500
point_size = 8
opacity = 0.82
fixed_range = true
show_threshold_lines = true
label_max_chars = 46
title.en = "$title_en"
title.zh = "$title_zh"
note.en = "$note_en"
note.zh = "$note_zh"

TOML
}

emit_interactive_pca_plot() {
    local id="$1"
    local source="$2"
    local title_en="$3"
    local title_zh="$4"
    local note_en="$5"
    local note_zh="$6"
    cat <<TOML
[[sections.components]]
type = "interactive_plot"
id = "$id"
kind = "pca"
source = "$source"
sample = "sample"
group = "condition"
pc1 = "PC1"
pc2 = "PC2"
x_label = "PC1"
y_label = "PC2"
max_points = 1000
height = 500
point_size = 10
opacity = 0.88
fixed_range = true
title.en = "$title_en"
title.zh = "$title_zh"
note.en = "$note_en"
note.zh = "$note_zh"

TOML
}

emit_code_file() {
    local id="$1"
    local source="$2"
    local language="$3"
    local title_en="$4"
    local title_zh="$5"
    local note_en="$6"
    local note_zh="$7"
    cat <<TOML
[[sections.components]]
type = "code_file"
id = "$id"
source = "$source"
language = "$language"
copy = true
title.en = "$title_en"
title.zh = "$title_zh"
note.en = "$note_en"
note.zh = "$note_zh"

TOML
}

emit_native_subreport() {
    local id="$1"
    local kind="$2"
    local path="$3"
    local title_en="$4"
    local title_zh="$5"
    local note_en="$6"
    local note_zh="$7"
    cat <<TOML
[[sections.components]]
type = "native_subreport"
id = "$id"
kind = "$kind"
path = "$path"
embed_policy = "auto"
embed_linked_pages = true
title.en = "$title_en"
title.zh = "$title_zh"
note.en = "$note_en"
note.zh = "$note_zh"

TOML
}

emit_rnaseq_plot_cards() {
    emit_plot_card "de-pca" "03_results/collected_plots/de.pca_plot.png" "PCA plot" "PCA 图" "Global sample separation in principal-component space." "样本在主成分空间中的整体分离情况。"
    emit_plot_card "de-sample-correlation" "03_results/collected_plots/de.sample_correlation_heatmap.png" "Sample correlation heatmap" "样本相关性热图" "Pairwise sample correlations from transformed expression values." "基于转换后表达值的样本两两相关性。"
    emit_plot_card "de-volcano" "03_results/collected_plots/de.volcano_plot.png" "Volcano plot" "火山图" "Fold change and adjusted significance for each tested feature." "每个被检验特征的 fold change 与校正显著性。"
    emit_plot_card "de-ma" "03_results/collected_plots/de.ma_plot.png" "MA plot" "MA 图" "Expression strength versus log fold change." "表达强度与 log fold change 的关系。"
    emit_plot_card "de-heatmap" "03_results/collected_plots/de.heatmap.png" "DE heatmap" "差异特征热图" "Expression pattern of selected differentially expressed features." "选定差异特征的表达模式。"
    emit_plot_card "de-deg-counts" "03_results/collected_plots/de.deg_counts_barplot.png" "DE feature count bar plot" "差异特征数量柱状图" "Number of up- and down-regulated features under the configured thresholds." "在设定阈值下上调和下调差异特征数量。"
    emit_plot_card "de-expression-distribution" "03_results/collected_plots/de.expression_distribution.png" "Expression distribution" "表达量分布" "Raw or transformed expression distribution across samples." "各样本原始或转换表达量分布。"
    emit_plot_card "de-normalized-count-distribution" "03_results/collected_plots/de.normalized_count_distribution.png" "Normalized count distribution" "标准化 count 分布" "Distribution of normalized counts used for downstream comparison." "用于后续比较的标准化 counts 分布。"
    emit_plot_card "de-top-genes-expression" "03_results/collected_plots/de.top_genes_expression.png" "Top features expression" "Top features 表达图" "Expression of high-priority features across all samples." "重点特征在所有样本中的表达情况。"
    emit_plot_card "enrichment-dotplot" "03_results/collected_plots/enrichment.dotplot.png" "Enrichment dot plot" "富集气泡图" "A polished ORA dot plot for quick review of enriched terms." "用于快速审阅富集条目的优化 ORA 气泡图。"
    emit_plot_card "enrichment-dotplot-original" "03_results/collected_plots/enrichment.dotplot_original.png" "Original ORA dot plot" "原始 ORA 气泡图" "The original upstream-style dot plot retained for audit and comparison." "保留上游原始风格气泡图，便于审计和比较。"
    emit_plot_card "enrichment-ora-barplot" "03_results/collected_plots/enrichment.ora_barplot.png" "ORA bar plot" "ORA 柱状图" "Leading over-representation terms by adjusted significance." "按校正显著性展示靠前的过度富集条目。"
    emit_plot_card "enrichment-gsea-curves" "03_results/collected_plots/enrichment.gsea_enrichment_curves.png" "GSEA enrichment curves" "GSEA 富集曲线" "Running enrichment score curves for selected gene sets." "选定基因集的 running enrichment score 曲线。"
    emit_plot_card "enrichment-gsea-nes" "03_results/collected_plots/enrichment.gsea_nes_plot.png" "GSEA NES plot" "GSEA NES 图" "Normalized enrichment scores for leading GSEA terms." "主要 GSEA 条目的标准化富集分数。"
}

emit_rnaseq_native_subreports() {
    local html_index="$1"
    tail -n +2 "$html_index" | while IFS=$'\t' read -r module report_name report_type _original _local _relative _bytes bundle_id; do
        [ -n "$bundle_id" ] || continue
        local kind="html"
        local module_title="$module"
        local report_label="$report_name"
        case "$module" in
            expression) module_title="Expression" ;;
            alignment) module_title="Alignment" ;;
            count) module_title="Count" ;;
            alignment_qc) module_title="Alignment QC" ;;
            denovo_assembly) module_title="De novo assembly" ;;
            denovo_expression) module_title="De novo expression" ;;
            report) module_title="Report" ;;
        esac
        case "$report_type" in
            MultiQC) kind="multiqc"; report_label="MultiQC" ;;
            FastQC) kind="fastqc"; report_label="FastQC ${report_name#fastqc_}" ;;
            Qualimap) kind="qualimap"; report_label="Qualimap ${report_name#qualimap_}" ;;
            HTML) kind="html"; report_label="Interpretation companion" ;;
        esac
        emit_native_subreport \
            "native-$(safe_id "$bundle_id")" \
            "$kind" \
            "03_results/collected_html/$bundle_id/index.html" \
            "$module_title $report_label" \
            "$module_title $report_label" \
            "Native HTML report collected from the real RNA-seq standard run." \
            "真实 RNA-seq standard 运行收集到的原生 HTML 报告。"
    done
}

render_from_spec() {
    local fixture="$1"
    local source_root="$2"
    local spec="$3"
    local min_bytes="$4"
    local min_embedded="$5"
    local category
    category=$(fixture_category "$fixture")
    local category_root
    category_root=$(category_out_root "$category")
    local category_report_index
    category_report_index=$(category_index "$category")
    local fixture_dir="$category_root/$fixture"
    local report_dir="$category_root/$fixture/04_reports"
    local report="$report_dir/taffish_report.html"
    local manifest="$report_dir/report.manifest.json"
    local files_index="$report_dir/report_files.tsv"
    local embedded_index="$report_dir/embedded_html_reports.tsv"
    local full_spec="$fixture_dir/report.full.toml"
    local step_start

    mkdir -p "$fixture_dir" "$report_dir"
    if ! cmp -s "$spec" "$full_spec"; then
        cp "$spec" "$full_spec"
    fi
    cp "$spec" "$report_dir/report.full.toml"

    echo "[REAL] validate spec: $fixture"
    if [ "$min_bytes" -ge 30000000 ]; then
        echo "[REAL] note: $fixture is a large standalone HTML fixture; rendering and shared checks can be quiet for several minutes."
    fi
    "$renderer" validate-spec --spec "$spec"
    "$renderer" lint --spec "$spec" --root "$source_root"

    echo "[REAL] render fixture: $fixture"
    step_start=$SECONDS
    local render_args=(
        render
        --spec "$spec"
        --root "$source_root"
        --out "$report"
        --force
    )
    if [ "$run_validate" = true ]; then
        render_args+=(--validate)
    fi
    if grep -F 'runtime = "ngl"' "$spec" >/dev/null; then
        ensure_ngl_runtime_for_real_run
    fi
    if grep -F 'runtime = "igv"' "$spec" >/dev/null && ! { grep -F 'viewer_mode = "linked"' "$spec" >/dev/null && ! grep -F 'viewer_mode = "embedded"' "$spec" >/dev/null; }; then
        ensure_igv_runtime_for_real_run
    fi
    "$renderer" "${render_args[@]}"
    echo "[REAL] render done: $fixture (${SECONDS-step_start}s)"

    test -s "$report"
    test -s "$manifest"
    test -s "$report_dir/report.normalized.json"
    test -s "$report_dir/report.spec.toml"
    test -s "$files_index"
    test -s "$embedded_index"

    if [ "$run_checker" = true ]; then
        echo "[REAL] shared checker: $fixture"
        step_start=$SECONDS
        python3 "$checker" --require-logo-data-uri "$report"
        echo "[REAL] shared checker done: $fixture (${SECONDS-step_start}s)"
    fi

    grep -F "flex-wrap: nowrap;" "$report" >/dev/null
    grep -F "reading-guide-primary" "$report" >/dev/null
    grep -F "reading-guide-steps" "$report" >/dev/null
    grep -F "status-card-content" "$report" >/dev/null
    grep -F "grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));" "$report" >/dev/null
    grep -F "max-height: min(420px, 52vh);" "$report" >/dev/null
    grep -F "overflow-x: auto;" "$report" >/dev/null
    grep -F "overflow-y: auto;" "$report" >/dev/null
    grep -F "width: max-content;" "$report" >/dev/null
    grep -F "min-width: 100%;" "$report" >/dev/null
    grep -F "min-inline-size: 0;" "$report" >/dev/null
    grep -F "max-inline-size: 100%;" "$report" >/dev/null
    grep -F "white-space: nowrap;" "$report" >/dev/null
    grep -F "openEmbeddedSubreportWindow" "$report" >/dev/null
    grep -F 'window.open("about:blank", "_blank")' "$report" >/dev/null
    grep -F "data-subreport-loading" "$report" >/dev/null
    grep -F "table-expandable-scroll" "$report" >/dev/null
    grep -F "data-table-scroll-controls" "$report" >/dev/null
    grep -F "data-table-scroll-left" "$report" >/dev/null
    grep -F "data-table-scroll-right" "$report" >/dev/null
    grep -F "data-table-toolbar" "$report" >/dev/null
    grep -F "data-table-search" "$report" >/dev/null
    grep -F "data-table-scope" "$report" >/dev/null
    grep -F "data-image-modal" "$report" >/dev/null
    grep -F ".section > .structure-card" "$report" >/dev/null
    grep -F "max-width: 380px;" "$report" >/dev/null
    grep -F ".file-category span {" "$report" >/dev/null
    grep -F "white-space: normal;" "$report" >/dev/null
    if grep -F 'class="plot-card"' "$report" >/dev/null; then
        grep -F "data-open-image" "$report" >/dev/null
    fi
    if grep -F 'class="table-preview-card' "$report" >/dev/null; then
        grep -F "data-cell-value=" "$report" >/dev/null
    fi
    if grep -F 'runtime = "ngl"' "$spec" >/dev/null; then
        grep -F 'data-taffish-runtime="ngl"' "$report" >/dev/null
        grep -F "data-structure-ngl-stage" "$report" >/dev/null
        if grep -F 'require("three")' "$report" >/dev/null || grep -F "require('three')" "$report" >/dev/null || grep -F 't.three,t.chroma,t.signalsWrapper,t.sprintfJs' "$report" >/dev/null; then
            echo "ERROR: embedded NGL runtime is dependency-externalized, not standalone dist/ngl.js" >&2
            exit 1
        fi
        if grep -F "TAFFISH_NGL_TEST_SHIM" "$report" >/dev/null; then
            echo "ERROR: real-run report used the NGL test shim" >&2
            exit 1
        fi
        if grep -F '"runtimeShim":true' "$report" >/dev/null || grep -F 'data-taffish-runtime-version="test-shim"' "$report" >/dev/null; then
            echo "ERROR: real-run report contains test-shim runtime metadata" >&2
            exit 1
        fi
        grep -F "addNglSiteRepresentations" "$report" >/dev/null
        grep -F "readStructureControlState" "$report" >/dev/null
        grep -F "data-structure-controls" "$report" >/dev/null
        grep -F "data-structure-model-toggle" "$report" >/dev/null
        grep -F "body.report-modal-open" "$report" >/dev/null
        grep -F "syncModalScrollLock" "$report" >/dev/null
        grep -F "overscroll-behavior: contain;" "$report" >/dev/null
        grep -F 'params.colorScheme = "uniform";' "$report" >/dev/null
        grep -F '"pdbText"' "$report" >/dev/null
        grep -F '"atoms"' "$report" >/dev/null
        grep -F "fallbackToBuiltinStructureViewer" "$report" >/dev/null
        grep -F "data-structure-fallback-active" "$report" >/dev/null
        grep -F "initBuiltinStructureViewer" "$report" >/dev/null
    fi
    if grep -F 'runtime = "igv"' "$spec" >/dev/null; then
        grep -F "renderGenomeBrowserFallback" "$report" >/dev/null
        grep -F '"viewerMode"' "$report" >/dev/null
        grep -F "genome-browser-fallback-panel" "$report" >/dev/null
    fi
    if [ "$fixture" = "chengdu-yuanda-report12" ]; then
        grep -F '"siteGroups"' "$report" >/dev/null
        grep -F '"target_matches_DHA"' "$report" >/dev/null
        grep -F '"target_matches_EPA"' "$report" >/dev/null
        grep -F '"target_other"' "$report" >/dev/null
        grep -F "data-structure-site-toggle" "$report" >/dev/null
        grep -F "data-structure-site-radius" "$report" >/dev/null
        grep -F "data-structure-site-opacity" "$report" >/dev/null
        grep -F '<details class="structure-controls" data-structure-controls><summary>' "$report" >/dev/null
        grep -F -- "-site-table" "$files_index" >/dev/null
        grep -F '"spacefill"' "$report" >/dev/null
    fi

    for forbidden in \
        "table-remaining-toggle" \
        "table-expand-bar" \
        "table-expand-control-row" \
        "full-table-scroll" \
        "table-full-panel" \
        "data-table-modal"
    do
        if grep -F "$forbidden" "$report" >/dev/null; then
            echo "ERROR: obsolete table UI marker leaked into $fixture report: $forbidden" >&2
            exit 1
        fi
    done

    local embedded_count
    embedded_count=$(tail -n +2 "$embedded_index" | wc -l | tr -d ' ')
    if [ "$embedded_count" -lt "$min_embedded" ]; then
        echo "ERROR: expected at least $min_embedded embedded/native HTML records for $fixture, got $embedded_count" >&2
        exit 1
    fi

    local report_bytes
    report_bytes=$(wc -c < "$report" | tr -d ' ')
    if [ "$report_bytes" -lt "$min_bytes" ]; then
        echo "ERROR: $fixture full report looks too small: $report_bytes bytes" >&2
        exit 1
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$fixture" "$source_root" "$report" "$manifest" "$files_index" "$embedded_index" >> "$category_report_index"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$category" "$fixture" "$source_root" "$report" "$manifest" "$files_index" "$embedded_index" >> "$index"
    echo "[REAL] embedded HTML records for $fixture: $embedded_count"
    echo "[REAL] report bytes for $fixture: $report_bytes"
}

render_ngs_qc() {
    local fixture="ngs-qc"
    local source_root
    source_root=$(require_root "$ngs_qc_source" "$fixture")
    local spec="$(fixture_work_dir "$fixture")/report.full.toml"
    local html_index="$source_root/04_reports/html_reports.tsv"

    for required in \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/module_status.tsv" \
        "$source_root/04_reports/quality_gates.tsv" \
        "$source_root/04_reports/parameters.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/03_results/raw_seqkit/raw_fastq_stats.tsv" \
        "$source_root/03_results/clean_seqkit/clean_fastq_stats.tsv" \
        "$html_index"
    do
        require_file "$required"
    done

    mkdir -p "$(dirname "$spec")"
    {
        cat <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "real-run-current"
language_default = "zh"

[project]
flow_name = "ngs-qc-flow"
flow_version = "0.2.0-r1"
analysis_mode = "quality-control"
title.zh = "TAFFISH NGS QC 完整报告"
title.en = "TAFFISH NGS QC full report"
subtitle.zh = "基于 ngs-qc-flow 真实 test-real-run 输出，完整覆盖 raw/clean SeqKit、fastp、FastQC 和 MultiQC 报告。"
subtitle.en = "Rendered from the real ngs-qc-flow test-real-run output, covering raw/clean SeqKit, fastp, FastQC, and MultiQC reports."

[provenance]
manifest = "04_reports/report.manifest.json"
versions = "04_reports/versions.tsv"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Project Overview"
note.zh = "展示输入样本、清洗状态、模块状态和报告打包状态。"
note.en = "Summarizes input samples, cleaning status, module status, and report packaging."

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/flow_summary.tsv"

[[sections.components]]
type = "status_grid"
id = "module-status"
source = "04_reports/module_status.tsv"

[[sections]]
id = "quality"
kind = "quality_control"
title.zh = "测序质量控制"
title.en = "Sequencing Quality Control"
note.zh = "保留真实参数、质量门限和 raw/clean FASTQ 统计，判断 reads 是否适合后续分析。"
note.en = "Keeps real parameters, quality gates, and raw/clean FASTQ statistics to judge whether reads are suitable for downstream analysis."

[[sections.components]]
type = "quality_gate_table"
id = "quality-gates"
source = "04_reports/quality_gates.tsv"

TOML
        emit_table_preview "parameters" "04_reports/parameters.tsv" "Run parameters" "运行参数" 10
        emit_table_preview "raw-seqkit" "03_results/raw_seqkit/raw_fastq_stats.tsv" "Raw FASTQ statistics" "原始 FASTQ 统计" 10
        emit_table_preview "clean-seqkit" "03_results/clean_seqkit/clean_fastq_stats.tsv" "Clean FASTQ statistics" "清洗后 FASTQ 统计" 10
        cat <<'TOML'
[[sections]]
id = "native-html"
kind = "native_reports"
title.zh = "原生 QC 报告"
title.en = "Native QC Reports"
note.zh = "完整声明真实 NGS QC 输出中的 MultiQC、fastp、raw FastQC 和 clean FastQC HTML。"
note.en = "Declares the complete MultiQC, fastp, raw FastQC, and clean FastQC HTML set from the real NGS QC output."

TOML
        tail -n +2 "$html_index" | while IFS=$'\t' read -r id group label path _rest; do
            [ -n "$id" ] || continue
            local kind="html"
            case "$group" in
                multiqc) kind="multiqc" ;;
                fastp) kind="fastp" ;;
                raw_fastqc|clean_fastqc) kind="fastqc" ;;
            esac
            emit_native_subreport "native-$(safe_id "$id")" "$kind" "$path" "$label" "$label" "Native $group HTML generated by ngs-qc-flow." "ngs-qc-flow 生成的原生 $group HTML。"
        done
        cat <<'TOML'
[[sections]]
id = "tool-audit"
kind = "provenance"
title.zh = "工具、参数与交付文件"
title.en = "Tools, Parameters, and Deliverables"
note.zh = "保留版本、方法和 HTML payload 索引，便于审计和复用。"
note.en = "Keeps versions, methods, and HTML payload indexes for audit and reuse."

TOML
        emit_table_preview "versions" "04_reports/versions.tsv" "Version table" "版本表" 12
        emit_table_preview "html-index" "04_reports/html_reports.tsv" "HTML subreport index" "HTML 子报告索引" 12
        emit_code_file "methods" "04_reports/methods.txt" "text" "Methods text" "方法文本" "Methods text generated by the source flow." "来源 flow 生成的方法文本。"
    } > "$spec"

    render_from_spec "$fixture" "$source_root" "$spec" 6000000 9
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    grep -F 'data-i18n-lang="en">Criterion' "$report" >/dev/null
    grep -F 'data-i18n-lang="zh">判定标准' "$report" >/dev/null
    grep -F 'data-taffish-runtime=\"plotly-1.2.0\"' "$report" >/dev/null
    grep -F "P1.fastp.html" "$report" >/dev/null
    grep -F "S2.fastp.html" "$report" >/dev/null
    grep -F "P1_R1.clean_fastqc.html" "$report" >/dev/null
    if grep -F "criterion_en" "$report" >/dev/null; then
        echo "ERROR: raw language-specific table column leaked into NGS QC report: criterion_en" >&2
        exit 1
    fi
    if grep -F 'src=\"https://opengene.org/plotly-1.2.0.min.js' "$report" >/dev/null; then
        echo "ERROR: remote fastp Plotly runtime leaked into rendered report" >&2
        exit 1
    fi
    if grep -F "window.Plotly || document.write" "$report" >/dev/null; then
        echo "ERROR: fastp remote fallback loader leaked into rendered report" >&2
        exit 1
    fi
}

render_bam_qc() {
    local fixture="bam-qc"
    local source_root
    source_root=$(require_root "$bam_qc_source" "$fixture")
    local spec="$(fixture_work_dir "$fixture")/report.full.toml"

    for required in \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/module_status.tsv" \
        "$source_root/04_reports/quality_gates.tsv" \
        "$source_root/04_reports/parameters.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/04_reports/html_reports.tsv" \
        "$source_root/04_reports/multiqc_report.html" \
        "$source_root/03_results/samtools/idxstats/tiny.idxstats.tsv" \
        "$source_root/03_results/samtools/coverage/tiny.coverage.tsv" \
        "$source_root/03_results/samtools/flagstat/tiny.flagstat.txt" \
        "$source_root/03_results/samtools/stats/tiny.stats.txt" \
        "$source_root/03_results/mosdepth/genome/tiny.genome.mosdepth.summary.txt" \
        "$source_root/03_results/mosdepth/regions/tiny.regions.mosdepth.summary.txt"
    do
        require_file "$required"
    done

    mkdir -p "$(dirname "$spec")"
    {
        cat <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "real-run-current"
language_default = "zh"

[project]
flow_name = "bam-qc-flow"
flow_version = "0.2.0-r1"
analysis_mode = "alignment-quality-control"
title.zh = "TAFFISH BAM QC 完整报告"
title.en = "TAFFISH BAM QC full report"
subtitle.zh = "基于 bam-qc-flow 真实 test-real-run 输出，覆盖 samtools、mosdepth 和 MultiQC 证据。"
subtitle.en = "Rendered from the real bam-qc-flow test-real-run output, covering samtools, mosdepth, and MultiQC evidence."

[provenance]
manifest = "04_reports/report.manifest.json"
versions = "04_reports/versions.tsv"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Project Overview"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/flow_summary.tsv"

[[sections.components]]
type = "status_grid"
id = "module-status"
source = "04_reports/module_status.tsv"

[[sections]]
id = "alignment-qc"
kind = "quality_control"
title.zh = "比对质量"
title.en = "Alignment Quality"
note.zh = "整合 BAM 可读性、samtools 指标、mosdepth 覆盖度和 MultiQC 原生报告。"
note.en = "Combines BAM readability, samtools metrics, mosdepth coverage, and native MultiQC."

[[sections.components]]
type = "quality_gate_table"
id = "quality-gates"
source = "04_reports/quality_gates.tsv"

TOML
        emit_table_preview "parameters" "04_reports/parameters.tsv" "Run parameters" "运行参数" 10
        emit_table_preview "idxstats" "03_results/samtools/idxstats/tiny.idxstats.tsv" "idxstats summary" "idxstats 摘要" 10
        emit_table_preview "coverage" "03_results/samtools/coverage/tiny.coverage.tsv" "coverage summary" "coverage 摘要" 10
        emit_table_preview "mosdepth-genome" "03_results/mosdepth/genome/tiny.genome.mosdepth.summary.txt" "mosdepth genome summary" "mosdepth 全基因组摘要" 10
        emit_table_preview "mosdepth-regions" "03_results/mosdepth/regions/tiny.regions.mosdepth.summary.txt" "mosdepth regions summary" "mosdepth 区域摘要" 10
        emit_code_file "flagstat" "03_results/samtools/flagstat/tiny.flagstat.txt" "text" "samtools flagstat" "samtools flagstat" "Raw flagstat text retained for audit." "保留原始 flagstat 文本用于审计。"
        emit_code_file "stats" "03_results/samtools/stats/tiny.stats.txt" "text" "samtools stats" "samtools stats" "Raw samtools stats text retained for audit." "保留原始 samtools stats 文本用于审计。"
        cat <<'TOML'
[[sections]]
id = "native-html"
kind = "native_reports"
title.zh = "原生 QC 报告"
title.en = "Native QC Reports"

TOML
        emit_native_subreport "native-multiqc" "multiqc" "04_reports/multiqc_report.html" "MultiQC BAM QC report" "MultiQC BAM QC 报告" "Native MultiQC report generated by bam-qc-flow." "bam-qc-flow 生成的原生 MultiQC 报告。"
        cat <<'TOML'
[[sections]]
id = "tool-audit"
kind = "provenance"
title.zh = "工具、参数与交付文件"
title.en = "Tools, Parameters, and Deliverables"

TOML
        emit_table_preview "versions" "04_reports/versions.tsv" "Version table" "版本表" 12
        emit_table_preview "html-index" "04_reports/html_reports.tsv" "HTML subreport index" "HTML 子报告索引" 12
        emit_code_file "methods" "04_reports/methods.txt" "text" "Methods text" "方法文本" "Methods text generated by the source flow." "来源 flow 生成的方法文本。"
    } > "$spec"

    render_from_spec "$fixture" "$source_root" "$spec" 2500000 1
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    grep -F "samtools flagstat" "$report" >/dev/null
    grep -F "tiny.genome.mosdepth.summary.txt" "$report" >/dev/null
    grep -F "MultiQC BAM QC report" "$report" >/dev/null
}

render_phylogeny() {
    local fixture="phylogeny"
    local source_root
    source_root=$(require_root "$phylogeny_source" "$fixture")
    local spec="$(fixture_work_dir "$fixture")/report.full.toml"

    for required in \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/04_reports/commands.sh" \
        "$source_root/04_reports/methods.txt" \
        "$source_root/00_inputs/input_summary.tsv" \
        "$source_root/00_inputs/parameters.tsv" \
        "$source_root/03_results/alignment/trimmed.fa" \
        "$source_root/03_results/alignment/alignment_stats.tsv" \
        "$source_root/03_results/alignment/trimming_summary.tsv" \
        "$source_root/03_results/tree/model_summary.tsv" \
        "$source_root/03_results/tree/support_summary.tsv" \
        "$source_root/03_results/tree/tree.nwk" \
        "$source_root/03_results/tree/tree.unrooted.nwk" \
        "$source_root/03_results/tree/plots/tree.png" \
        "$source_root/03_results/tree/plots/tree.svg" \
        "$source_root/03_results/tree/plots/tree.pdf" \
        "$source_root/03_results/tree/plots/rectangular/tree.png" \
        "$source_root/03_results/tree/plots/circular/tree.png"
    do
        require_file "$required"
    done

    mkdir -p "$(dirname "$spec")"
    {
        cat <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "real-run-current"
language_default = "zh"

[project]
flow_name = "phylogeny-flow"
flow_version = "0.2.0-r1"
analysis_mode = "phylogeny"
title.zh = "TAFFISH 系统发育完整报告"
title.en = "TAFFISH phylogeny full report"
subtitle.zh = "基于 phylogeny-flow 真实 test-real-run 输出，覆盖输入统计、比对、剪切、建树、矩形/环形树图和 Newick 文本。"
subtitle.en = "Rendered from the real phylogeny-flow test-real-run output, covering input stats, alignment, trimming, tree inference, rectangular/circular plots, and Newick text."

[provenance]
versions = "04_reports/versions.tsv"
commands = "04_reports/commands.sh"
methods = "04_reports/methods.txt"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Project Overview"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/flow_summary.tsv"

TOML
        emit_table_preview "input-summary" "00_inputs/input_summary.tsv" "Input summary" "输入摘要" 10
        emit_table_preview "parameters" "00_inputs/parameters.tsv" "Run parameters" "运行参数" 10
        cat <<'TOML'
[[sections]]
id = "alignment"
kind = "quality_control"
title.zh = "比对与剪切"
title.en = "Alignment and Trimming"
note.zh = "系统发育树的可信度首先取决于序列输入、比对质量和剪切边界。"
note.en = "Phylogenetic interpretation first depends on sequence inputs, alignment quality, and trimming boundaries."

TOML
        emit_table_preview "alignment-stats" "03_results/alignment/alignment_stats.tsv" "Alignment statistics" "比对统计" 10
        emit_table_preview "trimming-summary" "03_results/alignment/trimming_summary.tsv" "Trimming summary" "剪切摘要" 10
        cat <<'TOML'
[[sections.components]]
type = "sequence_alignment"
id = "trimmed-alignment"
source = "03_results/alignment/trimmed.fa"
format = "fasta"
alphabet = "protein"
max_sequences = 40
max_columns = 220
show_consensus = true
title.en = "Trimmed multiple sequence alignment"
title.zh = "修剪后的多序列比对"
note.en = "A browser view of the upstream trimmed alignment used for tree inference."
note.zh = "浏览上游修剪后的建树输入比对，用于核对保守位点和差异位点。"

TOML
        cat <<'TOML'
[[sections]]
id = "tree"
kind = "result_plots"
title.zh = "系统发育树"
title.en = "Phylogenetic Tree"
note.zh = "同时展示默认树图、矩形树图、环形树图和 Newick 文本，便于审阅与复用。"
note.en = "Shows default, rectangular, and circular tree plots plus reusable Newick text."

TOML
        emit_plot_card "tree-main" "03_results/tree/plots/tree.png" "Main tree plot" "主树图" "Default tree rendering from the real flow." "真实 flow 生成的默认树图。"
        emit_plot_card "tree-rectangular" "03_results/tree/plots/rectangular/tree.png" "Rectangular tree plot" "矩形树图" "Rectangular layout produced by the plotting step." "绘图步骤生成的矩形布局。"
        emit_plot_card "tree-circular" "03_results/tree/plots/circular/tree.png" "Circular tree plot" "环形树图" "Circular layout produced by the plotting step." "绘图步骤生成的环形布局。"
        cat <<'TOML'
[[sections.components]]
type = "tree_viewer"
id = "tree-inline"
source = "03_results/tree/tree.nwk"
height = 460
show_branch_lengths = true
title.en = "Interactive inline Newick tree"
title.zh = "内联 Newick 树浏览器"
note.en = "The Newick tree is rendered directly inside the standalone report and remains copyable for downstream tree tools."
note.zh = "Newick 树直接在单文件报告中渲染，并保留可复制源文本以便下游树图工具复用。"

TOML
        emit_code_file "tree-newick" "03_results/tree/tree.nwk" "newick" "Newick tree file" "Newick 树文件" "The tree text can be copied into FigTree, iTOL, ETE Toolkit, or other tree tools." "树文件内容可复制到 FigTree、iTOL、ETE Toolkit 或其他绘图工具中复用。"
        emit_code_file "tree-unrooted-newick" "03_results/tree/tree.unrooted.nwk" "newick" "Unrooted Newick tree file" "未定根 Newick 树文件" "The unrooted tree text is retained for downstream plotting." "保留未定根树文本，便于下游绘图。"
        emit_table_preview "model-summary" "03_results/tree/model_summary.tsv" "Model summary" "模型摘要" 10
        emit_table_preview "support-summary" "03_results/tree/support_summary.tsv" "Support summary" "支持率摘要" 10
        emit_table_preview "plot-gallery" "03_results/tree/plots/tree_plot_gallery.tsv" "Tree plot gallery index" "树图索引" 10
        cat <<'TOML'
[[sections]]
id = "tool-audit"
kind = "provenance"
title.zh = "工具、命令与方法"
title.en = "Tools, Commands, and Methods"

TOML
        emit_table_preview "versions" "04_reports/versions.tsv" "Version table" "版本表" 12
        emit_code_file "commands" "04_reports/commands.sh" "bash" "Commands" "命令记录" "Commands generated by the source flow." "来源 flow 生成的命令记录。"
        emit_code_file "methods" "04_reports/methods.txt" "text" "Methods text" "方法文本" "Methods text generated by the source flow." "来源 flow 生成的方法文本。"
    } > "$spec"

    render_from_spec "$fixture" "$source_root" "$spec" 300000 0
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    grep -F 'class="code-file-card" id="tree-newick"' "$report" >/dev/null
    grep -F 'data-tree-viewer' "$report" >/dev/null
    grep -F 'data-sequence-alignment' "$report" >/dev/null
    grep -F 'data-copy-code' "$report" >/dev/null
    grep -F 'human_P99999_Homo' "$report" >/dev/null
    grep -F "tree-rectangular" "$report" >/dev/null
    grep -F "tree-circular" "$report" >/dev/null
}

render_rnaseq_reference() {
    local fixture="rnaseq-reference"
    local source_root
    source_root=$(require_root "$rnaseq_reference_source" "$fixture")
    local spec="$(fixture_work_dir "$fixture")/report.full.toml"
    local html_index="$source_root/04_reports/html_reports.tsv"

    for required in \
        "$source_root/04_reports/project_summary.tsv" \
        "$source_root/04_reports/key_metrics.tsv" \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/04_reports/tool_links.tsv" \
        "$source_root/04_reports/plot_files.tsv" \
        "$html_index" \
        "$source_root/03_results/collected_tables/standard.subflows.subflows.tsv" \
        "$source_root/03_results/collected_tables/reference.summary.reference_summary.tsv" \
        "$source_root/03_results/collected_tables/expression.summary.expression_summary.tsv" \
        "$source_root/03_results/collected_tables/alignment.summary.alignment_summary.tsv" \
        "$source_root/03_results/collected_tables/count.summary.count_summary.tsv" \
        "$source_root/03_results/collected_tables/alignment_qc.summary.rnaseq_qc_summary.tsv" \
        "$source_root/03_results/collected_tables/de.summary.de_summary.tsv" \
        "$source_root/03_results/collected_tables/enrichment.summary.enrichment_summary.tsv"
    do
        require_file "$required"
    done

    mkdir -p "$(dirname "$spec")"
    {
        cat <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "real-run-current"
language_default = "zh"

[project]
flow_name = "rnaseq-standard-flow"
flow_version = "0.3.0-r1"
analysis_mode = "reference"
title.zh = "TAFFISH RNA-seq 有参分析完整报告"
title.en = "TAFFISH RNA-seq full reference report"
subtitle.zh = "基于 yeast SNF2 24 样本真实示例输出，完整嵌入所有声明的 DE/富集图、MultiQC、FastQC、Qualimap 和解释报告。"
subtitle.en = "A full renderer-driven reproduction of the yeast SNF2 24-sample reference-guided example, embedding all declared DE/enrichment plots, MultiQC, FastQC, Qualimap, and interpretation reports."

[provenance]
versions = "04_reports/versions.tsv"
template_version = "04_reports/report_template_version.txt"
interpretation_report = "04_reports/report_interpretation.html"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Executive Summary"
note.zh = "从真实 yeast-standard-report 结果树收集关键指标、项目摘要和流程完成状态。"
note.en = "Collects key metrics, project summary, and flow completion status from the real yeast-standard-report result tree."

[[sections.components]]
type = "dashboard_cards"
id = "overview-key-metrics"
source = "04_reports/key_metrics.tsv"

TOML
        emit_table_preview "overview-project-summary" "04_reports/project_summary.tsv" "Project summary and collection status" "项目摘要与收集状态" 12
        emit_table_preview "overview-flow-summary" "04_reports/flow_summary.tsv" "Flow summary" "Flow summary" 10
        cat <<'TOML'
[[sections]]
id = "workflow"
kind = "workflow"
title.zh = "分析流程与生物学问题"
title.en = "Workflow and Biological Questions"
note.zh = "展示标准有参 RNA-seq 路线中参考构建、表达定量、比对计数、差异表达、富集和报告生成的衔接关系。"
note.en = "Shows how reference preparation, expression quantification, alignment/counting, DE, enrichment, and reporting connect in the standard reference-guided RNA-seq route."

[[sections.components]]
type = "workflow_diagram"
id = "workflow-subflows"
source = "03_results/collected_tables/standard.subflows.subflows.tsv"

[[sections.components]]
type = "status_grid"
id = "workflow-module-status"
source = "03_results/collected_tables/standard.subflows.subflows.tsv"

TOML
        emit_table_preview "workflow-subflow-table" "03_results/collected_tables/standard.subflows.subflows.tsv" "Subflow outputs" "子流程输出" 10
        cat <<'TOML'
[[sections]]
id = "reference"
kind = "workflow"
title.zh = "参考构建"
title.en = "Reference Preparation"
note.zh = "有参分析需要把 genome 和 annotation 标准化为 Salmon/HISAT2/featureCounts 等后续步骤可复用的参考资产。"
note.en = "Reference-guided analysis standardizes genome and annotation inputs into reusable assets for Salmon, HISAT2, featureCounts, and downstream reporting."

TOML
        emit_table_preview "reference-summary" "03_results/collected_tables/reference.summary.reference_summary.tsv" "Reference summary" "参考构建摘要" 12
        emit_table_preview "reference-genome-index" "03_results/collected_tables/reference.genome_index.genome_index.tsv" "Genome index assets" "基因组索引资产" 12
        cat <<'TOML'
[[sections]]
id = "expression"
kind = "quality_control"
title.zh = "测序质控与表达定量"
title.en = "Read QC and Expression Quantification"
note.zh = "Salmon-first 路线从 FASTQ 直接获得 transcript/gene abundance，同时保留 FastQC 与 MultiQC 原生报告用于审阅。"
note.en = "The Salmon-first route estimates transcript/gene abundance directly from FASTQ while keeping native FastQC and MultiQC reports for review."

TOML
        emit_table_preview "expression-summary" "03_results/collected_tables/expression.summary.expression_summary.tsv" "Salmon expression summary" "Salmon 表达定量摘要" 12
        emit_table_preview "expression-gene-tpm" "03_results/collected_tables/expression.gene_tpm.gene_tpm.tsv" "Gene TPM matrix preview" "Gene TPM 矩阵预览" 8 8000
        cat <<'TOML'
[[sections]]
id = "alignment"
kind = "quality_control"
title.zh = "比对、计数与 RNA-seq QC"
title.en = "Alignment, Counting, and RNA-seq QC"
note.zh = "可选证据分支把 reads 比对回基因组，生成 BAM、featureCounts 矩阵和 RSeQC/Qualimap 质量评估。"
note.en = "The optional evidence branch aligns reads to the genome, producing BAM files, featureCounts matrices, and RSeQC/Qualimap quality assessment."

TOML
        emit_table_preview "alignment-summary" "03_results/collected_tables/alignment.summary.alignment_summary.tsv" "Alignment summary" "比对摘要" 12
        emit_table_preview "count-summary" "03_results/collected_tables/count.summary.count_summary.tsv" "featureCounts summary" "featureCounts 摘要" 12
        emit_table_preview "alignment-qc-summary" "03_results/collected_tables/alignment_qc.summary.rnaseq_qc_summary.tsv" "RNA-seq QC summary" "RNA-seq QC 摘要" 12
        cat <<'TOML'
[[sections]]
id = "de"
kind = "differential_expression"
title.zh = "差异表达"
title.en = "Differential Expression"
note.zh = "差异表达图表说明不同条件之间哪些特征发生变化，以及样本对该比较的支持强度。"
note.en = "Differential-expression figures show which features change between conditions and how strongly the samples support the contrast."

TOML
        emit_rnaseq_plot_cards
        emit_interactive_plot "de-interactive-volcano" "volcano" "03_results/collected_tables/de.results.results.tsv" "Interactive volcano explorer" "交互火山图浏览器" "Review DESeq2 result rows with adjustable padj and log2FC display cutoffs. This only changes the browser view of already-computed rows." "用可调 padj 和 log2FC 展示阈值审阅 DESeq2 结果行；这只改变已计算结果的浏览器视图。"
        emit_interactive_plot "de-interactive-ma" "ma" "03_results/collected_tables/de.results.results.tsv" "Interactive MA explorer" "交互 MA 图浏览器" "Browse expression strength versus log fold change with the same already-computed DESeq2 rows." "基于同一批已计算 DESeq2 结果行浏览表达强度与 log fold change 的关系。"
        if [ -s "$source_root/03_results/collected_tables/de.pca_scores.pca_scores.tsv" ]; then
            emit_interactive_pca_plot "de-interactive-pca" "03_results/collected_tables/de.pca_scores.pca_scores.tsv" "Interactive PCA explorer" "交互 PCA 图浏览器" "Browse already-computed PCA sample coordinates without recalculating PCA." "浏览已计算的 PCA 样本坐标，不重新计算 PCA。"
        fi
        emit_table_preview "de-summary" "03_results/collected_tables/de.summary.de_summary.tsv" "DE summary" "差异表达摘要" 12
        emit_table_preview "de-results" "03_results/collected_tables/de.results.results.tsv" "DESeq2 full result preview" "DESeq2 完整结果预览" 10 8000
        emit_table_preview "de-significant-genes" "03_results/collected_tables/de.significant_genes.significant_genes.tsv" "Significant genes" "显著差异基因" 12
        cat <<'TOML'
[[sections]]
id = "enrichment"
kind = "enrichment"
title.zh = "功能富集"
title.en = "Functional Enrichment"
note.zh = "功能富集把差异基因或排序基因表转换为可解释的生物过程、通路或功能模块。"
note.en = "Functional enrichment turns DE or ranked gene lists into interpretable biological processes, pathways, or functional modules."

TOML
        emit_interactive_plot "enrichment-interactive-ora" "ora_dotplot" "03_results/collected_tables/enrichment.ora_results.ora_results.tsv" "Interactive ORA dot plot" "交互 ORA 气泡图" "Filter already-computed ORA terms by adjusted p-value and Top N to inspect the leading biological terms without recomputing enrichment." "按校正 p 值和 Top N 筛选已计算 ORA 条目，用于查看主要生物学条目，不重新计算富集。" 20
        emit_table_preview "enrichment-summary" "03_results/collected_tables/enrichment.summary.enrichment_summary.tsv" "Enrichment summary" "富集摘要" 12
        emit_table_preview "enrichment-ora-results" "03_results/collected_tables/enrichment.ora_results.ora_results.tsv" "ORA results" "ORA 结果" 10 5000
        emit_table_preview "enrichment-gsea-results" "03_results/collected_tables/enrichment.gsea_results.gsea_results.tsv" "GSEA results" "GSEA 结果" 10 5000
        cat <<'TOML'
[[sections]]
id = "native-reports"
kind = "native_reports"
title.zh = "原生 QC 与解释报告"
title.en = "Native QC and Interpretation Reports"
note.zh = "完整声明真实报告收集到的 MultiQC、FastQC、Qualimap 和解释报告；renderer 会把本地 HTML payload 打包进单文件报告。"
note.en = "Declares the full set of collected MultiQC, FastQC, Qualimap, and interpretation reports; the renderer bundles their local HTML payloads into the standalone report."

TOML
        emit_rnaseq_native_subreports "$html_index"
        cat <<'TOML'
[[sections]]
id = "tools"
kind = "provenance"
title.zh = "工具、来源与交付文件"
title.en = "Tools, Sources, and Deliverables"
note.zh = "保留工具版本、来源链接、图表索引和 HTML payload 索引，便于审计和复现。"
note.en = "Keeps tool versions, source links, plot index, and HTML payload index for audit and reproducibility."

TOML
        emit_table_preview "tools-source-links" "04_reports/tool_links.tsv" "Tool source links" "工具来源链接" 16
        emit_table_preview "tools-versions" "04_reports/versions.tsv" "Version table" "版本表" 16
        emit_table_preview "tools-plot-index" "04_reports/plot_files.tsv" "Plot index" "图表索引" 16
        emit_table_preview "tools-html-index" "04_reports/html_reports.tsv" "HTML subreport index" "HTML 子报告索引" 16
    } > "$spec"

    render_from_spec "$fixture" "$source_root" "$spec" 50000000 53
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    grep -F "TAFFISH RNA-seq full reference report" "$report" >/dev/null
    grep -F "de.top_genes_expression.png" "$report" >/dev/null
    grep -F "enrichment.gsea_enrichment_curves.png" "$report" >/dev/null
    grep -F "FastQC WT_12" "$report" >/dev/null
    grep -F "FastQC SNF2KO_12" "$report" >/dev/null
    grep -F "alignment_qc.qualimap_WT_12" "$report" >/dev/null
    grep -F "report.interpretation" "$report" >/dev/null
    grep -F "data-open-subreport=\"native-expression-fastqc-wt-12\"" "$report" >/dev/null
    grep -F "data-interactive-plot" "$report" >/dev/null
    grep -F "de-interactive-volcano" "$report" >/dev/null
    grep -F "de-interactive-ma" "$report" >/dev/null
    grep -F "enrichment-interactive-ora" "$report" >/dev/null
    grep -F "data-interactive-plot-payload" "$report" >/dev/null
    grep -F 'data-taffish-runtime="echarts-6.1.0"' "$report" >/dev/null
    assert_interactive_plot_layout "$report"
}

render_rnaseq_denovo() {
    local fixture="rnaseq-denovo"
    local source_root
    source_root=$(require_root "$rnaseq_denovo_source" "$fixture")
    local spec="$(fixture_work_dir "$fixture")/report.full.toml"
    local html_index="$source_root/04_reports/html_reports.tsv"

    for required in \
        "$source_root/04_reports/project_summary.tsv" \
        "$source_root/04_reports/key_metrics.tsv" \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/04_reports/tool_links.tsv" \
        "$source_root/04_reports/plot_files.tsv" \
        "$html_index" \
        "$source_root/03_results/collected_tables/standard.subflows.subflows.tsv" \
        "$source_root/03_results/collected_tables/denovo_assembly.summary.assembly_summary.tsv" \
        "$source_root/03_results/collected_tables/denovo_expression.summary.expression_summary.tsv" \
        "$source_root/03_results/collected_tables/denovo_annotation.summary.annotation_summary.tsv" \
        "$source_root/03_results/collected_tables/de.summary.de_summary.tsv" \
        "$source_root/03_results/collected_tables/enrichment.summary.enrichment_summary.tsv"
    do
        require_file "$required"
    done

    mkdir -p "$(dirname "$spec")"
    {
        cat <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
template_version = "real-run-current"
language_default = "zh"

[project]
flow_name = "rnaseq-standard-flow"
flow_version = "0.3.0-r1"
analysis_mode = "denovo"
title.zh = "TAFFISH RNA-seq 无参分析完整报告"
title.en = "TAFFISH RNA-seq full de novo report"
subtitle.zh = "基于 yeast SNF2 24 样本真实无参示例输出，完整嵌入组装、表达、注释、DE/富集图、MultiQC、FastQC 和解释报告。"
subtitle.en = "A full renderer-driven reproduction of the yeast SNF2 24-sample de novo example, embedding assembly, expression, annotation, DE/enrichment plots, MultiQC, FastQC, and interpretation reports."

[provenance]
versions = "04_reports/versions.tsv"
template_version = "04_reports/report_template_version.txt"
interpretation_report = "04_reports/report_interpretation.html"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "项目总览"
title.en = "Executive Summary"
note.zh = "从真实 yeast-denovo-standard-report 结果树收集关键指标、项目摘要和流程完成状态。"
note.en = "Collects key metrics, project summary, and flow completion status from the real yeast-denovo-standard-report result tree."

[[sections.components]]
type = "dashboard_cards"
id = "overview-key-metrics"
source = "04_reports/key_metrics.tsv"

TOML
        emit_table_preview "overview-project-summary" "04_reports/project_summary.tsv" "Project summary and collection status" "项目摘要与收集状态" 14
        emit_table_preview "overview-flow-summary" "04_reports/flow_summary.tsv" "Flow summary" "Flow summary" 12
        cat <<'TOML'
[[sections]]
id = "workflow"
kind = "workflow"
title.zh = "分析流程与生物学问题"
title.en = "Workflow and Biological Questions"
note.zh = "无参路线从 FASTQ 出发，先组装转录组，再对组装转录本定量、注释、差异分析、富集和报告汇总。"
note.en = "The de novo route starts from FASTQ, assembles transcripts, quantifies against assembled transcripts, annotates them, then performs DE, enrichment, and reporting."

[[sections.components]]
type = "workflow_diagram"
id = "workflow-subflows"
source = "03_results/collected_tables/standard.subflows.subflows.tsv"

[[sections.components]]
type = "status_grid"
id = "workflow-module-status"
source = "03_results/collected_tables/standard.subflows.subflows.tsv"

TOML
        emit_table_preview "workflow-subflow-table" "03_results/collected_tables/standard.subflows.subflows.tsv" "Subflow outputs" "子流程输出" 12
        cat <<'TOML'
[[sections]]
id = "reference"
kind = "workflow"
title.zh = "参考构建"
title.en = "Reference Preparation"
note.zh = "无参模式不提供 reference 输出，这是预期行为：被量化和检验的 feature 空间来自组装 transcript，而不是基因组注释。"
note.en = "Reference outputs are intentionally absent in de novo mode: the quantified and tested feature space comes from assembled transcripts rather than genome annotation."

TOML
        emit_table_preview "reference-denovo-mode" "04_reports/project_summary.tsv" "De novo mode and reference-branch status" "无参模式与 reference 分支状态" 16
        cat <<'TOML'
[[sections]]
id = "denovo"
kind = "workflow"
title.zh = "无参组装、表达与注释"
title.en = "De novo Assembly, Expression, and Annotation"
note.zh = "这是无参报告的核心分支：组装、表达矩阵、同源注释、GO gene set 和 background 都在这里汇总。"
note.en = "This is the core branch of the de novo report: assembly, expression matrix, homology annotation, GO gene sets, and background are summarized here."

TOML
        emit_table_preview "denovo-assembly-summary" "03_results/collected_tables/denovo_assembly.summary.assembly_summary.tsv" "Transcriptome assembly" "Transcriptome assembly" 10
        emit_table_preview "denovo-assembly-stats" "03_results/collected_tables/denovo_assembly.assembly_stats.assembly_stats.tsv" "Assembly statistics" "组装统计" 10
        emit_table_preview "denovo-expression-summary" "03_results/collected_tables/denovo_expression.summary.expression_summary.tsv" "De novo expression summary" "无参表达摘要" 10
        emit_table_preview "denovo-annotation-summary" "03_results/collected_tables/denovo_annotation.summary.annotation_summary.tsv" "Annotation summary" "Annotation summary" 10
        emit_table_preview "denovo-annotation-hits" "03_results/collected_tables/denovo_annotation.protein_hits.protein_hits.tsv" "Protein hit preview" "蛋白同源命中预览" 10 8000
        cat <<'TOML'
[[sections]]
id = "de"
kind = "differential_expression"
title.zh = "差异表达"
title.en = "Differential Expression"
note.zh = "无参路线中的差异分析基于 assembled transcript count-like matrix；这里保留 PCA、样本相关性、火山图和完整差异表。"
note.en = "The de novo DE layer uses the assembled-transcript count-like matrix and keeps PCA, sample correlation, volcano, and full DE tables."

TOML
        emit_rnaseq_plot_cards
        emit_interactive_plot "de-interactive-volcano" "volcano" "03_results/collected_tables/de.results.results.tsv" "Interactive volcano explorer" "交互火山图浏览器" "Review transcript-level DESeq2 result rows with adjustable padj and log2FC display cutoffs. This only changes the browser view of already-computed rows." "用可调 padj 和 log2FC 展示阈值审阅 transcript-level DESeq2 结果行；这只改变已计算结果的浏览器视图。"
        emit_interactive_plot "de-interactive-ma" "ma" "03_results/collected_tables/de.results.results.tsv" "Interactive MA explorer" "交互 MA 图浏览器" "Browse expression strength versus log fold change with the same already-computed transcript-level DESeq2 rows." "基于同一批已计算 transcript-level DESeq2 结果行浏览表达强度与 log fold change 的关系。"
        if [ -s "$source_root/03_results/collected_tables/de.pca_scores.pca_scores.tsv" ]; then
            emit_interactive_pca_plot "de-interactive-pca" "03_results/collected_tables/de.pca_scores.pca_scores.tsv" "Interactive PCA explorer" "交互 PCA 图浏览器" "Browse already-computed PCA sample coordinates without recalculating PCA." "浏览已计算的 PCA 样本坐标，不重新计算 PCA。"
        fi
        emit_table_preview "de-summary" "03_results/collected_tables/de.summary.de_summary.tsv" "DE summary" "差异表达摘要" 12
        emit_table_preview "de-results" "03_results/collected_tables/de.results.results.tsv" "DESeq2 full result preview" "DESeq2 完整结果预览" 10 8000
        emit_table_preview "de-significant-genes" "03_results/collected_tables/de.significant_genes.significant_genes.tsv" "Significant transcripts" "显著差异 transcript" 12
        cat <<'TOML'
[[sections]]
id = "enrichment"
kind = "enrichment"
title.zh = "功能富集"
title.en = "Functional Enrichment"
note.zh = "无参报告中富集分析必须使用与 transcript-level DE 一致的 ID 空间；这里保留 annotation-derived GMT/background 的完整结果摘要。"
note.en = "In de novo reports, enrichment must use the same transcript-ID space as transcript-level DE; this section keeps the annotation-derived GMT/background result summary."

TOML
        emit_interactive_plot "enrichment-interactive-ora" "ora_dotplot" "03_results/collected_tables/enrichment.ora_results.ora_results.tsv" "Interactive ORA dot plot" "交互 ORA 气泡图" "Filter already-computed transcript-level ORA terms by adjusted p-value and Top N without recomputing enrichment." "按校正 p 值和 Top N 筛选已计算 transcript-level ORA 条目，不重新计算富集。" 20
        emit_table_preview "enrichment-summary" "03_results/collected_tables/enrichment.summary.enrichment_summary.tsv" "Enrichment summary" "富集摘要" 12
        emit_table_preview "enrichment-ora-results" "03_results/collected_tables/enrichment.ora_results.ora_results.tsv" "ORA results" "ORA 结果" 10 5000
        emit_table_preview "enrichment-gsea-results" "03_results/collected_tables/enrichment.gsea_results.gsea_results.tsv" "GSEA results" "GSEA 结果" 10 5000
        cat <<'TOML'
[[sections]]
id = "native-reports"
kind = "native_reports"
title.zh = "原生 QC 与解释报告"
title.en = "Native QC and Interpretation Reports"
note.zh = "完整声明真实无参报告收集到的 MultiQC、FastQC 和解释报告；renderer 会把本地 HTML payload 打包进单文件报告。"
note.en = "Declares the full set of collected MultiQC, FastQC, and interpretation reports from the real de novo output; the renderer bundles their local HTML payloads into the standalone report."

TOML
        emit_rnaseq_native_subreports "$html_index"
        cat <<'TOML'
[[sections]]
id = "tools"
kind = "provenance"
title.zh = "工具、来源与交付文件"
title.en = "Tools, Sources, and Deliverables"
note.zh = "保留工具版本、来源链接、图表索引和 HTML payload 索引，便于审计和复现。"
note.en = "Keeps tool versions, source links, plot index, and HTML payload index for audit and reproducibility."

TOML
        emit_table_preview "tools-source-links" "04_reports/tool_links.tsv" "Tool source links" "工具来源链接" 16
        emit_table_preview "tools-versions" "04_reports/versions.tsv" "Version table" "版本表" 16
        emit_table_preview "tools-plot-index" "04_reports/plot_files.tsv" "Plot index" "图表索引" 16
        emit_table_preview "tools-html-index" "04_reports/html_reports.tsv" "HTML subreport index" "HTML 子报告索引" 16
    } > "$spec"

    render_from_spec "$fixture" "$source_root" "$spec" 30000000 27
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    grep -F "TAFFISH RNA-seq full de novo report" "$report" >/dev/null
    grep -F "denovo_assembly.summary.assembly_summary.tsv" "$report" >/dev/null
    grep -F "denovo_annotation.protein_hits.protein_hits.tsv" "$report" >/dev/null
    grep -F "enrichment.ora_results.ora_results.tsv" "$report" >/dev/null
    grep -F "TRINITY_DN" "$report" >/dev/null
    grep -F "denovo_expression.fastqc_WT_12" "$report" >/dev/null
    grep -F "report.interpretation" "$report" >/dev/null
    grep -F "data-interactive-plot" "$report" >/dev/null
    grep -F "de-interactive-volcano" "$report" >/dev/null
    grep -F "de-interactive-ma" "$report" >/dev/null
    grep -F "enrichment-interactive-ora" "$report" >/dev/null
    grep -F "data-interactive-plot-payload" "$report" >/dev/null
    grep -F 'data-taffish-runtime="echarts-6.1.0"' "$report" >/dev/null
    assert_interactive_plot_layout "$report"
}

render_chengdu_yuanda_report12() {
    local fixture="chengdu-yuanda-report12"
    local source_root
    source_root=$(require_root "$chengdu_yuanda_report12_source" "$fixture")
    local spec="$source_root/report.toml"

    for required in \
        "$source_root/report.toml" \
        "$source_root/04_reports/flow_summary.tsv" \
        "$source_root/04_reports/versions.tsv" \
        "$source_root/04_reports/methods.txt" \
        "$source_root/03_results/tables/pufa_structure_comparison_all_domains.domain_differentiation_summary.tsv" \
        "$source_root/03_results/tables/pufa_structure_comparison_all_domains.motif_sites_on_target.tsv" \
        "$source_root/03_results/tables/pufa_structure_comparison_all_domains.overlay_pdb_manifest.tsv" \
        "$source_root/03_results/tables/pufa_structure_comparison_all_domains.overlay_priority_summary.tsv" \
        "$source_root/03_results/tables/pufa_structure_comparison_all_domains.foldseek_structural_similarity.tsv" \
        "$source_root/03_results/figures/pufa_structure_comparison_all_domains.fig3_foldseek_alntmscore.png" \
        "$source_root/03_results/figures/pufa_structure_comparison_all_domains.fig3_foldseek_identity.png" \
        "$source_root/03_results/structure_figures/pufa_structure_comparison_all_domains.target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1.target_epa_dha_overlay.png" \
        "$source_root/03_results/structure_figures/pufa_structure_comparison_all_domains.target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1.motif_on_structure.png" \
        "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/target.pdb" \
        "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/epa_EPA_shewanella_pneumatophori_scrc2738_PfaB_AT_MAT_AT_MAT_1.aligned.pdb" \
        "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/dha_DHA_aurantiochytrium_l_bl10_OrfB_AT_MAT_AT_MAT_1.aligned.pdb"
    do
        require_file "$required"
    done

    render_from_spec "$fixture" "$source_root" "$spec" 25000000 0
    local report="$(fixture_work_dir "$fixture")/04_reports/taffish_report.html"
    local files_index="$(fixture_work_dir "$fixture")/04_reports/report_files.tsv"
    grep -F "Chengdu Yuanda PUFA Structure Comparison Report 12" "$report" >/dev/null
    grep -F "data-structure-viewer" "$report" >/dev/null
    grep -F "data-structure-payload" "$report" >/dev/null
    grep -F '"models"' "$report" >/dev/null
    grep -F '"pdbText"' "$report" >/dev/null
    grep -F 'data-taffish-runtime="ngl"' "$report" >/dev/null
    grep -F "data-structure-ngl-stage" "$report" >/dev/null
    grep -F "handleResize" "$report" >/dev/null
    grep -F "requestRender" "$report" >/dev/null
    grep -F "structure-static-image-button" "$report" >/dev/null
    grep -F "data-open-image=\"overlay-target-schizochytrium-company-orfb-at-mat-at-mat-1-static\"" "$report" >/dev/null
    grep -F "target | Schizochytrium | OrfB AT/MAT" "$report" >/dev/null
    grep -F "EPA | S_pneumatophori_scrc2738 | PfaB AT/MAT" "$report" >/dev/null
    grep -F "DHA | aurantiochytrium_l_bl10 | OrfB AT/MAT" "$report" >/dev/null
    grep -F "pufa_structure_comparison_all_domains.foldseek_structural_similarity.tsv" "$report" >/dev/null
    grep -F "pufa_structure_comparison_all_domains.fig3_foldseek_identity.png" "$files_index" >/dev/null
    grep -F "target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1.target_epa_dha_overlay.png" "$files_index" >/dev/null
    grep -F "target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/target.pdb" "$files_index" >/dev/null
    grep -F $'runtime\t' "$files_index" >/dev/null
    awk -F '\t' 'NR>1 && $1=="image"{n++} END{exit(n>=31 ? 0 : 1)}' "$files_index"
    awk -F '\t' 'NR>1 && $1=="pdb"{n++} END{exit(n>=33 ? 0 : 1)}' "$files_index"
    awk -F '\t' 'NR>1 && $1=="table"{n++} END{exit(n>=16 ? 0 : 1)}' "$files_index"
}

render_component_basic_components() {
    local fixture="component-basic-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root="$fixture_dir/source"
    local spec="$fixture_dir/report.full.toml"
    mkdir -p "$source_root/03_results/plots" "$source_root/03_results/tables" "$source_root/03_results/html" "$source_root/04_reports" "$(dirname "$spec")"
    cat > "$source_root/04_reports/flow_summary.tsv" <<'TSV'
metric	value
component_family	basic
tables	2
plots	1
native_html	1
TSV
    cat > "$source_root/04_reports/module_status.tsv" <<'TSV'
module	status	message_en	message_zh
dashboard	OK	Dashboard cards render from TSV.	Dashboard card 可以从 TSV 渲染。
table	OK	Tables stay inside their card with scroll controls.	表格保持在卡片内并带滚动控制。
native_html	OK	Native HTML is embedded and opened as a local page.	原生 HTML 会内嵌并作为本地页面打开。
TSV
    cat > "$source_root/04_reports/quality_gates.tsv" <<'TSV'
gate	status	criterion_en	criterion_zh	message_en	message_zh
standalone	OK	No external required assets	无必需外部资源	CSS, JS, logo, plot and native HTML are embedded.	CSS、JS、logo、图和原生 HTML 均已内嵌。
layout	OK	Cards do not overflow	卡片不溢出	Long paths and table values wrap or scroll inside the component.	长路径和表格值在组件内部换行或滚动。
TSV
    cat > "$source_root/03_results/tables/long_table.tsv" <<'TSV'
id	description	value	note_en	note_zh
row_001	A compact row used as a preview.	42	English note for row 001.	第 001 行中文说明。
row_002	A very long value that should not force the card to expand outside the report shell because it represents a common bioinformatics path or annotation payload.	84	English note for row 002.	第 002 行中文说明。
row_003	Another row retained for in-place expansion and search.	126	English note for row 003.	第 003 行中文说明。
TSV
    cat > "$source_root/03_results/plots/basic.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 420">
  <rect width="720" height="420" rx="24" fill="#f4f8f7"/>
  <path d="M80 330 C160 140 260 260 340 110 S520 210 640 80" fill="none" stroke="#087f74" stroke-width="18" stroke-linecap="round"/>
  <circle cx="80" cy="330" r="18" fill="#2b8cbe"/>
  <circle cx="640" cy="80" r="18" fill="#d95f02"/>
  <text x="80" y="70" font-family="Arial,sans-serif" font-size="32" fill="#0b2530">Embedded SVG plot</text>
</svg>
SVG
    local native_html_source="$app_root/testdata/fixtures/ngs-qc/03_results/html/P1.fastp.html"
    require_file "$native_html_source"
    cp "$native_html_source" "$source_root/03_results/html/native.html"
    cat > "$source_root/04_reports/methods.txt" <<'TEXT'
This is a component-regression fixture. It is generated only from TOML and local data assets.
TEXT
    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-regression-basic"
title.en = "Basic component regression test"
title.zh = "基础组件库测试"
subtitle.en = "A TOML-only report covering dashboard, status, quality gates, table, plot, code and native HTML components."
subtitle.zh = "仅通过 TOML 生成，覆盖 dashboard、状态、质量门、表格、图片、文本和原生 HTML 组件。"

[[sections]]
id = "overview"
kind = "overview"
title.en = "Overview"
title.zh = "总览"

[[sections.components]]
type = "dashboard_cards"
id = "cards"
source = "04_reports/flow_summary.tsv"

[[sections.components]]
type = "status_grid"
id = "status"
source = "04_reports/module_status.tsv"

[[sections]]
id = "checks"
kind = "quality_control"
title.en = "Quality Gates"
title.zh = "质量门"

[[sections.components]]
type = "quality_gate_table"
id = "quality-gates"
source = "04_reports/quality_gates.tsv"

[[sections.components]]
type = "table_preview"
id = "long-table"
source = "03_results/tables/long_table.tsv"
preview_rows = 2
embed_full = true
max_embed_rows = 100
max_embed_bytes = 200000
title.en = "Table preview with long values"
title.zh = "包含长值的表格预览"

[[sections.components]]
type = "plot_card"
id = "basic-plot"
image = "03_results/plots/basic.svg"
title.en = "Embedded SVG plot"
title.zh = "内嵌 SVG 图"
caption.en = "The plot should use the common plot card and image lightbox."
caption.zh = "该图应使用统一 plot card 和大图查看。"

[[sections.components]]
type = "code_file"
id = "methods"
source = "04_reports/methods.txt"
language = "text"
copy = true
title.en = "Methods text"
title.zh = "方法文本"

[[sections.components]]
type = "native_subreport"
id = "native"
kind = "html"
path = "03_results/html/native.html"
embed_policy = "auto"
title.en = "Native HTML payload"
title.zh = "原生 HTML payload"
TOML
    render_from_spec "$fixture" "$source_root" "$spec" 200000 1
    local report="$fixture_dir/04_reports/taffish_report.html"
    grep -F "Basic component regression test" "$report" >/dev/null
    grep -F "data-open-image" "$report" >/dev/null
    grep -F "data-open-subreport=\"native\"" "$report" >/dev/null
    grep -F "data-cell-value=" "$report" >/dev/null
}

render_component_media_layout() {
    local fixture="component-media-layout-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root="$fixture_dir/source"
    local spec="$fixture_dir/report.full.toml"
    local phylogeny_image="$phylogeny_source/03_results/tree/plots/rectangular/tree.png"
    local rnaseq_image="$rnaseq_reference_source/03_results/collected_plots/de.heatmap.png"
    local structure_image="$chengdu_yuanda_report12_source/03_results/figures/pufa_structure_comparison_all_domains.fig2_structure_confidence.png"

    require_file "$phylogeny_image"
    require_file "$rnaseq_image"
    require_file "$structure_image"
    mkdir -p "$source_root/03_results/figures" "$source_root/04_reports" "$(dirname "$spec")"
    cp "$phylogeny_image" "$source_root/03_results/figures/phylogeny-rectangular-tree.png"
    cp "$rnaseq_image" "$source_root/03_results/figures/rnaseq-de-heatmap.png"
    cp "$structure_image" "$source_root/03_results/figures/pufa-structure-confidence.png"

    cat > "$source_root/04_reports/flow_summary.tsv" <<'TSV'
metric	value
component_family	plot_card-media
real_images	3
media_cards	4
legacy_cards	2
TSV

    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-media-layout-report"
title.en = "Scientific media-layout regression"
title.zh = "科研图文 media 布局回归"
subtitle.en = "A TOML-only report using real phylogeny, RNA-seq and protein-structure figures to verify safe horizontal image-and-text cards."
subtitle.zh = "仅通过 TOML 使用真实系统发育、RNA-seq 与蛋白结构图片，验证安全的横向图文卡片。"

[[sections]]
id = "media-cards"
kind = "results"
title.en = "Horizontal scientific narratives"
title.zh = "横向科研图文叙事"
note.en = "Each media card owns one row. The image and explanation stay close without changing the established grid and wide layouts."
note.zh = "每个 media 卡片独占一行，让图片与解释保持邻近，同时不改变既有 grid 和 wide 布局。"

[[sections.components]]
type = "plot_card"
id = "media-default-ratio"
image = "03_results/figures/phylogeny-rectangular-tree.png"
layout = "media"
title.en = "Reference phylogeny and its biological interpretation"
title.zh = "参考系统发育树及其生物学解释"
note.en = "The default 0.42 image ratio keeps the complete rectangular tree visible while reserving enough room to explain topology, branch length and support. This layout is intended for contextual or conceptual figures rather than dense axis-heavy result plots."
note.zh = "默认 0.42 图片比例可完整展示矩形系统发育树，同时为拓扑、枝长与支持度解读保留足够空间。该布局主要用于背景或概念型图片，而非坐标轴密集的正式结果图。"
zoom = true
default_fit = "contain"

[[sections.components]]
type = "plot_card"
id = "media-right-portrait"
image = "03_results/figures/pufa-structure-confidence.png"
layout = "media"
image_position = "right"
media_image_ratio = 0.30
media_vertical_align = "start"
media_gap = "compact"
title.en = "Tall protein-structure confidence figure"
title.zh = "纵向蛋白结构置信度图"
note.en = "A narrow right-hand image column is useful for this genuinely tall confidence panel. The renderer preserves the full image with object-fit contain; no crop, arbitrary CSS expression or report-specific HTML patch is used."
note.zh = "这张真实纵向置信度图适合使用较窄的右侧图片栏。renderer 通过 object-fit contain 保留完整图片，不裁切、不接受任意 CSS 表达式，也不使用项目专用 HTML 补丁。"
zoom = true
default_fit = "contain"

[[sections.components]]
type = "plot_card"
id = "media-centered-transparent"
image = "03_results/figures/rnaseq-de-heatmap.png"
layout = "media"
image_position = "left"
media_image_ratio = 0.50
media_vertical_align = "center"
media_gap = "relaxed"
title.en = "Differential-expression heatmap with a deliberately long bilingual explanation"
title.zh = "带有较长双语说明的差异表达热图"
note.en = "This real RNA-seq heatmap verifies center alignment and resilient wrapping. Long links such as https://github.com/taffish/taffish-report-render/tree/main/docs and uninterrupted identifiers such as TAFFISH_REPORT_RENDER_MEDIA_LAYOUT_UNINTERRUPTED_IDENTIFIER_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 must remain inside the text column without widening the report or hiding the image actions."
note.zh = "这张真实 RNA-seq 热图用于验证居中对齐和稳健换行。长链接与连续标识符必须始终留在文字栏内，不能撑宽报告、遮挡图片操作，也不能造成横向滚动。"
caption.en = "Use the lightbox for detailed labels; the image remains embedded in the standalone HTML."
caption.zh = "可通过大图模式阅读密集标签；图片仍完整内嵌在单文件 HTML 中。"
zoom = true
default_fit = "contain"

[[sections.components]]
type = "plot_card"
id = "media-upper-bound"
image = "03_results/figures/phylogeny-rectangular-tree.png"
layout = "media"
image_position = "right"
media_image_ratio = 0.70
media_vertical_align = "start"
media_gap = "normal"
title.en = "Upper safe image ratio"
title.zh = "安全图片比例上界"
note.en = "The validated upper boundary gives the figure more room while preserving a readable explanation column."
note.zh = "经过校验的比例上界为图片提供更多空间，同时仍保留可读的说明栏。"
zoom = true
default_fit = "contain"

[[sections]]
id = "legacy-layouts"
kind = "results"
title.en = "Historical layout compatibility"
title.zh = "历史布局兼容性"
note.en = "The same report mixes media with unchanged grid and wide plot cards."
note.zh = "同一报告同时混排 media 与行为不变的 grid、wide 图片卡片。"

[[sections.components]]
type = "plot_card"
id = "legacy-grid"
image = "03_results/figures/rnaseq-de-heatmap.png"
layout = "grid"
title.en = "Legacy grid card"
title.zh = "历史 grid 卡片"
note.en = "This card remains in the ordinary plot grid."
note.zh = "该卡片继续进入普通图片网格。"

[[sections.components]]
type = "plot_card"
id = "legacy-wide"
image = "03_results/figures/phylogeny-rectangular-tree.png"
layout = "wide"
note_position = "top"
title.en = "Legacy wide scientific figure"
title.zh = "历史 wide 科学结果图"
note.en = "Dense scientific plots may keep the established full-width layout with the note above the figure."
note.zh = "坐标与标签密集的科学结果图仍可保持既有全宽布局，并把说明放在图片上方。"
TOML

    render_from_spec "$fixture" "$source_root" "$spec" 900000 0
    local report="$fixture_dir/04_reports/taffish_report.html"
    local files_index="$fixture_dir/04_reports/report_files.tsv"
    test "$(grep -o 'class="plot-card plot-card-media' "$report" | wc -l | tr -d ' ')" = "4"
    test "$(grep -o 'class="plot-media-stack"' "$report" | wc -l | tr -d ' ')" = "1"
    grep -F 'data-media-image-ratio="0.42"' "$report" >/dev/null
    grep -F 'data-media-image-ratio="0.3"' "$report" >/dev/null
    grep -F 'data-media-image-ratio="0.5"' "$report" >/dev/null
    grep -F 'data-media-image-ratio="0.7"' "$report" >/dev/null
    grep -F 'plot-media-image-right' "$report" >/dev/null
    grep -F 'plot-media-align-center' "$report" >/dev/null
    grep -F 'plot-media-gap-relaxed' "$report" >/dev/null
    grep -F '@media (max-width: 820px)' "$report" >/dev/null
    grep -F 'grid-template-areas:' "$report" >/dev/null
    grep -F '      "image"' "$report" >/dev/null
    grep -F '      "copy"' "$report" >/dev/null
    grep -F 'TAFFISH_REPORT_RENDER_MEDIA_LAYOUT_UNINTERRUPTED_IDENTIFIER_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' "$report" >/dev/null
    grep -F 'data-open-image="media-centered-transparent"' "$report" >/dev/null
    grep -F 'data:image/png;base64,' "$report" >/dev/null
    grep -F 'legacy-grid' "$report" >/dev/null
    grep -F 'plot-card-wide' "$report" >/dev/null
    grep -F 'phylogeny-rectangular-tree.png' "$files_index" >/dev/null
    grep -F 'rnaseq-de-heatmap.png' "$files_index" >/dev/null
    grep -F 'pufa-structure-confidence.png' "$files_index" >/dev/null
}

render_component_echarts() {
    local fixture="component-echarts-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root="$fixture_dir/source"
    local spec="$fixture_dir/report.full.toml"
    mkdir -p "$source_root/03_results/tables" "$source_root/04_reports" "$(dirname "$spec")"
    cat > "$source_root/03_results/tables/de.tsv" <<'TSV'
gene_id	baseMean	log2FoldChange	pvalue	padj
geneA	100	2.5	0.0001	0.001
geneB	80	-2.1	0.0002	0.002
geneC	30	0.2	0.5	0.8
geneD	160	1.7	0.003	0.02
geneE	95	-1.6	0.004	0.03
TSV
    cat > "$source_root/03_results/tables/pca.tsv" <<'TSV'
sample	condition	PC1	PC2
WT_01	WT	-2.1	0.4
WT_02	WT	-1.8	-0.2
SNF2KO_01	SNF2KO	2.2	0.6
SNF2KO_02	SNF2KO	1.9	-0.5
TSV
    cat > "$source_root/03_results/tables/ora.tsv" <<'TSV'
ID	Description	GeneRatio	BgRatio	pvalue	p.adjust	Count
GO:0001	rRNA processing [biological_process]	3/20	40/500	0.0001	0.001	3
GO:0002	cell wall organization [biological_process]	2/20	30/500	0.004	0.02	2
GO:0003	oxidative stress response [biological_process]	1/20	20/500	0.2	0.4	1
TSV
    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-component-echarts-report"
title.en = "ECharts interactive plot library test"
title.zh = "ECharts 交互图组件库测试"

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
height = 500
title.en = "Interactive volcano"
title.zh = "交互火山图"

[[sections.components]]
type = "interactive_plot"
id = "ma"
kind = "ma"
source = "03_results/tables/de.tsv"
default_padj = 0.05
default_log2fc = 1
height = 500
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
height = 500
title.en = "Interactive PCA"
title.zh = "交互 PCA 图"

[[sections.components]]
type = "interactive_plot"
id = "ora"
kind = "ora_dotplot"
source = "03_results/tables/ora.tsv"
default_padj = 0.05
top_n = 10
height = 500
title.en = "Interactive ORA"
title.zh = "交互 ORA 图"
TOML
    render_from_spec "$fixture" "$source_root" "$spec" 900000 0
    local report="$fixture_dir/04_reports/taffish_report.html"
    grep -F 'data-taffish-runtime="echarts-6.1.0"' "$report" >/dev/null
    grep -F '"kind":"volcano"' "$report" >/dev/null
    grep -F '"kind":"ma"' "$report" >/dev/null
    grep -F '"kind":"pca"' "$report" >/dev/null
    grep -F '"kind":"ora_dotplot"' "$report" >/dev/null
    assert_interactive_plot_layout "$report"
}

render_component_tree_alignment() {
    local fixture="component-tree-alignment-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root="$fixture_dir/source"
    local spec="$fixture_dir/report.full.toml"
    mkdir -p "$source_root/03_results/tree" "$source_root/03_results/alignment" "$source_root/04_reports" "$(dirname "$spec")"
    cat > "$source_root/03_results/tree/library.nwk" <<'NEWICK'
((sample_A:0.0123,sample_B:0.0188)node1:0.04,(sample_C:0.02,sample_D:0.031)node2:0.05)root;
NEWICK
    cat > "$source_root/03_results/alignment/library.fa" <<'FASTA'
>sample_A
ATGCCGTTAACCGGTTAA--
>sample_B
ATGCCGTTAACTGGTTAA--
>sample_C
ATGCCATTAACCGGCTAA--
>sample_D
ATGCCATTAACCGGCTAACC
FASTA
    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-component-tree-alignment-report"
title.en = "Tree and alignment component regression test"
title.zh = "树和多序列比对组件库测试"

[[sections]]
id = "tree"
kind = "phylogeny"
title.en = "Tree and alignment"
title.zh = "树与比对"

[[sections.components]]
type = "tree_viewer"
id = "tree-viewer"
source = "03_results/tree/library.nwk"
height = 420
show_branch_lengths = true
branch_color = "#087f74"
label_color = "#10252c"
scale_color = "#63757d"
background = "#fbfdfc"
branch_width = 2.4
label_size = 13
title.en = "Inline Newick tree"
title.zh = "内联 Newick 树"

[[sections.components]]
type = "sequence_alignment"
id = "alignment-viewer"
source = "03_results/alignment/library.fa"
format = "fasta"
alphabet = "dna"
color_scheme = "classic"
font_size = 14
label_width = 180
residue_a = "#dff5ec"
residue_c = "#ddeeff"
residue_g = "#fff2c8"
residue_t = "#ffe0dc"
gap_color = "#edf3f2"
show_consensus = true
max_sequences = 12
max_columns = 120
title.en = "Inline FASTA alignment"
title.zh = "内联 FASTA 比对"
TOML
    render_from_spec "$fixture" "$source_root" "$spec" 200000 0
    local report="$fixture_dir/04_reports/taffish_report.html"
    grep -F "data-tree-viewer" "$report" >/dev/null
    grep -F "data-sequence-alignment" "$report" >/dev/null
    grep -F -- "--tree-branch-color:#087f74" "$report" >/dev/null
    grep -F "alignment-scheme-classic" "$report" >/dev/null
    grep -F -- "--alignment-font-size:14px" "$report" >/dev/null
    grep -F "sample_D" "$report" >/dev/null
}

render_component_igv() {
    local fixture="component-igv-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root="$fixture_dir/source"
    local spec="$fixture_dir/report.full.toml"
    local yeast_ref_root="$hub_root/repos/apps/bio/flows/rna-seq/test-data/yeast/data/03_results/yeast-reference-sgd-r64.4.1-v1/reference"
    local yeast_fasta="$yeast_ref_root/genome/yeast_s288c_reference_genome_R64-4-1.fa"
    local yeast_gff="$yeast_ref_root/annotation/yeast_s288c_gene_annotation_R64-4-1.gff3"
    if [ ! -s "$yeast_fasta" ] || [ ! -s "$yeast_gff" ]; then
        cat >&2 <<EOF
ERROR: component-igv-report requires the central yeast reference FASTA/GFF3 fixture.

Missing one of:
  $yeast_fasta
  $yeast_gff

Prepare it with the RNA-seq yeast data helper before running full real-run:
  taf-rnaseq-yeast-get-data --outdir <yeast-data-dir> --stage reference --force

IGV real-run is not allowed to fall back to toy hg38/example.org data.
EOF
        exit 1
    fi
    mkdir -p "$source_root/03_results/genome" "$source_root/03_results/tracks" "$source_root/04_reports" "$(dirname "$spec")"
    python3 - "$yeast_fasta" "$yeast_gff" "$source_root" <<'PY'
from pathlib import Path
import sys
import urllib.parse

fasta = Path(sys.argv[1])
gff = Path(sys.argv[2])
root = Path(sys.argv[3])
genome_dir = root / "03_results" / "genome"
track_dir = root / "03_results" / "tracks"
chrom = "chrI"
start = 1
end = 5000

seq_parts = []
active = False
with fasta.open("rt", encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if line.startswith(">"):
            name = line[1:].split()[0]
            active = name == chrom
            continue
        if active:
            seq_parts.append(line.strip())
sequence = "".join(seq_parts)
if len(sequence) < end:
    raise SystemExit(f"yeast FASTA chromosome {chrom} is too short or missing")
window_seq = sequence[start - 1 : end].upper()

fa_out = genome_dir / "yeast_sgd_chrI_1_5000.fa"
with fa_out.open("wt", encoding="utf-8") as out:
    out.write(f">{chrom}\n")
    for idx in range(0, len(window_seq), 80):
        out.write(window_seq[idx : idx + 80] + "\n")
offset = len(f">{chrom}\n".encode("utf-8"))
(genome_dir / "yeast_sgd_chrI_1_5000.fa.fai").write_text(
    f"{chrom}\t{len(window_seq)}\t{offset}\t80\t81\n",
    encoding="utf-8",
)

def attr_value(attrs: str, key: str) -> str:
    for part in attrs.split(";"):
        if "=" not in part:
            continue
        left, right = part.split("=", 1)
        if left == key:
            return urllib.parse.unquote(right)
    return ""

bed_rows = []
with gff.open("rt", encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 9 or fields[0] != chrom or fields[2] != "gene":
            continue
        g_start = int(fields[3])
        g_end = int(fields[4])
        if g_end < start or g_start > end:
            continue
        name = attr_value(fields[8], "Name") or attr_value(fields[8], "ID") or f"{chrom}:{g_start}-{g_end}"
        score = "0"
        strand = fields[6] if fields[6] in {"+", "-"} else "."
        bed_start = max(g_start, start) - start
        bed_end = min(g_end, end) - start + 1
        bed_rows.append((chrom, bed_start, bed_end, name, score, strand))
if not bed_rows:
    raise SystemExit("did not find yeast gene annotations in chrI:1-5000")

bed_out = track_dir / "yeast_sgd_chrI_1_5000_genes.bed"
bed_out.write_text(
    "\n".join("\t".join(map(str, row)) for row in bed_rows) + "\n",
    encoding="utf-8",
)

bg_rows = []
bin_size = 100
for offset0 in range(0, len(window_seq), bin_size):
    chunk = window_seq[offset0 : offset0 + bin_size]
    gc = (chunk.count("G") + chunk.count("C")) / max(1, len(chunk))
    bg_rows.append((chrom, offset0, offset0 + len(chunk), f"{gc:.3f}"))
bedgraph_out = track_dir / "yeast_sgd_chrI_1_5000_gc.bedgraph"
bedgraph_out.write_text(
    "\n".join("\t".join(map(str, row)) for row in bg_rows) + "\n",
    encoding="utf-8",
)

(root / "03_results" / "igv_fixture_provenance.tsv").write_text(
    "field\tvalue\n"
    f"source_fasta\t{fasta}\n"
    f"source_gff3\t{gff}\n"
    f"locus\t{chrom}:{start}-{end}\n"
    f"genes\t{len(bed_rows)}\n"
    f"gc_bins\t{len(bg_rows)}\n",
    encoding="utf-8",
)
PY
    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-component-igv-report"
title.en = "IGV genome browser library test"
title.zh = "IGV 基因组浏览组件库测试"

[[sections]]
id = "genome"
kind = "result_plots"
title.en = "Genome browser"
title.zh = "基因组浏览器"

[[sections.components]]
type = "genome_browser"
id = "igv-browser"
runtime = "igv"
viewer_mode = "embedded"
viewer_modes = ["embedded", "linked"]
data_mode = "embedded-small-assets"
reference_name = "SGD_R64_chrI_slice"
reference_fasta = "03_results/genome/yeast_sgd_chrI_1_5000.fa"
reference_index = "03_results/genome/yeast_sgd_chrI_1_5000.fa.fai"
embed_reference = true
embed_tracks = true
locus = "chrI:1-5000"
height = 420
title.en = "IGV embedded/link genome browser"
title.zh = "IGV 内嵌/链接轨道浏览器"
note.en = "This single component reviews a real SGD yeast chrI locus with embedded mini FASTA, FAI, gene BED, and GC bedGraph tracks."
note.zh = "这个单一组件审阅真实 SGD 酵母 chrI 小位点，并内嵌 mini FASTA、FAI、gene BED 和 GC bedGraph 轨道。"

[[sections.components.tracks]]
name = "SGD genes chrI:1-5000"
type = "annotation"
format = "bed"
source = "03_results/tracks/yeast_sgd_chrI_1_5000_genes.bed"
color = "#087f74"

[[sections.components.tracks]]
name = "Reference GC content"
type = "wig"
format = "bedgraph"
source = "03_results/tracks/yeast_sgd_chrI_1_5000_gc.bedgraph"
color = "#2563eb"
TOML
    render_from_spec "$fixture" "$source_root" "$spec" 180000 0
    local report="$fixture_dir/04_reports/taffish_report.html"
    local files_index="$fixture_dir/04_reports/report_files.tsv"
    grep -F "data-genome-browser" "$report" >/dev/null
    grep -F "data-genome-browser-payload" "$report" >/dev/null
    grep -F "igv-browser" "$report" >/dev/null
    grep -F ".genome-browser-card.is-live .genome-browser-layout" "$report" >/dev/null
    grep -F ".genome-browser-stage.is-live" "$report" >/dev/null
    grep -F 'card.classList.add("is-live")' "$report" >/dev/null
    grep -F 'stage.classList.add("is-live")' "$report" >/dev/null
    grep -F "overflow: auto" "$report" >/dev/null
    grep -F "padding: 0 12px" "$report" >/dev/null
    if grep -A8 -F ".genome-browser-stage.is-live" "$report" | grep -F "overflow: visible" >/dev/null; then
        echo "ERROR: live IGV stage must not use overflow: visible" >&2
        exit 1
    fi
    test "$(grep -o 'data-genome-browser>' "$report" | wc -l | tr -d ' ')" = "1"
    grep -F '"viewerMode":"embedded"' "$report" >/dev/null
    grep -F '"viewerModes":["embedded","linked"]' "$report" >/dev/null
    grep -F 'data-genome-browser-mode="embedded"' "$report" >/dev/null
    grep -F 'data-genome-browser-mode="linked"' "$report" >/dev/null
    grep -F "genome-browser-fallback-panel" "$report" >/dev/null
    grep -F "SGD genes chrI:1-5000" "$report" >/dev/null
    grep -F "Reference GC content" "$report" >/dev/null
    grep -F "data:text/plain;base64" "$report" >/dev/null
    grep -F "yeast_sgd_chrI_1_5000.fa" "$files_index" >/dev/null
    grep -F "yeast_sgd_chrI_1_5000_genes.bed" "$files_index" >/dev/null
    grep -F "genome-track" "$files_index" >/dev/null
    if grep -F "example.org" "$report" >/dev/null; then
        echo "ERROR: component-igv-report still contains fake example.org URLs" >&2
        exit 1
    fi
}

render_component_ngl_native_html() {
    local fixture="component-ngl-native-report"
    local fixture_dir
    fixture_dir=$(fixture_work_dir "$fixture")
    local source_root
    source_root=$(require_root "$chengdu_yuanda_report12_source" "$fixture")
    local spec="$fixture_dir/report.full.toml"
    mkdir -p "$(dirname "$spec")"
    require_file "$source_root/03_results/structure_figures/pufa_structure_comparison_all_domains.target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1.target_epa_dha_overlay.png"
    require_file "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/target.pdb"
    require_file "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/epa_EPA_shewanella_pneumatophori_scrc2738_PfaB_AT_MAT_AT_MAT_1.aligned.pdb"
    require_file "$source_root/03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/dha_DHA_aurantiochytrium_l_bl10_OrfB_AT_MAT_AT_MAT_1.aligned.pdb"
    require_file "$source_root/03_results/tables/pufa_structure_comparison_all_domains.motif_sites_on_target.tsv"
    require_file "$source_root/03_results/tables/pufa_structure_comparison_all_domains.foldseek_structural_similarity.tsv"
    cat > "$spec" <<'TOML'
schema_version = "0.1"
template = "taffish-flow-report"
language_default = "zh"

[project]
flow_name = "taffish-report-render"
flow_version = "0.2.0-r1"
analysis_mode = "component-ngl-native-report"
title.en = "Real NGL structure component regression"
title.zh = "真实 NGL 结构组件回归"
subtitle.en = "A TOML-only report that reuses a real Chengdu Yuanda target/EPA/DHA PDB overlay, static figure and motif-site table."
subtitle.zh = "仅通过 TOML 复用真实成都圆大 target/EPA/DHA PDB 叠合、静态图和 motif 位点表。"

[[sections]]
id = "structure"
kind = "structure"
title.en = "Target/reference overlay"
title.zh = "目标/参考结构叠合"

[[sections.components]]
type = "table_preview"
id = "foldseek-summary"
source = "03_results/tables/pufa_structure_comparison_all_domains.foldseek_structural_similarity.tsv"
preview_rows = 8
embed_full = true
max_embed_rows = 200
max_embed_bytes = 3000000
title.en = "Foldseek structural similarity"
title.zh = "Foldseek 结构相似性"

[[sections.components]]
type = "structure_viewer"
id = "orfb-at-mat-overlay"
runtime = "ngl"
representation = "cartoon"
static_image = "03_results/structure_figures/pufa_structure_comparison_all_domains.target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1.target_epa_dha_overlay.png"
atom_filter = "ca"
height = 460
max_atoms = 2600
controls_open = false
site_table = "03_results/tables/pufa_structure_comparison_all_domains.motif_sites_on_target.tsv"
site_structure_id = "target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1"
site_model = "target"
site_chain = "A"
site_residue_column = "structure_residue"
site_group_column = "target_state"
site_label_column = "target_residue_label"
site_max_sites = 80
title.en = "target | Schizochytrium | OrfB AT/MAT target versus EPA/DHA reference overlay"
title.zh = "target | Schizochytrium | OrfB AT/MAT target 与 EPA/DHA reference 结构叠合"
note.en = "Black is the target, cyan is the EPA reference, and purple is the DHA reference. Site markers are loaded from the real motif-site table."
note.zh = "黑色为 target，青色为 EPA reference，紫色为 DHA reference。位点球标记来自真实 motif-site 表。"

[[sections.components.models]]
id = "target"
pdb = "03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/target.pdb"
color = "#2b2f33"
label.en = "target | Schizochytrium | OrfB AT/MAT"
label.zh = "target | Schizochytrium | OrfB AT/MAT"

[[sections.components.models]]
id = "epa"
pdb = "03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/epa_EPA_shewanella_pneumatophori_scrc2738_PfaB_AT_MAT_AT_MAT_1.aligned.pdb"
color = "#0b84a5"
label.en = "EPA | S_pneumatophori_scrc2738 | PfaB AT/MAT"
label.zh = "EPA | S_pneumatophori_scrc2738 | PfaB AT/MAT"

[[sections.components.models]]
id = "dha"
pdb = "03_results/overlay_pdb/target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/dha_DHA_aurantiochytrium_l_bl10_OrfB_AT_MAT_AT_MAT_1.aligned.pdb"
color = "#8b5cf6"
label.en = "DHA | aurantiochytrium_l_bl10 | OrfB AT/MAT"
label.zh = "DHA | aurantiochytrium_l_bl10 | OrfB AT/MAT"
TOML
    render_from_spec "$fixture" "$source_root" "$spec" 1000000 0
    local report="$fixture_dir/04_reports/taffish_report.html"
    local files_index="$fixture_dir/04_reports/report_files.tsv"
    grep -F "data-structure-viewer" "$report" >/dev/null
    grep -F "data-taffish-runtime=\"ngl\"" "$report" >/dev/null
    grep -F "pdbText" "$report" >/dev/null
    grep -F '"target"' "$report" >/dev/null
    grep -F '"epa"' "$report" >/dev/null
    grep -F '"dha"' "$report" >/dev/null
    grep -F '"siteGroups"' "$report" >/dev/null
    grep -F "target_schizochytrium_company_OrfB_AT_MAT_AT_MAT_1/target.pdb" "$files_index" >/dev/null
}

check_output_layout() {
    echo "[REAL] output layout checks"
    test -d "$out_root"
    test -d "$flow_out_root"
    test -d "$component_out_root"
    test -s "$index"
    test -s "$flow_index"
    test -s "$component_index"
    if [ "$default_run" = true ]; then
        for expected in "${flow_fixtures[@]}"; do
            if [ ! -d "$flow_out_root/$expected/04_reports" ]; then
                echo "ERROR: missing expected full flow-report output directory: $flow_out_root/$expected/04_reports" >&2
                exit 1
            fi
        done
        for expected in "${component_fixtures[@]}"; do
            if [ ! -d "$component_out_root/$expected/04_reports" ]; then
                echo "ERROR: missing expected component-regression output directory: $component_out_root/$expected/04_reports" >&2
                exit 1
            fi
        done
    fi
    for fixture in "${fixtures[@]}"; do
        local category
        category=$(fixture_category "$fixture")
        local fixture_dir
        fixture_dir=$(fixture_work_dir "$fixture")
        local report_dir="$fixture_dir/04_reports"
        test -d "$fixture_dir"
        test -d "$report_dir"
        test -s "$fixture_dir/report.full.toml"
        test -s "$report_dir/taffish_report.html"
        test -s "$report_dir/report.spec.toml"
        test -s "$report_dir/report.normalized.json"
        test -s "$report_dir/report.manifest.json"
        test -s "$report_dir/report_files.tsv"
        test -s "$report_dir/embedded_html_reports.tsv"
        grep -F "$category	$fixture" "$index" >/dev/null
        grep -F "$fixture" "$(category_index "$category")" >/dev/null
    done
}

for fixture in "${fixtures[@]}"; do
    case "$fixture" in
        ngs-qc)
            render_ngs_qc
            ;;
        bam-qc)
            render_bam_qc
            ;;
        phylogeny)
            render_phylogeny
            ;;
        rnaseq-reference)
            render_rnaseq_reference
            ;;
        rnaseq-denovo)
            render_rnaseq_denovo
            ;;
        chengdu-yuanda-report12)
            render_chengdu_yuanda_report12
            ;;
        component-basic-report)
            render_component_basic_components
            ;;
        component-media-layout-report)
            render_component_media_layout
            ;;
        component-echarts-report)
            render_component_echarts
            ;;
        component-tree-alignment-report)
            render_component_tree_alignment
            ;;
        component-igv-report)
            render_component_igv
            ;;
        component-ngl-native-report)
            render_component_ngl_native_html
            ;;
        *)
            echo "ERROR: unknown real-run fixture: $fixture" >&2
            echo "Known fixtures: ${flow_fixtures[*]} ${component_fixtures[*]}" >&2
            exit 2
            ;;
    esac
done

check_output_layout
echo "[REAL] rendered reports index: $index"
echo "[REAL] flow reports index: $flow_index"
echo "[REAL] component regression index: $component_index"
echo "[REAL] ok"
