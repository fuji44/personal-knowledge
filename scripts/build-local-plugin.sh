#!/usr/bin/env bash
set -euo pipefail

# Build a local personal-knowledge plugin directory with a custom MCP endpoint URL.
# Useful when connecting to a non-default port, LAN IP, or remote/OAuth endpoint.
#
# Usage:
#   ./scripts/build-local-plugin.sh [MCP_URL] [OUTPUT_DIR]
#   BASIC_MEMORY_MCP_URL="http://192.168.1.xxx:48000/mcp" ./scripts/build-local-plugin.sh
#
# Examples:
#   ./scripts/build-local-plugin.sh "http://192.168.1.xxx:48000/mcp"
#   ./scripts/build-local-plugin.sh "https://bm.example.com/mcp" "$HOME/.gemini/config/plugins/personal-knowledge"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  echo "Usage: $0 [MCP_URL] [OUTPUT_DIR]" >&2
  echo "  (or set BASIC_MEMORY_MCP_URL environment variable)" >&2
  echo "Example: $0 'http://192.168.1.xxx:48000/mcp'" >&2
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

MCP_URL="${1:-${BASIC_MEMORY_MCP_URL:-}}"
OUTPUT_DIR="${2:-${REPO_ROOT}/dist/personal-knowledge}"

if [[ -z "${MCP_URL}" ]]; then
  usage
  exit 1
fi

SHORT_SHA="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || true)"

python3 - "${REPO_ROOT}/plugins/personal-knowledge" "${OUTPUT_DIR}" "${MCP_URL}" "${SHORT_SHA}" <<'PY'
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

src = Path(sys.argv[1]).resolve()
raw_dest = Path(sys.argv[2]).expanduser()
if raw_dest.is_symlink():
    raise SystemExit(f"Error: Refusing symlink OUTPUT_DIR: {raw_dest}")
dest = raw_dest.resolve()
mcp_url = sys.argv[3]
short_sha = sys.argv[4].strip()
build_meta = f"local.{short_sha}" if short_sha else "local"

parsed = urlparse(mcp_url)
if parsed.scheme not in ("http", "https") or not parsed.netloc:
    raise SystemExit(f"Error: MCP_URL must be a valid http(s):// URL with host (got: {mcp_url})")

home_dir = Path.home().resolve()
if dest == src or dest == Path("/") or dest == home_dir or dest in src.parents or src in dest.parents:
    raise SystemExit(f"Error: Refusing unsafe OUTPUT_DIR: {dest}")

if dest.is_file():
    raise SystemExit(f"Error: OUTPUT_DIR must not be an existing file: {dest}")

if dest.exists():
    shutil.rmtree(dest)

dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def rewrite_url(filename: str, key: str) -> None:
    path = dest / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, entry in data.get("mcpServers", {}).items():
        if filename == "mcp_config.json":
            data["mcpServers"][name] = {"url": mcp_url}
        else:
            entry[key] = mcp_url
    if filename == ".claude-plugin/plugin.json":
        data.pop("userConfig", None)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_local_version(filename: str) -> None:
    path = dest / filename
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if isinstance(version, str) and version:
        base_version = version.split("+", 1)[0]
        data["version"] = f"{base_version}+{build_meta}"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


rewrite_url("mcp_config.json", "url")
rewrite_url("mcp.json", "url")
rewrite_url(".claude-plugin/plugin.json", "url")
append_local_version("plugin.json")
append_local_version(".claude-plugin/plugin.json")
PY

echo "Built local plugin at: ${OUTPUT_DIR} (MCP URL: ${MCP_URL})"
