"""Backup, verify and restore for the Sarthi database."""
import hashlib
import io
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.management import call_command
from django.db import connection, connections
from django.utils import timezone

from .audit import log_event
from .exceptions import RecordNotFound, SarthiError
from .models import AuditLog

logger = logging.getLogger(__name__)

KINDS = ("manual", "auto", "pre-restore")
FILENAME_RE = re.compile(
    r"^sarthi_(?P<kind>[a-z-]+)_(?P<stamp>\d{8}_\d{6})\.zip(?P<enc>\.enc)?$"
)
DB_MEMBER = "db.sqlite3"
MANIFEST_MEMBER = "manifest.json"


class BackupError(SarthiError):
    default_message = "The backup could not be completed."
    status_code = 500


def _backup_dir():
    folder = Path(settings.BACKUP_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _live_db_path(db_path=None):
    name = str(db_path if db_path is not None else connection.settings_dict["NAME"])
    if name == ":memory:" or name.startswith("file:"):
        raise BackupError("The database is in memory, so it cannot be backed up.")
    return Path(name)


def _fernet():
    key = settings.BACKUP_ENCRYPTION_KEY
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise BackupError("BACKUP_ENCRYPTION_KEY in .env is not a valid key.") from exc


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot_database(source, destination):
    """Safe copy of a live SQLite database (uses SQLite's own backup feature)."""
    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(destination))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _inspect_database(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        try:
            users = conn.execute("SELECT count(*) FROM accounts_user").fetchone()[0]
        except sqlite3.Error:
            users = None
    finally:
        conn.close()
    return integrity, tables, users


def create_backup(kind="manual", db_path=None):
    if kind not in KINDS:
        raise BackupError(f"Unknown backup kind: {kind}")
    source = _live_db_path(db_path)
    if not source.exists():
        raise BackupError("The database file was not found.")
    folder = _backup_dir()
    fernet = _fernet()
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_copy = Path(tmp) / DB_MEMBER
        _snapshot_database(source, db_copy)
        db_bytes = db_copy.read_bytes()
        manifest = {
            "app": "sarthi",
            "version": settings.SARTHI_VERSION,
            "created_at": timezone.now().isoformat(),
            "kind": kind,
            "db_sha256": _sha256_bytes(db_bytes),
            "db_bytes": len(db_bytes),
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(DB_MEMBER, db_bytes)
            bundle.writestr(MANIFEST_MEMBER, json.dumps(manifest, indent=2))
        payload = buffer.getvalue()

    if fernet is not None:
        payload = fernet.encrypt(payload)
        suffix = ".zip.enc"
    else:
        suffix = ".zip"
        logger.warning("Backup is NOT encrypted: set BACKUP_ENCRYPTION_KEY in .env")

    final = folder / f"sarthi_{kind}_{stamp}{suffix}"
    partial = final.with_name(final.name + ".partial")
    partial.write_bytes(payload)
    os.replace(partial, final)

    copied = _copy_to_second_location(final)
    if kind == "auto":
        prune_auto_backups()
    log_event(AuditLog.Action.BACKUP, note=final.name)
    logger.info("Backup created: %s", final.name)
    return {
        "name": final.name,
        "path": final,
        "size": final.stat().st_size,
        "encrypted": fernet is not None,
        "copied": copied,
    }


def _copy_to_second_location(file_path):
    target = settings.BACKUP_COPY_DIR
    if not target:
        return False
    try:
        folder = Path(target)
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, folder / file_path.name)
        return True
    except OSError:
        logger.exception("Could not copy the backup to BACKUP_COPY_DIR")
        return False


def list_backups():
    items = []
    for entry in _backup_dir().iterdir():
        match = FILENAME_RE.match(entry.name)
        if not match or not entry.is_file():
            continue
        created = datetime.strptime(match["stamp"], "%Y%m%d_%H%M%S")
        items.append({
            "name": entry.name,
            "kind": match["kind"],
            "created": created,
            "created_text": created.strftime("%d-%m-%Y %H:%M"),
            "size_kb": max(1, entry.stat().st_size // 1024),
            "encrypted": bool(match["enc"]),
        })
    items.sort(key=lambda item: item["created"], reverse=True)
    return items


def prune_auto_backups():
    keep = max(1, int(settings.BACKUP_KEEP_AUTO))
    automatic = [item for item in list_backups() if item["kind"] == "auto"]
    for old in automatic[keep:]:
        try:
            (_backup_dir() / old["name"]).unlink()
        except OSError:
            logger.exception("Could not delete old backup %s", old["name"])


def resolve_backup_path(name):
    """Only plain backup file names inside the backups folder are accepted."""
    clean = Path(str(name)).name
    if not FILENAME_RE.match(clean):
        raise RecordNotFound("That is not a valid backup file name.")
    path = _backup_dir() / clean
    if not path.is_file():
        raise RecordNotFound("That backup file was not found.")
    return path


def _extract(path, tmp_dir):
    raw = path.read_bytes()
    if path.name.endswith(".enc"):
        fernet = _fernet()
        if fernet is None:
            raise BackupError(
                "This backup is encrypted but BACKUP_ENCRYPTION_KEY is not set in .env."
            )
        try:
            raw = fernet.decrypt(raw)
        except InvalidToken as exc:
            raise BackupError(
                "Could not decrypt this backup. The key is wrong or the file is damaged."
            ) from exc
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            if set(bundle.namelist()) != {DB_MEMBER, MANIFEST_MEMBER}:
                raise BackupError("The backup contains unexpected files.")
            manifest = json.loads(bundle.read(MANIFEST_MEMBER))
            db_bytes = bundle.read(DB_MEMBER)
    except (zipfile.BadZipFile, ValueError) as exc:
        raise BackupError("The backup file is damaged.") from exc
    if _sha256_bytes(db_bytes) != manifest.get("db_sha256"):
        raise BackupError("The backup failed its checksum test. It may be damaged.")
    db_path = Path(tmp_dir) / DB_MEMBER
    db_path.write_bytes(db_bytes)
    return db_path, manifest


def verify_backup(name):
    """Open the backup completely (decrypt, unzip, checksum, database check)."""
    path = resolve_backup_path(name)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path, manifest = _extract(path, tmp)
        integrity, tables, users = _inspect_database(db_path)
    if integrity != "ok":
        raise BackupError("The database inside this backup is damaged.")
    return {
        "name": path.name,
        "tables": tables,
        "users": users,
        "kind": manifest.get("kind", ""),
        "encrypted": path.name.endswith(".enc"),
    }


def restore_backup(name, db_path=None, run_migrate=True):
    """Replace the live database with a verified backup (safety backup first)."""
    path = resolve_backup_path(name)
    target = _live_db_path(db_path)
    safety_name = None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        verified_db, _manifest = _extract(path, tmp)
        integrity, _tables, _users = _inspect_database(verified_db)
        if integrity != "ok":
            raise BackupError("The database inside this backup is damaged. Nothing was changed.")
        if target.exists():
            safety_name = create_backup(kind="pre-restore", db_path=target)["name"]
        if db_path is None:
            connections.close_all()
        staged = target.with_name(target.name + ".restoring")
        shutil.copyfile(verified_db, staged)
        try:
            os.replace(staged, target)
        except PermissionError as exc:
            staged.unlink(missing_ok=True)
            raise BackupError(
                "The database file is in use. Stop the Sarthi server and any other "
                "Sarthi window, then try again."
            ) from exc
    if run_migrate:
        call_command("migrate", interactive=False, verbosity=0)
    log_event(AuditLog.Action.RESTORE, note=f"Restored from {path.name}")
    logger.warning("Database restored from %s", path.name)
    return {"restored_from": path.name, "safety_backup": safety_name}
