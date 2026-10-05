from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT_PATH = ROOT / "assets" / "board_layout.json"

DEFAULT_BOARD_LAYOUT: dict[str, Any] = {
    "canvas": {"width": 1680, "height": 945},
    "colors": {
        "blue": [0, 153, 255], "gold": [255, 191, 40], "white": [245, 248, 255],
        "dark": [0, 0, 0], "red": [230, 40, 40], "inactive_x": [35, 35, 35],
        "answer_hidden": [22, 35, 62], "answer_glow": [255, 191, 40, 92],
        "score_red_outline": [255, 65, 65], "score_blue_outline": [0, 153, 255],
        "badge_fill": [7, 17, 65, 218], "badge_outline": [255, 191, 40]
    },
    "fonts": {"score": 72, "answer_max": 46, "answer_min": 18, "points": 58, "small": 32, "label": 36, "badge": 30},
    "scores": {
        "red_label": [70, 58, 348, 108], "blue_label": [1324, 58, 1602, 108],
        "red_score": [101, 110, 318, 189], "blue_score": [1353, 110, 1568, 189],
        "outline_width": 3
    },
    "strikes": {
        "red_boxes": [[104, 431, 194, 521], [104, 533, 194, 623], [104, 635, 194, 725]],
        "blue_boxes": [[1488, 431, 1578, 521], [1488, 533, 1578, 623], [1488, 635, 1578, 725]],
        "line_width": 14, "padding": 18, "inactive_line_width": 10
    },
    "answers": {
        "row_top": 233, "row_height": 81, "row_bottom_offset": 68,
        "answer_text_x": 391, "answer_text_right": 1240, "answer_text_top_offset": 12,
        "hidden_text_top_offset": 20, "answer_box_left": 372, "answer_box_right": 1272,
        "points_box": [1292, 4, 1413, -2], "points_text_box": [1298, 0, 1412, 0],
        "glow_enabled": True, "glow_radius": 8, "glow_width": 4
    },
    "badge": {"enabled": True, "box": [650, 830, 1030, 875], "radius": 14, "text_prefix": "ROUND"},
    "footer": {"box": [470, 880, 1215, 925]}
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_board_layout(path: str | Path | None = None) -> dict[str, Any]:
    layout_path = Path(path) if path else DEFAULT_LAYOUT_PATH
    if not layout_path.exists():
        return copy.deepcopy(DEFAULT_BOARD_LAYOUT)
    try:
        with layout_path.open("r", encoding="utf-8") as handle:
            user_layout = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_BOARD_LAYOUT)
    return _deep_merge(DEFAULT_BOARD_LAYOUT, user_layout) if isinstance(user_layout, dict) else copy.deepcopy(DEFAULT_BOARD_LAYOUT)
