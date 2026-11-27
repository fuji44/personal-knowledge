import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_SCRIPT = REPO_ROOT / "scripts" / "backup.sh"
RESTORE_SCRIPT = REPO_ROOT / "scripts" / "restore.sh"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify-backup.sh"


def _clean_env(**overrides: str) -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "ENV_FILE",
        "BASIC_MEMORY_UID_GID",
        "BACKUP_KEEP_GENERATIONS",
        "BASIC_MEMORY_CONTAINER_NAME",
        "BASIC_MEMORY_HOME",
    ):
        env.pop(key, None)
    env.update(overrides)
    return env


def populate_sample_data(data_dir: Path, note_text: str = "# Note v1\n") -> None:
    bm_dir = data_dir / ".basic-memory"
    bm_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "projects": {
            "general": "/data/general",
            "work": "/data/work",
        }
    }
    (bm_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    # SQLite DB and WAL files that must be excluded from backups
    (bm_dir / "memory.db").write_bytes(b"SQLite format 3\x00dummy")
    (bm_dir / "memory.db-wal").write_bytes(b"dummy-wal")
    (bm_dir / "memory.db-shm").write_bytes(b"dummy-shm")

    general_dir = data_dir / "general" / "notes"
    general_dir.mkdir(parents=True, exist_ok=True)
    (general_dir / "sample.md").write_text(note_text, encoding="utf-8")


class BackupRestoreVerifyTest(unittest.TestCase):
    def test_backup_excludes_sqlite_and_passes_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            backup_dir = base / "backups"
            populate_sample_data(data_dir)

            env = _clean_env(
                HOST_DATA_PATH=str(data_dir),
                BACKUP_DIR=str(backup_dir),
                BACKUP_KEEP_GENERATIONS="3",
                BACKUP_TIMESTAMP="20261121-120000",
            )
            res = subprocess.run(
                ["bash", str(BACKUP_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)

            archive = backup_dir / "basic-memory-backup-20261121-120000.tar.gz"
            self.assertTrue(archive.is_file())

            with tarfile.open(archive, "r:gz") as tf:
                names = [m.name.removeprefix("./") for m in tf.getmembers()]
                self.assertIn(".basic-memory/config.json", names)
                self.assertIn("general/notes/sample.md", names)
                self.assertNotIn(".basic-memory/memory.db", names)
                self.assertNotIn(".basic-memory/memory.db-wal", names)
                self.assertNotIn(".basic-memory/memory.db-shm", names)

            res_verify_all = subprocess.run(
                ["bash", str(VERIFY_SCRIPT), "--all", str(backup_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_verify_all.returncode, 0, res_verify_all.stderr)
            self.assertIn("[OK]", res_verify_all.stdout)

    def test_generation_rotation_keeps_newest_n(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            backup_dir = base / "backups"
            populate_sample_data(data_dir)

            timestamps = [
                "20261121-010000",
                "20261121-020000",
                "20261121-030000",
                "20261121-040000",
                "20261121-050000",
            ]
            for ts in timestamps:
                env = _clean_env(
                    HOST_DATA_PATH=str(data_dir),
                    BACKUP_DIR=str(backup_dir),
                    BACKUP_KEEP_GENERATIONS="3",
                    BACKUP_TIMESTAMP=ts,
                )
                res = subprocess.run(
                    ["bash", str(BACKUP_SCRIPT)],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(res.returncode, 0, res.stderr)

            remaining = sorted(p.name for p in backup_dir.glob("basic-memory-backup-*.tar.gz"))
            self.assertEqual(
                remaining,
                [
                    "basic-memory-backup-20261121-030000.tar.gz",
                    "basic-memory-backup-20261121-040000.tar.gz",
                    "basic-memory-backup-20261121-050000.tar.gz",
                ],
            )

    def test_failed_backup_does_not_rotate_out_good_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            backup_dir = base / "backups"
            populate_sample_data(data_dir)

            for ts in ["20261121-010000", "20261121-020000"]:
                env = _clean_env(
                    HOST_DATA_PATH=str(data_dir),
                    BACKUP_DIR=str(backup_dir),
                    BACKUP_KEEP_GENERATIONS="2",
                    BACKUP_TIMESTAMP=ts,
                )
                res = subprocess.run(
                    ["bash", str(BACKUP_SCRIPT)],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(res.returncode, 0, res.stderr)

            # Corrupt source directory by removing all Markdown files so verification fails
            for md in data_dir.rglob("*.md"):
                md.unlink()

            env_fail = _clean_env(
                HOST_DATA_PATH=str(data_dir),
                BACKUP_DIR=str(backup_dir),
                BACKUP_KEEP_GENERATIONS="2",
                BACKUP_TIMESTAMP="20261121-030000",
            )
            res_fail = subprocess.run(
                ["bash", str(BACKUP_SCRIPT)],
                env=env_fail,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_fail.returncode, 0)

            # Existing 2 valid generations must still be intact, and no tmp/new archive left
            remaining = sorted(p.name for p in backup_dir.iterdir())
            self.assertEqual(
                remaining,
                [
                    "basic-memory-backup-20261121-010000.tar.gz",
                    "basic-memory-backup-20261121-020000.tar.gz",
                ],
            )

    def test_verify_detects_corrupted_and_invalid_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # 1. Truncated / corrupted gzip file
            corrupted = base / "corrupted.tar.gz"
            corrupted.write_bytes(b"\x1f\x8b\x08\x00broken-stream")
            res1 = subprocess.run(
                ["bash", str(VERIFY_SCRIPT), str(corrupted)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res1.returncode, 0)

            # 2. Valid tar.gz but missing .basic-memory/config.json
            no_config = base / "no-config.tar.gz"
            with tarfile.open(no_config, "w:gz") as tf:
                content = b"# hello"
                info = tarfile.TarInfo(name="general/note.md")
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
            res2 = subprocess.run(
                ["bash", str(VERIFY_SCRIPT), str(no_config)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res2.returncode, 0)

            # 3. Valid config.json but no .md files
            no_md = base / "no-md.tar.gz"
            with tarfile.open(no_md, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info = tarfile.TarInfo(name=".basic-memory/config.json")
                info.size = len(cfg)
                tf.addfile(info, io.BytesIO(cfg))
            res3 = subprocess.run(
                ["bash", str(VERIFY_SCRIPT), str(no_md)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res3.returncode, 0)

            # 4. Path traversal entry (../)
            traversal = base / "traversal.tar.gz"
            with tarfile.open(traversal, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# evil"
                info_md = tarfile.TarInfo(name="../escape.md")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
            res4 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(traversal)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res4.returncode, 0)

            # 5. Symlink member
            symlink_tar = base / "symlink.tar.gz"
            with tarfile.open(symlink_tar, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# note"
                info_md = tarfile.TarInfo(name="general/note.md")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
                sym = tarfile.TarInfo(name="general/link")
                sym.type = tarfile.SYMTYPE
                sym.linkname = "/etc/passwd"
                tf.addfile(sym)
            res5 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(symlink_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res5.returncode, 0)

            # 6. SUID bit on regular file
            suid_tar = base / "suid.tar.gz"
            with tarfile.open(suid_tar, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# note"
                info_md = tarfile.TarInfo(name="general/note.md")
                info_md.size = len(md)
                info_md.mode = 0o4755
                tf.addfile(info_md, io.BytesIO(md))
            res6 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(suid_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res6.returncode, 0)

            # 7. Derived .basic-memory/memory.db included
            db_tar = base / "db.tar.gz"
            with tarfile.open(db_tar, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# note"
                info_md = tarfile.TarInfo(name="general/note.md")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
                db = b"sqlite"
                info_db = tarfile.TarInfo(name=".basic-memory/memory.db")
                info_db.size = len(db)
                tf.addfile(info_db, io.BytesIO(db))
            res7 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(db_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res7.returncode, 0)

            # 8. Dot-slash-slash (.//) absolute path bypass
            slash_tar = base / "slash.tar.gz"
            with tarfile.open(slash_tar, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# evil"
                info_md = tarfile.TarInfo(name=".//etc/passwd")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
            res8 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(slash_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res8.returncode, 0)

            # 9. Dot-slash-slash (.//) memory.db exclusion bypass
            slash_db_tar = base / "slash-db.tar.gz"
            with tarfile.open(slash_db_tar, "w:gz") as tf:
                cfg = json.dumps({"projects": {"general": "/data/general"}}).encode("utf-8")
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# note"
                info_md = tarfile.TarInfo(name="general/note.md")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
                db = b"sqlite"
                info_db = tarfile.TarInfo(name=".//.basic-memory/memory.db")
                info_db.size = len(db)
                tf.addfile(info_db, io.BytesIO(db))
            res9 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(slash_db_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res9.returncode, 0)

            # 10. Valid non-object JSON in config.json ([])
            list_cfg_tar = base / "list-cfg.tar.gz"
            with tarfile.open(list_cfg_tar, "w:gz") as tf:
                cfg = b"[]"
                info_cfg = tarfile.TarInfo(name=".basic-memory/config.json")
                info_cfg.size = len(cfg)
                tf.addfile(info_cfg, io.BytesIO(cfg))
                md = b"# note"
                info_md = tarfile.TarInfo(name="general/note.md")
                info_md.size = len(md)
                tf.addfile(info_md, io.BytesIO(md))
            res10 = subprocess.run(["bash", str(VERIFY_SCRIPT), str(list_cfg_tar)], capture_output=True, text=True, check=False)
            self.assertNotEqual(res10.returncode, 0)
            self.assertNotIn("Traceback", res10.stderr)

    def test_restore_recovers_data_and_creates_pre_restore_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            backup_dir = base / "backups"
            populate_sample_data(data_dir, note_text="# Original v1\n")

            env = _clean_env(
                HOST_DATA_PATH=str(data_dir),
                BACKUP_DIR=str(backup_dir),
                BACKUP_TIMESTAMP="20261121-100000",
                RESTORE_TIMESTAMP="20261121-110000",
            )
            res_backup = subprocess.run(
                ["bash", str(BACKUP_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_backup.returncode, 0, res_backup.stderr)
            archive = backup_dir / "basic-memory-backup-20261121-100000.tar.gz"

            # Modify data directory and add an extra file + stale SQLite DB
            (data_dir / "general" / "notes" / "sample.md").write_text("# Modified v2\n", encoding="utf-8")
            (data_dir / "general" / "notes" / "extra.md").write_text("# Extra file\n", encoding="utf-8")
            (data_dir / ".basic-memory" / "memory.db").write_bytes(b"stale-db")

            res_restore = subprocess.run(
                ["bash", str(RESTORE_SCRIPT), "--yes", "--no-docker", str(archive)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_restore.returncode, 0, res_restore.stderr)

            # Content is restored to v1, extra file and stale memory.db are gone
            restored_text = (data_dir / "general" / "notes" / "sample.md").read_text(encoding="utf-8")
            self.assertEqual(restored_text, "# Original v1\n")
            self.assertFalse((data_dir / "general" / "notes" / "extra.md").exists())
            self.assertFalse((data_dir / ".basic-memory" / "memory.db").exists())

            # Safety pre-restore backup was created and passes verification
            pre_restore = backup_dir / "pre-restore-20261121-110000.tar.gz"
            self.assertTrue(pre_restore.is_file())
            res_verify_pre = subprocess.run(
                ["bash", str(VERIFY_SCRIPT), str(pre_restore)],
                env=_clean_env(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_verify_pre.returncode, 0, res_verify_pre.stderr)

    def test_restore_rejects_trailing_slash_symlink_and_allows_in_container_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "data"
            backup_dir = base / "backups"
            populate_sample_data(data_dir, note_text="# v1\n")

            env = _clean_env(
                HOST_DATA_PATH=str(data_dir),
                BACKUP_DIR=str(backup_dir),
                BACKUP_TIMESTAMP="20261121-100000",
                RESTORE_TIMESTAMP="20261121-110000",
                HOME=str(data_dir),
                BASIC_MEMORY_HOME=str(data_dir),
            )
            res_backup = subprocess.run(["bash", str(BACKUP_SCRIPT)], env=env, capture_output=True, text=True, check=False)
            self.assertEqual(res_backup.returncode, 0, res_backup.stderr)
            archive = backup_dir / "basic-memory-backup-20261121-100000.tar.gz"

            # In-container restore where HOME == BASIC_MEMORY_HOME == HOST_DATA_PATH must succeed
            (data_dir / "general" / "notes" / "sample.md").write_text("# v2\n", encoding="utf-8")
            res_container = subprocess.run(
                ["bash", str(RESTORE_SCRIPT), "--yes", "--no-docker", str(archive)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_container.returncode, 0, res_container.stderr)
            self.assertEqual((data_dir / "general" / "notes" / "sample.md").read_text(encoding="utf-8"), "# v1\n")

            # Trailing-slash symlink HOST_DATA_PATH must be rejected without touching target
            real_target = base / "real-target"
            real_target.mkdir()
            (real_target / "important.txt").write_text("keep", encoding="utf-8")
            sym_path = base / "sym-data"
            sym_path.symlink_to(real_target)
            res_sym = subprocess.run(
                ["bash", str(RESTORE_SCRIPT), "--yes", "--no-docker", str(archive)],
                env=_clean_env(HOST_DATA_PATH=f"{sym_path}/", BACKUP_DIR=str(backup_dir)),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_sym.returncode, 0)
            self.assertTrue((real_target / "important.txt").is_file())


if __name__ == "__main__":
    unittest.main()
