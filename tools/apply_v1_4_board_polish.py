from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = REPO_ROOT / "main.py"

OLD_BLOCK = '''    for strike_index in range(3):
        y = 431 + strike_index * 102
        red_active = strike_index < get_team_strikes(game, "red")
        blue_active = strike_index < get_team_strikes(game, "blue")
        draw_centered_text(
            draw,
            (104, y, 194, y + 90),
            "X",
            strike_font,
            red if red_active else (35, 35, 35),
            stroke_fill=dark,
            stroke_width=2
        )
        draw_centered_text(
            draw,
            (1488, y, 1578, y + 90),
            "X",
            strike_font,
            red if blue_active else (35, 35, 35),
            stroke_fill=dark,
            stroke_width=2
        )
'''

NEW_BLOCK = '''    # V1.4: Draw strike crosses as geometry instead of a font glyph.
    # The previous font-based "X" depended on font metrics, which made the
    # strikes drift inside the side boxes on some machines/templates.
    strike_boxes = {
        "red": [
            (104, 431, 194, 521),
            (104, 533, 194, 623),
            (104, 635, 194, 725),
        ],
        "blue": [
            (1488, 431, 1578, 521),
            (1488, 533, 1578, 623),
            (1488, 635, 1578, 725),
        ],
    }

    def draw_strike_cross(box: Tuple[int, int, int, int], active: bool) -> None:
        left, top, right, bottom = box
        cross_color = red if active else (35, 35, 35)
        outline_color = dark
        pad_x = 25
        pad_y = 16
        line_width = 12 if active else 10

        points_a = (left + pad_x, top + pad_y, right - pad_x, bottom - pad_y)
        points_b = (left + pad_x, bottom - pad_y, right - pad_x, top + pad_y)

        # Dark underlay keeps inactive and active strikes readable on blue panels.
        draw.line(points_a, fill=outline_color, width=line_width + 5)
        draw.line(points_b, fill=outline_color, width=line_width + 5)
        draw.line(points_a, fill=cross_color, width=line_width)
        draw.line(points_b, fill=cross_color, width=line_width)

    for strike_index in range(3):
        red_active = strike_index < get_team_strikes(game, "red")
        blue_active = strike_index < get_team_strikes(game, "blue")
        draw_strike_cross(strike_boxes["red"][strike_index], red_active)
        draw_strike_cross(strike_boxes["blue"][strike_index], blue_active)
'''


def main() -> int:
    if not MAIN_PATH.exists():
        print(f"Could not find {MAIN_PATH}")
        return 1

    content = MAIN_PATH.read_text(encoding="utf-8")

    if "# V1.4: Draw strike crosses as geometry" in content:
        print("V1.4 board polish is already applied.")
        return 0

    if OLD_BLOCK not in content:
        print("Could not find the original strike drawing block. main.py may have changed.")
        return 1

    MAIN_PATH.write_text(content.replace(OLD_BLOCK, NEW_BLOCK), encoding="utf-8")
    print("Applied V1.4 board polish to main.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
