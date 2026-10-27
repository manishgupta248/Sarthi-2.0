# CURRENT_STATE.md

Last updated: 27-10-2026

## Phase status
- Phase 0 (setup, Git, documents): done
- Phase 1 (core): done
- Phase 2 (dashboard shell, audit trail, backup and restore): done when the Phase 2 smoke test passes and main is updated
- Phase 3 (Tasks and Reminders app): not started

## What exists
- Everything from Phase 1 (Django 5.2, custom user, settings split, logging, error handling, health page, tests)
- Login page and Bootstrap 5 dashboard shell with plug-in sidebar menu, dark mode, mobile layout
- Audit trail (AuditLog, read-only, field names only) visible at /system/audit/
- Encrypted backups: web page /system/backups/, commands backup_db, verify_backup, restore_backup
- Daily automatic backup via Windows Task Scheduler ("Sarthi Daily Backup", 21:00)
- Restore drill completed successfully

## Next
Phase 3: first real app (Tasks and Reminders, manual entry) built on BaseModel and the menu registry. Also decide how the stable main version is run day to day.

## Known issues and open items
- No login lockout after repeated wrong passwords. Add django-axes before Sarthi is reachable from anywhere except this PC.
- Soft delete (BaseModel) has no automated test yet; it will be tested with the first real model in Phase 3.
- Production run method (serving static files when DEBUG is off, for example WhiteNoise plus Waitress) is not set up yet.
- SQLite WAL mode not enabled yet (consider when the Telegram bot and web run together).
- Windows may print a harmless warning when a log file rotates while the dev server auto-reloads.
