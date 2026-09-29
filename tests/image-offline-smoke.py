#!/usr/bin/env python3
"""Independent offline runtime smoke for a built release image."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from smoke_support import run


APP_ROOT = Path(__file__).resolve().parents[1]
RENDERER = os.environ.get("TAFFISH_REPORT_RENDER_BIN", "/usr/local/bin/report-render")
FIXTURE_BUILDER = APP_ROOT / "tests" / "build-image-mime-fixture.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def build_and_render(root: Path, profile: str) -> tuple[Path, dict[str, object]]:
    spec = root / "report.toml"
    report = root / "04_reports" / "taffish_report.html"
    run(
        sys.executable,
        str(FIXTURE_BUILDER),
        "--root",
        str(root),
        "--spec",
        str(spec),
        "--profile",
        profile,
    )
    run(RENDERER, "validate-spec", "--spec", str(spec), "--root", str(root))
    run(RENDERER, "lint", "--strict", "--spec", str(spec), "--root", str(root))
    run(
        RENDERER,
        "render",
        "--spec",
        str(spec),
        "--root",
        str(root),
        "--out",
        str(report),
        "--force",
        "--validate",
    )
    inspection = json.loads(run(RENDERER, "inspect-html", str(report), "--validate", "--json").stdout)
    return report, inspection


def check_sidecars(root: Path, expected_images: int) -> None:
    index = root / "04_reports" / "report_files.tsv"
    rows = [line.split("\t") for line in index.read_text(encoding="utf-8").splitlines()[1:]]
    images = [row for row in rows if row and row[0] == "image"]
    require(len(images) == expected_images, f"expected {expected_images} image sidecars, got {len(images)}")
    require(all(len(row) >= 6 and row[5] == "ok" for row in images), "image sidecar status is not ok")


def main() -> int:
    require(
        run(RENDERER, "--version").stdout.strip() == "taffish-report-render 0.4.1-r1",
        "release version mismatch",
    )
    components = run(RENDERER, "components").stdout
    for component in ("plot_card", "native_subreport", "structure_viewer", "genome_browser"):
        require(component in components, f"missing component: {component}")
    schema = json.loads(run(RENDERER, "schema").stdout)
    schema_text = json.dumps(schema)
    for field in ("note_items", "media_image_ratio", "media_note_layout", "boundary"):
        require(field in schema_text, f"missing schema field: {field}")

    unit = run(
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(APP_ROOT / "tests"),
        "-p",
        "test_*.py",
    )
    require("Ran " in unit.stderr and "OK" in unit.stderr, "unit suite did not complete")

    with tempfile.TemporaryDirectory(prefix="taffish-image-offline-smoke-") as temp:
        base = Path(temp)
        core_root = base / "core"
        core_report, core_inspection = build_and_render(core_root, "core")
        core_html = core_report.read_text(encoding="utf-8")
        core_counts = {
            "data:image/png;base64,": 2,
            "data:image/jpeg;base64,": 1,
            "data:image/webp;base64,": 1,
            "data:image/svg+xml;base64,": 1,
            "data:application/octet-stream;base64,": 0,
        }
        for marker, expected in core_counts.items():
            require(core_html.count(marker) == expected, f"core {marker} count mismatch")
        require(core_inspection["data_image_count"] == 5, "core data_image_count must be 5")
        require(core_inspection["non_image_img_data_uri_count"] == 0, "core image MIME diagnostic failed")
        check_sidecars(core_root, 4)

        bad_report = core_root / "04_reports" / "invalid-image-mime.html"
        bad_report.write_text(
            core_html.replace("data:image/webp;base64,", "data:application/octet-stream;base64,", 1),
            encoding="utf-8",
        )
        rejected = run(RENDERER, "validate-html", str(bad_report), check=False)
        require(rejected.returncode != 0, "validate-html accepted a non-image MIME")
        require(
            "image element uses non-image data URI MIME: application/octet-stream" in rejected.stderr,
            "validate-html emitted the wrong MIME diagnostic",
        )
        bad_inspection = json.loads(run(RENDERER, "inspect-html", str(bad_report), "--json").stdout)
        require(bad_inspection["data_image_count"] == 4, "negative data_image_count must be 4")
        require(bad_inspection["non_image_img_data_uri_count"] == 1, "negative MIME count must be 1")

        fungal_root = base / "fungal-equivalent"
        fungal_report, fungal_inspection = build_and_render(fungal_root, "fungal-equivalent")
        fungal_html = fungal_report.read_text(encoding="utf-8")
        fungal_counts = {
            "data:image/png;base64,": 3,
            "data:image/svg+xml;base64,": 4,
            "data:image/webp;base64,": 1,
            "data:application/octet-stream;base64,": 0,
        }
        for marker, expected in fungal_counts.items():
            require(fungal_html.count(marker) == expected, f"fungal {marker} count mismatch")
        require(fungal_inspection["data_image_count"] == 8, "fungal data_image_count must be 8")
        require(
            fungal_inspection["non_image_img_data_uri_count"] == 0,
            "fungal image MIME diagnostic failed",
        )
        check_sidecars(fungal_root, 7)

    print("IMAGE_OFFLINE_SMOKE_OK version=0.4.1-r1 core_images=5 fungal_images=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
