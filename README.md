# Family Feud Fortune Bot

A Discord Family Fortunes / Family Feud style bot with team play, host controls, rendered game boards, question packs, custom server questions, leaderboards, Fast Money, lobbies, daily surveys, weekly challenges, rivalries, and question-quality tools.

## Current Version

`1.4.3`

## V1.4.3 Discord Presentation Upgrade

V1.4.3 improves the in-Discord game presentation without changing the core scoring rules.

Added:

- `tools/apply_v1_4_3_presentation_upgrade.py`
- `docs/V1.4.3_DISCORD_PRESENTATION.md`
- `/feud_live` compact live-round panel
- richer `/feud_board` layout
- active round buttons:
  - Show Board
  - Join Red
  - Join Blue
  - Scores
  - Host Controls
- better correct-answer embeds
- Top Answer callout when answer #1 is found
- better wrong-answer embeds with strike pressure text
- better steal incoming/result embeds
- Board Clear wording when every answer is found

Run this once after pulling V1.4.3:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

Then run:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

Restart the bot and Discord should sync:

```text
/feud_live
```

## V1.4.2 Board UI Polish

V1.4.2 moves the PNG board rendering into reusable modules and adds local preview tooling so visual issues can be checked without running Discord.

Added:

- `feudbot/board_config.py`
- `feudbot/board_renderer.py`
- `assets/board_layout.json`
- `tools/apply_v1_4_2_board_ui_polish.py`
- `tools/render_board_preview.py`
- `docs/V1.4.2_BOARD_UI_POLISH.md`

Board improvements:

- Strike Xs are drawn as centred diagonal geometry rather than font-rendered text.
- Strike co-ordinates now live in `assets/board_layout.json`.
- Revealed answers can show a subtle glow.
- Long answers shrink more safely to fit the row.
- Red and Blue score boxes have team-colour outlines.
- The board now has a small round-type badge.
- Preview images can be generated locally for 0/1/2/3 strikes, partial reveal, completed board, and mode badges.

Run this once after pulling V1.4.2 or newer:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
```

Then generate local preview boards:

```powershell
.\.venv\Scripts\python.exe tools\render_board_preview.py
```

Preview images are written to:

```text
rendered_boards/previews/
```

## V1.4.1 Question Audit False-Positive Fix

V1.4.1 tightens the question-audit logic so it no longer treats valid underscore categories such as `big_lebowski`, `social_media`, or `random_weird` as unknown categories, and no longer matches fact-check terms inside unrelated words such as `talking` or `checking`.

## V1.4 Board Polish & Question QA

V1.4 added a practical board fix and a proper question-pack review workflow.

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
- Improved Discord presentation with `/feud_live` and active round buttons.

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
   .\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
   .\.venv\Scripts\python.exe tools\render_board_preview.py
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
- `/feud_live` shows the compact live round panel with action buttons.
- `/feud_start` starts a round with category packs and game modes.
- `/feud_lobby` opens a pre-game lobby with team joins and category voting.
- `/feud_join` joins the current round on Red or Blue team.
- `/feud_board` shows the current board with the presentation panel.
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

Suggested follow-up upgrades after V1.4.3:

1. Test `/feud_live`, `/feud_board`, correct/wrong answer posts, and steal phase in Discord.
2. Add real Double Points and Triple Points scoring modes so the board badge has full gameplay support.
3. Add a Discord `/feud_question_report` command using the question-audit logic.
4. Build a guided Game Night mode with lobby, category vote, normal rounds, double/triple points, Fast Money, and a winner ceremony.
5. Add board/themes such as classic, neon arcade, pub quiz, mafia noir, Dude bowling, and Christmas.
