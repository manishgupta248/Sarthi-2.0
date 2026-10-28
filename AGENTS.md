# AGENTS.md - Permanent rules for Sarthi (read this first in every new chat)

## Project
Sarthi: ONE Django platform with pluggable apps, for personal and family use.
Folder: D:\Sarthi. GitHub: private repo Sarthi-2.0. PC: Windows, i5, 16GB RAM, no graphics card.

## About the user
Non-programmer professional. Use plain English only.

## How we work (mandatory)
1. Claude does not write project files by itself. Claude gives complete step-by-step instructions for a whole phase; the user runs them and reports back.
2. Every PowerShell command and file change is explicit and complete: full paths, full code blocks, exact commands.
3. Each phase ends with a smoke test. Smoke tests are the main validation.
4. CURRENT_STATE.md is updated only at phase completion or when the user asks.
5. Claude must not blindly agree. Flag complexity, technical debt and security risk plainly before implementing.
6. Documentation is updated after every major step.

## Technology decisions
- Python 3.13, Django (latest LTS), Django REST Framework (kept minimal at first)
- SQLite first; later a stronger database
- Frontend: Django templates + Bootstrap 5 (later HTMX); no JavaScript framework for now
- Pydantic for data validation. No LangChain at first. LangGraph only if a real workflow needs it.
- LLM order: deterministic rules first, then local Ollama (CPU only), then cloud models for NON-sensitive text only.
- Sensitive data (IDs, bank, health) NEVER goes to cloud LLMs.
- Telegram bot answers only the owner's Telegram user ID.
- Reminders only run while the PC is on; check for missed reminders at startup.

## Folder layout (project root)
apps/ (pluggable apps), config/ (Django settings), templates/, static/, data/, backups/, logs/, docs/, scripts/

## Git rules
- main = stable and working. develop = daily work.
- Merge develop into main only after the smoke test passes.
- Never commit .env, databases, backups, logs or keys.

## Starting a new chat
Paste AGENTS.md and CURRENT_STATE.md, then say which phase or step you are on.

## Daily commands (run from D:\Sarthi with .venv active)
- Start the app: python manage.py runserver
- Run tests: python manage.py test
- Phase smoke test: .\scripts\smoke_phase1.ps1
- Work on branch develop. Merge into main only after the smoke test passes.

## Phase 2 rules
- New apps: register a sidebar entry with register_menu() in AppConfig.ready().
- Data models inherit BaseModel (soft delete plus audit trail). A model __str__ must not contain private numbers.
- Backups: python manage.py backup_db | verify_backup | restore_backup FILENAME. Keep the .env copy outside the PC.
- Phase smoke test: .\scripts\smoke_phase2.ps1

## Phase 3 rules
- Sensitive text fields use EncryptedTextField (apps.core.fields). Never put private numbers in titles or __str__ (they appear in lists and the audit log).
- Documents and files go through the vault (apps/vault). Link to them with a ManyToManyField to vault.Document.
- People live only in apps/family (Person). Other apps link to Person.
- NEVER store passwords, PINs, CVV, OTPs or full card numbers.
- Keep a copy of .env (SECRET_KEY, BACKUP_ENCRYPTION_KEY, FIELD_ENCRYPTION_KEY) outside the PC.
- Phase smoke test: .\scripts\smoke_phase3.ps1

## Phase 4A rules
- Wealth code lives in apps/wealth. Money is Decimal in INR; show it with the inr template filter.
- Never display a stored account number or customer ID except through the audited Reveal view.
- To add a card to the home dashboard, call register_dashboard_widget in AppConfig.ready().
- Phase smoke test: .\scripts\smoke_phase4a.ps1

## Phase 4B rules
- Transactions and balance checks live in apps/wealth (models.py, reconciliation.py, views_transactions.py).
- Never put account numbers in transaction descriptions; references are encrypted.
- Phase smoke test: .\scripts\smoke_phase4b.ps1

## Phase 4C rules
- Report logic lives in apps/wealth/reports.py as plain functions (no HTML), so other channels can reuse it.
- When adding a transaction category, set its group; the group decides how reports count it.
- Phase smoke test: .\scripts\smoke_phase4c.ps1

## Phase 5 rules
- Investments, loans given and liabilities are Holding records (apps/wealth). To add a new type, add it to Holding.Kind and to KIND_FIELDS, KIND_LABELS and REQUIRED in forms_holdings.py (and LIABILITY_KINDS if it is a liability).
- Value logic lives in apps/wealth/networth.py as plain functions (no HTML) so reminders and Telegram can reuse them.
- Phase smoke test: .\scripts\smoke_phase5.ps1
