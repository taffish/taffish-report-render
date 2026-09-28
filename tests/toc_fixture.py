"""人工目录验收素材；不包含客户数据，不作科学结果声明。"""
from pathlib import Path
from taffish_report_render.cli import dump_toml_spec


def text(zh, en):
    return {"zh": zh, "en": en}


def make_spec(targets=19, windows=10):
    spec = {"template": "taffish-flow-report", "schema_version": "0.1",
            "project": {"title": text("人工长报告：目录导航验收", "Synthetic long report: navigation acceptance")},
            "sections": []}
    def section(ident, title, parent=None):
        node = {"id": ident, "title": title, "components": []}
        if parent:
            node["toc"] = {"parent": parent}
        spec["sections"].append(node)
        return node
    intro = section("overview", text("1. 总览", "1. Overview"))
    intro["components"] = [{"id": "intro-text", "type": "code_file", "source": "methods.txt", "title": text("1.1 方法", "1.1 Methods")}]
    positions = section("positions", text("4. 候选差异具体在哪里", "4. Candidate differences"))
    positions["toc"] = {"collapsed": True}
    basis = section("basis", text("4.0 判定依据", "4.0 Evidence basis"), "positions")
    basis["components"] = [{"id": "basis-text", "type": "code_file", "source": "methods.txt", "toc": {"visible": False}}]
    section("focused_targets", text("4.1 有候选差异的目标", "4.1 Targets with candidate differences"), "positions")
    for i in range(1, targets + 1):
        ident = f"candidate_{i:02d}"
        node = section(ident, text(f"4.1.{i} 目标{i}的完整名称与说明" + "长标题" * 12,
                                   f"4.1.{i} Full description of target {i} " + "LONG_IDENTIFIER_" * 10), "focused_targets")
        node["toc"]["title"] = text(f"4.1.{i} 目标{i}", f"4.1.{i} Target {i}")
        node["components"].append({"id": f"{ident}_score", "type": "plot_card", "image": "score.svg", "layout": "wide",
                                   "title": text("评分示意", "Illustrative score"), "toc": {"visible": False}})
        for j in range(1, windows + 1):
            node["components"].append({"id": f"{ident}_window_{j:02d}", "type": "sequence_alignment", "source": "alignment.fa",
                                       "title": text(f"局部比对窗口{j}", f"Alignment window {j}"), "toc": {"visible": False}})
    other = section("other_targets", text("4.2 其他目标", "4.2 Other targets"), "positions")
    other["components"] = [{"id": "other-text", "type": "code_file", "source": "methods.txt", "toc": {"title": text("说明", "Notes")}}]
    return spec


def write_fixture(root: Path, targets=19, windows=10):
    root.mkdir(parents=True, exist_ok=False)
    (root / "methods.txt").write_text("SYNTHETIC ONLY\nNo customer data. No scientific inference.\n" * 8)
    (root / "alignment.fa").write_text(">reference\nACGTACGTACGTACGT\n>target\nACGTACGTTCGTACGT\n")
    (root / "score.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><rect x="20" y="20" width="240" height="65" fill="#298c80"/><text x="20" y="110">Synthetic score only</text></svg>')
    spec = make_spec(targets, windows)
    (root / "report.toml").write_text(dump_toml_spec(spec), encoding="utf-8")
    return spec


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--targets", type=int, default=19)
    parser.add_argument("--windows", type=int, default=10)
    args = parser.parse_args()
    write_fixture(args.outdir, args.targets, args.windows)
