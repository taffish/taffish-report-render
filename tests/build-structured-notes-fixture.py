#!/usr/bin/env python3
"""Build the deterministic structured-note and responsive-overflow fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def append_note_item(
    lines: list[str],
    table: str,
    *,
    kind: str,
    label_en: str,
    label_zh: str,
    body_en: str | None = None,
    body_zh: str | None = None,
    items_en: list[str] | None = None,
    items_zh: list[str] | None = None,
) -> None:
    lines.extend(["", f"[[{table}]]", f"kind = {toml_string(kind)}"])
    lines.extend(
        [
            f"label.en = {toml_string(label_en)}",
            f"label.zh = {toml_string(label_zh)}",
        ]
    )
    if body_en is not None and body_zh is not None:
        lines.extend(
            [
                f"body.en = {toml_string(body_en)}",
                f"body.zh = {toml_string(body_zh)}",
            ]
        )
    if items_en is not None and items_zh is not None:
        lines.extend(
            [
                f"items.en = [{', '.join(toml_string(item) for item in items_en)}]",
                f"items.zh = [{', '.join(toml_string(item) for item in items_zh)}]",
            ]
        )


def build(root: Path, spec: Path) -> None:
    figure_dir = root / "03_results" / "figures"
    table_dir = root / "03_results" / "tables"
    report_dir = root / "04_reports"
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    spec.parent.mkdir(parents=True, exist_ok=True)

    zh_long = (
        "这一段结构化说明用于验证真实科研报告中的长中文叙述不会把章节、卡片、导航或操作区撑出页面。"
        "它明确区分研究问题、输入材料、执行方法、阅读方式、当前观察与结论边界，并保留可审计的技术标识。"
        "读者应先核对输入与质量门，再结合图表和原始表格理解结果；任何视觉模式都不自动等于生物学因果关系。"
    ) * 4
    en_long = (
        "This deliberately long structured explanation verifies that a realistic scientific narrative remains inside the report shell, cards, navigation, and action areas at every supported viewport. "
        "It separates the research question, input material, completed method, reading guidance, current observation, and claim boundary while retaining auditable technical identifiers. "
        "Reviewers should inspect inputs and quality gates first, then interpret figures together with source tables; a visual pattern alone does not establish biological causality or validate an untested mechanism. "
    ) * 2
    if not 300 <= len(zh_long) <= 600:
        raise ValueError(f"Chinese stress paragraph must have 300-600 characters, got {len(zh_long)}")
    if not 1000 <= len(en_long) <= 1500:
        raise ValueError(f"English stress paragraph must have 1000-1500 characters, got {len(en_long)}")

    sha64 = "0123456789abcdef" * 4
    no_space = "NO_SPACE_TOKEN_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 7
    run_id = "SRR12345678_RUN_2026_08_08_ATTEMPT_000042"
    accession = "GCA_999999999.1_TAFFISH_STRUCTURED_NOTE_FIXTURE"
    url_like = "https://example.invalid/results/two-speed-genome/" + no_space
    malicious = (
        '<script data-taffish-attack="1">alert("x")</script>'
        '<img src=x onerror=alert(2)><style>body{display:none}</style> '
        "**Markdown stays text**"
    )

    (report_dir / "flow_summary.tsv").write_text(
        "metric\tvalue\n"
        "sections\t3\n"
        "structured_note_items\t12\n"
        "responsive_breakpoints\t5\n",
        encoding="utf-8",
    )
    (report_dir / "workflow.tsv").write_text(
        "step_en\tstep_zh\tstatus\tnote_en\tnote_zh\n"
        "Validate inputs\t校验输入\tOK\tCheck hashes and identifiers.\t检查哈希与标识符。\n"
        "Render report\t渲染报告\tOK\tCompile the fixed component tree.\t编译固定组件树。\n"
        "Audit boundaries\t审计边界\tOK\tKeep claims within the supplied evidence.\t将结论限制在已有证据内。\n",
        encoding="utf-8",
    )
    (table_dir / "wide.tsv").write_text(
        "sample\tsha256\trun_id\taccession\turl_like\tno_space\tnote_en\tnote_zh\n"
        f"sample_001\t{sha64}\t{run_id}\t{accession}\t{url_like}\t{no_space}\t"
        "Long values stay available in the full table.\t长值在完整表格中保持可用。\n",
        encoding="utf-8",
    )
    (report_dir / "technical-identifiers.txt").write_text(
        f"sha256={sha64}\n"
        f"run_id={run_id}\n"
        f"accession={accession}\n"
        f"url_like={url_like}\n"
        f"no_space={no_space}\n",
        encoding="utf-8",
    )
    (figure_dir / "stress.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 480">'
        '<rect width="1200" height="480" fill="#f4f8f7"/>'
        '<path d="M80 390 C260 80 410 330 610 120 S920 300 1120 70" '
        'fill="none" stroke="#087f74" stroke-width="18"/>'
        '<text x="70" y="65" font-family="Arial,sans-serif" font-size="34" fill="#10252c">'
        "Structured explanation responsive stress figure</text></svg>",
        encoding="utf-8",
    )

    lines = [
        'schema_version = "0.1"',
        'template = "taffish-flow-report"',
        'languages = ["zh", "en"]',
        'language_default = "zh"',
        "",
        "[project]",
        'flow_name = "taffish-report-render"',
        'flow_version = "0.3.1-r1"',
        'analysis_mode = "component-structured-notes-report"',
        'title.en = "0. Structured explanation and responsive overflow stress report"',
        'title.zh = "0. 结构化说明与响应式溢出压力报告"',
        f"subtitle.en = {toml_string(en_long)}",
        f"subtitle.zh = {toml_string(zh_long)}",
        "",
        "[[sections]]",
        'id = "overview"',
        'kind = "overview"',
        'title.en = "0. Reading entry"',
        'title.zh = "0. 阅读入口"',
        'note.en = "A short backward-compatible lead precedes the structured explanation."',
        'note.zh = "一段向后兼容的简短导语位于结构化说明之前。"',
    ]
    append_note_item(
        lines,
        "sections.note_items",
        kind="summary",
        label_en="Summary",
        label_zh="摘要",
        body_en=en_long,
        body_zh=zh_long,
    )
    lines.extend(
        [
            "",
            "[[sections.components]]",
            'type = "dashboard_cards"',
            'id = "overview-cards"',
            'source = "04_reports/flow_summary.tsv"',
            'title.en = "0.1 Validation scope"',
            'title.zh = "0.1 验证范围"',
        ]
    )
    append_note_item(
        lines,
        "sections.components.note_items",
        kind="reading",
        label_en="How to read",
        label_zh="如何阅读",
        items_en=[
            "Confirm the declared input and SHA-256 identity.",
            "Read the workflow in the displayed order.",
            "Use the wide table's internal horizontal scroller.",
            "Compare the wide and media figure layouts.",
            "Switch between English and Chinese without reloading.",
            "Treat the boundary statement as part of the result.",
        ],
        items_zh=[
            "确认声明的输入与 SHA-256 身份。",
            "按照展示顺序阅读工作流。",
            "使用宽表自身的横向滚动区域。",
            "比较 wide 与 media 图文布局。",
            "无需刷新即可切换中英文。",
            "将结论边界视为结果的一部分。",
        ],
    )

    lines.extend(
        [
            "",
            "[[sections]]",
            'id = "results"',
            'kind = "results"',
            'title.en = "1. Main evidence"',
            'title.zh = "1. 主要证据"',
        ]
    )
    note_specs = [
        (
            "question",
            "Question",
            "问题",
            "Can long bilingual scientific explanations remain readable without changing scientific results?",
            "长篇双语科研说明能否在不改变科学结果的前提下保持可读？",
        ),
        (
            "input",
            "Input",
            "输入",
            f"The fixture includes {sha64}, {run_id}, {accession}, and URL-like or unbroken identifiers.",
            f"夹具包含 {sha64}、{run_id}、{accession} 以及 URL 样式和连续标识符。",
        ),
        (
            "method",
            "Method",
            "方法",
            "Compile one fixed-component TOML specification and audit its standalone HTML at desktop, boundary, mobile, zoom, and print states.",
            "编译一份固定组件 TOML 说明，并在桌面、断点、移动、缩放与打印状态审计 standalone HTML。",
        ),
        (
            "reading",
            "Reading",
            "判读",
            "Use component-local scrolling only for wide tables and code; the page shell itself must not scroll horizontally.",
            "仅允许宽表与代码组件内部滚动，页面外壳本身不得横向滚动。",
        ),
        ("observation", "Observation", "观察", malicious, malicious),
        (
            "boundary",
            "Boundary",
            "边界",
            "This fixture validates structure, escaping, preservation, and layout behavior; it does not validate a biological hypothesis.",
            "该夹具验证结构、转义、保留与布局行为，不验证任何生物学假说。",
        ),
    ]
    for kind, label_en, label_zh, body_en, body_zh in note_specs:
        append_note_item(
            lines,
            "sections.note_items",
            kind=kind,
            label_en=label_en,
            label_zh=label_zh,
            body_en=body_en,
            body_zh=body_zh,
        )

    component_specs = [
        ("workflow_diagram", "workflow", "source", "04_reports/workflow.tsv", "1.1 Reproducible workflow", "1.1 可复现工作流", "method", "方法"),
        ("plot_card", "wide-figure", "image", "03_results/figures/stress.svg", "1.2 Wide figure", "1.2 全宽图", "reading", "判读"),
        ("plot_card", "media-figure", "image", "03_results/figures/stress.svg", "1.3 Media figure", "1.3 图文卡片", "observation", "观察"),
        ("table_preview", "wide-table", "source", "03_results/tables/wide.tsv", "1.4 Wide technical table", "1.4 宽技术表格", "boundary", "边界"),
    ]
    for component_type, component_id, path_field, path, title_en, title_zh, kind, label_zh in component_specs:
        lines.extend(
            [
                "",
                "[[sections.components]]",
                f"type = {toml_string(component_type)}",
                f"id = {toml_string(component_id)}",
                f"{path_field} = {toml_string(path)}",
            ]
        )
        if component_id == "wide-figure":
            lines.extend(['layout = "wide"', 'note_position = "top"'])
        elif component_id == "media-figure":
            lines.extend(
                [
                    'layout = "media"',
                    'image_position = "right"',
                    "media_image_ratio = 0.70",
                    'media_vertical_align = "center"',
                    'media_gap = "relaxed"',
                ]
            )
        elif component_id == "wide-table":
            lines.extend(
                [
                    "preview_rows = 1",
                    "embed_full = true",
                    "max_embed_rows = 10",
                    "max_embed_bytes = 200000",
                ]
            )
        lines.extend(
            [
                f"title.en = {toml_string(title_en)}",
                f"title.zh = {toml_string(title_zh)}",
            ]
        )
        append_note_item(
            lines,
            "sections.components.note_items",
            kind=kind,
            label_en=kind.title(),
            label_zh=label_zh,
            body_en=en_long,
            body_zh=zh_long,
        )

    lines.extend(
        [
            "",
            "[[sections]]",
            'id = "technical-appendix"',
            'kind = "appendix"',
            'title.en = "A. Technical appendix"',
            'title.zh = "A. 技术附录"',
        ]
    )
    append_note_item(
        lines,
        "sections.note_items",
        kind="provenance",
        label_en="Provenance",
        label_zh="溯源",
        body_en=f"Identifiers are preserved exactly: {sha64} {run_id} {accession}",
        body_zh=f"以下标识符按原样保留：{sha64} {run_id} {accession}",
    )
    lines.extend(
        [
            "",
            "[[sections.components]]",
            'type = "code_file"',
            'id = "technical-identifiers"',
            'source = "04_reports/technical-identifiers.txt"',
            'language = "text"',
            "copy = true",
            'title.en = "A.1 Exact identifiers"',
            'title.zh = "A.1 精确标识符"',
        ]
    )
    append_note_item(
        lines,
        "sections.components.note_items",
        kind="provenance",
        label_en="Exact text",
        label_zh="精确文本",
        body_en="Copyable values remain plain text and are not interpreted as markup or URLs.",
        body_zh="可复制值保持纯文本，不会被解释成标记或 URL。",
    )

    spec.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    build(args.root, args.spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
