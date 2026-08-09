#!/usr/bin/env python3
"""Prepare the ignored Chengdu Yuanda report-12 real-run fixture.

The scientific source tree is intentionally external to this repository.  This
helper converts its immutable result tables, overlay PDB files and archived
static structure figures into the relative-path fixture contract consumed by
tests/test-real-run.sh.  It never runs biological analysis and uses only the
Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, NoReturn


HELPER_VERSION = "1"
PREFIX = "pufa_structure_comparison_all_domains"

REQUIRED_TABLES = (
    f"{PREFIX}.domain_differentiation_data_rank.tsv",
    f"{PREFIX}.domain_differentiation_mechanism_candidates.tsv",
    f"{PREFIX}.domain_differentiation_summary.tsv",
    f"{PREFIX}.figure_files.pre_pymol.tsv",
    f"{PREFIX}.figure_files.tsv",
    f"{PREFIX}.foldseek_structural_similarity.raw.tsv",
    f"{PREFIX}.foldseek_structural_similarity.tsv",
    f"{PREFIX}.local_motif_structural_similarity.tsv",
    f"{PREFIX}.motif_sites_on_target.tsv",
    f"{PREFIX}.overlay_pdb_manifest.tsv",
    f"{PREFIX}.overlay_priority_summary.tsv",
    f"{PREFIX}.selected_structures.tsv",
    f"{PREFIX}.selection_summary.tsv",
    f"{PREFIX}.structure_quality.tsv",
    f"{PREFIX}.target_local_motif_preference.tsv",
)

# The source contains 15 TSV names; report_files.tsv reaches the historic
# 16-table minimum through the motif site table referenced by every structure
# viewer.  Keep the ordered set explicit so source drift is a hard failure.

REQUIRED_REPORT_FILES = ("flow_summary.tsv", "versions.tsv", "methods.txt")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"missing required source file: {path}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    require_file(path)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def safe_number(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def sanitize_path_cell(value: str) -> str:
    """Remove maintainer absolute prefixes without changing scientific values."""
    normalized = value.replace("\\", "/")
    marker = "/03_results/"
    if marker in normalized:
        return "03_results/" + normalized.split(marker, 1)[1]
    if normalized.startswith("analysis/") and marker.lstrip("/") in normalized:
        return "03_results/" + normalized.split(marker.lstrip("/"), 1)[1]
    if normalized.startswith("/"):
        return "external-source/" + Path(normalized).name
    return value


def copy_sanitized_tsv(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        rows = [[sanitize_path_cell(cell) for cell in row] for row in reader]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerows(rows)


def slug(value: str) -> str:
    text = "".join(char.lower() if char.isalnum() else "-" for char in value)
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "item"


def grouped_count(rows: Iterable[dict[str, str]], key: str) -> list[tuple[str, float]]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        label = row.get(key, "").strip() or "unknown"
        counts[label] += 1
    return [(label, float(counts[label])) for label in sorted(counts)]


def grouped_mean(rows: Iterable[dict[str, str]], key: str, value_key: str) -> list[tuple[str, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        number = safe_number(row.get(value_key, ""))
        if number is not None:
            values[row.get(key, "").strip() or "unknown"].append(number)
    return [(label, sum(items) / len(items)) for label, items in sorted(values.items()) if items]


def write_value_svg(path: Path, title: str, values: list[tuple[str, float]], color: str) -> None:
    if not values:
        fail(f"cannot derive chart without numeric values: {title}")
    values = values[:18]
    width = 1200
    row_height = 44
    top = 92
    height = top + len(values) * row_height + 48
    label_width = 390
    plot_width = width - label_width - 90
    lower = min(0.0, min(value for _, value in values))
    upper = max(0.0, max(value for _, value in values))
    span = upper - lower or 1.0
    zero_x = label_width + ((0.0 - lower) / span) * plot_width
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7fbfa" rx="24"/>',
        f'<text x="42" y="52" font-family="Arial,sans-serif" font-size="28" font-weight="700" fill="#17343c">{html.escape(title)}</text>',
        f'<line x1="{zero_x:.2f}" y1="72" x2="{zero_x:.2f}" y2="{height - 28}" stroke="#8aa5aa" stroke-width="2"/>',
    ]
    for index, (label, value) in enumerate(values):
        y = top + index * row_height
        value_x = label_width + ((value - lower) / span) * plot_width
        bar_x = min(zero_x, value_x)
        bar_width = max(2.0, abs(value_x - zero_x))
        short_label = label if len(label) <= 46 else label[:43] + "..."
        lines.extend(
            [
                f'<text x="42" y="{y + 19}" font-family="Arial,sans-serif" font-size="16" fill="#29464d">{html.escape(short_label)}</text>',
                f'<rect x="{bar_x:.2f}" y="{y}" width="{bar_width:.2f}" height="25" rx="6" fill="{color}" opacity="0.84"/>',
                f'<text x="{min(width - 70, max(label_width + 6, value_x + 8)):.2f}" y="{y + 19}" font-family="Arial,sans-serif" font-size="14" fill="#17343c">{value:.4g}</text>',
            ]
        )
    lines.append("</svg>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


SITE_COLORS = {
    "target_matches_DHA": "#8b5cf6",
    "target_matches_EPA": "#0b84a5",
    "target_other": "#d97706",
}


def write_motif_track_svg(path: Path, structure_id: str, rows: list[dict[str, str]]) -> None:
    sites: list[tuple[int, str, str]] = []
    for row in rows:
        if row.get("structure_id") != structure_id:
            continue
        number = safe_number(row.get("structure_residue", ""))
        if number is None:
            continue
        sites.append((int(number), row.get("target_state", "target_other"), row.get("target_residue_label", "")))
    sites.sort()
    maximum = max((site[0] for site in sites), default=1)
    width, height = 1200, 330
    left, right = 80, 1120
    axis_y = 178
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7fbfa" rx="24"/>',
        f'<text x="44" y="48" font-family="Arial,sans-serif" font-size="25" font-weight="700" fill="#17343c">Motif-site residue track</text>',
        f'<text x="44" y="78" font-family="Arial,sans-serif" font-size="15" fill="#49666c">{html.escape(structure_id)}</text>',
        f'<line x1="{left}" y1="{axis_y}" x2="{right}" y2="{axis_y}" stroke="#6b8790" stroke-width="5" stroke-linecap="round"/>',
        f'<text x="{left}" y="{axis_y + 38}" font-family="Arial,sans-serif" font-size="14">1</text>',
        f'<text x="{right - 34}" y="{axis_y + 38}" font-family="Arial,sans-serif" font-size="14">{maximum}</text>',
    ]
    if not sites:
        lines.append('<text x="80" y="128" font-family="Arial,sans-serif" font-size="17" fill="#8a5a18">No mapped motif sites in the archived result table for this target.</text>')
    for residue, group, label in sites:
        x = left + (residue - 1) / max(1, maximum - 1) * (right - left)
        color = SITE_COLORS.get(group, SITE_COLORS["target_other"])
        lines.append(f'<circle cx="{x:.2f}" cy="{axis_y}" r="9" fill="{color}" stroke="#ffffff" stroke-width="2"><title>{html.escape(label or str(residue))} | {html.escape(group)}</title></circle>')
    legend_x = 120
    for index, (group, color) in enumerate(SITE_COLORS.items()):
        x = legend_x + index * 310
        lines.append(f'<circle cx="{x}" cy="276" r="8" fill="{color}"/><text x="{x + 16}" y="282" font-family="Arial,sans-serif" font-size="15" fill="#29464d">{html.escape(group)}</text>')
    lines.append("</svg>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def append_bilingual(lines: list[str], field: str, text: str) -> None:
    lines.append(f"{field}.en = {toml_string(text)}")
    lines.append(f"{field}.zh = {toml_string(text)}")


def write_report_spec(
    destination: Path,
    table_names: list[str],
    chart_names: list[tuple[str, str]],
    groups: list[tuple[str, list[dict[str, str]]]],
) -> None:
    lines = [
        'schema_version = "0.1"',
        'template = "taffish-flow-report"',
        'template_version = "real-run-current"',
        'language_default = "zh"',
        "",
        "[project]",
        'flow_name = "pufa-structure-comparison-flow"',
        'flow_version = "0.3.3-r1"',
        'analysis_mode = "chengdu-yuanda-report12-real-fixture"',
        'title.en = "Chengdu Yuanda PUFA Structure Comparison Report 12"',
        'title.zh = "成都圆大 PUFA 结构比较第 12 步报告"',
        'subtitle.en = "Deterministically prepared from archived scientific tables, overlay PDB models and static structure figures."',
        'subtitle.zh = "由归档科学结果表、结构叠合 PDB 模型和静态结构图确定性准备。"',
        "",
        "[provenance]",
        'versions = "04_reports/versions.tsv"',
        'methods = "04_reports/methods.txt"',
        "",
        "[[sections]]",
        'id = "overview"',
        'kind = "overview"',
        'title.en = "Result overview"',
        'title.zh = "结果总览"',
        "",
        "[[sections.components]]",
        'type = "dashboard_cards"',
        'id = "flow-summary"',
        'source = "04_reports/flow_summary.tsv"',
        "",
        "[[sections]]",
        'id = "scientific-tables"',
        'kind = "results"',
        'title.en = "Scientific result tables"',
        'title.zh = "科学结果表"',
    ]
    for name in table_names:
        lines.extend(
            [
                "",
                "[[sections.components]]",
                'type = "table_preview"',
                f'id = {toml_string("table-" + slug(Path(name).stem))}',
                f'source = {toml_string("03_results/tables/" + name)}',
                "preview_rows = 8",
                "embed_full = true",
                "max_embed_rows = 1200",
                "max_embed_bytes = 6000000",
            ]
        )
        append_bilingual(lines, "title", Path(name).stem.replace("_", " "))
    lines.extend(
        [
            "",
            "[[sections]]",
            'id = "derived-visual-summaries"',
            'kind = "results"',
            'title.en = "Deterministic visual summaries"',
            'title.zh = "确定性可视化摘要"',
            'note.en = "These SVG panels are test-fixture visualizations derived from the archived scientific TSV values; they do not recompute scientific results."',
            'note.zh = "这些 SVG 面板由归档科学 TSV 数值派生，仅用于测试 fixture 可视化，不重新计算科学结果。"',
        ]
    )
    for filename, title in chart_names:
        lines.extend(
            [
                "",
                "[[sections.components]]",
                'type = "plot_card"',
                f'id = {toml_string("summary-" + slug(Path(filename).stem))}',
                f'image = {toml_string("03_results/figures/" + filename)}',
                'layout = "wide"',
            ]
        )
        append_bilingual(lines, "title", title)
    lines.extend(
        [
            "",
            "[[sections]]",
            'id = "structure-overlays"',
            'kind = "structure"',
            'title.en = "Target, EPA and DHA structure overlays"',
            'title.zh = "Target、EPA 与 DHA 结构叠合"',
            'note.en = "Each interactive viewer embeds three real aligned PDB models and motif markers from the archived site table."',
            'note.zh = "每个交互查看器内嵌三个真实对齐 PDB 模型，并从归档位点表加载 motif 标记。"',
        ]
    )
    for structure_id, models in groups:
        target = next(row for row in models if row["model_role"].lower() == "target")
        motif_name = f"{PREFIX}.{structure_id}.motif_site_track.svg"
        overlay_name = f"{PREFIX}.{structure_id}.target_epa_dha_overlay.png"
        lines.extend(
            [
                "",
                "[[sections.components]]",
                'type = "plot_card"',
                f'id = {toml_string("motif-track-" + slug(structure_id))}',
                f'image = {toml_string("03_results/structure_figures/" + motif_name)}',
                'layout = "wide"',
            ]
        )
        append_bilingual(lines, "title", f"Motif residue track | {target['label']}")
        lines.extend(
            [
                "",
                "[[sections.components]]",
                'type = "structure_viewer"',
                f'id = {toml_string("overlay-" + slug(structure_id))}',
                'runtime = "ngl"',
                'representation = "cartoon"',
                f'static_image = {toml_string("03_results/structure_figures/" + overlay_name)}',
                'atom_filter = "ca"',
                "height = 460",
                "max_atoms = 2600",
                "controls_open = false",
                f'site_table = {toml_string("03_results/tables/" + PREFIX + ".motif_sites_on_target.tsv")}',
                f'site_structure_id = {toml_string(structure_id)}',
                'site_model = "target"',
                'site_chain = "A"',
                'site_residue_column = "structure_residue"',
                'site_group_column = "target_state"',
                'site_label_column = "target_residue_label"',
                "site_max_sites = 80",
            ]
        )
        append_bilingual(lines, "title", f"{target['label']} target versus EPA/DHA reference overlay")
        append_bilingual(lines, "note", "Black is the target, cyan is the EPA reference, and purple is the DHA reference; controls only change the browser view.")
        for row in sorted(models, key=lambda item: {"target": 0, "EPA": 1, "DHA": 2}.get(item["model_role"], 9)):
            role = row["model_role"].lower()
            pdb_name = Path(row["pdb_path"]).name
            lines.extend(
                [
                    "",
                    "[[sections.components.models]]",
                    f'id = {toml_string(role)}',
                    f'pdb = {toml_string(f"03_results/overlay_pdb/{structure_id}/{pdb_name}")}',
                    f'color = {toml_string(row.get("color") or SITE_COLORS.get(role, "#64748b"))}',
                ]
            )
            append_bilingual(lines, "label", row["label"])
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_charts(source_results: Path, output_figures: Path) -> list[tuple[str, str]]:
    selected = read_tsv(source_results / f"{PREFIX}.selected_structures.tsv")
    quality = read_tsv(source_results / f"{PREFIX}.structure_quality.tsv")
    foldseek = read_tsv(source_results / f"{PREFIX}.foldseek_structural_similarity.tsv")
    motif = read_tsv(source_results / f"{PREFIX}.motif_sites_on_target.tsv")
    local = read_tsv(source_results / f"{PREFIX}.local_motif_structural_similarity.tsv")
    preference = read_tsv(source_results / f"{PREFIX}.target_local_motif_preference.tsv")
    charts = [
        ("fig1_structure_selection.svg", "Selected structures by biological role", grouped_count(selected, "role"), "#0b8f82"),
        ("fig2_structure_confidence.svg", "Mean structure confidence by biological role", grouped_mean(quality, "role", "mean_plddt"), "#315b9b"),
        ("fig3_foldseek_alntmscore.svg", "Mean Foldseek alignment TM-score by target", grouped_mean(foldseek, "query", "alntmscore"), "#0b84a5"),
        ("fig3_foldseek_identity.svg", "Mean Foldseek residue identity by target", grouped_mean(foldseek, "query", "fident"), "#8b5cf6"),
        ("fig3_foldseek_rmsd.svg", "Mean Foldseek RMSD by target", grouped_mean(foldseek, "query", "rmsd"), "#d97706"),
        ("fig4_motif_site_positions.svg", "Motif-site count by target structure", grouped_count(motif, "structure_id"), "#b83280"),
        ("fig5_motif_window_local_rmsd.svg", "Mean motif-window local RMSD by comparison group", grouped_mean(local, "comparison_group", "motif_window_rmsd"), "#2563eb"),
        ("fig6_motif_site_local_rmsd.svg", "Mean motif-site local RMSD by comparison group", grouped_mean(local, "comparison_group", "motif_site_rmsd"), "#0891b2"),
        ("fig7_target_local_preference.svg", "EPA minus DHA motif-site RMSD by target", grouped_mean(preference, "target_structure_id", "EPA_minus_DHA_site_rmsd"), "#7c3aed"),
    ]
    output: list[tuple[str, str]] = []
    for filename, title, values, color in charts:
        write_value_svg(output_figures / filename, title, values, color)
        output.append((filename, title))
    return output


def collect_file_records(root: Path) -> list[dict[str, object]]:
    records = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "fixture-preparation.json"):
        records.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def prepare(source_root: Path, outdir: Path, expected_overlay_groups: int) -> None:
    source_root = source_root.resolve()
    source_results = source_root / "03_results"
    source_reports = source_root / "04_reports"
    if outdir.exists():
        fail(f"output already exists; remove it or choose a fresh directory: {outdir}")

    for name in REQUIRED_TABLES:
        require_file(source_results / name)
    for name in REQUIRED_REPORT_FILES:
        require_file(source_reports / name)
    overlay_root = source_results / "overlay_pdb"
    display_root = source_results / "structure_figures_display"
    if not overlay_root.is_dir() or not display_root.is_dir():
        fail("source must contain 03_results/overlay_pdb and 03_results/structure_figures_display")

    manifest_rows = read_tsv(source_results / f"{PREFIX}.overlay_pdb_manifest.tsv")
    grouped_models: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in manifest_rows:
        grouped_models[row.get("target_structure_id", "")].append(row)
    groups = sorted((key, rows) for key, rows in grouped_models.items() if key)
    if len(groups) != expected_overlay_groups:
        fail(f"expected {expected_overlay_groups} overlay groups, found {len(groups)}")
    for structure_id, rows in groups:
        roles = sorted(row.get("model_role", "") for row in rows)
        if roles != ["DHA", "EPA", "target"]:
            fail(f"overlay {structure_id} must contain exactly target/EPA/DHA models; found {roles}")
        source_group = overlay_root / structure_id
        if not source_group.is_dir():
            fail(f"missing overlay PDB directory: {source_group}")
        for row in rows:
            require_file(source_group / Path(row["pdb_path"]).name)

    output_tables = outdir / "03_results" / "tables"
    output_figures = outdir / "03_results" / "figures"
    output_structures = outdir / "03_results" / "structure_figures"
    output_overlay = outdir / "03_results" / "overlay_pdb"
    output_reports = outdir / "04_reports"
    for directory in (output_tables, output_figures, output_structures, output_reports):
        directory.mkdir(parents=True, exist_ok=True)

    for name in REQUIRED_TABLES:
        copy_sanitized_tsv(source_results / name, output_tables / name)
    for name in REQUIRED_REPORT_FILES:
        source = source_reports / name
        destination = output_reports / name
        if source.suffix == ".tsv":
            copy_sanitized_tsv(source, destination)
        else:
            shutil.copyfile(source, destination)
    shutil.copytree(overlay_root, output_overlay)

    motif_rows = read_tsv(source_results / f"{PREFIX}.motif_sites_on_target.tsv")
    for structure_id, _ in groups:
        display_source = require_file(display_root / f"{PREFIX}.{structure_id}.target_epa_dha_overlay.display.png")
        shutil.copyfile(display_source, output_structures / f"{PREFIX}.{structure_id}.target_epa_dha_overlay.png")
        write_motif_track_svg(output_structures / f"{PREFIX}.{structure_id}.motif_site_track.svg", structure_id, motif_rows)

    chart_names = build_charts(source_results, output_figures)
    write_report_spec(outdir / "report.toml", list(REQUIRED_TABLES), chart_names, groups)

    input_paths = [source_results / name for name in REQUIRED_TABLES]
    input_paths.extend(source_reports / name for name in REQUIRED_REPORT_FILES)
    input_paths.extend(sorted(path for path in overlay_root.rglob("*") if path.is_file()))
    input_paths.extend(sorted(display_root.glob("*.display.png")))
    receipt = {
        "schema_version": "1",
        "helper": "prepare-chengdu-yuanda-report12-fixture",
        "helper_version": HELPER_VERSION,
        "expected_overlay_groups": expected_overlay_groups,
        "input_files": [
            {"path": path.relative_to(source_root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(set(input_paths))
        ],
        "output_files": collect_file_records(outdir),
    }
    (outdir / "fixture-preparation.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"prepared Chengdu Yuanda report-12 fixture: {outdir}")
    print(f"overlay_groups={len(groups)} input_files={len(receipt['input_files'])} output_files={len(receipt['output_files'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path, help="Archived raw pufa_structure_comparison_all_domains_local_complete root.")
    parser.add_argument("--outdir", required=True, type=Path, help="Fresh ignored fixture output directory.")
    parser.add_argument("--expected-overlay-groups", type=int, default=11, help="Hard expected target overlay count (default: 11).")
    args = parser.parse_args()
    if args.expected_overlay_groups < 1:
        fail("--expected-overlay-groups must be positive")
    prepare(args.source_root, args.outdir, args.expected_overlay_groups)


if __name__ == "__main__":
    main()
