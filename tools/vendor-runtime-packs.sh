#!/usr/bin/env bash
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
app_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
runtime_root="$app_root/python/taffish_report_render/runtime_packs"

ngl_version="${TAFFISH_REPORT_RENDER_NGL_NPM_VERSION:-2.4.0}"
igv_version="${TAFFISH_REPORT_RENDER_IGV_NPM_VERSION:-latest}"
runtime="all"

usage() {
    cat <<'EOF'
Usage:
  tools/vendor-runtime-packs.sh [--runtime all|ngl|igv]

Maintainer-only helper for vendoring browser runtime packs into the renderer
source tree. Normal report generation and tests do not call this script.

Environment:
  TAFFISH_REPORT_RENDER_NGL_NPM_VERSION   NGL npm version. Default: 2.4.0
  TAFFISH_REPORT_RENDER_IGV_NPM_VERSION   IGV npm version. Default: latest
  HTTP_PROXY / HTTPS_PROXY                Optional proxy for restricted networks.

Outputs:
  python/taffish_report_render/runtime_packs/ngl/ngl.js
  python/taffish_report_render/runtime_packs/igv/igv.min.js
  VERSION, SOURCE.json and LICENSE beside each runtime.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --runtime)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --runtime requires all, ngl, or igv" >&2
                exit 2
            fi
            runtime="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$runtime" in
    all|ngl|igv) ;;
    *)
        echo "ERROR: --runtime must be all, ngl, or igv" >&2
        exit 2
        ;;
esac

if [ "${TAFFISH_REPORT_RENDER_USE_SYSTEM_PROXY:-1}" != "0" ] && command -v scutil >/dev/null 2>&1; then
    proxy_info=$(scutil --proxy 2>/dev/null || true)
    if [ -n "$proxy_info" ] && [ -z "${HTTPS_PROXY:-}${https_proxy:-}" ]; then
        https_enable=$(printf '%s\n' "$proxy_info" | awk '/HTTPSEnable/{print $3; exit}')
        https_host=$(printf '%s\n' "$proxy_info" | awk '/HTTPSProxy/{print $3; exit}')
        https_port=$(printf '%s\n' "$proxy_info" | awk '/HTTPSPort/{print $3; exit}')
        if [ "$https_enable" = "1" ] && [ -n "$https_host" ] && [ -n "$https_port" ]; then
            export HTTPS_PROXY="http://${https_host}:${https_port}"
            export https_proxy="$HTTPS_PROXY"
            echo "[VENDOR] use macOS HTTPS proxy: ${https_host}:${https_port}"
        fi
    fi
    if [ -n "$proxy_info" ] && [ -z "${HTTP_PROXY:-}${http_proxy:-}" ]; then
        http_enable=$(printf '%s\n' "$proxy_info" | awk '/HTTPEnable/{print $3; exit}')
        http_host=$(printf '%s\n' "$proxy_info" | awk '/HTTPProxy/{print $3; exit}')
        http_port=$(printf '%s\n' "$proxy_info" | awk '/HTTPPort/{print $3; exit}')
        if [ "$http_enable" = "1" ] && [ -n "$http_host" ] && [ -n "$http_port" ]; then
            export HTTP_PROXY="http://${http_host}:${http_port}"
            export http_proxy="$HTTP_PROXY"
            echo "[VENDOR] use macOS HTTP proxy: ${http_host}:${http_port}"
        fi
    fi
fi

fetch_runtime() {
    local package="$1"
    local version_spec="$2"
    local runtime_kind="$3"
    local out_js="$4"
    mkdir -p "$(dirname "$out_js")"
    python3 - "$package" "$version_spec" "$runtime_kind" "$out_js" <<'PY'
import base64
import hashlib
import json
import pathlib
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request

package, version_spec, runtime_kind, out_js = sys.argv[1:5]
out_path = pathlib.Path(out_js)
metadata_url = (
    f"https://registry.npmjs.org/{urllib.parse.quote(package, safe='')}/latest"
    if version_spec == "latest"
    else f"https://registry.npmjs.org/{urllib.parse.quote(package, safe='')}/{urllib.parse.quote(version_spec, safe='')}"
)
bundle_candidates = {
    "ngl": ("package/dist/ngl.js",),
    "igv": ("package/dist/igv.min.js", "package/dist/igv.js"),
}[runtime_kind]

with urllib.request.urlopen(metadata_url, timeout=60) as handle:
    manifest = json.loads(handle.read().decode("utf-8"))
version = manifest["version"]
tarball = manifest["dist"]["tarball"]
integrity = manifest.get("dist", {}).get("integrity", "")
with urllib.request.urlopen(tarball, timeout=120) as handle:
    archive_data = handle.read()

if integrity.startswith("sha512-"):
    expected = base64.b64decode(integrity.split("-", 1)[1])
    got = hashlib.sha512(archive_data).digest()
    if got != expected:
        raise SystemExit(f"{package} tarball failed sha512 integrity check")

with tempfile.TemporaryDirectory() as tmp:
    archive = pathlib.Path(tmp) / f"{package}.tgz"
    archive.write_bytes(archive_data)
    with tarfile.open(archive, "r:gz") as handle:
        names = set(handle.getnames())
        bundle_name = next((candidate for candidate in bundle_candidates if candidate in names), "")
        if not bundle_name:
            raise SystemExit(f"{package} package did not contain: {', '.join(bundle_candidates)}")
        data = handle.extractfile(bundle_name).read()
        sample = data[:2_000_000].decode("utf-8", errors="ignore")
        if runtime_kind == "ngl":
            if len(data) < 100_000 or "NGL" not in sample or "Stage" not in sample:
                raise SystemExit("NGL bundle does not look valid")
            externalized = (
                'require("three")',
                "require('three')",
                'define(["exports","three"',
                "define(['exports','three'",
                ".NGL={},t.three,t.chroma,t.signalsWrapper,t.sprintfJs",
            )
            if any(marker in sample for marker in externalized):
                raise SystemExit("NGL bundle is dependency-externalized; use standalone dist/ngl.js")
        if runtime_kind == "igv":
            if len(data) < 100_000 or "igv" not in sample.lower() or "createBrowser" not in sample:
                raise SystemExit("IGV bundle does not look valid")
        out_path.write_bytes(data)
        out_path.with_name("VERSION").write_text(version + "\n", encoding="utf-8")
        out_path.with_name("SOURCE.json").write_text(
            json.dumps(
                {
                    "package": package,
                    "version": version,
                    "metadata_url": metadata_url,
                    "tarball": tarball,
                    "integrity": integrity,
                    "bundle": bundle_name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        license_name = "package/LICENSE"
        if license_name in names:
            out_path.with_name("LICENSE").write_bytes(handle.extractfile(license_name).read())
PY
}

if [ "$runtime" = "all" ] || [ "$runtime" = "ngl" ]; then
    echo "[VENDOR] NGL ${ngl_version}"
    fetch_runtime "ngl" "$ngl_version" "ngl" "$runtime_root/ngl/ngl.js"
fi

if [ "$runtime" = "all" ] || [ "$runtime" = "igv" ]; then
    echo "[VENDOR] IGV ${igv_version}"
    fetch_runtime "igv" "$igv_version" "igv" "$runtime_root/igv/igv.min.js"
fi

echo "[VENDOR] done"
