"""主命令与子命令 help 的独立离线检查，先检查退出码再检查稳定字段。"""
import os
from smoke_support import run

renderer = os.environ.get("TAFFISH_REPORT_RENDER_BIN", "report-render")
for args, required in ((["--help"], ["render", "validate-spec", "inspect-html"]),
                       (["render", "--help"], ["--spec", "--root", "--out", "--validate"])):
    output = run(renderer, *args, stage="help " + " ".join(args)).stdout
    for marker in required:
        if marker not in output:
            raise SystemExit(f"HELP_SMOKE_FAILED args={args!r} missing={marker}")
print("CLI_HELP_SMOKE_OK")
