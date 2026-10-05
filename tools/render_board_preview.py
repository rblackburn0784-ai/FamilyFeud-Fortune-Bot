from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from feudbot.board_renderer import render_game_board

POINTS = [37, 24, 16, 9, 6, 4, 3, 1]
ANSWERS = ["Wedding Cake", "First Dance", "Best Man Speech", "Open Bar", "Family Argument", "Bouquet Toss", "Awkward Photos", "Someone Crying"]
LONG_ANSWERS = ["Someone Who Forgets The Rings", "A Very Long Best Man Speech", "The DJ Playing The Wrong Song", "A Relative Starting An Argument", "The Cake Being Dropped", "Rain During The Photos", "Awkward Table Seating", "The Bar Running Dry"]


def make_game(name: str, strikes: int, revealed_count: int, mode: str, long_answers: bool = False) -> SimpleNamespace:
    texts = LONG_ANSWERS if long_answers else ANSWERS
    answers = [SimpleNamespace(text=text, points=POINTS[index]) for index, text in enumerate(texts)]
    return SimpleNamespace(
        channel_id=f"preview_{name}",
        mode=mode,
        team_scores={"red": 120 + strikes * 5, "blue": 85 + revealed_count * 3},
        team_strikes={"red": strikes, "blue": max(0, 3 - strikes) if name == "completed_board" else 0},
        revealed=[index < revealed_count for index in range(8)],
        question=SimpleNamespace(
            category="wedding",
            difficulty="hard",
            question="Name something that might happen at a chaotic wedding.",
            answers=answers,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate board preview PNGs without running Discord.")
    parser.add_argument("--template", default=str(ROOT / "assets" / "game_board_template.png"), help="Board template PNG path.")
    parser.add_argument("--layout", default=str(ROOT / "assets" / "board_layout.json"), help="Board layout JSON path.")
    parser.add_argument("--out", default=str(ROOT / "rendered_boards" / "previews"), help="Output directory.")
    args = parser.parse_args()

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = [
        ("00_strikes", 0, 0, "classic", False),
        ("01_strike", 1, 1, "classic", False),
        ("02_strikes", 2, 3, "classic", False),
        ("03_strikes", 3, 4, "classic", False),
        ("partial_reveal", 1, 4, "fast_money", True),
        ("completed_board", 0, 8, "chaos", True),
        ("sudden_death_badge", 0, 1, "sudden_death", False),
        ("double_points_badge", 0, 2, "double_points", False),
        ("triple_points_badge", 0, 3, "triple_points", False),
    ]

    print("Generating board previews...")
    for name, strikes, revealed, mode, long_answers in scenarios:
        game = make_game(name, strikes, revealed, mode, long_answers=long_answers)
        path = render_game_board(game, template_path=args.template, output_dir=output_dir, output_name=f"{name}.png", layout_path=args.layout)
        print(f"- {path}")
    print(f"Done. Preview folder: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
