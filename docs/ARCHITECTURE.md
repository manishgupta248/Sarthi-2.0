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

## Phase 4A additions (apps/wealth)

### Models
- Institution, AccountType (editable list, seeded by migration, edit in the admin site), Account, BalanceSnapshot. All inherit BaseModel (soft delete and audit trail).
- Account: holder, joint holders and nominee are Person records (apps/family). Account number, customer ID and remarks are encrypted. Only the last 4 characters of the number are kept readable (account_number_last4) for masked display and search. Documents link through a ManyToManyField to vault.Document.
- BalanceSnapshot: one active snapshot per account per day (database rule). Amounts are Decimal (INR).

### Rules
- Numbers are shown masked everywhere. The only way to see a full number is the Reveal button (POST, staff only, audited, hides after 30 seconds). Edit pages never show stored numbers.
- Audit log stores field names only. Account __str__ and nickname must never contain numbers.
- A joint account is counted once, under the main holder. Closed accounts are left out of today's totals but included in the history chart up to their closing date.
- A balance older than 90 days (STALE_DAYS in services.py) appears in "Needs attention".
- Wealth totals live in apps/wealth/services.py (wealth_summary, monthly_trend).

### Excel export
- apps/wealth/export.py builds one sheet with all accounts and a total. Masked by default; "full details" option is audited. Text that starts like a formula is neutralised. The file is not encrypted: delete it after use.

### Plug-in dashboard and menu
- Apps call register_menu and register_dashboard_widget (apps/core/navigation.py) in AppConfig.ready(). The home dashboard shows registered widget cards; a failing widget is logged and skipped.
- Template filters: inr (Indian money format) and mask_last4 in apps/core/templatetags/sarthi_extras.py.
- Charts use Chart.js stored locally in static/vendor/chartjs/.

## Phase 4A-2 changes (account form)
- Joint holder is one dropdown on the form (the database table can still hold several). Saving keeps exactly the chosen one.
- Remarks are separate encrypted entries (AccountRemark), added one by one on the account page. The add form has an optional first remark. The former single Account.remarks field was copied into entries and removed (migrations 0003 to 0005).
- Documents are uploaded from the account page through apps/vault/services.py (store_document), the same checked and encrypted path the Vault page uses. They are linked to the account and filed under the holder. Unlink removes only the link.

## Phase 4B additions (transactions and balance checking)

### Models
- TransactionCategory (editable list, seeded, edit in the admin site) and Transaction (BaseModel): account, date, direction (in or out), positive amount, category, description, counterparty, reference (encrypted).
- Account.full_tracking: tick for accounts where every transaction is recorded; enables mismatch warnings.

### Balance check (apps/wealth/reconciliation.py)
- Each recorded balance is a checkpoint, counted as of the END of its day. For consecutive checkpoints: earlier balance + money in - money out should equal the later balance. A difference under 1.00 counts as a match.
- Transactions dated on or before the first recorded balance are treated as already included in it.
- Estimated balance = last recorded balance + transactions after it. The wealth dashboard total still uses recorded balances only.
- Mismatch warnings appear in "Needs attention" only for accounts with full_tracking.

### Pages
- /wealth/transactions/ (filters, totals, pagination), add/edit/archive, /wealth/transactions/transfer/ (creates the out and in entries together, category Transfer), /wealth/accounts/<id>/reconciliation/.
- The audit log never contains amounts, descriptions or references.

## Phase 4C additions (browsing and reports)

### Browsing long transaction lists
- Nothing is ever moved or deleted to keep lists short. The Transactions page opens on the current month, with Year and Month buttons, All time, a custom date range, and 50-per-page pagination. /wealth/transactions/archive/ lists every year and month with counts and totals.
- Transaction has indexes on (account, date) and (date).

### Category groups and reports (apps/wealth/reports.py)
- Each TransactionCategory has a group: income, expense, investment, transfer, loan, other. Uncategorised transactions have no group.
- Income = in minus out (income group). Expenses = out minus in (expense group; refunds reduce it). Invested = out minus in (investment group). Left over = income - expenses - invested. Savings rate = left over / income.
- Transfers are left out. Loans, Other and uncategorised are shown separately ("Not classified") so nothing is hidden.
- basis "fy" (default) = Indian financial year April to March, identified by the year it starts in (2026 = FY 2026-27). basis "calendar" = January to December.
- Reports are plain functions returning data (monthly_summary, yearly_summary, category_breakdown, category_matrix, top_transactions) so other channels (Telegram, later) can reuse them.
- Pages: /wealth/reports/ (month by month, year by year), /wealth/reports/categories/ (with previous-period comparison, month-by-month table and largest items), Excel report at /wealth/reports/export/ (audited, no account numbers, not encrypted).
- Categories are managed at /wealth/categories/.

## Phase 5 additions (investments, liabilities, net worth)

### Model (apps/wealth/models.py)
- Holding (BaseModel): one record type for fixed deposits, recurring deposits, bonds, insurance, loans given, gold, property, other assets AND liabilities (home, car, personal, education loans, credit card dues, other). The kind decides which fields the form shows (apps/wealth/forms_holdings.py: KIND_FIELDS, KIND_LABELS, REQUIRED). LIABILITY_KINDS marks the liabilities.
- Policy, deposit and loan numbers are encrypted (identifier); only the last 4 characters are readable (identifier_last4). Revealing a number is audited.
- HoldingValuation: 'on this date it was worth (or still owed) this amount'; one active entry per holding per day.
- Documents link through ManyToMany to vault.Document and are uploaded with the same checked, encrypted function as accounts.

### Valuation rules (apps/wealth/networth.py: holding_value)
1. latest recorded value on or before the date ("recorded"); 2. fixed and recurring deposits: estimate from rate and dates ("estimated"; 365-day year, quarterly compounding by default, instalments compounded quarterly, no TDS or penalties); 3. bonds, loans given, gold, property, liabilities: original amount ("cost"); 4. otherwise none (for example insurance).
- Net worth = bank balances + asset holdings - liabilities, per type and per person. Closed holdings drop out after their closing date. Joint holdings count once, under the main holder.
- upcoming_events() lists maturities (60 days) and due dates (30 days) and flags overdue ones; holding_attention() flags missing and stale (over 180 days) values. Phase 6 reminders will reuse both.

### Pages
- /wealth/networth/, /wealth/investments/, /wealth/liabilities/, /wealth/holdings/add/<type>/, /wealth/holdings/<id>/, /wealth/values/update/, Excel export at /wealth/holdings/export/ (masked by default, audited, not encrypted).
- The home dashboard card now shows net worth.
