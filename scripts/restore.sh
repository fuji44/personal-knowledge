#!/usr/bin/env bash
set -euo pipefail

# Restore the basic-memory data directory (HOST_DATA_PATH) from a backup archive (.tar.gz).
#
# Restore workflow:
#   1. Verify archive integrity with verify-backup.sh (abort without changes on failure)
#   2. Confirmation prompt (skipped with --yes / -y)
#   3. Temporarily stop any running basic-memory container (unless --no-docker)
#   4. If current data directory is non-empty, save it to BACKUP_DIR/pre-restore-YYYYMMDD-HHMMSS.tar.gz and verify
#   5. Re-verify archive, clean existing files in HOST_DATA_PATH (including stale memory.db*), and extract
#   6. Restart the stopped container if restore completed cleanly
#
# Usage:
#   ./scripts/restore.sh [--yes|-y] [--no-docker] <ARCHIVE_FILE>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-}"
CONTAINER_NAME="${BASIC_MEMORY_CONTAINER_NAME:-basic-memory}"

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
  echo "Usage: $0 [--yes|-y] [--no-docker] <ARCHIVE_FILE>" >&2
}

AUTO_YES=0
NO_DOCKER=0
ARCHIVE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)
      AUTO_YES=1
      shift
      ;;
    --no-docker)
      NO_DOCKER=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    -*)
      echo "Error: Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -n "${ARCHIVE_FILE}" ]]; then
        echo "Error: Multiple archive files specified." >&2
        usage
        exit 1
      fi
      ARCHIVE_FILE="$1"
      shift
      ;;
  esac
done

if [[ -z "${ARCHIVE_FILE}" ]]; then
  usage
  exit 1
fi

HOST_DATA_PATH="${HOST_DATA_PATH:-$(load_env_default HOST_DATA_PATH)}"
BACKUP_DIR="${BACKUP_DIR:-$(load_env_default BACKUP_DIR)}"

if [[ -z "${HOST_DATA_PATH}" ]]; then
  echo "Error: HOST_DATA_PATH is not set (set environment variable or ENV_FILE)." >&2
  exit 1
fi

STRIPPED_DATA_PATH="${HOST_DATA_PATH}"
while [[ "${STRIPPED_DATA_PATH}" == */ && "${STRIPPED_DATA_PATH}" != "/" ]]; do
  STRIPPED_DATA_PATH="${STRIPPED_DATA_PATH%/}"
done
if [[ -n "${STRIPPED_DATA_PATH}" && -L "${STRIPPED_DATA_PATH}" ]]; then
  echo "Error: HOST_DATA_PATH must not be a symlink: ${HOST_DATA_PATH}" >&2
  exit 1
fi

if [[ -n "${BASIC_MEMORY_UID_GID:-}" && ! "${BASIC_MEMORY_UID_GID}" =~ ^[0-9]+:[0-9]+$ ]]; then
  echo "Error: BASIC_MEMORY_UID_GID must be in '<uid>:<gid>' numeric format (got: ${BASIC_MEMORY_UID_GID})." >&2
  exit 1
fi

if [[ -z "${BACKUP_DIR}" ]]; then
  BACKUP_DIR="$(dirname "${ARCHIVE_FILE}")"
fi

echo "Verifying target archive before restore ..."
"${SCRIPT_DIR}/verify-backup.sh" "${ARCHIVE_FILE}"

if [[ ${AUTO_YES} -ne 1 ]]; then
  echo "WARNING: This will replace all contents in ${HOST_DATA_PATH} with ${ARCHIVE_FILE}."
  read -r -p "Proceed with restore? [y/N]: " confirm
  if [[ ! "${confirm}" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo "Restore cancelled."
    exit 0
  fi
fi

CONTAINER_WAS_RUNNING=0
RESTORE_COMPLETE=0
PRE_RESTORE_TMP=""

stop_container_if_running() {
  if [[ ${NO_DOCKER} -eq 1 ]]; then
    return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx -- "${CONTAINER_NAME}"; then
      echo "Stopping running ${CONTAINER_NAME} container ..."
      docker stop "${CONTAINER_NAME}" >/dev/null
      CONTAINER_WAS_RUNNING=1
    fi
  fi
}

cleanup_and_restart() {
  if [[ -n "${PRE_RESTORE_TMP}" && -f "${PRE_RESTORE_TMP}" ]]; then
    rm -f -- "${PRE_RESTORE_TMP}"
  fi
  if [[ ${CONTAINER_WAS_RUNNING} -eq 1 ]]; then
    if [[ ${RESTORE_COMPLETE} -eq 1 ]]; then
      echo "Restarting ${CONTAINER_NAME} container ..."
      docker start "${CONTAINER_NAME}" >/dev/null
    else
      echo "Warning: Restore did not complete cleanly; ${CONTAINER_NAME} container was left stopped." >&2
    fi
  fi
}

stop_container_if_running
trap cleanup_and_restart EXIT

mkdir -p "${HOST_DATA_PATH}"
mkdir -p "${BACKUP_DIR}"

# Save a safety pre-restore archive atomically if current data directory is non-empty
if [[ -n "$(ls -A "${HOST_DATA_PATH}" 2>/dev/null || true)" ]]; then
  PRE_RESTORE_TS="${RESTORE_TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"
  if [[ ! "${PRE_RESTORE_TS}" =~ ^[0-9A-Za-z._-]+$ ]]; then
    echo "Error: RESTORE_TIMESTAMP contains invalid characters: ${PRE_RESTORE_TS}" >&2
    exit 1
  fi
  PRE_RESTORE_ARCHIVE="${BACKUP_DIR}/pre-restore-${PRE_RESTORE_TS}.tar.gz"
  PRE_RESTORE_TMP="${BACKUP_DIR}/.pre-restore-${PRE_RESTORE_TS}.$$.tmp.tar.gz"
  echo "Creating safety backup of current data to ${PRE_RESTORE_ARCHIVE} ..."
  tar -czf - \
    --numeric-owner \
    --exclude='./.basic-memory/memory.db' \
    --exclude='./.basic-memory/memory.db-*' \
    --exclude='.basic-memory/memory.db' \
    --exclude='.basic-memory/memory.db-*' \
    -C "${HOST_DATA_PATH}" . > "${PRE_RESTORE_TMP}"
  mv -f -- "${PRE_RESTORE_TMP}" "${PRE_RESTORE_ARCHIVE}"
  PRE_RESTORE_TMP=""

  # Verify the safety archive if current data looks like a valid basic-memory layout
  if [[ -f "${HOST_DATA_PATH}/.basic-memory/config.json" ]]; then
    if ! "${SCRIPT_DIR}/verify-backup.sh" "${PRE_RESTORE_ARCHIVE}"; then
      echo "Warning: Current data did not pass standard verification, but raw safety archive is preserved at ${PRE_RESTORE_ARCHIVE}" >&2
    fi
  fi
fi

# Re-verify immediately before wiping and extracting to minimize TOCTOU window
"${SCRIPT_DIR}/verify-backup.sh" "${ARCHIVE_FILE}"

echo "Cleaning existing data in ${HOST_DATA_PATH} ..."
python3 - "${HOST_DATA_PATH}" <<'PY'
import os
import shutil
import sys
from pathlib import Path

raw = Path(sys.argv[1])
if raw.is_symlink():
    raise SystemExit(f"Error: HOST_DATA_PATH must not be a symlink: '{raw}'")

root = raw.resolve()
protected = {
    Path(p)
    for p in ("/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/proc", "/root", "/run", "/sbin", "/sys", "/tmp", "/usr", "/var")
}
protected |= {p.resolve() for p in protected if p.exists()}
home_resolved = Path.home().resolve()
protected |= set(home_resolved.parents)

bm_home = os.environ.get("BASIC_MEMORY_HOME")
bm_home_resolved = Path(bm_home).resolve() if bm_home else None
if bm_home_resolved is None or root != bm_home_resolved:
    protected.add(home_resolved)

if root in protected:
    raise SystemExit(f"Error: Refusing to clean protected directory '{root}'")

for child in root.iterdir():
    if child.is_dir() and not child.is_symlink():
        shutil.rmtree(child)
    else:
        child.unlink()
PY

echo "Extracting ${ARCHIVE_FILE} into ${HOST_DATA_PATH} ..."
tar -xzf - --no-same-owner --no-same-permissions -C "${HOST_DATA_PATH}" < "${ARCHIVE_FILE}"

# Align ownership when running as root and BASIC_MEMORY_UID_GID is explicitly set
if [[ "$(id -u)" -eq 0 && -n "${BASIC_MEMORY_UID_GID:-}" ]]; then
  chown -RP -- "${BASIC_MEMORY_UID_GID}" "${HOST_DATA_PATH}"
fi

RESTORE_COMPLETE=1
echo "Restore completed successfully into ${HOST_DATA_PATH}"
