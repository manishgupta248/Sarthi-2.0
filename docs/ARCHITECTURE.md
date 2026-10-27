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
