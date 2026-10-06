# Tools

Local operator tools for Family Feud Fortune Bot.

## Healthcheck

Run this before starting the bot, after pulling updates, or before a Discord game night:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

The healthcheck does **not** connect to Discord. It checks required files, `.env`, Python compilation, question JSON quality, runtime JSON, SQLite readability, board template availability, and detected slash commands.

## V1.4.5 Game Night Patcher

Run this once after pulling V1.4.5:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_5_game_night.py
```

This adds a guided Game Night session layer:

- `/feud_game_night`
- `/feud_game_night_score`
- `/feud_game_night_next`
- `/feud_game_night_finish`
- Red/Blue lobby buttons
- Auto-balance
- Category voting
- locked teams
- session scoreboard
- winner ceremony and awards

The patcher writes a local backup named:

```text
main.py.v1_4_5_game_night_backup
```

## V1.4.4 Question Admin Patcher

Run this once after pulling V1.4.4 or newer if not already applied:

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
