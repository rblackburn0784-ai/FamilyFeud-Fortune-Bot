# Family Feud Fortune Bot

A Discord Family Fortunes / Family Feud style bot with team play, host controls, rendered game boards, question packs, custom server questions, leaderboards, Fast Money, lobbies, daily surveys, weekly challenges, rivalries, question-quality tools, presentation panels, and Discord-side question review/admin tools.

## Current Version

`1.4.4`

## V1.4.4 Question Admin & Review UI

V1.4.4 adds Discord-side tools for managing the large question pool without opening JSON files during a game night.

Added:

- `tools/apply_v1_4_4_question_admin.py`
- `docs/V1.4.4_QUESTION_ADMIN.md`
- `/feud_question_review`
- `/feud_question_report`
- `/feud_category_list`
- `/feud_category_preview`
- `/feud_disable_question`
- `/feud_enable_question`
- `/feud_alias_cleanup`

Run this once after pulling V1.4.4:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
```

Then run:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

Restart the bot and Discord should sync the new commands.

### Question review

`/feud_question_review` shows one board at a time with buttons:

- Approve
- Flag
- Edit Needed
- Skip
- Disable Question
- Previous
- Next

The review queue is sorted by question quality score so weaker boards appear first.

### Question report

`/feud_question_report` shows total questions, category count, average quality score, review counts, disabled count, low-quality count, alias-cleanup candidates, and most common categories.

### Category tools

Use:

```text
/feud_category_list
/feud_category_preview category:wedding
```

### Disable / enable questions

Use:

```text
/feud_disable_question search:<question or answer text>
/feud_enable_question
/feud_enable_question index:<number>
```

Disabled question IDs are stored in the bot's engagement state. The patcher also updates normal question selection so disabled questions are skipped.

### Alias cleanup

Use:

```text
/feud_alias_cleanup
/feud_alias_cleanup apply:true
```

Dry-run mode reports duplicate aliases and aliases that exactly duplicate the answer text. Apply mode cleans runtime/custom-question aliases where possible. It does not rewrite bundled JSON files directly.

## V1.4.3 Discord Presentation Upgrade

V1.4.3 improves the in-Discord game presentation without changing the core scoring rules.

Added:

- `tools/apply_v1_4_3_presentation_upgrade.py`
- `docs/V1.4.3_DISCORD_PRESENTATION.md`
- `/feud_live` compact live-round panel
- richer `/feud_board` layout
- active round buttons: Show Board, Join Red, Join Blue, Scores, Host Controls
- better correct/wrong answer embeds
- Top Answer callout
- Board Clear wording
- cleaner steal incoming/result embeds

Run after pulling V1.4.3 or newer if not already applied:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_3_presentation_upgrade.py
```

## V1.4.2 Board UI Polish

V1.4.2 moves PNG board rendering into reusable modules and adds local preview tooling.

Added:

- `feudbot/board_config.py`
- `feudbot/board_renderer.py`
- `assets/board_layout.json`
- `tools/apply_v1_4_2_board_ui_polish.py`
- `tools/render_board_preview.py`
- `docs/V1.4.2_BOARD_UI_POLISH.md`

Run after pulling V1.4.2 or newer if not already applied:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_4_2_board_ui_polish.py
.\.venv\Scripts\python.exe tools\render_board_preview.py
```

Preview images are written to:

```text
rendered_boards/previews/
```

## V1.4.1 Question Audit False-Positive Fix

V1.4.1 tightens the question-audit logic so valid underscore categories are no longer treated as unknown, and fact-check keywords no longer match inside unrelated words.

## V1.4 Board Polish & Question QA

Run the local question audit:

```powershell
.\.venv\Scripts\python.exe tools\question_audit.py
```

It writes:

- `reports/question_audit_report.md`
- `reports/question_audit_findings.csv`
- `reports/question_web_check_candidates.csv`

Family Feud / Family Fortunes answers are survey-style answers, not normal quiz facts. Most boards should be judged for plausibility, fun, short answer wording, fair scoring, and play feedback.

## V1.3 Modularisation & Health Command

V1.3 added the `feudbot/` package and `/feud_health`.

Run if your local `main.py` has not been patched yet:

```powershell
.\.venv\Scripts\python.exe tools\apply_v1_3_modularisation.py
```

## V1.2 Diagnostics & Operator Tools

Run before starting the bot:

```powershell
.\.venv\Scripts\python.exe tools\healthcheck.py
```

## V1.1 Stability & Repo Hygiene

V1.1 added `.gitignore`, `.env.example`, and removed runtime files from the public source repo.

## Features

- Team-based Family Fortunes / Feud-style rounds.
- Red vs Blue team play with strikes, steals, captain mode, and host controls.
- Multiple game modes including Classic, Fast Money, Sudden Death, Teams Only, and Chaos.
- Question packs, categories, difficulty filtering, and autocomplete.
- Custom server questions and moderator-managed suggestions.
- Discord-side question review, reports, category previews, disabling/enabling, and alias cleanup.
- Player profiles, achievements, daily/weekly/lifetime leaderboards, and rivalry stats.
- Daily survey prompts, weekly challenges, mini polls, and between-round callouts.
- Question analytics, bad-answer tracking, board ratings, and alias suggestions.
- Rendered PNG board using `assets/game_board_template.png`.
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
   .\.venv\Scripts\python.exe tools\apply_v1_4_4_question_admin.py
   .\.venv\Scripts\python.exe tools\render_board_preview.py
   .\.venv\Scripts\python.exe tools\healthcheck.py
   .\.venv\Scripts\python.exe tools\question_audit.py
   ```

6. Run the bot:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

## Runtime Files

These files are created or updated while the bot runs and should stay local to the hosting machine/server:

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
- `/feud_question_review` reviews questions one at a time.
- `/feud_question_report` shows question quality/review summary.
- `/feud_category_list` lists question categories and counts.
- `/feud_category_preview` previews questions from a category.
- `/feud_disable_question` disables a board from normal selection.
- `/feud_enable_question` lists or re-enables disabled boards.
- `/feud_alias_cleanup` reports or cleans duplicate/self-duplicating aliases.
- `/feud_fast_money` starts a solo 5-question Fast Money challenge.
- `/feud_add_question` adds custom questions for the current server.
- `/feud_custom_questions`, `/feud_edit_custom`, and `/feud_delete_custom` manage server questions.
- `/feud_settings` adjusts cooldowns, strikes, timers, steal mode, and more.
- `/feud_leaderboard` supports lifetime, weekly, and daily boards.
- `/feud_profile` shows a player's stat profile.
- `/feud_validate_questions` checks question data quality inside Discord.
- `/feud_question_analytics` shows freshness and performance stats.
- `/feud_suggest` lets players suggest future questions.
- `/feud_approve_suggestion` turns a suggestion into a server custom question.

## Local Question Manager

Run this to browse, search, and validate the bundled question files:

```powershell
.\.venv\Scripts\python.exe question_manager.py
```

Then open `http://127.0.0.1:8765`.

## Recommended Next Steps

Suggested follow-up upgrades after V1.4.4:

1. Test `/feud_question_review`, disable a weak board, and confirm normal games skip it.
2. Use `/feud_question_report` to find weak categories and alias cleanup candidates.
3. Add real Double Points and Triple Points scoring modes.
4. Build a guided Game Night mode with lobby, category vote, normal rounds, double/triple points, Fast Money, and a winner ceremony.
5. Add board/themes such as classic, neon arcade, pub quiz, mafia noir, Dude bowling, and Christmas.
