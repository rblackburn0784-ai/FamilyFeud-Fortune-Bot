# Family Feud Fortune Bot

A Discord Family Fortunes game bot with team play, host controls, question packs, custom server questions, per-server settings, daily and weekly leaderboards, timers, persistent in-progress rounds, rendered game boards, Fast Money, lobbies, daily surveys, weekly challenges, rivalries, and question-quality tools.

## Current Version

`1.3.0`

## V1.3 Modularisation & Health Command

V1.3 starts the proper modularisation path by adding a `feudbot/` package:

- `feudbot/version.py` keeps version metadata out of the main bot file.
- `feudbot/diagnostics.py` contains reusable health and diagnostics helpers.
- `feudbot/health_command.py` contains the Discord `/feud_health` command registration.
- `tools/apply_v1_3_modularisation.py` safely patches the large existing `main.py` to wire in the new command.

Because the existing bot still lives in a very large single `main.py`, V1.3 uses a safe patcher rather than a risky full-file rewrite. Run this once after pulling V1.3:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_3_modularisation.py
```

Then run the local healthcheck:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

After restarting the bot, Discord will sync the new command:

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

V1.1 focuses on making the project safer to clone, run, and maintain:

- Added `.gitignore` rules for secrets, virtual environments, Python caches, runtime JSON state, SQLite databases, generated board images, and logs.
- Added `.env.example` so setup is clearer without exposing a real Discord token.
- Documented which files are source files and which files are runtime state.
- Cleaned the intended repository shape so future upgrades can be made without committing local bot data.

> Existing installs can keep their local runtime files. New commits should avoid adding `.env`, `fortune_bot.sqlite3`, `active_games.json`, `server_scores.json`, `engagement_state.json`, `custom_questions.json`, `server_settings.json`, `rendered_boards/`, or `__pycache__/`.

## Features

- Team-based Family Fortunes / Feud-style rounds.
- Red vs Blue team play with strikes, steals, captain mode, and host controls.
- Multiple game modes including classic, Fast Money, Sudden Death, Teams Only, and Chaos.
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

The bot also supports a rendered PNG game board using `assets/game_board_template.png`.
If that file exists, round boards are posted as a full game-show image with scores,
strikes, answers, and points drawn onto the template.

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

   Guesses are read from normal channel messages, so the bot needs this intent enabled.

5. Optional but recommended: run the healthcheck:

   ```powershell
   .\.venv\Scripts\python.exe tools\healthcheck.py
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

Runtime state is still written to JSON files for readability and mirrored into `fortune_bot.sqlite3` for safer long-term storage.

## Useful Commands

- `/feud_health` shows bot version, uptime, latency, content counts, active rounds, SQLite status, and board asset status.
- `/feud_menu` opens the main button menu.
- `/feud_start` starts a round with category packs and game modes.
- `/feud_lobby` opens a pre-game lobby with team joins and category voting.
- `/feud_join` joins the current round on Red or Blue team.
- `/feud_board` shows the current board.
- `/feud_admin` opens host buttons for board, reveal, skip, clear strikes, reveal all, and stop.
- `/feud_admin_menu` opens the compact host/admin control menu.
- `/feud_fast_money` starts a solo 5-question Fast Money challenge.
- `/feud_add_question` adds custom questions for the current server.
- `/feud_custom_questions`, `/feud_edit_custom`, and `/feud_delete_custom` manage server questions.
- `/feud_settings` adjusts cooldowns, strikes, timers, steal mode, and more.
- `/feud_blacklist_word`, `/feud_unblacklist_word`, and `/feud_pause` provide moderation controls.
- `/feud_leaderboard` supports lifetime, weekly, and daily boards.
- `/feud_profile` shows a player's richer stat profile.
- `/feud_validate_questions` checks built-in and custom question quality.
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

Suggested follow-up upgrades after V1.3:

1. Split storage helpers into `feudbot/storage.py`.
2. Move dataclasses into `feudbot/models.py`.
3. Move question loading/matching into `feudbot/questions.py`.
4. Move board rendering into `feudbot/rendering.py`.
5. Move Discord views and commands into `feudbot/views/` and `feudbot/commands/`.
6. Add board themes such as classic, neon arcade, pub quiz, mafia noir, Dude bowling, and Christmas.
7. Build a guided Game Night mode with lobby, category vote, normal rounds, double/triple points, Fast Money, and a winner ceremony.
