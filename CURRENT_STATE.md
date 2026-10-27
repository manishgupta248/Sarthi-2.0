# CURRENT_STATE.md

Last updated: 27-10-2026

## Phase status
- Phase 0 (setup, Git, documents): done
- Phase 1 (core): done
- Phase 2 (dashboard shell, audit trail, backup and restore): done
- Phase 3 (family and vault foundation): done when the Phase 3 smoke test passes and main is updated
- Phase 4 (Wealth v1: accounts, snapshots, transactions, dashboard): not started

## What exists
- Everything from Phases 1 and 2
- Family app (people records) and Document vault (encrypted files: PDF, JPG, PNG, docx, xlsx)
- EncryptedTextField for sensitive text; FIELD_ENCRYPTION_KEY in .env
- Backups include vault files (zip format 2); restore drill with files passed
- 30-minute idle sign-out
- Soft delete and audit trail now exercised by a real model (Person, Document)

## Next
Phase 4: Wealth v1 (institutions, accounts with encrypted numbers and masked display with audited reveal, balance snapshots, major transactions with reconciliation, wealth dashboard with charts). Accounts link to documents and nominee from the Person list.

## Known issues and open items
- No login lockout after repeated wrong passwords. Add django-axes before Sarthi is reachable from anywhere except this PC.
- Production run method (serving static files when DEBUG is off, for example WhiteNoise plus Waitress) is not set up yet.
- SQLite WAL mode not enabled yet.
- Backups are built in memory; vault limit about 700 MB before a redesign is needed.
- Uploads larger than the limit are rejected only after Django has received them (single-user PC, low risk).
- Windows may print a harmless warning when a log file rotates while the dev server auto-reloads.
- Dashboard has no widgets from other apps yet; a widget registry will be added with the wealth dashboard.
