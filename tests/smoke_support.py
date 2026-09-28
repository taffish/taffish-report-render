"""独立 smoke 的有界失败日志；保留子进程退出状态，不吞掉真正诊断。"""
import shlex
import subprocess
import sys

LOG_TAIL_CHARS = 8000


def run(*args: str, check: bool = True, stage: str | None = None) -> subprocess.CompletedProcess[str]:
    command = tuple(map(str, args))
    label = (stage or shlex.join(command))[:500]
    try:
        result = subprocess.run(command, text=True, capture_output=True)
    except OSError as exc:
        print(f"SMOKE_CHILD_FAILED stage={label} exit=127\nstderr tail:\n{str(exc)[-LOG_TAIL_CHARS:]}", file=sys.stderr)
        raise SystemExit(127) from None
    if check and result.returncode:
        print(f"SMOKE_CHILD_FAILED stage={label} exit={result.returncode}", file=sys.stderr)
        for stream in ("stdout", "stderr"):
            print(f"{stream} tail (max {LOG_TAIL_CHARS} chars):\n{getattr(result, stream)[-LOG_TAIL_CHARS:]}", file=sys.stderr)
        raise SystemExit(result.returncode if result.returncode > 0 else 128 - result.returncode)
    return result
