# Family Feud Fortune Bot

A Discord Family Fortunes game bot with team play, host controls, question packs, custom server questions, per-server settings, daily and weekly leaderboards, timers, and persistent in-progress rounds.

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

4. Run the bot:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

The bot needs the Message Content intent enabled in the Discord Developer Portal because guesses are read from normal channel messages.

## Useful Commands

- `/feud_start` starts a round with category packs and game modes.
- `/feud_admin` opens host buttons for board, reveal, skip, clear strikes, reveal all, and stop.
- `/feud_fast_money` starts a solo 5-question Fast Money challenge.
- `/feud_add_question` adds custom questions for the current server.
- `/feud_custom_questions`, `/feud_edit_custom`, and `/feud_delete_custom` manage server questions.
- `/feud_settings` adjusts cooldowns, strikes, timers, steal mode, and more.
- `/feud_blacklist_word`, `/feud_unblacklist_word`, and `/feud_pause` provide moderation controls.
- `/feud_leaderboard` supports lifetime, weekly, and daily boards.
- `/feud_profile` shows a player's richer stat profile.
- `/feud_validate_questions` checks built-in and custom question quality.
- `/feud_question_analytics` shows freshness and performance stats.
- `/feud_lobby` opens a pre-game lobby with team joins and category voting.
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

Runtime state is still written to JSON files for readability and mirrored into `fortune_bot.sqlite3` for safer long-term storage.
