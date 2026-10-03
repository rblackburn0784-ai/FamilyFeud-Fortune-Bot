"""Discord /feud_health command registration."""

from __future__ import annotations

import time
from typing import Any

import discord

from .diagnostics import runtime_summary


STARTED_AT = time.time()


def format_uptime() -> str:
    seconds = int(time.time() - STARTED_AT)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def register_health_command(
    *,
    bot: Any,
    version: str,
    questions: list[Any],
    custom_questions: dict[str, list[Any]],
    server_scores: dict[str, Any],
    engagement_state: dict[str, Any],
    active_games: dict[Any, Any],
    database_file: str,
    board_template_file: str,
) -> None:
    """Register /feud_health once on the supplied Discord bot."""

    if getattr(bot, "_feud_health_registered", False):
        return

    @bot.tree.command(name="feud_health", description="Show Family Fortunes bot health and runtime status.")
    async def feud_health(interaction: discord.Interaction):
        summary = runtime_summary(
            version=version,
            questions=questions,
            custom_questions=custom_questions,
            server_scores=server_scores,
            engagement_state=engagement_state,
            active_games=active_games,
            database_file=database_file,
            board_template_file=board_template_file,
        )

        db_icon = "✅" if summary["database_ok"] else "❌"
        board_icon = "✅" if summary["board_template_present"] else "⚠️"
        latency_ms = round(getattr(bot, "latency", 0) * 1000)

        embed = discord.Embed(
            title="🩺 Feud Bot Health",
            description=f"Version `{summary['version']}` | Uptime `{format_uptime()}`",
            color=discord.Color.green() if summary["database_ok"] else discord.Color.orange(),
        )
        embed.add_field(
            name="Runtime",
            value=(
                f"Discord latency: `{latency_ms}ms`\n"
                f"Servers: `{len(getattr(bot, 'guilds', []))}`\n"
                f"Active rounds: `{summary['active_rounds']}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="Content",
            value=(
                f"Question pool: `{summary['questions']}`\n"
                f"Custom questions: `{summary['custom_questions']}`\n"
                f"Score servers: `{summary['score_servers']}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="Storage & Assets",
            value=(
                f"{db_icon} SQLite: `{summary['database_detail']}`\n"
                f"{board_icon} Board template: `{'present' if summary['board_template_present'] else 'missing'}`"
            ),
            inline=False,
        )
        embed.set_footer(text="Use tools/healthcheck.py locally for deeper startup diagnostics.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot._feud_health_registered = True
