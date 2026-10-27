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
