# Tools

Local operator tools for Family Feud Fortune Bot.

## Healthcheck

Run this before starting the bot, after pulling updates, or before a Discord game night:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

Or on macOS/Linux:

```bash
python tools/healthcheck.py
```

The healthcheck does **not** connect to Discord. It checks:

- required source files
- `.env` / `.env.example` setup
- Python compilation of `main.py`
- built-in question JSON quality
- optional runtime JSON validity
- SQLite database readability
- board template availability
- slash-command surface detected in `main.py`
