"""Apply V1.5 Question Index & 5k Pack Loader patch to main.py.

Run after building the V1.5 pack:
    python tools/build_v1_5_question_pack.py
    python tools/apply_v1_5_question_index.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
BACKUP = ROOT / "main.py.v1_5_question_index_backup"
MARKER = "# --- V1.5 QUESTION INDEX PATCH APPLIED ---"

OLD_GET_QUESTIONS_FOR_CATEGORY = '''def get_questions_for_category(category: str, guild_id: Optional[int] = None) -> List[FeudQuestion]:
    category = normalize_category(category)
    questions = get_all_questions(guild_id)

    if category == "random":
        return questions

    if category.startswith("pack:"):
        pack = normalize_pack(category)
        categories = QUESTION_PACKS.get(pack, [])

        return [
            question
            for question in questions
            if normalize_category(question.category) in categories or normalize_category(question.pack) == pack
        ]

    return [
        question
        for question in questions
        if normalize_category(question.category) == category
    ]
'''

NEW_GET_QUESTIONS_FOR_CATEGORY = '''def get_questions_for_category(category: str, guild_id: Optional[int] = None) -> List[FeudQuestion]:
    category = normalize_category(category)
    custom_questions = CUSTOM_QUESTIONS.get(str(guild_id), []) if guild_id is not None else []

    # V1.5: use the base-question index for the large 5k pool, then merge any server custom questions.
    if category == "random":
        return QUESTION_INDEX.all() + custom_questions

    if category.startswith("pack:"):
        pack = normalize_pack(category)
        indexed_questions = QUESTION_INDEX.for_pack(pack, QUESTION_PACKS.get(pack, []))
        custom_matches = [
            question
            for question in custom_questions
            if normalize_category(question.category) in QUESTION_PACKS.get(pack, []) or normalize_category(question.pack) == pack
        ]
        return indexed_questions + custom_matches

    indexed_questions = QUESTION_INDEX.for_category(category)
    custom_matches = [
        question
        for question in custom_questions
        if normalize_category(question.category) == category
    ]
    return indexed_questions + custom_matches
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find patch target: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    if not MAIN.exists():
        raise SystemExit("main.py not found. Run this from the project root.")

    text = MAIN.read_text(encoding="utf-8")
    if MARKER in text:
        print("V1.5 question index patch already applied.")
        return 0

    if not BACKUP.exists():
        BACKUP.write_text(text, encoding="utf-8")
        print(f"Backup written to {BACKUP.name}")

    text = replace_once(
        text,
        "from PIL import Image, ImageDraw, ImageFont\n",
        "from PIL import Image, ImageDraw, ImageFont\nfrom feudbot.question_index import QuestionIndex\n",
        "QuestionIndex import",
    )

    text = replace_once(
        text,
        'MEGA_QUESTIONS_FILE = "mega_questions.json"\n',
        'MEGA_QUESTIONS_FILE = "mega_questions.json"\nV15_QUESTIONS_FILE = "v1_5_questions.json"\n',
        "V15 questions config",
    )

    text = replace_once(
        text,
        '        (EXTRA_QUESTIONS_FILE, "fresh"),\n        (MEGA_QUESTIONS_FILE, "mega")\n    ]:',
        '        (EXTRA_QUESTIONS_FILE, "fresh"),\n        (MEGA_QUESTIONS_FILE, "mega"),\n        (V15_QUESTIONS_FILE, "v1_5")\n    ]:',
        "load v1_5 question pack",
    )

    text = replace_once(
        text,
        "QUESTIONS = load_questions()\n",
        "QUESTIONS = load_questions()\nQUESTION_INDEX = QuestionIndex.build(QUESTIONS, normalize_category)\n" + MARKER + "\n",
        "build question index",
    )

    text = replace_once(
        text,
        OLD_GET_QUESTIONS_FOR_CATEGORY,
        NEW_GET_QUESTIONS_FOR_CATEGORY,
        "indexed get_questions_for_category",
    )

    MAIN.write_text(text, encoding="utf-8")
    print("Applied V1.5 question index and pack-loader patch.")
    print("Run tools/healthcheck.py and tools/question_audit.py before starting the bot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
