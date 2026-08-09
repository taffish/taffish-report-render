#!/usr/bin/env python3
"""Build self-contained NGS-QC and phylogeny smoke inputs."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def padded_html(title: str, body: str, script: str = "") -> str:
    padding = "fixture-payload-" * 8500
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
        + title
        + "</title>"
        + script
        + "</head><body><h1>"
        + title
        + "</h1><p>"
        + body
        + "</p><!--"
        + padding
        + "--></body></html>\n"
    )


def build_ngs(root: Path) -> None:
    html_dir = root / "03_results" / "html"
    seqkit_dir = root / "03_results" / "seqkit"
    plot_dir = root / "03_results" / "plots"
    report_dir = root / "04_reports"
    for directory in (html_dir, seqkit_dir, plot_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (report_dir / "flow_summary.tsv").write_text(
        "metric\tvalue\nstatus\tcomplete\nsamples\t2\npaired_end\tyes\n", encoding="utf-8"
    )
    (report_dir / "module_status.tsv").write_text(
        "module\tstatus\tmessage_en\tmessage_zh\nfastqc\tOK\tRead-level QC complete.\tRead 级质控完成。\nfastp\tOK\tAdapter trimming complete.\t接头过滤完成。\n",
        encoding="utf-8",
    )
    (report_dir / "quality_gates.tsv").write_text(
        "gate\tstatus\tcriterion_en\tcriterion_zh\tmessage_en\tmessage_zh\nreadable\tOK\tEvery declared FASTQ is readable\t所有声明的 FASTQ 可读取\tAll fixture inputs passed.\t所有 fixture 输入均通过。\nadapter\tOK\tAdapter rate is reviewed\t已审阅接头比例\tNo blocking adapter signal.\t没有阻塞性接头信号。\n",
        encoding="utf-8",
    )
    (seqkit_dir / "clean_fastq_stats.tsv").write_text(
        "sample\treads\tbases\tmean_length\tgc_percent\tlong_value\nP1\t1000\t150000\t150\t48.2\t/fixture/output/with/a/very/long/path/that/must/stay/inside/the/table/card/P1.clean.fastq.gz\nP2\t1200\t180000\t150\t49.1\t/fixture/output/with/a/very/long/path/that/must/stay/inside/the/table/card/P2.clean.fastq.gz\nP3\t900\t135000\t150\t47.8\t/fixture/output/with/a/very/long/path/that/must/stay/inside/the/table/card/P3.clean.fastq.gz\n",
        encoding="utf-8",
    )
    (plot_dir / "quality.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 320"><rect width="640" height="320" fill="#f4f8f7"/><path d="M60 260L180 170l120 45 120-135 150 80" fill="none" stroke="#087f74" stroke-width="16"/><text x="60" y="55" font-family="Arial" font-size="28">Read-quality profile</text></svg>\n',
        encoding="utf-8",
    )
    (html_dir / "multiqc_report.html").write_text(
        padded_html("MultiQC smoke report", "Representative multi-module QC payload."), encoding="utf-8"
    )
    (html_dir / "P1.fastp.html").write_text(
        padded_html(
            "fastp smoke report",
            "Representative adapter and quality payload.",
            '<script src="https://opengene.org/plotly-1.2.0.min.js"></script>',
        ),
        encoding="utf-8",
    )
    (html_dir / "P1_fastqc.html").write_text(
        padded_html("FastQC smoke report", "Representative per-read QC payload."), encoding="utf-8"
    )
    (root / "report.toml").write_text(
        '''schema_version = "0.1"
template = "taffish-flow-report"
template_version = "smoke-self-contained"
language_default = "zh"

[project]
flow_name = "ngs-qc-flow"
flow_version = "smoke"
analysis_mode = "self-contained-ngs-qc"
title.en = "Self-contained NGS QC smoke report"
title.zh = "自包含 NGS QC smoke 报告"

[[sections]]
id = "overview"
kind = "overview"
title.en = "Overview"
title.zh = "总览"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/flow_summary.tsv"

[[sections.components]]
type = "status_grid"
id = "module-status"
source = "04_reports/module_status.tsv"

[[sections]]
id = "quality"
kind = "quality_control"
title.en = "Quality gates and clean-read statistics"
title.zh = "质量门和 clean-read 统计"

[[sections.components]]
type = "quality_gate_table"
id = "quality-gates"
source = "04_reports/quality_gates.tsv"

[[sections.components]]
type = "table_preview"
id = "clean-stats"
source = "03_results/seqkit/clean_fastq_stats.tsv"
preview_rows = 1
embed_full = true
max_embed_rows = 100
max_embed_bytes = 200000
title.en = "Clean FASTQ statistics"
title.zh = "Clean FASTQ 统计"

[[sections.components]]
type = "plot_card"
id = "quality-plot"
image = "03_results/plots/quality.svg"
title.en = "Read-quality profile"
title.zh = "Read 质量曲线"

[[sections]]
id = "native-reports"
kind = "native_reports"
title.en = "Native QC reports"
title.zh = "原生 QC 报告"

[[sections.components]]
type = "native_subreport"
id = "multiqc"
kind = "html"
path = "03_results/html/multiqc_report.html"
embed_policy = "always"
title.en = "MultiQC"
title.zh = "MultiQC"

[[sections.components]]
type = "native_subreport"
id = "fastp"
kind = "html"
path = "03_results/html/P1.fastp.html"
embed_policy = "always"
title.en = "fastp"
title.zh = "fastp"

[[sections.components]]
type = "native_subreport"
id = "fastqc"
kind = "html"
path = "03_results/html/P1_fastqc.html"
embed_policy = "always"
title.en = "FastQC"
title.zh = "FastQC"
''',
        encoding="utf-8",
    )


def build_phylogeny(root: Path) -> None:
    tree_dir = root / "03_results" / "tree"
    plot_dir = tree_dir / "plots"
    alignment_dir = root / "03_results" / "alignment"
    report_dir = root / "04_reports"
    for directory in (plot_dir, alignment_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (tree_dir / "tree.nwk").write_text(
        "((sample_A:0.0123,sample_B:0.0188)node1:0.04,(human_P99999_Homo:0.02,yeast_P12345:0.031)node2:0.05)root;\n",
        encoding="utf-8",
    )
    (alignment_dir / "trimmed.fa").write_text(
        ">sample_A\nMKTAYIAKQRQISFVKSHFSRQ\n>human_P99999_Homo\nMKTAYIAKQRQISFVKAHFSRQ\n>yeast_P12345\nMKTAYIAKQRQISFVKSHFARQ\n",
        encoding="utf-8",
    )
    (plot_dir / "tree.png").write_bytes(PNG_1X1)
    (report_dir / "flow_summary.tsv").write_text("metric\tvalue\nstatus\tcomplete\ntips\t4\n", encoding="utf-8")
    (root / "report.toml").write_text(
        '''schema_version = "0.1"
template = "taffish-flow-report"
template_version = "smoke-self-contained"
language_default = "zh"

[project]
flow_name = "phylogeny-flow"
flow_version = "smoke"
analysis_mode = "self-contained-phylogeny"
title.en = "Self-contained phylogeny smoke report"
title.zh = "自包含系统发育 smoke 报告"

[[sections]]
id = "overview"
kind = "overview"
title.en = "Overview"
title.zh = "总览"

[[sections.components]]
type = "dashboard_cards"
id = "summary"
source = "04_reports/flow_summary.tsv"

[[sections]]
id = "tree"
kind = "phylogeny"
title.en = "Tree and alignment"
title.zh = "树和比对"

[[sections.components]]
type = "plot_card"
id = "tree-plot"
image = "03_results/tree/plots/tree.png"
title.en = "Tree plot"
title.zh = "树图"

[[sections.components]]
type = "code_file"
id = "tree-newick"
source = "03_results/tree/tree.nwk"
language = "newick"
copy = true
title.en = "Newick source"
title.zh = "Newick 源文件"

[[sections.components]]
type = "tree_viewer"
id = "tree-inline"
source = "03_results/tree/tree.nwk"
height = 320
title.en = "Interactive tree"
title.zh = "交互树"

[[sections.components]]
type = "sequence_alignment"
id = "trimmed-alignment"
source = "03_results/alignment/trimmed.fa"
format = "fasta"
alphabet = "protein"
max_columns = 80
title.en = "Trimmed alignment"
title.zh = "修剪后比对"
''',
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    build_ngs(args.outdir / "ngs-qc")
    build_phylogeny(args.outdir / "phylogeny")


if __name__ == "__main__":
    main()
