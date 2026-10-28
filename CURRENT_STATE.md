# CURRENT_STATE.md

Last updated: 28-10-2026

## Phase status
- Phases 0 to 3: done
- Phases 4A, 4A-2, 4B, 4C (accounts, balances, transactions, reports): done
- Phase 5 (investments, liabilities, net worth): done when the Phase 5 smoke test passes and main is updated
- Phase 4D (bulk re-categorise, budgets, duplicate detection): planned
- Phase 6 (Tasks and Reminders): not started

## What exists
- Everything from earlier phases
- Holdings: fixed and recurring deposits, bonds, insurance, loans given, gold, property, other assets, and liabilities (loans, card dues), each with a type-specific form
- Recorded values with estimates for deposits, Update values page, Net worth page with 12-month trend, upcoming due dates and maturities, attention list, Excel export, home dashboard net worth card

## Next
Phase 6 (Tasks and Reminders, using the due dates, maturities, document expiries and stale values already tracked) or Phase 4D (bulk re-categorise, budgets, duplicate detection), as you prefer.

## Known issues and open items
- No login lockout after repeated wrong passwords. Add django-axes before Sarthi is reachable from anywhere except this PC.
- Production run method (static files when DEBUG is off, for example WhiteNoise plus Waitress) is not set up yet.
- Archiving a person does not archive or block their accounts and holdings (to be guarded in a later phase).
- Deposit estimates are approximations (no TDS, penalties or bank-specific rules). Recorded values override them.
- Charts keep the colours of the theme they were loaded with; reload after switching light/dark mode.
- Excel exports are not encrypted; delete them after use.
- Backups are built in memory; vault limit about 700 MB before a redesign is needed.
- SQLite WAL mode not enabled yet.
