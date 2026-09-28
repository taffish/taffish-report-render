"""故障注入验证 smoke 本身；不是仅测试成功路径。"""
import contextlib
import io
import subprocess
import sys
import unittest
from unittest.mock import patch
from smoke_support import LOG_TAIL_CHARS, run


class SmokeDiagnosticsTests(unittest.TestCase):
    def test_failure_has_bounded_output_and_original_exit(self):
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.assertRaises(SystemExit) as caught:
            run(sys.executable, "-c", "import sys; print('x'*20000+'REAL_STDOUT'); print('y'*20000+'REAL_STDERR',file=sys.stderr); sys.exit(42)", stage="injected-fixture")
        self.assertEqual(caught.exception.code, 42)
        log = stream.getvalue()
        for marker in ("stage=injected-fixture", "exit=42", "REAL_STDOUT", "REAL_STDERR"):
            self.assertIn(marker, log)
        self.assertLess(len(log), 2 * LOG_TAIL_CHARS + 500)

    def test_expected_negative_result_is_returned(self):
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            result = run(sys.executable, "-c", "import sys; print('EXPECTED'); sys.exit(23)", check=False)
        self.assertEqual(result.returncode, 23)
        self.assertIn("EXPECTED", result.stdout)
        self.assertEqual(stream.getvalue(), "")

    def test_signal_and_missing_executable(self):
        with patch("smoke_support.subprocess.run", return_value=subprocess.CompletedProcess(["fake"], -15, "", "terminated")), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            run("fake")
        self.assertEqual(caught.exception.code, 143)
        with patch("smoke_support.subprocess.run", side_effect=FileNotFoundError("missing child")), contextlib.redirect_stderr(io.StringIO()) as stream, self.assertRaises(SystemExit) as caught:
            run("missing", stage="missing-child")
        self.assertEqual(caught.exception.code, 127)
        self.assertIn("stage=missing-child exit=127", stream.getvalue())
