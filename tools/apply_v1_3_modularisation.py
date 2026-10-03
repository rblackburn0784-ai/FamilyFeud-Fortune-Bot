"""Apply the small V1.3 integration patch to main.py.

This keeps the live bot mostly unchanged while wiring in the modular health command.
Run from the repository root:

    python tools/apply_v1_3_modularisation.py

The script is idempotent and creates main.py.v1_3_backup before editing.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
BACKUP = ROOT / "main.py.v1_3_backup"

IMPORT_ANCHOR = "from PIL import Image, ImageDraw, ImageFont"
IMPORT_BLOCK = """from PIL import Image, ImageDraw, ImageFont
from feudbot.version import __version__
from feudbot.health_command import register_health_command"""

RUN_ANCHOR = "# ----------------------------\n# RUN BOT\n# ----------------------------\n\nbot.run(TOKEN)"
REGISTER_BLOCK = """# ----------------------------
# V1.3 MODULAR HEALTH COMMAND
# ----------------------------

register_health_command(
    bot=bot,
    version=__version__,
    questions=QUESTIONS,
    custom_questions=CUSTOM_QUESTIONS,
    server_scores=SERVER_SCORES,
    engagement_state=ENGAGEMENT_STATE,
    active_games=active_games,
    database_file=DATABASE_FILE,
    board_template_file=BOARD_TEMPLATE_FILE,
)


# ----------------------------
# RUN BOT
# ----------------------------

bot.run(TOKEN)"""


def main() -> int:
    if not MAIN.exists():
        print("❌ main.py not found. Run this from the repository root.")
        return 1

    text = MAIN.read_text(encoding="utf-8")
    changed = False

    if "from feudbot.version import __version__" not in text:
        if IMPORT_ANCHOR not in text:
            print("❌ Import anchor not found. main.py may have changed.")
            return 1
        text = text.replace(IMPORT_ANCHOR, IMPORT_BLOCK, 1)
        changed = True

    if "register_health_command(" not in text:
        normalized = text.replace("\r\n", "\n")
        if RUN_ANCHOR not in normalized:
            print("❌ Run anchor not found. main.py may have changed.")
            return 1
        normalized = normalized.replace(RUN_ANCHOR, REGISTER_BLOCK, 1)
        text = normalized
        changed = True

    if not changed:
        print("✅ main.py already has the V1.3 health command integration.")
        return 0

    if not BACKUP.exists():
        BACKUP.write_text(MAIN.read_text(encoding="utf-8"), encoding="utf-8")

    MAIN.write_text(text, encoding="utf-8", newline="\n")
    print("✅ V1.3 integration applied to main.py.")
    print("   Backup created at main.py.v1_3_backup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
