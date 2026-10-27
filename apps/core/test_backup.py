import sqlite3
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.core.backup import (
    BackupError, create_backup, list_backups, prune_auto_backups,
    restore_backup, verify_backup,
)
from apps.core.exceptions import RecordNotFound


class BackupTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.backup_dir = root / "backups"
        self.db_file = root / "live.sqlite3"
        conn = sqlite3.connect(str(self.db_file))
        conn.execute("CREATE TABLE accounts_user (id INTEGER PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO accounts_user (username) VALUES ('alice')")
        conn.commit()
        conn.close()
        self.key = Fernet.generate_key().decode()
        override = override_settings(
            BACKUP_DIR=self.backup_dir, BACKUP_ENCRYPTION_KEY=self.key,
            BACKUP_COPY_DIR="", BACKUP_KEEP_AUTO=2,
        )
        override.enable()
        self.addCleanup(override.disable)

    def _count_users(self):
        conn = sqlite3.connect(str(self.db_file))
        try:
            return conn.execute("SELECT count(*) FROM accounts_user").fetchone()[0]
        finally:
            conn.close()

    def test_backup_is_encrypted_and_verifies(self):
        result = create_backup("manual", db_path=self.db_file)
        self.assertTrue(result["name"].endswith(".zip.enc"))
        info = verify_backup(result["name"])
        self.assertEqual(info["users"], 1)
        self.assertNotIn(b"alice", (self.backup_dir / result["name"]).read_bytes())

    def test_wrong_key_is_rejected(self):
        result = create_backup("manual", db_path=self.db_file)
        with override_settings(BACKUP_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertRaises(BackupError):
                verify_backup(result["name"])

    def test_damaged_file_is_rejected(self):
        result = create_backup("manual", db_path=self.db_file)
        (self.backup_dir / result["name"]).write_bytes(b"not a real backup")
        with self.assertRaises(BackupError):
            verify_backup(result["name"])

    def test_restore_brings_back_old_data(self):
        result = create_backup("manual", db_path=self.db_file)
        conn = sqlite3.connect(str(self.db_file))
        conn.execute("INSERT INTO accounts_user (username) VALUES ('bob')")
        conn.commit()
        conn.close()
        self.assertEqual(self._count_users(), 2)
        restore_backup(result["name"], db_path=self.db_file, run_migrate=False)
        self.assertEqual(self._count_users(), 1)
        self.assertTrue(any(item["kind"] == "pre-restore" for item in list_backups()))

    def test_path_tricks_are_rejected(self):
        with self.assertRaises(RecordNotFound):
            verify_backup("..\\..\\.env")
        with self.assertRaises(RecordNotFound):
            verify_backup("../../.env")

    def test_old_automatic_backups_are_pruned(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        for stamp in ("20260101_010101", "20260102_010101", "20260103_010101"):
            (self.backup_dir / f"sarthi_auto_{stamp}.zip.enc").write_bytes(b"x")
        prune_auto_backups()
        names = sorted(item["name"] for item in list_backups())
        self.assertEqual(names, [
            "sarthi_auto_20260102_010101.zip.enc",
            "sarthi_auto_20260103_010101.zip.enc",
        ])
