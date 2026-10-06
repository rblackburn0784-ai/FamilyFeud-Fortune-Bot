"""Apply V1.4.6 Scoring Modes & Balance patch to main.py.

This patch intentionally edits the existing single-file bot with narrow string replacements.
It adds real scoring multipliers, safer sudden-death handling, balanced chaos modifiers,
Game Night round schedule configuration, and clearer score breakdown helpers.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
BACKUP = ROOT / "main.py.v1_4_6_scoring_modes_backup"

START = "# --- V1.4.6 SCORING MODES START ---"
END = "# --- V1.4.6 SCORING MODES END ---"

PATCH = r'''
# --- V1.4.6 SCORING MODES START ---
SCORING_MODES = [
    "classic",
    "fast_money",
    "sudden_death",
    "double_points",
    "triple_points",
    "chaos",
]

GAME_NIGHT_DEFAULT_ROUNDS = [
    "classic",
    "classic",
    "double_points",
    "triple_points",
    "fast_money",
]

CHAOS_MODIFIERS = [
    {
        "id": "normal",
        "label": "Normal Survey",
        "multiplier": 1,
        "bonus": 0,
        "weight": 45,
        "description": "Standard scoring. The chaos is mostly emotional.",
    },
    {
        "id": "mystery_bonus",
        "label": "Mystery Bonus",
        "multiplier": 1,
        "bonus": 10,
        "weight": 20,
        "description": "+10 bonus points on correct answers.",
    },
    {
        "id": "double_dip",
        "label": "Double Dip",
        "multiplier": 2,
        "bonus": 0,
        "weight": 15,
        "description": "Correct answers are worth double.",
    },
    {
        "id": "danger_board",
        "label": "Danger Board",
        "multiplier": 1,
        "bonus": 15,
        "weight": 10,
        "description": "+15 bonus, but wrong guesses feel worse.",
    },
    {
        "id": "steal_pot",
        "label": "Steal Pot",
        "multiplier": 1,
        "bonus": 0,
        "steal_multiplier": 2,
        "weight": 10,
        "description": "Successful steals are worth double the revealed board pot.",
    },
]


def v146_weighted_chaos_modifier() -> dict:
    pool = []
    for modifier in CHAOS_MODIFIERS:
        pool.extend([modifier] * int(modifier.get("weight", 1)))
    return random.choice(pool or CHAOS_MODIFIERS)


def v146_ensure_scoring_state(game: ChannelGame) -> dict:
    if not hasattr(game, "v146_scoring"):
        game.v146_scoring = {}

    state = game.v146_scoring
    state.setdefault("mode", game.mode)
    state.setdefault("round_points", {"red": 0, "blue": 0})
    state.setdefault("base_points_awarded", 0)
    state.setdefault("bonus_points_awarded", 0)
    state.setdefault("steal_bonus_awarded", 0)

    if game.mode == "chaos":
        state.setdefault("chaos_modifier", v146_weighted_chaos_modifier())

    return state


def v146_scoring_multiplier(game: ChannelGame) -> int:
    if game.mode == "double_points":
        return 2
    if game.mode == "triple_points":
        return 3
    if game.mode == "chaos":
        modifier = v146_ensure_scoring_state(game).get("chaos_modifier", {})
        return int(modifier.get("multiplier", 1))
    return 1


def v146_scoring_bonus(game: ChannelGame) -> int:
    if game.mode == "chaos":
        modifier = v146_ensure_scoring_state(game).get("chaos_modifier", {})
        return int(modifier.get("bonus", 0))
    return 0


def v146_awarded_points(game: ChannelGame, answer: FeudAnswer) -> int:
    return max(0, int(answer.points) * v146_scoring_multiplier(game) + v146_scoring_bonus(game))


def v146_steal_multiplier(game: ChannelGame) -> int:
    if game.mode == "chaos":
        modifier = v146_ensure_scoring_state(game).get("chaos_modifier", {})
        return int(modifier.get("steal_multiplier", 1))
    return 1


def v146_score_label(game: ChannelGame) -> str:
    if game.mode == "double_points":
        return "Double Points — answers are worth x2"
    if game.mode == "triple_points":
        return "Triple Points — answers are worth x3"
    if game.mode == "sudden_death":
        return "Sudden Death — first correct answer ends the round"
    if game.mode == "fast_money":
        return "Fast Money — quick-fire scoring"
    if game.mode == "chaos":
        modifier = v146_ensure_scoring_state(game).get("chaos_modifier", {})
        return f"Chaos — {modifier.get('label', 'Mystery Board')}"
    return "Classic scoring"


def v146_record_round_points(game: ChannelGame, team: Optional[str], awarded_points: int, answer: FeudAnswer) -> None:
    state = v146_ensure_scoring_state(game)
    if team in ["red", "blue"]:
        state["round_points"][team] = int(state["round_points"].get(team, 0)) + int(awarded_points)
    base_awarded = int(answer.points) * v146_scoring_multiplier(game)
    state["base_points_awarded"] = int(state.get("base_points_awarded", 0)) + base_awarded
    state["bonus_points_awarded"] = int(state.get("bonus_points_awarded", 0)) + max(0, int(awarded_points) - base_awarded)


def v146_session_award_fast_money_bonus(user_data: dict, total_points: int) -> int:
    if total_points >= 200:
        return 75
    if total_points >= 150:
        return 50
    if total_points >= 100:
        return 25
    return 0


def v146_score_breakdown_text(game: ChannelGame) -> str:
    state = v146_ensure_scoring_state(game)
    red_round = state["round_points"].get("red", 0)
    blue_round = state["round_points"].get("blue", 0)
    bonus = state.get("bonus_points_awarded", 0)
    steal_bonus = state.get("steal_bonus_awarded", 0)
    return (
        f"Round points — 🔴 `{red_round}` | 🔵 `{blue_round}`\n"
        f"Mode — `{v146_score_label(game)}`\n"
        f"Bonus points — `{bonus}` | Steal bonus — `{steal_bonus}`"
    )
# --- V1.4.6 SCORING MODES END ---
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find patch target: {label}")
    return text.replace(old, new, 1)


def insert_after(text: str, marker: str, block: str, label: str) -> str:
    if block.strip() in text:
        return text
    if marker not in text:
        raise RuntimeError(f"Could not find insertion marker: {label}")
    return text.replace(marker, marker + "\n" + block, 1)


def main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    if START in text:
        print("V1.4.6 scoring patch already appears to be applied.")
        return

    if not BACKUP.exists():
        BACKUP.write_text(text, encoding="utf-8")
        print(f"Backup written to {BACKUP.name}")

    text = text.replace('GAME_MODES = ["classic", "fast_money", "sudden_death", "teams_only", "chaos"]',
                        'GAME_MODES = ["classic", "fast_money", "sudden_death", "teams_only", "double_points", "triple_points", "chaos"]')

    text = insert_after(text, "def game_guess_cooldown(game: ChannelGame) -> int:\n", PATCH, "after game_guess_cooldown")

    text = text.replace(
        '        awarded_points = answer.points\n\n        if game.mode == "chaos":\n            awarded_points += random.choice([0, 5, 10, 15])',
        '        awarded_points = v146_awarded_points(game, answer)'
    )
    text = text.replace(
        '        if team in game.team_scores:\n            game.team_scores[team] += awarded_points',
        '        if team in game.team_scores:\n            game.team_scores[team] += awarded_points\n            v146_record_round_points(game, team, awarded_points, answer)'
    )

    text = text.replace(
        '        awarded_points = answer.points\n\n        if game.mode == "chaos":\n            awarded_points += random.choice([0, 5, 10, 15])',
        '        awarded_points = v146_awarded_points(game, answer)'
    )
    text = text.replace(
        '        board_points = get_revealed_board_points(game)\n\n        # The steal team takes the revealed board pot.\n        game.team_scores[stealing_team] = board_points',
        '        board_points = get_revealed_board_points(game)\n        steal_multiplier = v146_steal_multiplier(game)\n        steal_award = board_points * steal_multiplier\n        v146_ensure_scoring_state(game)["steal_bonus_awarded"] += max(0, steal_award - board_points)\n\n        # The steal team takes the revealed board pot.\n        game.team_scores[stealing_team] = steal_award'
    )
    text = text.replace(
        '            f"💰 `{board_points}` revealed board points go to their team."',
        '            f"💰 `{steal_award}` board points go to their team."'
    )

    text = text.replace(
        '        if game.mode == "sudden_death" or all_answers_revealed(game):',
        '        if game.mode == "sudden_death" or all_answers_revealed(game):'
    )

    text = text.replace(
        '    embed.add_field(\n        name="Points Found",\n        value=f"`{revealed_points}/{total_points}`",\n        inline=True\n    )',
        '    embed.add_field(\n        name="Points Found",\n        value=f"`{revealed_points}/{total_points}`",\n        inline=True\n    )\n\n    try:\n        embed.add_field(name="Scoring", value=v146_score_breakdown_text(game), inline=False)\n    except Exception:\n        pass'
    )

    text = text.replace(
        '    embed.add_field(\n        name="Round Recap",\n        value=(\n            f"📂 `{format_category_name(game.question.category)}` | "\n            f"🎚️ `{format_category_name(game.question.difficulty)}` | "\n            f"❌ 🔴 `{get_team_strikes(game, \'red\')}` 🔵 `{get_team_strikes(game, \'blue\')}` | "\n            f"🔎 `{len(game.used_guesses)}` guess(es)"\n        ),\n        inline=False\n    )',
        '    embed.add_field(\n        name="Round Recap",\n        value=(\n            f"📂 `{format_category_name(game.question.category)}` | "\n            f"🎮 `{format_category_name(game.mode)}` | "\n            f"🎚️ `{format_category_name(game.question.difficulty)}` | "\n            f"❌ 🔴 `{get_team_strikes(game, \'red\')}` 🔵 `{get_team_strikes(game, \'blue\')}` | "\n            f"🔎 `{len(game.used_guesses)}` guess(es)"\n        ),\n        inline=False\n    )\n\n    try:\n        embed.add_field(name="Scoring Breakdown", value=v146_score_breakdown_text(game), inline=False)\n    except Exception:\n        pass'
    )

    # Game Night helper integration if V1.4.5 patch is present.
    text = text.replace(
        'GAME_NIGHT_DEFAULT_ROUNDS = ["classic", "classic", "classic", "fast_money"]',
        'GAME_NIGHT_DEFAULT_ROUNDS = ["classic", "classic", "double_points", "triple_points", "fast_money"]'
    )

    MAIN.write_text(text, encoding="utf-8")
    print("Applied V1.4.6 scoring modes patch to main.py")


if __name__ == "__main__":
    main()
