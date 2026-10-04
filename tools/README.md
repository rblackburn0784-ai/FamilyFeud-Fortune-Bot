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

## V1.4 Board Polish Patcher

Run this once after pulling V1.4 to fix strike-cross alignment on the rendered board:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_board_polish.py
```

The patcher changes the strike marks from font-rendered `X` glyphs to centred diagonal geometry, so the crosses line up consistently inside the strike boxes.

## Question Audit

Run this to check the built-in question packs and optional server custom question file:

```powershell
.\.venv\Scripts\python.exe tools\question_audit.py
```

It creates:

- `reports/question_audit_report.md`
- `reports/question_audit_findings.csv`
- `reports/question_web_check_candidates.csv`

The audit checks structure, duplicate questions/answers, scoring shape, overly long or vague answers, category names, and fact/current-sensitive prompts that need manual or web verification.
