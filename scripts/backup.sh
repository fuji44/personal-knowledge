#!/usr/bin/env bash
set -euo pipefail

# Archive the basic-memory data directory (HOST_DATA_PATH), verify it with
# verify-backup.sh, and then apply generation rotation.
#
# Excludes the derived SQLite index (.basic-memory/memory.db*) and archives only
# the Markdown files (source of truth) and .basic-memory/config.json.
#
# Usage:
#   ./scripts/backup.sh
#   HOST_DATA_PATH=/path/to/data BACKUP_DIR=/path/to/backups BACKUP_KEEP_GENERATIONS=7 ./scripts/backup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
  echo "Usage: $0" >&2
  echo "Environment variables (or configured in ENV_FILE):" >&2
  echo "  HOST_DATA_PATH           Source data directory" >&2
  echo "  BACKUP_DIR               Destination directory for backup archives" >&2
  echo "  BACKUP_KEEP_GENERATIONS  Number of backup generations to keep (default: 7)" >&2
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

HOST_DATA_PATH="${HOST_DATA_PATH:-$(load_env_default HOST_DATA_PATH)}"
BACKUP_DIR="${BACKUP_DIR:-$(load_env_default BACKUP_DIR)}"
BACKUP_KEEP_GENERATIONS="${BACKUP_KEEP_GENERATIONS:-$(load_env_default BACKUP_KEEP_GENERATIONS)}"
BACKUP_KEEP_GENERATIONS="${BACKUP_KEEP_GENERATIONS:-7}"

if [[ -z "${HOST_DATA_PATH}" ]]; then
  echo "Error: HOST_DATA_PATH is not set (set environment variable or ENV_FILE)." >&2
  exit 1
fi

if [[ -z "${BACKUP_DIR}" ]]; then
  echo "Error: BACKUP_DIR is not set (set environment variable or ENV_FILE)." >&2
  exit 1
fi

if [[ ! "${BACKUP_KEEP_GENERATIONS}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: BACKUP_KEEP_GENERATIONS must be a positive integer (got: ${BACKUP_KEEP_GENERATIONS})." >&2
  exit 1
fi

if [[ ! -d "${HOST_DATA_PATH}" ]]; then
  echo "Error: HOST_DATA_PATH does not exist: ${HOST_DATA_PATH}" >&2
  exit 1
fi

if [[ ! -f "${HOST_DATA_PATH}/.basic-memory/config.json" ]]; then
  echo "Error: ${HOST_DATA_PATH}/.basic-memory/config.json not found." >&2
  exit 1
fi

TIMESTAMP="${BACKUP_TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"
if [[ ! "${TIMESTAMP}" =~ ^[0-9A-Za-z._-]+$ ]]; then
  echo "Error: BACKUP_TIMESTAMP contains invalid characters: ${TIMESTAMP}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

FINAL_ARCHIVE="${BACKUP_DIR}/basic-memory-backup-${TIMESTAMP}.tar.gz"
TMP_ARCHIVE="${BACKUP_DIR}/.basic-memory-backup-${TIMESTAMP}.$$.tmp.tar.gz"

cleanup_tmp() {
  if [[ -f "${TMP_ARCHIVE}" ]]; then
    rm -f "${TMP_ARCHIVE}"
  fi
}
trap cleanup_tmp EXIT

echo "Creating backup archive from ${HOST_DATA_PATH} ..."
tar -czf - \
  --numeric-owner \
  --exclude='./.basic-memory/memory.db' \
  --exclude='./.basic-memory/memory.db-*' \
  --exclude='.basic-memory/memory.db' \
  --exclude='.basic-memory/memory.db-*' \
  -C "${HOST_DATA_PATH}" . > "${TMP_ARCHIVE}"

echo "Verifying created archive ..."
if ! "${SCRIPT_DIR}/verify-backup.sh" "${TMP_ARCHIVE}"; then
  echo "Error: Created backup archive failed verification. Existing backups were not touched." >&2
  exit 1
fi

mv -f -- "${TMP_ARCHIVE}" "${FINAL_ARCHIVE}"
echo "Backup saved: ${FINAL_ARCHIVE}"

# Generation rotation (runs only after the verified archive is finalized)
shopt -s nullglob
all_backups=("${BACKUP_DIR}"/basic-memory-backup-*.tar.gz)
shopt -u nullglob

if [[ ${#all_backups[@]} -gt ${BACKUP_KEEP_GENERATIONS} ]]; then
  # Sort by filename (ascending timestamp) and remove oldest generations first
  mapfile -d '' -t sorted_backups < <(printf '%s\0' "${all_backups[@]}" | LC_ALL=C sort -z)

  delete_count=$(( ${#sorted_backups[@]} - BACKUP_KEEP_GENERATIONS ))
  for (( i=0; i<delete_count; i++ )); do
    old_archive="${sorted_backups[i]}"
    rm -f -- "${old_archive}"
    echo "Rotated out old backup: ${old_archive}"
  done
fi
