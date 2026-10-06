# Tools

Local operator tools for Family Feud Fortune Bot.

## V1.5 Question Pack Builder

Run this to generate the checked V1.5 expansion pack:

```powershell
.\.venv\Scripts\python.exe tools\build_v1_5_question_pack.py
```

Creates:

```text
v1_5_questions.json
reports/v1_5_question_pack_report.md
```

The builder generates roughly 3,000 additional survey-style boards and validates survey phrasing, categories, answer count, descending points, duplicates, and aliases.

## V1.5 Question Index Patcher

After building the pack, run:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_5_question_index.py
```

This patches `main.py` to load `v1_5_questions.json` and use `feudbot.question_index.QuestionIndex` for faster category/pack lookup.

Backup:

```text
main.py.v1_5_question_index_backup
```

## Healthcheck

Run this before starting the bot, after pulling updates, or before a Discord game night:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

The healthcheck does **not** connect to Discord. It checks required files, `.env`, Python compilation, question JSON quality, runtime JSON, SQLite readability, board template availability, and detected slash commands.

## V1.4.6 Scoring Modes Patcher

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_6_scoring_modes.py
```

Adds real support for Classic, Fast Money, Sudden Death, Double Points, Triple Points, and Chaos.

## V1.4.5 Game Night Patcher

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_5_game_night.py
```

Adds `/feud_game_night`, session teams, category voting, scoreboards, and winner ceremony.

## V1.4.4 Question Admin Patcher

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
```

Adds `/feud_question_review`, `/feud_question_report`, `/feud_category_list`, `/feud_category_preview`, `/feud_disable_question`, `/feud_enable_question`, and `/feud_alias_cleanup`.

## V1.4.3 Discord Presentation Patcher

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

Adds `/feud_live`, richer live-round embeds, active round buttons, improved `/feud_board`, better answer moments, and cleaner steal phase/result embeds.

## V1.4.2 Board UI Polish Patcher

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
```

Moves board rendering into reusable modules and uses `assets/board_layout.json` for layout configuration.

## Board Preview Tool

```powershell
.\.venv\Scripts\python.exe tools\render_board_preview.py
```

Writes preview boards to:

```text
rendered_boards/previews/
```

## Question Audit

```powershell
.\.venv\Scripts\python.exe tools\question_audit.py
```

Creates:

- `reports/question_audit_report.md`
- `reports/question_audit_findings.csv`
- `reports/question_web_check_candidates.csv`
