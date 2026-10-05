from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"

IMPORT_LINE = "from feudbot.board_renderer import render_game_board\n"
OLD_START = "def render_board_image(game: ChannelGame) -> Optional[str]:\n"
OLD_END_MARKER = "\n\nSPELLING_VARIANTS = {"
NEW_FUNCTION = '''def render_board_image(game: ChannelGame) -> Optional[str]:
    return render_game_board(
        game,
        template_path=BOARD_TEMPLATE_FILE,
        output_dir=BOARD_RENDER_DIR,
        output_name=f"board_{game.channel_id}.png",
        layout_path=os.path.join("assets", "board_layout.json"),
        format_category_name=format_category_name,
    )
'''


def main() -> int:
    if not MAIN.exists():
        print("main.py not found. Run this from the repository root.")
        return 1

    original = MAIN.read_text(encoding="utf-8")
    content = original
    changed = False

    if IMPORT_LINE not in content:
        anchor = "from PIL import Image, ImageDraw, ImageFont\n"
        if anchor not in content:
            print("Could not find PIL import anchor in main.py.")
            return 1
        content = content.replace(anchor, anchor + IMPORT_LINE, 1)
        changed = True

    start = content.find(OLD_START)
    if start == -1:
        print("Could not find render_board_image function. It may already have been patched.")
    else:
        end = content.find(OLD_END_MARKER, start)
        if end == -1:
            print("Could not find end marker after render_board_image.")
            return 1
        existing = content[start:end]
        if "render_game_board(" not in existing:
            content = content[:start] + NEW_FUNCTION + content[end:]
            changed = True

    if not changed:
        print("V1.4.2 board UI patch already applied. No changes made.")
        return 0

    backup = MAIN.with_suffix(".py.v142.bak")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")

    MAIN.write_text(content, encoding="utf-8")
    print("Applied V1.4.2 board UI polish patch to main.py.")
    print(f"Backup written to {backup.name}")
    print("Next: run tools/render_board_preview.py and tools/healthcheck.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
