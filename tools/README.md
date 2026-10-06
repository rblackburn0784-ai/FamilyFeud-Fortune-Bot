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

The healthcheck does **not** connect to Discord. It checks required source files, `.env`, Python compilation, question JSON quality, runtime JSON, SQLite readability, board template availability, and detected slash commands.

## V1.4.4 Question Admin Patcher

Run this once after pulling V1.4.4:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
```

This adds Discord-side question management:

- `/feud_question_review`
- `/feud_question_report`
- `/feud_category_list`
- `/feud_category_preview`
- `/feud_disable_question`
- `/feud_enable_question`
- `/feud_alias_cleanup`

It also patches the normal question picker so disabled questions are skipped during regular gameplay.

The patcher writes a local backup named:

```text
main.py.v1_4_4_question_admin_backup
```

## V1.4.3 Discord Presentation Patcher

Run this once after pulling V1.4.3 or newer if not already applied:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

This improves the Discord chat presentation by adding richer live-round embeds, `/feud_live`, active round buttons, improved `/feud_board`, better correct/wrong answer embeds, Top Answer callouts, Board Clear wording, and cleaner steal phase/result embeds.

The patcher writes a local backup named:

```text
main.py.v1_4_3_presentation_backup
```

## V1.4.2 Board UI Polish Patcher

Run this once after pulling V1.4.2 or newer if not already applied:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
```

This replaces the old hard-coded `render_board_image` body in `main.py` with a small wrapper around `feudbot.board_renderer.render_game_board`.

The reusable renderer adds centred diagonal strike X geometry, co-ordinates in `assets/board_layout.json`, safer long-answer fitting, optional revealed-answer glow, team score outlines, and a round-type badge.

The patcher writes a local backup named `main.py.v142.bak` the first time it edits the file.

## Board Preview Tool

Generate preview PNGs without connecting to Discord:

```powershell
.\.venv\Scripts\python.exe tools\render_board_preview.py
```

It writes preview boards to:

```text
rendered_boards/previews/
```

## V1.4 Board Polish Patcher

The original V1.4 patcher is kept for history:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_board_polish.py
```

For new installs, prefer the V1.4.2 patcher because it moves rendering into reusable modules instead of only patching the strike drawing block.

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
