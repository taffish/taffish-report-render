#!/usr/bin/env python3
"""Regression contracts for the 0.3.3 compact-media layout fixture."""

from __future__ import annotations

import importlib.util
import tempfile
import tomllib
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = APP_ROOT / "python" / "taffish_report_render" / "assets" / "report.css"
FIXTURE_BUILDER = APP_ROOT / "tests" / "build-structured-notes-fixture.py"


def load_fixture_builder():
    spec = importlib.util.spec_from_file_location("structured_notes_fixture", FIXTURE_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load fixture builder: {FIXTURE_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise AssertionError(f"not a valid PNG fixture: {path}")
    return int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")


def webp_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if payload[:4] != b"RIFF" or payload[8:12] != b"WEBP":
        raise AssertionError(f"not a valid WebP fixture: {path}")
    kind = payload[12:16]
    if kind == b"VP8X":
        return 1 + int.from_bytes(payload[24:27], "little"), 1 + int.from_bytes(payload[27:30], "little")
    if kind == b"VP8L" and payload[20] == 0x2F:
        bits = int.from_bytes(payload[21:25], "little")
        return 1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)
    raise AssertionError(f"unsupported WebP fixture encoding: {kind!r}")


def css_block(css: str, marker: str) -> str:
    start = css.index(marker)
    opening = css.index("{", start)
    depth = 0
    for index in range(opening, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[start : index + 1]
    raise AssertionError(f"unterminated CSS block: {marker}")


class ResponsiveMediaFixtureTests(unittest.TestCase):
    def test_true_size_three_figure_fixture(self) -> None:
        builder = load_fixture_builder()
        with tempfile.TemporaryDirectory(prefix="taffish-responsive-media-") as temp:
            root = Path(temp)
            report_spec = root / "report.toml"
            builder.build(root, report_spec)

            figures = root / "03_results" / "figures"
            self.assertEqual(webp_dimensions(figures / "literature-landscape.webp"), (2500, 2101))
            self.assertEqual(png_dimensions(figures / "literature-landscape-alt.png"), (1660, 1130))
            self.assertEqual(png_dimensions(figures / "literature-portrait.png"), (1000, 1660))

            manifest = tomllib.loads(report_spec.read_text(encoding="utf-8"))
            media = [
                component
                for section in manifest["sections"]
                for component in section.get("components", [])
                if component.get("type") == "plot_card" and component.get("layout") == "media"
            ]
            self.assertEqual([component["id"] for component in media], [
                "media-auto-webp",
                "media-compact-portrait",
                "media-compact-landscape",
            ])
            self.assertTrue(all(component["zoom"] is True for component in media))
            self.assertTrue(all(len(component["note_items"]) == 5 for component in media))
            self.assertEqual(media[0].get("media_note_layout", "auto"), "auto")
            self.assertEqual([component.get("media_note_layout") for component in media[1:]], ["compact", "compact"])

    def test_compact_single_column_and_print_css_contract(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        container = css_block(css, "@container plot-media-stack (max-width: 900px)")
        fallback = css_block(css, "@supports not (container-type: inline-size)")
        printing = css_block(css, "@media print")

        for block in (container, fallback):
            self.assertIn("max-height: min(720px, 85vh);", block)
            self.assertIn("width: auto;", block)
            self.assertIn("max-width: 100%;", block)
            self.assertIn("min-height: 0;", block)
            self.assertIn("place-items: center;", block)
            self.assertNotIn("max-height: none;", block)

        self.assertIn("max-height: 180mm;", printing)
        self.assertIn("width: auto;", printing)
        self.assertIn("object-fit: contain;", printing)
        self.assertIn("align-items: stretch;", css)
        self.assertIn("align-self: stretch;", css)
        self.assertIn("box-sizing: border-box;", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
