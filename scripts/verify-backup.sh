#!/usr/bin/env bash
set -euo pipefail

# Verify integrity of a basic-memory backup archive (.tar.gz).
#
# Checks:
#   1. Readable as a valid tar.gz stream without corruption
#   2. Member count and total decompressed size within safe bounds
#   3. No path traversal (absolute paths, `..` segments, or NUL bytes)
#   4. No symlinks, hardlinks, device nodes, FIFOs, or SUID/SGID bits
#   5. No derived cache files (.basic-memory/memory.db*) included
#   6. .basic-memory/config.json exists and is valid JSON with a projects map
#   7. At least one Markdown (.md) file is present
#
# Usage:
#   ./scripts/verify-backup.sh <ARCHIVE_FILE>
#   ./scripts/verify-backup.sh --all [BACKUP_DIR]

ENV_FILE="${ENV_FILE:-}"

load_env_default() {
  local key="$1"
  if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
    local val
    val="$(grep -E -- "^[[:space:]]*${key}=" "${ENV_FILE}" | tail -n 1 | cut -d'=' -f2- | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)"
    if [[ -n "${val}" ]]; then
      printf '%s' "${val}"
    fi
  fi
}

usage() {
  echo "Usage:" >&2
  echo "  $0 <ARCHIVE_FILE>" >&2
  echo "  $0 --all [BACKUP_DIR]" >&2
}

verify_single_archive() {
  local archive_path="$1"

  if [[ ! -f "${archive_path}" ]]; then
    echo "Error: Archive file not found: ${archive_path}" >&2
    return 1
  fi

  if [[ ! -s "${archive_path}" ]]; then
    echo "Error: Archive file is empty: ${archive_path}" >&2
    return 1
  fi

  python3 - "${archive_path}" <<'PY'
import json
import os
import sys
import tarfile
import zlib
from pathlib import Path, PurePosixPath

MAX_CONFIG_BYTES = 1_048_576
CHUNK_BYTES = 65_536
archive_path = Path(sys.argv[1])

try:
    MAX_ARCHIVE_BYTES = int(os.environ.get("MAX_ARCHIVE_BYTES", str(512 * 1024 * 1024)))
    MAX_ARCHIVE_MEMBERS = int(os.environ.get("MAX_ARCHIVE_MEMBERS", "50000"))
except ValueError as exc:
    print(f"[FAIL] {archive_path.name}: invalid archive limit environment variable ({exc})", file=sys.stderr)
    raise SystemExit(1)

try:
    with tarfile.open(archive_path, mode="r:gz") as tf:
        config_member = None
        md_count = 0
        total_files = 0
        total_bytes = 0
        member_count = 0

        for m in tf:
            member_count += 1
            if member_count > MAX_ARCHIVE_MEMBERS:
                print(
                    f"[FAIL] {archive_path.name}: too many entries (>{MAX_ARCHIVE_MEMBERS})",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            if not (m.isfile() or m.isdir()):
                print(
                    f"[FAIL] {archive_path.name}: unsupported non-regular entry in archive: {m.name}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            if m.mode & 0o6000:
                print(
                    f"[FAIL] {archive_path.name}: SUID/SGID mode bit not allowed: {m.name}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            if "\x00" in m.name:
                print(
                    f"[FAIL] {archive_path.name}: NUL byte in entry name: {m.name!r}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            norm_name = m.name
            while norm_name.startswith("./"):
                norm_name = norm_name[2:]
            if not norm_name or norm_name == ".":
                continue

            pure = PurePosixPath(norm_name)
            if m.name.startswith("/") or norm_name.startswith("/") or pure.is_absolute() or ".." in pure.parts:
                print(
                    f"[FAIL] {archive_path.name}: unsafe path in archive: {m.name}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            if pure.as_posix().startswith(".basic-memory/memory.db"):
                print(
                    f"[FAIL] {archive_path.name}: SQLite index file must not be included: {m.name}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            if m.isfile():
                if m.size > MAX_ARCHIVE_BYTES - total_bytes:
                    print(
                        f"[FAIL] {archive_path.name}: decompressed size exceeds limit ({MAX_ARCHIVE_BYTES}B)",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)
                total_files += 1
                extracted = tf.extractfile(m)
                if extracted is None:
                    print(
                        f"[FAIL] {archive_path.name}: unable to read entry: {m.name}",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)

                with extracted:
                    if pure.as_posix() == ".basic-memory/config.json":
                        if m.size > MAX_CONFIG_BYTES:
                            print(
                                f"[FAIL] {archive_path.name}: .basic-memory/config.json exceeds size limit ({m.size}B)",
                                file=sys.stderr,
                            )
                            raise SystemExit(1)
                        config_member = extracted.read(MAX_CONFIG_BYTES + 1)
                        if len(config_member) > MAX_CONFIG_BYTES:
                            print(
                                f"[FAIL] {archive_path.name}: .basic-memory/config.json exceeds size limit",
                                file=sys.stderr,
                            )
                            raise SystemExit(1)
                        total_bytes += len(config_member)
                    else:
                        # Stream entry to EOF in fixed chunks to verify compression without OOM
                        while True:
                            chunk = extracted.read(CHUNK_BYTES)
                            if not chunk:
                                break
                            total_bytes += len(chunk)
                            if total_bytes > MAX_ARCHIVE_BYTES:
                                print(
                                    f"[FAIL] {archive_path.name}: decompressed size exceeds limit ({MAX_ARCHIVE_BYTES}B)",
                                    file=sys.stderr,
                                )
                                raise SystemExit(1)
                        if pure.suffix.lower() == ".md":
                            md_count += 1
                    if total_bytes > MAX_ARCHIVE_BYTES:
                        print(
                            f"[FAIL] {archive_path.name}: decompressed size exceeds limit ({MAX_ARCHIVE_BYTES}B)",
                            file=sys.stderr,
                        )
                        raise SystemExit(1)

        if member_count == 0:
            print(f"[FAIL] {archive_path.name}: archive contains no entries", file=sys.stderr)
            raise SystemExit(1)

        if config_member is None:
            print(
                f"[FAIL] {archive_path.name}: missing .basic-memory/config.json",
                file=sys.stderr,
            )
            raise SystemExit(1)

        try:
            config_data = json.loads(config_member.decode("utf-8"))
        except Exception as exc:
            print(
                f"[FAIL] {archive_path.name}: invalid JSON in .basic-memory/config.json ({exc})",
                file=sys.stderr,
            )
            raise SystemExit(1)

        if not isinstance(config_data, dict):
            print(
                f"[FAIL] {archive_path.name}: .basic-memory/config.json must be a JSON object",
                file=sys.stderr,
            )
            raise SystemExit(1)

        projects = config_data.get("projects")
        if not isinstance(projects, dict) or not projects:
            print(
                f"[FAIL] {archive_path.name}: .basic-memory/config.json has no valid 'projects' map",
                file=sys.stderr,
            )
            raise SystemExit(1)

        if md_count < 1:
            print(
                f"[FAIL] {archive_path.name}: archive contains no Markdown (.md) files",
                file=sys.stderr,
            )
            raise SystemExit(1)

        project_names = ", ".join(sorted(projects.keys()))
        size_bytes = archive_path.stat().st_size
        print(
            f"[OK] {archive_path.name} "
            f"(size={size_bytes}B, projects=[{project_names}], md_files={md_count}, total_files={total_files})"
        )
except (tarfile.TarError, EOFError, OSError, zlib.error) as exc:
    print(f"[FAIL] {archive_path.name}: corrupted tar.gz stream ({exc})", file=sys.stderr)
    raise SystemExit(1)
PY
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "$1" == "--all" ]]; then
  TARGET_DIR="${2:-${BACKUP_DIR:-$(load_env_default BACKUP_DIR)}}"
  if [[ -z "${TARGET_DIR}" ]]; then
    echo "Error: BACKUP_DIR is not specified (pass as 2nd argument, set BACKUP_DIR env, or configure ENV_FILE)." >&2
    exit 1
  fi
  if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "Error: BACKUP_DIR does not exist: ${TARGET_DIR}" >&2
    exit 1
  fi

  shopt -s nullglob
  archives=("${TARGET_DIR}"/basic-memory-backup-*.tar.gz)
  shopt -u nullglob

  if [[ ${#archives[@]} -eq 0 ]]; then
    echo "Error: No backup archives (basic-memory-backup-*.tar.gz) found in ${TARGET_DIR}" >&2
    exit 1
  fi

  failed=0
  for archive in "${archives[@]}"; do
    if ! verify_single_archive "${archive}"; then
      failed=$((failed + 1))
    fi
  done

  if [[ ${failed} -gt 0 ]]; then
    echo "Verification failed: ${failed} of ${#archives[@]} archive(s) invalid." >&2
    exit 1
  fi

  echo "All ${#archives[@]} archive(s) verified successfully."
  exit 0
fi

verify_single_archive "$1"
