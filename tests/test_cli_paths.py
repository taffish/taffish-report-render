"""new 的下一步命令需保留宿主 shell 和 TAF ARGV 两层参数边界。"""
import argparse
import contextlib
import io
import shlex
import tempfile
import unittest
from pathlib import Path
from taffish_report_render.cli import command_new


class CLIPathTests(unittest.TestCase):
    def test_new_copyable_next_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("simple", "report with spaces", "中文 报告", "O'Brien $HOME ;$(false)"):
                root = Path(tmp) / name
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    command_new(argparse.Namespace(outdir=root, force=False))
                printed = next(line.removeprefix("render with: ") for line in stream.getvalue().splitlines() if line.startswith("render with: "))
                # First split = invoking shell; joined argv = TAFFISH 0.11.0; second split = generated shell.
                actual = shlex.split(" ".join(shlex.split(printed)[1:]))
                self.assertEqual(actual, ["render", "--spec", str(root / "report.toml"), "--root", str(root),
                                          "--out", str(root / "04_reports/report.html"), "--force", "--validate"])
