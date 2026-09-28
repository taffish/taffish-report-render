#!/usr/bin/env python3
"""Command line interface for taffish-report-render."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import math
import mimetypes
import os
import re
import shlex
import sys
import tomllib
from dataclasses import dataclass, field
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import quote

from . import __version__
from .anchors import child_anchor
from .toc import build_toc_index, inspect_toc_html, render_toc, validate_toc
from .components import (
    COMPONENT_DOC_EXTENSIONS,
    COMPONENT_REGISTRY_EXTENSIONS,
    extended_component_path_values,
    normalize_structure_models,
    parse_pdb_atoms,
    validate_extended_component,
)


TEMPLATE_VERSION = "taffish-flow-report-render-0.4"
RENDER_COMPONENTS = [
    "dashboard_cards",
    "status_grid",
    "quality_gate_table",
    "table_preview",
    "code_file",
    "workflow_diagram",
    "plot_card",
    "interactive_plot",
    "structure_viewer",
    "tree_viewer",
    "sequence_alignment",
    "genome_browser",
    "native_subreport",
]
COLLECTION_COMPONENTS = [
    "plot_collection",
    "table_collection",
    "code_file_collection",
    "native_subreport_collection",
]
COMPONENTS = RENDER_COMPONENTS + COLLECTION_COMPONENTS
DEFAULT_LANGUAGES = ["en", "zh"]
DEFAULT_LANGUAGE = "zh"
HTML_WARN_BYTES = 50_000_000
HTML_ERROR_BYTES = 100_000_000
ASSET_WARN_BYTES = 20_000_000
NGL_RUNTIME_VERSION = "external"
NGL_RUNTIME_ENV = "TAFFISH_REPORT_RENDER_NGL_JS"
PLOTLY_RUNTIME_ID = "plotly-1.2.0"
ECHARTS_RUNTIME_ID = "echarts-6.1.0"
IGV_RUNTIME_ID = "igv"
IGV_RUNTIME_ENV = "TAFFISH_REPORT_RENDER_IGV_JS"
LANGUAGE_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,15}$")
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
    "it": "Italiano",
}
ACTIVE_LANGUAGES = DEFAULT_LANGUAGES[:]
ACTIVE_LANGUAGE_DEFAULT = DEFAULT_LANGUAGE

NOTE_ITEM_KINDS = (
    "summary",
    "question",
    "purpose",
    "input",
    "method",
    "elements",
    "reading",
    "observation",
    "result",
    "meaning",
    "boundary",
    "limitation",
    "next",
    "provenance",
)
NOTE_ITEM_FIELDS = {"kind", "label", "body", "items"}
MEDIA_NOTE_LAYOUTS = ("auto", "stack", "compact")
NOTE_LENGTH_WARN_LIMITS = {"zh": 240, "en": 700}
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

DEFAULT_SITE_GROUP_STYLES: dict[str, dict[str, Any]] = {
    "target_matches_DHA": {
        "color": "#8b5cf6",
        "label": {"en": "Target matches DHA motif", "zh": "target 匹配 DHA motif"},
    },
    "target_matches_EPA": {
        "color": "#0b84a5",
        "label": {"en": "Target matches EPA motif", "zh": "target 匹配 EPA motif"},
    },
    "target_other": {
        "color": "#d18b00",
        "label": {"en": "Other target motif state", "zh": "其他 target motif 状态"},
    },
    "target_gap": {
        "color": "#7b8794",
        "label": {"en": "Target motif gap", "zh": "target motif 缺口"},
    },
    "sites": {
        "color": "#d18b00",
        "label": {"en": "Highlighted sites", "zh": "高亮位点"},
    },
}


COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "dashboard_cards": {
        "kind": "render",
        "summary": "Render a compact metric-card dashboard from a TSV table.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "title", "note"],
    },
    "status_grid": {
        "kind": "render",
        "summary": "Render module or step status cards from a TSV table.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "title", "note"],
    },
    "quality_gate_table": {
        "kind": "render",
        "summary": "Render quality gates and threshold decisions from a TSV table.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "title", "note"],
    },
    "table_preview": {
        "kind": "render",
        "summary": "Render a TSV/CSV table as a compact preview plus an in-place full viewer when size limits allow.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "title",
            "note",
            "preview_rows",
            "embed_full",
            "fold_i18n_columns",
            "default_state",
            "max_embed_rows",
            "max_embed_bytes",
        ],
    },
    "code_file": {
        "kind": "render",
        "summary": "Embed a small text/code artifact such as Newick, a short config, a command block, or small JSON.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "title", "note", "language", "syntax", "copy", "max_embed_bytes", "max_lines"],
    },
    "workflow_diagram": {
        "kind": "render",
        "summary": "Render a linear workflow diagram from a TSV step table.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "title", "note"],
    },
    "plot_card": {
        "kind": "render",
        "summary": "Embed a primary image as a data URI using grid, wide, or responsive media layout with an optional large-image viewer.",
        "required": ["image"],
        "path_fields": ["image"],
        "fields": [
            "id", "type", "image", "title", "note", "caption", "zoom",
            "default_fit", "layout", "note_position", "image_position",
            "media_image_ratio", "media_vertical_align", "media_gap",
            "media_note_layout",
        ],
    },
    "native_subreport": {
        "kind": "render",
        "summary": "Bundle a native local HTML/QC subreport such as MultiQC, FastQC, fastp, or Qualimap.",
        "required": ["path"],
        "path_fields": ["path", "pages"],
        "fields": [
            "id",
            "type",
            "path",
            "kind",
            "title",
            "note",
            "embed_policy",
            "embed_linked_pages",
            "linked_page_limit",
            "pages",
        ],
    },
    "plot_collection": {
        "kind": "collection",
        "expands_to": "plot_card",
        "summary": "Expand rows from a TSV index into multiple plot_card components.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "id_prefix", "filter_column", "filter_value", "title", "note", "zoom", "default_fit"],
    },
    "table_collection": {
        "kind": "collection",
        "expands_to": "table_preview",
        "summary": "Expand rows from a TSV index into multiple table_preview components.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "id_prefix",
            "filter_column",
            "filter_value",
            "title",
            "note",
            "preview_rows",
            "embed_full",
            "fold_i18n_columns",
            "default_state",
            "max_embed_rows",
            "max_embed_bytes",
        ],
    },
    "code_file_collection": {
        "kind": "collection",
        "expands_to": "code_file",
        "summary": "Expand rows from a TSV index into multiple code_file components.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": ["id", "type", "source", "id_prefix", "filter_column", "filter_value", "title", "note", "language", "copy"],
    },
    "native_subreport_collection": {
        "kind": "collection",
        "expands_to": "native_subreport",
        "summary": "Expand rows from a TSV index into multiple native_subreport components.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "id_prefix",
            "filter_column",
            "filter_value",
            "title",
            "note",
            "kind",
            "embed_policy",
            "embed_linked_pages",
            "linked_page_limit",
        ],
    },
}
COMPONENT_REGISTRY.update(COMPONENT_REGISTRY_EXTENSIONS)
for _component_info in COMPONENT_REGISTRY.values():
    _fields = _component_info.setdefault("fields", [])
    _fields.append("toc")
    if "note_items" not in _fields:
        try:
            _fields.insert(_fields.index("note") + 1, "note_items")
        except ValueError:
            _fields.append("note_items")


COMPONENT_DOCS: dict[str, str] = {
    "dashboard_cards": "dashboard_cards reads a TSV summary table and renders compact report-level cards. Common columns are metric, value, note, note_en, and note_zh.",
    "status_grid": "status_grid reads a TSV module/status table and renders status cards. Common columns are module, step, name, status, note_en, and note_zh.",
    "quality_gate_table": "quality_gate_table renders threshold checks from a TSV table. Language-paired columns such as criterion_en/criterion_zh are folded into one multilingual column, and the component note is displayed above the table.",
    "table_preview": "table_preview renders a TSV/CSV file as a compact preview and, within size limits, an in-place full table viewer with search, sorting, two-axis scrolling, cell expansion, copy support, and a visible component note above the table.",
    "code_file": "code_file embeds a small text artifact such as a Newick tree, short config, command snippet, or small JSON block, with an optional copy button.",
    "workflow_diagram": "workflow_diagram renders a linear workflow route from a TSV table. Paired step_en/step_zh, note_en/note_zh, and status_en/status_zh columns switch with the active report language; legacy step, flow, status, and outdir columns remain supported.",
    "plot_card": "plot_card embeds a PNG/SVG/JPEG/WebP image as a data URI and supports a fit-to-window large-image viewer. layout supports grid, wide, and media; media adds a component-width-responsive image-and-explanation layout. media_note_layout accepts auto, stack, or compact; auto selects compact for four or more structured note items.",
    "native_subreport": "native_subreport bundles a local program-generated HTML/QC report. embed_policy supports auto, always, and never; local multi-page bundles can use embed_linked_pages or pages.",
    "plot_collection": "plot_collection expands a TSV index into plot_card components. Use columns such as id, image/path/source, title_en, title_zh, note_en, and note_zh.",
    "table_collection": "table_collection expands a TSV index into table_preview components. Use columns such as id, source/path, title_en, title_zh, note_en, and note_zh.",
    "code_file_collection": "code_file_collection expands a TSV index into code_file components. Use columns such as id, source/path, language, title_en, and title_zh.",
    "native_subreport_collection": "native_subreport_collection expands a TSV index into native_subreport components. Use columns such as id, path/source, kind, title_en, title_zh, and embed_policy.",
}
COMPONENT_DOCS.update(COMPONENT_DOC_EXTENSIONS)


class RenderError(RuntimeError):
    """User-facing renderer failure."""


@dataclass
class AssetRecord:
    kind: str
    component_id: str
    path: str
    bytes: int
    sha256: str
    status: str = "ok"
    message: str = ""


@dataclass
class SubreportRecord:
    id: str
    kind: str
    path: str
    status: str
    source_bytes: int
    embedded_bytes: int
    sha256: str
    message: str = ""


@dataclass
class RenderContext:
    root: Path
    report_dir: Path | None = None
    assets: list[AssetRecord] = field(default_factory=list)
    subreports: list[SubreportRecord] = field(default_factory=list)
    embedded_payloads: list[dict[str, str]] = field(default_factory=list)
    runtime_packs: dict[str, str] = field(default_factory=dict)
    runtime_pack_versions: dict[str, str] = field(default_factory=dict)


@dataclass
class TableColumn:
    label: str
    source: str | None = None
    variants: dict[str, str] = field(default_factory=dict)
    fallback_sources: list[str] = field(default_factory=list)


@dataclass
class LintIssue:
    severity: str
    location: str
    message: str


AUTOMATIC_SECTIONS = {
    "report-guide",
    "deliverables",
    "provenance",
}

SECTION_NOTES = {
    "overview": {
        "en": "This section summarizes the report-level status, input scale, and the first files a reviewer should read before moving into detailed results.",
        "zh": "本章节汇总报告级状态、输入规模，以及审阅详细结果前最应该优先阅读的文件。",
    },
    "workflow": {
        "en": "The workflow route explains how upstream outputs are transformed into reportable evidence and where each module contributes to the final interpretation.",
        "zh": "流程路径说明上游结果如何被转化为可报告证据，以及每个模块在最终解读中的作用。",
    },
    "quality_control": {
        "en": "Quality-control modules evaluate whether the input data and processed outputs are technically reliable enough for downstream interpretation.",
        "zh": "质控模块用于判断输入数据与处理后结果在技术上是否足够可靠，能否支撑后续解读。",
    },
    "native_reports": {
        "en": "Native reports preserve the original tool-generated HTML experience while being bundled into the standalone TAFFISH report whenever possible.",
        "zh": "原生报告尽可能保留上游工具生成的 HTML 体验，同时被打包进 TAFFISH 单文件报告中。",
    },
    "differential_expression": {
        "en": "Differential-expression figures and tables describe which features change between conditions and how strongly the samples support that contrast.",
        "zh": "差异表达图表说明不同条件之间哪些特征发生变化，以及样本对该比较的支持强度。",
    },
    "enrichment": {
        "en": "Enrichment results translate gene-level changes into interpretable biological processes, pathways, or functional categories.",
        "zh": "富集结果把基因层面的变化转化为更容易解释的生物过程、通路或功能类别。",
    },
    "phylogeny": {
        "en": "Phylogeny sections summarize sequence alignment, tree construction, and support evidence for interpreting evolutionary relationships.",
        "zh": "系统发育章节汇总序列比对、建树过程和支持度证据，用于解释演化关系。",
    },
}


def load_asset_text(name: str) -> str:
    return files("taffish_report_render.assets").joinpath(name).read_text(encoding="utf-8")


def load_asset_bytes(name: str) -> bytes:
    return files("taffish_report_render.assets").joinpath(name).read_bytes()


def script_safe_text(text: str) -> str:
    return text.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")


def load_ngl_runtime_pack() -> tuple[str, str, bytes, str]:
    env_path = os.environ.get(NGL_RUNTIME_ENV, "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        if not path.is_file():
            raise RenderError(f"{NGL_RUNTIME_ENV} points to a missing NGL runtime file: {path}")
        data = path.read_bytes()
        validate_ngl_runtime_bytes(data, str(path))
        version = os.environ.get("TAFFISH_REPORT_RENDER_NGL_VERSION", "external").strip() or "external"
        if os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") == "1" and b"TAFFISH_NGL_TEST_SHIM" in data:
            version = "test-shim"
        return str(path), path.name, data, version

    runtime_dir = files("taffish_report_render").joinpath("runtime_packs", "ngl")
    for candidate_name in ("ngl.js",):
        resource = runtime_dir.joinpath(candidate_name)
        if resource.is_file():
            data = resource.read_bytes()
            validate_ngl_runtime_bytes(data, f"runtime_packs/ngl/{candidate_name}")
            version_resource = runtime_dir.joinpath("VERSION")
            version = version_resource.read_text(encoding="utf-8").strip() if version_resource.is_file() else NGL_RUNTIME_VERSION
            return f"runtime_packs/ngl/{candidate_name}", candidate_name, data, version

    for path in [
        Path("/opt/taffish-report-render/python/taffish_report_render/runtime_packs/ngl/ngl.js"),
        Path("/usr/local/share/taffish-report-render/runtime-packs/ngl/ngl.js"),
    ]:
        if path.is_file():
            data = path.read_bytes()
            validate_ngl_runtime_bytes(data, str(path))
            version_file = path.with_name("VERSION")
            version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else NGL_RUNTIME_VERSION
            return str(path), path.name, data, version

    raise RenderError(
        "structure_viewer runtime='ngl' was requested, but no NGL runtime pack was found. "
        "This is a renderer installation issue, not a report TOML issue. Normal report use only "
        "needs TOML/JSON plus --root; browser runtime files must be vendored into the renderer "
        "package/image before rendering or real-run testing."
    )


def validate_ngl_runtime_bytes(data: bytes, source: str) -> None:
    if os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") == "1" and b"TAFFISH_NGL_TEST_SHIM" in data:
        return
    if len(data) < 100_000:
        raise RenderError(f"NGL runtime candidate is too small to be a real bundle: {source}")
    sample = data[:2_000_000].decode("utf-8", errors="ignore")
    if "NGL" not in sample or "Stage" not in sample:
        raise RenderError(f"NGL runtime candidate does not look like an NGL bundle: {source}")
    externalized_markers = (
        'require("three")',
        "require('three')",
        'define(["exports","three"',
        "define(['exports','three'",
        ".NGL={},t.three,t.chroma,t.signalsWrapper,t.sprintfJs",
    )
    if any(marker in sample for marker in externalized_markers):
        raise RenderError(
            "NGL runtime candidate is dependency-externalized and cannot run inside a standalone HTML report: "
            f"{source}. Use the browser standalone bundle dist/ngl.js, not dist/ngl.umd.js."
        )


def load_plotly_runtime_pack() -> tuple[str, str, bytes, str]:
    asset_name = "plotly-1.2.0.min.js"
    data = load_asset_bytes(asset_name)
    if b"Plotly" not in data or b"newPlot" not in data:
        raise RenderError(f"bundled Plotly runtime does not look valid: assets/{asset_name}")
    return f"assets/{asset_name}", asset_name, data, PLOTLY_RUNTIME_ID


def load_echarts_runtime_pack() -> tuple[str, str, bytes, str]:
    asset_name = "echarts-6.1.0.min.js"
    data = load_asset_bytes(asset_name)
    sample = data[:2_000_000].decode("utf-8", errors="ignore")
    if len(data) < 200_000 or "echarts" not in sample or ".init" not in sample:
        raise RenderError(f"bundled ECharts runtime does not look valid: assets/{asset_name}")
    return f"assets/{asset_name}", asset_name, data, ECHARTS_RUNTIME_ID


def load_igv_runtime_pack() -> tuple[str, str, bytes, str]:
    env_path = os.environ.get(IGV_RUNTIME_ENV, "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        if not path.is_file():
            raise RenderError(f"{IGV_RUNTIME_ENV} points to a missing IGV runtime file: {path}")
        data = path.read_bytes()
        validate_igv_runtime_bytes(data, str(path))
        version = os.environ.get("TAFFISH_REPORT_RENDER_IGV_VERSION", "external").strip() or "external"
        if os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") == "1" and b"TAFFISH_IGV_TEST_SHIM" in data:
            version = "test-shim"
        return str(path), path.name, data, version

    runtime_dir = files("taffish_report_render").joinpath("runtime_packs", "igv")
    for candidate_name in ("igv.min.js", "igv.js"):
        resource = runtime_dir.joinpath(candidate_name)
        if resource.is_file():
            data = resource.read_bytes()
            validate_igv_runtime_bytes(data, f"runtime_packs/igv/{candidate_name}")
            version_resource = runtime_dir.joinpath("VERSION")
            version = version_resource.read_text(encoding="utf-8").strip() if version_resource.is_file() else "external"
            return f"runtime_packs/igv/{candidate_name}", candidate_name, data, version

    for path in [
        Path("/opt/taffish-report-render/python/taffish_report_render/runtime_packs/igv/igv.min.js"),
        Path("/usr/local/share/taffish-report-render/runtime-packs/igv/igv.min.js"),
    ]:
        if path.is_file():
            data = path.read_bytes()
            validate_igv_runtime_bytes(data, str(path))
            version_file = path.with_name("VERSION")
            version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "external"
            return str(path), path.name, data, version
    raise RenderError(
        "genome_browser runtime='igv' was requested, but no IGV runtime pack was found. "
        "This is a renderer installation issue, not a report TOML issue. Normal report use only "
        "needs TOML/JSON plus --root; browser runtime files must be vendored into the renderer "
        "package/image before rendering or real-run testing. Large genomic tracks can stay "
        "external, but the browser runtime itself must be available."
    )


def validate_igv_runtime_bytes(data: bytes, source: str) -> None:
    if os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") == "1" and b"TAFFISH_IGV_TEST_SHIM" in data:
        return
    if len(data) < 100_000:
        raise RenderError(f"IGV runtime candidate is too small to be a real bundle: {source}")
    sample = data[:2_000_000].decode("utf-8", errors="ignore")
    if "igv" not in sample.lower() or "createBrowser" not in sample:
        raise RenderError(f"IGV runtime candidate does not look like an igv.js browser bundle: {source}")


def known_external_script_asset(src: str) -> tuple[str, str] | None:
    normalized = src.strip().lower()
    known = {
        "https://opengene.org/plotly-1.2.0.min.js": ("plotly-1.2.0", "plotly-1.2.0.min.js"),
        "https://cdn.plot.ly/plotly-1.2.0.min.js": ("plotly-1.2.0", "plotly-1.2.0.min.js"),
    }
    return known.get(normalized)


def normalize_language_code(value: Any) -> str:
    code = str(value).strip()
    if not LANGUAGE_CODE_RE.match(code):
        raise RenderError(f"invalid language code: {code!r}")
    return code


def normalize_languages(value: Any = None, default: Any = None) -> tuple[list[str], str]:
    if value is None:
        items: list[Any] = DEFAULT_LANGUAGES[:]
    elif isinstance(value, str):
        items = [item for item in re.split(r"[\s,]+", value.strip()) if item]
    elif isinstance(value, list):
        items = value
    else:
        raise RenderError("languages must be a list or comma-separated string")

    languages: list[str] = []
    seen: set[str] = set()
    for item in items:
        code = normalize_language_code(item)
        if code not in seen:
            languages.append(code)
            seen.add(code)
    if not languages:
        languages = DEFAULT_LANGUAGES[:]

    default_code = normalize_language_code(default or DEFAULT_LANGUAGE)
    if default_code not in seen:
        languages.insert(0, default_code)
    return languages, default_code


def set_active_languages(languages: list[str], default: str) -> None:
    global ACTIVE_LANGUAGES, ACTIVE_LANGUAGE_DEFAULT
    ACTIVE_LANGUAGES = languages[:]
    ACTIVE_LANGUAGE_DEFAULT = default


def translated_value(value: dict[str, Any], lang: str) -> str:
    fallback_order = [lang, ACTIVE_LANGUAGE_DEFAULT, "en", "zh"]
    for key in fallback_order:
        candidate = value.get(key)
        if candidate is not None and str(candidate) != "":
            return str(candidate)
    for candidate in value.values():
        if candidate is not None and str(candidate) != "":
            return str(candidate)
    return ""


def language_visibility_css(languages: list[str]) -> str:
    rules = [".report-i18n { display: none !important; }"]
    for lang in languages:
        rules.append(
            f'html[data-lang="{lang}"] .report-i18n[data-i18n-lang="{lang}"] '
            "{ display: inline !important; }"
        )
    return "\n".join(rules)


def language_button_label(lang: str) -> str:
    return LANGUAGE_NAMES.get(lang, lang.upper())


def i18n(value: Any, key: str | None = None) -> str:
    if key is not None:
        value = value.get(key, {}) if isinstance(value, dict) else {}
    if isinstance(value, dict):
        pieces = []
        for lang in ACTIVE_LANGUAGES:
            text = escape(translated_value(value, lang))
            pieces.append(
                f'<span class="report-i18n lang-{escape(lang)}" data-i18n-lang="{escape(lang, quote=True)}">{text}</span>'
            )
        return "".join(pieces)
    else:
        text = escape("" if value is None else str(value))
        return "".join(
            f'<span class="report-i18n lang-{escape(lang)}" data-i18n-lang="{escape(lang, quote=True)}">{text}</span>'
            for lang in ACTIVE_LANGUAGES
        )


def render_structured_note_items(owner: dict[str, Any]) -> str:
    note_items = owner.get("note_items")
    if not isinstance(note_items, list) or not note_items:
        return ""
    rendered_items: list[str] = []
    for item in note_items:
        kind = str(item.get("kind", "summary"))
        if kind not in NOTE_ITEM_KINDS:
            continue
        body_html = f'<p class="structured-note-body">{i18n(item.get("body"))}</p>' if item.get("body") else ""
        list_html = ""
        localized_items = item.get("items")
        if isinstance(localized_items, dict) and localized_items:
            item_count = max((len(value) for value in localized_items.values() if isinstance(value, list)), default=0)
            rows = []
            for index in range(item_count):
                localized_row = {
                    lang: values[index]
                    for lang, values in localized_items.items()
                    if isinstance(values, list) and index < len(values)
                }
                rows.append(f"<li>{i18n(localized_row)}</li>")
            list_html = '<ul class="structured-note-list">' + "".join(rows) + "</ul>"
        rendered_items.append(
            f'<div class="structured-note-item structured-note-kind-{escape(kind)}" data-note-kind="{escape(kind, quote=True)}">'
            '<dt>'
            f'<span class="structured-note-label">{i18n(item.get("label"))}</span>'
            '</dt>'
            f'<dd>{body_html}{list_html}</dd>'
            '</div>'
        )
    if not rendered_items:
        return ""
    kinds = ",".join(str(item.get("kind", "")) for item in note_items)
    return (
        f'<dl class="structured-note" data-structured-note-count="{len(rendered_items)}" '
        f'data-structured-note-kinds="{escape(kinds, quote=True)}">'
        + "".join(rendered_items)
        + "</dl>"
    )


def render_note_block(
    owner: dict[str, Any],
    fallback: Any = None,
    classes: str = "component-note-block",
) -> str:
    items_html = render_structured_note_items(owner)
    lead = owner.get("note")
    if lead is None and not items_html:
        lead = fallback
    lead_html = f'<p class="structured-note-lead">{i18n(lead)}</p>' if lead else ""
    if not lead_html and not items_html:
        return ""
    return f'<div class="{escape(classes)}">{lead_html}{items_html}</div>'


def media_note_layout_values(component: dict[str, Any]) -> tuple[str | None, str, str, int]:
    declared_value = component.get("media_note_layout")
    declared = str(declared_value).strip().lower() if declared_value is not None else None
    requested = declared or "auto"
    note_items = component.get("note_items")
    note_item_count = len(note_items) if isinstance(note_items, list) else 0
    if requested == "compact" and note_item_count:
        effective = "compact"
    elif requested == "auto" and note_item_count >= 4:
        effective = "compact"
    else:
        effective = "stack"
    return declared, requested, effective, note_item_count


def text_value(value: Any, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get("en") or value.get("zh") or fallback)
    if value is None:
        return fallback
    return str(value)


def bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def int_value(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def float_value(value: Any, default: float, minimum: float | None = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def color_value(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if re.match(r"^#[0-9A-Fa-f]{6}$", text):
        return text
    return default


def css_var_style(values: dict[str, str | int | float | None]) -> str:
    pieces: list[str] = []
    for name, value in values.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        pieces.append(f"{name}:{escape(text, quote=True)}")
    return ";".join(pieces)


def label(en: str, zh: str) -> str:
    return i18n({"en": en, "zh": zh})


FIELD_LABELS = {
    "metric": {"en": "Metric", "zh": "指标"},
    "value": {"en": "Value", "zh": "数值"},
    "module": {"en": "Module", "zh": "模块"},
    "step": {"en": "Step", "zh": "步骤"},
    "name": {"en": "Name", "zh": "名称"},
    "status": {"en": "Status", "zh": "状态"},
    "note": {"en": "Note", "zh": "说明"},
    "kind": {"en": "Type", "zh": "类型"},
    "source": {"en": "Source", "zh": "来源"},
    "path": {"en": "Path", "zh": "路径"},
    "bytes": {"en": "Size", "zh": "大小"},
    "id": {"en": "ID", "zh": "ID"},
    "source_bytes": {"en": "Source bytes", "zh": "源文件字节"},
    "embedded_bytes": {"en": "Embedded bytes", "zh": "内嵌字节"},
    "sha256": {"en": "SHA256", "zh": "SHA256"},
    "message": {"en": "Message", "zh": "信息"},
    "feature": {"en": "Feature", "zh": "特征"},
    "term": {"en": "Term", "zh": "术语"},
    "definition": {"en": "Definition", "zh": "定义"},
    "topic": {"en": "Topic", "zh": "主题"},
    "meaning": {"en": "Meaning", "zh": "含义"},
    "criterion": {"en": "Criterion", "zh": "判定标准"},
    "evidence": {"en": "Evidence", "zh": "证据"},
    "impact": {"en": "Impact", "zh": "影响"},
    "severity": {"en": "Severity", "zh": "严重程度"},
    "title": {"en": "Title", "zh": "标题"},
    "body": {"en": "Body", "zh": "正文"},
    "action": {"en": "Action", "zh": "建议动作"},
}


STATUS_LABELS = {
    "embedded": {"en": "embedded", "zh": "已内嵌"},
    "linked": {"en": "linked", "zh": "外部链接"},
    "warn": {"en": "warning", "zh": "需注意"},
    "ok": {"en": "ok", "zh": "正常"},
    "fail": {"en": "failed", "zh": "失败"},
    "skipped": {"en": "skipped", "zh": "跳过"},
    "ready": {"en": "ready", "zh": "就绪"},
}


def field_label(name: str) -> str:
    normalized = name.strip()
    key = normalized.lower()
    return i18n(FIELD_LABELS.get(key, {"en": normalized, "zh": normalized}))


def field_label_pair(name: str) -> dict[str, str]:
    normalized = name.strip()
    key = normalized.lower()
    pair = FIELD_LABELS.get(key, {"en": normalized, "zh": normalized})
    return {"en": str(pair["en"]), "zh": str(pair["zh"])}


def status_label(status: str) -> str:
    normalized = status.strip().lower()
    return i18n(STATUS_LABELS.get(normalized, {"en": status, "zh": status}))


def split_language_column(name: str) -> tuple[str, str] | None:
    for separator in ("_", "."):
        if separator not in name:
            continue
        base, suffix = name.rsplit(separator, 1)
        if base and suffix in set(ACTIVE_LANGUAGES + DEFAULT_LANGUAGES):
            return base, suffix
    return None


def display_table_columns(headers: list[str]) -> list[TableColumn]:
    by_base: dict[str, dict[str, str]] = {}
    for header in headers:
        split = split_language_column(header)
        if split is None:
            continue
        base, lang = split
        by_base.setdefault(base, {})[lang] = header

    columns: list[TableColumn] = []
    consumed: set[str] = set()
    for header in headers:
        if header in consumed:
            continue
        split = split_language_column(header)
        if split is not None:
            base, _ = split
            variants = by_base.get(base, {})
            consumed.update(variants.values())
            fallback_sources = [variants[lang] for lang in ACTIVE_LANGUAGES if lang in variants]
            fallback_sources.extend(source for source in variants.values() if source not in fallback_sources)
            columns.append(TableColumn(label=base, variants=variants, fallback_sources=fallback_sources))
            continue
        variants = by_base.get(header, {})
        if variants:
            consumed.add(header)
            consumed.update(variants.values())
            fallback_sources = [header]
            fallback_sources.extend(variants[lang] for lang in ACTIVE_LANGUAGES if lang in variants)
            fallback_sources.extend(source for source in variants.values() if source not in fallback_sources)
            columns.append(TableColumn(label=header, source=header, variants=variants, fallback_sources=fallback_sources))
        else:
            consumed.add(header)
            columns.append(TableColumn(label=header, source=header, fallback_sources=[header]))
    return columns


def first_nonempty(row: dict[str, str], sources: list[str]) -> str:
    for source in sources:
        value = row.get(source, "")
        if value != "":
            return value
    return ""


def render_table_cell(column: TableColumn, row: dict[str, str]) -> str:
    if column.variants:
        values: dict[str, str] = {}
        fallback = first_nonempty(row, column.fallback_sources)
        for lang in ACTIVE_LANGUAGES:
            source = column.variants.get(lang)
            values[lang] = row.get(source, "") if source else fallback
        return i18n(values)
    value = row.get(column.source or "", "")
    return escape(value)


def plain_table_cell_value(column: TableColumn, row: dict[str, str]) -> str:
    if column.variants:
        values = []
        for source in column.fallback_sources:
            value = row.get(source, "")
            if value and value not in values:
                values.append(value)
        return " / ".join(values)
    return row.get(column.source or "", "")


def component_nav_title(component: dict[str, Any]) -> str:
    if "title" in component:
        return i18n(component["title"])
    ctype = str(component.get("type", "component"))
    fallback = {
        "dashboard_cards": {"en": "Dashboard", "zh": "概览卡片"},
        "status_grid": {"en": "Status", "zh": "状态"},
        "quality_gate_table": {"en": "Quality gates", "zh": "质控门限"},
        "table_preview": {"en": "Table preview", "zh": "表格预览"},
        "code_file": {"en": "Text file", "zh": "文本文件"},
        "workflow_diagram": {"en": "Workflow", "zh": "流程"},
        "plot_card": {"en": "Plot", "zh": "图片"},
        "interactive_plot": {"en": "Interactive plot", "zh": "交互图"},
        "structure_viewer": {"en": "Structure viewer", "zh": "结构查看器"},
        "tree_viewer": {"en": "Tree viewer", "zh": "树图浏览器"},
        "sequence_alignment": {"en": "Sequence alignment", "zh": "序列比对"},
        "genome_browser": {"en": "Genome browser", "zh": "基因组浏览器"},
        "native_subreport": {"en": "Native report", "zh": "原生报告"},
    }.get(ctype, {"en": ctype.replace("_", " "), "zh": ctype.replace("_", " ")})
    return i18n(fallback)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return cleaned or "item"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mime_type_for_path(path: Path) -> str:
    mime = IMAGE_MIME_TYPES.get(path.suffix.lower())
    if mime is not None:
        return mime
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def data_uri(path: Path) -> str:
    data = path.read_bytes()
    mime = mime_type_for_path(path)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def text_data_uri(path: Path) -> str:
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:text/plain;base64,{encoded}"


def is_external_resource(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
        return True
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", stripped):
        return True
    if stripped.startswith("//"):
        return True
    return False


def attr_value(attrs: str, name: str) -> str | None:
    match = re.search(rf"\b{name}\s*=\s*([\"'])(.*?)\1", attrs, re.I | re.S)
    return match.group(2) if match else None


def replace_attr(attrs: str, name: str, value: str) -> str:
    pattern = re.compile(rf"(\b{name}\s*=\s*)([\"'])(.*?)\2", re.I | re.S)
    escaped = escape(value, quote=True)
    if pattern.search(attrs):
        return pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{escaped}{m.group(2)}", attrs, count=1)
    return attrs.rstrip() + f' {name}="{escaped}"'


def resolve_optional_resource(base_dir: Path, href: str) -> Path | None:
    if is_external_resource(href):
        return None
    clean_href = href.split("#", 1)[0].split("?", 1)[0]
    if not clean_href:
        return None
    path = (base_dir / clean_href).resolve()
    try:
        path.relative_to(base_dir.resolve())
    except ValueError:
        return None
    return path if path.exists() and path.is_file() else None


def inline_css_urls(css: str, base_dir: Path, unresolved: list[str]) -> str:
    resource_suffixes = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".css",
        ".js",
        ".map",
    }

    def should_track_missing_css_url(href: str) -> bool:
        if any(token in href for token in ("+", "=", "{", "}", "<", ">", " ")):
            return False
        suffix = Path(href.split("#", 1)[0].split("?", 1)[0]).suffix.lower()
        return suffix in resource_suffixes

    def repl(match: re.Match[str]) -> str:
        quote = match.group(1) or ""
        href = match.group(2).strip()
        if is_external_resource(href):
            return match.group(0)
        resource = resolve_optional_resource(base_dir, href)
        if resource is None:
            if should_track_missing_css_url(href):
                unresolved.append(href)
            return match.group(0)
        return f"url({quote}{data_uri(resource)}{quote})"

    return re.sub(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", repl, css, flags=re.I)


def inline_srcset(value: str, base_dir: Path, unresolved: list[str]) -> str:
    items = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        bits = item.split()
        href = bits[0]
        if is_external_resource(href):
            items.append(item)
            continue
        resource = resolve_optional_resource(base_dir, href)
        if resource is None:
            unresolved.append(href)
            items.append(item)
            continue
        bits[0] = data_uri(resource)
        items.append(" ".join(bits))
    return ", ".join(items)


def discover_linked_html_pages(path: Path, limit: int = 25) -> list[Path]:
    seen = {path.resolve()}
    queue = [path]
    pages: list[Path] = []
    while queue and len(pages) < limit:
        current = queue.pop(0)
        text = current.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"<a\b([^>]*)>", text, flags=re.I | re.S):
            href = attr_value(match.group(1), "href")
            if not href or is_external_resource(href):
                continue
            resource = resolve_optional_resource(current.parent, href)
            if resource is None or resource.suffix.lower() not in {".html", ".htm"}:
                continue
            resolved = resource.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            pages.append(resource)
            queue.append(resource)
            if len(pages) >= limit:
                break
    return pages


def component_extra_pages(component: dict[str, Any], ctx: RenderContext, main_path: Path) -> list[Path]:
    pages: list[Path] = []
    seen = {main_path.resolve()}

    def add_page(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        if path.suffix.lower() not in {".html", ".htm"}:
            raise RenderError(f"native_subreport extra page is not HTML: {path}")
        seen.add(resolved)
        pages.append(path)

    for item in component.get("pages", []) or []:
        rel = item.get("path") if isinstance(item, dict) else str(item)
        add_page(resolve_path(ctx.root, rel))
    if bool(component.get("embed_linked_pages", False)):
        limit = int(component.get("linked_page_limit", 25))
        for page in discover_linked_html_pages(main_path, limit=limit):
            add_page(page)
    return pages


def inline_subreport_html(path: Path, page_id_map: dict[str, str] | None = None) -> tuple[str, list[str]]:
    base_dir = path.parent.resolve()
    unresolved: list[str] = []
    inlined_runtimes: set[str] = set()
    html_text = path.read_text(encoding="utf-8", errors="replace")

    def stylesheet_repl(match: re.Match[str]) -> str:
        attrs = match.group(1)
        rel = attr_value(attrs, "rel") or ""
        href = attr_value(attrs, "href")
        if href is None or "stylesheet" not in rel.lower() or is_external_resource(href):
            return match.group(0)
        resource = resolve_optional_resource(base_dir, href)
        if resource is None:
            unresolved.append(href)
            return match.group(0)
        css = resource.read_text(encoding="utf-8", errors="replace")
        css = inline_css_urls(css, resource.parent, unresolved)
        return f"<style data-taffish-inline-source={json.dumps(href)}>{css}</style>"

    html_text = re.sub(r"<link\b([^>]*)>", stylesheet_repl, html_text, flags=re.I | re.S)

    def script_repl(match: re.Match[str]) -> str:
        attrs_before = match.group(1)
        quote = match.group(2)
        src = match.group(3)
        attrs_after = match.group(4)
        body = match.group(5) or ""
        known_asset = known_external_script_asset(src)
        if known_asset is not None:
            runtime_id, asset_name = known_asset
            inlined_runtimes.add(runtime_id)
            script = load_asset_text(asset_name)
            attrs = (attrs_before + attrs_after).strip()
            attrs = re.sub(r"\s*\bsrc\s*=\s*([\"']).*?\1", "", attrs, flags=re.I | re.S).strip()
            attrs = (
                attrs
                + f' data-taffish-runtime={json.dumps(runtime_id)}'
                + f' data-taffish-inline-source={json.dumps(src)}'
            ).strip()
            return f"<script {attrs}>{script}{body}</script>"
        if is_external_resource(src):
            return match.group(0)
        resource = resolve_optional_resource(base_dir, src)
        if resource is None:
            unresolved.append(src)
            return match.group(0)
        script = resource.read_text(encoding="utf-8", errors="replace")
        attrs = (attrs_before + attrs_after).strip()
        attrs = re.sub(r"\s*\bsrc\s*=\s*([\"']).*?\1", "", attrs, flags=re.I | re.S).strip()
        attrs = (attrs + f' data-taffish-inline-source={json.dumps(src)}').strip()
        return f"<script {attrs}>{script}{body}</script>"

    html_text = re.sub(
        r"<script\b([^>]*)\bsrc\s*=\s*([\"'])(.*?)\2([^>]*)>(.*?)</script>",
        script_repl,
        html_text,
        flags=re.I | re.S,
    )
    if "plotly-1.2.0" in inlined_runtimes:
        html_text = re.sub(
            r"<script\b[^>]*>\s*window\.Plotly\s*\|\|\s*document\.write\(.*?</script>",
            "",
            html_text,
            flags=re.I | re.S,
        )

    def style_repl(match: re.Match[str]) -> str:
        attrs = match.group(1)
        css = inline_css_urls(match.group(2), base_dir, unresolved)
        return f"<style{attrs}>{css}</style>"

    html_text = re.sub(r"<style\b([^>]*)>(.*?)</style>", style_repl, html_text, flags=re.I | re.S)

    protected_blocks: list[str] = []

    def protect_block(match: re.Match[str]) -> str:
        protected_blocks.append(match.group(0))
        return f"\ue000TAFFISH_PROTECTED_BLOCK_{len(protected_blocks) - 1}\ue000"

    protected_html = re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", protect_block, html_text, flags=re.I | re.S)

    def resource_tag_repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs = match.group(2)
        for name in ("src", "poster", "data"):
            href = attr_value(attrs, name)
            if href is None or is_external_resource(href):
                continue
            resource = resolve_optional_resource(base_dir, href)
            if resource is None:
                unresolved.append(href)
                continue
            attrs = replace_attr(attrs, name, data_uri(resource))
        srcset = attr_value(attrs, "srcset")
        if srcset is not None:
            attrs = replace_attr(attrs, "srcset", inline_srcset(srcset, base_dir, unresolved))
        return f"<{tag}{attrs}>"

    protected_html = re.sub(
        r"<(img|source|video|audio|embed|object)\b([^>]*)>",
        resource_tag_repl,
        protected_html,
        flags=re.I | re.S,
    )

    if page_id_map:
        def local_page_link_repl(match: re.Match[str]) -> str:
            attrs = match.group(1)
            href = attr_value(attrs, "href")
            if href is None or is_external_resource(href):
                return match.group(0)
            resource = resolve_optional_resource(base_dir, href)
            if resource is None:
                return match.group(0)
            page_id = page_id_map.get(str(resource.resolve()))
            if page_id is None:
                return match.group(0)
            attrs = replace_attr(attrs, "href", "#taffish-subreport=" + quote(page_id, safe=""))
            attrs = replace_attr(attrs, "target", "_blank")
            attrs = replace_attr(attrs, "rel", "noopener")
            return f"<a{attrs}>"

        protected_html = re.sub(r"<a\b([^>]*)>", local_page_link_repl, protected_html, flags=re.I | re.S)

    for idx, block in enumerate(protected_blocks):
        protected_html = protected_html.replace(f"\ue000TAFFISH_PROTECTED_BLOCK_{idx}\ue000", block)
    html_text = protected_html

    return html_text, sorted(set(unresolved))


def resolve_path(root: Path, rel: str, required: bool = True) -> Path:
    if not rel:
        raise RenderError("empty asset path")
    candidate = Path(rel)
    if candidate.is_absolute():
        raise RenderError(f"absolute paths are not allowed in report specs: {rel}")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise RenderError(f"path escapes report root: {rel}")
    if required and not resolved.exists():
        raise RenderError(f"required asset is missing: {rel}")
    return resolved


def report_relative_href(ctx: RenderContext, path: Path, fallback_rel: str) -> str:
    if ctx.report_dir is not None:
        try:
            rel = os.path.relpath(path.resolve(), ctx.report_dir.resolve())
        except ValueError:
            rel = fallback_rel
    else:
        rel = fallback_rel
    return quote(rel.replace("\\", "/"), safe="/._-~")


def read_tsv(path: Path, limit: int | None = None) -> tuple[list[str], list[dict[str, str]]]:
    return read_delimited_table(path, delimiter="\t", limit=limit)


def read_delimited_table(
    path: Path, delimiter: str | None = None, limit: int | None = None
) -> tuple[list[str], list[dict[str, str]]]:
    if delimiter is None:
        delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            return [], []
        rows: list[dict[str, str]] = []
        for row in reader:
            if limit is not None and len(rows) >= limit:
                break
            rows.append({k: (v or "") for k, v in row.items() if k is not None})
        return list(reader.fieldnames), rows


def row_first(row: dict[str, str], names: list[str], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return default


def row_i18n(row: dict[str, str], base: str, fallback: str = "") -> dict[str, str]:
    values: dict[str, str] = {}
    fallback_value = row_first(row, [base, f"{base}_en", f"{base}.en", f"{base}_zh", f"{base}.zh"], fallback)
    for lang in ACTIVE_LANGUAGES:
        values[lang] = row_first(row, [f"{base}_{lang}", f"{base}.{lang}", base], fallback_value)
    if "en" not in values:
        values["en"] = row_first(row, [f"{base}_en", f"{base}.en", base], fallback_value)
    if "zh" not in values:
        values["zh"] = row_first(row, [f"{base}_zh", f"{base}.zh", base], fallback_value)
    return values


def row_bool(row: dict[str, str], names: list[str], default: bool) -> bool:
    value = row_first(row, names, "")
    return bool_value(value, default) if value != "" else default


def row_int(row: dict[str, str], names: list[str], default: int, minimum: int | None = None) -> int:
    value = row_first(row, names, "")
    return int_value(value, default, minimum=minimum) if value != "" else default


def collection_row_enabled(component: dict[str, Any], row: dict[str, str]) -> bool:
    enabled = row_first(row, ["enabled", "include", "selected"], "")
    if enabled and not bool_value(enabled, True):
        return False
    filter_column = str(component.get("filter_column", "")).strip()
    if not filter_column:
        return True
    filter_value = str(component.get("filter_value", "")).strip()
    values = {item.strip() for item in filter_value.split(",") if item.strip()}
    current = row.get(filter_column, "")
    return current in values if values else bool(current)


def collection_component_id(prefix: str, row: dict[str, str], rel: str, index: int) -> str:
    explicit = row_first(row, ["component_id", "id", "name"], "")
    if explicit:
        return slug(f"{prefix}-{explicit}" if prefix else explicit)
    stem = Path(rel).stem if rel else f"item-{index}"
    return slug(f"{prefix}-{stem}" if prefix else stem)


def scalar_override(component: dict[str, Any], target: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        if key in component:
            target[key] = component[key]


def copy_collection_note_items(component: dict[str, Any], target: dict[str, Any]) -> None:
    if "toc" in component:
        target["toc"] = json.loads(json.dumps(component["toc"], ensure_ascii=False))
    if "note_items" in component:
        target["note_items"] = json.loads(json.dumps(component["note_items"], ensure_ascii=False))


def expand_collection_component(component: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    ctype = str(component.get("type", ""))
    rel = str(component.get("source", ""))
    index_path = resolve_path(root, rel)
    headers, rows = read_tsv(index_path)
    if not headers:
        return []
    prefix = str(component.get("id_prefix") or component.get("id") or ctype.replace("_collection", ""))
    expanded: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        if not collection_row_enabled(component, row):
            continue
        if ctype == "plot_collection":
            image = row_first(row, ["image", "plot", "path", "source", "file"])
            if not image:
                continue
            item = {
                "type": "plot_card",
                "id": collection_component_id(prefix, row, image, idx),
                "image": image,
                "title": row_i18n(row, "title", Path(image).stem),
                "note": row_i18n(row, "note", row_first(row, ["caption", "description"], image)),
            }
            scalar_override(component, item, ["zoom", "default_fit"])
            copy_collection_note_items(component, item)
            expanded.append(item)
            continue
        if ctype == "table_collection":
            source = row_first(row, ["source", "table", "path", "file"])
            if not source:
                continue
            item = {
                "type": "table_preview",
                "id": collection_component_id(prefix, row, source, idx),
                "source": source,
                "title": row_i18n(row, "title", Path(source).stem),
                "note": row_i18n(row, "note", source),
            }
            for key in ("preview_rows", "max_embed_rows", "max_embed_bytes"):
                default = int_value(component.get(key), 8 if key == "preview_rows" else (5000 if key == "max_embed_rows" else 5_000_000), minimum=0 if key == "preview_rows" else 1)
                item[key] = row_int(row, [key], default, minimum=0 if key == "preview_rows" else 1)
            item["embed_full"] = row_bool(row, ["embed_full"], bool_value(component.get("embed_full"), True))
            item["default_state"] = row_first(row, ["default_state"], str(component.get("default_state", "preview")))
            copy_collection_note_items(component, item)
            expanded.append(item)
            continue
        if ctype == "code_file_collection":
            source = row_first(row, ["source", "code", "path", "file"])
            if not source:
                continue
            item = {
                "type": "code_file",
                "id": collection_component_id(prefix, row, source, idx),
                "source": source,
                "title": row_i18n(row, "title", Path(source).stem),
                "note": row_i18n(row, "note", source),
                "language": row_first(row, ["language", "syntax"], str(component.get("language", component.get("syntax", "text")))),
                "copy": row_bool(row, ["copy"], bool_value(component.get("copy"), True)),
            }
            scalar_override(component, item, ["max_embed_bytes", "max_lines"])
            copy_collection_note_items(component, item)
            expanded.append(item)
            continue
        if ctype == "native_subreport_collection":
            path_value = row_first(row, ["path", "html", "source", "file"])
            if not path_value:
                continue
            item = {
                "type": "native_subreport",
                "id": collection_component_id(prefix, row, path_value, idx),
                "path": path_value,
                "kind": row_first(row, ["kind", "report_kind"], str(component.get("kind", "html"))),
                "title": row_i18n(row, "title", Path(path_value).stem),
                "note": row_i18n(row, "note", path_value),
                "embed_policy": row_first(row, ["embed_policy"], str(component.get("embed_policy", "auto"))),
                "embed_linked_pages": row_bool(row, ["embed_linked_pages"], bool_value(component.get("embed_linked_pages"), False)),
            }
            if "linked_page_limit" in component or row_first(row, ["linked_page_limit"], ""):
                item["linked_page_limit"] = row_int(row, ["linked_page_limit"], int_value(component.get("linked_page_limit"), 25, minimum=1), minimum=1)
            copy_collection_note_items(component, item)
            expanded.append(item)
            continue
        raise RenderError(f"unsupported collection component type: {ctype}")
    return expanded


def record_asset(ctx: RenderContext, kind: str, component_id: str, rel: str, path: Path) -> None:
    data = path.read_bytes()
    record_asset_bytes(ctx, kind, component_id, rel, data)


def record_asset_bytes(ctx: RenderContext, kind: str, component_id: str, rel: str, data: bytes) -> None:
    ctx.assets.append(
        AssetRecord(
            kind=kind,
            component_id=component_id,
            path=rel,
            bytes=len(data),
            sha256=sha256_bytes(data),
        )
    )


def ensure_runtime_pack(ctx: RenderContext, runtime_id: str, component_id: str) -> None:
    if runtime_id in ctx.runtime_packs:
        return
    if runtime_id == "ngl":
        source, asset_name, data, version = load_ngl_runtime_pack()
        rel = f"runtime-packs/ngl/{asset_name}"
        message = f"version=ngl@{version}"
    elif runtime_id == PLOTLY_RUNTIME_ID:
        source, asset_name, data, version = load_plotly_runtime_pack()
        rel = f"runtime-packs/plotly/{asset_name}"
        message = f"version={version}"
    elif runtime_id == ECHARTS_RUNTIME_ID:
        source, asset_name, data, version = load_echarts_runtime_pack()
        rel = f"runtime-packs/echarts/{asset_name}"
        message = f"version={version}"
    elif runtime_id == IGV_RUNTIME_ID:
        source, asset_name, data, version = load_igv_runtime_pack()
        rel = f"runtime-packs/igv/{asset_name}"
        message = f"version=igv@{version}"
    else:
        raise RenderError(f"unsupported runtime pack: {runtime_id}")
    ctx.runtime_packs[runtime_id] = data.decode("utf-8", errors="replace")
    ctx.runtime_pack_versions[runtime_id] = version
    record_asset_bytes(ctx, "runtime", component_id, rel, data)
    if source != rel:
        ctx.assets[-1].message = f"source={source}; {message}"
    else:
        ctx.assets[-1].message = message


def parse_spec(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".toml":
        with path.open("rb") as handle:
            return tomllib.load(handle)
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    raise RenderError("spec must be TOML or JSON")


def validate_i18n(value: Any, label: str) -> None:
    if not isinstance(value, dict) or "en" not in value or "zh" not in value:
        raise RenderError(f"{label} must contain both en and zh text")


def validate_note_item_languages(value: Any, location: str, languages: list[str]) -> None:
    if not isinstance(value, dict):
        raise RenderError(f"{location} must be a language table")
    for lang in languages:
        if lang not in value or not isinstance(value[lang], str) or not value[lang].strip():
            raise RenderError(f"{location}.{lang} must be a non-empty string")


def validate_note_items(value: Any, location: str, languages: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise RenderError(f"{location} must be an array of tables")
    for index, item in enumerate(value, start=1):
        item_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            raise RenderError(f"{item_location} must be a table")
        unknown = sorted(set(item) - NOTE_ITEM_FIELDS)
        if unknown:
            raise RenderError(f"{item_location} has unknown fields: {', '.join(unknown)}")
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in NOTE_ITEM_KINDS:
            raise RenderError(f"{item_location}.kind must be one of: {', '.join(NOTE_ITEM_KINDS)}")
        validate_note_item_languages(item.get("label"), f"{item_location}.label", languages)
        has_body = "body" in item
        has_items = "items" in item
        if not has_body and not has_items:
            raise RenderError(f"{item_location} requires body or items")
        if has_body:
            validate_note_item_languages(item.get("body"), f"{item_location}.body", languages)
        if has_items:
            items = item.get("items")
            if not isinstance(items, dict):
                raise RenderError(f"{item_location}.items must be a language table of string arrays")
            expected_count: int | None = None
            for lang in languages:
                language_items = items.get(lang)
                if not isinstance(language_items, list) or not language_items:
                    raise RenderError(f"{item_location}.items.{lang} must be a non-empty string array")
                if any(not isinstance(entry, str) or not entry.strip() for entry in language_items):
                    raise RenderError(f"{item_location}.items.{lang} contains an empty or non-string item")
                if expected_count is None:
                    expected_count = len(language_items)
                elif len(language_items) != expected_count:
                    raise RenderError(f"{item_location}.items language arrays must have the same number of entries")


def validate_component_required_fields(component: dict[str, Any], location: str) -> None:
    ctype = str(component.get("type", ""))
    info = COMPONENT_REGISTRY.get(ctype, {})
    for field_name in info.get("required", []):
        value = component.get(field_name)
        if value is None or value == "":
            raise RenderError(f"{location}.{field_name} is required for {ctype}")
    if ctype == "plot_card":
        validate_plot_card_component(component, location)
    try:
        validate_extended_component(component, location)
    except ValueError as exc:
        raise RenderError(str(exc)) from exc


def validate_plot_card_component(component: dict[str, Any], location: str) -> None:
    layout = str(component.get("layout", "grid")).strip().lower()
    if layout not in {"grid", "wide", "media"}:
        raise RenderError(f"{location}.layout must be one of: grid, wide, media")

    enum_fields = {
        "image_position": ({"left", "right"}, "left"),
        "media_vertical_align": ({"start", "center"}, "start"),
        "media_gap": ({"compact", "normal", "relaxed"}, "normal"),
        "media_note_layout": (set(MEDIA_NOTE_LAYOUTS), "auto"),
    }
    for field_name, (allowed, default) in enum_fields.items():
        value = str(component.get(field_name, default)).strip().lower()
        if value not in allowed:
            choices = ", ".join(sorted(allowed))
            raise RenderError(f"{location}.{field_name} must be one of: {choices}")

    media_only_fields = {
        "image_position",
        "media_image_ratio",
        "media_vertical_align",
        "media_gap",
        "media_note_layout",
    }
    declared_media_fields = sorted(field for field in media_only_fields if field in component)
    if layout != "media" and declared_media_fields:
        fields = ", ".join(declared_media_fields)
        raise RenderError(f"{location}: media-only fields require layout=media: {fields}")

    if "media_image_ratio" in component:
        value = component["media_image_ratio"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RenderError(f"{location}.media_image_ratio must be a finite number between 0.25 and 0.70")
        ratio = float(value)
        if not math.isfinite(ratio) or not 0.25 <= ratio <= 0.70:
            raise RenderError(f"{location}.media_image_ratio must be a finite number between 0.25 and 0.70")


def validate_spec(spec: dict[str, Any], allow_collections: bool = True) -> None:
    if spec.get("template") != "taffish-flow-report":
        raise RenderError("template must be taffish-flow-report")
    project = spec.get("project")
    if not isinstance(project, dict):
        raise RenderError("project table is required")
    validate_i18n(project.get("title"), "project.title")
    languages, _ = normalize_languages(spec.get("languages"), spec.get("language_default", DEFAULT_LANGUAGE))
    sections = spec.get("sections")
    if not isinstance(sections, list) or not sections:
        raise RenderError("at least one section is required")
    seen_sections: set[str] = set()
    seen_components: set[str] = set()
    for idx, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            raise RenderError(f"section {idx} is not an object")
        section_id = slug(str(section.get("id") or f"section-{idx}"))
        if section_id in seen_sections:
            raise RenderError(f"duplicate section id: {section_id}")
        if section_id in AUTOMATIC_SECTIONS:
            raise RenderError(f"section id is reserved by the renderer: {section_id}")
        seen_sections.add(section_id)
        validate_i18n(section.get("title"), f"section {section_id}.title")
        validate_note_items(section.get("note_items"), f"section {section_id}.note_items", languages)
        for cidx, component in enumerate(section.get("components", []), start=1):
            if not isinstance(component, dict):
                raise RenderError(f"component {section_id}.{cidx} is not an object")
            ctype = component.get("type")
            if ctype not in COMPONENTS:
                raise RenderError(f"unsupported component type: {ctype}")
            if not allow_collections and ctype in COLLECTION_COMPONENTS:
                raise RenderError(f"collection component was not expanded before render: {ctype}")
            component_id = slug(str(component.get("id") or f"{section_id}-{ctype}-{cidx}"))
            if component_id in seen_components:
                raise RenderError(f"duplicate component id: {component_id}")
            seen_components.add(component_id)
            validate_note_items(
                component.get("note_items"),
                f"component {section_id}.{component_id}.note_items",
                languages,
            )
            validate_component_required_fields(component, f"component {section_id}.{component_id}")
    try:
        validate_toc(spec, slug, languages)
    except ValueError as exc:
        raise RenderError(str(exc)) from exc


def normalize_spec(spec: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    normalized = json.loads(json.dumps(spec, ensure_ascii=False))
    normalized.setdefault("schema_version", "0.1")
    normalized.setdefault("template", "taffish-flow-report")
    normalized.setdefault("template_version", TEMPLATE_VERSION)
    normalized.setdefault("language_default", "zh")
    languages, language_default = normalize_languages(normalized.get("languages"), normalized.get("language_default"))
    normalized["languages"] = languages
    normalized["language_default"] = language_default
    set_active_languages(languages, language_default)
    normalized.setdefault("provenance", {})
    for sidx, section in enumerate(normalized.get("sections", []), start=1):
        section["id"] = slug(str(section.get("id") or f"section-{sidx}"))
        section.setdefault("kind", "section")
        expanded_components: list[dict[str, Any]] = []
        for cidx, component in enumerate(section.get("components", []), start=1):
            component["id"] = slug(str(component.get("id") or f"{section['id']}-{component.get('type', 'component')}-{cidx}"))
            if component.get("type") in COLLECTION_COMPONENTS and root is not None:
                expanded = expand_collection_component(component, root)
                expanded_components.extend(expanded)
                if not expanded and "toc" in component:
                    # 空 collection 仍须保留显式启用新目录模式的意图。
                    section.setdefault("toc", {})
            else:
                expanded_components.append(component)
        section["components"] = expanded_components
        for cidx, component in enumerate(section.get("components", []), start=1):
            component["id"] = slug(str(component.get("id") or f"{section['id']}-{component.get('type', 'component')}-{cidx}"))
    return normalized


def render_dashboard(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    headers, rows = read_tsv(path, limit=12)
    cards = []
    for idx, row in enumerate(rows, start=1):
        if "metric" in row and "value" in row:
            label, value, note = row["metric"], row["value"], row.get("note", "")
        elif "field" in row and "value" in row:
            label, value, note = row["field"], row["value"], row.get("note", "")
        else:
            label = row.get(headers[0], f"row {idx}") if headers else f"row {idx}"
            value = row.get(headers[1], "") if len(headers) > 1 else ""
            note = "; ".join(f"{h}={row.get(h, '')}" for h in headers[2:5])
        cards.append(
            '<article class="dashboard-card">'
            f"<small>{escape(label)}</small>"
            f"<strong>{escape(value)}</strong>"
            f"<p>{escape(note)}</p>"
            "</article>"
        )
    if not cards:
        cards.append(
            '<article class="dashboard-card">'
            f"<small>{label('No data', '无数据')}</small>"
            "<strong>0</strong>"
            f"<p>{label('Empty source table.', '源表为空。')}</p>"
            "</article>"
        )
    return (
        f'<div class="dashboard-component" id="{escape(component["id"])}">'
        f'{render_note_block(component, classes="component-intro")}'
        f'<div class="dashboard-grid">' + "\n".join(cards) + "</div></div>"
    )


def render_status_grid(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    _, rows = read_tsv(path)
    cards = []
    for row in rows:
        module = row.get("module") or row.get("step") or row.get("name") or "module"
        status = (row.get("status") or "neutral").lower()
        note_en = row.get("note_en") or row.get("note") or ""
        note_zh = row.get("note_zh") or note_en
        cards.append(
            f'<article class="status-card status-{escape(status)}">'
            f'<span class="status-dot status-{escape(status)}"></span>'
            '<div class="status-card-content">'
            f"<strong>{escape(module)}</strong>"
            f"<small>{escape(status.upper())}</small>"
            f"<p>{i18n({'en': note_en, 'zh': note_zh})}</p>"
            "</div>"
            "</article>"
        )
    return (
        f'<div class="status-component" id="{escape(component["id"])}">'
        f'{render_note_block(component, classes="component-intro")}'
        f'<div class="status-grid">' + "\n".join(cards) + "</div></div>"
    )


def render_table_rows(columns: list[TableColumn], rows: list[dict[str, str]], preview_limit: int | None = None) -> str:
    rendered_rows = []
    for idx, row in enumerate(rows):
        cells = []
        for column in columns:
            plain = plain_table_cell_value(column, row)
            cell_attrs = (
                f'data-cell-value="{escape(plain, quote=True)}" '
                f'title="{escape(plain, quote=True)}" tabindex="0"'
            )
            cells.append(f"<td {cell_attrs}>{render_table_cell(column, row)}</td>")
        preview_attr = ' data-preview-hidden="true"' if preview_limit is not None and idx >= preview_limit else ""
        rendered_rows.append(f'<tr data-table-row{preview_attr}>' + "".join(cells) + "</tr>")
    return "".join(rendered_rows)


def render_table(
    headers: list[str],
    rows: list[dict[str, str]],
    wrap_class: str = "table-wrap",
    table_class: str = "taffish-table",
    preview_limit: int | None = None,
) -> str:
    columns = display_table_columns(headers)
    head = "".join(
        f'<th><button type="button" class="table-sort-button" data-table-sort="{idx}">{field_label(column.label)}</button></th>'
        for idx, column in enumerate(columns)
    )
    body = render_table_rows(columns, rows, preview_limit=preview_limit)
    return f'<div class="{escape(wrap_class)}"><table class="{escape(table_class)}" data-table-ui><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_component_intro(component: dict[str, Any]) -> str:
    return render_note_block(component, classes="component-intro")


def render_quality_gate_table(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    headers, rows = read_tsv(path)
    return f'<div class="gate-table" id="{escape(component["id"])}">{render_component_intro(component)}{render_table(headers, rows)}</div>'


def render_table_preview(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    preview_rows = int_value(component.get("preview_rows"), 8, minimum=0)
    max_embed_rows = int_value(component.get("max_embed_rows"), 5000, minimum=1)
    max_embed_bytes = int_value(component.get("max_embed_bytes"), 5_000_000, minimum=1)
    default_state = str(component.get("default_state", "preview")).strip().lower()
    if default_state not in {"preview", "collapsed", "full"}:
        default_state = "preview"
    embed_full = bool_value(component.get("embed_full"), True)
    headers, rows = read_tsv(path, limit=preview_rows)
    source_bytes = path.stat().st_size
    full_headers: list[str] = headers
    full_rows: list[dict[str, str]] = []
    full_embedded = False
    full_message = {
        "en": "The full table is embedded in this same table; expand it to show all rows, search, sort, and scroll horizontally.",
        "zh": "完整表格已内嵌在同一张表中；展开后可查看全部行、搜索、排序，并左右滚动宽表列。",
    }
    if embed_full and source_bytes <= max_embed_bytes:
        full_headers, candidate_rows = read_tsv(path, limit=max_embed_rows + 1)
        if len(candidate_rows) <= max_embed_rows:
            full_rows = candidate_rows
            full_embedded = True
        else:
            full_message = {
                "en": f"Full table is not embedded because it exceeds max_embed_rows={max_embed_rows}. Keep the original result file.",
                "zh": f"完整表格未内嵌，因为超过 max_embed_rows={max_embed_rows}。请保留原始结果文件。",
            }
    elif embed_full:
        full_message = {
            "en": f"Full table is not embedded because the source file exceeds max_embed_bytes={max_embed_bytes}. Keep the original result file.",
            "zh": f"完整表格未内嵌，因为源文件超过 max_embed_bytes={max_embed_bytes}。请保留原始结果文件。",
        }
    else:
        full_message = {"en": "Full-table embedding is disabled for this component.", "zh": "此组件已关闭完整表格内嵌。"}
    title = component.get("title", {"en": rel, "zh": rel})
    if full_embedded:
        preview_note = {
            "en": f"{rel}; preview shown here, full table available in-place.",
            "zh": f"{rel}；这里显示预览，完整表格可在原地展开查看。",
        }
        if default_state == "collapsed":
            preview_note = {
                "en": f"{rel}; open this card to review the preview and full-table viewer.",
                "zh": f"{rel}；展开此卡片查看预览和完整表格查看器。",
            }
    else:
        preview_note = {"en": f"{rel}; showing up to {preview_rows} rows.", "zh": f"{rel}；最多显示 {preview_rows} 行。"}
    full_hidden = default_state != "full"
    table_headers = full_headers if full_embedded else headers
    table_rows = full_rows if full_embedded else rows
    table_preview_limit = preview_rows if full_embedded and full_hidden else None
    table_wrap_class = "table-wrap table-scroll table-preview-scroll"
    if full_embedded:
        table_wrap_class += " table-expandable-scroll"
    toolbar = ""
    if full_embedded:
        hidden_attr = " hidden" if full_hidden else ""
        toolbar = (
            f'<div class="table-toolbar"{hidden_attr} data-table-toolbar>'
            '<label class="table-search-label">'
            f'<span>{label("Search full table", "搜索完整表格")}</span>'
            f'<input type="search" data-table-search placeholder="{escape(text_value({"en": "Filter rows...", "zh": "过滤行..."}, "Filter rows..."), quote=True)}">'
            "</label>"
            f'<span class="table-row-count" data-table-row-count data-total-rows="{len(full_rows)}">{i18n({"en": f"{len(full_rows)} rows embedded", "zh": f"已内嵌 {len(full_rows)} 行"})}</span>'
            "</div>"
        )
    usage_note = ""
    if full_embedded:
        hidden_attr = " hidden" if full_hidden else ""
        usage_note = f'<p class="table-usage-note"{hidden_attr} data-table-usage>{i18n({"en": "This is one table: the button expands or collapses hidden rows in place. Click a cell to wrap or unwrap long content; double-click to copy the complete cell value. Sort columns from the header; search filters embedded rows without changing the source data.", "zh": "这是一张表：按钮会在原表中展开或收起隐藏行。点击单元格可展开或收起长内容；双击可复制完整单元格值。表头可排序；搜索只过滤内嵌行，不改变源数据。"})}</p>'
    scroll_controls = (
        '<div class="table-scroll-controls" hidden data-table-scroll-controls>'
        f'<span>{i18n({"en": "Wide table", "zh": "宽表"})}</span>'
        '<div class="table-scroll-buttons">'
        f'<button type="button" data-table-scroll-left aria-label="{escape(text_value({"en": "Scroll table left", "zh": "向左滚动表格"}, "Scroll table left"), quote=True)}">{escape("←")}</button>'
        f'<button type="button" data-table-scroll-right aria-label="{escape(text_value({"en": "Scroll table right", "zh": "向右滚动表格"}, "Scroll table right"), quote=True)}">{escape("→")}</button>'
        "</div>"
        "</div>"
    )
    table_panel = (
        '<div class="table-preview-pane table-inline-full-panel" data-table-preview-pane data-table-scope>'
        f"{toolbar}"
        f"{scroll_controls}"
        f"{render_table(table_headers, table_rows, table_wrap_class, preview_limit=table_preview_limit)}"
        f"{usage_note}"
        "</div>"
    )
    source_href = report_relative_href(ctx, path, rel)
    source_link = (
        f'<a class="table-source-link" href="{escape(source_href)}" target="_blank" rel="noopener">'
        f'{label("Open source file", "打开源文件")}</a>'
    )
    open_attr = "" if default_state == "collapsed" else " open"
    badge = label("full available", "可展开完整表") if full_embedded else label("preview", "预览")
    toggle = ""
    if full_embedded:
        toggle_label = label("Hide full table", "收起完整表格") if not full_hidden else label("Show full table", "展开完整表格")
        toggle = (
            f'<button type="button" class="table-source-link table-full-toggle" '
            f'data-table-toggle aria-expanded="{"false" if full_hidden else "true"}" '
            f'data-label-show-en="Show full table" data-label-show-zh="展开完整表格" '
            f'data-label-hide-en="Hide full table" data-label-hide-zh="收起完整表格">'
            f"{toggle_label}</button>"
        )
    return (
        f'<details class="table-card table-preview-card{" is-table-expanded" if full_embedded and not full_hidden else ""}" '
        f'id="{escape(component["id"])}"{open_attr}>'
        "<summary>"
        '<span class="table-summary-main">'
        f"<strong>{i18n(title)}</strong>"
        f"<small>{i18n(preview_note)}</small>"
        "</span>"
        f'<span class="table-summary-badge">{badge}</span>'
        "</summary>"
        '<div class="table-card-body">'
        f"{render_component_intro(component)}"
        f"{table_panel}"
        '<div class="table-preview-actions">'
        f"{toggle}"
        f"{source_link}"
        f'<span class="table-embed-note">{i18n(full_message)}</span>'
        "</div>"
        "</div>"
        "</details>"
    )


def render_code_file(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "text", component["id"], rel, path)
    max_bytes = int_value(component.get("max_embed_bytes"), 250_000, minimum=1)
    max_lines = int_value(component.get("max_lines"), 1000, minimum=1)
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines])
        truncated = True
    title = component.get("title", {"en": rel, "zh": rel})
    note = component.get("note", {"en": rel, "zh": rel})
    syntax = str(component.get("language", component.get("syntax", "text")))
    copy_enabled = bool_value(component.get("copy", True), True)
    copy_button = ""
    if copy_enabled:
        copy_button = (
            '<button class="copy-code-button" type="button" data-copy-code '
            f'data-copy-target="{escape(child_anchor(component["id"], "code"), quote=True)}">'
            f'{label("Copy", "复制")}</button>'
        )
    truncated_note = ""
    if truncated:
        truncated_note = (
            f'<p class="code-file-boundary">{i18n({"en": "The displayed text is truncated for report size control; keep the original file for the full content.", "zh": "为控制报告体积，此处展示文本已截断；完整内容请保留原始文件。"})}</p>'
        )
    return (
        f'<article class="code-file-card" id="{escape(component["id"])}">'
        '<div class="code-file-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f"<small>{escape(rel)}</small>"
        "</div>"
        f"{copy_button}"
        "</div>"
        f'{render_note_block(component, fallback=note, classes="code-file-note component-note-block")}'
        f'<pre class="code-file-pre"><code id="{escape(child_anchor(component["id"], "code"), quote=True)}" data-code-language="{escape(syntax, quote=True)}">{escape(text)}</code></pre>'
        f"{truncated_note}"
        "</article>"
    )


def render_workflow(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("source", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    headers, rows = read_tsv(path)
    steps = []
    for idx, row in enumerate(rows, start=1):
        fallback_name = row.get("flow") or row.get("step") or row.get(headers[0], f"step {idx}")
        name = row_i18n(row, "step", fallback_name)
        note = row_i18n(row, "note", row.get("outdir", ""))
        status = row_i18n(row, "status", row.get("status", ""))
        status_html = f'<span class="workflow-status">{i18n(status)}</span>' if any(status.values()) else ""
        steps.append(
            '<div class="workflow-step">'
            f'<span class="workflow-index">{idx}</span>'
            f"<strong>{i18n(name)}</strong>"
            f"{status_html}"
            f"<p>{i18n(note)}</p>"
            "</div>"
        )
    joined = '<span class="workflow-connector" aria-hidden="true"></span>'.join(steps)
    return (
        f'<div class="workflow-component" id="{escape(component["id"])}">'
        f'{render_component_intro(component)}'
        f'<div class="workflow-row">{joined}</div>'
        '</div>'
    )


def render_plot_card(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("image", "")
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "image", component["id"], rel, path)
    title = component.get("title", {"en": path.name, "zh": path.name})
    caption = component.get("caption")
    note_fallback = caption or {"en": rel, "zh": rel}
    zoom = bool_value(component.get("zoom"), True)
    fit = str(component.get("default_fit", "contain")).strip().lower()
    if fit not in {"contain", "original"}:
        fit = "contain"
    src = data_uri(path)
    title_en = text_value(title, path.name)
    image_html = (
        f'<button type="button" class="plot-image-button" data-open-image="{escape(component["id"])}" aria-label="{escape(title_en, quote=True)}">'
        f'<img src="{escape(src)}" alt="{escape(title_en)}">'
        "</button>"
        if zoom
        else f'<img src="{escape(src)}" alt="{escape(title_en)}">'
    )
    zoom_button = (
        f'<button type="button" class="plot-zoom-link" data-open-image="{escape(component["id"])}">{label("View large", "查看大图")}</button>'
        if zoom
        else ""
    )
    raw_href = report_relative_href(ctx, path, rel)
    layout = str(component.get("layout", "grid")).strip().lower()
    if layout not in {"grid", "wide", "media"}:
        layout = "grid"
    note_position = str(component.get("note_position", "bottom")).strip().lower()
    if note_position not in {"top", "bottom"}:
        note_position = "bottom"
    caption_html = (
        "<figcaption>"
        f"<strong>{i18n(title)}</strong>"
        '<span class="plot-links">'
        f"{zoom_button}"
        f'<a href="{escape(raw_href)}" target="_blank" rel="noopener">{label("Raw", "原始文件")}</a>'
        "</span>"
        "</figcaption>"
    )
    note_html = render_note_block(
        component,
        fallback=note_fallback,
        classes=f"plot-note plot-note-{note_position} component-note-block",
    )
    if layout == "media":
        image_position = str(component.get("image_position", "left")).strip().lower()
        vertical_align = str(component.get("media_vertical_align", "start")).strip().lower()
        media_gap = str(component.get("media_gap", "normal")).strip().lower()
        ratio = float(component.get("media_image_ratio", 0.42))
        image_track = f"{ratio * 100:.6g}fr"
        copy_track = f"{(1.0 - ratio) * 100:.6g}fr"
        media_style = css_var_style({
            "--media-image-track": image_track,
            "--media-copy-track": copy_track,
        })
        declared_note_layout, requested_note_layout, effective_note_layout, note_item_count = media_note_layout_values(component)
        caption_detail = (
            f'<div class="plot-media-caption">{i18n(caption)}</div>'
            if caption and (component.get("note") is not None or note_item_count > 0)
            else ""
        )
        note_layout_attrs = (
            f'data-media-note-layout="{escape(effective_note_layout, quote=True)}" '
            f'data-media-note-layout-requested="{escape(requested_note_layout, quote=True)}" '
            f'data-media-note-layout-declared="{escape(declared_note_layout or "", quote=True)}" '
            f'data-media-note-item-count="{note_item_count}"'
        )
        if effective_note_layout == "compact":
            media_head_html = (
                '<figcaption class="plot-media-head">'
                f'<strong>{i18n(title)}</strong>'
                f'<span class="plot-links">{zoom_button}'
                f'<a href="{escape(raw_href)}" target="_blank" rel="noopener">{label("Raw", "原始文件")}</a>'
                '</span>'
                '</figcaption>'
            )
            media_copy_html = (
                '<div class="plot-media-copy">'
                f'{note_html}{caption_detail}'
                '</div>'
            )
            return (
                f'<figure class="plot-card plot-card-media plot-media-note-compact plot-media-image-{escape(image_position)} '
                f'plot-media-align-{escape(vertical_align)} plot-media-gap-{escape(media_gap)}" '
                f'id="{escape(component["id"])}" data-image-fit="{escape(fit)}" '
                f'data-plot-layout="media" data-media-image-ratio="{ratio:.6g}" {note_layout_attrs} style="{media_style}">'
                f'{media_head_html}'
                f'<div class="plot-media-image">{image_html}</div>'
                f'{media_copy_html}'
                '</figure>'
            )
        media_caption_html = (
            '<figcaption class="plot-media-copy">'
            f'<strong>{i18n(title)}</strong>'
            f'<span class="plot-links">{zoom_button}'
            f'<a href="{escape(raw_href)}" target="_blank" rel="noopener">{label("Raw", "原始文件")}</a>'
            '</span>'
            f'{note_html}{caption_detail}'
            '</figcaption>'
        )
        return (
            f'<figure class="plot-card plot-card-media plot-media-image-{escape(image_position)} '
            f'plot-media-align-{escape(vertical_align)} plot-media-gap-{escape(media_gap)}" '
            f'id="{escape(component["id"])}" data-image-fit="{escape(fit)}" '
            f'data-plot-layout="media" data-media-image-ratio="{ratio:.6g}" {note_layout_attrs} style="{media_style}">'
            f'<div class="plot-media-image">{image_html}</div>'
            f'{media_caption_html}'
            '</figure>'
        )
    ordered_content = (
        f"{caption_html}{note_html}{image_html}"
        if note_position == "top"
        else f"{image_html}{caption_html}{note_html}"
    )
    return (
        f'<figure class="plot-card plot-card-{escape(layout)}" id="{escape(component["id"])}" '
        f'data-image-fit="{escape(fit)}" data-plot-layout="{escape(layout)}">'
        f"{ordered_content}"
        "</figure>"
    )


def parse_newick(text: str) -> dict[str, Any]:
    source = text.strip()
    if source.endswith(";"):
        source = source[:-1]
    idx = 0

    def skip_space() -> None:
        nonlocal idx
        while idx < len(source) and source[idx].isspace():
            idx += 1

    def parse_token(stops: set[str]) -> str:
        nonlocal idx
        skip_space()
        token: list[str] = []
        if idx < len(source) and source[idx] in {"'", '"'}:
            quote_char = source[idx]
            idx += 1
            while idx < len(source):
                char = source[idx]
                idx += 1
                if char == quote_char:
                    break
                token.append(char)
            skip_space()
            return "".join(token).strip()
        while idx < len(source) and source[idx] not in stops:
            token.append(source[idx])
            idx += 1
        return "".join(token).strip()

    def parse_node() -> dict[str, Any]:
        nonlocal idx
        skip_space()
        children: list[dict[str, Any]] = []
        if idx < len(source) and source[idx] == "(":
            idx += 1
            while True:
                children.append(parse_node())
                skip_space()
                if idx >= len(source):
                    break
                if source[idx] == ",":
                    idx += 1
                    continue
                if source[idx] == ")":
                    idx += 1
                    break
                raise RenderError(f"invalid Newick tree near offset {idx}: expected ',' or ')'")
        name = parse_token({":", ",", "(", ")"})
        length = ""
        skip_space()
        if idx < len(source) and source[idx] == ":":
            idx += 1
            length = parse_token({",", "(", ")"})
        return {"name": name, "length": length, "children": children}

    if not source:
        raise RenderError("empty Newick tree")
    root = parse_node()
    skip_space()
    if idx != len(source):
        raise RenderError(f"invalid Newick tree near offset {idx}: trailing text")
    return root


def newick_tree_stats(node: dict[str, Any]) -> dict[str, int]:
    tips = 0
    internal = 0
    max_depth = 0

    def walk(item: dict[str, Any], depth: int) -> None:
        nonlocal tips, internal, max_depth
        max_depth = max(max_depth, depth)
        children = item.get("children") or []
        if children:
            internal += 1
            for child in children:
                walk(child, depth + 1)
        else:
            tips += 1

    walk(node, 0)
    return {"tips": tips, "internal_nodes": internal, "max_depth": max_depth}


def render_newick_svg(
    node: dict[str, Any],
    width: int,
    height: int,
    show_labels: bool,
    show_branch_lengths: bool,
    max_tips: int,
    style_vars: dict[str, str | int | float | None] | None = None,
) -> tuple[str, dict[str, int]]:
    stats = newick_tree_stats(node)
    tips = max(1, stats["tips"])
    if tips > max_tips:
        show_labels = False
    width = max(360, width)
    height = max(240, height, tips * 24 + 80)
    left = 42
    right = 180 if show_labels else 56
    top = 32
    bottom = 34
    plot_w = max(80, width - left - right)
    plot_h = max(80, height - top - bottom)
    leaves_seen = 0
    max_x = 0.0

    def branch_length(item: dict[str, Any]) -> float:
        try:
            return max(0.0, float(str(item.get("length", "")).strip() or "0"))
        except ValueError:
            return 0.0

    def layout(item: dict[str, Any], depth: int, distance: float) -> None:
        nonlocal leaves_seen, max_x
        children = item.get("children") or []
        distance_here = distance + (branch_length(item) if show_branch_lengths else 1.0 if depth else 0.0)
        item["_x_value"] = distance_here if show_branch_lengths else float(depth)
        max_x = max(max_x, float(item["_x_value"]))
        if children:
            for child in children:
                layout(child, depth + 1, distance_here)
            item["_y_value"] = sum(float(child["_y_value"]) for child in children) / len(children)
        else:
            item["_y_value"] = float(leaves_seen)
            leaves_seen += 1

    layout(node, 0, 0.0)
    max_x = max(max_x, 1.0)
    y_denominator = max(1, tips - 1)

    def sx(item: dict[str, Any]) -> float:
        return left + (float(item["_x_value"]) / max_x) * plot_w

    def sy(item: dict[str, Any]) -> float:
        return top + (float(item["_y_value"]) / y_denominator) * plot_h

    lines: list[str] = []
    labels_html: list[str] = []

    def draw(item: dict[str, Any]) -> None:
        children = item.get("children") or []
        if children:
            child_ys = [sy(child) for child in children]
            x = sx(item)
            lines.append(
                f'<line x1="{x:.2f}" y1="{min(child_ys):.2f}" x2="{x:.2f}" y2="{max(child_ys):.2f}" class="tree-branch tree-branch-vertical"/>'
            )
            for child in children:
                lines.append(
                    f'<line x1="{x:.2f}" y1="{sy(child):.2f}" x2="{sx(child):.2f}" y2="{sy(child):.2f}" class="tree-branch"/>'
                )
                draw(child)
        else:
            name = str(item.get("name") or "tip")
            if show_labels:
                labels_html.append(
                    f'<text x="{sx(item) + 7:.2f}" y="{sy(item) + 4:.2f}" class="tree-tip-label">{escape(name)}</text>'
                )

    draw(node)
    axis = (
        f'<line x1="{left:.2f}" y1="{height - bottom + 6:.2f}" x2="{left + plot_w:.2f}" y2="{height - bottom + 6:.2f}" class="tree-scale"/>'
        f'<text x="{left + plot_w:.2f}" y="{height - 8:.2f}" class="tree-scale-label">{escape("branch length" if show_branch_lengths else "relative depth")}</text>'
    )
    style_attr = f' style="{css_var_style(style_vars or {})}"' if style_vars else ""
    svg = (
        f'<svg class="tree-viewer-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Newick tree"{style_attr}>'
        '<rect width="100%" height="100%" class="tree-background"/>'
        f"{''.join(lines)}{''.join(labels_html)}{axis}</svg>"
    )
    return svg, stats


def render_tree_viewer(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = str(component.get("source", ""))
    path = resolve_path(ctx.root, rel)
    component_id = component["id"]
    record_asset(ctx, "newick", component_id, rel, path)
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = parse_newick(text)
    width = int_value(component.get("width"), 920, minimum=360)
    height = int_value(component.get("height"), 420, minimum=240)
    show_labels = bool_value(component.get("show_labels"), True)
    show_lengths = bool_value(component.get("show_branch_lengths"), True)
    max_tips = int_value(component.get("max_tips"), 500, minimum=1)
    branch_width = float_value(component.get("branch_width"), 2.2, minimum=0.4)
    label_size = int_value(component.get("label_size"), 12, minimum=8)
    tree_style = {
        "--tree-branch-color": color_value(component.get("branch_color"), "#0b6f67"),
        "--tree-branch-width": f"{branch_width}px",
        "--tree-label-color": color_value(component.get("label_color"), "#10252c"),
        "--tree-label-size": f"{label_size}px",
        "--tree-scale-color": color_value(component.get("scale_color"), "#63757d"),
        "--tree-background-fill": color_value(component.get("background"), "transparent"),
    }
    svg, stats = render_newick_svg(tree, width, height, show_labels, show_lengths, max_tips, tree_style)
    title = component.get("title", {"en": "Phylogenetic tree", "zh": "系统发育树"})
    note = component.get("note", {"en": rel, "zh": rel})
    copy_enabled = bool_value(component.get("copy"), True)
    copy_button = (
        f'<button class="tree-action-link" type="button" data-copy-code data-copy-target="{escape(component_id, quote=True)}-newick">{label("Copy Newick", "复制 Newick")}</button>'
        if copy_enabled
        else ""
    )
    source_href = report_relative_href(ctx, path, rel)
    stats_html = (
        '<div class="tree-stats">'
        f'<span><strong>{stats["tips"]}</strong>{label("tips", "叶节点")}</span>'
        f'<span><strong>{stats["internal_nodes"]}</strong>{label("internal nodes", "内节点")}</span>'
        f'<span><strong>{stats["max_depth"]}</strong>{label("max depth", "最大深度")}</span>'
        "</div>"
    )
    return (
        f'<article class="tree-viewer-card" id="{escape(component_id)}" data-tree-viewer>'
        '<div class="tree-viewer-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        "</div>"
        '<span class="tree-runtime-badge">Newick</span>'
        "</div>"
        f"{stats_html}"
        f'<div class="tree-svg-wrap">{svg}</div>'
        '<div class="tree-actions">'
        f"{copy_button}"
        f'<a class="tree-action-link" href="{escape(source_href)}" target="_blank" rel="noopener">{label("Open source", "打开源文件")}</a>'
        "</div>"
        f'<details class="tree-source"><summary>{label("Show embedded Newick", "查看内嵌 Newick")}</summary>'
        f'<pre><code id="{escape(child_anchor(component_id, "newick"), quote=True)}">{escape(text)}</code></pre></details>'
        "</article>"
    )


def parse_fasta_alignment(text: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    name = ""
    seq: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if name:
                records.append((name, "".join(seq)))
            name = stripped[1:].strip() or f"sequence_{len(records) + 1}"
            seq = []
        else:
            seq.append(stripped.replace(" ", ""))
    if name:
        records.append((name, "".join(seq)))
    return records


def parse_clustal_alignment(text: str) -> list[tuple[str, str]]:
    chunks: dict[str, list[str]] = {}
    order: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.upper().startswith("CLUSTAL") or stripped.startswith("#"):
            continue
        if stripped[0].isspace():
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        name, seq = parts[0], parts[1]
        if name not in chunks:
            order.append(name)
            chunks[name] = []
        chunks[name].append(seq)
    return [(name, "".join(chunks[name])) for name in order]


def detect_alignment_alphabet(records: list[tuple[str, str]], requested: str) -> str:
    requested = requested.lower()
    if requested in {"dna", "rna", "protein"}:
        return requested
    letters = "".join(seq.upper().replace("-", "").replace(".", "") for _, seq in records)
    alphabet = set(letters)
    if alphabet and alphabet <= set("ACGTUN"):
        return "rna" if "U" in alphabet and "T" not in alphabet else "dna"
    return "protein"


def alignment_residue_class(char: str, alphabet: str) -> str:
    residue = char.upper()
    if residue in {"-", "."}:
        return "residue-gap"
    if alphabet in {"dna", "rna"}:
        mapping = {
            "A": "residue-a",
            "C": "residue-c",
            "G": "residue-g",
            "T": "residue-t",
            "U": "residue-u",
            "N": "residue-n",
        }
        return mapping.get(residue, "residue-other")
    if residue in set("AVLIMFWY"):
        return "residue-hydrophobic"
    if residue in set("KRH"):
        return "residue-positive"
    if residue in set("DE"):
        return "residue-negative"
    if residue in set("STNQ"):
        return "residue-polar"
    if residue in set("CGP"):
        return "residue-special"
    return "residue-other"


def alignment_consensus(records: list[tuple[str, str]], max_columns: int) -> str:
    if not records:
        return ""
    width = min(max_columns, max(len(seq) for _, seq in records))
    chars: list[str] = []
    for idx in range(width):
        column = [seq[idx].upper() for _, seq in records if idx < len(seq) and seq[idx] not in {"-", "."}]
        if not column:
            chars.append(" ")
        elif len(set(column)) == 1 and len(column) == len(records):
            chars.append("*")
        elif column.count(max(set(column), key=column.count)) >= max(2, len(column) // 2 + 1):
            chars.append(".")
        else:
            chars.append(" ")
    return "".join(chars)


def render_alignment_sequence(seq: str, alphabet: str, max_columns: int) -> str:
    pieces = []
    for char in seq[:max_columns]:
        pieces.append(f'<span class="seq-residue {alignment_residue_class(char, alphabet)}">{escape(char)}</span>')
    return "".join(pieces)


def render_sequence_alignment(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = str(component.get("source", ""))
    path = resolve_path(ctx.root, rel)
    component_id = component["id"]
    record_asset(ctx, "alignment", component_id, rel, path)
    text = path.read_text(encoding="utf-8", errors="replace")
    fmt = str(component.get("format", "auto")).strip().lower()
    if fmt == "auto":
        fmt = "fasta" if text.lstrip().startswith(">") else "clustal"
    records = parse_fasta_alignment(text) if fmt == "fasta" else parse_clustal_alignment(text)
    if not records:
        raise RenderError(f"sequence_alignment {component_id} did not find any aligned sequences in {rel}")
    max_sequences = int_value(component.get("max_sequences"), 80, minimum=1)
    max_columns = int_value(component.get("max_columns"), 240, minimum=1)
    alphabet = detect_alignment_alphabet(records, str(component.get("alphabet", "auto")).strip())
    color_scheme = str(component.get("color_scheme", "taffish")).strip().lower() or "taffish"
    font_size = int_value(component.get("font_size"), 13, minimum=8)
    label_width = int_value(component.get("label_width"), 240, minimum=88)
    alignment_style = {
        "--alignment-font-size": f"{font_size}px",
        "--alignment-label-width": f"{label_width}px",
        "--residue-a-bg": color_value(component.get("residue_a"), "#dff5ec"),
        "--residue-c-bg": color_value(component.get("residue_c"), "#ddeeff"),
        "--residue-g-bg": color_value(component.get("residue_g"), "#fff2c8"),
        "--residue-t-bg": color_value(component.get("residue_t"), "#ffe0dc"),
        "--residue-u-bg": color_value(component.get("residue_u"), "#ffe0dc"),
        "--residue-n-bg": color_value(component.get("residue_n"), "#efe7ff"),
        "--residue-gap-bg": color_value(component.get("gap_color"), "#edf3f2"),
        "--residue-hydrophobic-bg": color_value(component.get("residue_hydrophobic"), "#dff5ec"),
        "--residue-positive-bg": color_value(component.get("residue_positive"), "#ddeeff"),
        "--residue-negative-bg": color_value(component.get("residue_negative"), "#ffe0dc"),
        "--residue-polar-bg": color_value(component.get("residue_polar"), "#fff2c8"),
        "--residue-special-bg": color_value(component.get("residue_special"), "#efe7ff"),
    }
    style_attr = f' style="{css_var_style(alignment_style)}"'
    rows = []
    for name, seq in records[:max_sequences]:
        rows.append(
            '<div class="alignment-row">'
            f'<span class="alignment-label" title="{escape(name, quote=True)}">{escape(name)}</span>'
            f'<span class="alignment-seq">{render_alignment_sequence(seq, alphabet, max_columns)}</span>'
            "</div>"
        )
    if bool_value(component.get("show_consensus"), True):
        consensus = alignment_consensus(records[:max_sequences], max_columns)
        rows.append(
            '<div class="alignment-row alignment-consensus">'
            f'<span class="alignment-label">{label("consensus", "一致性")}</span>'
            f'<span class="alignment-seq">{escape(consensus)}</span>'
            "</div>"
        )
    truncated = len(records) > max_sequences or max(len(seq) for _, seq in records) > max_columns
    title = component.get("title", {"en": "Multiple sequence alignment", "zh": "多序列比对"})
    note = component.get("note", {"en": rel, "zh": rel})
    source_href = report_relative_href(ctx, path, rel)
    boundary_html = (
        f'<p class="alignment-boundary">{i18n({"en": "The browser view is truncated for layout stability; the full source alignment is embedded below and available from the source file.", "zh": "为保持排版稳定，浏览视图已截断；完整源比对文本内嵌在下方，也可打开源文件。"})}</p>'
        if truncated
        else ""
    )
    return (
        f'<article class="alignment-card alignment-scheme-{escape(color_scheme, quote=True)}" id="{escape(component_id)}" data-sequence-alignment{style_attr}>'
        '<div class="alignment-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        "</div>"
        f'<span class="alignment-runtime-badge">{escape(alphabet.upper())}</span>'
        "</div>"
        '<div class="alignment-meta">'
        f'<span><strong>{len(records)}</strong>{label("sequences", "序列")}</span>'
        f'<span><strong>{max(len(seq) for _, seq in records)}</strong>{label("columns", "列")}</span>'
        f'<span><strong>{escape(fmt)}</strong>{label("format", "格式")}</span>'
        "</div>"
        '<div class="alignment-scroll" tabindex="0">'
        + "".join(rows)
        + "</div>"
        f"{boundary_html}"
        '<div class="alignment-actions">'
        f'<button class="alignment-action-link" type="button" data-copy-code data-copy-target="{escape(component_id, quote=True)}-alignment">{label("Copy alignment", "复制比对")}</button>'
        f'<a class="alignment-action-link" href="{escape(source_href)}" target="_blank" rel="noopener">{label("Open source", "打开源文件")}</a>'
        "</div>"
        f'<details class="alignment-source"><summary>{label("Show embedded alignment text", "查看内嵌比对文本")}</summary>'
        f'<pre><code id="{escape(child_anchor(component_id, "alignment"), quote=True)}">{escape(text)}</code></pre></details>'
        "</article>"
    )


def normalize_genome_browser_modes(component: dict[str, Any]) -> list[str]:
    raw_modes = component.get("viewer_modes")
    if raw_modes is None:
        raw_modes = component.get("viewer_mode", "embedded")
    if isinstance(raw_modes, str):
        if raw_modes.strip().lower() in {"both", "embedded+linked", "linked+embedded"}:
            candidates = ["embedded", "linked"]
        else:
            candidates = [part.strip() for part in re.split(r"[,/|+ ]+", raw_modes) if part.strip()]
    elif isinstance(raw_modes, list):
        candidates = [str(value).strip() for value in raw_modes]
    else:
        candidates = [str(raw_modes).strip()]
    modes: list[str] = []
    for candidate in candidates:
        mode = candidate.lower()
        if mode not in {"embedded", "linked"}:
            raise RenderError(f"genome_browser viewer mode must be embedded or linked, got {candidate!r}")
        if mode not in modes:
            modes.append(mode)
    return modes or ["embedded"]


def genome_browser_mode_switch(viewer_modes: list[str], active_mode: str) -> str:
    if len(viewer_modes) <= 1:
        return ""
    buttons = []
    for mode in viewer_modes:
        active = mode == active_mode
        text = label("Embedded", "内嵌") if mode == "embedded" else label("Linked", "链接")
        buttons.append(
            f'<button type="button" class="genome-mode-button{" is-active" if active else ""}" '
            f'data-genome-browser-mode="{escape(mode, quote=True)}" '
            f'aria-pressed="{"true" if active else "false"}">{text}</button>'
        )
    return '<div class="genome-mode-switch" role="group" aria-label="IGV viewer mode">' + "".join(buttons) + "</div>"


def genome_browser_static_panel(payload: dict[str, Any], reason: str) -> str:
    options = payload.get("options", {}) if isinstance(payload.get("options"), dict) else {}
    tracks = options.get("tracks", []) if isinstance(options.get("tracks"), list) else []
    reference = options.get("reference", {}) if isinstance(options.get("reference"), dict) else {}
    track_cards = []
    for idx, track in enumerate(tracks, start=1):
        if not isinstance(track, dict):
            continue
        url = str(track.get("url") or track.get("URL") or track.get("source") or "")
        index_url = str(track.get("indexURL") or track.get("index_url") or "")
        track_cards.append(
            '<article class="genome-browser-fallback-track">'
            f'<strong>{escape(str(track.get("name") or f"track-{idx}"))}</strong>'
            f'<span>{escape(str(track.get("type", "track")))} / {escape(str(track.get("format", "unknown")))}</span>'
            + (f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{label("Open track", "打开轨道")}</a>' if url else "")
            + (f'<a href="{escape(index_url, quote=True)}" target="_blank" rel="noopener">{label("Open index", "打开索引")}</a>' if index_url else "")
            + "</article>"
        )
    reference_html = ""
    if reference.get("fastaURL") or reference.get("indexURL"):
        fasta = str(reference.get("fastaURL") or "")
        index = str(reference.get("indexURL") or "")
        reference_html = (
            '<div class="genome-browser-reference">'
            f'<strong>{label("Reference", "参考序列")}</strong>'
            f'<p>{escape(str(reference.get("id") or options.get("genome") or "custom"))}</p>'
            + (f'<a href="{escape(fasta, quote=True)}" target="_blank" rel="noopener">FASTA</a>' if fasta else "")
            + (f'<a href="{escape(index, quote=True)}" target="_blank" rel="noopener">FAI</a>' if index else "")
            + "</div>"
        )
    config_text = escape(json.dumps(options, ensure_ascii=False, indent=2))
    return (
        '<div class="genome-browser-fallback-panel">'
        '<div class="genome-browser-fallback-summary">'
        f'<strong>{label("IGV review configuration", "IGV 审阅配置")}</strong>'
        f"<p>{reason}</p>"
        "<dl>"
        f'<div><dt>mode</dt><dd>{escape(str(payload.get("viewerMode", "embedded")))}</dd></div>'
        f'<div><dt>data</dt><dd>{escape(str(payload.get("dataMode", "external")))}</dd></div>'
        f'<div><dt>genome</dt><dd>{escape(str(options.get("genome") or reference.get("id") or "custom"))}</dd></div>'
        f'<div><dt>locus</dt><dd>{escape(str(options.get("locus", "")))}</dd></div>'
        "</dl>"
        "</div>"
        f"{reference_html}"
        '<div class="genome-browser-fallback-tracks">'
        + ("".join(track_cards) if track_cards else f'<p>{label("No tracks declared.", "未声明轨道。")}</p>')
        + "</div>"
        f'<details class="genome-browser-config"><summary>{label("Show embedded IGV config", "查看内嵌 IGV 配置")}</summary><pre><code>{config_text}</code></pre></details>'
        "</div>"
    )


def genome_browser_resource_url(
    ctx: RenderContext,
    component_id: str,
    rel_or_url: str,
    *,
    kind: str,
    embed: bool,
) -> str:
    value = rel_or_url.strip()
    if not value:
        return value
    if is_external_resource(value):
        return value
    path = resolve_path(ctx.root, value)
    record_asset(ctx, kind, component_id, value, path)
    if embed:
        return text_data_uri(path)
    return value


def render_genome_browser(component: dict[str, Any], ctx: RenderContext) -> str:
    component_id = component["id"]
    runtime = str(component.get("runtime", "igv")).strip().lower()
    if runtime != "igv":
        raise RenderError(f"genome_browser {component_id} only supports runtime='igv'")
    viewer_modes = normalize_genome_browser_modes(component)
    requested_mode = str(component.get("viewer_mode", viewer_modes[0])).strip().lower() or viewer_modes[0]
    viewer_mode = requested_mode if requested_mode in viewer_modes else viewer_modes[0]
    if "embedded" in viewer_modes:
        ensure_runtime_pack(ctx, IGV_RUNTIME_ID, component_id)
    title = component.get("title", {"en": "Genome browser", "zh": "基因组浏览器"})
    note = component.get("note", {"en": "External genomic tracks are opened inside an embedded IGV browser.", "zh": "外部基因组轨道会在内嵌 IGV 浏览器中打开。"})
    data_mode = str(component.get("data_mode", "external")).strip().lower()
    locus = str(component.get("locus", "")).strip()
    height = int_value(component.get("height"), 520, minimum=280)
    tracks = component.get("tracks", []) or []
    if not isinstance(tracks, list):
        raise RenderError(f"genome_browser {component_id}.tracks must be a list")
    igv_tracks: list[dict[str, Any]] = []
    track_cards: list[str] = []
    for idx, track in enumerate(tracks, start=1):
        if not isinstance(track, dict):
            raise RenderError(f"genome_browser {component_id}.tracks[{idx}] must be a table")
        name = str(track.get("name") or track.get("id") or f"track-{idx}")
        url = str(track.get("url") or track.get("source") or "").strip()
        if not url:
            raise RenderError(f"genome_browser {component_id}.tracks[{idx}] requires url/source")
        embed_track = bool_value(track.get("embed"), bool_value(component.get("embed_tracks"), False))
        igv_url = genome_browser_resource_url(ctx, component_id, url, kind="genome-track", embed=embed_track)
        item: dict[str, Any] = {
            "name": name,
            "url": igv_url,
            "type": str(track.get("type", "annotation")),
            "format": str(track.get("format", "bed")),
        }
        for optional_key, igv_key in [
            ("index_url", "indexURL"),
            ("height", "height"),
            ("color", "color"),
            ("display_mode", "displayMode"),
            ("visibility_window", "visibilityWindow"),
        ]:
            if optional_key in track:
                item[igv_key] = track[optional_key]
        igv_tracks.append(item)
        href = escape(url, quote=True)
        track_cards.append(
            '<article class="genome-track-card">'
            f"<strong>{escape(name)}</strong>"
            f"<span>{escape(item['type'])} / {escape(item['format'])}</span>"
            f'<a href="{href}" target="_blank" rel="noopener">{label("Open track", "打开轨道")}</a>'
            "</article>"
        )
    options: dict[str, Any] = {"locus": locus, "tracks": igv_tracks}
    if component.get("genome"):
        options["genome"] = str(component.get("genome"))
    reference_fasta = str(component.get("reference_fasta", "") or "").strip()
    if reference_fasta:
        embed_reference = bool_value(component.get("embed_reference"), False)
        reference: dict[str, Any] = {
            "id": str(component.get("reference_name", component.get("genome", "custom-reference"))),
            "fastaURL": genome_browser_resource_url(
                ctx,
                component_id,
                reference_fasta,
                kind="genome-reference",
                embed=embed_reference,
            ),
        }
        reference_index = str(component.get("reference_index", "") or "").strip()
        if reference_index:
            reference["indexURL"] = genome_browser_resource_url(
                ctx,
                component_id,
                reference_index,
                kind="genome-reference-index",
                embed=embed_reference,
            )
        options["reference"] = reference
    payload = {
        "id": component_id,
        "runtime": runtime,
        "viewerMode": viewer_mode,
        "viewerModes": viewer_modes,
        "dataMode": data_mode,
        "height": height,
        "options": options,
    }
    runtime_version = ctx.runtime_pack_versions.get(IGV_RUNTIME_ID, "linked" if "embedded" not in viewer_modes else "external")
    tracks_html = "".join(track_cards) if track_cards else f'<p class="genome-browser-empty">{label("No tracks declared", "未声明轨道")}</p>'
    if viewer_mode == "linked":
        status_text = label("Linked review mode; no IGV runtime is required.", "链接审阅模式；不需要 IGV runtime。")
    elif runtime_version == "test-shim":
        status_text = label(
            "IGV test shim detected; this card shows the auditable configuration panel instead of a real genome browser.",
            "检测到 IGV test shim；本卡片显示可审计配置面板，而不伪装成真实基因组浏览器。",
        )
    else:
        status_text = label("IGV runtime is embedded; genomic data may remain external.", "IGV runtime 已内嵌；基因组轨道数据可以保持外部引用。")
    mode_switch = genome_browser_mode_switch(viewer_modes, viewer_mode)
    static_reason = (
        label(
            "Embedded IGV mode is selected. If browser JavaScript and the IGV runtime are available, this panel upgrades to an interactive browser; otherwise the complete review configuration remains visible.",
            "当前选择内嵌 IGV 模式。如果浏览器 JavaScript 和 IGV runtime 可用，此区域会升级为交互式浏览器；否则完整审阅配置仍保持可见。",
        )
        if viewer_mode == "embedded"
        else label(
            "Linked review mode is selected. Track URLs and the IGV configuration are preserved for reuse in an external genome browser.",
            "当前选择链接审阅模式。轨道 URL 和 IGV 配置会保存在报告中，可在外部 genome browser 中复用。",
        )
    )
    initial_panel = genome_browser_static_panel(payload, static_reason)
    return (
        f'<article class="genome-browser-card" id="{escape(component_id)}" data-genome-browser>'
        '<div class="genome-browser-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        "</div>"
        '<div class="genome-browser-head-actions">'
        f"{mode_switch}"
        f'<span class="genome-runtime-badge">IGV {escape(runtime_version)}</span>'
        "</div>"
        "</div>"
        '<div class="genome-browser-layout">'
        '<div class="genome-browser-panel">'
        f'<div class="genome-browser-stage" style="height:{height}px" data-genome-browser-stage>'
        f"{initial_panel}"
        "</div>"
        f'<p class="genome-browser-status" data-genome-browser-status>{status_text}</p>'
        "</div>"
        '<div class="genome-browser-side">'
        '<div class="genome-browser-locus">'
        f'<small>{label("Locus", "位点")}</small><strong>{escape(locus)}</strong>'
        "</div>"
        f"{tracks_html}"
        "</div>"
        "</div>"
        f'<script type="application/json" data-genome-browser-payload>{script_safe_json(payload)}</script>'
        "</article>"
    )


def number_or_none(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or text.upper() in {"NA", "NAN", "NULL", "NONE", "INF", "-INF"}:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def ratio_or_none(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        numerator = number_or_none(left)
        denominator = number_or_none(right)
        if numerator is not None and denominator not in {None, 0}:
            return numerator / denominator
    return number_or_none(text)


def first_existing_column(headers: list[str], candidates: list[str], explicit: Any = None) -> str:
    if explicit:
        value = str(explicit).strip()
        if value:
            return value
    lower_to_header = {header.lower(): header for header in headers}
    for candidate in candidates:
        if candidate in headers:
            return candidate
        if candidate.lower() in lower_to_header:
            return lower_to_header[candidate.lower()]
    return candidates[0]


def interactive_plot_payload(component: dict[str, Any], ctx: RenderContext) -> dict[str, Any]:
    rel = str(component.get("source", ""))
    path = resolve_path(ctx.root, rel)
    record_asset(ctx, "table", component["id"], rel, path)
    headers, rows = read_delimited_table(path)
    kind = str(component.get("kind", "")).strip().lower()
    max_points_default = 10_000 if kind in {"volcano", "ma"} else 500
    max_points = int_value(component.get("max_points"), max_points_default, minimum=1)
    top_n = int_value(component.get("top_n"), 20, minimum=1)
    default_padj = float_value(component.get("default_padj"), 0.05, minimum=0.0)
    default_log2fc = float_value(component.get("default_log2fc"), 1.0, minimum=0.0)
    point_size_default = 10.0 if kind == "ora_dotplot" else 7.0
    opacity_default = 0.86 if kind == "ora_dotplot" else 0.78
    default_point_size = min(24.0, float_value(component.get("point_size"), point_size_default, minimum=2.0))
    default_opacity = min(1.0, float_value(component.get("opacity"), opacity_default, minimum=0.05))
    default_label_max_chars = int_value(component.get("label_max_chars"), 46, minimum=12)
    fixed_range = bool_value(component.get("fixed_range"), True)
    show_threshold_lines = bool_value(component.get("show_threshold_lines"), True)

    fields = {
        "gene": first_existing_column(headers, ["gene_id", "gene", "id", "ID"], component.get("gene") or component.get("label")),
        "log2fc": first_existing_column(headers, ["log2FoldChange", "log2fc", "logFC"], component.get("log2fc") or component.get("x")),
        "padj": first_existing_column(headers, ["padj", "p.adjust", "qvalue", "FDR"], component.get("padj")),
        "pvalue": first_existing_column(headers, ["pvalue", "p.value", "PValue"], component.get("pvalue")),
        "base_mean": first_existing_column(headers, ["baseMean", "base_mean", "mean"], component.get("base_mean")),
        "description": first_existing_column(headers, ["Description", "description", "term", "name"], component.get("description") or component.get("label")),
        "count": first_existing_column(headers, ["Count", "count", "gene_count"], component.get("count") or component.get("size")),
        "gene_ratio": first_existing_column(headers, ["GeneRatio", "gene_ratio", "ratio"], component.get("gene_ratio") or component.get("x")),
        "sample": first_existing_column(headers, ["sample", "sample_id", "Sample", "name", "label"], component.get("sample") or component.get("label")),
        "pc1": first_existing_column(headers, ["PC1", "pc1", "PCA1", "Dim1", "x"], component.get("pc1") or component.get("x")),
        "pc2": first_existing_column(headers, ["PC2", "pc2", "PCA2", "Dim2", "y"], component.get("pc2") or component.get("y")),
        "group": first_existing_column(headers, ["group", "condition", "treatment", "factor", "class"], component.get("group") or component.get("color")),
    }
    if component.get("y"):
        fields["y"] = str(component["y"])
    if component.get("color"):
        fields["color"] = str(component["color"])
    if component.get("size"):
        fields["size"] = str(component["size"])

    payload_rows: list[dict[str, Any]] = []
    for row in rows:
        if kind in {"volcano", "ma"}:
            item = {
                "label": row.get(fields["gene"], ""),
                "log2fc": number_or_none(row.get(fields["log2fc"], "")),
                "padj": number_or_none(row.get(fields["padj"], "")),
                "pvalue": number_or_none(row.get(fields["pvalue"], "")),
                "baseMean": number_or_none(row.get(fields["base_mean"], "")),
            }
        elif kind == "pca":
            item = {
                "label": row.get(fields["sample"], ""),
                "sample": row.get(fields["sample"], ""),
                "group": row.get(fields["group"], ""),
                "x": number_or_none(row.get(fields["pc1"], "")),
                "y": number_or_none(row.get(fields["pc2"], "")),
            }
        else:
            item = {
                "label": row.get(fields["description"], ""),
                "id": row.get(first_existing_column(headers, ["ID", "id"], component.get("label")), ""),
                "count": number_or_none(row.get(fields["count"], "")),
                "geneRatio": row.get(fields["gene_ratio"], ""),
                "geneRatioValue": ratio_or_none(row.get(fields["gene_ratio"], "")),
                "padj": number_or_none(row.get(fields["padj"], "")),
                "pvalue": number_or_none(row.get(fields["pvalue"], "")),
            }
        if item:
            payload_rows.append(item)
        if len(payload_rows) >= max_points:
            break

    return {
        "id": component["id"],
        "kind": kind,
        "source": rel,
        "sourceRows": len(rows),
        "embeddedRows": len(payload_rows),
        "truncated": len(rows) > len(payload_rows),
        "fields": fields,
        "defaults": {
            "padj": default_padj,
            "log2fc": default_log2fc,
            "topN": top_n,
            "pointSize": default_point_size,
            "opacity": default_opacity,
            "colorUp": color_value(component.get("color_up"), "#d95f02"),
            "colorDown": color_value(component.get("color_down"), "#2b8cbe"),
            "colorNs": color_value(component.get("color_ns"), "#9aa8ad"),
            "colorLow": color_value(component.get("color_low"), "#f7e64b"),
            "colorHigh": color_value(component.get("color_high"), "#5b21b6"),
            "labelMaxChars": default_label_max_chars,
            "fixedRange": fixed_range,
            "showThresholdLines": show_threshold_lines,
            "xLabel": str(component.get("x_label") or component.get("pc1_label") or "PC1"),
            "yLabel": str(component.get("y_label") or component.get("pc2_label") or "PC2"),
        },
        "rows": payload_rows,
    }


def render_interactive_plot(component: dict[str, Any], ctx: RenderContext) -> str:
    component_id = component["id"]
    ensure_runtime_pack(ctx, ECHARTS_RUNTIME_ID, component_id)
    payload = interactive_plot_payload(component, ctx)
    payload_json = script_safe_json(payload)
    title = component.get("title", {"en": component_id, "zh": component_id})
    kind = str(component.get("kind", "")).strip().lower()
    default_note = {
        "en": "Interactive controls filter or restyle already-computed result rows; they do not recompute statistics.",
        "zh": "交互控件只筛选或重绘已计算结果行，不重新计算统计模型。",
    }
    note = component.get("note", default_note)
    height = int_value(component.get("height"), 460, minimum=260)
    controls_open = bool_value(component.get("controls_open"), False)
    controls_attr = " open" if controls_open else ""
    defaults = payload["defaults"]
    point_output_id = child_anchor(component_id, "point-size-output")
    opacity_output_id = child_anchor(component_id, "opacity-output")
    common_controls = (
        '<label class="interactive-plot-control interactive-plot-control-inline">'
        f'<span>{label("Point size", "点大小")} <output id="{escape(point_output_id)}">{escape(str(defaults["pointSize"]))}</output></span>'
        f'<input type="range" min="2" max="24" step="1" value="{escape(str(defaults["pointSize"]))}" data-output-target="{escape(point_output_id, quote=True)}" data-plot-point-size>'
        "</label>"
        '<label class="interactive-plot-control interactive-plot-control-inline">'
        f'<span>{label("Opacity", "透明度")} <output id="{escape(opacity_output_id)}">{escape(str(defaults["opacity"]))}</output></span>'
        f'<input type="range" min="0.05" max="1" step="0.05" value="{escape(str(defaults["opacity"]))}" data-output-target="{escape(opacity_output_id, quote=True)}" data-plot-opacity>'
        "</label>"
    )
    if kind in {"volcano", "ma"}:
        controls = (
            '<label class="interactive-plot-control">'
            f'<span>{label("Adjusted p cutoff", "校正 p 阈值")}</span>'
            f'<input type="number" min="0" max="1" step="0.001" value="{escape(str(defaults["padj"]))}" data-plot-padj>'
            "</label>"
            '<label class="interactive-plot-control">'
            f'<span>{label("Absolute log2FC cutoff", "|log2FC| 阈值")}</span>'
            f'<input type="number" min="0" step="0.1" value="{escape(str(defaults["log2fc"]))}" data-plot-log2fc>'
            "</label>"
            f"{common_controls}"
            '<div class="interactive-plot-color-row">'
            '<label class="interactive-plot-control">'
            f'<span>{label("Up color", "上调颜色")}</span>'
            f'<input type="color" value="{escape(str(defaults["colorUp"]))}" data-plot-color-up>'
            "</label>"
            '<label class="interactive-plot-control">'
            f'<span>{label("Down color", "下调颜色")}</span>'
            f'<input type="color" value="{escape(str(defaults["colorDown"]))}" data-plot-color-down>'
            "</label>"
            '<label class="interactive-plot-control">'
            f'<span>{label("NS color", "不显著颜色")}</span>'
            f'<input type="color" value="{escape(str(defaults["colorNs"]))}" data-plot-color-ns>'
            "</label>"
            "</div>"
            '<label class="interactive-plot-check">'
            f'<input type="checkbox" {"checked" if defaults["fixedRange"] else ""} data-plot-fixed-range>'
            f'<span>{label("Keep full-data axis range", "固定全数据坐标范围")}</span>'
            "</label>"
            '<label class="interactive-plot-check">'
            f'<input type="checkbox" {"checked" if defaults["showThresholdLines"] else ""} data-plot-threshold-lines>'
            f'<span>{label("Show threshold guides", "显示阈值参考线")}</span>'
            "</label>"
        )
    elif kind == "ora_dotplot":
        controls = (
            '<label class="interactive-plot-control">'
            f'<span>{label("Adjusted p cutoff", "校正 p 阈值")}</span>'
            f'<input type="number" min="0" max="1" step="0.001" value="{escape(str(defaults["padj"]))}" data-plot-padj>'
            "</label>"
            '<label class="interactive-plot-control">'
            f'<span>{label("Top terms", "Top 条目数")}</span>'
            f'<input type="number" min="3" step="1" value="{escape(str(defaults["topN"]))}" data-plot-topn>'
            "</label>"
            f"{common_controls}"
            '<div class="interactive-plot-color-row">'
            '<label class="interactive-plot-control">'
            f'<span>{label("High significance", "高显著性")}</span>'
            f'<input type="color" value="{escape(str(defaults["colorLow"]))}" data-plot-color-low>'
            "</label>"
            '<label class="interactive-plot-control">'
            f'<span>{label("Low significance", "低显著性")}</span>'
            f'<input type="color" value="{escape(str(defaults["colorHigh"]))}" data-plot-color-high>'
            "</label>"
            "</div>"
        )
    else:
        controls = (
            f"{common_controls}"
            '<label class="interactive-plot-check">'
            f'<input type="checkbox" {"checked" if defaults["fixedRange"] else ""} data-plot-fixed-range>'
            f'<span>{label("Keep full-data axis range", "固定全数据坐标范围")}</span>'
            "</label>"
        )
    source_note = {
        "en": f"{payload['source']}; embedded {payload['embeddedRows']} of {payload['sourceRows']} source rows.",
        "zh": f"{payload['source']}；已内嵌 {payload['embeddedRows']} / {payload['sourceRows']} 行源数据。",
    }
    if payload["truncated"]:
        source_note = {
            "en": f"{source_note['en']} The payload was capped for standalone report size.",
            "zh": f"{source_note['zh']} 为控制单文件报告体积，payload 已截断。",
        }
    return (
        f'<article class="interactive-plot-card" id="{escape(component_id)}" data-interactive-plot>'
        '<div class="interactive-plot-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        f"<small>{i18n(source_note)}</small>"
        "</div>"
        f'<span class="interactive-plot-badge">{label("interactive", "交互")}</span>'
        "</div>"
        f'<details class="interactive-plot-controls" data-interactive-plot-controls{controls_attr}>'
        f'<summary>{label("Display controls", "显示控制")}</summary>'
        '<div class="interactive-plot-control-grid">'
        f"{controls}"
        "</div>"
        '<div class="interactive-plot-actions">'
        f'<button type="button" class="mini-action" data-plot-reset>{label("Reset view", "重置视图")}</button>'
        "</div>"
        '<p class="interactive-plot-control-note">'
        f'{label("These controls change only the browser view of embedded rows.", "这些控件只改变内嵌结果行的浏览器视图。")}'
        "</p>"
        "</details>"
        '<div class="interactive-plot-layout">'
        f'<div class="interactive-plot-stage" style="height:{height}px;min-height:{height}px" data-interactive-plot-stage></div>'
        '<aside class="interactive-plot-side">'
        '<div class="interactive-plot-legend" data-interactive-plot-legend></div>'
        "</aside>"
        "</div>"
        '<dl class="interactive-plot-stats" data-interactive-plot-stats></dl>'
        f'<script type="application/json" data-interactive-plot-payload>{payload_json}</script>'
        "</article>"
    )


def parse_residue_values(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[\s,;]+", str(value or "").strip())
    residues: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text or text in {"-", "NA", "na", "None", "none"}:
            continue
        if not re.match(r"^[A-Za-z0-9_.:-]+$", text):
            continue
        if text not in seen:
            seen.add(text)
            residues.append(text)
    return residues


def structure_site_group_styles(component: dict[str, Any]) -> dict[str, dict[str, Any]]:
    styles = {key: dict(value) for key, value in DEFAULT_SITE_GROUP_STYLES.items()}
    for group in component.get("site_groups", []) or []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or group.get("group") or group.get("name") or "").strip()
        if not group_id:
            continue
        style = dict(styles.get(group_id, {}))
        for field in ("color", "label", "representation", "atom", "radius_scale", "opacity"):
            if field in group:
                style[field] = group[field]
        styles[group_id] = style
    return styles


def site_group_payload(
    group_id: str,
    residues: list[str],
    *,
    model_id: str,
    chain: str,
    styles: dict[str, dict[str, Any]],
    labels: list[str] | None = None,
    selection: str | None = None,
    fallback_label: Any = None,
) -> dict[str, Any] | None:
    if not residues and not selection:
        return None
    style = styles.get(group_id, DEFAULT_SITE_GROUP_STYLES.get("sites", {}))
    label_value = style.get("label") or fallback_label or group_id
    payload: dict[str, Any] = {
        "id": slug(group_id),
        "sourceGroup": group_id,
        "model": model_id,
        "label": text_value(label_value, group_id),
        "color": str(style.get("color", DEFAULT_SITE_GROUP_STYLES["sites"]["color"])),
        "residues": residues,
        "representation": str(style.get("representation", "spacefill")),
        "atom": str(style.get("atom", "CA")),
        "radiusScale": float_value(style.get("radius_scale"), 1.65, minimum=0.1),
        "opacity": float_value(style.get("opacity"), 0.96, minimum=0.05),
    }
    if chain:
        payload["chain"] = chain
    if labels:
        payload["residueLabels"] = labels
    if selection:
        payload["selection"] = selection
    return payload


def structure_site_groups(component: dict[str, Any], ctx: RenderContext, default_model_id: str) -> list[dict[str, Any]]:
    styles = structure_site_group_styles(component)
    default_model = slug(str(component.get("site_model") or default_model_id))
    default_chain = str(component.get("site_chain", "") or "").strip()
    groups: list[dict[str, Any]] = []

    for explicit in component.get("site_groups", []) or []:
        if not isinstance(explicit, dict):
            continue
        residues = parse_residue_values(explicit.get("residues") or explicit.get("residue") or "")
        selection = str(explicit.get("selection") or "").strip() or None
        if not residues and not selection:
            continue
        group_id = str(explicit.get("id") or explicit.get("group") or explicit.get("name") or "sites").strip()
        item = site_group_payload(
            group_id,
            residues,
            model_id=slug(str(explicit.get("model") or default_model)),
            chain=str(explicit.get("chain") or default_chain or "").strip(),
            styles=styles,
            labels=[str(value) for value in explicit.get("labels", [])] if isinstance(explicit.get("labels"), list) else None,
            selection=selection,
            fallback_label=explicit.get("label"),
        )
        if item is not None:
            groups.append(item)

    table_rel = str(component.get("site_table", "") or "").strip()
    if not table_rel:
        return groups
    table_path = resolve_path(ctx.root, table_rel)
    record_asset(ctx, "table", f"{component['id']}-site-table", table_rel, table_path)
    headers, rows = read_tsv(table_path)
    if not headers:
        return groups
    structure_filter = str(component.get("site_structure_id", "") or "").strip()
    structure_col = str(component.get("site_structure_column", "structure_id"))
    residue_col = str(component.get("site_residue_column", "structure_residue"))
    group_col = str(component.get("site_group_column", "target_state"))
    label_col = str(component.get("site_label_column", "target_residue_label"))
    chain_col = str(component.get("site_chain_column", "chain"))
    max_sites = int_value(component.get("site_max_sites"), 80, minimum=1)
    grouped: dict[str, dict[str, Any]] = {}
    added = 0
    for row in rows:
        if structure_filter and row.get(structure_col, "") != structure_filter:
            continue
        residues = parse_residue_values(row.get(residue_col, ""))
        if not residues:
            continue
        group_id = row.get(group_col, "") or "sites"
        bucket = grouped.setdefault(group_id, {"residues": [], "labels": [], "seen": set(), "chain": default_chain})
        if not bucket["chain"] and row.get(chain_col):
            bucket["chain"] = row[chain_col].strip()
        for residue in residues:
            if added >= max_sites:
                break
            if residue in bucket["seen"]:
                continue
            bucket["seen"].add(residue)
            bucket["residues"].append(residue)
            bucket["labels"].append(row.get(label_col, "") or residue)
            added += 1
        if added >= max_sites:
            break
    for group_id, bucket in grouped.items():
        item = site_group_payload(
            group_id,
            bucket["residues"],
            model_id=default_model,
            chain=bucket["chain"],
            styles=styles,
            labels=bucket["labels"],
        )
        if item is not None:
            groups.append(item)
    return groups


def render_structure_controls(
    model_payloads: list[dict[str, Any]], site_groups: list[dict[str, Any]], runtime: str, controls_open: bool
) -> str:
    if runtime != "ngl":
        return ""
    model_items = []
    for model in model_payloads:
        model_items.append(
            '<label class="structure-control-item structure-model-control">'
            f'<input type="checkbox" checked data-structure-model-toggle value="{escape(str(model["id"]), quote=True)}">'
            f'<span class="structure-control-swatch" style="--control-color:{escape(str(model.get("color", "#087f74")), quote=True)}"></span>'
            f'<span>{escape(str(model.get("label") or model["id"]))}</span>'
            "</label>"
        )
    site_items = []
    for group in site_groups:
        count = len(group.get("residues", []) or [])
        suffix = f" ({count})" if count else ""
        site_items.append(
            '<label class="structure-control-item structure-site-control">'
            f'<input type="checkbox" checked data-structure-site-toggle value="{escape(str(group["id"]), quote=True)}">'
            f'<span class="structure-control-swatch" style="--control-color:{escape(str(group.get("color", "#d18b00")), quote=True)}"></span>'
            f'<span>{escape(str(group.get("label") or group["id"]))}{escape(suffix)}</span>'
            "</label>"
        )
    site_group_markup = ""
    site_tuning_markup = ""
    if site_items:
        site_group_markup = (
            '<div class="structure-control-group">'
            f'<strong>{label("Site groups", "位点分组")}</strong>'
            '<div class="structure-control-list">'
            + "".join(site_items)
            + "</div>"
            "</div>"
        )
        site_tuning_markup = (
            '<div class="structure-control-group structure-range-controls">'
            f'<strong>{label("Site display", "位点显示")}</strong>'
            '<label class="structure-range-control">'
            f'<span>{label("Ball size", "球大小")}</span>'
            '<input type="range" min="0.4" max="3" step="0.05" value="1.65" data-structure-site-radius>'
            '<output data-structure-site-radius-output>1.65</output>'
            "</label>"
            '<label class="structure-range-control">'
            f'<span>{label("Opacity", "透明度")}</span>'
            '<input type="range" min="0.1" max="1" step="0.05" value="0.96" data-structure-site-opacity>'
            '<output data-structure-site-opacity-output>0.96</output>'
            "</label>"
            "</div>"
        )
    open_attr = " open" if controls_open else ""
    return (
        f'<details class="structure-controls" data-structure-controls{open_attr}>'
        f'<summary>{label("Interactive display controls", "交互显示控制")}</summary>'
        '<div class="structure-controls-grid">'
        '<div class="structure-control-group">'
        f'<strong>{label("Models", "模型")}</strong>'
        '<div class="structure-control-list">'
        + "".join(model_items)
        + "</div>"
        "</div>"
        f"{site_group_markup}"
        f"{site_tuning_markup}"
        "</div>"
        '<p class="structure-control-note">'
        f'{label("Controls only change the current browser view; embedded PDB, colors, and site groups remain unchanged.", "控件只改变当前浏览器视图；内嵌 PDB、颜色和位点分组数据不会被改写。")}'
        "</p>"
        "</details>"
    )


def render_structure_viewer(component: dict[str, Any], ctx: RenderContext) -> str:
    component_id = component["id"]
    title = component.get("title", {"en": component_id, "zh": component_id})
    note = component.get(
        "note",
        {
            "en": "PDB structure evidence embedded for local review.",
            "zh": "用于本地审阅的 PDB 结构证据。",
        },
    )
    runtime = str(component.get("runtime", "builtin")).strip().lower()
    atom_filter = str(component.get("atom_filter", "ca")).strip().lower()
    max_atoms = int_value(component.get("max_atoms"), 2500, minimum=1)
    height = int_value(component.get("height"), 420, minimum=240)
    representation = str(component.get("representation", "cartoon")).strip().lower()
    background = str(component.get("background", "white")).strip() or "white"
    show_surface = bool_value(component.get("show_surface"), False)
    spin = bool_value(component.get("spin"), False)
    controls_open = bool_value(component.get("controls_open"), False)
    ngl_runtime_is_test_shim = False
    if runtime == "ngl":
        ensure_runtime_pack(ctx, "ngl", component_id)
        ngl_version = ctx.runtime_pack_versions.get("ngl", NGL_RUNTIME_VERSION)
        ngl_runtime_is_test_shim = ngl_version == "test-shim"
        runtime_note = {
            "en": f"NGL WebGL runtime pack ngl@{ngl_version}; the runtime is embedded only because this component requested runtime='ngl'.",
            "zh": f"NGL WebGL runtime pack ngl@{ngl_version}；仅当本组件请求 runtime='ngl' 时才内嵌此 runtime。",
        }
    else:
        runtime_note = {
            "en": "Built-in lightweight PDB trace viewer; no external 3D runtime is embedded unless this component is used.",
            "zh": "内置轻量 PDB trace 查看器；除非使用此组件，否则不会嵌入额外 3D runtime。",
        }
    model_payloads: list[dict[str, Any]] = []
    model_cards: list[str] = []
    for idx, model in enumerate(normalize_structure_models(component), start=1):
        rel = str(model.get("pdb", ""))
        path = resolve_path(ctx.root, rel)
        record_asset(ctx, "pdb", component_id, rel, path)
        pdb_text = path.read_text(encoding="utf-8", errors="replace")
        atoms, summary = parse_pdb_atoms(pdb_text, atom_filter=atom_filter, max_atoms=max_atoms)
        model_id = slug(str(model.get("id") or f"model-{idx}"))
        label_value = model.get("label") or model.get("title") or model_id
        model_label = i18n(label_value) if isinstance(label_value, dict) else escape(str(label_value))
        color = str(model.get("color", "#087f74"))
        source_href = report_relative_href(ctx, path, rel)
        payload_item = {
            "id": model_id,
            "label": text_value(label_value, model_id),
            "color": color,
            "source": rel,
            "summary": summary,
            "atoms": atoms,
        }
        if runtime == "ngl":
            payload_item["pdbText"] = pdb_text
            payload_item["representation"] = str(model.get("representation", representation)).strip().lower() or representation
        model_payloads.append(payload_item)
        model_cards.append(
            '<article class="structure-model-card">'
            f'<span class="structure-model-color" style="--model-color:{escape(color, quote=True)}"></span>'
            "<div>"
            f"<strong>{model_label}</strong>"
            f"<small>{escape(rel)}</small>"
            '<dl class="structure-model-stats">'
            f"<div><dt>{field_label('atoms')}</dt><dd>{summary['atom_rows']}</dd></div>"
            f"<div><dt>{field_label('residues')}</dt><dd>{summary['residues']}</dd></div>"
            f"<div><dt>{field_label('chains')}</dt><dd>{summary['chains']}</dd></div>"
            f"<div><dt>{field_label('viewer_atoms')}</dt><dd>{summary['viewer_atoms']}</dd></div>"
            "</dl>"
            f'<a href="{escape(source_href)}" target="_blank" rel="noopener">{label("Open PDB", "打开 PDB")}</a>'
            "</div>"
            "</article>"
        )
    static_html = ""
    static_rel = str(component.get("static_image", "") or "")
    if static_rel:
        static_path = resolve_path(ctx.root, static_rel)
        record_asset(ctx, "image", component_id, static_rel, static_path)
        static_src = data_uri(static_path)
        static_id = child_anchor(component_id, "static")
        static_title = {"en": "Static structure figure", "zh": "静态结构图"}
        static_raw_href = report_relative_href(ctx, static_path, static_rel)
        static_html = (
            f'<figure class="structure-static-figure" id="{escape(static_id)}" data-image-fit="contain">'
            f'<button type="button" class="structure-static-image-button" data-open-image="{escape(static_id)}" '
            f'aria-label="{escape(text_value(static_title, "Static structure figure"), quote=True)}">'
            f'<img src="{escape(static_src)}" alt="{escape(text_value(title, component_id))}">'
            "</button>"
            "<figcaption>"
            f"<strong>{i18n(static_title)}</strong>"
            '<span class="plot-links">'
            f'<button type="button" class="plot-zoom-link" data-open-image="{escape(static_id)}">{label("View large", "查看大图")}</button>'
            f'<a href="{escape(static_raw_href)}" target="_blank" rel="noopener">{label("Raw", "原始文件")}</a>'
            "</span>"
            "</figcaption>"
            "</figure>"
        )
    site_groups = structure_site_groups(component, ctx, model_payloads[0]["id"] if model_payloads else "model-1")
    payload = {
        "id": component_id,
        "runtime": runtime,
        "height": height,
        "representation": representation,
        "background": background,
        "showSurface": show_surface,
        "spin": spin,
        "models": model_payloads,
    }
    if ngl_runtime_is_test_shim:
        payload["runtimeShim"] = True
    if site_groups:
        payload["siteGroups"] = site_groups
    payload_json = script_safe_json(payload)
    controls_html = render_structure_controls(model_payloads, site_groups, runtime, controls_open)
    if runtime == "ngl":
        stage_class = "structure-ngl-stage"
        if ngl_runtime_is_test_shim:
            stage_class += " is-runtime-fallback"
        viewer_markup = (
            f'<div class="{stage_class}" style="height:{height}px" data-structure-ngl-stage '
            f'aria-label="{escape(text_value(title, component_id), quote=True)}"></div>'
        )
        if ngl_runtime_is_test_shim:
            representation_control = (
                '<label class="structure-select-label">'
                f'<span>{label("Fallback style", "Fallback 样式")}</span>'
                '<select data-structure-representation disabled aria-label="Built-in fallback only supports trace view">'
                '<option value="trace" selected>fallback trace</option>'
                "</select>"
                "</label>"
            )
            status_initial = label(
                "NGL test shim detected; switching to the built-in fallback trace viewer.",
                "检测到 NGL test shim；将切换到内置 fallback trace 查看器。",
            )
        else:
            representation_control = (
                '<label class="structure-select-label">'
                f'<span>{label("Style", "样式")}</span>'
                '<select data-structure-representation>'
                f'<option value="cartoon"{" selected" if representation == "cartoon" else ""}>cartoon</option>'
                f'<option value="backbone"{" selected" if representation == "backbone" else ""}>backbone</option>'
                f'<option value="licorice"{" selected" if representation == "licorice" else ""}>licorice</option>'
                f'<option value="ball+stick"{" selected" if representation == "ball+stick" else ""}>ball+stick</option>'
                f'<option value="spacefill"{" selected" if representation == "spacefill" else ""}>spacefill</option>'
                f'<option value="surface"{" selected" if representation == "surface" else ""}>surface</option>'
                "</select>"
                "</label>"
            )
            status_initial = label("Loading NGL", "正在加载 NGL")
        toolbar_markup = (
            '<div class="structure-toolbar">'
            f'<button type="button" data-structure-reset>{label("Reset view", "重置视图")}</button>'
            f'<button type="button" data-structure-spin>{label("Spin", "旋转")}</button>'
            f"{representation_control}"
            f'<span data-structure-status>{status_initial}</span>'
            "</div>"
        )
    else:
        viewer_markup = (
            f'<canvas class="structure-canvas" height="{height}" style="height:{height}px" '
            f'data-structure-canvas aria-label="{escape(text_value(title, component_id), quote=True)}"></canvas>'
        )
        toolbar_markup = (
            '<div class="structure-toolbar">'
            f'<button type="button" data-structure-reset>{label("Reset", "重置")}</button>'
            f'<button type="button" data-structure-zoom-in>{label("Zoom in", "放大")}</button>'
            f'<button type="button" data-structure-zoom-out>{label("Zoom out", "缩小")}</button>'
            f'<span data-structure-status>{label("Drag to rotate", "拖拽旋转")}</span>'
            "</div>"
        )
    return (
        f'<article class="structure-card{" is-structure-fallback" if ngl_runtime_is_test_shim else ""}" id="{escape(component_id)}" data-structure-viewer>'
        '<div class="structure-head">'
        "<div>"
        f"<strong>{i18n(title)}</strong>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        "</div>"
        f'<span class="structure-runtime-badge">{escape(runtime)}</span>'
        "</div>"
        '<div class="structure-model-grid">'
        + "".join(model_cards)
        + "</div>"
        '<div class="structure-layout">'
        '<div class="structure-viewer-panel">'
        f"{viewer_markup}"
        f"{toolbar_markup}"
        f"{controls_html}"
        f'<p class="structure-runtime-note">{i18n(runtime_note)}</p>'
        "</div>"
        f"{static_html}"
        "</div>"
        f'<script type="application/json" data-structure-payload>{payload_json}</script>'
        "</article>"
    )


def render_native_subreport(component: dict[str, Any], ctx: RenderContext) -> str:
    rel = component.get("path", "")
    path = resolve_path(ctx.root, rel)
    data = path.read_bytes()
    sha = sha256_bytes(data)
    component_id = component["id"]
    kind = component.get("kind", "html")
    embed_policy = str(component.get("embed_policy", "auto")).strip().lower()
    if embed_policy not in {"auto", "always", "never"}:
        raise RenderError(f"unsupported embed_policy for {component_id}: {embed_policy}")
    html_text = ""
    unresolved: list[str] = []
    embedded_bytes = 0
    status = "linked"
    message = ""
    page_paths: list[Path] = []
    page_id_map: dict[str, str] = {}
    if embed_policy != "never":
        page_paths = component_extra_pages(component, ctx, path)
        page_id_map[str(path.resolve())] = component_id
        for page_path in page_paths:
            try:
                rel_page = str(page_path.resolve().relative_to(ctx.root.resolve()))
            except ValueError:
                rel_page = page_path.name
            page_id_map[str(page_path.resolve())] = component_id + "--" + slug(rel_page)
        html_text, unresolved = inline_subreport_html(path, page_id_map)
        embedded_bytes = len(html_text.encode("utf-8"))
        status = "embedded" if not unresolved else "warn"
        if page_paths:
            message = f"embedded linked HTML pages: {len(page_paths)}"
        if unresolved:
            unresolved_message = "unresolved local resources: " + ", ".join(unresolved[:12])
            message = f"{message}; {unresolved_message}" if message else unresolved_message
        if unresolved and embed_policy == "always":
            raise RenderError(f"native_subreport {component_id} required full embedding but unresolved resources remain: {', '.join(unresolved[:12])}")
        ctx.embedded_payloads.append({"id": component_id, "html": html_text})
        for page_path in page_paths:
            rel_page = str(page_path.resolve().relative_to(ctx.root.resolve()))
            page_data = page_path.read_bytes()
            page_unresolved: list[str]
            page_html, page_unresolved = inline_subreport_html(page_path, page_id_map)
            if page_unresolved and embed_policy == "always":
                raise RenderError(f"native_subreport {component_id} extra page has unresolved resources: {rel_page}: {', '.join(page_unresolved[:12])}")
            page_id = page_id_map[str(page_path.resolve())]
            page_message = "" if not page_unresolved else "unresolved local resources: " + ", ".join(page_unresolved[:12])
            page_status = "embedded" if not page_unresolved else "warn"
            ctx.assets.append(AssetRecord("html", page_id, rel_page, len(page_data), sha256_bytes(page_data)))
            ctx.subreports.append(
                SubreportRecord(page_id, f"{kind}:page", rel_page, page_status, len(page_data), len(page_html.encode("utf-8")), sha256_bytes(page_data), page_message)
            )
            ctx.embedded_payloads.append({"id": page_id, "html": page_html})
    else:
        message = "embed_policy=never; original local report path is recorded but not bundled"
    ctx.assets.append(AssetRecord("html", component_id, rel, len(data), sha))
    ctx.subreports.append(
        SubreportRecord(component_id, kind, rel, status, len(data), embedded_bytes, sha, message)
    )
    title = component.get("title", {"en": component_id, "zh": component_id})
    note = component.get("note", {"en": rel, "zh": rel})
    if message and status == "linked":
        message_text = {"en": "This subreport is linked, not embedded. Keep the original result tree beside the report.", "zh": "这个子报告仅记录为外部链接，未内嵌。请保留原始结果目录。"}
    elif message:
        message_text = {"en": message, "zh": message}
    else:
        message_text = {"en": "Local resources were bundled into the standalone report payload.", "zh": "本地资源已打包进单文件报告 payload。"}
    message_html = f'<p class="subreport-resource">{i18n(message_text)}</p>'
    source_href = report_relative_href(ctx, path, rel)
    action_links: list[str] = []
    if status != "linked":
        embedded_attrs = f'data-open-subreport="{escape(component_id)}" href="#taffish-subreport={escape(component_id)}" target="_blank" rel="noopener"'
        action_links.append(
            f'<a class="subreport-open-link" {embedded_attrs}>{i18n({"en": "Open embedded report", "zh": "打开内嵌报告"})}</a>'
        )
        action_links.append(
            f'<a class="subreport-source-link" href="{escape(source_href)}" target="_blank" rel="noopener">{i18n({"en": "Open source HTML", "zh": "打开源 HTML"})}</a>'
        )
    else:
        action_links.append(
            f'<a class="subreport-source-link primary" href="{escape(source_href)}" target="_blank" rel="noopener">{i18n({"en": "Open linked report", "zh": "打开外部报告"})}</a>'
        )
    actions_html = '<div class="subreport-actions">' + "".join(action_links) + "</div>"
    return (
        f'<article class="subreport-card" id="{escape(component_id)}">'
        '<div class="subreport-card-head">'
        f'<span class="status-dot status-{"ok" if status == "embedded" else "warn"}"></span>'
        f"<strong>{i18n(title)}</strong>"
        "</div>"
        f'{render_note_block(component, fallback=note, classes="component-note-block")}'
        "<dl>"
        f"<div><dt>{field_label('kind')}</dt><dd>{escape(str(kind))}</dd></div>"
        f"<div><dt>{field_label('source')}</dt><dd>{escape(rel)}</dd></div>"
        f"<div><dt>{field_label('bytes')}</dt><dd>{len(data)}</dd></div>"
        f"<div><dt>{field_label('status')}</dt><dd>{status_label(status)}</dd></div>"
        "</dl>"
        f"{message_html}"
        f"{actions_html}"
        "</article>"
    )


def render_component(component: dict[str, Any], ctx: RenderContext) -> str:
    ctype = component.get("type")
    if ctype == "dashboard_cards":
        return render_dashboard(component, ctx)
    if ctype == "status_grid":
        return render_status_grid(component, ctx)
    if ctype == "quality_gate_table":
        return render_quality_gate_table(component, ctx)
    if ctype == "table_preview":
        return render_table_preview(component, ctx)
    if ctype == "code_file":
        return render_code_file(component, ctx)
    if ctype == "workflow_diagram":
        return render_workflow(component, ctx)
    if ctype == "plot_card":
        return render_plot_card(component, ctx)
    if ctype == "interactive_plot":
        return render_interactive_plot(component, ctx)
    if ctype == "structure_viewer":
        return render_structure_viewer(component, ctx)
    if ctype == "tree_viewer":
        return render_tree_viewer(component, ctx)
    if ctype == "sequence_alignment":
        return render_sequence_alignment(component, ctx)
    if ctype == "genome_browser":
        return render_genome_browser(component, ctx)
    if ctype == "native_subreport":
        return render_native_subreport(component, ctx)
    raise RenderError(f"unsupported component type: {ctype}")


def section_note(section: dict[str, Any]) -> dict[str, str]:
    explicit = section.get("note") or section.get("description")
    if isinstance(explicit, dict):
        return {
            "en": str(explicit.get("en", explicit.get("zh", ""))),
            "zh": str(explicit.get("zh", explicit.get("en", ""))),
        }
    kind = str(section.get("kind", "section"))
    return SECTION_NOTES.get(
        kind,
        {
            "en": "This section collects the result files and explanations declared by the report specification.",
            "zh": "本章节展示报告配置声明的结果文件、图表和说明内容。",
        },
    )


def render_section_shell(section: dict[str, Any], body: str, note: dict[str, str] | None = None) -> str:
    sid = section["id"]
    note_html = render_note_block(section, fallback=note, classes="section-note-block")
    return (
        f'<section class="section" id="{escape(sid)}">'
        '<div class="section-head">'
        f'<p class="kicker">{escape(str(section.get("kind", "section")).replace("_", " ").upper())}</p>'
        f"<h2>{i18n(section, 'title')}</h2>"
        f"{note_html}"
        "</div>"
        f"{body}"
        "</section>"
    )


def render_report_guide(manifest: dict[str, Any]) -> str:
    project = manifest["project"]
    mode = str(project.get("analysis_mode") or "report")
    section = {
        "id": "report-guide",
        "kind": "reading_guide",
        "title": {"en": "How to Read This Report", "zh": "如何阅读本报告"},
    }
    body = f"""
      <div class="executive-grid reading-guide-grid">
        <div class="reading-guide-primary">
          <article class="executive-card">
          <p class="eyebrow">REVIEW FIRST</p>
          <h3>{i18n({"en": "A standalone TAFFISH flow report for structured review", "zh": "用于结构化审阅的 TAFFISH 单文件流程报告"})}</h3>
          <p>{i18n({"en": "This report is designed to be opened as one HTML file. Primary figures, summary tables, the TAFFISH logo, template CSS/JS, and supported native HTML subreports are embedded for offline reading.", "zh": "本报告设计为一个 HTML 文件即可打开阅读。主要图片、摘要表、TAFFISH logo、模板 CSS/JS 以及支持的原生 HTML 子报告都会内嵌，便于离线交付。"})}</p>
          <ul>
            <li>{i18n({"en": "Start with the overview and quality/status cards before interpreting detailed plots.", "zh": "先阅读项目总览和质量/状态卡，再解读详细图表。"})}</li>
            <li>{i18n({"en": "Use native subreport buttons to open bundled upstream QC pages in their own local tab.", "zh": "使用原生报告按钮，在独立本地标签页中打开已打包的上游 QC 页面。"})}</li>
            <li>{i18n({"en": "Use the deliverables section to find machine-readable files and renderer configuration.", "zh": "使用交付文件章节查找机器可读文件和渲染配置。"})}</li>
          </ul>
          </article>
          <div class="insight-grid reading-guide-steps">
            <article class="insight-card"><strong>{i18n({"en": "1. Check status", "zh": "1. 先看状态"})}</strong><p>{i18n({"en": "Warnings and skipped modules define what should be interpreted cautiously.", "zh": "警告和跳过模块决定哪些结果需要谨慎解读。"})}</p></article>
            <article class="insight-card"><strong>{i18n({"en": "2. Read figures by module", "zh": "2. 按模块看图"})}</strong><p>{i18n({"en": "Plots are grouped by biological or technical role instead of being dumped as a gallery.", "zh": "图表按生物学或技术意义分组，而不是简单堆成图库。"})}</p></article>
            <article class="insight-card"><strong>{i18n({"en": "3. Open native reports", "zh": "3. 打开原生报告"})}</strong><p>{i18n({"en": "Bundled upstream HTML pages preserve detailed interactive QC when the source report supports it.", "zh": "已打包的上游 HTML 页面会尽量保留原本的详细交互式 QC 信息。"})}</p></article>
            <article class="insight-card"><strong>{i18n({"en": "4. Reuse data files", "zh": "4. 复用数据文件"})}</strong><p>{i18n({"en": "Machine-readable TSV/JSON indexes remain available for audit, downstream analysis, and report debugging.", "zh": "机器可读 TSV/JSON 索引可用于审计、下游分析和报告调试。"})}</p></article>
          </div>
        </div>
        <aside class="module-status-panel reading-guide-contract">
          <p class="eyebrow">REPORT CONTRACT</p>
          <h3>{escape(mode)}</h3>
          <div class="status-grid">
            <article class="status-card status-ok"><span class="status-dot"></span><div><strong>{i18n({"en": "Standalone HTML", "zh": "单文件 HTML"})}</strong><small>OK</small><p>{i18n({"en": "Primary report assets are embedded into the main report.", "zh": "主要报告资源已内嵌到主报告中。"})}</p></div></article>
            <article class="status-card status-ok"><span class="status-dot"></span><div><strong>{i18n({"en": "Auditable outputs", "zh": "可审计输出"})}</strong><small>OK</small><p>{i18n({"en": "Manifest, file index, embedded HTML index, and config copies are kept beside the report.", "zh": "manifest、文件索引、HTML 内嵌索引和配置副本会随报告一起保留。"})}</p></div></article>
            <article class="status-card status-warn"><span class="status-dot"></span><div><strong>{i18n({"en": "Review boundary", "zh": "审阅边界"})}</strong><small>WARN</small><p>{i18n({"en": "The renderer presents collected results; scientific interpretation still depends on the upstream flow and input data quality.", "zh": "渲染器负责呈现已收集结果；科学解释仍取决于上游流程和输入数据质量。"})}</p></div></article>
          </div>
        </aside>
      </div>
    """
    return render_section_shell(
        section,
        body,
        {
            "en": "This guide explains the report contract before domain-specific results. It is generated by the shared renderer, so all TAFFISH reports start from the same reading model.",
            "zh": "本指南在领域结果之前说明报告契约。它由共享渲染器生成，因此所有 TAFFISH 报告都从同一套阅读模型开始。",
        },
    )


def render_deliverables(spec_suffix: str) -> str:
    section = {
        "id": "deliverables",
        "kind": "deliverables",
        "title": {"en": "Deliverables and Configuration", "zh": "交付文件与配置"},
    }
    spec_name = f"report.spec{spec_suffix if spec_suffix in {'.toml', '.json'} else '.input'}"
    categories = [
        (
            {"en": "Main report", "zh": "主报告"},
            "taffish_report.html",
            {"en": "Standalone HTML intended for reading and sharing.", "zh": "用于阅读和交付的单文件 HTML 报告。"},
        ),
        (
            {"en": "Renderer configuration", "zh": "渲染配置"},
            f"{spec_name}; report.normalized.json",
            {"en": "The original input spec and normalized canonical manifest used for rendering.", "zh": "用于渲染的原始输入配置和规范化后的 canonical manifest。"},
        ),
        (
            {"en": "Report indexes", "zh": "报告索引"},
            "report_files.tsv; embedded_html_reports.tsv",
            {"en": "Machine-readable indexes for embedded assets and native HTML subreport bundling status.", "zh": "记录内嵌资产和原生 HTML 子报告打包状态的机器可读索引。"},
        ),
        (
            {"en": "Template metadata", "zh": "模板元数据"},
            "report.manifest.json; report_template_version.txt",
            {"en": "Report metadata, template version, and provenance for audit.", "zh": "用于审计的报告元数据、模板版本和溯源信息。"},
        ),
    ]
    body = '<div class="file-category-grid">' + "".join(
        '<article class="file-category">'
        f"<strong>{i18n(title)}</strong>"
        f"<span>{escape(files)}</span>"
        f"<p>{i18n(note)}</p>"
        "</article>"
        for title, files, note in categories
    ) + "</div>"
    body += (
        '<div class="callout">'
        f"<strong>{i18n({'en': 'Why keep the config?', 'zh': '为什么保留配置？'})}</strong>"
        f"<p>{i18n({'en': 'A rendered HTML report is for reading; the copied spec and normalized JSON are for reproducing, reviewing, and debugging the exact report generation step.', 'zh': '渲染后的 HTML 用于阅读；复制出来的 spec 和规范化 JSON 用于复现、审阅和调试这一次具体的报告生成过程。'})}</p>"
        "</div>"
    )
    return render_section_shell(
        section,
        body,
        {
            "en": "The renderer keeps human-readable and machine-readable files next to the HTML report so the report can be audited without re-running the upstream analysis.",
            "zh": "渲染器会把人类可读和机器可读文件保存在 HTML 报告旁边，因此无需重跑上游分析也能审计报告生成过程。",
        },
    )


def render_interaction_shells() -> str:
    return f"""
      <div class="report-modal" data-image-modal hidden aria-hidden="true">
        <div class="report-modal-backdrop" data-modal-close></div>
        <section class="report-modal-panel image-modal-panel" role="dialog" aria-modal="true" aria-labelledby="image-modal-title">
          <div class="modal-toolbar">
            <h2 id="image-modal-title"></h2>
            <div class="modal-actions">
              <button type="button" class="modal-tool-button" data-image-fit-reset>{label("Fit", "适配窗口")}</button>
              <button type="button" class="modal-tool-button modal-icon-button" data-image-zoom-out aria-label="Zoom out">{label("−", "−")}</button>
              <span class="image-zoom-status" data-image-zoom-status>Fit</span>
              <button type="button" class="modal-tool-button modal-icon-button" data-image-zoom-in aria-label="Zoom in">{label("+", "+")}</button>
              <button type="button" class="modal-close" data-modal-close aria-label="Close">{label("Close", "关闭")}</button>
            </div>
          </div>
          <div class="image-modal-canvas">
            <img data-image-modal-img alt="">
          </div>
        </section>
      </div>
    """


def render_section_components(section: dict[str, Any], ctx: RenderContext) -> str:
    chunks: list[str] = []
    group_kind: str | None = None
    group_items: list[str] = []

    def flush_group() -> None:
        nonlocal group_kind, group_items
        if not group_items:
            return
        if group_kind in {"plot_card", "plot_card_wide", "plot_card_media"}:
            if group_kind == "plot_card_wide":
                grid_class = "plot-grid plot-grid-wide"
            elif group_kind == "plot_card_media":
                grid_class = "plot-media-stack"
            else:
                grid_class = "plot-grid"
            chunks.append(f'<div class="{grid_class}">' + "\n".join(group_items) + "</div>")
        elif group_kind == "native_subreport":
            chunks.append('<div class="subreport-open-grid" data-subreport-browser>' + "\n".join(group_items) + "</div>")
        else:
            chunks.extend(group_items)
        group_kind = None
        group_items = []

    for component in section.get("components", []):
        ctype = component.get("type")
        rendered = render_component(component, ctx)
        if ctype in {"plot_card", "native_subreport"}:
            component_layout = str(component.get("layout", "grid")).strip().lower()
            if ctype == "plot_card" and component_layout == "wide":
                desired_group = "plot_card_wide"
            elif ctype == "plot_card" and component_layout == "media":
                desired_group = "plot_card_media"
            else:
                desired_group = ctype
            if group_kind != desired_group:
                flush_group()
                group_kind = desired_group
            group_items.append(rendered)
        else:
            flush_group()
            chunks.append(rendered)
    flush_group()
    return "\n".join(chunks)


def render_section_nav(section: dict[str, Any]) -> str:
    sid = section["id"]
    components = section.get("components", [])
    title = i18n(section, "title")
    if not components:
        return f'<a href="#{escape(sid)}">{title}</a>'
    children = [
        f'<a class="nav-child nav-overview" href="#{escape(sid)}">{label("Overview", "章节总览")}</a>'
    ]
    for component in components:
        cid = escape(str(component["id"]))
        children.append(f'<a class="nav-child" href="#{cid}">{component_nav_title(component)}</a>')
    return (
        '<details class="nav-group">'
        f"<summary>{title}</summary>"
        '<div class="nav-sub">'
        + "".join(children)
        + "</div>"
        "</details>"
    )


def render_report(spec: dict[str, Any], root: Path, spec_path: Path | None = None, out_path: Path | None = None) -> tuple[str, RenderContext, dict[str, Any]]:
    validate_spec(spec)
    manifest = normalize_spec(spec, root=root)
    validate_spec(manifest, allow_collections=False)
    ctx = RenderContext(root=root, report_dir=out_path.parent if out_path is not None else None)
    languages = manifest["languages"]
    language_default = manifest["language_default"]
    set_active_languages(languages, language_default)
    css = load_asset_text("report.css") + "\n" + language_visibility_css(languages)
    js = load_asset_text("report.js") + "\n" + load_asset_text("toc.js")
    logo = f'<img src="{escape(data_uri_from_bytes(load_asset_bytes("taffish-logo.png"), "image/png"))}" alt="TAFFISH logo">'
    project = manifest["project"]
    sections_html = []
    nav = []
    guide_html = render_report_guide(manifest)
    nav.append(f'<a href="#report-guide">{i18n({"en": "How to Read", "zh": "如何阅读"})}</a>')
    sections_html.append(guide_html)
    for section in manifest["sections"]:
        sid = section["id"]
        if sid in AUTOMATIC_SECTIONS:
            raise RenderError(f"section id is reserved by the renderer: {sid}")
        nav.append(render_section_nav(section))
        components = render_section_components(section, ctx)
        sections_html.append(render_section_shell(section, components, section_note(section)))
    spec_suffix = spec_path.suffix.lower() if spec_path is not None else ".input"
    nav.append(f'<a href="#deliverables">{i18n({"en": "Deliverables", "zh": "交付文件"})}</a>')
    sections_html.append(render_deliverables(spec_suffix))
    nav.append(f'<a href="#provenance">{i18n({"en": "Provenance", "zh": "溯源信息"})}</a>')
    toc_index = build_toc_index(manifest)
    if toc_index["mode"] == "tree":
        toc_titles = {node["id"]: i18n(node["title"]) for node in toc_index["nodes"]}
        for section in manifest["sections"]:
            for component in section.get("components", []):
                if "title" not in component.get("toc", {}):
                    toc_titles[component["id"]] = component_nav_title(component)
        nav = [render_toc(toc_index, toc_titles, label)]
    payload_json = script_safe_json(ctx.embedded_payloads)
    meta_items = [
        ("Flow", project.get("flow_name", "")),
        ("Version", project.get("flow_version", "")),
        ("Mode", project.get("analysis_mode", "")),
        ("Template", manifest.get("template_version", TEMPLATE_VERSION)),
    ]
    meta = "\n".join(
        '<div class="meta-item">'
        f'<span class="meta-label">{escape(k)}</span>'
        f'<strong class="meta-value">{escape(str(v))}</strong>'
        "</div>"
        for k, v in meta_items
        if v
    )
    sidebar_links = "\n".join(
        [
            "<strong>TAFFISH links</strong>",
            '<a href="https://taffish.com" target="_blank" rel="noopener">TAFFISH website</a>',
            '<a href="https://taffish.github.io/" target="_blank" rel="noopener">TAFFISH Hub</a>',
            '<a href="https://github.com/taffish" target="_blank" rel="noopener">TAFFISH GitHub</a>',
        ]
    )
    language_buttons = "\n".join(
        f'<button type="button" data-lang-toggle="{escape(lang, quote=True)}" '
        f'aria-pressed="{"true" if lang == language_default else "false"}">{escape(language_button_label(lang))}</button>'
        for lang in languages
    )
    provenance = render_provenance(manifest, ctx)
    runtime_scripts = "\n".join(
        f'<script data-taffish-runtime="{escape(runtime_id, quote=True)}" '
        f'data-taffish-runtime-version="{escape(ctx.runtime_pack_versions.get(runtime_id, ""), quote=True)}">'
        f"{script_safe_text(script)}</script>"
        for runtime_id, script in sorted(ctx.runtime_packs.items())
    )
    html = f"""<!doctype html>
<html lang="{escape(language_default)}" data-lang="{escape(language_default)}" data-template="taffish-flow-report" data-template-version="{escape(TEMPLATE_VERSION)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(text_value(project.get("title"), "TAFFISH report"))}</title>
  <style>{css}</style>
  <script>{js}</script>
  {runtime_scripts}
</head>
<body>
  <div class="report-shell">
    <aside class="report-sidebar">
      <a class="brand-link" href="https://taffish.com" target="_blank" rel="noopener">
        {logo}
        <span><strong>TAFFISH</strong><small>Report renderer</small></span>
      </a>
      <div class="language-switch" aria-label="Language">
        {language_buttons}
      </div>
      <nav class="section-nav" aria-label="Report sections" data-toc-mode="{toc_index['mode']}">
        {"".join(nav)}
      </nav>
      <div class="sidebar-external" aria-label="TAFFISH links">
        {sidebar_links}
      </div>
    </aside>
    <main class="report-main">
      <header class="hero" id="top">
        <p class="eyebrow">TAFFISH REPORT</p>
        <h1>{i18n(project.get("title"))}</h1>
        <p class="lead">{i18n(project.get("subtitle", {"en": "", "zh": ""}))}</p>
        <div class="meta-grid">{meta}</div>
      </header>
      {"".join(sections_html)}
      <section class="section" id="provenance">
        <div class="section-head">
          <p class="kicker">PROVENANCE</p>
          <h2>{i18n({"en": "Provenance", "zh": "溯源信息"})}</h2>
          <p>{i18n({"en": "Renderer outputs and embedded asset indexes.", "zh": "渲染器输出与内嵌资产索引。"})}</p>
        </div>
        {provenance}
      </section>
      {render_interaction_shells()}
      <script type="application/json" id="embedded-subreports-data">{payload_json}</script>
      <script type="application/json" id="report-toc-data">{script_safe_json(toc_index)}</script>
      <footer class="report-footer">
        <p>{i18n({"en": "Generated by taffish-report-render.", "zh": "由 taffish-report-render 生成。"})}</p>
        <p>Template: TAFFISH flow-report {escape(TEMPLATE_VERSION)}. Report flow: {escape(str(project.get("flow_name", "")))} {escape(str(project.get("flow_version", "")))}.</p>
      </footer>
    </main>
  </div>
</body>
</html>
"""
    manifest["embedded_reports"] = [record.__dict__ for record in ctx.subreports]
    return html, ctx, manifest


def data_uri_from_bytes(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def script_safe_json(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_provenance(manifest: dict[str, Any], ctx: RenderContext) -> str:
    cards = [
        (
            {"en": "Template", "zh": "模板"},
            manifest.get("template_version", TEMPLATE_VERSION),
            {"en": "Canonical TAFFISH flow-report shell with inline CSS, JavaScript, logo, images, tables, and payload metadata.", "zh": "标准 TAFFISH flow-report 外壳，包含内联 CSS、JavaScript、logo、图片、表格和 payload 元数据。"},
        ),
        (
            {"en": "Assets", "zh": "资源"},
            str(len(ctx.assets)),
            {"en": "Input images, tables, and HTML pages collected by the renderer before writing output indexes.", "zh": "渲染器在写出索引前收集的输入图片、表格和 HTML 页面。"},
        ),
        (
            {"en": "Embedded HTML", "zh": "内嵌 HTML"},
            str(len(ctx.subreports)),
            {"en": "Native HTML reports stored inside the standalone HTML payload when local bundling is possible.", "zh": "在可本地打包时保存进单文件 HTML payload 的原生 HTML 报告。"},
        ),
        (
            {"en": "Config", "zh": "配置"},
            {"en": "kept", "zh": "已保留"},
            {"en": "Original report spec and normalized JSON are copied next to the final report.", "zh": "原始 report spec 和规范化 JSON 会复制到最终报告旁边。"},
        ),
    ]
    body = '<div class="method-grid">' + "".join(
        f'<article class="method-card"><small>{i18n(k)}</small><strong>{i18n(v) if isinstance(v, dict) else escape(str(v))}</strong><p>{i18n(note)}</p></article>'
        for k, v, note in cards
    ) + "</div>"
    if ctx.subreports:
        headers = ["id", "kind", "path", "status", "source_bytes", "embedded_bytes", "sha256", "message"]
        rows = [
            {
                "id": record.id,
                "kind": record.kind,
                "path": record.path,
                "status": record.status,
                "source_bytes": str(record.source_bytes),
                "embedded_bytes": str(record.embedded_bytes),
                "sha256": record.sha256,
                "message": record.message,
            }
            for record in ctx.subreports
        ]
        body += f"<h3>{label('Embedded HTML payloads', '内嵌 HTML payload')}</h3>" + render_table(headers, rows)
    return body


def record_generated_file(ctx: RenderContext, kind: str, component_id: str, label: str, path: Path) -> None:
    data = path.read_bytes()
    ctx.assets.append(
        AssetRecord(
            kind=kind,
            component_id=component_id,
            path=label,
            bytes=len(data),
            sha256=sha256_bytes(data),
        )
    )


def write_config_outputs(spec_path: Path, report_dir: Path, manifest: dict[str, Any], ctx: RenderContext) -> None:
    suffix = spec_path.suffix.lower()
    if suffix not in {".toml", ".json"}:
        suffix = ".input"
    spec_copy = report_dir / f"report.spec{suffix}"
    normalized = report_dir / "report.normalized.json"
    spec_copy.write_bytes(spec_path.read_bytes())
    normalized.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record_generated_file(ctx, "config", "renderer-spec", spec_copy.name, spec_copy)
    record_generated_file(ctx, "config", "renderer-normalized", normalized.name, normalized)


def write_indexes(out: Path, manifest: dict[str, Any], ctx: RenderContext) -> None:
    report_dir = out.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    toc_path = report_dir / "report_toc.json"
    toc_path.write_text(json.dumps(build_toc_index(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record_generated_file(ctx, "config", "renderer-toc", toc_path.name, toc_path)
    layout_index = report_dir / "report_layouts.tsv"
    with layout_index.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "component_id",
                "layout",
                "media_note_layout_declared",
                "media_note_layout_requested",
                "media_note_layout_effective",
                "note_item_count",
            ]
        )
        for section in manifest.get("sections", []):
            for component in section.get("components", []):
                if component.get("type") != "plot_card" or str(component.get("layout", "grid")).strip().lower() != "media":
                    continue
                declared, requested, effective, note_item_count = media_note_layout_values(component)
                writer.writerow(
                    [
                        component.get("id", ""),
                        "media",
                        declared or "",
                        requested,
                        effective,
                        note_item_count,
                    ]
                )
    record_generated_file(ctx, "config", "renderer-layouts", layout_index.name, layout_index)
    (report_dir / "report.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (report_dir / "report_template_version.txt").write_text(TEMPLATE_VERSION + "\n", encoding="utf-8")
    with (report_dir / "report_files.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["kind", "component_id", "path", "bytes", "sha256", "status", "message"])
        for record in ctx.assets:
            writer.writerow([record.kind, record.component_id, record.path, record.bytes, record.sha256, record.status, record.message])
    with (report_dir / "embedded_html_reports.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["id", "kind", "path", "status", "source_bytes", "embedded_bytes", "sha256", "message"])
        for record in ctx.subreports:
            writer.writerow([record.id, record.kind, record.path, record.status, record.source_bytes, record.embedded_bytes, record.sha256, record.message])


def component_path_values(component: dict[str, Any]) -> list[tuple[str, str]]:
    ctype = str(component.get("type", ""))
    values: list[tuple[str, str]] = []
    for field_name in COMPONENT_REGISTRY.get(ctype, {}).get("path_fields", []):
        value = component.get(field_name)
        if value is None or value == "":
            continue
        if field_name == "pages":
            for idx, item in enumerate(value if isinstance(value, list) else []):
                page_value = item.get("path") if isinstance(item, dict) else item
                if page_value:
                    values.append((f"pages[{idx}]", str(page_value)))
        else:
            values.append((field_name, str(value)))
    values.extend(extended_component_path_values(component))
    return values


def add_issue(issues: list[LintIssue], severity: str, location: str, message: str) -> None:
    issues.append(LintIssue(severity=severity, location=location, message=message))


def check_text_languages(issues: list[LintIssue], value: Any, location: str, languages: list[str]) -> None:
    if not isinstance(value, dict):
        add_issue(issues, "warn", location, "text is not language-structured; the same value will be shown in every language")
        return
    for lang in languages:
        text = value.get(lang)
        if text is None or text == "":
            add_issue(issues, "warn", location, f"missing {lang!r} text; renderer will use fallback text")


def check_long_unstructured_note(
    issues: list[LintIssue],
    owner: dict[str, Any],
    location: str,
    languages: list[str],
) -> None:
    note = owner.get("note")
    if note is None or owner.get("note_items"):
        return
    if isinstance(note, dict):
        for lang in languages:
            value = note.get(lang)
            if not isinstance(value, str):
                continue
            limit = NOTE_LENGTH_WARN_LIMITS.get(lang, 500)
            length = len(value.strip())
            if length > limit:
                add_issue(
                    issues,
                    "warn",
                    f"{location}.{lang}",
                    f"long note ({length} characters; suggested maximum {limit}) has no note_items",
                )
        return
    if isinstance(note, str) and len(note.strip()) > 500:
        add_issue(
            issues,
            "warn",
            location,
            f"long unstructured note ({len(note.strip())} characters) has no note_items",
        )


def lint_spec(spec: dict[str, Any], root: Path | None = None, strict: bool = False) -> tuple[list[LintIssue], dict[str, Any] | None]:
    issues: list[LintIssue] = []
    try:
        validate_spec(spec)
    except RenderError as exc:
        add_issue(issues, "error", "spec", str(exc))
        return issues, None
    try:
        manifest = normalize_spec(spec, root=root)
        if root is not None:
            validate_spec(manifest, allow_collections=False)
    except RenderError as exc:
        add_issue(issues, "error", "normalize", str(exc))
        return issues, None

    languages = manifest.get("languages", DEFAULT_LANGUAGES)
    check_text_languages(issues, manifest.get("project", {}).get("title"), "project.title", languages)
    if manifest.get("project", {}).get("subtitle") is not None:
        check_text_languages(issues, manifest.get("project", {}).get("subtitle"), "project.subtitle", languages)

    seen_paths: set[str] = set()
    component_count = 0
    for section in manifest.get("sections", []):
        section_id = section.get("id", "section")
        check_text_languages(issues, section.get("title"), f"sections.{section_id}.title", languages)
        if section.get("note") is not None:
            check_text_languages(issues, section.get("note"), f"sections.{section_id}.note", languages)
        check_long_unstructured_note(issues, section, f"sections.{section_id}.note", languages)
        components = section.get("components", [])
        if not components and not any(s.get("toc", {}).get("parent") == section_id for s in manifest.get("sections", [])):
            add_issue(issues, "warn", f"sections.{section_id}", "section has no components")
        for component in components:
            component_count += 1
            ctype = str(component.get("type", ""))
            component_id = str(component.get("id", f"{section_id}.{component_count}"))
            location = f"components.{component_id}"
            if ctype in COLLECTION_COMPONENTS and root is None:
                add_issue(issues, "warn", location, "collection component cannot be expanded without --root")
            if component.get("title") is not None:
                check_text_languages(issues, component.get("title"), f"{location}.title", languages)
            if component.get("note") is not None:
                check_text_languages(issues, component.get("note"), f"{location}.note", languages)
            check_long_unstructured_note(issues, component, f"{location}.note", languages)
            known_fields = set(COMPONENT_REGISTRY.get(ctype, {}).get("fields", []))
            if strict:
                for key in component:
                    if key not in known_fields:
                        add_issue(issues, "warn", f"{location}.{key}", f"unknown field for component type {ctype}")
            for field_name, rel in component_path_values(component):
                if root is None:
                    continue
                try:
                    path = resolve_path(root, rel)
                except RenderError as exc:
                    add_issue(issues, "error", f"{location}.{field_name}", str(exc))
                    continue
                seen_paths.add(rel)
                size = path.stat().st_size
                if size >= ASSET_WARN_BYTES:
                    add_issue(issues, "warn", f"{location}.{field_name}", f"large asset: {size} bytes")
                if ctype == "table_preview" and field_name == "source":
                    max_embed_bytes = int_value(component.get("max_embed_bytes"), 5_000_000, minimum=1)
                    if size > max_embed_bytes and bool_value(component.get("embed_full"), True):
                        add_issue(issues, "warn", f"{location}.source", f"table exceeds max_embed_bytes={max_embed_bytes}; full table will be linked/truncated")
                if ctype == "native_subreport" and field_name == "path":
                    policy = str(component.get("embed_policy", "auto")).strip().lower()
                    if policy not in {"auto", "always", "never"}:
                        add_issue(issues, "error", f"{location}.embed_policy", f"unsupported embed_policy: {policy}")
    if component_count == 0:
        add_issue(issues, "warn", "spec.sections", "no renderable components were declared")
    if root is not None and not seen_paths:
        add_issue(issues, "warn", "spec.assets", "no local assets were referenced")
    return issues, manifest


def lint_status(issues: list[LintIssue]) -> tuple[int, int]:
    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warn")
    return errors, warnings


def print_lint_issues(issues: list[LintIssue]) -> None:
    if not issues:
        print("lint ok: no issues")
        return
    for issue in issues:
        print(f"{issue.severity.upper()}\t{issue.location}\t{issue.message}")


def explain_manifest(manifest: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    sections = []
    total_components = 0
    referenced_assets = []
    total_source_bytes = 0
    for section in manifest.get("sections", []):
        components = []
        for component in section.get("components", []):
            total_components += 1
            paths = component_path_values(component)
            path_infos = []
            for field_name, rel in paths:
                info: dict[str, Any] = {"field": field_name, "path": rel}
                if root is not None:
                    try:
                        path = resolve_path(root, rel)
                        size = path.stat().st_size
                        total_source_bytes += size
                        info.update({"exists": True, "bytes": size})
                    except RenderError as exc:
                        info.update({"exists": False, "message": str(exc)})
                path_infos.append(info)
                referenced_assets.append(info)
            component_explanation = {
                "id": component.get("id"),
                "type": component.get("type"),
                "title": text_value(component.get("title"), str(component.get("id", ""))),
                "note_item_count": len(component.get("note_items", [])),
                "note_item_kinds": [item.get("kind") for item in component.get("note_items", [])],
                "paths": path_infos,
            }
            if component.get("type") == "plot_card" and str(component.get("layout", "grid")).strip().lower() == "media":
                declared, requested, effective, note_item_count = media_note_layout_values(component)
                component_explanation.update(
                    {
                        "media_note_layout_declared": declared,
                        "media_note_layout_requested": requested,
                        "media_note_layout_effective": effective,
                        "note_item_count": note_item_count,
                    }
                )
            components.append(component_explanation)
        sections.append(
            {
                "id": section.get("id"),
                "kind": section.get("kind"),
                "title": text_value(section.get("title"), str(section.get("id", ""))),
                "note_item_count": len(section.get("note_items", [])),
                "note_item_kinds": [item.get("kind") for item in section.get("note_items", [])],
                "component_count": len(components),
                "components": components,
            }
        )
    return {
        "schema_version": manifest.get("schema_version"),
        "toc": build_toc_index(manifest),
        "template": manifest.get("template"),
        "template_version": manifest.get("template_version"),
        "project": manifest.get("project", {}),
        "language_default": manifest.get("language_default"),
        "languages": manifest.get("languages", []),
        "section_count": len(sections),
        "component_count": total_components,
        "asset_count": len(referenced_assets),
        "referenced_source_bytes": total_source_bytes,
        "html_warn_bytes": HTML_WARN_BYTES,
        "html_error_bytes": HTML_ERROR_BYTES,
        "sections": sections,
    }


def report_json_schema() -> dict[str, Any]:
    component_defs: dict[str, Any] = {}
    for name, info in COMPONENT_REGISTRY.items():
        properties: dict[str, Any] = {
            "type": {"const": name},
            "id": {"type": "string"},
            "toc": {"$ref": "#/$defs/componentToc"},
            "title": {"$ref": "#/$defs/i18nText"},
            "note": {"$ref": "#/$defs/i18nText"},
            "note_items": {
                "type": "array",
                "items": {"$ref": "#/$defs/noteItem"},
            },
        }
        for field_name in info.get("fields", []):
            if field_name in properties or field_name in {"id", "type", "title", "note", "note_items"}:
                continue
            if field_name in {
                "source",
                "image",
                "path",
                "pdb",
                "static_image",
                "runtime",
                "representation",
                "color_scheme",
                "background",
                "atom_filter",
                "kind",
                "language",
                "syntax",
                "default_state",
                "embed_policy",
                "id_prefix",
                "filter_column",
                "filter_value",
                "site_table",
                "site_structure_id",
                "site_structure_column",
                "site_model",
                "site_chain",
                "site_chain_column",
                "site_residue_column",
                "site_group_column",
                "site_label_column",
                "x",
                "y",
                "label",
                "size",
                "color",
                "pvalue",
                "padj",
                "log2fc",
                "base_mean",
                "gene",
                "description",
                "count",
                "gene_ratio",
                "color_up",
                "color_down",
                "color_ns",
                "color_low",
                "color_high",
                "image_position",
                "media_vertical_align",
                "media_gap",
                "media_note_layout",
            }:
                properties[field_name] = {"type": "string"}
            elif field_name in {"pages"}:
                properties[field_name] = {
                    "type": "array",
                    "items": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}]},
                }
            elif field_name in {"models"}:
                properties[field_name] = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "pdb": {"type": "string"},
                            "color": {"type": "string"},
                            "label": {"anyOf": [{"type": "string"}, {"$ref": "#/$defs/i18nText"}]},
                            "title": {"$ref": "#/$defs/i18nText"},
                        },
                        "required": ["pdb"],
                        "additionalProperties": True,
                    },
                }
            elif field_name in {"site_groups"}:
                properties[field_name] = {"type": "array", "items": {"type": "object", "additionalProperties": True}}
            elif field_name in {
                "zoom",
                "embed_full",
                "copy",
                "embed_linked_pages",
                "show_surface",
                "spin",
                "controls_open",
                "fixed_range",
                "show_threshold_lines",
            }:
                properties[field_name] = {"type": "boolean"}
            elif field_name in {
                "preview_rows",
                "max_embed_rows",
                "max_embed_bytes",
                "max_lines",
                "linked_page_limit",
                "max_atoms",
                "height",
                "site_max_sites",
                "top_n",
                "max_points",
                "label_max_chars",
            }:
                properties[field_name] = {"type": "integer", "minimum": 0}
            elif field_name in {"default_padj", "default_log2fc", "point_size", "opacity"}:
                properties[field_name] = {"type": "number", "minimum": 0}
            elif field_name == "media_image_ratio":
                properties[field_name] = {"type": "number", "minimum": 0.25, "maximum": 0.70}
            elif field_name == "caption":
                properties[field_name] = {"$ref": "#/$defs/i18nText"}
            else:
                properties[field_name] = {}
        if name == "plot_card":
            properties["layout"] = {"type": "string", "enum": ["grid", "wide", "media"], "default": "grid"}
            properties["default_fit"] = {"type": "string", "enum": ["contain", "original"], "default": "contain"}
            properties["note_position"] = {"type": "string", "enum": ["top", "bottom"], "default": "bottom"}
            properties["image_position"] = {"type": "string", "enum": ["left", "right"], "default": "left"}
            properties["media_vertical_align"] = {"type": "string", "enum": ["start", "center"], "default": "start"}
            properties["media_gap"] = {"type": "string", "enum": ["compact", "normal", "relaxed"], "default": "normal"}
            properties["media_note_layout"] = {"type": "string", "enum": list(MEDIA_NOTE_LAYOUTS), "default": "auto"}
        component_defs[name] = {
            "type": "object",
            "properties": properties,
            "required": ["type", *info.get("required", [])],
            "additionalProperties": True,
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/taffish/taffish-report-render/schema/report.spec.schema.json",
        "title": "TAFFISH report spec",
        "type": "object",
        "required": ["template", "project", "sections"],
        "properties": {
            "schema_version": {"type": "string"},
            "template": {"const": "taffish-flow-report"},
            "template_version": {"type": "string"},
            "languages": {"type": "array", "items": {"type": "string"}},
            "language_default": {"type": "string"},
            "project": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "flow_name": {"type": "string"},
                    "flow_version": {"type": "string"},
                    "analysis_mode": {"type": "string"},
                    "title": {"$ref": "#/$defs/i18nText"},
                    "subtitle": {"$ref": "#/$defs/i18nText"},
                },
                "additionalProperties": True,
            },
            "provenance": {"type": "object", "additionalProperties": True},
            "sections": {
                "type": "array",
                "items": {"$ref": "#/$defs/section"},
                "minItems": 1,
            },
        },
        "$defs": {
            "tocI18nText": {
                "type": "object", "minProperties": 1,
                "additionalProperties": {"type": "string", "minLength": 1, "pattern": "\\S"},
                "description": "Non-empty plain text for every declared report language; cross-field coverage is checked by validate-spec.",
            },
            "sectionToc": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "parent": {"type": "string", "minLength": 1, "pattern": "^[A-Za-z0-9_.-]+$"},
                    "collapsed": {"type": "boolean"},
                    "title": {"$ref": "#/$defs/tocI18nText"},
                },
            },
            "componentToc": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "visible": {"type": "boolean"},
                    "title": {"$ref": "#/$defs/tocI18nText"},
                },
            },
            "i18nText": {
                "type": "object",
                "properties": {lang: {"type": "string"} for lang in LANGUAGE_NAMES},
                "additionalProperties": {"type": "string"},
            },
            "noteItem": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(NOTE_ITEM_KINDS)},
                    "label": {"$ref": "#/$defs/noteI18nText"},
                    "body": {"$ref": "#/$defs/noteI18nText"},
                    "items": {"$ref": "#/$defs/noteI18nList"},
                },
                "required": ["kind", "label"],
                "anyOf": [{"required": ["body"]}, {"required": ["items"]}],
                "additionalProperties": False,
            },
            "noteI18nText": {
                "type": "object",
                "properties": {lang: {"type": "string", "minLength": 1} for lang in LANGUAGE_NAMES},
                "required": ["en", "zh"],
                "additionalProperties": {"type": "string", "minLength": 1},
            },
            "noteI18nList": {
                "type": "object",
                "properties": {
                    lang: {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}
                    for lang in LANGUAGE_NAMES
                },
                "required": ["en", "zh"],
                "additionalProperties": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 1},
                },
            },
            "section": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "id": {"type": "string"},
                    "toc": {"$ref": "#/$defs/sectionToc"},
                    "kind": {"type": "string"},
                    "title": {"$ref": "#/$defs/i18nText"},
                    "note": {"$ref": "#/$defs/i18nText"},
                    "note_items": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/noteItem"},
                    },
                    "components": {
                        "type": "array",
                        "items": {"anyOf": [{"$ref": f"#/$defs/{name}"} for name in COMPONENTS]},
                    },
                },
                "additionalProperties": True,
            },
            **component_defs,
        },
    }


def toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RenderError("cannot migrate a non-finite number to TOML")
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_scalar(item) for item in value) + "]"
    return toml_quote("" if value is None else str(value))


def toml_write_i18n(lines: list[str], prefix: str, value: Any) -> None:
    if isinstance(value, dict):
        for lang in sorted(value):
            lines.append(f"{prefix}.{lang} = {toml_scalar(value[lang])}")
    elif value is not None:
        lines.append(f"{prefix} = {toml_scalar(value)}")


def toml_write_toc(lines: list[str], toc: dict[str, Any]) -> None:
    for key, value in toc.items():
        if key == "title":
            toml_write_i18n(lines, "toc.title", value)
        else:
            lines.append(f"toc.{key} = {toml_scalar(value)}")
    if not toc:
        lines.append("toc = {}")


def toml_write_note_items(lines: list[str], table_path: str, note_items: Any) -> None:
    if not isinstance(note_items, list):
        return
    for item in note_items:
        if not isinstance(item, dict):
            continue
        lines.append("")
        lines.append(f"[[{table_path}]]")
        lines.append(f"kind = {toml_scalar(item.get('kind'))}")
        toml_write_i18n(lines, "label", item.get("label"))
        if item.get("body") is not None:
            toml_write_i18n(lines, "body", item.get("body"))
        if isinstance(item.get("items"), dict):
            toml_write_i18n(lines, "items", item.get("items"))


def dump_toml_spec(manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("schema_version", "template", "template_version", "languages", "language_default"):
        if key in manifest:
            lines.append(f"{key} = {toml_scalar(manifest[key])}")
    lines.append("")
    lines.append("[project]")
    project = manifest.get("project", {})
    for key, value in project.items():
        if isinstance(value, dict):
            toml_write_i18n(lines, key, value)
        else:
            lines.append(f"{key} = {toml_scalar(value)}")
    if manifest.get("provenance"):
        lines.append("")
        lines.append("[provenance]")
        for key, value in manifest["provenance"].items():
            lines.append(f"{key} = {toml_scalar(value)}")
    for section in manifest.get("sections", []):
        lines.append("")
        lines.append("[[sections]]")
        for key, value in section.items():
            if key in {"components", "note_items"}:
                continue
            if key == "toc":
                toml_write_toc(lines, value)
            elif isinstance(value, dict):
                toml_write_i18n(lines, key, value)
            else:
                lines.append(f"{key} = {toml_scalar(value)}")
        toml_write_note_items(lines, "sections.note_items", section.get("note_items"))
        for component in section.get("components", []):
            lines.append("")
            lines.append("[[sections.components]]")
            for key, value in component.items():
                if key == "note_items":
                    continue
                if key == "toc":
                    toml_write_toc(lines, value)
                elif isinstance(value, dict):
                    toml_write_i18n(lines, key, value)
                else:
                    lines.append(f"{key} = {toml_scalar(value)}")
            toml_write_note_items(lines, "sections.components.note_items", component.get("note_items"))
    return "\n".join(lines) + "\n"


def html_summary(path: Path) -> dict[str, Any]:
    html = path.read_text(encoding="utf-8", errors="replace")
    try:
        toc_index = inspect_toc_html(html)
    except (ValueError, KeyError, TypeError) as exc:
        raise RenderError(f"html inspection failed; toc: {exc}") from exc
    image_data_uri_mimes = main_document_image_data_uri_mimes(html)
    payload_match = re.search(r'<script[^>]+id="embedded-subreports-data"[^>]*>(.*?)</script>', html, re.I | re.S)
    payload_count = 0
    if payload_match:
        try:
            payload_count = len(json.loads(payload_match.group(1)))
        except json.JSONDecodeError:
            payload_count = -1
    return {
        "path": str(path),
        "toc": toc_index,
        "bytes": path.stat().st_size,
        "template": "taffish-flow-report" if 'data-template="taffish-flow-report"' in html else "",
        "data_image_count": html.count("data:image/"),
        "non_image_img_data_uri_count": sum(not mime.startswith("image/") for mime in image_data_uri_mimes),
        "embedded_subreport_payloads": payload_count,
        "external_stylesheet_links": len(re.findall(r"<link\b[^>]*stylesheet", html, re.I)),
        "external_script_src": len(re.findall(r"<script\b[^>]*\bsrc\s*=", html, re.I)),
        "section_count": len(re.findall(r'<section\b[^>]*class="section"', html, re.I)),
    }


def command_render(args: argparse.Namespace) -> int:
    spec = parse_spec(args.spec)
    root = args.root.resolve()
    out = args.out.resolve()
    if out.exists() and not args.force:
        raise RenderError(f"output already exists: {out}; use --force to overwrite")
    html, ctx, manifest = render_report(spec, root, args.spec, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    record_generated_file(ctx, "report", "renderer-html", out.name, out)
    write_config_outputs(args.spec, out.parent, manifest, ctx)
    write_indexes(out, manifest, ctx)
    if args.validate:
        validate_html_file(out)
    print(f"rendered: {out}")
    return 0


def command_validate_spec(args: argparse.Namespace) -> int:
    spec = parse_spec(args.spec)
    validate_spec(spec)
    if getattr(args, "root", None) is not None:
        manifest = normalize_spec(spec, root=args.root.resolve())
        validate_spec(manifest, allow_collections=False)
    print(f"spec ok: {args.spec}")
    return 0


def command_validate_html(args: argparse.Namespace) -> int:
    validate_html_file(args.html)
    print(f"html ok: {args.html}")
    return 0


def command_components(_: argparse.Namespace) -> int:
    for component in COMPONENTS:
        print(component)
    return 0


def command_schema(args: argparse.Namespace) -> int:
    schema_text = json.dumps(report_json_schema(), ensure_ascii=False, indent=2) + "\n"
    if args.out is None or str(args.out) == "-":
        print(schema_text, end="")
    else:
        if args.out.exists() and not args.force:
            raise RenderError(f"output already exists: {args.out}; use --force to overwrite")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(schema_text, encoding="utf-8")
        print(f"created: {args.out}")
    return 0


def command_component_doc(args: argparse.Namespace) -> int:
    if args.component == "all":
        names = COMPONENTS
    else:
        if args.component not in COMPONENTS:
            raise RenderError(f"unknown component: {args.component}")
        names = [args.component]
    for name in names:
        info = COMPONENT_REGISTRY[name]
        print(name)
        print("  kind     :", info.get("kind", ""))
        if info.get("expands_to"):
            print("  expands  :", info["expands_to"])
        print("  required :", ", ".join(info.get("required", [])) or "none")
        print("  fields   :", ", ".join(info.get("fields", [])))
        print("  summary  :", COMPONENT_DOCS.get(name, info.get("summary", "")))
        print()
    return 0


def command_lint(args: argparse.Namespace) -> int:
    spec = parse_spec(args.spec)
    root = args.root.resolve() if args.root is not None else None
    issues, manifest = lint_spec(spec, root=root, strict=args.strict)
    if args.json:
        payload = {
            "spec": str(args.spec),
            "root": str(root) if root is not None else None,
            "issues": [issue.__dict__ for issue in issues],
            "summary": {
                "errors": lint_status(issues)[0],
                "warnings": lint_status(issues)[1],
                "sections": len(manifest.get("sections", [])) if manifest else 0,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_lint_issues(issues)
    errors, warnings = lint_status(issues)
    if errors:
        return 1
    if warnings and args.fail_on_warn:
        return 1
    return 0


def command_explain(args: argparse.Namespace) -> int:
    spec = parse_spec(args.spec)
    validate_spec(spec)
    root = args.root.resolve() if args.root is not None else None
    manifest = normalize_spec(spec, root=root)
    validate_spec(manifest, allow_collections=False if root is not None else True)
    explanation = explain_manifest(manifest, root=root)
    if args.json:
        print(json.dumps(explanation, ensure_ascii=False, indent=2))
        return 0
    project = explanation["project"]
    print(f"project : {project.get('flow_name', '')} {project.get('flow_version', '')}".rstrip())
    print(f"mode    : {project.get('analysis_mode', '')}")
    print(f"template: {explanation['template']} {explanation['template_version']}")
    print(f"language: {explanation['language_default']} ({', '.join(explanation['languages'])})")
    print(f"sections: {explanation['section_count']}")
    print(f"components: {explanation['component_count']}")
    print(f"assets  : {explanation['asset_count']}")
    if root is not None:
        print(f"source bytes: {explanation['referenced_source_bytes']}")
    for section in explanation["sections"]:
        section_kinds = ",".join(str(kind) for kind in section["note_item_kinds"]) or "none"
        print(
            f"- {section['id']} [{section['kind']}] components={section['component_count']} "
            f"note_items={section['note_item_count']} kinds={section_kinds}"
        )
        for component in section["components"]:
            path_text = ", ".join(item["path"] for item in component["paths"]) if component["paths"] else "no direct asset"
            component_kinds = ",".join(str(kind) for kind in component["note_item_kinds"]) or "none"
            media_layout_text = ""
            if "media_note_layout_effective" in component:
                declared = component.get("media_note_layout_declared") or "<default>"
                media_layout_text = (
                    f"; media_note_layout declared={declared} "
                    f"requested={component['media_note_layout_requested']} "
                    f"effective={component['media_note_layout_effective']}"
                )
            print(
                f"  - {component['id']} ({component['type']}): {path_text}; "
                f"note_items={component['note_item_count']} kinds={component_kinds}{media_layout_text}"
            )
    return 0


def command_migrate(args: argparse.Namespace) -> int:
    spec = parse_spec(args.spec)
    validate_spec(spec)
    root = args.root.resolve() if args.root is not None else None
    manifest = normalize_spec(spec, root=root)
    validate_spec(manifest, allow_collections=False if root is not None else True)
    output_format = args.format
    if output_format == "auto":
        suffix = "" if args.out is None or str(args.out) == "-" else args.out.suffix.lower()
        output_format = "toml" if suffix == ".toml" else "json"
    if output_format == "toml":
        text = dump_toml_spec(manifest)
    else:
        text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.out is None or str(args.out) == "-":
        print(text, end="")
        return 0
    if args.out.exists() and not args.force:
        raise RenderError(f"output already exists: {args.out}; use --force to overwrite")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"created: {args.out}")
    return 0


def command_inspect_html(args: argparse.Namespace) -> int:
    summary = html_summary(args.html)
    if args.validate:
        validate_html_file(args.html)
        summary["validation"] = "ok"
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for key, value in summary.items():
            print(f"{key}: {value}")
    if summary["bytes"] >= HTML_ERROR_BYTES:
        return 1
    return 0


def read_tsv_records(path: Path) -> list[dict[str, str]]:
    _, rows = read_tsv(path)
    return rows


def command_list_assets(args: argparse.Namespace) -> int:
    path = args.path
    report_dir = path if path.is_dir() else path.parent
    files_index = report_dir / "report_files.tsv"
    embedded_index = report_dir / "embedded_html_reports.tsv"
    layout_index = report_dir / "report_layouts.tsv"
    payload: dict[str, Any] = {"report_dir": str(report_dir), "files": [], "embedded_html": [], "layouts": []}
    if files_index.exists():
        payload["files"] = read_tsv_records(files_index)
    if embedded_index.exists():
        payload["embedded_html"] = read_tsv_records(embedded_index)
    if layout_index.exists():
        payload["layouts"] = read_tsv_records(layout_index)
    if path.is_file() and path.suffix.lower() in {".html", ".htm"}:
        payload["html"] = html_summary(path)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"report_dir: {payload['report_dir']}")
        print(f"files: {len(payload['files'])}")
        for row in payload["files"]:
            print(f"  {row.get('kind', '')}\t{row.get('component_id', '')}\t{row.get('bytes', '')}\t{row.get('path', '')}")
        print(f"embedded_html: {len(payload['embedded_html'])}")
        for row in payload["embedded_html"]:
            print(f"  {row.get('status', '')}\t{row.get('id', '')}\t{row.get('embedded_bytes', '')}\t{row.get('path', '')}")
        print(f"layouts: {len(payload['layouts'])}")
        for row in payload["layouts"]:
            print(
                f"  {row.get('component_id', '')}\t{row.get('layout', '')}\t"
                f"{row.get('media_note_layout_requested', '')}->{row.get('media_note_layout_effective', '')}"
            )
        if "html" in payload:
            print(f"html_bytes: {payload['html']['bytes']}")
            print(f"data_image_count: {payload['html']['data_image_count']}")
            print(f"non_image_img_data_uri_count: {payload['html']['non_image_img_data_uri_count']}")
            print(f"embedded_subreport_payloads: {payload['html']['embedded_subreport_payloads']}")
    return 0


def starter_report_toml(include_demo_assets: bool = False) -> str:
    components = """[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/key_metrics.tsv"
title.zh = "0.1 输入、输出与核心状态"
title.en = "0.1 Inputs, Outputs, and Headline Status"

[[sections.components.note_items]]
kind = "reading"
label.zh = "怎么看"
label.en = "How to read"
body.zh = "先检查状态卡，再进入详细表格和图。"
body.en = "Review the status cards before opening detailed tables and plots."
"""
    if include_demo_assets:
        components += """
[[sections.components]]
type = "table_preview"
id = "example_table"
source = "03_results/example_table.tsv"
preview_rows = 2
embed_full = true

[[sections.components]]
type = "plot_card"
id = "example_plot"
title.zh = "示例图片"
title.en = "Example Plot"
image = "03_results/example_plot.svg"
zoom = true
caption.zh = "这张 SVG 图片会被内嵌进最终 HTML。"
caption.en = "This SVG image is embedded into the final HTML."
"""
    return f"""schema_version = "0.1"
template = "taffish-flow-report"
template_version = "{TEMPLATE_VERSION}"
languages = ["en", "zh"]
language_default = "zh"

[project]
flow_name = "example-flow"
flow_version = "0.2.0-r1"
analysis_mode = "example"
title.zh = "示例 TAFFISH 报告"
title.en = "Example TAFFISH Report"
subtitle.zh = "一个最小 report.toml。"
subtitle.en = "A minimal report.toml."

[provenance]
versions = "04_reports/versions.tsv"

[[sections]]
id = "overview"
kind = "overview"
title.zh = "0. 项目总览"
title.en = "0. Project Overview"
note.zh = "先确认报告身份和主要状态。"
note.en = "Confirm report identity and headline status first."

[[sections.note_items]]
kind = "boundary"
label.zh = "说明边界"
label.en = "Boundary"
body.zh = "示例报告只验证 renderer，不代表科学分析已完成。"
body.en = "This starter validates the renderer; it does not represent a completed scientific analysis."

{components}"""


def command_init(args: argparse.Namespace) -> int:
    sample = starter_report_toml()
    if args.out is None or str(args.out) == "-":
        print(sample, end="")
        return 0
    if args.out.exists() and not args.force:
        raise RenderError(f"output already exists: {args.out}; use --force to overwrite")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(sample, encoding="utf-8")
    print(f"created: {args.out}")
    return 0


def command_new(args: argparse.Namespace) -> int:
    outdir = args.outdir
    if outdir.exists() and not outdir.is_dir():
        raise RenderError(f"output path exists but is not a directory: {outdir}")
    if outdir.exists() and any(outdir.iterdir()) and not args.force:
        raise RenderError(f"output directory is not empty: {outdir}; use --force to overwrite starter files")
    reports_dir = outdir / "04_reports"
    results_dir = outdir / "03_results"
    reports_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.toml").write_text(starter_report_toml(include_demo_assets=True), encoding="utf-8")
    (reports_dir / "key_metrics.tsv").write_text(
        "metric\tvalue\tnote\n"
        "Samples\t3\tDemo sample count\n"
        "Report mode\tstandalone\tAll primary assets are embedded\n"
        "Status\tready\tGenerated by taffish-report-render new\n",
        encoding="utf-8",
    )
    (results_dir / "example_table.tsv").write_text(
        "feature\tvalue\tstatus\n"
        "input_spec\treport.toml\tok\n"
        "asset_root\t.\tok\n"
        "standalone_html\t04_reports/report.html\tpending\n",
        encoding="utf-8",
    )
    (results_dir / "example_plot.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 320" role="img" aria-label="TAFFISH demo plot">
  <rect width="720" height="320" rx="24" fill="#f6fbfa"/>
  <line x1="90" y1="250" x2="640" y2="250" stroke="#183238" stroke-width="3"/>
  <line x1="90" y1="250" x2="90" y2="70" stroke="#183238" stroke-width="3"/>
  <rect x="140" y="135" width="80" height="115" rx="8" fill="#0f8a7a"/>
  <rect x="280" y="95" width="80" height="155" rx="8" fill="#f2b84b"/>
  <rect x="420" y="165" width="80" height="85" rx="8" fill="#7aa7ff"/>
  <text x="90" y="45" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#183238">Standalone report demo</text>
  <text x="140" y="280" font-family="Arial, sans-serif" font-size="18" fill="#52666d">tables</text>
  <text x="278" y="280" font-family="Arial, sans-serif" font-size="18" fill="#52666d">plots</text>
  <text x="416" y="280" font-family="Arial, sans-serif" font-size="18" fill="#52666d">subreports</text>
</svg>
""",
        encoding="utf-8",
    )
    print(f"created demo workspace: {outdir}")
    # TAFFISH 0.11.0 joins *ARGV* as shell text. Preserve one quoting layer
    # through the invoking shell; this is not needed for direct report-render.
    render_args = ["render", "--spec", str(outdir / "report.toml"), "--root", str(outdir),
                   "--out", str(reports_dir / "report.html"), "--force", "--validate"]
    print(
        "render with: "
        + shlex.join(["taf-taffish-report-render", *map(shlex.quote, render_args)])
    )
    return 0


def main_document_image_data_uri_mimes(html: str) -> list[str]:
    main_markup = re.sub(r"<script\b[^>]*>.*?</script\s*>", "", html, flags=re.I | re.S)
    mimes: list[str] = []
    for match in re.finditer(r"<img\b([^>]*)>", main_markup, re.I | re.S):
        src = attr_value(match.group(1), "src")
        if src is None or not src.lower().startswith("data:"):
            continue
        mime_match = re.match(r"data:([^;,]+)(?:;[^,]*)?,", src, re.I)
        mimes.append(mime_match.group(1).lower() if mime_match else "")
    return mimes


def validate_html_file(path: Path) -> None:
    html = path.read_text(encoding="utf-8", errors="replace")
    try:
        inspect_toc_html(html, validate=True)
    except (ValueError, KeyError, TypeError) as exc:
        raise RenderError(f"html validation failed; toc: {exc}") from exc
    required = [
        'data-template="taffish-flow-report"',
        "report-shell",
        "report-sidebar",
        "report-main",
        "brand-link",
        "language-switch",
        "section-nav",
        "sidebar-external",
        "hero",
        "section",
        "report-footer",
        "data:image/",
        "<style>",
        "<script>",
    ]
    missing = [item for item in required if item not in html]
    if missing:
        raise RenderError("html validation failed; missing: " + ", ".join(missing))
    head_match = re.search(r"<head\b[^>]*>(.*?)</head>", html, re.I | re.S)
    head = head_match.group(1) if head_match else html[:4096]
    if re.search(r"<link\b[^>]*stylesheet", head, re.I):
        raise RenderError("html validation failed; external stylesheet link found")
    if re.search(r"<script\b[^>]*\bsrc\s*=", html, re.I):
        raise RenderError("html validation failed; external script src found in main report")
    if re.search(r"data:image/[^;\"']+;base64,[\"']", html, re.I):
        raise RenderError("html validation failed; empty image data URI found")
    invalid_image_mimes = [
        mime or "<invalid>"
        for mime in main_document_image_data_uri_mimes(html)
        if not mime.startswith("image/")
    ]
    if invalid_image_mimes:
        raise RenderError(
            "html validation failed; image element uses non-image data URI MIME: "
            + ", ".join(sorted(set(invalid_image_mimes)))
        )
    if "TAFFISH_NGL_TEST_SHIM" in html and os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") != "1":
        raise RenderError("html validation failed; test-only NGL shim found in a non-test validation context")
    if "TAFFISH_IGV_TEST_SHIM" in html and os.environ.get("TAFFISH_REPORT_RENDER_ALLOW_RUNTIME_SHIMS") != "1":
        raise RenderError("html validation failed; test-only IGV shim found in a non-test validation context")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taf-taffish-report-render", description="Render TAFFISH standalone HTML reports from structured specs.")
    parser.add_argument("--version", action="version", version=f"taffish-report-render {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="render a standalone HTML report")
    p.add_argument("--spec", required=True, type=Path, help="report.toml or report.manifest.json")
    p.add_argument("--root", required=True, type=Path, help="report result root used to resolve relative paths")
    p.add_argument("--out", required=True, type=Path, help="output standalone HTML")
    p.add_argument("--force", action="store_true", help="overwrite existing output")
    p.add_argument("--validate", action="store_true", help="run a lightweight HTML contract check after rendering")
    p.set_defaults(func=command_render)

    p = sub.add_parser("validate-spec", help="validate a report spec")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--root", type=Path, help="optional result root; enables collection expansion checks")
    p.set_defaults(func=command_validate_spec)

    p = sub.add_parser("validate-html", help="validate a rendered report")
    p.add_argument("html", type=Path)
    p.set_defaults(func=command_validate_html)

    p = sub.add_parser("components", help="list supported stable components")
    p.set_defaults(func=command_components)

    p = sub.add_parser("schema", help="print the JSON schema for report specs")
    p.add_argument("--out", type=Path, help="write schema to file; omit or use - for stdout")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_schema)

    p = sub.add_parser("component-doc", help="describe one component or all components")
    p.add_argument("component", help="component name or 'all'")
    p.set_defaults(func=command_component_doc)

    p = sub.add_parser("lint", help="preflight-check a report spec without rendering")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--root", type=Path, help="optional result root for path, collection and size checks")
    p.add_argument("--strict", action="store_true", help="warn about unknown component fields")
    p.add_argument("--json", action="store_true", help="emit machine-readable lint results")
    p.add_argument("--fail-on-warn", action="store_true", help="return non-zero when warnings are present")
    p.set_defaults(func=command_lint)

    p = sub.add_parser("explain", help="summarize what a report spec will render")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--root", type=Path, help="optional result root for path and size summaries")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_explain)

    p = sub.add_parser("migrate", help="normalize or expand a report spec to JSON/TOML")
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--root", type=Path, help="optional result root; expands collection components")
    p.add_argument("--out", type=Path, help="output file; omit or use - for stdout")
    p.add_argument("--format", choices=["auto", "json", "toml"], default="auto")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_migrate)

    p = sub.add_parser("inspect-html", help="inspect a rendered standalone HTML report")
    p.add_argument("html", type=Path)
    p.add_argument("--json", action="store_true")
    p.add_argument("--validate", action="store_true", help="also run validate-html")
    p.set_defaults(func=command_inspect_html)

    p = sub.add_parser("list-assets", help="list report_files.tsv and embedded_html_reports.tsv entries")
    p.add_argument("path", type=Path, help="report HTML file or report directory")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_list_assets)

    p = sub.add_parser("init", help="write a minimal report.toml")
    p.add_argument("--out", type=Path, help="write to file; omit or use - for stdout")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_init)

    p = sub.add_parser("new", help="create a runnable starter report workspace")
    p.add_argument("--outdir", required=True, type=Path)
    p.add_argument("--force", action="store_true", help="overwrite starter files in an existing directory")
    p.set_defaults(func=command_new)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
