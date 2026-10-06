# Family Feud Fortune Bot

A Discord Family Fortunes / Family Feud style bot with team play, host controls, rendered game boards, question packs, custom server questions, leaderboards, Fast Money, lobbies, daily surveys, weekly challenges, rivalries, question-quality tools, presentation panels, Discord-side question review/admin tools, and guided Game Night flow.

## Current Version

`1.4.5`

## V1.4.5 Game Night Flow

V1.4.5 adds a guided party-session layer on top of the existing round system.

Added:

- `tools/apply_v1_4_5_game_night.py`
- `docs/V1.4.5_GAME_NIGHT_FLOW.md`
- `/feud_game_night`
- `/feud_game_night_score`
- `/feud_game_night_next`
- `/feud_game_night_finish`
- Game Night lobby with Red/Blue buttons
- Auto-balance teams
- Category voting
- Locked teams once Game Night starts
- Session score separate from lifetime score
- Between-round scoreboard
- Round intro screen
- Fast Money finale prompt
- Winner ceremony and awards

Run this once after pulling V1.4.5:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_5_game_night.py
```

Then run:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

Restart the bot and Discord should sync the new commands.

### Game Night flow

```text
Lobby opens
Players join Red/Blue
Category vote
Round 1 — Classic
Round 2 — Double Points style round
Round 3 — Triple Points style round
Fast Money Finale prompt
Winner Ceremony
Next Game Night prompt
```

### Awards

The ceremony includes:

- Top Answer Magnet
- Best Steal
- Worst Guess
- Fastest Finger
- The Dude Abides

## Recent patches

### V1.4.4 Question Admin & Review UI

Adds `/feud_question_review`, `/feud_question_report`, `/feud_category_list`, `/feud_category_preview`, `/feud_disable_question`, `/feud_enable_question`, and `/feud_alias_cleanup`.

Run if not already applied:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
```

### V1.4.3 Discord Presentation Upgrade

Adds `/feud_live`, improved `/feud_board`, active round buttons, better correct/wrong answer embeds, Top Answer callouts, Board Clear wording, and cleaner steal phase embeds.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

### V1.4.2 Board UI Polish

Moves PNG board rendering into reusable modules and adds local preview tooling.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
.\.venv\Scripts\python.exe tools\render_board_preview.py
```

### V1.4 Question Audit

Run the local question audit:

```powershell
.\.venv\Scripts\python.exe tools\question_audit.py
```

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

5. Run patchers/checks after pulling the latest version:

   ```powershell
   .\.venv\Scripts\python.exe tools\apply_v1_3_modularisation.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
   .\.venv\Scripts\python.exe tools\apply_v1_4_5_game_night.py
   .\.venv\Scripts\python.exe tools\healthcheck.py
   ```

6. Run the bot:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

## Runtime files

These files are created or updated while the bot runs and should stay local to the hosting machine/server:

- `active_games.json`
- `engagement_state.json`
- `server_scores.json`
- `custom_questions.json`
- `server_settings.json`
- `fortune_bot.sqlite3`
- `rendered_boards/`
- `reports/`

## Useful commands

- `/feud_game_night` opens a guided party-session lobby.
- `/feud_game_night_score` shows the Game Night scoreboard.
- `/feud_game_night_next` advances Game Night after a round ends.
- `/feud_game_night_finish` posts the winner ceremony and closes the session.
- `/feud_health` shows bot/version/latency/content health.
- `/feud_menu` opens the main button menu.
- `/feud_live` shows the compact live round panel with action buttons.
- `/feud_start` starts a round with category packs and game modes.
- `/feud_lobby` opens a pre-game lobby with team joins and category voting.
- `/feud_join` joins the current round on Red or Blue team.
- `/feud_board` shows the current board.
- `/feud_admin` opens host controls.
- `/feud_question_review` reviews questions one at a time.
- `/feud_question_report` shows question quality/review summary.
- `/feud_category_list` lists question categories and counts.
- `/feud_category_preview` previews questions from a category.
- `/feud_disable_question` disables a board from normal selection.
- `/feud_enable_question` lists or re-enables disabled boards.
- `/feud_alias_cleanup` reports or cleans duplicate/self-duplicating aliases.
- `/feud_fast_money` starts a solo 5-question Fast Money challenge.
- `/feud_leaderboard` supports lifetime, weekly, and daily boards.
- `/feud_profile` shows a player's stat profile.

## Local Question Manager

Run this to browse, search, and validate the bundled question files:

```powershell
.\.venv\Scripts\python.exe question_manager.py
```

Then open `http://127.0.0.1:8765`.

## Recommended next steps

Suggested follow-up upgrades after V1.4.5:

1. Test a full Game Night flow in Discord with 2–4 players.
2. Add deeper real Double Points and Triple Points support for normal `/feud_start` modes.
3. Add richer tracking for Game Night awards such as Best Steal and Fastest Finger.
4. Add themes such as Classic, Dude Bowling, Pub Quiz, Mafia Noir, Neon Arcade, and Christmas.
5. Move Game Night state into persistent JSON/SQLite so sessions survive restarts.
