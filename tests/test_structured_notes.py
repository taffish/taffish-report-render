#!/usr/bin/env python3
"""Unit and round-trip coverage for the shared structured-note contract."""

from __future__ import annotations

import tempfile
import tomllib
import unittest
from copy import deepcopy
from pathlib import Path

from taffish_report_render.cli import (
    COMPONENT_REGISTRY,
    NOTE_ITEM_KINDS,
    RenderError,
    dump_toml_spec,
    explain_manifest,
    lint_spec,
    normalize_spec,
    render_structured_note_items,
    validate_spec,
)


def note_item(kind: str = "purpose") -> dict[str, object]:
    return {
        "kind": kind,
        "label": {"en": f"{kind} label", "zh": f"{kind} 标签"},
        "body": {
            "en": "A focused English explanation for this evidence unit.",
            "zh": "这一证据单元的中文结构化说明。",
        },
    }


def base_spec() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "template": "taffish-flow-report",
        "languages": ["en", "zh"],
        "language_default": "zh",
        "project": {
            "flow_name": "structured-note-test",
            "flow_version": "0.3.1-r1",
            "analysis_mode": "unit",
            "title": {"en": "Structured note test", "zh": "结构化说明测试"},
        },
        "sections": [
            {
                "id": "overview",
                "kind": "overview",
                "title": {"en": "0. Overview", "zh": "0. 总览"},
                "note_items": [note_item("question")],
                "components": [
                    {
                        "type": "dashboard_cards",
                        "id": "summary",
                        "source": "summary.tsv",
                        "title": {"en": "0.1 Summary", "zh": "0.1 摘要"},
                        "note_items": [note_item("reading")],
                    }
                ],
            }
        ],
    }


class StructuredNoteTests(unittest.TestCase):
    def test_every_component_advertises_shared_note_items(self) -> None:
        missing = [name for name, info in COMPONENT_REGISTRY.items() if "note_items" not in info["fields"]]
        self.assertEqual(missing, [])

    def test_existing_table_i18n_fold_field_remains_strict_lint_compatible(self) -> None:
        spec = base_spec()
        component = spec["sections"][0]["components"][0]  # type: ignore[index]
        component["type"] = "table_preview"
        component["fold_i18n_columns"] = True
        issues, _ = lint_spec(spec, strict=True)
        self.assertFalse(any("fold_i18n_columns" in issue.location for issue in issues))

    def test_every_kind_validates_and_renders_in_source_order(self) -> None:
        spec = base_spec()
        items = [note_item(kind) for kind in NOTE_ITEM_KINDS]
        spec["sections"][0]["note_items"] = items  # type: ignore[index]
        validate_spec(spec)
        html = render_structured_note_items({"note_items": items})
        self.assertEqual(html.count('class="structured-note-item '), len(NOTE_ITEM_KINDS))
        positions = [html.index(f'data-note-kind="{kind}"') for kind in NOTE_ITEM_KINDS]
        self.assertEqual(positions, sorted(positions))

    def test_body_and_real_list_can_coexist_and_are_escaped(self) -> None:
        item = note_item("elements")
        item["label"] = {"en": "**Elements**", "zh": "**图中元素**"}
        item["body"] = {
            "en": '<script>alert("x")</script>',
            "zh": '<img src=x onerror="alert(1)">',
        }
        item["items"] = {
            "en": ["64-character SHA: " + "a" * 64, "URL-like https://example.invalid/" + "x" * 120],
            "zh": ["64 字符校验值：" + "a" * 64, "类似 URL 的纯文本：https://example.invalid/" + "甲" * 80],
        }
        spec = base_spec()
        spec["sections"][0]["note_items"] = [item]  # type: ignore[index]
        validate_spec(spec)
        html = render_structured_note_items({"note_items": [item]})
        self.assertIn("&lt;script&gt;alert", html)
        self.assertIn("&lt;img src=x onerror=", html)
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertNotIn('<img src=x onerror="alert(1)">', html)
        self.assertIn("**Elements**", html)
        self.assertEqual(html.count("<li>"), 2)

    def test_invalid_contracts_fail_with_locations(self) -> None:
        invalid_items = []

        wrong_kind = note_item()
        wrong_kind["kind"] = "custom"
        invalid_items.append((wrong_kind, ".kind must be one of"))

        unknown_field = note_item()
        unknown_field["style"] = "color:red"
        invalid_items.append((unknown_field, "unknown fields: style"))

        missing_language = note_item()
        missing_language["label"] = {"en": "Purpose"}
        invalid_items.append((missing_language, ".label.zh must be a non-empty string"))

        empty_item = {"kind": "purpose", "label": {"en": "Purpose", "zh": "目的"}}
        invalid_items.append((empty_item, "requires body or items"))

        mismatch = note_item()
        mismatch.pop("body")
        mismatch["items"] = {"en": ["one", "two"], "zh": ["一"]}
        invalid_items.append((mismatch, "language arrays must have the same number"))

        for item, marker in invalid_items:
            with self.subTest(marker=marker):
                spec = base_spec()
                spec["sections"][0]["note_items"] = [item]  # type: ignore[index]
                with self.assertRaisesRegex(RenderError, marker):
                    validate_spec(spec)

        spec = base_spec()
        spec["sections"][0]["note_items"] = {"kind": "purpose"}  # type: ignore[index]
        with self.assertRaisesRegex(RenderError, "must be an array of tables"):
            validate_spec(spec)

    def test_normalize_and_toml_round_trip_preserve_note_items(self) -> None:
        spec = base_spec()
        list_item = note_item("elements")
        list_item.pop("body")
        list_item["items"] = {"en": ["one", "two"], "zh": ["一", "二"]}
        spec["sections"][0]["note_items"].append(list_item)  # type: ignore[index,union-attr]
        manifest = normalize_spec(spec)
        dumped = dump_toml_spec(manifest)
        parsed = tomllib.loads(dumped)
        validate_spec(parsed)
        self.assertEqual(parsed["sections"][0]["note_items"], manifest["sections"][0]["note_items"])
        self.assertEqual(
            parsed["sections"][0]["components"][0]["note_items"],
            manifest["sections"][0]["components"][0]["note_items"],
        )

    def test_collection_expansion_preserves_explicit_note_items(self) -> None:
        with tempfile.TemporaryDirectory(prefix="taffish-note-collection-") as temp:
            root = Path(temp)
            (root / "plots.tsv").write_text("id\timage\np1\tp1.svg\n", encoding="utf-8")
            (root / "p1.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 2"><path d="M0 0h2v2H0z"/></svg>\n',
                encoding="utf-8",
            )
            spec = base_spec()
            collection = {
                "type": "plot_collection",
                "id": "plots",
                "source": "plots.tsv",
                "note_items": [note_item("provenance")],
            }
            spec["sections"][0]["components"] = [collection]  # type: ignore[index]
            validate_spec(spec)
            manifest = normalize_spec(spec, root=root)
            expanded = manifest["sections"][0]["components"][0]
            self.assertEqual(expanded["type"], "plot_card")
            self.assertEqual(expanded["note_items"], collection["note_items"])

    def test_explain_reports_counts_and_kinds(self) -> None:
        explanation = explain_manifest(normalize_spec(base_spec()))
        section = explanation["sections"][0]
        component = section["components"][0]
        self.assertEqual(section["note_item_count"], 1)
        self.assertEqual(section["note_item_kinds"], ["question"])
        self.assertEqual(component["note_item_count"], 1)
        self.assertEqual(component["note_item_kinds"], ["reading"])

    def test_lint_warns_for_long_legacy_notes_only(self) -> None:
        spec = base_spec()
        section = spec["sections"][0]  # type: ignore[index]
        section.pop("note_items")
        section["note"] = {"en": "E" * 701, "zh": "中" * 241}
        issues, _ = lint_spec(spec)
        messages = [issue.message for issue in issues]
        self.assertTrue(any("long note (701 characters" in message for message in messages))
        self.assertTrue(any("long note (241 characters" in message for message in messages))

        structured = deepcopy(spec)
        structured["sections"][0]["note_items"] = [note_item("summary")]  # type: ignore[index]
        issues, _ = lint_spec(structured)
        self.assertFalse(any("long note" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
