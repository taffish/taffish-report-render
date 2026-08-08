#!/usr/bin/env python3
"""Deterministic image MIME and rendered-HTML contract coverage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from taffish_report_render.cli import (
    RenderError,
    data_uri,
    html_summary,
    main_document_image_data_uri_mimes,
    mime_type_for_path,
    validate_html_file,
)


CORE_IMAGE_MIMES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def minimal_report_html(extra_image: str = "") -> str:
    return f"""<!doctype html>
<html data-template="taffish-flow-report">
<head><style>.report-shell {{ display: block; }}</style></head>
<body>
<div class="report-shell report-sidebar report-main brand-link language-switch
section-nav sidebar-external hero section report-footer">
<img src="data:image/png;base64,AA==" alt="logo">
{extra_image}
</div>
<script>window.example = '<img src="data:application/octet-stream;base64,AA==">';</script>
</body>
</html>
"""


class ImageMimeContractTests(unittest.TestCase):
    def test_core_image_types_do_not_depend_on_host_mime_database(self) -> None:
        with patch("taffish_report_render.cli.mimetypes.guess_type", return_value=(None, None)):
            for suffix, expected in CORE_IMAGE_MIMES.items():
                with self.subTest(suffix=suffix):
                    self.assertEqual(mime_type_for_path(Path("figure" + suffix.upper())), expected)

    def test_unknown_type_uses_host_guess_then_octet_stream_fallback(self) -> None:
        with patch("taffish_report_render.cli.mimetypes.guess_type", return_value=("image/avif", None)):
            self.assertEqual(mime_type_for_path(Path("figure.avif")), "image/avif")
        with patch("taffish_report_render.cli.mimetypes.guess_type", return_value=(None, None)):
            self.assertEqual(mime_type_for_path(Path("payload.unknown")), "application/octet-stream")

    def test_data_uri_uses_exact_core_prefixes_without_host_registration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="taffish-mime-unit-") as temp:
            root = Path(temp)
            with patch("taffish_report_render.cli.mimetypes.guess_type", return_value=(None, None)):
                for suffix, expected in CORE_IMAGE_MIMES.items():
                    with self.subTest(suffix=suffix):
                        path = root / ("figure" + suffix)
                        path.write_bytes(b"real fixture bytes are covered by smoke")
                        self.assertTrue(data_uri(path).startswith(f"data:{expected};base64,"))

    def test_main_document_scan_ignores_script_literals(self) -> None:
        html = minimal_report_html('<img src="data:image/webp;base64,AA==" alt="figure">')
        self.assertEqual(main_document_image_data_uri_mimes(html), ["image/png", "image/webp"])

    def test_inspect_summary_reports_non_image_img_data_uri(self) -> None:
        with tempfile.TemporaryDirectory(prefix="taffish-mime-summary-") as temp:
            report = Path(temp) / "report.html"
            report.write_text(
                minimal_report_html(
                    '<img src="data:application/octet-stream;base64,AA==" alt="bad figure">'
                ),
                encoding="utf-8",
            )
            summary = html_summary(report)
            self.assertEqual(summary["data_image_count"], 1)
            self.assertEqual(summary["non_image_img_data_uri_count"], 1)

    def test_validate_html_rejects_non_image_mime_on_image_element(self) -> None:
        with tempfile.TemporaryDirectory(prefix="taffish-mime-validation-") as temp:
            good = Path(temp) / "good.html"
            bad = Path(temp) / "bad.html"
            good.write_text(
                minimal_report_html('<img src="data:image/webp;base64,AA==" alt="figure">'),
                encoding="utf-8",
            )
            bad.write_text(
                minimal_report_html(
                    '<img src="data:application/octet-stream;base64,AA==" alt="bad figure">'
                ),
                encoding="utf-8",
            )
            validate_html_file(good)
            with self.assertRaisesRegex(
                RenderError,
                "image element uses non-image data URI MIME: application/octet-stream",
            ):
                validate_html_file(bad)


if __name__ == "__main__":
    unittest.main()
