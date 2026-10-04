# Family Feud Fortune Bot

A Discord Family Fortunes / Family Feud style bot with team play, host controls, rendered game boards, question packs, custom server questions, leaderboards, Fast Money, lobbies, daily surveys, weekly challenges, rivalries, and question-quality tools.

## Current Version

`1.4.0`

## V1.4 Board Polish & Question QA

V1.4 adds a practical board fix and a proper question-pack review workflow.

### Board strike alignment

The rendered board previously drew strike crosses using a font-rendered `X`. Font metrics can shift between machines, which is why the crosses could drift inside the strike boxes.

Run this once after pulling V1.4:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_board_polish.py
```

The patcher replaces the strike drawing block in `main.py` with centred diagonal line geometry.

### Question audit

Run this to scan the built-in question packs and optional custom question file:

```powershell
.\.venv\Scripts\python.exe tools\question_audit.py
```

It writes:

- `reports/question_audit_report.md`
- `reports/question_audit_findings.csv`
- `reports/question_web_check_candidates.csv`

The audit checks JSON structure, duplicate questions/answers, point ordering, suspicious/vague answers, category names, and fact/current-sensitive wording that needs manual or web checking.

> Family Feud / Family Fortunes answers are survey-style answers, not normal quiz facts. The internet can help with factual/current prompts, but most boards should be judged for plausibility, fun, short answer wording, fair scoring, and play feedback.

## V1.3 Modularisation & Health Command

V1.3 started the modularisation path by adding a `feudbot/` package:

- `feudbot/version.py` keeps version metadata out of the main bot file.
- `feudbot/diagnostics.py` contains reusable health and diagnostics helpers.
- `feudbot/health_command.py` contains the Discord `/feud_health` command registration.
- `tools/apply_v1_3_modularisation.py` safely patches the large existing `main.py` to wire in the new command.

Run this once after pulling V1.3 or newer if your local `main.py` has not been patched yet:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_3_modularisation.py
```

After restarting the bot, Discord will sync:

```text
/feud_health
```

It reports version, uptime, Discord latency, server count, active rounds, question pool size, custom questions, SQLite status, and board-template status.

## V1.2 Diagnostics & Operator Tools

V1.2 added a local healthcheck for checking setup before starting the bot:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

It checks required files, `.env`, `main.py` syntax, question JSON structure, runtime JSON, SQLite readability, board template presence, and detected slash commands.

## V1.1 Stability & Repo Hygiene

V1.1 cleaned up the repo and added safer defaults:

- `.gitignore` for secrets, virtual environments, caches, runtime state, SQLite files, generated boards, and logs.
- `.env.example` for safer setup.
- Runtime files removed from the public source repo.

## Features

- Team-based Family Fortunes / Feud-style rounds.
- Red vs Blue team play with strikes, steals, captain mode, and host controls.
- Multiple game modes including Classic, Fast Money, Sudden Death, Teams Only, and Chaos.
- Question packs, categories, difficulty filtering, and autocomplete.
- Custom server questions and moderator-managed suggestions.
- Player profiles, achievements, daily/weekly/lifetime leaderboards, and rivalry stats.
- Daily survey prompts, weekly challenges, mini polls, and between-round callouts.
- Question analytics, bad-answer tracking, board ratings, and alias suggestions.
- Optional rendered PNG board using `assets/game_board_template.png`.

The bundled question pool contains 2,000 questions across 60 categories:

- `questions.json`: original base pack
- `extra_questions.json`: hand-curated fresh pack
- `mega_questions.json`: large expansion pack

## Setup

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

2. Install dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add your Discord bot token:

   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   ```

4. Enable **Message Content Intent** in the Discord Developer Portal.

5. Run the patchers/checks after pulling the latest version:

   ```powershell
   .\.venv\Scripts\python.exe tools\apply_v1_3_modularisation.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_board_polish.py
   .\.venv\Scripts\python.exe tools\healthcheck.py
   .\.venv\Scripts\python.exe tools\question_audit.py
   ```

6. Run the bot:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

## Runtime Files

These files are created or updated while the bot runs and should stay local to the machine/server hosting the bot:

- `active_games.json`
- `engagement_state.json`
- `server_scores.json`
- `custom_questions.json`
- `server_settings.json`
- `fortune_bot.sqlite3`
- `rendered_boards/`
- `reports/`

## Useful Commands

- `/feud_health` shows bot version, uptime, latency, content counts, active rounds, SQLite status, and board asset status.
- `/feud_menu` opens the main button menu.
- `/feud_start` starts a round with category packs and game modes.
- `/feud_lobby` opens a pre-game lobby with team joins and category voting.
- `/feud_join` joins the current round on Red or Blue team.
- `/feud_board` shows the current board.
- `/feud_admin` opens host controls.
- `/feud_admin_menu` opens the compact host/admin control menu.
- `/feud_fast_money` starts a solo 5-question Fast Money challenge.
- `/feud_add_question` adds custom questions for the current server.
- `/feud_custom_questions`, `/feud_edit_custom`, and `/feud_delete_custom` manage server questions.
- `/feud_settings` adjusts cooldowns, strikes, timers, steal mode, and more.
- `/feud_blacklist_word`, `/feud_unblacklist_word`, and `/feud_pause` provide moderation controls.
- `/feud_leaderboard` supports lifetime, weekly, and daily boards.
- `/feud_profile` shows a player's stat profile.
- `/feud_validate_questions` checks question data quality inside Discord.
- `/feud_question_analytics` shows freshness and performance stats.
- `/feud_daily_survey` posts the daily casual survey prompt.
- `/feud_mini_poll` posts a quick between-round poll.
- `/feud_challenge` shows this week's challenge.
- `/feud_rivalry` shows Red vs Blue or player-vs-player rivalry stats.
- `/feud_suggest` lets players suggest future questions.
- `/feud_approve_suggestion` turns a suggestion into a server custom question.

## Local Question Manager

Run this to browse, search, and validate the bundled question files:

```powershell
.\.venv\Scripts\python.exe question_manager.py
```

Then open `http://127.0.0.1:8765`.

## Recommended Next Steps

Suggested follow-up upgrades after V1.4:

1. Use `reports/question_audit_findings.csv` to clean up flagged boards.
2. Add a Discord `/feud_question_report` command using the same audit logic.
3. Split board rendering into `feudbot/rendering.py`.
4. Add board themes such as classic, neon arcade, pub quiz, mafia noir, Dude bowling, and Christmas.
5. Build a guided Game Night mode with lobby, category vote, normal rounds, double/triple points, Fast Money, and a winner ceremony.
