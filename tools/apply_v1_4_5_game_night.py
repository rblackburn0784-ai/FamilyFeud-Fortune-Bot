"""
V1.4.5 Game Night Flow patcher for Family Feud Fortune Bot.

This safely patches the large single-file bot by inserting a Discord Game Night
session layer before the RUN BOT block. It is intentionally idempotent.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
BACKUP = ROOT / "main.py.v1_4_5_game_night_backup"
MARKER_START = "# --- V1.4.5 GAME NIGHT FLOW START ---"
MARKER_END = "# --- V1.4.5 GAME NIGHT FLOW END ---"
RUN_MARKER = "# ----------------------------\n# RUN BOT\n# ----------------------------"

PATCH = r'''
# --- V1.4.5 GAME NIGHT FLOW START ---

GAME_NIGHT_ROUNDS = [
    {"label": "Round 1", "mode": "classic", "multiplier": 1},
    {"label": "Round 2", "mode": "classic", "multiplier": 2, "display_mode": "double_points"},
    {"label": "Round 3", "mode": "classic", "multiplier": 3, "display_mode": "triple_points"},
]

active_game_nights: Dict[int, dict] = {}

def game_night_key(channel_id: int) -> str:
    return str(channel_id)


def create_game_night_state(channel_id: int, guild_id: Optional[int], host_id: int, host_name: str) -> dict:
    return {
        "channel_id": channel_id,
        "guild_id": guild_id,
        "host_id": host_id,
        "host_name": host_name,
        "locked": False,
        "phase": "lobby",
        "theme": "Classic",
        "host_style": "Cheeky",
        "round_index": 0,
        "category_votes": {},
        "red_players": {},
        "blue_players": {},
        "session_scores": {"red": 0, "blue": 0},
        "player_awards": {},
        "wrong_guesses": [],
        "steals": [],
        "top_answers": {},
        "fastest_finger": None,
        "started_at": time.time(),
    }


def game_night_player_count(state: dict) -> int:
    return len(state.get("red_players", {})) + len(state.get("blue_players", {}))


def game_night_team_lines(players: dict) -> str:
    if not players:
        return "No players yet"
    return ", ".join(players.values())


def game_night_vote_summary(state: dict) -> str:
    votes = state.get("category_votes", {})
    if not votes:
        return "No category votes yet."
    totals: Dict[str, int] = {}
    for category in votes.values():
        totals[category] = totals.get(category, 0) + 1
    return "\n".join(
        f"**{format_category_name(category)}** — `{count}` vote(s)"
        for category, count in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    )


def game_night_winning_category(state: dict) -> str:
    votes = state.get("category_votes", {})
    if not votes:
        return "random"
    totals: Dict[str, int] = {}
    for category in votes.values():
        totals[category] = totals.get(category, 0) + 1
    return max(totals.items(), key=lambda item: item[1])[0]


def create_game_night_lobby_embed(state: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🎬 FEUD BOT GAME NIGHT",
        description=(
            f"**Players:** `{game_night_player_count(state)}`\n"
            f"**Mode:** `Classic Show`\n"
            f"**Rounds:** `3 + Fast Money Finale`\n"
            f"**Theme:** `{state.get('theme', 'Classic')}`\n"
            f"**Host Style:** `{state.get('host_style', 'Cheeky')}`\n"
            f"**Status:** `{'Locked' if state.get('locked') else 'Lobby Open'}`"
        ),
        color=discord.Color.gold()
    )
    embed.add_field(name="🔴 Red Team", value=game_night_team_lines(state.get("red_players", {})), inline=False)
    embed.add_field(name="🔵 Blue Team", value=game_night_team_lines(state.get("blue_players", {})), inline=False)
    embed.add_field(name="Category Vote", value=game_night_vote_summary(state), inline=False)
    embed.set_footer(text="Join a team, vote a category, then the host starts Game Night.")
    return embed


def create_game_night_scoreboard_embed(state: dict, title: str = "📊 Game Night Scoreboard") -> discord.Embed:
    scores = state.get("session_scores", {"red": 0, "blue": 0})
    embed = discord.Embed(title=title, color=discord.Color.blurple())
    embed.add_field(name="Session Score", value=f"🔴 Red `{scores.get('red', 0)}`\n🔵 Blue `{scores.get('blue', 0)}`", inline=True)
    embed.add_field(name="Round", value=f"`{state.get('round_index', 0)}/3` before Fast Money", inline=True)
    embed.add_field(name="Next Category", value=f"`{format_category_name(game_night_winning_category(state))}`", inline=True)
    return embed


def create_game_night_awards_embed(state: dict) -> discord.Embed:
    scores = state.get("session_scores", {"red": 0, "blue": 0})
    if scores.get("red", 0) > scores.get("blue", 0):
        winner = "🔴 Red Team wins!"
    elif scores.get("blue", 0) > scores.get("red", 0):
        winner = "🔵 Blue Team wins!"
    else:
        winner = "🤝 It is a draw!"

    top_answer_counts = state.get("top_answers", {})
    top_answer_magnet = "Not awarded"
    if top_answer_counts:
        user_id, count = max(top_answer_counts.items(), key=lambda item: item[1])
        name = state.get("red_players", {}).get(str(user_id)) or state.get("blue_players", {}).get(str(user_id)) or f"Player {user_id}"
        top_answer_magnet = f"{name} — `{count}` top answer(s)"

    fastest = state.get("fastest_finger") or "Not awarded"
    best_steal = state.get("steals", [])[-1] if state.get("steals") else "Not awarded"
    worst_guess = random.choice(state.get("wrong_guesses", ["Not awarded"]))

    embed = discord.Embed(
        title="🏆 GAME NIGHT WINNER CEREMONY",
        description=f"{winner}\n\nFinal Score: 🔴 `{scores.get('red', 0)}` - `{scores.get('blue', 0)}` 🔵",
        color=discord.Color.gold()
    )
    embed.add_field(name="🧲 Top Answer Magnet", value=top_answer_magnet, inline=False)
    embed.add_field(name="🚨 Best Steal", value=best_steal, inline=False)
    embed.add_field(name="💀 Worst Guess", value=worst_guess, inline=False)
    embed.add_field(name="⚡ Fastest Finger", value=fastest, inline=False)
    embed.add_field(name="🌿 The Dude Abides", value="Awarded to everyone who kept the game moving.", inline=False)
    return embed


class GameNightView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=3600)
        self.channel_id = channel_id

    def state(self) -> Optional[dict]:
        return active_game_nights.get(self.channel_id)

    async def refresh(self, interaction: discord.Interaction) -> None:
        state = self.state()
        if state and interaction.message:
            await interaction.message.edit(embed=create_game_night_lobby_embed(state), view=self)

    @discord.ui.button(label="Join Red", style=discord.ButtonStyle.danger, row=0)
    async def join_red(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.state()
        if not state:
            await interaction.response.send_message("That Game Night lobby is no longer active.", ephemeral=True)
            return
        if state.get("locked"):
            await interaction.response.send_message("Teams are locked for this Game Night.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        state["blue_players"].pop(uid, None)
        state["red_players"][uid] = interaction.user.display_name
        await self.refresh(interaction)
        await interaction.response.send_message("You joined 🔴 Red Team.", ephemeral=True)

    @discord.ui.button(label="Join Blue", style=discord.ButtonStyle.primary, row=0)
    async def join_blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.state()
        if not state:
            await interaction.response.send_message("That Game Night lobby is no longer active.", ephemeral=True)
            return
        if state.get("locked"):
            await interaction.response.send_message("Teams are locked for this Game Night.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        state["red_players"].pop(uid, None)
        state["blue_players"][uid] = interaction.user.display_name
        await self.refresh(interaction)
        await interaction.response.send_message("You joined 🔵 Blue Team.", ephemeral=True)

    @discord.ui.button(label="Auto Balance", style=discord.ButtonStyle.secondary, row=0)
    async def auto_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.state()
        if not state:
            await interaction.response.send_message("No Game Night lobby is active.", ephemeral=True)
            return
        if state.get("locked"):
            await interaction.response.send_message("Teams are locked for this Game Night.", ephemeral=True)
            return
        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message("Auto-balance needs host permissions.", ephemeral=True)
            return
        players = list(state["red_players"].items()) + list(state["blue_players"].items())
        random.shuffle(players)
        state["red_players"] = dict(players[::2])
        state["blue_players"] = dict(players[1::2])
        await self.refresh(interaction)
        await interaction.response.send_message("Teams auto-balanced.", ephemeral=True)

    @discord.ui.button(label="Vote Category", style=discord.ButtonStyle.secondary, row=1)
    async def vote_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.state()
        if not state:
            await interaction.response.send_message("No Game Night lobby is active.", ephemeral=True)
            return
        view = GameNightCategoryVoteView(self.channel_id)
        await interaction.response.send_message("Pick a Game Night category.", view=view, ephemeral=True)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, row=1)
    async def start_game_night(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.state()
        if not state:
            await interaction.response.send_message("No Game Night lobby is active.", ephemeral=True)
            return
        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message("Starting Game Night needs host permissions.", ephemeral=True)
            return
        if game_night_player_count(state) < 2:
            await interaction.response.send_message("Game Night needs at least two players.", ephemeral=True)
            return
        state["locked"] = True
        state["phase"] = "running"
        state["round_index"] = 1
        await interaction.response.defer(ephemeral=False)
        await interaction.channel.send(embed=create_game_night_scoreboard_embed(state, title="🎬 Game Night Starting"))
        await start_game_night_round(interaction.channel, state)
        if interaction.message:
            await interaction.message.edit(embed=create_game_night_lobby_embed(state), view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel_game_night(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message("Cancelling Game Night needs host permissions.", ephemeral=True)
            return
        active_game_nights.pop(self.channel_id, None)
        await interaction.response.edit_message(content="🛑 Game Night cancelled.", embed=None, view=None)


class GameNightCategoryVoteView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        for category in pick_vote_categories():
            self.add_item(GameNightCategoryButton(category))


class GameNightCategoryButton(discord.ui.Button):
    def __init__(self, category: str):
        super().__init__(label=format_category_name(category), style=discord.ButtonStyle.secondary)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        state = active_game_nights.get(self.view.channel_id)
        if not state:
            await interaction.response.send_message("No Game Night lobby is active.", ephemeral=True)
            return
        state["category_votes"][str(interaction.user.id)] = self.category
        await interaction.response.send_message(f"Vote counted for **{format_category_name(self.category)}**.", ephemeral=True)


async def start_game_night_round(channel: discord.abc.Messageable, state: dict) -> None:
    round_number = int(state.get("round_index", 1))
    round_plan = GAME_NIGHT_ROUNDS[min(round_number - 1, len(GAME_NIGHT_ROUNDS) - 1)]
    category = game_night_winning_category(state)
    await channel.send(
        f"🎬 **{round_plan['label']} — Game Night Round**\n"
        f"📂 Category: `{format_category_name(category)}`\n"
        f"✨ Multiplier: `x{round_plan.get('multiplier', 1)}`\n"
        "Teams are locked. Good luck."
    )
    started = await start_new_round_in_channel(channel, category=category, mode=round_plan.get("mode", "classic"))
    if started:
        game = active_games[channel.id]
        game.game_night_multiplier = int(round_plan.get("multiplier", 1))
        game.game_night_channel_id = state["channel_id"]
        display_mode = round_plan.get("display_mode")
        if display_mode:
            game.mode = display_mode
        for user_id, name in state.get("red_players", {}).items():
            game.player_teams[int(user_id)] = "red"
            game.player_names[int(user_id)] = name
        for user_id, name in state.get("blue_players", {}).items():
            game.player_teams[int(user_id)] = "blue"
            game.player_names[int(user_id)] = name
        save_active_games()
        await update_board_message(channel, game, force_new=True)


def apply_game_night_round_result(game: ChannelGame) -> None:
    state = active_game_nights.get(game.channel_id)
    if not state:
        return
    red = int(game.team_scores.get("red", 0))
    blue = int(game.team_scores.get("blue", 0))
    state["session_scores"]["red"] = state["session_scores"].get("red", 0) + red
    state["session_scores"]["blue"] = state["session_scores"].get("blue", 0) + blue
    if game.wrong_guesses:
        state["wrong_guesses"].extend(game.wrong_guesses[-5:])


@bot.tree.command(name="feud_game_night", description="Open a guided Family Fortunes Game Night lobby.")
async def feud_game_night(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Game Night only works inside a server.", ephemeral=True)
        return
    if interaction.channel_id in active_game_nights:
        await interaction.response.send_message("A Game Night lobby is already active in this channel.", ephemeral=True)
        return
    state = create_game_night_state(interaction.channel_id, interaction.guild.id, interaction.user.id, interaction.user.display_name)
    active_game_nights[interaction.channel_id] = state
    await interaction.response.send_message(embed=create_game_night_lobby_embed(state), view=GameNightView(interaction.channel_id))


@bot.tree.command(name="feud_game_night_score", description="Show the current Game Night session scoreboard.")
async def feud_game_night_score(interaction: discord.Interaction):
    state = active_game_nights.get(interaction.channel_id)
    if not state:
        await interaction.response.send_message("No Game Night is active in this channel.", ephemeral=True)
        return
    await interaction.response.send_message(embed=create_game_night_scoreboard_embed(state))


@bot.tree.command(name="feud_game_night_next", description="Advance Game Night to the next round or finale.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_game_night_next(interaction: discord.Interaction):
    state = active_game_nights.get(interaction.channel_id)
    if not state:
        await interaction.response.send_message("No Game Night is active in this channel.", ephemeral=True)
        return
    if interaction.channel_id in active_games:
        await interaction.response.send_message("Finish or stop the current round before advancing Game Night.", ephemeral=True)
        return
    state["round_index"] = int(state.get("round_index", 1)) + 1
    await interaction.response.defer()
    if state["round_index"] <= len(GAME_NIGHT_ROUNDS):
        await interaction.channel.send(embed=create_game_night_scoreboard_embed(state, title="📊 Between-Round Scoreboard"))
        await start_game_night_round(interaction.channel, state)
        await interaction.followup.send("Next Game Night round started.", ephemeral=True)
    else:
        state["phase"] = "finale"
        await interaction.channel.send("⚡ **Fast Money Finale!** Use `/feud_fast_money` for the final challenge, then close with `/feud_game_night_finish`.")
        await interaction.followup.send("Fast Money finale prompt posted.", ephemeral=True)


@bot.tree.command(name="feud_game_night_finish", description="Finish Game Night and post the winner ceremony.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_game_night_finish(interaction: discord.Interaction):
    state = active_game_nights.get(interaction.channel_id)
    if not state:
        await interaction.response.send_message("No Game Night is active in this channel.", ephemeral=True)
        return
    await interaction.response.send_message(embed=create_game_night_awards_embed(state))
    await interaction.channel.send("🎲 Want another Game Night? Use `/feud_game_night` to open a fresh lobby.")
    active_game_nights.pop(interaction.channel_id, None)

# --- V1.4.5 GAME NIGHT FLOW END ---
'''


def patch_main() -> None:
    if not MAIN.exists():
        raise FileNotFoundError(f"Cannot find {MAIN}")
    text = MAIN.read_text(encoding="utf-8")
    if MARKER_START in text:
        print("V1.4.5 Game Night patch already applied.")
        return
    if RUN_MARKER not in text:
        raise RuntimeError("Could not find RUN BOT marker in main.py")
    if not BACKUP.exists():
        BACKUP.write_text(text, encoding="utf-8")
    text = text.replace(RUN_MARKER, PATCH + "\n\n" + RUN_MARKER)

    # Hook session score capture into end_active_game, before round result recording.
    old = "    if game:\n        record_round_result(game)\n"
    new = "    if game:\n        apply_game_night_round_result(game)\n        record_round_result(game)\n"
    if old in text and "apply_game_night_round_result(game)" not in text.split("def end_active_game", 1)[1].split("def ", 1)[0]:
        text = text.replace(old, new, 1)

    # Apply Game Night multipliers at scoring points if the target snippets are present.
    text = text.replace(
        "        awarded_points = answer.points\n\n        if game.mode == \"chaos\":",
        "        awarded_points = answer.points * int(getattr(game, 'game_night_multiplier', 1))\n\n        if game.mode == \"chaos\":",
        1
    )
    text = text.replace(
        "        awarded_points = answer.points\n\n        if game.mode == \"chaos\":",
        "        awarded_points = answer.points * int(getattr(game, 'game_night_multiplier', 1))\n\n        if game.mode == \"chaos\":",
        1
    )

    MAIN.write_text(text, encoding="utf-8")
    print("Applied V1.4.5 Game Night Flow patch.")
    print(f"Backup: {BACKUP}")


if __name__ == "__main__":
    patch_main()
