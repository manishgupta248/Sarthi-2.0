# DECISIONS.md - why we chose things

- 27-10-2026: One Sarthi with pluggable apps, not copied projects (avoids copies drifting apart and repeated security fixes).
- 27-10-2026: Bootstrap 5 + Django templates first (simplest; JavaScript framework can come later).
- 27-10-2026: Sensitive data stays local; cloud LLMs only see non-sensitive text.
- 27-10-2026: User enters family data; no family logins at first.
- 27-10-2026: Runs only while the PC is on; missed-reminder check at startup.
- 27-10-2026: No LangChain at first; own small LLM layer that can switch between Ollama, Gemini and Grok.
- 27-10-2026: No graphics card, so local model runs on CPU as a small helper only.
- 27-10-2026: Login by username, not email (simpler; email login is hard to change later).
- 27-10-2026: Django 5.2 LTS pinned; exact versions recorded in requirements-lock.txt.
- 27-10-2026: Soft delete by default via BaseModel; hard_delete() only on purpose.
- 27-10-2026: Every log line carries a request ID; unknown errors are logged privately and shown generically.
- 27-10-2026: Django admin is the temporary data-entry screen until the dashboard (Phase 2).
