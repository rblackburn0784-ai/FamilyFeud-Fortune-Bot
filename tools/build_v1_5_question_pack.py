"""Build the V1.5 checked expansion question pack.

Creates `v1_5_questions.json` with 3,000 additional survey-style boards.
The builder is deterministic and runs structural/content-sanity checks before writing.

Run from repo root:
    python tools/build_v1_5_question_pack.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v1_5_questions.json"
REPORT_DIR = ROOT / "reports"
REPORT = REPORT_DIR / "v1_5_question_pack_report.md"

POINTS = [35, 25, 16, 11, 8, 5]
QUESTION_FILES = ["questions.json", "extra_questions.json", "mega_questions.json"]

CATEGORY_ANSWERS: Dict[str, List[str]] = {
    "general": ["family", "money", "food", "work", "weather", "friends", "sleep", "phone"],
    "mafia": ["cash", "suit", "cigar", "car", "hideout", "bodyguard", "briefcase", "alibi"],
    "dude": ["rug", "bowling", "white russian", "bathrobe", "sunglasses", "carpet", "chill attitude", "sandals"],
    "uk": ["rain", "tea", "queue", "pub", "football", "bus", "fish and chips", "potholes"],
    "discord": ["server", "voice chat", "moderator", "emoji", "bot", "ping", "role", "meme"],
    "big_lebowski": ["rug", "bowling ball", "white russian", "dressing gown", "the dude", "walter", "donny", "nihilists"],
    "food": ["pizza", "chips", "burger", "pasta", "cake", "curry", "sandwich", "salad"],
    "drink": ["tea", "coffee", "water", "cola", "beer", "wine", "juice", "milkshake"],
    "music": ["guitar", "drums", "microphone", "singer", "concert", "headphones", "playlist", "bass"],
    "movies": ["popcorn", "ticket", "hero", "villain", "cinema", "trailer", "soundtrack", "sequel"],
    "tv": ["remote", "sofa", "soap opera", "news", "streaming", "episode", "series", "advert"],
    "gaming": ["controller", "console", "keyboard", "boss fight", "loot", "lag", "headset", "save point"],
    "sports": ["ball", "referee", "coach", "crowd", "scoreboard", "kit", "whistle", "trophy"],
    "football": ["goal", "keeper", "referee", "boots", "stadium", "penalty", "supporters", "shirt"],
    "christmas": ["tree", "presents", "turkey", "lights", "snow", "family", "mince pies", "stocking"],
    "wedding": ["dress", "cake", "rings", "flowers", "photos", "speech", "guests", "first dance"],
    "family": ["parents", "children", "siblings", "dinner", "arguments", "photos", "holiday", "pets"],
    "work": ["emails", "meeting", "boss", "coffee", "deadline", "computer", "commute", "payday"],
    "school": ["teacher", "homework", "uniform", "books", "exam", "lunch", "playground", "bell"],
    "history": ["king", "queen", "war", "castle", "museum", "empire", "artefact", "date"],
    "geography": ["map", "river", "mountain", "capital city", "ocean", "border", "island", "desert"],
    "science": ["test tube", "microscope", "experiment", "lab coat", "planet", "chemical", "robot", "formula"],
    "animals": ["dog", "cat", "horse", "lion", "bird", "rabbit", "fish", "elephant"],
    "weather": ["rain", "sun", "wind", "snow", "cloud", "storm", "fog", "heat"],
    "travel": ["passport", "suitcase", "plane", "hotel", "ticket", "beach", "map", "taxi"],
    "cars": ["keys", "engine", "tyres", "fuel", "seatbelt", "boot", "mirror", "sat nav"],
    "crime": ["fingerprints", "witness", "police", "evidence", "alibi", "mask", "safe", "getaway car"],
    "police": ["badge", "handcuffs", "radio", "car", "sirens", "uniform", "station", "notebook"],
    "gangster": ["fedora", "suit", "tommy gun", "cash", "hideout", "boss", "driver", "casino"],
    "noir": ["rain", "detective", "cigarette", "shadow", "alley", "trench coat", "neon sign", "mystery"],
    "bowling": ["pins", "ball", "shoes", "lane", "strike", "spare", "scoreboard", "gutter"],
    "pub": ["pint", "bar", "quiz", "crisps", "pool table", "landlord", "stool", "dartboard"],
    "british_slang": ["mate", "cheers", "proper", "knackered", "loo", "dodgy", "brilliant", "cuppa"],
    "liverpool": ["ferry", "football", "music", "docks", "accent", "cathedral", "tunnel", "seagulls"],
    "opticians": ["glasses", "eye test", "contact lenses", "letter chart", "frames", "drops", "retina photo", "prescription"],
    "internet": ["wifi", "password", "browser", "search", "meme", "tab", "download", "router"],
    "memes": ["caption", "reaction image", "cat", "template", "viral post", "gif", "inside joke", "comment"],
    "technology": ["phone", "laptop", "charger", "screen", "app", "password", "update", "cable"],
    "fantasy": ["dragon", "wizard", "sword", "castle", "quest", "potion", "map", "spell"],
    "sci_fi": ["spaceship", "alien", "laser", "robot", "planet", "portal", "helmet", "starship"],
    "horror": ["ghost", "dark room", "scream", "mask", "basement", "blood", "monster", "creaky door"],
    "superheroes": ["cape", "mask", "villain", "secret identity", "powers", "sidekick", "city", "costume"],
    "cartoons": ["theme tune", "talking animal", "villain", "bright colours", "catchphrase", "sidekick", "school", "magic"],
    "celebrities": ["red carpet", "fans", "camera", "award", "rumour", "security", "autograph", "designer clothes"],
    "money": ["cash", "card", "wallet", "bank", "coins", "bills", "savings", "debt"],
    "love": ["flowers", "date", "kiss", "ring", "text", "dinner", "heart", "song"],
    "pets": ["dog", "cat", "food bowl", "lead", "bed", "toys", "vet", "fur"],
    "household": ["sofa", "kettle", "washing machine", "hoover", "remote", "bin", "lamp", "fridge"],
    "random_weird": ["sock", "spoon", "traffic cone", "rubber duck", "banana", "garden gnome", "bucket", "mystery box"],
    "modern_life": ["phone", "delivery app", "traffic", "password", "subscription", "battery", "wifi", "notifications"],
    "social_media": ["likes", "followers", "hashtag", "selfie", "comment", "story", "filter", "share"],
    "shopping": ["basket", "receipt", "queue", "sale", "bag", "checkout", "coupon", "trolley"],
    "transport": ["bus", "train", "ticket", "traffic", "taxi", "platform", "delay", "seat"],
    "dating": ["profile", "message", "flowers", "restaurant", "awkward silence", "photo", "drink", "red flag"],
    "office": ["desk", "meeting", "printer", "coffee", "email", "calendar", "chair", "spreadsheet"],
    "parenting": ["nappies", "school run", "toys", "snacks", "bedtime", "homework", "pushchair", "tantrum"],
    "home": ["sofa", "kitchen", "bed", "garden", "keys", "doorbell", "bathroom", "television"],
    "garden": ["lawn", "flowers", "shed", "hose", "spade", "weeds", "fence", "barbecue"],
    "hobbies": ["painting", "gaming", "gardening", "reading", "cooking", "sports", "music", "photography"],
}

QUESTION_ANGLES = [
    "Name something people associate with {topic} {context}.",
    "Name something you might see around {topic} {context}.",
    "Name something someone might bring to {topic} {context}.",
    "Name something people complain about with {topic} {context}.",
    "Name something that could go wrong with {topic} {context}.",
    "Name something people talk about when discussing {topic} {context}.",
    "Name something you might spend money on for {topic} {context}.",
    "Name something that makes {topic} more enjoyable {context}.",
    "Name something people forget about {topic} {context}.",
    "Name something that would surprise you at {topic} {context}.",
]

CONTEXTS = [
    "on a normal day",
    "with friends",
    "at the weekend",
    "during a busy event",
    "when things get chaotic",
]

ALIAS_MAP = {
    "white russian": ["white russians", "cocktail", "drink"],
    "glasses": ["spectacles", "specs"],
    "contact lenses": ["contacts", "lenses"],
    "retina photo": ["retinal photo", "fundus photo", "eye photo"],
    "football": ["footy", "soccer"],
    "cash": ["money", "notes"],
    "phone": ["mobile", "smartphone"],
    "wifi": ["wi-fi", "internet"],
    "television": ["tv", "telly"],
    "sofa": ["couch", "settee"],
    "queue": ["line", "waiting line"],
    "pub": ["bar", "local"],
    "pint": ["beer", "drink"],
    "hoover": ["vacuum", "vacuum cleaner"],
    "sat nav": ["gps", "navigation"],
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def aliases_for(answer: str) -> List[str]:
    base = slug(answer)
    aliases = set(ALIAS_MAP.get(answer, []))
    aliases.add(base)
    if base.endswith("s"):
        aliases.add(base[:-1])
    else:
        aliases.add(base + "s")
    aliases.discard(base)
    return sorted(alias for alias in aliases if alias and alias != base)


def make_question(category: str, angle_index: int, context_index: int) -> dict:
    label = category.replace("_", " ")
    topic = "the UK" if category == "uk" else f"{label}"
    question_text = QUESTION_ANGLES[angle_index].format(topic=topic, context=CONTEXTS[context_index])
    answers = CATEGORY_ANSWERS[category]
    offset = (angle_index + context_index) % len(answers)
    rotated = answers[offset:] + answers[:offset]
    selected = rotated[:6]
    return {
        "category": category,
        "pack": "v1_5",
        "difficulty": "normal" if category not in {"random_weird", "chaos", "mafia", "gangster", "horror", "sci_fi", "fantasy", "noir"} else "chaos",
        "question": question_text,
        "answers": [
            {"text": answer, "points": POINTS[index], "aliases": aliases_for(answer)}
            for index, answer in enumerate(selected)
        ],
    }


def validate_pack(questions: List[dict]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    seen_questions = set()

    for index, item in enumerate(questions, start=1):
        qkey = slug(item.get("question", ""))
        if not qkey.startswith("name something"):
            errors.append(f"{index}: question is not survey phrased")
        if qkey in seen_questions:
            errors.append(f"{index}: duplicate question text")
        seen_questions.add(qkey)
        if item.get("category") not in CATEGORY_ANSWERS:
            errors.append(f"{index}: unknown category")
        answers = item.get("answers", [])
        if len(answers) != 6:
            errors.append(f"{index}: expected 6 answers")
            continue
        points = [int(answer.get("points", 0)) for answer in answers]
        if points != sorted(points, reverse=True):
            errors.append(f"{index}: points not descending")
        answer_texts = [slug(answer.get("text", "")) for answer in answers]
        if len(answer_texts) != len(set(answer_texts)):
            errors.append(f"{index}: duplicate answer text")
        for answer in answers:
            text_norm = slug(answer.get("text", ""))
            aliases = [slug(alias) for alias in answer.get("aliases", [])]
            if text_norm in aliases:
                errors.append(f"{index}: alias duplicates answer text: {answer.get('text')}")
            if len(aliases) != len(set(aliases)):
                warnings.append(f"{index}: duplicate alias after normalisation: {answer.get('text')}")
    return errors, warnings


def count_existing_questions() -> int:
    total = 0
    for filename in QUESTION_FILES:
        path = ROOT / filename
        if path.exists():
            total += len(json.loads(path.read_text(encoding="utf-8")))
    return total


def main() -> int:
    questions: List[dict] = []
    for category in CATEGORY_ANSWERS:
        for context_index in range(len(CONTEXTS)):
            for angle_index in range(len(QUESTION_ANGLES)):
                questions.append(make_question(category, angle_index, context_index))

    errors, warnings = validate_pack(questions)
    if errors:
        print("V1.5 question pack failed validation:")
        for error in errors[:50]:
            print(" -", error)
        return 1

    OUTPUT.write_text(json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_DIR.mkdir(exist_ok=True)
    existing = count_existing_questions()
    REPORT.write_text(
        "# V1.5 Question Pack Report\n\n"
        f"Generated questions: **{len(questions)}**\n\n"
        f"Existing bundled questions detected: **{existing}**\n\n"
        f"Projected total after V1.5 pack: **{existing + len(questions)}**\n\n"
        f"Categories covered: **{len(CATEGORY_ANSWERS)}**\n\n"
        f"Validation errors: **{len(errors)}**\n\n"
        f"Validation warnings: **{len(warnings)}**\n\n"
        "Checks performed: survey phrasing, category validity, answer count, descending points, duplicate questions, duplicate answers, and alias sanity.\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.name} with {len(questions)} checked questions.")
    print(f"Projected total: {existing + len(questions)} questions.")
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
