"""独立离线 CLI 验收，fresh scratch，无生产 bind；失败回放 subprocess 日志。"""
import json
import os
import tempfile
from pathlib import Path
from toc_fixture import write_fixture
from smoke_support import run as run_child


def run(*args):
    return run_child(os.environ.get("TAFFISH_REPORT_RENDER_BIN", "report-render"), *args, stage=str(args[0])).stdout


def main():
    with tempfile.TemporaryDirectory(prefix="taffish-toc-") as tmp:
        root = Path(tmp) / "fixture"
        write_fixture(root, 19, 10)
        spec = root / "report.toml"
        run("validate-spec", "--spec", spec, "--root", root)
        run("lint", "--spec", spec, "--root", root, "--strict", "--json", "--fail-on-warn")
        before = json.loads(run("migrate", "--spec", spec, "--root", root, "--format", "json"))
        json_path = root / "canonical.json"
        json_path.write_text(json.dumps(before))
        toml_path = root / "roundtrip.toml"
        toml_path.write_text(run("migrate", "--spec", json_path, "--root", root, "--format", "toml"))
        assert before == json.loads(run("migrate", "--spec", toml_path, "--root", root, "--format", "json"))
        explained = json.loads(run("explain", "--spec", spec, "--root", root, "--json"))
        report = root / "output" / "report.html"
        run("render", "--spec", spec, "--root", root, "--out", report, "--validate")
        inspected = json.loads(run("inspect-html", report, "--validate", "--json"))
        assert inspected["toc"] == explained["toc"]
        assert inspected["toc"]["interaction"] == "follow"
        assert inspected["toc"]["version"] == 2
        assert inspected["toc"]["hidden_count"] == 210
        assert inspected["toc"]["visible_count"] == 29
        assert inspected["data_image_count"] == 20
        assert explained["component_count"] == 212
        assert json.loads((report.parent / "report_toc.json").read_text()) == inspected["toc"]
        run("list-assets", report, "--json")
        before["toc"] = {"interaction": "manual"}
        json_path.write_text(json.dumps(before))
        toml_path.write_text(run("migrate", "--spec", json_path, "--root", root, "--format", "toml"))
        assert before == json.loads(run("migrate", "--spec", toml_path, "--root", root, "--format", "json"))
        manual_report = root / "manual" / "report.html"
        run("render", "--spec", toml_path, "--root", root, "--out", manual_report, "--validate")
        manual = json.loads(run("inspect-html", manual_report, "--validate", "--json"))
        assert manual["toc"]["interaction"] == "manual"
        assert manual["toc"]["nodes"] == inspected["toc"]["nodes"]
        assert 'class="toc-controls"' not in report.read_text()
        assert 'class="toc-controls"' in manual_report.read_text()
    print("TOC_OFFLINE_SMOKE_OK targets=19 windows=190 hidden=210 visible=29 components=212")


if __name__ == "__main__": main()
