from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
BACKUP = ROOT / "main.py.v1_4_3_presentation_backup"
MARKER = "# V1.4.3_PRESENTATION_UPGRADE"

PRESENTATION_BLOCK = r"""
# V1.4.3_PRESENTATION_UPGRADE
def strike_display(count: int, maximum: int) -> str:
    count = max(0, min(maximum, int(count or 0)))
    return " ".join(["❌"] * count + ["⬛"] * (maximum - count))


def board_found_count(game: ChannelGame) -> int:
    return sum(1 for revealed in game.revealed if revealed)


def format_score_3(value: int) -> str:
    return str(max(0, int(value or 0))).zfill(3)


def team_name(team: Optional[str]) -> str:
    if team == "red":
        return "Red Team"
    if team == "blue":
        return "Blue Team"
    return "No Team"


def team_icon(team: Optional[str]) -> str:
    if team == "red":
        return "🔴"
    if team == "blue":
        return "🔵"
    return "⚪"


def game_colour_for_team(team: Optional[str]) -> discord.Color:
    if team == "red":
        return discord.Color.red()
    if team == "blue":
        return discord.Color.blue()
    return discord.Color.gold()


def create_board_embed(game: ChannelGame, title: str = "🎤 FEUD BOT LIVE", compact: bool = False) -> discord.Embed:
    settings = get_server_settings(game.guild_id)
    found = board_found_count(game)
    total = len(game.question.answers)
    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)
    max_strikes = settings["max_strikes"]

    timer_text = ""
    if game.ends_at:
        remaining = max(0, int(game.ends_at - time.time()))
        timer_text = f"\n⏱️ **Time Left:** `{remaining // 60}:{remaining % 60:02d}`"

    embed = discord.Embed(
        title=title,
        description=(
            f"**{game.question.question}**\n\n"
            f"🎮 **Round Type:** `{format_category_name(game.mode)}`\n"
            f"📂 **Category:** `{format_category_name(game.question.category)}`\n"
            f"🎚️ **Difficulty:** `{format_category_name(game.question.difficulty)}`\n"
            f"📋 **Current Board:** `{found}/{total}` found{timer_text}"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Scoreboard",
        value=(
            f"🔴 **Red:** `{format_score_3(red_score)}`\n"
            f"🔵 **Blue:** `{format_score_3(blue_score)}`"
        ),
        inline=True
    )
    embed.add_field(
        name="Strikes",
        value=(
            f"🔴 {strike_display(get_team_strikes(game, 'red'), max_strikes)}\n"
            f"🔵 {strike_display(get_team_strikes(game, 'blue'), max_strikes)}"
        ),
        inline=True
    )

    revealed_points = sum(
        answer.points
        for index, answer in enumerate(game.question.answers)
        if index < len(game.revealed) and game.revealed[index]
    )
    total_points = sum(answer.points for answer in game.question.answers)
    embed.add_field(
        name="Board Value",
        value=f"`{revealed_points}/{total_points}` points found",
        inline=True
    )

    if not compact:
        board_lines = []
        for index, answer in enumerate(game.question.answers):
            number = index + 1
            if index < len(game.revealed) and game.revealed[index]:
                marker = "🏆 " if index == 0 else ""
                board_lines.append(f"**{number}.** {marker}**{answer.text}** — `{answer.points}`")
            else:
                hidden_bar = "█" * max(4, min(14, answer.points // 3))
                board_lines.append(f"**{number}.** `{hidden_bar}`")
        embed.add_field(name="Survey Board", value="\n".join(board_lines), inline=False)

    red_players = [
        game.player_names.get(user_id, f"Player {user_id}")
        for user_id, player_team in game.player_teams.items()
        if player_team == "red"
    ]
    blue_players = [
        game.player_names.get(user_id, f"Player {user_id}")
        for user_id, player_team in game.player_teams.items()
        if player_team == "blue"
    ]

    if compact:
        embed.add_field(
            name="Teams",
            value=(
                f"🔴 {', '.join(red_players) if red_players else 'No players yet'}\n"
                f"🔵 {', '.join(blue_players) if blue_players else 'No players yet'}"
            ),
            inline=False
        )
    else:
        embed.add_field(name="🔴 Red Players", value=", ".join(red_players) if red_players else "No players yet", inline=True)
        embed.add_field(name="🔵 Blue Players", value=", ".join(blue_players) if blue_players else "No players yet", inline=True)

    if game.pending_steal and game.stealing_team:
        embed.add_field(
            name="🚨 Steal Chance",
            value=f"{team_icon(game.stealing_team)} **{team_name(game.stealing_team)}** has one guess to steal the board.",
            inline=False
        )

    if game.wrong_guesses and not compact:
        embed.add_field(name="Recent Wrong Guesses", value=", ".join(game.wrong_guesses[-5:]), inline=False)

    embed.set_footer(text="Use the buttons below, /feud_join, or type a guess if you are already on a team.")
    return embed


def create_live_round_embed(game: ChannelGame) -> discord.Embed:
    return create_board_embed(game, title="🎤 FEUD BOT LIVE", compact=True)


def create_correct_answer_embed(
    game: ChannelGame,
    answer_index: int,
    answer: FeudAnswer,
    awarded_points: int,
    scoring_team: Optional[str],
    display_name: str,
    fuzzy_used: bool = False,
    achievement_messages: Optional[List[str]] = None
) -> discord.Embed:
    title = "🏆 TOP ANSWER!" if answer_index == 0 else "🔔 GOOD ANSWER!"
    embed = discord.Embed(
        title=title,
        description=f"**#{answer_index + 1} — {answer.text.upper()}**\nSurvey value: `{str(answer.points).zfill(3)}`",
        color=game_colour_for_team(scoring_team)
    )
    embed.add_field(name="Points", value=f"{team_icon(scoring_team)} **{team_name(scoring_team)}** `+{awarded_points}`", inline=True)
    embed.add_field(name="Player", value=f"**{display_name}**", inline=True)
    if fuzzy_used:
        embed.add_field(name="Match Note", value="Accepted as a close match.", inline=False)
    if achievement_messages:
        embed.add_field(name="Achievements", value="\n".join(achievement_messages)[:1000], inline=False)
    return embed


def create_wrong_answer_embed(
    game: ChannelGame,
    player_team: Optional[str],
    team_strikes: int,
    display_name: str,
    achievement_messages: Optional[List[str]] = None
) -> discord.Embed:
    max_strikes = game_max_strikes(game)
    remaining = max(0, max_strikes - team_strikes)
    warning = "One more and the other team gets a steal chance." if remaining == 1 else f"`{remaining}` strike(s) left."
    embed = discord.Embed(
        title="❌ SURVEY SAYS... NO!",
        description=f"**{team_name(player_team)}** strike `{team_strikes}/{max_strikes}`.\n{warning}\n\n💥 **{display_name}'s streak has been reset.**",
        color=game_colour_for_team(player_team)
    )
    embed.add_field(
        name="Strikes",
        value=f"🔴 {strike_display(get_team_strikes(game, 'red'), max_strikes)}\n🔵 {strike_display(get_team_strikes(game, 'blue'), max_strikes)}",
        inline=False
    )
    if achievement_messages:
        embed.add_field(name="Achievements", value="\n".join(achievement_messages)[:1000], inline=False)
    return embed


def create_steal_incoming_embed(game: ChannelGame) -> discord.Embed:
    stealing_team = game.stealing_team
    defending_team = get_other_team(stealing_team) if stealing_team else None
    embed = create_board_embed(game, title="🚨 STEAL INCOMING!", compact=True)
    embed.color = game_colour_for_team(stealing_team)
    embed.add_field(
        name="How Steal Works",
        value=(
            f"{team_icon(stealing_team)} **{team_name(stealing_team)}** gets **one answer**.\n"
            "✅ Correct = steal the revealed board value.\n"
            f"❌ Wrong = **{team_name(defending_team)}** survives."
        ),
        inline=False
    )
    return embed


def create_steal_result_embed(
    game: ChannelGame,
    success: bool,
    stealing_team: Optional[str],
    display_name: str,
    board_points: int = 0,
    answer: Optional[FeudAnswer] = None
) -> discord.Embed:
    if success:
        description = (
            f"{team_icon(stealing_team)} **{team_name(stealing_team)}** steals the board!\n"
            f"💰 `{board_points}` revealed board points go to their team."
        )
        if answer:
            description += f"\n\nSteal answer: **{answer.text.upper()}**"
        title = "🚨 STEAL SUCCESSFUL!"
    else:
        title = "❌ STEAL FAILED!"
        description = "The board survives the attempted robbery. Current scores stay."
    embed = discord.Embed(title=title, description=description, color=game_colour_for_team(stealing_team))
    embed.add_field(name="Player", value=f"**{display_name}**", inline=True)
    return embed


def create_steal_embed(game: ChannelGame) -> discord.Embed:
    return create_steal_incoming_embed(game)
"""

ACTIVE_PANEL_BLOCK = r"""
# V1.4.3_PRESENTATION_UPGRADE
class ActiveRoundPanelView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=1800)
        self.channel_id = channel_id

    async def get_game_or_reply(self, interaction: discord.Interaction) -> Optional[ChannelGame]:
        game = active_games.get(self.channel_id)
        if game is None:
            await interaction.response.send_message("There is no active round in this channel.", ephemeral=True)
            return None
        return game

    async def join_team(self, interaction: discord.Interaction, chosen_team: str) -> None:
        game = active_games.get(self.channel_id)
        if game is None:
            await interaction.response.send_message("That round is no longer active.", ephemeral=True)
            return

        user_id = interaction.user.id
        display_name = interaction.user.display_name

        if user_id in game.player_scores and game.player_scores[user_id] > 0:
            await interaction.response.send_message("You cannot switch teams after scoring points this round.", ephemeral=True)
            return

        game.player_teams[user_id] = chosen_team
        game.player_names[user_id] = display_name
        game.captain_by_team.setdefault(chosen_team, user_id)
        save_active_games()
        await update_board_message(interaction.channel, game)

        await interaction.response.send_message(f"{team_icon(chosen_team)} You joined **{team_name(chosen_team)}**.", ephemeral=True)
        await maybe_send_host_line(interaction.channel, game.guild_id, TEAM_JOIN_HOST_LINES)

    @discord.ui.button(label="Show Board", style=discord.ButtonStyle.primary, row=0)
    async def show_board_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return
        board_file_path = render_board_image(game)
        if board_file_path:
            await interaction.response.send_message(embed=create_live_round_embed(game), file=discord.File(board_file_path, filename="family_fortunes_board.png"), view=ActiveRoundPanelView(self.channel_id), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_board_embed(game), view=ActiveRoundPanelView(self.channel_id), ephemeral=True)

    @discord.ui.button(label="Join Red", style=discord.ButtonStyle.danger, row=0)
    async def join_red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "red")

    @discord.ui.button(label="Join Blue", style=discord.ButtonStyle.primary, row=0)
    async def join_blue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_team(interaction, "blue")

    @discord.ui.button(label="Scores", style=discord.ButtonStyle.secondary, row=1)
    async def scores_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return
        await interaction.response.send_message(embed=create_score_embed(game), ephemeral=True)

    @discord.ui.button(label="Host Controls", style=discord.ButtonStyle.secondary, row=1)
    async def host_controls_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message("Host controls need Manage Messages.", ephemeral=True)
            return
        game = await self.get_game_or_reply(interaction)
        if not game:
            return
        await interaction.response.send_message("Host controls are ready.", view=FeudAdminView(self.channel_id), ephemeral=True)
"""

FEUD_LIVE_COMMAND = r"""
@bot.tree.command(name="feud_live", description="Show the compact live round panel with action buttons.")
async def feud_live(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in active_games:
        await interaction.response.send_message("There is no active Family Fortunes round in this channel.", ephemeral=True)
        return

    game = active_games[channel_id]
    board_file_path = render_board_image(game)
    if board_file_path:
        await interaction.response.send_message(embed=create_live_round_embed(game), file=discord.File(board_file_path, filename="family_fortunes_board.png"), view=ActiveRoundPanelView(channel_id))
    else:
        await interaction.response.send_message(embed=create_board_embed(game), view=ActiveRoundPanelView(channel_id))


"""

FEUD_BOARD_COMMAND = r"""@bot.tree.command(name="feud_board", description="Show the current Family Fortunes board.")
async def feud_board(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in active_games:
        await interaction.response.send_message("There is no active Family Fortunes round in this channel.", ephemeral=True)
        return

    game = active_games[channel_id]
    board_file_path = render_board_image(game)
    if board_file_path:
        await interaction.response.send_message(embed=create_live_round_embed(game), file=discord.File(board_file_path, filename="family_fortunes_board.png"), view=ActiveRoundPanelView(channel_id))
    else:
        await interaction.response.send_message(embed=create_board_embed(game), view=ActiveRoundPanelView(channel_id))



"""


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError(f"Could not find start marker: {start_marker}")
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f"Could not find end marker after {start_marker}: {end_marker}")
    return text[:start] + replacement + "\n\n" + text[end:]


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find expected text:\n{old[:400]}")
    return text.replace(old, new, 1)


def replace_call_block(text: str, start_text: str, end_text: str, replacement: str, occurrence: int = 1) -> str:
    pos = -1
    search_from = 0
    for _ in range(occurrence):
        pos = text.find(start_text, search_from)
        if pos == -1:
            raise RuntimeError(f"Could not find block start: {start_text[:120]}")
        search_from = pos + len(start_text)
    end = text.find(end_text, pos)
    if end == -1:
        raise RuntimeError(f"Could not find block end after: {start_text[:120]}")
    end += len(end_text)
    return text[:pos] + replacement + text[end:]


def main() -> int:
    if not MAIN.exists():
        raise FileNotFoundError(MAIN)

    text = MAIN.read_text(encoding="utf-8")
    if MARKER in text:
        print("V1.4.3 presentation upgrade is already applied.")
        return 0

    if not BACKUP.exists():
        BACKUP.write_text(text, encoding="utf-8")

    text = replace_between(
        text,
        'def create_board_embed(game: ChannelGame, title: str = "🎤 Family Fortunes", compact: bool = False) -> discord.Embed:',
        'def create_final_embed(game: ChannelGame, reason: str) -> discord.Embed:',
        PRESENTATION_BLOCK
    )

    text = replace_once(
        text,
        "\nclass FeudAdminView(discord.ui.View):",
        "\n" + ACTIVE_PANEL_BLOCK + "\n\nclass FeudAdminView(discord.ui.View):"
    )

    text = replace_once(
        text,
        "        await message.channel.send(response_text)\n",
        "        await message.channel.send(\n            embed=create_correct_answer_embed(game, answer_index, answer, awarded_points, team, display_name, fuzzy_used, achievement_messages),\n            view=ActiveRoundPanelView(game.channel_id)\n        )\n"
    )

    text = replace_call_block(
        text,
        "    await message.channel.send(\n        f\"{wrong_text}",
        "    )\n",
        "    await message.channel.send(\n        embed=create_wrong_answer_embed(game, team, team_strikes, display_name, achievement_messages),\n        view=ActiveRoundPanelView(game.channel_id)\n    )\n",
        occurrence=1
    )

    text = replace_once(
        text,
        "        await message.channel.send(embed=steal_embed)\n",
        "        await message.channel.send(embed=steal_embed, view=ActiveRoundPanelView(game.channel_id))\n"
    )

    text = replace_call_block(
        text,
        "        await message.channel.send(\n            f\"{correct_intro}",
        "        )\n",
        "        await message.channel.send(\n            embed=create_steal_result_embed(game, True, stealing_team, display_name, board_points, answer),\n            view=ActiveRoundPanelView(game.channel_id)\n        )\n",
        occurrence=1
    )

    text = replace_call_block(
        text,
        "    await message.channel.send(\n        f\"❌ **Steal failed!",
        "    )\n",
        "    await message.channel.send(\n        embed=create_steal_result_embed(game, False, game.stealing_team, display_name),\n        view=ActiveRoundPanelView(game.channel_id)\n    )\n",
        occurrence=1
    )

    text = replace_once(
        text,
        '                "⚡ Sudden Death answer found!" if game.mode == "sudden_death" else "✅ Every answer was found!"\n',
        '                "⚡ Sudden Death answer found!" if game.mode == "sudden_death" else "🏁 Board Clear! Every answer was found!"\n'
    )

    text = replace_between(
        text,
        '@bot.tree.command(name="feud_board", description="Show the current Family Fortunes board.")',
        '@bot.tree.command(name="feud_score", description="Show the current Family Fortunes scores.")',
        FEUD_LIVE_COMMAND + FEUD_BOARD_COMMAND
    )

    MAIN.write_text(text, encoding="utf-8")
    print("Applied V1.4.3 Discord Presentation Upgrade to main.py.")
    print(f"Backup written to {BACKUP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
