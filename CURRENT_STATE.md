# CURRENT_STATE.md

Last updated: 27-10-2026

## Phase status
- Phase 0 (setup, Git, documents): done
- Phase 1 (core): done when the Phase 1 smoke test passes and main is updated
- Phase 2 (dashboard shell, audit, backup and restore): not started

## What exists
- Django 5.2 project with development and production settings (config/settings/)
- Custom user model (apps/accounts), login by username
- Core app (apps/core): soft-delete BaseModel, SarthiError types, request ID middleware, logging to logs/, health page at /health/
- Secrets in .env (not in Git); .env.example is the template
- Database: data/db.sqlite3 (not in Git)
- Admin site at /admin/ used for temporary data entry
- Automated tests (python manage.py test) and scripts/smoke_phase1.ps1

## Next
Phase 2: dashboard shell (Bootstrap 5: top bar, left sidebar, footer), audit trail, backup and restore with a restore test.

## Known issues
- Windows may print a harmless warning when a log file rotates while the dev server auto-reloads.
- The home page / has no content until Phase 2.
