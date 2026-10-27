# ARCHITECTURE.md - how the Sarthi core is built

## Layout
- config/settings/base.py: shared settings. development.py and production.py extend it.
- apps/core: shared foundation (base model with soft delete, error types, request ID, health page).
- apps/accounts: custom user model (login by username; phone and telegram_user_id fields).
- templates/: HTML pages, including friendly error pages.
- data/, logs/, backups/: runtime folders, never committed to Git.

## Rules for building new apps
1. Each new app lives in apps/<name>/ and is listed in INSTALLED_APPS.
2. Data models inherit BaseModel from apps.core.models (gives soft delete and timestamps).
3. Expected problems raise a SarthiError type from apps.core.exceptions.
4. Use the logging module (logger = logging.getLogger(__name__)). Never print secrets or personal data.
5. Secrets and passwords live only in .env.

## Settings choice
- manage.py uses development settings. wsgi.py and asgi.py use production settings.

## Error handling
- API errors always return {"error": {"code", "message"}}.
- Unknown errors are logged in full (logs/errors.log) but shown to the user as a generic message.

## Logging
- logs/sarthi.log (everything) and logs/errors.log (errors only), each line tagged with a request ID.

## Phase 2 additions

### Dashboard and menu
- templates/base.html is the shell (top bar, left sidebar, footer, light/dark mode). Bootstrap 5.3.3 and Bootstrap Icons are stored locally in static/vendor/.
- New apps add their sidebar entry by calling register_menu(...) from apps.core.navigation inside their AppConfig.ready(). The core never needs editing.
- Pages that only administrators may see use the staff_required decorator (apps/core/views.py).

### Audit trail
- Table AuditLog (read-only). Records logins, failed logins, logouts, backups, restores, and create/update/delete of accounts.User and of every model that inherits BaseModel.
- Stores the NAMES of changed fields, never the values. A model's __str__ text is stored, so it must never contain account numbers or ID numbers.

### Backups
- apps/core/backup.py. Commands: backup_db, verify_backup, restore_backup.
- A backup is a zip (database plus manifest with a checksum), encrypted with the key BACKUP_ENCRYPTION_KEY from .env, stored in backups/ as sarthi_<kind>_<date>_<time>.zip.enc.
- Kinds: manual, auto (daily, pruned to the newest 14), pre-restore (safety copy made before every restore).
- Optional second copy: BACKUP_COPY_DIR in .env.
- Restore is command-line only, needs typed confirmation, and makes a safety backup first.
- LOSING THE KEY MAKES BACKUPS UNREADABLE. Keep a copy of .env in a safe place outside the PC.
- Windows Task Scheduler task "Sarthi Daily Backup" runs at 21:00 (runs later if the PC was off).

## Phase 3 additions

### Encryption (apps/core/fields.py)
- Key: FIELD_ENCRYPTION_KEY in .env (optional FIELD_ENCRYPTION_OLD_KEYS list for key rotation).
- EncryptedTextField: text stored encrypted in the database, plain in the app. Cannot be searched or filtered.
- encrypt_bytes / decrypt_bytes: used for vault files.
- LOSING THE KEY MAKES ENCRYPTED DATA UNRECOVERABLE. Keep a copy of .env outside the PC.

### Family app (apps/family)
- Person (BaseModel): full_name, relationship, date_of_birth, notes (encrypted). Not a login user. Shared by every later app.

### Vault app (apps/vault)
- Document (BaseModel): title, type, person, notes (encrypted), expiry date, file details. Titles are NOT encrypted (they show in lists and the audit log): never put account numbers in a title.
- Files are encrypted and stored as data/vault/<xx>/<random>.bin. Never served as static files; downloads go through a login-protected page and are audited.
- Allowed: PDF, JPG, PNG, .docx, .xlsx, max 10 MB. File contents are checked against the extension. Macro files (.docm, .xlsm, vbaProject) and old .doc/.xls are refused. Sarthi never opens or runs the files.
- Other apps link to documents with a ManyToManyField to vault.Document (the vault never depends on finance).

### Backups (updated)
- Backup zip format 2: database + manifest + vault files, every file checksummed. Phase 2 backups still restore.
- Restore adds or overwrites vault files, never deletes them. A safety backup is made first.
- Safety stop at about 700 MB of vault content (backups are built in memory).

### Sessions
- Sign-out after SESSION_IDLE_MINUTES (default 30) of inactivity.
