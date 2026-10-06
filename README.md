# Family Feud Fortune Bot

A Discord Family Fortunes / Family Feud style bot with team play, host controls, rendered game boards, large question packs, custom server questions, leaderboards, Fast Money, Game Night flow, review tools, and real scoring modes.

## Current Version

`1.5.0`

## V1.5 Question Index & 5k Checked Pack

V1.5 is a performance and content release.

Added:

- `feudbot/question_index.py`
- `tools/build_v1_5_question_pack.py`
- `tools/apply_v1_5_question_index.py`
- `docs/V1.5_QUESTION_INDEX_AND_5K_PACK.md`
- optional generated pack: `v1_5_questions.json`
- indexed category/pack lookup for larger question pools

### Build the V1.5 question pack

Run this first:

```powershell
.\.venv\Scripts\python.exe tools\build_v1_5_question_pack.py
```

This creates:

```text
v1_5_questions.json
reports/v1_5_question_pack_report.md
```

The builder generates roughly 3,000 additional checked boards. Combined with the existing bundled packs, the bot sits at around 5,000 questions.

The builder checks survey phrasing, category validity, answer count, descending points, duplicate question text, duplicate answers, and alias sanity.

### Apply the V1.5 index patch

After generating the pack:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_5_question_index.py
```

Then run:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
.\.venv\Scripts\python.exe tools\question_audit.py
```

Restart the bot after those checks pass.

## Recent patches

### V1.4.6 Scoring Modes & Balance

Adds real `double_points`, `triple_points`, improved Sudden Death labels, balanced Chaos modifiers, steal bonus support, and Game Night schedule support.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_6_scoring_modes.py
```

### V1.4.5 Game Night Flow

Adds `/feud_game_night`, `/feud_game_night_score`, `/feud_game_night_next`, `/feud_game_night_finish`, team lobby buttons, auto-balance, category voting, session score, round intro, Fast Money prompt, and winner ceremony.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_5_game_night.py
```

### V1.4.4 Question Admin & Review UI

Adds `/feud_question_review`, `/feud_question_report`, `/feud_category_list`, `/feud_category_preview`, `/feud_disable_question`, `/feud_enable_question`, and `/feud_alias_cleanup`.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
```

### V1.4.3 Discord Presentation Upgrade

Adds `/feud_live`, improved `/feud_board`, action buttons, better correct/wrong answer embeds, Top Answer callouts, Board Clear wording, and cleaner steal embeds.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

### V1.4.2 Board UI Polish

Moves PNG board rendering into reusable modules and adds local preview tooling.

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
.\.venv\Scripts\python.exe tools\render_board_preview.py
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
   .\.venv\Scripts\python.exe tools\apply_v1_4_6_scoring_modes.py
   .\.venv\Scripts\python.exe tools\build_v1_5_question_pack.py
   .\.venv\Scripts\python.exe tools\apply_v1_5_question_index.py
   .\.venv\Scripts\python.exe tools\healthcheck.py
   .\.venv\Scripts\python.exe tools\question_audit.py
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
- `v1_5_questions.json`

## Useful commands

- `/feud_game_night` opens a guided party-session lobby.
- `/feud_game_night_score` shows the Game Night scoreboard.
- `/feud_game_night_next` advances Game Night.
- `/feud_game_night_finish` posts the winner ceremony.
- `/feud_health` shows bot/version/latency/content health.
- `/feud_live` shows the compact live round panel.
- `/feud_start` starts a round with category packs and game modes.
- `/feud_board` shows the current board.
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

## Performance note

Normal guessing remains fast with around 5,000 questions because guesses only compare against the current board's answers. V1.5 indexes the large base pool so category and pack lookups do not repeatedly scan every bundled question.

## Local Question Manager

Run this to browse, search, and validate the bundled question files:

```powershell
.\.venv\Scripts\python.exe question_manager.py
```

Then open `http://127.0.0.1:8765`.

## Recommended next steps

Suggested follow-up upgrades after V1.5:

1. Test the generated V1.5 pack with `/feud_question_report` and `/feud_category_preview`.
2. Run a full Game Night with the larger question pool.
3. Add deeper theme support: Classic, Dude Bowling, Pub Quiz, Mafia Noir, Neon Arcade, and Christmas.
4. Move Game Night state into persistent JSON/SQLite so sessions survive restarts.
5. Add CI to compile patchers and run pack validation automatically.
