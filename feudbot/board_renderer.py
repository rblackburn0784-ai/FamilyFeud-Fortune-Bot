from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

from .board_config import load_board_layout

RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]


def _rgb(value: Sequence[int]) -> RGB:
    return (int(value[0]), int(value[1]), int(value[2]))


def _rgba(value: Sequence[int]) -> RGBA:
    return (int(value[0]), int(value[1]), int(value[2]), int(value[3] if len(value) > 3 else 255))


def format_label(value: str | None) -> str:
    value = (value or "classic").replace("_", " ").strip()
    return value.title() if value else "Classic"


def load_board_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def _size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, stroke_width: int = 0) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_text_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int = 18, stroke_width: int = 2) -> ImageFont.ImageFont:
    for size in range(max_size, min_size - 1, -2):
        font = load_board_font(size)
        if _size(draw, text, font, stroke_width=stroke_width)[0] <= max_width:
            return font
    return load_board_font(min_size)


def draw_centered_text(draw: ImageDraw.ImageDraw, box: Sequence[int], text: str, font: ImageFont.ImageFont, fill: RGB, stroke_fill: Optional[RGB] = None, stroke_width: int = 0, y_adjust: int = -2) -> None:
    left, top, right, bottom = [int(v) for v in box]
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + ((right - left) - width) / 2
    y = top + ((bottom - top) - height) / 2 + y_adjust
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill or fill)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _team_strikes(game: Any, team: str) -> int:
    data = _get(game, "team_strikes", {}) or {}
    return int(data.get(team, 0) if isinstance(data, dict) else _get(game, "strikes", 0) or 0)


def _answers(game: Any) -> list[Any]:
    return list(_get(_get(game, "question"), "answers", []) or [])


def _draw_x(draw: ImageDraw.ImageDraw, box: Sequence[int], active: bool, layout: dict[str, Any], colors: dict[str, Any]) -> None:
    left, top, right, bottom = [int(v) for v in box]
    pad = int(layout["strikes"].get("padding", 18))
    width = int(layout["strikes"].get("line_width", 14) if active else layout["strikes"].get("inactive_line_width", 10))
    fill = _rgb(colors["red"] if active else colors["inactive_x"])
    shadow = _rgb(colors["dark"])
    p1, p2 = (left + pad, top + pad), (right - pad, bottom - pad)
    p3, p4 = (right - pad, top + pad), (left + pad, bottom - pad)
    off = max(2, width // 5)
    draw.line([(p1[0] + off, p1[1] + off), (p2[0] + off, p2[1] + off)], fill=shadow, width=width + 4)
    draw.line([(p3[0] + off, p3[1] + off), (p4[0] + off, p4[1] + off)], fill=shadow, width=width + 4)
    draw.line([p1, p2], fill=fill, width=width)
    draw.line([p3, p4], fill=fill, width=width)


def _draw_scores(draw: ImageDraw.ImageDraw, game: Any, layout: dict[str, Any], fonts: dict[str, ImageFont.ImageFont], colors: dict[str, Any]) -> None:
    cfg = layout["scores"]
    white, dark, blue = _rgb(colors["white"]), _rgb(colors["dark"]), _rgb(colors["blue"])
    scores = _get(game, "team_scores", {}) or {}
    red_score = str(int(scores.get("red", 0) or 0)).zfill(4)[-4:]
    blue_score = str(int(scores.get("blue", 0) or 0)).zfill(4)[-4:]
    for key, label in [("red_label", "RED TEAM"), ("blue_label", "BLUE TEAM")]:
        draw.rounded_rectangle(cfg[key], radius=10, fill=(7, 17, 65))
        draw_centered_text(draw, cfg[key], label, fonts["label"], white, stroke_fill=dark, stroke_width=1)
    width = int(cfg.get("outline_width", 3))
    draw.rounded_rectangle(cfg["red_score"], radius=10, fill=(0, 0, 0), outline=_rgb(colors["score_red_outline"]), width=width)
    draw.rounded_rectangle(cfg["blue_score"], radius=10, fill=(0, 0, 0), outline=_rgb(colors["score_blue_outline"]), width=width)
    draw_centered_text(draw, cfg["red_score"], red_score, fonts["score"], blue)
    draw_centered_text(draw, cfg["blue_score"], blue_score, fonts["score"], blue)


def _draw_answers(draw: ImageDraw.ImageDraw, game: Any, layout: dict[str, Any], fonts: dict[str, ImageFont.ImageFont], colors: dict[str, Any]) -> None:
    cfg = layout["answers"]
    answers = _answers(game)
    revealed = list(_get(game, "revealed", []) or [])
    white, gold, dark = _rgb(colors["white"]), _rgb(colors["gold"]), _rgb(colors["dark"])
    for index in range(8):
        top = int(cfg["row_top"]) + index * int(cfg["row_height"])
        bottom = top + int(cfg["row_bottom_offset"])
        points_box = [cfg["points_box"][0], top + cfg["points_box"][1], cfg["points_box"][2], bottom + cfg["points_box"][3]]
        points_text_box = [cfg["points_text_box"][0], top + cfg["points_text_box"][1], cfg["points_text_box"][2], bottom + cfg["points_text_box"][3]]
        draw.rounded_rectangle(points_box, radius=8, fill=(0, 0, 0))
        if index >= len(answers):
            draw_centered_text(draw, points_text_box, "000", fonts["points"], gold, stroke_fill=dark, stroke_width=2)
            continue
        answer = answers[index]
        text = str(_get(answer, "text", "")).upper()
        points = int(_get(answer, "points", 0) or 0)
        if index < len(revealed) and revealed[index]:
            if cfg.get("glow_enabled", True):
                glow = [cfg["answer_box_left"], top + 4, cfg["answer_box_right"], bottom - 2]
                draw.rounded_rectangle(glow, radius=int(cfg.get("glow_radius", 8)), outline=_rgba(colors["answer_glow"]), width=int(cfg.get("glow_width", 4)))
            max_width = int(cfg["answer_text_right"]) - int(cfg["answer_text_x"])
            font = fit_text_font(draw, text, max_width, int(layout["fonts"]["answer_max"]), int(layout["fonts"]["answer_min"]), stroke_width=2)
            draw.text((int(cfg["answer_text_x"]), top + int(cfg["answer_text_top_offset"])), text, font=font, fill=white, stroke_width=2, stroke_fill=dark)
            draw_centered_text(draw, points_text_box, str(points).zfill(3), fonts["points"], gold, stroke_fill=dark, stroke_width=2)
        else:
            hidden = "█" * max(10, min(28, len(text) + 4))
            font = fit_text_font(draw, hidden, int(cfg["answer_text_right"]) - int(cfg["answer_text_x"]), 34, 18, stroke_width=0)
            draw.text((int(cfg["answer_text_x"]), top + int(cfg["hidden_text_top_offset"])), hidden, font=font, fill=_rgb(colors["answer_hidden"]))
            draw_centered_text(draw, points_text_box, "000", fonts["points"], gold, stroke_fill=dark, stroke_width=2)


def _draw_badge(draw: ImageDraw.ImageDraw, game: Any, layout: dict[str, Any], fonts: dict[str, ImageFont.ImageFont], colors: dict[str, Any], fmt: Callable[[str], str]) -> None:
    badge = layout.get("badge", {})
    if not badge.get("enabled", True):
        return
    box = badge.get("box", [650, 830, 1030, 875])
    mode = str(_get(game, "mode", "classic") or "classic")
    text = f"{badge.get('text_prefix', 'ROUND')}: {fmt(mode).upper()}"
    draw.rounded_rectangle(box, radius=int(badge.get("radius", 14)), fill=_rgba(colors["badge_fill"]), outline=_rgb(colors["badge_outline"]), width=2)
    draw_centered_text(draw, box, text, fonts["badge"], _rgb(colors["white"]), stroke_fill=_rgb(colors["dark"]), stroke_width=1)


def render_game_board(game: Any, template_path: str | Path = Path("assets") / "game_board_template.png", output_dir: str | Path = "rendered_boards", output_name: str | None = None, layout_path: str | Path | None = None, format_category_name: Callable[[str], str] | None = None) -> Optional[str]:
    layout = load_board_layout(layout_path)
    colors = layout["colors"]
    fmt = format_category_name or format_label
    template_path = Path(template_path)
    if template_path.exists():
        image = Image.open(template_path).convert("RGBA")
    else:
        canvas = layout.get("canvas", {})
        image = Image.new("RGBA", (int(canvas.get("width", 1680)), int(canvas.get("height", 945))), (3, 10, 35, 255))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    draw = ImageDraw.Draw(image, "RGBA")
    fonts = {key: load_board_font(int(size)) for key, size in {"score": 72, "points": 58, "small": 32, "label": 36, "badge": 30, **layout.get("fonts", {})}.items() if key in {"score", "points", "small", "label", "badge"}}
    _draw_scores(draw, game, layout, fonts, colors)
    for i, box in enumerate(layout["strikes"]["red_boxes"]):
        _draw_x(draw, box, i < _team_strikes(game, "red"), layout, colors)
    for i, box in enumerate(layout["strikes"]["blue_boxes"]):
        _draw_x(draw, box, i < _team_strikes(game, "blue"), layout, colors)
    _draw_answers(draw, game, layout, fonts, colors)
    _draw_badge(draw, game, layout, fonts, colors, fmt)
    question = _get(game, "question", SimpleNamespace(category="general", difficulty="normal"))
    footer = f"{fmt(str(_get(question, 'category', 'general')))} | {fmt(str(_get(game, 'mode', 'classic')))} | {fmt(str(_get(question, 'difficulty', 'normal')))}"
    draw_centered_text(draw, layout["footer"]["box"], footer.upper(), fonts["small"], _rgb(colors["white"]), stroke_fill=_rgb(colors["dark"]), stroke_width=2)
    path = output_dir / (output_name or f"board_{_get(game, 'channel_id', 'preview')}.png")
    image.save(path)
    return str(path)
