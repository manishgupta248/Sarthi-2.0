# CURRENT_STATE.md

Last updated: 27-10-2026

## Phase status
- Phases 0 to 3: done
- Phase 4A (accounts, balance snapshots, wealth dashboard, Excel export): done when the Phase 4A smoke test passes and main is updated
- Phase 4B (major transactions, reconciliation, needs-attention extras): not started

## What exists
- Everything from Phases 1 to 3 (core, dashboard shell, audit, encrypted backups with vault files, family, encrypted vault)
- Wealth app: institutions, accounts (encrypted number and customer ID, masked display, audited Reveal, joint holders, nominee, linked vault documents), balance snapshots, Update balances page, wealth dashboard with charts and needs-attention list, home dashboard Wealth card, masked Excel export
- Account types editable in the admin site (8 defaults loaded)
- Dashboard widget registry and Indian money format

## Next
Phase 4B: major transactions per account, calculated balance versus reported balance (reconciliation), categories as an editable list, extra attention items. Then Phase 5 (FDs, bonds, insurance, loans given, liabilities, net worth).

## Known issues and open items
- No login lockout after repeated wrong passwords. Add django-axes before Sarthi is reachable from anywhere except this PC.
- Production run method (static files when DEBUG is off, for example WhiteNoise plus Waitress) is not set up yet.
- Archiving a person does not archive or block their accounts (to be guarded in a later phase).
- Charts keep the colours of the theme they were loaded with; reload the page after switching light/dark mode.
- Excel exports are not encrypted; delete them after use.
- Backups are built in memory; vault limit about 700 MB before a redesign is needed.
- SQLite WAL mode not enabled yet.
