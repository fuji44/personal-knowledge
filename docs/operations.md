# Operations: Backup, Verification, and Restore

The repository includes standalone scripts under [scripts/](../scripts/) that archive the Markdown source of truth and `.basic-memory/config.json` while excluding derived SQLite caches (`.basic-memory/memory.db*`).

Run `--help` on any script for its exact options and environment variables.

## Typical Workflows

```bash
# Create, verify, and rotate backups
HOST_DATA_PATH=/path/to/data BACKUP_DIR=/path/to/backups ./scripts/backup.sh

# Verify a single archive or all backups in a directory
./scripts/verify-backup.sh /path/to/backups/basic-memory-backup-YYYYMMDD-HHMMSS.tar.gz
./scripts/verify-backup.sh --all /path/to/backups

# Restore from an archive (creates a safety pre-restore archive first)
HOST_DATA_PATH=/path/to/data ./scripts/restore.sh /path/to/backups/basic-memory-backup-YYYYMMDD-HHMMSS.tar.gz
```

## Notes

- **Container usage**: These scripts are bundled into `/usr/local/bin/` in the container image defined by [Dockerfile](../Dockerfile).
- **Environment file**: Optionally set `ENV_FILE=/path/to/.env` to supply `HOST_DATA_PATH`, `BACKUP_DIR`, or `BACKUP_KEEP_GENERATIONS`.
- **Ownership on `root` restore**: When running `restore.sh` as `root`, set `BASIC_MEMORY_UID_GID` (e.g., `1000:1000`) to align extracted file ownership.
