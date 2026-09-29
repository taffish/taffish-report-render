"""创建无客户数据的目录交互浏览器素材；所有输出进入新的显式目录。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shlex

from toc_fixture import text, write_fixture
from smoke_support import run
from taffish_report_render.cli import dump_toml_spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--wrapper", action="store_true", help="使用 TAFFISH 0.11.0 的 literal argv quoting")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=False)
    assets = args.outdir / "assets"
    long = write_fixture(assets)
    simple = {"template": "taffish-flow-report", "project": {"title": text("目录阅读回归", "Navigation regression")},
              "sections": [{"id": ident, "title": text(ident, ident), "components": [
                  {"id": f"{ident}{i}", "type": "plot_card", "image": "score.svg", "layout": "wide",
                   "title": text(f"{ident}{i}", f"{ident}{i}")} for i in (1, 2)]} for ident in ("alpha", "beta")]}
    hidden, title_only, empty = deepcopy(simple), deepcopy(simple), deepcopy(simple)
    hidden["sections"][0]["components"][1]["toc"] = {"visible": False}
    title_only["sections"][0]["toc"] = {"title": text("短标题", "Short title")}
    empty["sections"][0]["toc"] = {}
    manual = deepcopy(long)
    manual["toc"] = {"interaction": "manual"}
    manual_simple = deepcopy(simple)
    manual_simple["toc"] = {"interaction": "manual"}
    long_titles = deepcopy(long)
    for section in long_titles["sections"]:
        section.get("toc", {}).pop("title", None)
    cases = {"legacy": simple, "hide-only": hidden, "title-only": title_only, "empty-toc": empty,
             "follow": long, "manual": manual, "manual-simple": manual_simple, "long-toc-titles": long_titles}
    for name, spec in cases.items():
        spec_path = args.outdir / f"{name}.toml"
        spec_path.write_text(dump_toml_spec(spec), encoding="utf-8")
        command = ["render", "--spec", str(spec_path), "--root", str(assets),
                   "--out", str(args.outdir / name / "report.html"), "--validate"]
        if args.wrapper: command = [shlex.quote(value) for value in command]
        run(args.renderer, *command, stage=f"browser-fixture-{name}")
    (args.outdir / "cases.json").write_text(json.dumps(list(cases)) + "\n")
    print(f"TOC_BROWSER_FIXTURES_OK cases={len(cases)} synthetic_only=true")


if __name__ == "__main__": main()
