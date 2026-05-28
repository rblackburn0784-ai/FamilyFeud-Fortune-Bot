import os
import json
import random
import asyncio
import difflib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont


# ----------------------------
# LOAD TOKEN
# ----------------------------

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is missing from your .env file.")


# ----------------------------
# CONFIG
# ----------------------------

QUESTIONS_FILE = "questions.json"
EXTRA_QUESTIONS_FILE = "extra_questions.json"
MEGA_QUESTIONS_FILE = "mega_questions.json"
CUSTOM_QUESTIONS_FILE = "custom_questions.json"
SETTINGS_FILE = "server_settings.json"
ACTIVE_GAMES_FILE = "active_games.json"
ENGAGEMENT_FILE = "engagement_state.json"
DATABASE_FILE = "fortune_bot.sqlite3"
BOARD_TEMPLATE_FILE = os.path.join("assets", "game_board_template.png")
BOARD_RENDER_DIR = os.path.join("rendered_boards")
USED_QUESTIONS_LIMIT = 150
MAX_STRIKES = 3
FUZZY_MATCH_THRESHOLD = 0.82
SCORES_FILE = "server_scores.json"
GUESS_COOLDOWN_SECONDS = 30
DEFAULT_ROUND_SECONDS = 0
BOARD_REPOST_EVERY = 4
IDLE_HOST_ENABLED = True
IDLE_HOST_COOLDOWN_SECONDS = 45
IDLE_HOST_RANDOM_CHANCE = 0.08
HOST_NAMES = ["steve", "richard"]
DIRECT_HOST_COOLDOWN_SECONDS = 8
NEXT_ROUND_YES_VOTES_REQUIRED = 1

GAME_MODES = ["classic", "fast_money", "sudden_death", "teams_only", "chaos"]
QUESTION_DIFFICULTIES = ["any", "easy", "normal", "hard", "chaos"]
STEAL_MODES = ["any", "captain"]
HOST_PERSONALITIES = [
    "quiet",
    "cheeky",
    "tv_host",
    "chaos",
    "strict",
    "steve",
    "richard",
    "dry_british",
    "dramatic_american",
    "quizmaster"
]

QUESTION_PACKS = {
    "party_mix": ["general", "food", "drink", "music", "movies", "tv", "gaming"],
    "pub_quiz": ["uk", "british_slang", "pub", "sports", "football", "history"],
    "movie_night": ["movies", "tv", "celebrities", "superheroes", "horror", "cartoons"],
    "work_safe": ["work", "school", "technology", "science", "household", "travel"],
    "holiday": ["christmas", "wedding", "family", "food", "drink", "love"],
    "chaos": ["random_weird", "memes", "internet", "discord", "dude", "mafia"],
    "fresh": ["modern_life", "social_media", "shopping", "transport", "dating", "office", "parenting"],
    "weekend": ["home", "garden", "hobbies", "pets", "travel", "food", "drink"]
}

DEFAULT_SERVER_SETTINGS = {
    "max_strikes": MAX_STRIKES,
    "guess_cooldown_seconds": GUESS_COOLDOWN_SECONDS,
    "round_seconds": DEFAULT_ROUND_SECONDS,
    "idle_host_enabled": IDLE_HOST_ENABLED,
    "next_round_yes_votes_required": NEXT_ROUND_YES_VOTES_REQUIRED,
    "steal_mode": "any",
    "minimum_players": 1,
    "board_repost_every": BOARD_REPOST_EVERY,
    "host_personality": "cheeky",
    "daily_prompt_enabled": False,
    "daily_prompt_channel_id": None,
    "game_night_reminder_enabled": False,
    "game_night_channel_id": None,
    "game_night_weekday": 5,
    "game_night_hour_utc": 19,
    "game_night_notice_minutes": 30,
    "quiet_mode": False,
    "blacklisted_words": []
}

FEUD_CATEGORIES = [
    "random",
    "general",
    "mafia",
    "dude",
    "uk",
    "discord",
    "big_lebowski",
    "food",
    "drink",
    "music",
    "movies",
    "tv",
    "gaming",
    "sports",
    "football",
    "christmas",
    "wedding",
    "family",
    "work",
    "school",
    "history",
    "geography",
    "science",
    "animals",
    "weather",
    "travel",
    "cars",
    "crime",
    "police",
    "gangster",
    "noir",
    "bowling",
    "pub",
    "british_slang",
    "liverpool",
    "opticians",
    "internet",
    "memes",
    "technology",
    "fantasy",
    "sci_fi",
    "horror",
    "superheroes",
    "cartoons",
    "celebrities",
    "money",
    "love",
    "pets",
    "household",
    "random_weird",
    "modern_life",
    "social_media",
    "shopping",
    "transport",
    "dating",
    "office",
    "parenting",
    "home",
    "garden",
    "hobbies"
]

# ----------------------------
# DATA MODELS
# ----------------------------

@dataclass
class NextRoundVote:
    channel_id: int
    message_id: int
    category: str = "random"
    yes_votes: set = field(default_factory=set)

@dataclass
class FeudAnswer:
    text: str
    points: int
    aliases: List[str] = field(default_factory=list)


@dataclass
class FeudQuestion:
    question: str
    answers: List[FeudAnswer]
    category: str = "general"
    pack: str = "base"
    difficulty: str = "normal"


@dataclass
class ChannelGame:
    channel_id: int
    question: FeudQuestion
    revealed: List[bool]
    guild_id: Optional[int] = None
    mode: str = "classic"
    started_at: float = field(default_factory=time.time)
    ends_at: Optional[float] = None
    captain_by_team: Dict[str, int] = field(default_factory=dict)
    strikes: int = 0
    team_strikes: Dict[str, int] = field(default_factory=lambda: {
        "red": 0,
        "blue": 0
    })
    player_scores: Dict[int, int] = field(default_factory=dict)
    player_names: Dict[int, str] = field(default_factory=dict)
    wrong_guesses: List[str] = field(default_factory=list)
    used_guesses: List[str] = field(default_factory=list)
    board_message_id: Optional[int] = None
    guesses_since_board: int = 0

    # Team mode
    player_teams: Dict[int, str] = field(default_factory=dict)
    team_scores: Dict[str, int] = field(default_factory=lambda: {
        "red": 0,
        "blue": 0
    })

    # Steal mode
    pending_steal: bool = False
    stealing_team: Optional[str] = None

    # Anti-spam cooldown
    last_guess_times: Dict[int, float] = field(default_factory=dict)

    # Round achievement tracking
    round_correct_streaks: Dict[int, int] = field(default_factory=dict)


# ----------------------------
# QUESTION LOADING
# ----------------------------

def normalize_category(category: Optional[str]) -> str:
    if not category:
        return "general"

    category = category.lower().strip()
    category = category.replace(" ", "_")
    category = category.replace("-", "_")

    return "_".join(category.split())


def normalize_mode(mode: Optional[str]) -> str:
    mode = normalize_category(mode or "classic")
    return mode if mode in GAME_MODES else "classic"


def normalize_pack(pack: Optional[str]) -> str:
    pack = normalize_category(pack or "random")
    if pack.startswith("pack:"):
        pack = pack.split(":", 1)[1]
    return pack


def read_json_file(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return default

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: {path} is invalid. Using default data.")
        return default


def write_json_file(path: str, data: Any) -> None:
    temp_path = f"{path}.tmp"

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    os.replace(temp_path, path)


def question_to_dict(question: FeudQuestion) -> dict:
    return {
        "category": question.category,
        "question": question.question,
        "pack": question.pack,
        "difficulty": question.difficulty,
        "answers": [
            {
                "text": answer.text,
                "points": answer.points,
                "aliases": answer.aliases
            }
            for answer in question.answers
        ]
    }


def infer_question_difficulty(answers: List[FeudAnswer], category: Optional[str]) -> str:
    category = normalize_category(category)

    if category in ["random_weird", "noir", "sci_fi", "fantasy", "horror", "mafia", "gangster"]:
        return "chaos"

    top_points = answers[0].points if answers else 0
    answer_count = len(answers)

    if answer_count <= 4 or top_points >= 38:
        return "easy"

    if answer_count >= 7 or top_points <= 32:
        return "hard"

    return "normal"


def question_from_dict(item: dict, pack: str = "base") -> FeudQuestion:
    answers = [
        FeudAnswer(
            text=answer["text"],
            points=int(answer["points"]),
            aliases=answer.get("aliases", [])
        )
        for answer in item["answers"]
    ]

    difficulty_value = item.get("difficulty")
    difficulty = normalize_category(difficulty_value) if difficulty_value else infer_question_difficulty(
        answers,
        item.get("category", "general")
    )

    if difficulty not in QUESTION_DIFFICULTIES:
        difficulty = infer_question_difficulty(answers, item.get("category", "general"))

    return FeudQuestion(
        question=item["question"],
        answers=answers,
        category=normalize_category(item.get("category", "general")),
        pack=normalize_category(item.get("pack", pack)),
        difficulty=difficulty
    )


def load_questions() -> List[FeudQuestion]:
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        raw_questions = json.load(file)

    questions: List[FeudQuestion] = []

    for item in raw_questions:
        questions.append(question_from_dict(item, pack="base"))

    for pack_file, pack_name in [
        (EXTRA_QUESTIONS_FILE, "fresh"),
        (MEGA_QUESTIONS_FILE, "mega")
    ]:
        for item in read_json_file(pack_file, []):
            questions.append(question_from_dict(item, pack=pack_name))

    if not questions:
        raise RuntimeError("No questions found in questions.json.")

    return questions


def load_custom_questions() -> Dict[str, List[FeudQuestion]]:
    raw_custom = read_json_file(CUSTOM_QUESTIONS_FILE, {})
    custom_questions: Dict[str, List[FeudQuestion]] = {}

    for guild_key, items in raw_custom.items():
        custom_questions[guild_key] = [
            question_from_dict(item, pack=f"server_{guild_key}")
            for item in items
        ]

    return custom_questions


def save_custom_questions(custom_questions: Dict[str, List[FeudQuestion]]) -> None:
    raw_custom = {
        guild_key: [question_to_dict(question) for question in questions]
        for guild_key, questions in custom_questions.items()
    }
    write_json_file(CUSTOM_QUESTIONS_FILE, raw_custom)
    sqlite_put("state", "custom_questions", raw_custom)


def load_server_settings() -> Dict[str, dict]:
    raw_settings = read_json_file(SETTINGS_FILE, {})

    for guild_key, settings in raw_settings.items():
        merged = DEFAULT_SERVER_SETTINGS.copy()
        merged.update(settings)
        raw_settings[guild_key] = merged

    return raw_settings


def save_server_settings(settings: Dict[str, dict]) -> None:
    write_json_file(SETTINGS_FILE, settings)
    sqlite_put("state", "settings", settings)


def load_engagement_state() -> dict:
    return read_json_file(ENGAGEMENT_FILE, {
        "daily_surveys": {},
        "suggestions": {},
        "team_rivalries": {},
        "player_rivalries": {},
        "last_reminders": {},
        "recent_questions": {},
        "question_analytics": {}
    })


def save_engagement_state(state: dict) -> None:
    write_json_file(ENGAGEMENT_FILE, state)
    sqlite_put("state", "engagement", state)


def load_server_scores() -> Dict[str, Dict[str, dict]]:
    return read_json_file(SCORES_FILE, {})


def save_server_scores(scores: Dict[str, Dict[str, dict]]) -> None:
    write_json_file(SCORES_FILE, scores)
    sqlite_put("state", "scores", scores)


def init_database() -> None:
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (namespace, key)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS question_analytics (
                guild_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, question_id)
            )
            """
        )


def sqlite_put(namespace: str, key: str, value: Any) -> None:
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute(
            """
            INSERT INTO kv_store(namespace, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(namespace, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (namespace, key, json.dumps(value, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
        )


def mirror_core_state_to_sqlite() -> None:
    sqlite_put("state", "scores", SERVER_SCORES)
    sqlite_put("state", "settings", SERVER_SETTINGS)
    sqlite_put("state", "custom_questions", {
        guild_key: [question_to_dict(question) for question in questions]
        for guild_key, questions in CUSTOM_QUESTIONS.items()
    })
    sqlite_put("state", "engagement", ENGAGEMENT_STATE)


init_database()
CUSTOM_QUESTIONS = load_custom_questions()
SERVER_SETTINGS = load_server_settings()
SERVER_SCORES = load_server_scores()
ENGAGEMENT_STATE = load_engagement_state()

QUESTIONS = load_questions()


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def get_server_settings(guild_id: Optional[int]) -> dict:
    settings = DEFAULT_SERVER_SETTINGS.copy()

    if guild_id is not None:
        settings.update(SERVER_SETTINGS.get(str(guild_id), {}))

    settings["max_strikes"] = max(1, min(6, int(settings.get("max_strikes", MAX_STRIKES))))
    settings["guess_cooldown_seconds"] = max(0, min(300, int(settings.get("guess_cooldown_seconds", GUESS_COOLDOWN_SECONDS))))
    settings["round_seconds"] = max(0, min(3600, int(settings.get("round_seconds", DEFAULT_ROUND_SECONDS))))
    settings["next_round_yes_votes_required"] = max(1, min(10, int(settings.get("next_round_yes_votes_required", NEXT_ROUND_YES_VOTES_REQUIRED))))
    settings["minimum_players"] = max(1, min(20, int(settings.get("minimum_players", 1))))
    settings["board_repost_every"] = max(1, min(10, int(settings.get("board_repost_every", BOARD_REPOST_EVERY))))
    settings["game_night_weekday"] = max(0, min(6, int(settings.get("game_night_weekday", 5))))
    settings["game_night_hour_utc"] = max(0, min(23, int(settings.get("game_night_hour_utc", 19))))
    settings["game_night_notice_minutes"] = max(0, min(1440, int(settings.get("game_night_notice_minutes", 30))))
    settings["daily_prompt_enabled"] = bool(settings.get("daily_prompt_enabled", False))
    settings["game_night_reminder_enabled"] = bool(settings.get("game_night_reminder_enabled", False))
    settings["quiet_mode"] = bool(settings.get("quiet_mode", False))
    settings["blacklisted_words"] = [
        normalize_text(word)
        for word in settings.get("blacklisted_words", [])
        if normalize_text(str(word))
    ]

    if settings.get("steal_mode") not in STEAL_MODES:
        settings["steal_mode"] = "any"

    if settings.get("host_personality") not in HOST_PERSONALITIES:
        settings["host_personality"] = "cheeky"

    return settings


def update_server_setting(guild_id: int, key: str, value: Any) -> dict:
    guild_key = str(guild_id)
    settings = get_server_settings(guild_id)
    settings[key] = value
    SERVER_SETTINGS[guild_key] = settings
    save_server_settings(SERVER_SETTINGS)
    return settings


def get_all_questions(guild_id: Optional[int] = None) -> List[FeudQuestion]:
    if guild_id is None:
        return QUESTIONS

    return QUESTIONS + CUSTOM_QUESTIONS.get(str(guild_id), [])


def get_questions_for_category(category: str, guild_id: Optional[int] = None) -> List[FeudQuestion]:
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


def question_id(question: FeudQuestion) -> str:
    answer_text = "|".join(normalize_text(answer.text) for answer in question.answers)
    return f"{question.category}:{normalize_text(question.question)}:{answer_text}"


def get_recent_question_ids(guild_id: Optional[int]) -> List[str]:
    if guild_id is None:
        return []

    ENGAGEMENT_STATE.setdefault("recent_questions", {})
    return ENGAGEMENT_STATE["recent_questions"].setdefault(str(guild_id), [])


def remember_question_used(guild_id: Optional[int], question: FeudQuestion) -> None:
    if guild_id is None:
        return

    recent = get_recent_question_ids(guild_id)
    qid = question_id(question)

    if qid in recent:
        recent.remove(qid)

    recent.append(qid)
    del recent[:-USED_QUESTIONS_LIMIT]
    save_engagement_state(ENGAGEMENT_STATE)


def get_question_analytics(guild_id: Optional[int], question: FeudQuestion) -> dict:
    guild_key = str(guild_id or "global")
    ENGAGEMENT_STATE.setdefault("question_analytics", {})
    ENGAGEMENT_STATE["question_analytics"].setdefault(guild_key, {})
    analytics = ENGAGEMENT_STATE["question_analytics"][guild_key].setdefault(question_id(question), {
        "question": question.question,
        "category": question.category,
        "difficulty": question.difficulty,
        "times_used": 0,
        "correct_guesses": 0,
        "wrong_guesses": 0,
        "skips": 0,
        "steals": 0,
        "full_clears": 0
    })
    return analytics


def update_question_analytics(guild_id: Optional[int], question: FeudQuestion, key: str, amount: int = 1) -> None:
    analytics = get_question_analytics(guild_id, question)
    analytics[key] = int(analytics.get(key, 0)) + amount
    save_engagement_state(ENGAGEMENT_STATE)

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute(
            """
            INSERT INTO question_analytics(guild_id, question_id, data, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, question_id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (
                str(guild_id or "global"),
                question_id(question),
                json.dumps(analytics, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat()
            )
        )


def pick_question(
    category: str = "random",
    guild_id: Optional[int] = None,
    difficulty: str = "any"
) -> Optional[FeudQuestion]:
    matching_questions = get_questions_for_category(category, guild_id=guild_id)
    difficulty = normalize_category(difficulty or "any")

    if difficulty != "any":
        matching_questions = [
            question
            for question in matching_questions
            if question.difficulty == difficulty
        ]

    if not matching_questions:
        return None

    recent_ids = set(get_recent_question_ids(guild_id))
    fresh_questions = [
        question
        for question in matching_questions
        if question_id(question) not in recent_ids
    ]

    return random.choice(fresh_questions or matching_questions)


def format_category_name(category: str) -> str:
    category = normalize_category(category)

    if category == "random":
        return "Random"

    if category.startswith("pack:"):
        return f"Pack: {format_category_name(normalize_pack(category))}"

    return category.replace("_", " ").title()


async def category_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    current = normalize_category(current)
    guild_id = interaction.guild.id if interaction.guild else None

    available_categories = sorted({
        normalize_category(question.category)
        for question in get_all_questions(guild_id)
    })

    categories = ["random"] + [
        category
        for category in FEUD_CATEGORIES
        if category != "random"
    ]

    # Also include any categories that exist in questions.json
    # even if you forgot to add them to FEUD_CATEGORIES.
    for category in available_categories:
        if category not in categories:
            categories.append(category)

    for pack in QUESTION_PACKS:
        pack_value = f"pack:{pack}"
        if pack_value not in categories:
            categories.append(pack_value)

    matching_categories = [
        category
        for category in categories
        if current in category
    ]

    return [
        app_commands.Choice(
            name=format_category_name(category),
            value=category
        )
        for category in matching_categories[:25]
    ]


async def mode_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    current = normalize_category(current)
    return [
        app_commands.Choice(name=format_category_name(mode), value=mode)
        for mode in GAME_MODES
        if current in mode
    ][:25]


async def difficulty_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    current = normalize_category(current)
    return [
        app_commands.Choice(name=format_category_name(difficulty), value=difficulty)
        for difficulty in QUESTION_DIFFICULTIES
        if current in difficulty
    ][:25]

IDLE_HOST_KEYWORD_RESPONSES = {
    "wrong": [
        "❌ Survey says... absolutely not, but I respect the confidence.",
        "That answer walked in wearing sunglasses and still got recognised as wrong.",
        "You said that like it was going to be on the board. It was not."
    ],
    "yes": [
        "🔔 I heard confidence. Dangerous thing in this game.",
        "That sounded like a top answer. Or a trap. Hard to tell around here.",
        "You said that with your chest. I like it."
    ],
    "no": [
        "❌ That was a strong no. The board felt that.",
        "No? You sure? People have lost families over less confidence.",
        "That no had final-answer energy."
    ],
    "money": [
        "💰 Money? Now everybody suddenly knows the top answer.",
        "Cash on the board? Suddenly the room wakes up.",
        "Money always makes the survey more honest."
    ],
    "food": [
        "🍔 Food answers are dangerous. Someone always says cheese.",
        "If this turns into a food round, I am judging everyone.",
        "Food has entered the chat. The board is officially hungry."
    ],
    "drink": [
        "🥤 Drinks? Careful now, this is how the answers get weird.",
        "That sounds like something someone says after the third round.",
        "I heard drink and immediately trusted the answer less."
    ],
    "rug": [
        "That rug better be on the board, because it really ties the channel together.",
        "Careful with rug answers. Some men have built whole lives around them.",
        "The rug has entered the survey. Respectfully."
    ],
    "dude": [
        "The Dude abides, but the board remains suspicious.",
        "That answer has sandals, a robe, and absolutely no urgency.",
        "Very relaxed answer. Almost too relaxed."
    ],
    "mafia": [
        "That answer came in wearing a pinstripe suit and asking no questions.",
        "Careful. The board knows a guy who knows a guy.",
        "That was either a survey answer or evidence."
    ],
    "gun": [
        "Easy there, cowboy. This is Family Fortunes, not the final scene.",
        "That answer kicked the door open and refused to elaborate.",
        "The board just ducked."
    ],
    "police": [
        "The police answer always makes half the room look nervous.",
        "Somebody said police and suddenly everyone remembered an appointment.",
        "That answer came with flashing lights."
    ],
    "boss": [
        "The boss answer has arrived. Everybody sit up straight.",
        "That sounded like something said from behind a big desk.",
        "Boss energy. Not necessarily correct energy."
    ],
    "love": [
        "Love? Bold choice. The survey is rarely that emotionally available.",
        "That answer brought feelings into a points-based environment.",
        "Love is beautiful. The board may still reject it."
    ],
    "wedding": [
        "Wedding answers always start sweet and end with someone arguing over chairs.",
        "Careful. Wedding rounds bring out aunties with opinions.",
        "That answer just cost £12,000 and came with chair covers."
    ],
    "cat": [
        "A cat answer? It may be correct, but it will ignore us anyway.",
        "The cat is not on the board because it refused to participate.",
        "That answer knocked something off a shelf and walked away."
    ],
    "dog": [
        "Dog answers always have tail-wagging confidence.",
        "That answer barked before it thought.",
        "The dog answer may be wrong, but everybody still loves it."
    ],
    "weather": [
        "Weather answers in Britain are basically cheating.",
        "Rain is always lurking somewhere on the board.",
        "You mention weather and every British person suddenly becomes a survey expert."
    ],
    "tea": [
        "Tea? Strong British answer. The board has put the kettle on.",
        "That answer came with two sugars and emotional support.",
        "Tea is never a bad answer. It may be wrong, but morally it is right."
    ],
    "discord": [
        "Discord answers are risky. Someone is about to ping everyone.",
        "That answer has been muted by three moderators.",
        "The server heard that and immediately made a new channel for it."
    ],
    "lag": [
        "Lag? Classic. The official excuse of champions and cowards.",
        "That answer arrived three seconds late but blamed the Wi-Fi.",
        "Survey says... check your ping."
    ]
}


IDLE_HOST_GENERIC_RESPONSES = [
    "I don't know what that means, but somebody's nan probably said it on a survey.",
    "That has top-answer confidence and bottom-answer danger.",
    "The board is listening. The board is concerned.",
    "You all talk like people who have never seen three strikes before.",
    "That answer would either win the round or get the whole family disowned.",
    "Somewhere, a survey of 100 people is shaking its head.",
    "I need everyone to remember: confidence is not the same as points.",
    "That was said with conviction. Sadly, conviction is worth zero unless it is on the board.",
    "You are all one bad answer away from hearing the big red X.",
    "I have seen families fall apart over guesses cleaner than that.",
    "That message has strong ‘number six on the board’ energy.",
    "You said that like the survey owed you money.",
    "Interesting answer. Not good. Interesting.",
    "That one made the imaginary audience gasp.",
    "I am not saying that is wrong. I am saying the board just looked away.",
    "If this was Fast Money, I would already be nervous.",
    "That answer came in hot and parked badly.",
    "The survey says nothing yet, but emotionally, it is judging.",
    "That is the kind of answer that makes the host take two steps back.",
    "I respect it. I fear it. I will not defend it."
]

DIRECT_HOST_RESPONSES = [
    "You called?",
    "I'm listening. Judging, mostly, but listening.",
    "Say it with confidence. The board respects confidence. Sometimes.",
    "I have heard worse answers on national television.",
    "Careful now. You are saying my name like you have a top answer.",
    "I am not responsible for what the survey does to your feelings.",
    "Go on then. Give me something for the board.",
    "That has the energy of an answer your uncle would shout at Christmas.",
    "I respect the confidence. I question the strategy.",
    "The board is awake now. Make it count.",
    "You summoned the host. That usually means chaos is nearby.",
    "I am here, microphone in hand, emotionally unprepared.",
    "If this answer is wrong, I am stepping away from the podium.",
    "Alright, talk to me. What are we putting on the board?",
    "That better be good. The imaginary audience is already leaning forward."
]

DIRECT_HOST_QUESTION_RESPONSES = [
    "My professional opinion? Someone is about to say something wild.",
    "I think the safest answer is usually boring, and the funniest answer is usually wrong.",
    "The board wants simple answers. People keep giving it trauma.",
    "I would say yes, but I have trusted worse answers before.",
    "If your nan would say it, it might be on the board.",
    "That sounds like a number four answer with number one confidence.",
    "I cannot legally guarantee points, but I can guarantee drama.",
    "The survey is mysterious. The survey is cruel. The survey is rarely impressed.",
    "My gut says maybe. My face says absolutely not.",
    "I have no idea, but I will react like I did."
]

HOST_PERSONALITY_LINES = {
    "quiet": [
        "The board is ready when you are.",
        "No round running. Start one when the room is ready.",
        "I am keeping the microphone warm."
    ],
    "cheeky": IDLE_HOST_GENERIC_RESPONSES,
    "tv_host": [
        "We asked 100 people and the channel is already arguing.",
        "The lights are up, the board is waiting, and somebody is about to overthink it.",
        "Give me a family, give me a buzzer, give me a suspiciously confident answer."
    ],
    "chaos": [
        "No active round. Dangerous. People may start forming opinions unsupervised.",
        "The board is asleep, but it is dreaming of bad guesses.",
        "Someone start a round before the survey develops a personality."
    ],
    "strict": [
        "No round is active. Use `/feud_lobby` or `/feud_start`.",
        "Waiting for a host to start the next round.",
        "Idle period noted. Prepare sensible answers."
    ],
    "steve": [
        "Name something this channel is about to shout with too much confidence.",
        "The board is ready. The moustache is metaphorical, but the judgement is real.",
        "Good answer? Bad answer? I will make the same face either way."
    ],
    "richard": [
        "Survey says the room is restless.",
        "If you know, you know. If you do not, say it loudly anyway.",
        "The board has elegance. The guesses may not."
    ],
    "dry_british": [
        "Splendid. No active round. Tragic, in a manageable way.",
        "The board waits with the emotional range of a damp Tuesday.",
        "Someone could start a round. No pressure, except all of it."
    ],
    "dramatic_american": [
        "We are one click away from survey glory!",
        "The board is locked, loaded, and ready for chaos!",
        "Families, fortunes, feelings: everything is on the line!"
    ],
    "quizmaster": [
        "Stand by. The next question may expose troubling confidence.",
        "Please prepare one sensible answer and three regrettable ones.",
        "The room is between rounds. This is when reputations are made."
    ]
}

WRONG_ANSWER_REACTIONS = [
    "❌ **Not on the board!** The survey did not enjoy that.",
    "❌ **Nope!** That answer walked in confident and left embarrassed.",
    "❌ **Big red X!** I respect it. The board does not.",
    "❌ **Not there!** Somewhere, 100 people refused to say that.",
    "❌ **No points!** That one had number seven energy.",
    "❌ **Survey says... no!** That answer just got escorted out.",
    "❌ **Oof.** The board looked at that and changed the subject.",
    "❌ **Not there!** Bold answer, tragic outcome.",
    "❌ **Wrong answer!** The imaginary audience made a noise at that one.",
    "❌ **No match!** That one came in wearing confidence and left with nothing."
]

CORRECT_ANSWER_REACTIONS = [
    "🔔 **Survey says... {answer}!**",
    "✅ **There it is! {answer}!**",
    "🔔 **Good answer! {answer} is on the board!**",
    "✅ **You found it! {answer}!**",
    "🔔 **Ding ding ding! {answer}!**",
    "✅ **That’s on the board! {answer}!**",
    "🔔 **The survey likes that one! {answer}!**",
    "✅ **Yes! {answer} was hiding up there!**",
    "🔔 **Show me... {answer}!**",
    "✅ **The board accepts it! {answer}!**"
]

ACHIEVEMENTS = {
    "first_ding": {
        "emoji": "🏅",
        "name": "First Ding",
        "description": "Get your first correct answer."
    },
    "hot_streak": {
        "emoji": "🔥",
        "name": "Hot Streak",
        "description": "Get 3 correct answers in one round."
    },
    "big_brain": {
        "emoji": "🧠",
        "name": "Big Brain",
        "description": "Find the top answer."
    },
    "ice_cold": {
        "emoji": "🧊",
        "name": "Ice Cold",
        "description": "Guess correctly after two strikes."
    },
    "survey_victim": {
        "emoji": "💀",
        "name": "Survey Victim",
        "description": "Give 10 wrong answers lifetime."
    },
    "board_boss": {
        "emoji": "🥇",
        "name": "Board Boss",
        "description": "Score 100+ points in one round."
    },
    "steal_specialist": {
        "emoji": "🚨",
        "name": "Steal Specialist",
        "description": "Win a board with a successful steal."
    },
    "speed_demon": {
        "emoji": "⚡",
        "name": "Speed Demon",
        "description": "Find an answer within 15 seconds of a round starting."
    },
    "chaos_champion": {
        "emoji": "🌪️",
        "name": "Chaos Champion",
        "description": "Win a Chaos Mode round."
    },
    "top_answer_magnet": {
        "emoji": "🧲",
        "name": "Top Answer Magnet",
        "description": "Find 10 top answers lifetime."
    },
    "red_loyalist": {
        "emoji": "🔴",
        "name": "Red Loyalist",
        "description": "Play 10 rounds on Red Team."
    },
    "blue_loyalist": {
        "emoji": "🔵",
        "name": "Blue Loyalist",
        "description": "Play 10 rounds on Blue Team."
    }
}

def get_other_team(team: str) -> str:
    return "blue" if team == "red" else "red"


def get_lower_scoring_team(game: ChannelGame) -> Optional[str]:
    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)

    if red_score < blue_score:
        return "red"

    if blue_score < red_score:
        return "blue"

    return None


async def safe_add_reaction(message: discord.Message, emoji: str) -> None:
    try:
        await message.add_reaction(emoji)
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass


def game_max_strikes(game: ChannelGame) -> int:
    if game.mode == "fast_money":
        return 1

    return get_server_settings(game.guild_id)["max_strikes"]


def get_team_strikes(game: ChannelGame, team: Optional[str]) -> int:
    if team in ["red", "blue"]:
        return int(game.team_strikes.get(team, 0))

    return int(game.strikes)


def add_team_strike(game: ChannelGame, team: Optional[str]) -> int:
    if team not in ["red", "blue"]:
        game.strikes += 1
        return game.strikes

    game.team_strikes[team] = get_team_strikes(game, team) + 1
    game.strikes = max(game.team_strikes.values())
    return game.team_strikes[team]


def clear_team_strikes(game: ChannelGame) -> None:
    game.strikes = 0
    game.team_strikes = {"red": 0, "blue": 0}


def game_guess_cooldown(game: ChannelGame) -> int:
    if game.mode in ["fast_money", "chaos"]:
        return min(5, get_server_settings(game.guild_id)["guess_cooldown_seconds"])

    return get_server_settings(game.guild_id)["guess_cooldown_seconds"]


def count_joined_players(game: ChannelGame) -> int:
    return len(game.player_teams)


def game_requires_more_players(game: ChannelGame) -> bool:
    settings = get_server_settings(game.guild_id)

    if game.mode == "teams_only":
        return not (
            any(team == "red" for team in game.player_teams.values()) and
            any(team == "blue" for team in game.player_teams.values())
        )

    return count_joined_players(game) < settings["minimum_players"]


async def start_new_round_in_channel(
    channel: discord.abc.Messageable,
    starter_text: Optional[str] = None,
    category: str = "random",
    mode: str = "classic",
    difficulty: str = "any"
) -> bool:
    channel_id = channel.id
    category = normalize_category(category)
    guild_id = channel.guild.id if getattr(channel, "guild", None) else None
    mode = normalize_mode(mode)
    difficulty = normalize_category(difficulty or "any")
    settings = get_server_settings(guild_id)

    if channel_id in active_games:
        await channel.send("A Family Fortunes round is already active in this channel.")
        return False

    # Clear any old next-round vote for this channel.
    if channel_id in next_round_votes:
        del next_round_votes[channel_id]

    question = pick_question(category, guild_id=guild_id, difficulty=difficulty)

    if question is None:
        await channel.send(
            f"❌ No questions found for category **{format_category_name(category)}**.\n"
            "Try `/feud_start category:random` or add questions with that category to `questions.json`."
        )
        return False

    round_seconds = settings["round_seconds"]

    if mode == "fast_money" and round_seconds == 0:
        round_seconds = 60
    elif mode == "chaos" and round_seconds == 0:
        round_seconds = 90

    ends_at = time.time() + round_seconds if round_seconds else None

    game = ChannelGame(
        channel_id=channel_id,
        question=question,
        revealed=[False for _ in question.answers],
        guild_id=guild_id,
        mode=mode,
        ends_at=ends_at
    )

    active_games[channel_id] = game
    remember_question_used(guild_id, question)
    update_question_analytics(guild_id, question, "times_used")

    category_text = format_category_name(question.category)

    if starter_text:
        await channel.send(starter_text, view=TeamJoinView(channel_id))
    else:
        await channel.send(
            f"🎬 **New Family Fortunes round started!**\n"
            f"📂 **Category:** `{category_text}`\n"
            f"🎮 **Mode:** `{format_category_name(mode)}`\n"
            f"🎚️ **Difficulty:** `{format_category_name(question.difficulty)}`\n"
            "Join a team with `/feud_join red` or `/feud_join blue`.\n"
            "Only joined players can guess, so normal chat will not count as strikes.",
            view=TeamJoinView(channel_id)
        )

    board_file_path = render_board_image(game)

    if board_file_path:
        board_message = await channel.send(
            embed=create_board_embed(game, compact=True),
            file=discord.File(board_file_path, filename="family_fortunes_board.png")
        )
    else:
        board_message = await channel.send(embed=create_board_embed(game))

    game.board_message_id = board_message.id
    save_active_games()
    schedule_round_timer(channel, game)
    return True


async def post_next_round_vote(
    channel: discord.abc.Messageable,
    category: str = "random"
):
    channel_id = channel.id
    category = normalize_category(category)
    guild_id = channel.guild.id if getattr(channel, "guild", None) else None
    settings = get_server_settings(guild_id)

    # Do not post a next-round vote if another round already started.
    if channel_id in active_games:
        return

    embed = discord.Embed(
        title="🎲 Play another round?",
        description=(
            f"📂 **Category:** `{format_category_name(category)}`\n\n"
            "React below:\n\n"
            "✅ **Yes** — start another round in the same category\n"
            "🛑 **Stop** — end the session\n\n"
            f"Needs `{settings['next_round_yes_votes_required']}` yes vote(s). "
            "You can also use `/feud_next` to start the next round."
        ),
        color=discord.Color.green()
    )

    vote_message = await channel.send(embed=embed)

    await safe_add_reaction(vote_message, "✅")
    await safe_add_reaction(vote_message, "🛑")

    next_round_votes[channel_id] = NextRoundVote(
        channel_id=channel_id,
        message_id=vote_message.id,
        category=category
    )

def get_revealed_board_points(game: ChannelGame) -> int:
    return sum(
        answer.points
        for index, answer in enumerate(game.question.answers)
        if game.revealed[index]
    )


def create_steal_embed(game: ChannelGame) -> discord.Embed:
    stealing_team = game.stealing_team

    if stealing_team == "red":
        team_text = "🔴 Red Team"
        color = discord.Color.red()
    else:
        team_text = "🔵 Blue Team"
        color = discord.Color.blue()

    embed = create_board_embed(
        game,
        title="🚨 Steal the Board!"
    )

    embed.color = color

    embed.add_field(
        name="Steal Chance",
        value=(
            f"{team_text} gets **one guess** to steal the board.\n"
            "Guess any remaining answer.\n\n"
            "✅ Correct = steal all revealed board points.\n"
            "❌ Wrong = current scores stay."
        ),
        inline=False
    )

    return embed

def get_idle_host_response(message_content: str, personality: str = "cheeky") -> Optional[str]:
    cleaned = normalize_text(message_content)

    if not cleaned:
        return None

    if len(cleaned) < 3:
        return None

    words = cleaned.split()

    for keyword, responses in IDLE_HOST_KEYWORD_RESPONSES.items():
        if keyword in words:
            return random.choice(responses)

    if random.random() <= IDLE_HOST_RANDOM_CHANCE:
        return random.choice(HOST_PERSONALITY_LINES.get(personality, IDLE_HOST_GENERIC_RESPONSES))

    return None

async def maybe_idle_host_comment(message: discord.Message):
    settings = get_server_settings(message.guild.id if message.guild else None)

    if settings["quiet_mode"] or not settings["idle_host_enabled"]:
        return

    if message.author.bot:
        return

    if not message.guild:
        return

    channel_id = message.channel.id

    # Do not do idle chat while a game is active in this channel.
    if channel_id in active_games:
        return

    # Ignore commands.
    if message.content.startswith("/") or message.content.startswith("!"):
        return

    await maybe_post_daily_survey(message, settings)

    now = time.time()

    # Direct host-name response: Steve / Richard
    if message_mentions_host_name(message.content):
        last_direct = last_direct_host_comment.get(channel_id, 0)

        if now - last_direct >= DIRECT_HOST_COOLDOWN_SECONDS:
            response = get_direct_host_response(message.content)
            last_direct_host_comment[channel_id] = now
            await message.channel.send(response)
            return

    # Normal occasional idle commentary
    last_comment = last_idle_host_comment.get(channel_id, 0)

    if now - last_comment < IDLE_HOST_COOLDOWN_SECONDS:
        return

    response = get_idle_host_response(message.content, settings["host_personality"])

    if not response:
        return

    last_idle_host_comment[channel_id] = now

    await message.channel.send(response)


async def maybe_post_daily_survey(message: discord.Message, settings: dict) -> None:
    if not message.guild or not settings["daily_prompt_enabled"]:
        return

    configured_channel_id = settings.get("daily_prompt_channel_id")

    if configured_channel_id and int(configured_channel_id) != message.channel.id:
        return

    guild_data = get_guild_engagement(message.guild.id)
    survey = guild_data["daily_surveys"].get(today_key())

    if survey and survey.get("posted"):
        return

    if random.random() > 0.08:
        return

    embed = make_daily_survey_embed(message.guild.id)
    guild_data["daily_surveys"][today_key()]["posted"] = True
    save_engagement_state(ENGAGEMENT_STATE)
    await message.channel.send(embed=embed)

def message_mentions_host_name(message_content: str) -> bool:
    cleaned = normalize_text(message_content)

    words = cleaned.split()

    for host_name in HOST_NAMES:
        if host_name in words:
            return True

    return False


def get_direct_host_response(message_content: str) -> str:
    cleaned = normalize_text(message_content)
    words = cleaned.split()

    if "?" in message_content:
        return random.choice(DIRECT_HOST_QUESTION_RESPONSES)

    if any(word in words for word in ["wrong", "robbed", "cheated", "unfair"]):
        return "Robbed? Maybe. Wrong? Also maybe. The board is a harsh place."

    if any(word in words for word in ["right", "correct", "sure"]):
        return "You sound very sure. That is normally where the trouble starts."

    if "top answer" in cleaned:
        return "You sound very sure. That is normally where the trouble starts."

    if any(word in words for word in ["help", "hint", "clue"]):
        return "No hints from me. I just stand here and make faces at bad answers."

    if any(word in words for word in ["hello", "hi", "alright", "oi", "hey"]):
        return "Alright. I am here. The board is watching."

    return random.choice(DIRECT_HOST_RESPONSES)

def create_lifetime_leaderboard_embed(
    guild_id: int,
    limit: int = 10,
    period: str = "lifetime"
) -> discord.Embed:
    guild_key = str(guild_id)
    guild_scores = SERVER_SCORES.get(guild_key, {})
    period = normalize_category(period)
    score_key = {
        "daily": "daily_points",
        "weekly": "weekly_points"
    }.get(period, "total_points")

    embed = discord.Embed(
        title=f"🏆 Family Fortunes {format_category_name(period)} Leaderboard",
        color=discord.Color.purple()
    )

    if not guild_scores:
        embed.description = "No lifetime scores recorded for this server yet."
        return embed

    for data in guild_scores.values():
        refresh_period_scores(data)

    sorted_scores = sorted(
        guild_scores.items(),
        key=lambda item: item[1].get(score_key, 0),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(sorted_scores[:limit], start=1):
        name = data.get("name", f"Player {user_id}")
        total_points = data.get(score_key, 0)
        correct_answers = data.get("correct_answers", 0)
        best_streak = data.get("best_streak", 0)

        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = f"**{position}.**"

        lines.append(
            f"{medal} **{name}** — `{total_points}` pts | `{correct_answers}` correct | 🔥 best streak `{best_streak}`"
        )

    embed.description = "\n".join(lines)
    embed.set_footer(text="Scores are tracked per server. Daily and weekly boards reset automatically.")

    return embed


def current_period_keys() -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return now.date().isoformat(), f"{year}-W{week:02d}"


DAILY_SURVEY_PROMPTS = [
    "Name something people pretend to understand.",
    "Name something that disappears the moment you need it.",
    "Name something people buy and immediately regret.",
    "Name something that makes a group chat go silent.",
    "Name something everyone says they will do tomorrow.",
    "Name something that feels illegal but is not.",
    "Name something people get weirdly competitive about.",
    "Name something that ruins a perfectly good morning.",
    "Name something people always forget to charge.",
    "Name something that sounds fancy but is basically normal."
]

WEEKLY_CHALLENGES = [
    ("Top Answer Hunter", "Find 3 top answers this week.", "weekly_top_answers", 3),
    ("Point Collector", "Score 250 points this week.", "weekly_points", 250),
    ("Comeback Crew", "Win 2 rounds this week.", "weekly_wins", 2),
    ("Brave Guesser", "Make 15 correct guesses this week.", "weekly_correct", 15),
    ("Chaos Merchant", "Win a Chaos Mode round this week.", "weekly_chaos_wins", 1)
]


def current_weekly_challenge() -> Tuple[str, str, str, int]:
    _, week_key = current_period_keys()
    week_number = int(week_key.split("W")[-1])
    return WEEKLY_CHALLENGES[week_number % len(WEEKLY_CHALLENGES)]


def today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def stable_daily_index() -> int:
    return sum(ord(character) for character in today_key()) % len(DAILY_SURVEY_PROMPTS)


def get_guild_engagement(guild_id: int) -> dict:
    guild_key = str(guild_id)

    for section in ["daily_surveys", "suggestions", "team_rivalries", "player_rivalries", "last_reminders"]:
        ENGAGEMENT_STATE.setdefault(section, {})

    ENGAGEMENT_STATE["daily_surveys"].setdefault(guild_key, {})
    ENGAGEMENT_STATE["suggestions"].setdefault(guild_key, [])
    ENGAGEMENT_STATE["team_rivalries"].setdefault(guild_key, {
        "red_wins": 0,
        "blue_wins": 0,
        "draws": 0,
        "last_winner": None
    })
    ENGAGEMENT_STATE["player_rivalries"].setdefault(guild_key, {})
    return {
        "daily_surveys": ENGAGEMENT_STATE["daily_surveys"][guild_key],
        "suggestions": ENGAGEMENT_STATE["suggestions"][guild_key],
        "team_rivalries": ENGAGEMENT_STATE["team_rivalries"][guild_key],
        "player_rivalries": ENGAGEMENT_STATE["player_rivalries"][guild_key]
    }


def make_daily_survey_embed(guild_id: int) -> discord.Embed:
    guild_data = get_guild_engagement(guild_id)
    survey = guild_data["daily_surveys"].get(today_key())

    if not survey:
        prompt = DAILY_SURVEY_PROMPTS[stable_daily_index()]
        survey = {"prompt": prompt, "answers": {}}
        guild_data["daily_surveys"][today_key()] = survey
        save_engagement_state(ENGAGEMENT_STATE)

    answers = survey.get("answers", {})
    top_answers = sorted(answers.items(), key=lambda item: len(item[1]), reverse=True)[:5]

    embed = discord.Embed(
        title="📋 Survey of the Day",
        description=f"**{survey['prompt']}**\n\nReply with `/feud_daily_answer answer:<your answer>`.",
        color=discord.Color.blurple()
    )

    if top_answers:
        lines = [
            f"**{position}.** {answer} — `{len(user_ids)}` vote(s)"
            for position, (answer, user_ids) in enumerate(top_answers, start=1)
        ]
        embed.add_field(name="Current Crowd Answers", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Current Crowd Answers", value="No answers yet.", inline=False)

    return embed


def refresh_period_scores(user_data: dict) -> None:
    today_key, week_key = current_period_keys()

    if user_data.get("daily_key") != today_key:
        user_data["daily_key"] = today_key
        user_data["daily_points"] = 0
        user_data["daily_correct"] = 0
        user_data["daily_top_answers"] = 0

    if user_data.get("weekly_key") != week_key:
        user_data["weekly_key"] = week_key
        user_data["weekly_points"] = 0
        user_data["weekly_correct"] = 0
        user_data["weekly_top_answers"] = 0
        user_data["weekly_wins"] = 0
        user_data["weekly_chaos_wins"] = 0


def seed_score_record(display_name: str) -> dict:
    today_key, week_key = current_period_keys()

    return {
        "name": display_name,
        "total_points": 0,
        "correct_answers": 0,
        "wrong_answers": 0,
        "current_streak": 0,
        "best_streak": 0,
        "rounds_played": 0,
        "achievements": [],
        "daily_key": today_key,
        "daily_points": 0,
        "daily_correct": 0,
        "daily_top_answers": 0,
        "weekly_key": week_key,
        "weekly_points": 0,
        "weekly_correct": 0,
        "weekly_top_answers": 0,
        "weekly_wins": 0,
        "weekly_chaos_wins": 0,
        "games_won": 0,
        "top_answers": 0,
        "favorite_team": None
    }

def add_lifetime_score(
    guild_id: int,
    user_id: int,
    display_name: str,
    points: int
) -> None:
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in SERVER_SCORES:
        SERVER_SCORES[guild_key] = {}

    if user_key not in SERVER_SCORES[guild_key]:
        SERVER_SCORES[guild_key][user_key] = seed_score_record(display_name)

    user_data = SERVER_SCORES[guild_key][user_key]

    # Backwards compatibility for old server_scores.json files
    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)
    user_data.setdefault("achievements", [])
    user_data.setdefault("games_won", 0)
    user_data.setdefault("top_answers", 0)
    user_data.setdefault("favorite_team", None)
    refresh_period_scores(user_data)

    user_data["name"] = display_name
    user_data["total_points"] += points
    user_data["correct_answers"] += 1
    user_data["daily_points"] += points
    user_data["daily_correct"] += 1
    user_data["weekly_points"] += points
    user_data["weekly_correct"] += 1

    user_data["current_streak"] += 1

    if user_data["current_streak"] > user_data["best_streak"]:
        user_data["best_streak"] = user_data["current_streak"]

    save_server_scores(SERVER_SCORES)

def record_wrong_lifetime_guess(
    guild_id: int,
    user_id: int,
    display_name: str
) -> None:
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in SERVER_SCORES:
        SERVER_SCORES[guild_key] = {}

    if user_key not in SERVER_SCORES[guild_key]:
        SERVER_SCORES[guild_key][user_key] = seed_score_record(display_name)

    user_data = SERVER_SCORES[guild_key][user_key]

    # Backwards compatibility for old server_scores.json files
    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)
    user_data.setdefault("achievements", [])
    user_data.setdefault("games_won", 0)
    user_data.setdefault("top_answers", 0)
    user_data.setdefault("favorite_team", None)
    refresh_period_scores(user_data)

    user_data["name"] = display_name
    user_data["wrong_answers"] += 1
    user_data["current_streak"] = 0

    save_server_scores(SERVER_SCORES)

def get_or_create_user_score_record(
    guild_id: int,
    user_id: int,
    display_name: str
) -> dict:
    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in SERVER_SCORES:
        SERVER_SCORES[guild_key] = {}

    if user_key not in SERVER_SCORES[guild_key]:
        SERVER_SCORES[guild_key][user_key] = seed_score_record(display_name)

    user_data = SERVER_SCORES[guild_key][user_key]

    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)
    user_data.setdefault("achievements", [])
    user_data.setdefault("games_won", 0)
    user_data.setdefault("top_answers", 0)
    user_data.setdefault("favorite_team", None)
    refresh_period_scores(user_data)

    user_data["name"] = display_name

    return user_data


def award_achievement(
    guild_id: int,
    user_id: int,
    display_name: str,
    achievement_id: str
) -> Optional[str]:
    if achievement_id not in ACHIEVEMENTS:
        return None

    user_data = get_or_create_user_score_record(
        guild_id=guild_id,
        user_id=user_id,
        display_name=display_name
    )

    achievements = user_data.setdefault("achievements", [])

    if achievement_id in achievements:
        return None

    achievements.append(achievement_id)
    save_server_scores(SERVER_SCORES)

    achievement = ACHIEVEMENTS[achievement_id]

    return (
        f"{achievement['emoji']} **Achievement unlocked for {display_name}: "
        f"{achievement['name']}** — {achievement['description']}"
    )


def record_top_answer(guild_id: int, user_id: int, display_name: str) -> None:
    user_data = get_or_create_user_score_record(guild_id, user_id, display_name)
    refresh_period_scores(user_data)
    user_data["top_answers"] = user_data.get("top_answers", 0) + 1
    user_data["daily_top_answers"] = user_data.get("daily_top_answers", 0) + 1
    user_data["weekly_top_answers"] = user_data.get("weekly_top_answers", 0) + 1
    save_server_scores(SERVER_SCORES)


def increment_team_loyalty(user_data: dict, team: str) -> int:
    key = f"{team}_rounds"
    user_data[key] = user_data.get(key, 0) + 1
    return user_data[key]


def get_achievement_summary(user_data: dict) -> str:
    achievement_ids = user_data.get("achievements", [])

    if not achievement_ids:
        return "No achievements unlocked yet."

    lines = []

    for achievement_id in achievement_ids:
        achievement = ACHIEVEMENTS.get(achievement_id)

        if not achievement:
            continue

        lines.append(
            f"{achievement['emoji']} **{achievement['name']}** — {achievement['description']}"
        )

    return "\n".join(lines) if lines else "No achievements unlocked yet."

def normalize_text(text: str) -> str:
    text = text.lower().strip()

    replacements = {
        "&": " and ",
        "?": "",
        "!": "",
        ".": "",
        ",": "",
        "'": "",
        "\"": "",
        "-": " ",
        "_": " "
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def load_board_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)

    return ImageFont.load_default()


def fit_text_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int = 24) -> ImageFont.ImageFont:
    for size in range(max_size, min_size - 1, -2):
        font = load_board_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)

        if bbox[2] - bbox[0] <= max_width:
            return font

    return load_board_font(min_size)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    stroke_fill: Optional[Tuple[int, int, int]] = None,
    stroke_width: int = 0
) -> None:
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + ((right - left) - width) / 2
    y = top + ((bottom - top) - height) / 2 - 2
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill or fill
    )


def render_board_image(game: ChannelGame) -> Optional[str]:
    if not os.path.exists(BOARD_TEMPLATE_FILE):
        return None

    os.makedirs(BOARD_RENDER_DIR, exist_ok=True)
    image = Image.open(BOARD_TEMPLATE_FILE).convert("RGBA")
    draw = ImageDraw.Draw(image)

    score_font = load_board_font(72)
    strike_font = load_board_font(92)
    index_font = load_board_font(64)
    answer_font = load_board_font(48)
    points_font = load_board_font(58)
    small_font = load_board_font(32)
    label_font = load_board_font(36)

    blue = (0, 153, 255)
    gold = (255, 191, 40)
    white = (245, 248, 255)
    dark = (0, 0, 0)
    red = (230, 40, 40)

    red_score = str(game.team_scores.get("red", 0)).zfill(4)[-4:]
    blue_score = str(game.team_scores.get("blue", 0)).zfill(4)[-4:]
    draw.rounded_rectangle((70, 58, 348, 108), radius=10, fill=(7, 17, 65))
    draw.rounded_rectangle((1324, 58, 1602, 108), radius=10, fill=(7, 17, 65))
    draw_centered_text(draw, (70, 58, 348, 108), "RED TEAM", label_font, white, stroke_fill=dark, stroke_width=1)
    draw_centered_text(draw, (1324, 58, 1602, 108), "BLUE TEAM", label_font, white, stroke_fill=dark, stroke_width=1)
    draw.rounded_rectangle((101, 110, 318, 189), radius=10, fill=(0, 0, 0))
    draw.rounded_rectangle((1353, 110, 1568, 189), radius=10, fill=(0, 0, 0))
    draw_centered_text(draw, (99, 116, 318, 187), red_score, score_font, blue)
    draw_centered_text(draw, (1351, 116, 1568, 187), blue_score, score_font, blue)

    for strike_index in range(3):
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

    row_top = 233
    row_height = 81
    row_gap = 0

    for index in range(8):
        top = row_top + index * row_height + row_gap
        bottom = top + 68

        if index < len(game.question.answers):
            answer = game.question.answers[index]
            draw.rounded_rectangle((1292, top + 4, 1413, bottom - 2), radius=8, fill=(0, 0, 0))

            if game.revealed[index]:
                text = answer.text.upper()
                font = fit_text_font(draw, text, 850, 46, 24)
                draw.text(
                    (391, top + 12),
                    text,
                    font=font,
                    fill=white,
                    stroke_width=2,
                    stroke_fill=dark
                )
                draw_centered_text(
                    draw,
                    (1298, top, 1412, bottom),
                    str(answer.points).zfill(3),
                    points_font,
                    gold,
                    stroke_fill=dark,
                    stroke_width=2
                )
            else:
                hidden = "█" * max(10, min(28, len(answer.text) + 4))
                font = fit_text_font(draw, hidden, 850, 34, 20)
                draw.text((391, top + 20), hidden, font=font, fill=(22, 35, 62))
                draw_centered_text(draw, (1298, top, 1412, bottom), "000", points_font, gold, stroke_fill=dark, stroke_width=2)
        else:
            draw.rounded_rectangle((1292, top + 4, 1413, bottom - 2), radius=8, fill=(0, 0, 0))
            draw_centered_text(draw, (1298, top, 1412, bottom), "000", points_font, gold, stroke_fill=dark, stroke_width=2)

    footer = f"{format_category_name(game.question.category)} | {format_category_name(game.mode)} | {format_category_name(game.question.difficulty)}"
    draw_centered_text(draw, (470, 880, 1215, 925), footer.upper(), small_font, white, stroke_fill=dark, stroke_width=2)

    output_path = os.path.join(BOARD_RENDER_DIR, f"board_{game.channel_id}.png")
    image.save(output_path)
    return output_path


SPELLING_VARIANTS = {
    "color": "colour",
    "favorite": "favourite",
    "mom": "mum",
    "trash": "rubbish",
    "garbage": "rubbish",
    "apartment": "flat",
    "elevator": "lift",
    "vacation": "holiday",
    "soccer": "football",
    "fries": "chips",
    "chips": "crisps",
    "candy": "sweets",
    "cellphone": "mobile",
    "phone": "mobile"
}


def simple_singular(text: str) -> str:
    words = []

    for word in text.split():
        if len(word) > 4 and word.endswith("ies"):
            words.append(f"{word[:-3]}y")
        elif len(word) > 3 and word.endswith("es"):
            words.append(word[:-2])
        elif len(word) > 3 and word.endswith("s"):
            words.append(word[:-1])
        else:
            words.append(word)

    return " ".join(words)


def expand_match_terms(text: str) -> List[str]:
    normalized = normalize_text(text)
    terms = {normalized, simple_singular(normalized)}
    words = normalized.split()
    variant_words = [SPELLING_VARIANTS.get(word, word) for word in words]
    reverse_variants = {value: key for key, value in SPELLING_VARIANTS.items()}
    reverse_words = [reverse_variants.get(word, word) for word in words]
    terms.add(" ".join(variant_words))
    terms.add(" ".join(reverse_words))
    return [term for term in terms if term]


def answer_terms(answer: FeudAnswer) -> List[str]:
    terms = [answer.text] + answer.aliases
    expanded_terms = []

    for term in terms:
        expanded_terms.extend(expand_match_terms(term))

    return list(dict.fromkeys(expanded_terms))


def find_matching_answer(
    guess: str,
    game: ChannelGame
) -> Tuple[Optional[int], Optional[FeudAnswer], bool]:
    """
    Returns:
    - answer index
    - answer object
    - fuzzy_match_used
    """

    cleaned_guess = normalize_text(guess)

    for index, answer in enumerate(game.question.answers):
        if game.revealed[index]:
            continue

        terms = answer_terms(answer)

        # Exact alias/text match
        if cleaned_guess in terms:
            return index, answer, False

        guess_tokens = set(cleaned_guess.split())

        # Slightly flexible check
        for term in terms:
            term_tokens = set(term.split())

            if len(cleaned_guess) >= 4 and len(term) >= 4:
                if cleaned_guess in term or term in cleaned_guess:
                    return index, answer, True

            if guess_tokens and term_tokens:
                if guess_tokens.issubset(term_tokens) or term_tokens.issubset(guess_tokens):
                    return index, answer, True

            similarity = difflib.SequenceMatcher(None, cleaned_guess, term).ratio()

            if similarity >= FUZZY_MATCH_THRESHOLD:
                return index, answer, True

    return None, None, False


def all_answers_revealed(game: ChannelGame) -> bool:
    return all(game.revealed)


def create_board_embed(game: ChannelGame, title: str = "🎤 Family Fortunes", compact: bool = False) -> discord.Embed:
    settings = get_server_settings(game.guild_id)
    timer_text = ""

    if game.ends_at:
        remaining = max(0, int(game.ends_at - time.time()))
        timer_text = f"\n⏱️ **Time left:** `{remaining // 60}:{remaining % 60:02d}`"

    embed = discord.Embed(
        title=title,
        description=(
            f"📂 **Category:** `{format_category_name(game.question.category)}`\n\n"
            f"🎮 **Mode:** `{format_category_name(game.mode)}` | "
            f"🎚️ `{format_category_name(game.question.difficulty)}`{timer_text}\n\n"
            f"**{game.question.question}**"
        ),
        color=discord.Color.gold()
    )

    if compact:
        red_players = [
            game.player_names.get(user_id, f"Player {user_id}")
            for user_id, team in game.player_teams.items()
            if team == "red"
        ]

        blue_players = [
            game.player_names.get(user_id, f"Player {user_id}")
            for user_id, team in game.player_teams.items()
            if team == "blue"
        ]

        embed.add_field(
            name="🔴 Red Players",
            value=", ".join(red_players) if red_players else "No players yet",
            inline=True
        )
        embed.add_field(
            name="🔵 Blue Players",
            value=", ".join(blue_players) if blue_players else "No players yet",
            inline=True
        )
        embed.set_footer(
            text=f"Join with /feud_join red or /feud_join blue. Players can guess once every {settings['guess_cooldown_seconds']} seconds."
        )
        return embed

    board_lines = []

    for index, answer in enumerate(game.question.answers):
        number = index + 1

        if game.revealed[index]:
            board_lines.append(
                f"**{number}. {answer.text}** — `{answer.points}`"
            )
        else:
            hidden_bar = "█" * max(4, min(12, answer.points // 3))
            board_lines.append(
                f"**{number}.** `{hidden_bar}`"
            )

    embed.add_field(
        name="Board",
        value="\n".join(board_lines),
        inline=False
    )

    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)

    embed.add_field(
        name="🔴 Red Team",
        value=f"`{red_score}` points",
        inline=True
    )

    embed.add_field(
        name="🔵 Blue Team",
        value=f"`{blue_score}` points",
        inline=True
    )

    max_strikes = settings["max_strikes"]

    embed.add_field(
        name="Strikes",
        value=(
            f"🔴 `{get_team_strikes(game, 'red')}/{max_strikes}`\n"
            f"🔵 `{get_team_strikes(game, 'blue')}/{max_strikes}`"
        ),
        inline=True
    )

    revealed_points = sum(
        answer.points
        for index, answer in enumerate(game.question.answers)
        if game.revealed[index]
    )

    total_points = sum(answer.points for answer in game.question.answers)

    embed.add_field(
        name="Points Found",
        value=f"`{revealed_points}/{total_points}`",
        inline=True
    )

    red_players = [
        game.player_names.get(user_id, f"Player {user_id}")
        for user_id, team in game.player_teams.items()
        if team == "red"
    ]

    blue_players = [
        game.player_names.get(user_id, f"Player {user_id}")
        for user_id, team in game.player_teams.items()
        if team == "blue"
    ]

    embed.add_field(
        name="🔴 Red Players",
        value=", ".join(red_players) if red_players else "No players yet",
        inline=False
    )

    embed.add_field(
        name="🔵 Blue Players",
        value=", ".join(blue_players) if blue_players else "No players yet",
        inline=False
    )

    if game.wrong_guesses:
        recent_wrong = ", ".join(game.wrong_guesses[-5:])
        embed.add_field(
            name="Wrong Guesses",
            value=recent_wrong,
            inline=False
        )

    embed.set_footer(
        text=f"Join with /feud_join red or /feud_join blue. Players can guess once every {settings['guess_cooldown_seconds']} seconds."
    )

    return embed


def create_final_embed(game: ChannelGame, reason: str) -> discord.Embed:
    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)

    if red_score > blue_score:
        winner_text = f"🔴 **Red Team wins!** `{red_score}` - `{blue_score}`"
    elif blue_score > red_score:
        winner_text = f"🔵 **Blue Team wins!** `{blue_score}` - `{red_score}`"
    else:
        winner_text = f"🤝 **It is a draw!** `{red_score}` - `{blue_score}`"

    embed = discord.Embed(
        title="🏁 Round Over",
        description=f"{reason}\n\n{winner_text}",
        color=discord.Color.blue()
    )

    final_board = []

    for index, answer in enumerate(game.question.answers, start=1):
        final_board.append(f"**{index}. {answer.text}** — `{answer.points}`")

    embed.add_field(
        name="Final Board",
        value="\n".join(final_board),
        inline=False
    )

    embed.add_field(
        name="Team Scores",
        value=f"🔴 Red Team — `{red_score}` points\n🔵 Blue Team — `{blue_score}` points",
        inline=False
    )

    if game.wrong_guesses:
        embed.add_field(
            name="Funniest Wrong Guess",
            value=random.choice(game.wrong_guesses[-8:]),
            inline=True
        )

    embed.add_field(
        name="Round Recap",
        value=(
            f"📂 `{format_category_name(game.question.category)}` | "
            f"🎚️ `{format_category_name(game.question.difficulty)}` | "
            f"❌ 🔴 `{get_team_strikes(game, 'red')}` 🔵 `{get_team_strikes(game, 'blue')}` | "
            f"🔎 `{len(game.used_guesses)}` guess(es)"
        ),
        inline=False
    )

    if game.player_scores:
        sorted_scores = sorted(
            game.player_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )

        score_lines = []

        for position, (user_id, score) in enumerate(sorted_scores, start=1):
            name = game.player_names.get(user_id, f"Player {user_id}")
            team = game.player_teams.get(user_id, "no team")

            if team == "red":
                team_icon = "🔴"
            elif team == "blue":
                team_icon = "🔵"
            else:
                team_icon = "⚪"

            if position == 1:
                score_lines.append(f"🥇 {team_icon} **{name}** — `{score}` points")
            elif position == 2:
                score_lines.append(f"🥈 {team_icon} **{name}** — `{score}` points")
            elif position == 3:
                score_lines.append(f"🥉 {team_icon} **{name}** — `{score}` points")
            else:
                score_lines.append(f"**{position}.** {team_icon} **{name}** — `{score}` points")

        embed.add_field(
            name="Individual Scores",
            value="\n".join(score_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="Individual Scores",
            value="Nobody scored this round.",
            inline=False
        )

    return embed

def create_score_embed(game: ChannelGame) -> discord.Embed:
    embed = discord.Embed(
        title="🏆 Current Scores",
        color=discord.Color.green()
    )

    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)

    embed.add_field(
        name="Team Scores",
        value=f"🔴 Red Team — `{red_score}` points\n🔵 Blue Team — `{blue_score}` points",
        inline=False
    )

    if not game.player_scores:
        embed.add_field(
            name="Individual Scores",
            value="No individual points scored yet.",
            inline=False
        )
        return embed

    sorted_scores = sorted(
        game.player_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    lines = []

    for position, (user_id, score) in enumerate(sorted_scores, start=1):
        name = game.player_names.get(user_id, f"Player {user_id}")
        team = game.player_teams.get(user_id, "no team")

        if team == "red":
            team_icon = "🔴"
        elif team == "blue":
            team_icon = "🔵"
        else:
            team_icon = "⚪"

        lines.append(
            f"**{position}.** {team_icon} **{name}** — `{score}` points"
        )

    embed.add_field(
        name="Individual Scores",
        value="\n".join(lines),
        inline=False
    )

    return embed

# ----------------------------
# BOT SETUP
# ----------------------------

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

active_games: Dict[int, ChannelGame] = {}
next_round_votes: Dict[int, NextRoundVote] = {}
round_timer_tasks: Dict[int, asyncio.Task] = {}
active_lobbies: Dict[int, dict] = {}
fast_money_games: Dict[int, dict] = {}
engagement_background_task: Optional[asyncio.Task] = None

last_idle_host_comment: Dict[int, float] = {}
last_direct_host_comment: Dict[int, float] = {}


def game_to_dict(game: ChannelGame) -> dict:
    return {
        "channel_id": game.channel_id,
        "guild_id": game.guild_id,
        "question": question_to_dict(game.question),
        "revealed": game.revealed,
        "mode": game.mode,
        "started_at": game.started_at,
        "ends_at": game.ends_at,
        "captain_by_team": {team: str(user_id) for team, user_id in game.captain_by_team.items()},
        "strikes": game.strikes,
        "team_strikes": game.team_strikes,
        "player_scores": {str(user_id): score for user_id, score in game.player_scores.items()},
        "player_names": {str(user_id): name for user_id, name in game.player_names.items()},
        "wrong_guesses": game.wrong_guesses,
        "used_guesses": game.used_guesses,
        "board_message_id": game.board_message_id,
        "guesses_since_board": game.guesses_since_board,
        "player_teams": {str(user_id): team for user_id, team in game.player_teams.items()},
        "team_scores": game.team_scores,
        "pending_steal": game.pending_steal,
        "stealing_team": game.stealing_team,
        "last_guess_times": {str(user_id): value for user_id, value in game.last_guess_times.items()},
        "round_correct_streaks": {str(user_id): value for user_id, value in game.round_correct_streaks.items()}
    }


def game_from_dict(data: dict) -> ChannelGame:
    game = ChannelGame(
        channel_id=int(data["channel_id"]),
        guild_id=data.get("guild_id"),
        question=question_from_dict(data["question"]),
        revealed=data.get("revealed", []),
        mode=normalize_mode(data.get("mode", "classic")),
        started_at=float(data.get("started_at", time.time())),
        ends_at=data.get("ends_at")
    )
    game.captain_by_team = {
        team: int(user_id)
        for team, user_id in data.get("captain_by_team", {}).items()
    }
    game.strikes = int(data.get("strikes", 0))
    game.team_strikes = data.get("team_strikes", {"red": game.strikes, "blue": 0})
    game.team_strikes.setdefault("red", 0)
    game.team_strikes.setdefault("blue", 0)
    game.player_scores = {int(user_id): int(score) for user_id, score in data.get("player_scores", {}).items()}
    game.player_names = {int(user_id): name for user_id, name in data.get("player_names", {}).items()}
    game.wrong_guesses = data.get("wrong_guesses", [])
    game.used_guesses = data.get("used_guesses", [])
    game.board_message_id = data.get("board_message_id")
    game.guesses_since_board = int(data.get("guesses_since_board", 0))
    game.player_teams = {int(user_id): team for user_id, team in data.get("player_teams", {}).items()}
    game.team_scores = data.get("team_scores", {"red": 0, "blue": 0})
    game.pending_steal = bool(data.get("pending_steal", False))
    game.stealing_team = data.get("stealing_team")
    game.last_guess_times = {int(user_id): float(value) for user_id, value in data.get("last_guess_times", {}).items()}
    game.round_correct_streaks = {int(user_id): int(value) for user_id, value in data.get("round_correct_streaks", {}).items()}
    return game


def save_active_games() -> None:
    write_json_file(
        ACTIVE_GAMES_FILE,
        {str(channel_id): game_to_dict(game) for channel_id, game in active_games.items()}
    )


def load_active_games() -> None:
    raw_games = read_json_file(ACTIVE_GAMES_FILE, {})
    active_games.clear()

    for channel_id, data in raw_games.items():
        try:
            active_games[int(channel_id)] = game_from_dict(data)
        except Exception as error:
            print(f"Skipping saved game {channel_id}: {error}")


def record_round_result(game: ChannelGame) -> None:
    if not game.guild_id:
        return

    red_score = game.team_scores.get("red", 0)
    blue_score = game.team_scores.get("blue", 0)
    winning_team = None

    if red_score > blue_score:
        winning_team = "red"
    elif blue_score > red_score:
        winning_team = "blue"

    guild_engagement = get_guild_engagement(game.guild_id)
    team_rivalry = guild_engagement["team_rivalries"]

    if winning_team == "red":
        team_rivalry["red_wins"] = team_rivalry.get("red_wins", 0) + 1
        team_rivalry["last_winner"] = "red"
    elif winning_team == "blue":
        team_rivalry["blue_wins"] = team_rivalry.get("blue_wins", 0) + 1
        team_rivalry["last_winner"] = "blue"
    else:
        team_rivalry["draws"] = team_rivalry.get("draws", 0) + 1
        team_rivalry["last_winner"] = "draw"

    player_rivalries = guild_engagement["player_rivalries"]
    red_players = [user_id for user_id, team in game.player_teams.items() if team == "red"]
    blue_players = [user_id for user_id, team in game.player_teams.items() if team == "blue"]

    for red_player in red_players:
        for blue_player in blue_players:
            pair_key = "-".join(str(user_id) for user_id in sorted([red_player, blue_player]))
            pair = player_rivalries.setdefault(pair_key, {
                str(red_player): 0,
                str(blue_player): 0,
                "draws": 0
            })

            if winning_team == game.player_teams.get(red_player):
                pair[str(red_player)] = pair.get(str(red_player), 0) + 1
            elif winning_team == game.player_teams.get(blue_player):
                pair[str(blue_player)] = pair.get(str(blue_player), 0) + 1
            else:
                pair["draws"] = pair.get("draws", 0) + 1

    for user_id, team in game.player_teams.items():
        user_data = get_or_create_user_score_record(
            guild_id=game.guild_id,
            user_id=user_id,
            display_name=game.player_names.get(user_id, f"Player {user_id}")
        )
        user_data["rounds_played"] = user_data.get("rounds_played", 0) + 1
        user_data["favorite_team"] = team
        team_rounds = increment_team_loyalty(user_data, team)

        if team == "red" and team_rounds >= 10:
            award_achievement(game.guild_id, user_id, user_data["name"], "red_loyalist")
        elif team == "blue" and team_rounds >= 10:
            award_achievement(game.guild_id, user_id, user_data["name"], "blue_loyalist")

        if winning_team and team == winning_team:
            user_data["games_won"] = user_data.get("games_won", 0) + 1
            user_data["weekly_wins"] = user_data.get("weekly_wins", 0) + 1

            if game.mode == "chaos":
                user_data["weekly_chaos_wins"] = user_data.get("weekly_chaos_wins", 0) + 1
                award_achievement(game.guild_id, user_id, user_data["name"], "chaos_champion")

    save_server_scores(SERVER_SCORES)
    save_engagement_state(ENGAGEMENT_STATE)


def end_active_game(channel_id: int, game: Optional[ChannelGame] = None) -> None:
    if game is None:
        game = active_games.get(channel_id)

    if game:
        record_round_result(game)

    if channel_id in round_timer_tasks:
        task = round_timer_tasks[channel_id]
        if task is not asyncio.current_task():
            task.cancel()
        del round_timer_tasks[channel_id]

    if channel_id in active_games:
        del active_games[channel_id]

    save_active_games()


async def round_timer_worker(channel: discord.abc.Messageable, game: ChannelGame) -> None:
    if not game.ends_at:
        return

    warned = set()

    while game.channel_id in active_games:
        remaining = int(game.ends_at - time.time())

        if remaining <= 0:
            final_embed = create_final_embed(game, "⏱️ Time is up!")
            await channel.send(embed=final_embed)
            end_active_game(game.channel_id, game)
            await post_next_round_vote(channel, category=game.question.category)
            return

        for marker in [60, 30, 10]:
            if remaining <= marker and marker not in warned:
                warned.add(marker)
                await channel.send(f"⏱️ `{marker}` seconds left on the board.")

        await asyncio.sleep(2)


def schedule_round_timer(channel: discord.abc.Messageable, game: ChannelGame) -> None:
    if not game.ends_at:
        return

    if game.channel_id in round_timer_tasks:
        round_timer_tasks[game.channel_id].cancel()

    round_timer_tasks[game.channel_id] = asyncio.create_task(round_timer_worker(channel, game))


async def engagement_background_worker() -> None:
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(timezone.utc)

        for guild in bot.guilds:
            settings = get_server_settings(guild.id)

            if settings["game_night_reminder_enabled"] and settings.get("game_night_channel_id"):
                reminder_time = now.replace(
                    hour=settings["game_night_hour_utc"],
                    minute=0,
                    second=0,
                    microsecond=0
                )
                reminder_time = reminder_time.replace(
                    day=now.day
                )
                should_remind = (
                    now.weekday() == settings["game_night_weekday"] and
                    0 <= (reminder_time - now).total_seconds() <= settings["game_night_notice_minutes"] * 60
                )
                reminder_key = f"{guild.id}:{today_key()}:game_night"
                ENGAGEMENT_STATE.setdefault("last_reminders", {})

                if should_remind and ENGAGEMENT_STATE["last_reminders"].get(reminder_key) != "sent":
                    channel = guild.get_channel(int(settings["game_night_channel_id"]))

                    if channel:
                        await channel.send(
                            "🎙️ **Family Fortunes night is coming up.** "
                            "Use `/feud_lobby` to ready up and vote for the first category."
                        )
                        ENGAGEMENT_STATE["last_reminders"][reminder_key] = "sent"
                        save_engagement_state(ENGAGEMENT_STATE)

        await asyncio.sleep(300)


async def reveal_answer_number(
    channel: discord.abc.Messageable,
    game: ChannelGame,
    number: int,
    reason: str = "Host reveal"
) -> bool:
    index = number - 1

    if index < 0 or index >= len(game.question.answers):
        return False

    if game.revealed[index]:
        return False

    game.revealed[index] = True
    answer = game.question.answers[index]
    await channel.send(f"🎬 **{reason}:** `{number}. {answer.text}` for `{answer.points}` points.")
    await update_board_message(channel, game, force_new=True)
    save_active_games()

    if all_answers_revealed(game):
        await channel.send(embed=create_final_embed(game, "✅ The board has been fully revealed."))
        end_active_game(game.channel_id, game)
        await post_next_round_vote(channel, category=game.question.category)

    return True


async def reveal_all_answers(channel: discord.abc.Messageable, game: ChannelGame, reason: str = "Host revealed the board") -> None:
    game.revealed = [True for _ in game.question.answers]
    await update_board_message(channel, game, force_new=True)
    await channel.send(embed=create_final_embed(game, reason))
    end_active_game(game.channel_id, game)
    await post_next_round_vote(channel, category=game.question.category)


async def interaction_has_host_permission(interaction: discord.Interaction) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False

    permissions = interaction.user.guild_permissions
    return permissions.manage_messages or permissions.manage_guild


class FeudAdminView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=600)
        self.channel_id = channel_id

    async def get_game_or_reply(self, interaction: discord.Interaction) -> Optional[ChannelGame]:
        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message(
                "You need Manage Messages to use host controls.",
                ephemeral=True
            )
            return None

        game = active_games.get(self.channel_id)

        if game is None:
            await interaction.response.send_message(
                "There is no active round in this channel.",
                ephemeral=True
            )
            return None

        return game

    @discord.ui.button(label="Board", style=discord.ButtonStyle.secondary)
    async def board_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return
        await interaction.response.send_message(embed=create_board_embed(game), ephemeral=True)

    @discord.ui.button(label="Reveal Next", style=discord.ButtonStyle.primary)
    async def reveal_next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return

        await interaction.response.defer(ephemeral=True)

        for index, revealed in enumerate(game.revealed, start=1):
            if not revealed:
                await reveal_answer_number(interaction.channel, game, index, reason="Host reveal")
                await interaction.followup.send("Revealed the next hidden answer.", ephemeral=True)
                return

        await interaction.followup.send("Every answer is already revealed.", ephemeral=True)

    @discord.ui.button(label="Clear Strikes", style=discord.ButtonStyle.secondary)
    async def clear_strikes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return

        clear_team_strikes(game)
        game.pending_steal = False
        game.stealing_team = None
        await update_board_message(interaction.channel, game)
        await interaction.response.send_message("Strikes cleared.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.danger)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return

        category = game.question.category
        mode = game.mode
        end_active_game(self.channel_id, game)
        await interaction.response.defer(ephemeral=True)
        await start_new_round_in_channel(interaction.channel, category=category, mode=mode)
        await interaction.followup.send("Skipped to a new question.", ephemeral=True)

    @discord.ui.button(label="Reveal All", style=discord.ButtonStyle.danger)
    async def reveal_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return

        await interaction.response.defer(ephemeral=True)
        await reveal_all_answers(interaction.channel, game)
        await interaction.followup.send("Revealed the full board.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.get_game_or_reply(interaction)
        if not game:
            return

        final_embed = create_final_embed(game, "🛑 The host stopped the round.")
        end_active_game(self.channel_id, game)
        await interaction.response.send_message(embed=final_embed)


class TeamJoinView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=1800)
        self.channel_id = channel_id
        self.add_item(ActiveTeamJoinButton("red"))
        self.add_item(ActiveTeamJoinButton("blue"))


class ActiveTeamJoinButton(discord.ui.Button):
    def __init__(self, team: str):
        label = "Join Red" if team == "red" else "Join Blue"
        style = discord.ButtonStyle.danger if team == "red" else discord.ButtonStyle.primary
        super().__init__(label=label, style=style)
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        game = active_games.get(self.view.channel_id)

        if not game:
            await interaction.response.send_message("That round is no longer active.", ephemeral=True)
            return

        user_id = interaction.user.id
        display_name = interaction.user.display_name

        if user_id in game.player_scores and game.player_scores[user_id] > 0:
            await interaction.response.send_message("You cannot switch teams after scoring points this round.", ephemeral=True)
            return

        game.player_teams[user_id] = self.team
        game.player_names[user_id] = display_name
        game.captain_by_team.setdefault(self.team, user_id)
        save_active_games()
        await update_board_message(interaction.channel, game)
        await interaction.response.send_message(f"You joined **{format_category_name(self.team)} Team**.", ephemeral=True)


def pick_vote_categories() -> List[str]:
    categories = [category for category in FEUD_CATEGORIES if category != "random"]
    categories.extend([f"pack:{pack}" for pack in QUESTION_PACKS])
    return random.sample(categories, k=min(3, len(categories)))


class CategoryVoteView(discord.ui.View):
    def __init__(self, channel_id: int, categories: Optional[List[str]] = None):
        super().__init__(timeout=900)
        self.channel_id = channel_id
        self.categories = categories or pick_vote_categories()
        self.votes: Dict[int, str] = {}

        for category in self.categories:
            self.add_item(CategoryVoteButton(category))

    def winning_category(self) -> str:
        if not self.votes:
            return self.categories[0]

        totals = {
            category: list(self.votes.values()).count(category)
            for category in self.categories
        }
        return max(totals.items(), key=lambda item: item[1])[0]

    def summary(self) -> str:
        totals = {
            category: list(self.votes.values()).count(category)
            for category in self.categories
        }
        return "\n".join(
            f"**{format_category_name(category)}** — `{total}` vote(s)"
            for category, total in totals.items()
        )


class CategoryVoteButton(discord.ui.Button):
    def __init__(self, category: str):
        super().__init__(label=format_category_name(category), style=discord.ButtonStyle.secondary)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        view: CategoryVoteView = self.view
        view.votes[interaction.user.id] = self.category

        if isinstance(view, LobbyView):
            await view.refresh(interaction)

        await interaction.response.send_message(
            f"Vote counted for **{format_category_name(self.category)}**.\n\n{view.summary()}",
            ephemeral=True
        )


class LobbyView(CategoryVoteView):
    def __init__(self, channel_id: int, mode: str = "classic"):
        super().__init__(channel_id)
        self.mode = normalize_mode(mode)
        self.red_players: Dict[int, str] = {}
        self.blue_players: Dict[int, str] = {}
        self.add_item(LobbyJoinButton("red"))
        self.add_item(LobbyJoinButton("blue"))
        self.add_item(LobbyStartButton())

    def lobby_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎙️ Family Fortunes Lobby",
            description=(
                f"🎮 **Mode:** `{format_category_name(self.mode)}`\n"
                f"📂 **Winning Category:** `{format_category_name(self.winning_category())}`"
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="🔴 Red Team",
            value=", ".join(self.red_players.values()) if self.red_players else "No players yet",
            inline=False
        )
        embed.add_field(
            name="🔵 Blue Team",
            value=", ".join(self.blue_players.values()) if self.blue_players else "No players yet",
            inline=False
        )
        embed.add_field(name="Category Votes", value=self.summary(), inline=False)
        return embed

    async def refresh(self, interaction: discord.Interaction) -> None:
        if interaction.message:
            await interaction.message.edit(embed=self.lobby_embed(), view=self)


class LobbyJoinButton(discord.ui.Button):
    def __init__(self, team: str):
        label = "Join Red" if team == "red" else "Join Blue"
        style = discord.ButtonStyle.danger if team == "red" else discord.ButtonStyle.primary
        super().__init__(label=label, style=style)
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        view: LobbyView = self.view
        view.red_players.pop(interaction.user.id, None)
        view.blue_players.pop(interaction.user.id, None)

        if self.team == "red":
            view.red_players[interaction.user.id] = interaction.user.display_name
        else:
            view.blue_players[interaction.user.id] = interaction.user.display_name

        await view.refresh(interaction)
        await interaction.response.send_message(f"You joined **{format_category_name(self.team)} Team**.", ephemeral=True)


class LobbyStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Start Round", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: LobbyView = self.view

        if not await interaction_has_host_permission(interaction):
            await interaction.response.send_message("A host needs Manage Messages to start from the lobby.", ephemeral=True)
            return

        if view.channel_id in active_games:
            await interaction.response.send_message("A round is already active in this channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        category = view.winning_category()
        started = await start_new_round_in_channel(interaction.channel, category=category, mode=view.mode)

        if started:
            game = active_games[view.channel_id]

            for user_id, name in view.red_players.items():
                game.player_teams[user_id] = "red"
                game.player_names[user_id] = name

            for user_id, name in view.blue_players.items():
                game.player_teams[user_id] = "blue"
                game.player_names[user_id] = name

            game.captain_by_team = {}
            if view.red_players:
                game.captain_by_team["red"] = next(iter(view.red_players.keys()))
            if view.blue_players:
                game.captain_by_team["blue"] = next(iter(view.blue_players.keys()))

            save_active_games()
            active_lobbies.pop(view.channel_id, None)
            await update_board_message(interaction.channel, game)

        await interaction.followup.send("Lobby round started." if started else "No round was started.", ephemeral=True)


class MiniPollView(discord.ui.View):
    def __init__(self, question: FeudQuestion):
        super().__init__(timeout=900)
        self.question = question
        self.options = random.sample(question.answers, k=min(3, len(question.answers)))

        if question.answers[0] not in self.options:
            self.options[0] = question.answers[0]

        random.shuffle(self.options)
        self.votes: Dict[int, str] = {}

        for answer in self.options:
            self.add_item(MiniPollButton(answer.text))

        self.add_item(MiniPollRevealButton())

    def embed(self, revealed: bool = False) -> discord.Embed:
        embed = discord.Embed(
            title="📊 Mini Survey Poll",
            description=f"**Which answer do you think was worth the most?**\n\n{self.question.question}",
            color=discord.Color.blurple()
        )
        totals = {
            answer.text: list(self.votes.values()).count(answer.text)
            for answer in self.options
        }
        embed.add_field(
            name="Votes",
            value="\n".join(f"**{answer}** — `{total}`" for answer, total in totals.items()),
            inline=False
        )

        if revealed:
            top_answer = self.question.answers[0]
            embed.add_field(
                name="Survey Says",
                value=f"Top answer: **{top_answer.text}** for `{top_answer.points}` points.",
                inline=False
            )

        return embed


class MiniPollButton(discord.ui.Button):
    def __init__(self, answer_text: str):
        super().__init__(label=answer_text[:80], style=discord.ButtonStyle.secondary)
        self.answer_text = answer_text

    async def callback(self, interaction: discord.Interaction):
        view: MiniPollView = self.view
        view.votes[interaction.user.id] = self.answer_text
        if interaction.message:
            await interaction.message.edit(embed=view.embed(), view=view)
        await interaction.response.send_message(f"Vote counted for **{self.answer_text}**.", ephemeral=True)


class MiniPollRevealButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Reveal", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view: MiniPollView = self.view
        if interaction.message:
            await interaction.message.edit(embed=view.embed(revealed=True), view=None)
        await interaction.response.send_message("Revealed the mini poll.", ephemeral=True)

# ----------------------------
# BOT EVENTS
# ----------------------------

@bot.event
async def on_ready():
    global engagement_background_task

    print(f"Logged in as {bot.user}.")
    load_active_games()

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Failed to sync commands: {error}")

    for channel_id, game in list(active_games.items()):
        channel = bot.get_channel(channel_id)

        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception:
                continue

        schedule_round_timer(channel, game)

    if engagement_background_task is None or engagement_background_task.done():
        engagement_background_task = asyncio.create_task(engagement_background_worker())

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    channel_id = payload.channel_id

    if channel_id not in next_round_votes:
        return

    vote = next_round_votes[channel_id]

    if payload.message_id != vote.message_id:
        return

    emoji = str(payload.emoji)

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return

    # If a round already started somehow, clear the vote.
    if channel_id in active_games:
        del next_round_votes[channel_id]
        return

    if emoji == "✅":
        vote.yes_votes.add(payload.user_id)

        settings = get_server_settings(channel.guild.id if getattr(channel, "guild", None) else None)

        if len(vote.yes_votes) >= settings["next_round_yes_votes_required"]:
            del next_round_votes[channel_id]

            await start_new_round_in_channel(
                channel,
                starter_text=(
                    f"✅ **Another round it is!**\n"
                    f"📂 **Category:** `{format_category_name(vote.category)}`\n"
                    "Join a team with `/feud_join red` or `/feud_join blue`."
                ),
                category=vote.category
            )
        return

    if emoji == "🛑":
        del next_round_votes[channel_id]
        await channel.send("🛑 **Family Fortunes session stopped.**")
        return

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    channel_id = message.channel.id

    # If no game is active, let the host occasionally comment on normal chat.
    if channel_id not in active_games:
        await maybe_idle_host_comment(message)
        return

    # Ignore slash-looking or command-looking messages.
    if message.content.startswith("/") or message.content.startswith("!"):
        return

    game = active_games[channel_id]

    user_id = message.author.id
    display_name = message.author.display_name

    # Only registered players can make guesses.
    # Everyone else can chat normally without causing strikes.
    if user_id not in game.player_teams:
        return

    # If the round is in steal mode, only the stealing team gets one guess.
    if game.pending_steal:
        await handle_steal_guess(message, game)
        return

    if game_requires_more_players(game):
        await message.channel.send(
            "The round needs more players before guesses count. Use `/feud_join red` or `/feud_join blue`.",
            delete_after=6
        )
        return

    guess = normalize_text(message.content)

    if not guess:
        return

    settings = get_server_settings(game.guild_id)

    if settings["quiet_mode"]:
        return

    if len(guess) < 2 or len(set(guess.replace(" ", ""))) <= 1:
        await safe_add_reaction(message, "🧹")
        return

    if any(word and word in guess.split() for word in settings["blacklisted_words"]):
        await safe_add_reaction(message, "⛔")
        await message.channel.send(
            f"⛔ **{display_name}**, that guess is blocked by this server's Family Fortunes filter.",
            delete_after=6
        )
        return

    now = time.time()
    last_guess_time = game.last_guess_times.get(user_id, 0)
    seconds_since_last_guess = now - last_guess_time
    cooldown_seconds = game_guess_cooldown(game)

    if seconds_since_last_guess < cooldown_seconds:
        remaining = int(cooldown_seconds - seconds_since_last_guess)
        await safe_add_reaction(message, "⏳")

        try:
            await message.channel.send(
                f"⏳ **{display_name}**, wait `{remaining}` more seconds before guessing again.",
                delete_after=5
            )
        except discord.Forbidden:
            pass

        return

    game.last_guess_times[user_id] = now

    if guess in game.used_guesses:
        await safe_add_reaction(message, "🔁")
        return

    game.used_guesses.append(guess)
    game.guesses_since_board += 1

    answer_index, answer, fuzzy_used = find_matching_answer(guess, game)

    if answer is not None and answer_index is not None:
        update_question_analytics(game.guild_id, game.question, "correct_guesses")
        game.revealed[answer_index] = True

        team = game.player_teams.get(user_id)

        awarded_points = answer.points

        if game.mode == "chaos":
            awarded_points += random.choice([0, 5, 10, 15])

        game.player_scores[user_id] = game.player_scores.get(user_id, 0) + awarded_points
        game.player_names[user_id] = display_name

        if team in game.team_scores:
            game.team_scores[team] += awarded_points

        current_streak = 0
        best_streak = 0
        achievement_messages = []

        # Track correct answers in this round for Hot Streak.
        game.round_correct_streaks[user_id] = game.round_correct_streaks.get(user_id, 0) + 1
        round_streak = game.round_correct_streaks[user_id]

        if message.guild:
            add_lifetime_score(
                guild_id=message.guild.id,
                user_id=user_id,
                display_name=display_name,
                points=awarded_points
            )

            guild_key = str(message.guild.id)
            user_key = str(user_id)
            user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})

            current_streak = user_data.get("current_streak", 0)
            best_streak = user_data.get("best_streak", 0)
            correct_answers = user_data.get("correct_answers", 0)

            # 🏅 First Ding — first ever correct answer
            if correct_answers == 1:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "first_ding"
                )
                if msg:
                    achievement_messages.append(msg)

            # 🧠 Big Brain — got the top answer
            if answer_index == 0:
                record_top_answer(message.guild.id, user_id, display_name)
                user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})

                if user_data.get("top_answers", 0) >= 10:
                    msg = award_achievement(
                        message.guild.id,
                        user_id,
                        display_name,
                        "top_answer_magnet"
                    )
                    if msg:
                        achievement_messages.append(msg)

                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "big_brain"
                )
                if msg:
                    achievement_messages.append(msg)

            # 🧊 Ice Cold — correct after two strikes
            if get_team_strikes(game, team) >= 2:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "ice_cold"
                )
                if msg:
                    achievement_messages.append(msg)

            # 🔥 Hot Streak — 3 correct in one round
            if round_streak >= 3:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "hot_streak"
                )
                if msg:
                    achievement_messages.append(msg)

            # 🥇 Board Boss — 100+ points in one round
            if game.player_scores.get(user_id, 0) >= 100:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "board_boss"
                )
                if msg:
                    achievement_messages.append(msg)

            if time.time() - game.started_at <= 15:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "speed_demon"
                )
                if msg:
                    achievement_messages.append(msg)
        await safe_add_reaction(message, "✅")
        await asyncio.sleep(0.8)

        team_icon = "🔴" if team == "red" else "🔵"

        correct_intro = random.choice(CORRECT_ANSWER_REACTIONS).format(
            answer=answer.text.upper()
        )

        streak_line = ""

        if current_streak >= 2:
            streak_line = f"\n🔥 **Streak:** `{current_streak}` correct in a row!"

        if best_streak and current_streak == best_streak and current_streak >= 2:
            streak_line += f"\n🏅 **New best streak:** `{best_streak}`!"

        achievement_text = ""

        if achievement_messages:
            achievement_text = "\n\n" + "\n".join(achievement_messages)

        if fuzzy_used:
            response_text = (
                f"{correct_intro}\n"
                f"{team_icon} `+{awarded_points}` points to **{display_name}** and their team."
                f"{streak_line}"
                f"{achievement_text}\n"
                f"_Accepted as a close match._"
            )
        else:
            response_text = (
                f"{correct_intro}\n"
                f"{team_icon} `+{awarded_points}` points to **{display_name}** and their team."
                f"{streak_line}"
                f"{achievement_text}"
            )
        await message.channel.send(response_text)

        await update_board_message(message.channel, game)

        save_active_games()

        if game.mode == "sudden_death" or all_answers_revealed(game):
            if all_answers_revealed(game):
                update_question_analytics(game.guild_id, game.question, "full_clears")
            final_embed = create_final_embed(
                game,
                "⚡ Sudden Death answer found!" if game.mode == "sudden_death" else "✅ Every answer was found!"
            )
            await message.channel.send(embed=final_embed)
            end_active_game(channel_id, game)
            await post_next_round_vote(message.channel, category=game.question.category)

        return

    # Wrong answer
    update_question_analytics(game.guild_id, game.question, "wrong_guesses")
    team = game.player_teams.get(user_id)
    team_strikes = add_team_strike(game, team)
    game.wrong_guesses.append(message.content.strip())

    achievement_messages = []

    # Wrong answer resets the player's round streak too.
    game.round_correct_streaks[user_id] = 0

    if message.guild:
        record_wrong_lifetime_guess(
            guild_id=message.guild.id,
            user_id=user_id,
            display_name=display_name
        )

        guild_key = str(message.guild.id)
        user_key = str(user_id)
        user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})
        wrong_answers = user_data.get("wrong_answers", 0)

        # 💀 Survey Victim — 10 wrong answers lifetime
        if wrong_answers >= 10:
            msg = award_achievement(
                message.guild.id,
                user_id,
                display_name,
                "survey_victim"
            )
            if msg:
                achievement_messages.append(msg)

    wrong_text = random.choice(WRONG_ANSWER_REACTIONS)

    achievement_text = ""
    if achievement_messages:
        achievement_text = "\n\n" + "\n".join(achievement_messages)

    await safe_add_reaction(message, "❌")
    await asyncio.sleep(0.6)
    await message.channel.send(
        f"{wrong_text} {('Red Team' if team == 'red' else 'Blue Team')} strike `{team_strikes}/{game_max_strikes(game)}`\n"
        f"💥 **{display_name}'s streak has been reset.**"
        f"{achievement_text}"
    )
    await update_board_message(message.channel, game)

    save_active_games()

    if team_strikes >= game_max_strikes(game):
        stealing_team = get_other_team(team)

        # If the lower-scoring team has nobody in it, end the round normally.
        stealing_players = [
            user_id
            for user_id, team in game.player_teams.items()
            if team == stealing_team
        ]

        if not stealing_players:
            final_embed = create_final_embed(
                game,
                "❌❌❌ Three team strikes! No players are available on the other team to steal."
            )
            await message.channel.send(embed=final_embed)
            end_active_game(channel_id, game)
            await post_next_round_vote(message.channel, category=game.question.category)
            return

        game.pending_steal = True
        game.stealing_team = stealing_team
        save_active_games()

        steal_embed = create_steal_embed(game)

        team_text = "🔴 Red Team" if stealing_team == "red" else "🔵 Blue Team"

        await message.channel.send(
            f"🚨 **Three strikes for {('Red Team' if team == 'red' else 'Blue Team')}!** "
            f"{team_text} gets one chance to **steal the board**!"
        )

        await message.channel.send(embed=steal_embed)


async def update_board_message(
    channel: discord.abc.Messageable,
    game: ChannelGame,
    force_new: bool = False
):
    embed = create_board_embed(game)
    settings = get_server_settings(game.guild_id)
    board_file_path = render_board_image(game)

    # Re-post the board every 4 guesses so it stays visible in chat.
    if force_new or game.guesses_since_board >= settings["board_repost_every"]:
        if board_file_path:
            new_message = await channel.send(
                embed=create_board_embed(game, compact=True),
                file=discord.File(board_file_path, filename="family_fortunes_board.png")
            )
        else:
            new_message = await channel.send(embed=embed)

        game.board_message_id = new_message.id
        game.guesses_since_board = 0
        save_active_games()
        return

    # Attachments cannot be reliably edited in place, so image boards are reposted.
    if board_file_path:
        new_message = await channel.send(
            embed=create_board_embed(game, compact=True),
            file=discord.File(board_file_path, filename="family_fortunes_board.png")
        )
        game.board_message_id = new_message.id
        game.guesses_since_board = 0
        save_active_games()
        return

    # Otherwise, just edit the latest text board message.
    if game.board_message_id:
        try:
            old_message = await channel.fetch_message(game.board_message_id)
            await old_message.edit(embed=embed)
            save_active_games()
            return
        except Exception:
            pass

    # Fallback if the old board cannot be edited/found.
    new_message = await channel.send(embed=embed)
    game.board_message_id = new_message.id
    game.guesses_since_board = 0
    save_active_games()

async def handle_steal_guess(message: discord.Message, game: ChannelGame):
    channel_id = message.channel.id
    user_id = message.author.id
    display_name = message.author.display_name
    player_team = game.player_teams.get(user_id)

    if not game.pending_steal or not game.stealing_team:
        return

    if player_team != game.stealing_team:
        await safe_add_reaction(message, "⛔")

        try:
            team_name = "Red Team" if game.stealing_team == "red" else "Blue Team"
            await message.channel.send(
                f"⛔ Only **{team_name}** can make the steal guess.",
                delete_after=6
            )
        except discord.Forbidden:
            pass

        return

    settings = get_server_settings(game.guild_id)
    captain_id = game.captain_by_team.get(game.stealing_team)

    if settings["steal_mode"] == "captain" and captain_id and captain_id != user_id:
        await safe_add_reaction(message, "⛔")
        await message.channel.send(
            "Only this team's captain can make the steal guess.",
            delete_after=6
        )
        return

    guess = normalize_text(message.content)

    if not guess:
        return

    settings = get_server_settings(game.guild_id)

    if settings["quiet_mode"]:
        return

    if len(guess) < 2 or len(set(guess.replace(" ", ""))) <= 1:
        await safe_add_reaction(message, "🧹")
        return

    if any(word and word in guess.split() for word in settings["blacklisted_words"]):
        await safe_add_reaction(message, "⛔")
        await message.channel.send(
            f"⛔ **{display_name}**, that steal guess is blocked by this server's Family Fortunes filter.",
            delete_after=6
        )
        return

    game.used_guesses.append(guess)

    answer_index, answer, fuzzy_used = find_matching_answer(guess, game)

    # ----------------------------
    # SUCCESSFUL STEAL
    # ----------------------------
    if answer is not None and answer_index is not None:
        update_question_analytics(game.guild_id, game.question, "correct_guesses")
        update_question_analytics(game.guild_id, game.question, "steals")
        game.revealed[answer_index] = True

        stealing_team = game.stealing_team
        defending_team = get_other_team(stealing_team)

        board_points = get_revealed_board_points(game)

        # The steal team takes the revealed board pot.
        game.team_scores[stealing_team] = board_points
        game.team_scores[defending_team] = 0

        awarded_points = answer.points

        if game.mode == "chaos":
            awarded_points += random.choice([0, 5, 10, 15])

        game.player_scores[user_id] = game.player_scores.get(user_id, 0) + awarded_points
        game.player_names[user_id] = display_name

        achievement_messages = []
        current_streak = 0
        best_streak = 0

        game.round_correct_streaks[user_id] = game.round_correct_streaks.get(user_id, 0) + 1
        round_streak = game.round_correct_streaks[user_id]

        if message.guild:
            add_lifetime_score(
                guild_id=message.guild.id,
                user_id=user_id,
                display_name=display_name,
                points=awarded_points
            )

            guild_key = str(message.guild.id)
            user_key = str(user_id)
            user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})

            current_streak = user_data.get("current_streak", 0)
            best_streak = user_data.get("best_streak", 0)
            correct_answers = user_data.get("correct_answers", 0)

            if correct_answers == 1:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "first_ding"
                )
                if msg:
                    achievement_messages.append(msg)

            if answer_index == 0:
                record_top_answer(message.guild.id, user_id, display_name)
                user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})

                if user_data.get("top_answers", 0) >= 10:
                    msg = award_achievement(
                        message.guild.id,
                        user_id,
                        display_name,
                        "top_answer_magnet"
                    )
                    if msg:
                        achievement_messages.append(msg)

                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "big_brain"
                )
                if msg:
                    achievement_messages.append(msg)

            # A steal happens after 3 strikes, so this is a perfect Ice Cold moment.
            msg = award_achievement(
                message.guild.id,
                user_id,
                display_name,
                "ice_cold"
            )
            if msg:
                achievement_messages.append(msg)

            if round_streak >= 3:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "hot_streak"
                )
                if msg:
                    achievement_messages.append(msg)

            if game.player_scores.get(user_id, 0) >= 100:
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "board_boss"
                )
                if msg:
                    achievement_messages.append(msg)

            msg = award_achievement(
                message.guild.id,
                user_id,
                display_name,
                "steal_specialist"
            )
            if msg:
                achievement_messages.append(msg)

        await safe_add_reaction(message, "✅")
        await asyncio.sleep(0.8)

        team_icon = "🔴" if stealing_team == "red" else "🔵"

        correct_intro = random.choice(CORRECT_ANSWER_REACTIONS).format(
            answer=answer.text.upper()
        )

        streak_line = ""

        if current_streak >= 2:
            streak_line = f"\n🔥 **Streak:** `{current_streak}` correct in a row!"

        if best_streak and current_streak == best_streak and current_streak >= 2:
            streak_line += f"\n🏅 **New best streak:** `{best_streak}`!"

        achievement_text = ""

        if achievement_messages:
            achievement_text = "\n\n" + "\n".join(achievement_messages)

        close_match_text = "\n_Accepted as a close match._" if fuzzy_used else ""

        await message.channel.send(
            f"{correct_intro}\n"
            f"{team_icon} **{display_name} steals the board!**\n"
            f"💰 `{board_points}` revealed board points go to their team."
            f"{streak_line}"
            f"{achievement_text}"
            f"{close_match_text}"
        )

        final_embed = create_final_embed(
            game,
            "🚨 The steal was successful!"
        )

        await message.channel.send(embed=final_embed)

        if channel_id in active_games:
            end_active_game(channel_id, game)

        await post_next_round_vote(message.channel, category=game.question.category)
        return

    # ----------------------------
    # FAILED STEAL
    # ----------------------------
    update_question_analytics(game.guild_id, game.question, "wrong_guesses")
    game.wrong_guesses.append(message.content.strip())
    game.round_correct_streaks[user_id] = 0

    achievement_messages = []

    if message.guild:
        record_wrong_lifetime_guess(
            guild_id=message.guild.id,
            user_id=user_id,
            display_name=display_name
        )

        guild_key = str(message.guild.id)
        user_key = str(user_id)
        user_data = SERVER_SCORES.get(guild_key, {}).get(user_key, {})
        wrong_answers = user_data.get("wrong_answers", 0)

        if wrong_answers >= 10:
            msg = award_achievement(
                message.guild.id,
                user_id,
                display_name,
                "survey_victim"
            )
            if msg:
                achievement_messages.append(msg)

    achievement_text = ""

    if achievement_messages:
        achievement_text = "\n\n" + "\n".join(achievement_messages)

    await safe_add_reaction(message, "❌")
    await asyncio.sleep(0.6)

    await message.channel.send(
        f"❌ **Steal failed!** The board survives the attempted robbery.\n"
        f"💥 **{display_name}'s streak has been reset.**"
        f"{achievement_text}"
    )

    final_embed = create_final_embed(
        game,
        "❌ The steal failed. Current scores stay."
    )

    await message.channel.send(embed=final_embed)

    if channel_id in active_games:
        end_active_game(channel_id, game)

    await post_next_round_vote(message.channel, category=game.question.category)

# ----------------------------
# SLASH COMMANDS
# ----------------------------


@bot.tree.command(name="feud_badges", description="Show who has the most Family Fortunes achievements.")
async def feud_badges(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "Achievements only work inside a server.",
            ephemeral=True
        )
        return

    guild_key = str(interaction.guild.id)
    guild_scores = SERVER_SCORES.get(guild_key, {})

    if not guild_scores:
        await interaction.response.send_message(
            "No achievements have been unlocked yet.",
            ephemeral=True
        )
        return

    sorted_players = sorted(
        guild_scores.items(),
        key=lambda item: len(item[1].get("achievements", [])),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(sorted_players[:10], start=1):
        name = data.get("name", f"Player {user_id}")
        achievement_count = len(data.get("achievements", []))

        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = f"**{position}.**"

        lines.append(
            f"{medal} **{name}** — `{achievement_count}` achievements"
        )

    embed = discord.Embed(
        title="🏅 Family Fortunes Badge Board",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="feud_achievements", description="Show your Family Fortunes achievements.")
async def feud_achievements(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "Achievements only work inside a server.",
            ephemeral=True
        )
        return

    guild_key = str(interaction.guild.id)
    user_key = str(interaction.user.id)

    guild_scores = SERVER_SCORES.get(guild_key, {})
    user_data = guild_scores.get(user_key)

    if not user_data:
        await interaction.response.send_message(
            "You have not unlocked any achievements yet.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🏅 Your Family Fortunes Achievements",
        color=discord.Color.gold()
    )

    embed.description = get_achievement_summary(user_data)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="feud_host_toggle", description="Turn idle host chat on or off.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_host_toggle(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    current = get_server_settings(interaction.guild.id)["idle_host_enabled"]
    settings = update_server_setting(interaction.guild.id, "idle_host_enabled", not current)

    status = "enabled" if settings["idle_host_enabled"] else "disabled"

    await interaction.response.send_message(
        f"🎤 Idle host chat is now **{status}**.",
        ephemeral=True
    )


@feud_host_toggle.error
async def feud_host_toggle_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "You need the **Manage Messages** permission to toggle idle host chat.",
        ephemeral=True
    )


@bot.tree.command(name="feud_admin", description="Open host controls for the current round.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_admin(interaction: discord.Interaction):
    if interaction.channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round in this channel.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Host controls are ready.",
        view=FeudAdminView(interaction.channel_id),
        ephemeral=True
    )


@feud_admin.error
async def feud_admin_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "You need the **Manage Messages** permission to use host controls.",
        ephemeral=True
    )


@bot.tree.command(name="feud_reveal", description="Reveal one answer by board number.")
@app_commands.describe(number="The answer number to reveal.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_reveal(interaction: discord.Interaction, number: int):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message("There is no active round in this channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    revealed = await reveal_answer_number(interaction.channel, active_games[channel_id], number)
    await interaction.followup.send("Answer revealed." if revealed else "That answer number cannot be revealed.", ephemeral=True)


@bot.tree.command(name="feud_reveal_all", description="Reveal the full board and end the round.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_reveal_all(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message("There is no active round in this channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    await reveal_all_answers(interaction.channel, active_games[channel_id])
    await interaction.followup.send("Full board revealed.", ephemeral=True)


@bot.tree.command(name="feud_packs", description="Show available question packs.")
async def feud_packs(interaction: discord.Interaction):
    lines = [
        f"**{format_category_name(pack)}** — {', '.join(format_category_name(category) for category in categories)}"
        for pack, categories in QUESTION_PACKS.items()
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="feud_lobby", description="Open a pre-game lobby with teams and category voting.")
@app_commands.describe(mode="Choose a game mode for the lobby.")
@app_commands.autocomplete(mode=mode_autocomplete)
async def feud_lobby(interaction: discord.Interaction, mode: str = "classic"):
    if interaction.channel_id in active_games:
        await interaction.response.send_message("A round is already active in this channel.", ephemeral=True)
        return

    view = LobbyView(interaction.channel_id, mode=mode)
    active_lobbies[interaction.channel_id] = {"view": view}
    await interaction.response.send_message(embed=view.lobby_embed(), view=view)


@bot.tree.command(name="feud_category_vote", description="Start a quick vote for the next round category.")
async def feud_category_vote(interaction: discord.Interaction):
    view = CategoryVoteView(interaction.channel_id)
    embed = discord.Embed(
        title="🗳️ Vote for the Next Category",
        description=view.summary(),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="feud_mini_poll", description="Post a quick between-round survey poll.")
@app_commands.describe(category="Optional category for the mini poll.")
@app_commands.autocomplete(category=category_autocomplete)
async def feud_mini_poll(interaction: discord.Interaction, category: str = "random"):
    question = pick_question(category, guild_id=interaction.guild.id if interaction.guild else None)

    if not question:
        await interaction.response.send_message("No question found for that category.", ephemeral=True)
        return

    view = MiniPollView(question)
    await interaction.response.send_message(embed=view.embed(), view=view)


@bot.tree.command(name="feud_fast_money", description="Start a solo 5-question Fast Money challenge.")
@app_commands.describe(category="Optional category for Fast Money prompts.")
@app_commands.autocomplete(category=category_autocomplete)
async def feud_fast_money(interaction: discord.Interaction, category: str = "random"):
    if not interaction.guild:
        await interaction.response.send_message("Fast Money only works inside a server.", ephemeral=True)
        return

    all_questions = get_questions_for_category(category, guild_id=interaction.guild.id)

    if len(all_questions) < 5:
        await interaction.response.send_message("Not enough questions in that category for Fast Money.", ephemeral=True)
        return

    prompts = random.sample(all_questions, 5)
    fast_money_games[interaction.user.id] = {
        "guild_id": interaction.guild.id,
        "channel_id": interaction.channel_id,
        "questions": prompts,
        "started_at": time.time()
    }
    lines = [
        f"**{index}.** {question.question}"
        for index, question in enumerate(prompts, start=1)
    ]
    await interaction.response.send_message(
        "⚡ **Fast Money started!** Reply within 60 seconds with `/feud_fast_money_submit answers:` "
        "and separate your 5 answers with commas.\n\n" + "\n".join(lines),
        ephemeral=True
    )


@bot.tree.command(name="feud_fast_money_submit", description="Submit your 5 comma-separated Fast Money answers.")
@app_commands.describe(answers="Five answers separated by commas.")
async def feud_fast_money_submit(interaction: discord.Interaction, answers: str):
    game = fast_money_games.get(interaction.user.id)

    if not game:
        await interaction.response.send_message("You do not have an active Fast Money challenge.", ephemeral=True)
        return

    if time.time() - game["started_at"] > 60:
        del fast_money_games[interaction.user.id]
        await interaction.response.send_message("Time is up for that Fast Money challenge.", ephemeral=True)
        return

    submitted = [answer.strip() for answer in answers.split(",") if answer.strip()]

    if len(submitted) != 5:
        await interaction.response.send_message("Submit exactly five comma-separated answers.", ephemeral=True)
        return

    total_points = 0
    lines = []

    for index, (question, guess) in enumerate(zip(game["questions"], submitted), start=1):
        round_game = ChannelGame(
            channel_id=game["channel_id"],
            guild_id=game["guild_id"],
            question=question,
            revealed=[False for _ in question.answers],
            mode="fast_money"
        )
        _, answer, fuzzy_used = find_matching_answer(guess, round_game)

        if answer:
            total_points += answer.points
            marker = "close match" if fuzzy_used else "match"
            lines.append(f"**{index}.** `{guess}` → **{answer.text}** `{answer.points}` pts ({marker})")
        else:
            lines.append(f"**{index}.** `{guess}` → no match")

    add_lifetime_score(game["guild_id"], interaction.user.id, interaction.user.display_name, total_points)
    del fast_money_games[interaction.user.id]
    await interaction.response.send_message(
        f"⚡ **Fast Money total:** `{total_points}` points\n\n" + "\n".join(lines)
    )


@bot.tree.command(name="feud_daily_survey", description="Post or show today's casual survey prompt.")
async def feud_daily_survey(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Daily surveys only work inside a server.", ephemeral=True)
        return

    embed = make_daily_survey_embed(interaction.guild.id)
    get_guild_engagement(interaction.guild.id)["daily_surveys"][today_key()]["posted"] = True
    save_engagement_state(ENGAGEMENT_STATE)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="feud_daily_answer", description="Answer today's casual survey prompt.")
@app_commands.describe(answer="Your answer to today's survey.")
async def feud_daily_answer(interaction: discord.Interaction, answer: str):
    if not interaction.guild:
        await interaction.response.send_message("Daily surveys only work inside a server.", ephemeral=True)
        return

    answer_text = answer.strip()

    if not answer_text:
        await interaction.response.send_message("Give me an answer first.", ephemeral=True)
        return

    guild_data = get_guild_engagement(interaction.guild.id)
    survey = guild_data["daily_surveys"].setdefault(
        today_key(),
        {"prompt": DAILY_SURVEY_PROMPTS[stable_daily_index()], "answers": {}}
    )
    normalized_answer = normalize_text(answer_text).title()
    answers = survey.setdefault("answers", {})

    for existing_answer, user_ids in answers.items():
        if interaction.user.id in user_ids:
            user_ids.remove(interaction.user.id)

    answers.setdefault(normalized_answer, [])

    if interaction.user.id not in answers[normalized_answer]:
        answers[normalized_answer].append(interaction.user.id)

    save_engagement_state(ENGAGEMENT_STATE)
    await interaction.response.send_message(f"Survey answer counted: **{normalized_answer}**.", ephemeral=True)


@bot.tree.command(name="feud_challenge", description="Show this week's Family Fortunes challenge.")
async def feud_challenge(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Weekly challenges only work inside a server.", ephemeral=True)
        return

    name, description, metric, target = current_weekly_challenge()
    user_data = SERVER_SCORES.get(str(interaction.guild.id), {}).get(str(interaction.user.id))

    progress = 0
    if user_data:
        refresh_period_scores(user_data)
        progress = int(user_data.get(metric, 0))

    embed = discord.Embed(
        title=f"🎯 Weekly Challenge: {name}",
        description=description,
        color=discord.Color.orange()
    )
    embed.add_field(name="Your Progress", value=f"`{progress}/{target}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="feud_callout", description="Post a fun between-round leaderboard callout.")
async def feud_callout(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Callouts only work inside a server.", ephemeral=True)
        return

    guild_scores = SERVER_SCORES.get(str(interaction.guild.id), {})

    if not guild_scores:
        await interaction.response.send_message("No scores yet. Start a round and give me something to shout about.", ephemeral=True)
        return

    leaders = sorted(guild_scores.values(), key=lambda data: data.get("weekly_points", 0), reverse=True)
    leader = leaders[0]
    await interaction.response.send_message(
        f"📣 **Between-round callout:** **{leader.get('name', 'Someone')}** leads the week with "
        f"`{leader.get('weekly_points', 0)}` points and `{leader.get('best_streak', 0)}` as their best streak."
    )


@bot.tree.command(name="feud_rivalry", description="Show Red vs Blue or player rivalry stats.")
@app_commands.describe(member="Optional player to compare against you.")
async def feud_rivalry(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    if not interaction.guild:
        await interaction.response.send_message("Rivalries only work inside a server.", ephemeral=True)
        return

    guild_data = get_guild_engagement(interaction.guild.id)

    if member:
        pair_key = "-".join(str(user_id) for user_id in sorted([interaction.user.id, member.id]))
        pair = guild_data["player_rivalries"].get(pair_key, {})
        user_wins = pair.get(str(interaction.user.id), 0)
        member_wins = pair.get(str(member.id), 0)
        draws = pair.get("draws", 0)
        await interaction.response.send_message(
            f"🥊 **Player Rivalry:** {interaction.user.display_name} `{user_wins}` - `{member_wins}` "
            f"{member.display_name} | Draws `{draws}`"
        )
        return

    rivalry = guild_data["team_rivalries"]
    await interaction.response.send_message(
        f"🔴 **Red** `{rivalry.get('red_wins', 0)}` - `{rivalry.get('blue_wins', 0)}` **Blue** 🔵\n"
        f"Draws: `{rivalry.get('draws', 0)}` | Last result: `{format_category_name(rivalry.get('last_winner') or 'none')}`"
    )


@bot.tree.command(name="feud_suggest", description="Suggest a question for moderators to review.")
@app_commands.describe(category="Suggested category.", question="Suggested question.", answers="Comma-separated answers.")
async def feud_suggest(interaction: discord.Interaction, category: str, question: str, answers: str):
    if not interaction.guild:
        await interaction.response.send_message("Suggestions only work inside a server.", ephemeral=True)
        return

    answer_list = [answer.strip() for answer in answers.split(",") if answer.strip()]

    if len(answer_list) < 2:
        await interaction.response.send_message("Please suggest at least two comma-separated answers.", ephemeral=True)
        return

    guild_data = get_guild_engagement(interaction.guild.id)
    guild_data["suggestions"].append({
        "author_id": interaction.user.id,
        "author_name": interaction.user.display_name,
        "category": normalize_category(category),
        "question": question.strip(),
        "answers": answer_list[:8],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    save_engagement_state(ENGAGEMENT_STATE)
    await interaction.response.send_message("Suggestion saved for moderator review.", ephemeral=True)


@bot.tree.command(name="feud_suggestions", description="Review recent suggested questions.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_suggestions(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Suggestions only work inside a server.", ephemeral=True)
        return

    suggestions = get_guild_engagement(interaction.guild.id)["suggestions"][-5:]

    if not suggestions:
        await interaction.response.send_message("No suggestions yet.", ephemeral=True)
        return

    lines = [
        f"**{index}.** `{format_category_name(item['category'])}` {item['question']} "
        f"({', '.join(item['answers'])}) — {item['author_name']}"
        for index, item in enumerate(suggestions, start=1)
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="feud_approve_suggestion", description="Approve a suggested question into this server's custom questions.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(index="Suggestion number from /feud_suggestions.")
async def feud_approve_suggestion(interaction: discord.Interaction, index: int):
    if not interaction.guild:
        await interaction.response.send_message("Suggestions only work inside a server.", ephemeral=True)
        return

    guild_data = get_guild_engagement(interaction.guild.id)
    suggestions = guild_data["suggestions"]

    if index < 1 or index > min(5, len(suggestions)):
        await interaction.response.send_message("Use a suggestion number shown by `/feud_suggestions`.", ephemeral=True)
        return

    suggestion = suggestions[-5:][index - 1]
    default_points = [40, 25, 15, 10, 6, 4, 3, 2]
    answers = [
        FeudAnswer(text=answer, points=default_points[position])
        for position, answer in enumerate(suggestion["answers"][:8])
    ]
    custom_question = FeudQuestion(
        category=suggestion["category"],
        question=suggestion["question"],
        answers=answers,
        pack=f"server_{interaction.guild.id}"
    )

    guild_key = str(interaction.guild.id)
    CUSTOM_QUESTIONS.setdefault(guild_key, []).append(custom_question)
    save_custom_questions(CUSTOM_QUESTIONS)
    suggestions.remove(suggestion)
    save_engagement_state(ENGAGEMENT_STATE)
    await interaction.response.send_message("Suggestion approved and added to this server's question pool.", ephemeral=True)


@bot.tree.command(name="feud_custom_questions", description="List this server's custom questions.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_custom_questions(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Custom questions only work inside a server.", ephemeral=True)
        return

    questions = CUSTOM_QUESTIONS.get(str(interaction.guild.id), [])

    if not questions:
        await interaction.response.send_message("This server has no custom questions yet.", ephemeral=True)
        return

    lines = [
        f"**{index}.** `{format_category_name(question.category)}` {question.question}"
        for index, question in enumerate(questions[-15:], start=max(1, len(questions) - 14))
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="feud_delete_custom", description="Delete a server custom question by number.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_delete_custom(interaction: discord.Interaction, index: int):
    if not interaction.guild:
        await interaction.response.send_message("Custom questions only work inside a server.", ephemeral=True)
        return

    guild_key = str(interaction.guild.id)
    questions = CUSTOM_QUESTIONS.get(guild_key, [])

    if index < 1 or index > len(questions):
        await interaction.response.send_message("That custom question number does not exist.", ephemeral=True)
        return

    removed = questions.pop(index - 1)
    save_custom_questions(CUSTOM_QUESTIONS)
    await interaction.response.send_message(f"Deleted custom question: **{removed.question}**", ephemeral=True)


@bot.tree.command(name="feud_edit_custom", description="Edit a server custom question's category, question text, or difficulty.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_edit_custom(
    interaction: discord.Interaction,
    index: int,
    category: Optional[str] = None,
    question_text: Optional[str] = None,
    difficulty: Optional[str] = None
):
    if not interaction.guild:
        await interaction.response.send_message("Custom questions only work inside a server.", ephemeral=True)
        return

    questions = CUSTOM_QUESTIONS.get(str(interaction.guild.id), [])

    if index < 1 or index > len(questions):
        await interaction.response.send_message("That custom question number does not exist.", ephemeral=True)
        return

    custom_question = questions[index - 1]

    if category:
        custom_question.category = normalize_category(category)
    if question_text:
        custom_question.question = question_text.strip()
    if difficulty:
        normalized_difficulty = normalize_category(difficulty)
        if normalized_difficulty in QUESTION_DIFFICULTIES and normalized_difficulty != "any":
            custom_question.difficulty = normalized_difficulty

    save_custom_questions(CUSTOM_QUESTIONS)
    await interaction.response.send_message("Custom question updated.", ephemeral=True)


@bot.tree.command(name="feud_captain", description="Set yourself or another player as your team's steal captain.")
@app_commands.describe(member="Captain to set. Leave blank to choose yourself.")
async def feud_captain(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message("There is no active round in this channel.", ephemeral=True)
        return

    game = active_games[channel_id]
    target = member or interaction.user
    team = game.player_teams.get(target.id)

    if not team:
        await interaction.response.send_message("That player has not joined a team this round.", ephemeral=True)
        return

    requester_team = game.player_teams.get(interaction.user.id)

    if requester_team != team and not await interaction_has_host_permission(interaction):
        await interaction.response.send_message("Only a teammate or host can set that captain.", ephemeral=True)
        return

    game.captain_by_team[team] = target.id
    save_active_games()
    team_name = "Red Team" if team == "red" else "Blue Team"
    await interaction.response.send_message(f"🎙️ **{target.display_name}** is now captain for **{team_name}**.")


@bot.tree.command(name="feud_settings", description="View or update Family Fortunes server settings.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    setting="Setting to update. Leave blank to view current settings.",
    value="New value for the setting."
)
@app_commands.choices(setting=[
    app_commands.Choice(name="Max Strikes", value="max_strikes"),
    app_commands.Choice(name="Guess Cooldown Seconds", value="guess_cooldown_seconds"),
    app_commands.Choice(name="Round Seconds", value="round_seconds"),
    app_commands.Choice(name="Idle Host Enabled", value="idle_host_enabled"),
    app_commands.Choice(name="Next Round Yes Votes", value="next_round_yes_votes_required"),
    app_commands.Choice(name="Steal Mode", value="steal_mode"),
    app_commands.Choice(name="Minimum Players", value="minimum_players"),
    app_commands.Choice(name="Board Repost Every", value="board_repost_every"),
    app_commands.Choice(name="Host Personality", value="host_personality"),
    app_commands.Choice(name="Daily Prompt Enabled", value="daily_prompt_enabled"),
    app_commands.Choice(name="Daily Prompt Channel", value="daily_prompt_channel_id"),
    app_commands.Choice(name="Game Night Reminder Enabled", value="game_night_reminder_enabled"),
    app_commands.Choice(name="Game Night Channel", value="game_night_channel_id"),
    app_commands.Choice(name="Game Night Weekday", value="game_night_weekday"),
    app_commands.Choice(name="Game Night Hour UTC", value="game_night_hour_utc"),
    app_commands.Choice(name="Game Night Notice Minutes", value="game_night_notice_minutes"),
    app_commands.Choice(name="Quiet Mode", value="quiet_mode")
])
async def feud_settings(
    interaction: discord.Interaction,
    setting: Optional[app_commands.Choice[str]] = None,
    value: Optional[str] = None
):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    if setting and value is not None:
        key = setting.value

        if key in ["idle_host_enabled", "daily_prompt_enabled", "game_night_reminder_enabled", "quiet_mode"]:
            parsed_value = value.lower() in ["true", "yes", "1", "on", "enabled"]
        elif key == "steal_mode":
            parsed_value = normalize_category(value)
            if parsed_value not in STEAL_MODES:
                await interaction.response.send_message("Steal mode must be `any` or `captain`.", ephemeral=True)
                return
        elif key == "host_personality":
            parsed_value = normalize_category(value)
            if parsed_value not in HOST_PERSONALITIES:
                await interaction.response.send_message(
                    f"Host personality must be one of: {', '.join(HOST_PERSONALITIES)}.",
                    ephemeral=True
                )
                return
        elif key in ["daily_prompt_channel_id", "game_night_channel_id"]:
            parsed_value = int(value.replace("<#", "").replace(">", "")) if value else None
        else:
            try:
                parsed_value = int(value)
            except ValueError:
                await interaction.response.send_message("That setting needs a whole number.", ephemeral=True)
                return

        settings = update_server_setting(interaction.guild.id, key, parsed_value)
    else:
        settings = get_server_settings(interaction.guild.id)

    lines = [f"`{key}`: `{value}`" for key, value in settings.items()]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="feud_blacklist_word", description="Add a word to the Family Fortunes guess filter.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_blacklist_word(interaction: discord.Interaction, word: str):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    settings = get_server_settings(interaction.guild.id)
    normalized = normalize_text(word)

    if not normalized:
        await interaction.response.send_message("Give me a word to block.", ephemeral=True)
        return

    if normalized not in settings["blacklisted_words"]:
        settings["blacklisted_words"].append(normalized)
        update_server_setting(interaction.guild.id, "blacklisted_words", settings["blacklisted_words"])

    await interaction.response.send_message(f"`{normalized}` is now blocked for guesses.", ephemeral=True)


@bot.tree.command(name="feud_unblacklist_word", description="Remove a word from the Family Fortunes guess filter.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_unblacklist_word(interaction: discord.Interaction, word: str):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    settings = get_server_settings(interaction.guild.id)
    normalized = normalize_text(word)
    settings["blacklisted_words"] = [
        blocked
        for blocked in settings["blacklisted_words"]
        if blocked != normalized
    ]
    update_server_setting(interaction.guild.id, "blacklisted_words", settings["blacklisted_words"])
    await interaction.response.send_message(f"`{normalized}` removed from the guess filter.", ephemeral=True)


@bot.tree.command(name="feud_pause", description="Pause or unpause Family Fortunes chat handling.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_pause(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    current = get_server_settings(interaction.guild.id)["quiet_mode"]
    settings = update_server_setting(interaction.guild.id, "quiet_mode", not current)
    await interaction.response.send_message(
        f"Family Fortunes quiet mode is now **{'on' if settings['quiet_mode'] else 'off'}**.",
        ephemeral=True
    )


@bot.tree.command(name="feud_add_question", description="Add a custom question for this server.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(
    category="Question category.",
    question="Survey question.",
    answer1="Top answer.",
    points1="Top answer points.",
    answer2="Second answer.",
    points2="Second answer points.",
    answer3="Optional third answer.",
    points3="Optional third answer points.",
    answer4="Optional fourth answer.",
    points4="Optional fourth answer points."
)
async def feud_add_question(
    interaction: discord.Interaction,
    category: str,
    question: str,
    answer1: str,
    points1: int,
    answer2: str,
    points2: int,
    answer3: Optional[str] = None,
    points3: Optional[int] = None,
    answer4: Optional[str] = None,
    points4: Optional[int] = None
):
    if not interaction.guild:
        await interaction.response.send_message("Custom questions can only be added inside a server.", ephemeral=True)
        return

    answer_pairs = [(answer1, points1), (answer2, points2), (answer3, points3), (answer4, points4)]
    answers = [
        FeudAnswer(text=text.strip(), points=int(points))
        for text, points in answer_pairs
        if text and points is not None
    ]

    if len(answers) < 2:
        await interaction.response.send_message("Add at least two answers.", ephemeral=True)
        return

    if any(answer.points <= 0 for answer in answers):
        await interaction.response.send_message("Answer points must be positive.", ephemeral=True)
        return

    custom_question = FeudQuestion(
        category=normalize_category(category),
        question=question.strip(),
        answers=answers,
        pack=f"server_{interaction.guild.id}"
    )

    guild_key = str(interaction.guild.id)
    CUSTOM_QUESTIONS.setdefault(guild_key, []).append(custom_question)
    save_custom_questions(CUSTOM_QUESTIONS)
    await interaction.response.send_message(
        f"Added a custom `{format_category_name(custom_question.category)}` question with `{len(answers)}` answers.",
        ephemeral=True
    )


@bot.tree.command(name="feud_validate_questions", description="Check question data quality.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_validate_questions(interaction: discord.Interaction):
    guild_id = interaction.guild.id if interaction.guild else None
    questions = get_all_questions(guild_id)
    issues = []
    seen_questions = set()

    for index, question in enumerate(questions, start=1):
        normalized_question = (
            question.category,
            normalize_text(question.question),
            tuple(normalize_text(answer.text) for answer in question.answers)
        )

        if normalized_question in seen_questions:
            issues.append(f"{index}: duplicate full question")
        seen_questions.add(normalized_question)

        if len(question.answers) < 2:
            issues.append(f"{index}: fewer than two answers")

        seen_answers = set()
        total_points = 0

        for answer in question.answers:
            normalized_answer = normalize_text(answer.text)
            total_points += answer.points

            if normalized_answer in seen_answers:
                issues.append(f"{index}: duplicate answer `{answer.text}`")
            seen_answers.add(normalized_answer)

            if answer.points <= 0:
                issues.append(f"{index}: non-positive points for `{answer.text}`")

        if total_points > 150:
            issues.append(f"{index}: high point total `{total_points}`")

    if not issues:
        await interaction.response.send_message(f"Checked `{len(questions)}` questions. No issues found.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"Checked `{len(questions)}` questions and found `{len(issues)}` issue(s):\n" + "\n".join(issues[:20]),
        ephemeral=True
    )


@bot.tree.command(name="feud_question_analytics", description="Show question performance and freshness stats.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_question_analytics(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Analytics only work inside a server.", ephemeral=True)
        return

    guild_key = str(interaction.guild.id)
    analytics = ENGAGEMENT_STATE.setdefault("question_analytics", {}).get(guild_key, {})
    recent_count = len(get_recent_question_ids(interaction.guild.id))

    if not analytics:
        await interaction.response.send_message(
            f"No question analytics yet. Recent-question memory currently has `{recent_count}` item(s).",
            ephemeral=True
        )
        return

    most_used = sorted(analytics.values(), key=lambda item: item.get("times_used", 0), reverse=True)[:5]
    skipped = sorted(analytics.values(), key=lambda item: item.get("skips", 0), reverse=True)[:5]
    lines = [f"Recent-question memory: `{recent_count}/{USED_QUESTIONS_LIMIT}`"]
    lines.append("**Most Used**")
    lines.extend(
        f"`{item.get('times_used', 0)}` {item.get('question', 'Unknown')[:80]}"
        for item in most_used
    )
    lines.append("**Most Skipped**")
    lines.extend(
        f"`{item.get('skips', 0)}` {item.get('question', 'Unknown')[:80]}"
        for item in skipped
    )
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="feud_profile", description="Show a richer Family Fortunes player profile.")
async def feud_profile(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    if not interaction.guild:
        await interaction.response.send_message("Profiles only work inside a server.", ephemeral=True)
        return

    target = member or interaction.user
    user_data = SERVER_SCORES.get(str(interaction.guild.id), {}).get(str(target.id))

    if not user_data:
        await interaction.response.send_message("No Family Fortunes profile exists for that player yet.", ephemeral=True)
        return

    refresh_period_scores(user_data)
    total_points = user_data.get("total_points", 0)
    correct = user_data.get("correct_answers", 0)
    wrong = user_data.get("wrong_answers", 0)
    guesses = correct + wrong
    accuracy = round((correct / guesses) * 100) if guesses else 0

    embed = discord.Embed(
        title=f"📊 {target.display_name}'s Family Fortunes Profile",
        color=discord.Color.green()
    )
    embed.add_field(name="Lifetime", value=f"`{total_points}` pts | `{accuracy}%` accuracy", inline=False)
    embed.add_field(name="This Week", value=f"`{user_data.get('weekly_points', 0)}` pts", inline=True)
    embed.add_field(name="Today", value=f"`{user_data.get('daily_points', 0)}` pts", inline=True)
    embed.add_field(name="Best Streak", value=f"`{user_data.get('best_streak', 0)}`", inline=True)
    embed.add_field(name="Rounds", value=f"`{user_data.get('rounds_played', 0)}` played | `{user_data.get('games_won', 0)}` won", inline=False)
    embed.add_field(name="Favorite Team", value=format_category_name(user_data.get("favorite_team") or "none"), inline=True)
    embed.add_field(name="Achievements", value=get_achievement_summary(user_data), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="feud_join", description="Join the current Family Fortunes round on Red or Blue team.")
@app_commands.describe(team="Choose red or blue")
@app_commands.choices(team=[
    app_commands.Choice(name="Red Team", value="red"),
    app_commands.Choice(name="Blue Team", value="blue")
])
async def feud_join(interaction: discord.Interaction, team: app_commands.Choice[str]):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round. Start one with `/feud_start`.",
            ephemeral=True
        )
        return

    game = active_games[channel_id]
    user_id = interaction.user.id
    display_name = interaction.user.display_name
    chosen_team = team.value

    # Prevent players from switching teams after scoring points.
    if user_id in game.player_scores and game.player_scores[user_id] > 0:
        await interaction.response.send_message(
            "You cannot switch teams after scoring points this round.",
            ephemeral=True
        )
        return

    game.player_teams[user_id] = chosen_team
    game.player_names[user_id] = display_name
    game.captain_by_team.setdefault(chosen_team, user_id)

    team_icon = "🔴" if chosen_team == "red" else "🔵"
    team_name = "Red Team" if chosen_team == "red" else "Blue Team"

    await interaction.response.send_message(
        f"{team_icon} **{display_name}** joined **{team_name}**!"
    )

    await update_board_message(interaction.channel, game)
    save_active_games()

@bot.tree.command(name="feud_leave", description="Leave the current Family Fortunes round.")
async def feud_leave(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round in this channel.",
            ephemeral=True
        )
        return

    game = active_games[channel_id]
    user_id = interaction.user.id
    display_name = interaction.user.display_name

    if user_id not in game.player_teams:
        await interaction.response.send_message(
            "You are not currently in this round.",
            ephemeral=True
        )
        return

    game.player_teams.pop(user_id)
    for team, captain_id in list(game.captain_by_team.items()):
        if captain_id == user_id:
            del game.captain_by_team[team]

    await interaction.response.send_message(
        f"👋 **{display_name}** left the round."
    )

    await update_board_message(interaction.channel, game)
    save_active_games()

@bot.tree.command(name="feud_myscore", description="Show your lifetime Family Fortunes score.")
async def feud_myscore(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "Lifetime scores only work inside a server.",
            ephemeral=True
        )
        return

    guild_key = str(interaction.guild.id)
    user_key = str(interaction.user.id)

    guild_scores = SERVER_SCORES.get(guild_key, {})
    user_data = guild_scores.get(user_key)

    if not user_data:
        await interaction.response.send_message(
            "You do not have a lifetime Family Fortunes score yet.",
            ephemeral=True
        )
        return

    total_points = user_data.get("total_points", 0)
    correct_answers = user_data.get("correct_answers", 0)
    wrong_answers = user_data.get("wrong_answers", 0)
    current_streak = user_data.get("current_streak", 0)
    best_streak = user_data.get("best_streak", 0)
    achievements_text = get_achievement_summary(user_data)

    embed = discord.Embed(
        title="📊 Your Family Fortunes Score",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Player",
        value=interaction.user.display_name,
        inline=False
    )

    embed.add_field(
        name="Lifetime Points",
        value=f"`{total_points}`",
        inline=True
    )

    embed.add_field(
        name="Correct Answers",
        value=f"`{correct_answers}`",
        inline=True
    )
    embed.add_field(
        name="Wrong Answers",
        value=f"`{wrong_answers}`",
        inline=True
    )

    embed.add_field(
        name="Current Streak",
        value=f"`{current_streak}`",
        inline=True
    )

    embed.add_field(
        name="Best Streak",
        value=f"`{best_streak}`",
        inline=True
    )
    embed.add_field(
        name="Achievements",
        value=achievements_text,
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="feud_reset_scores", description="Reset this server's lifetime Family Fortunes scores.")
@app_commands.checks.has_permissions(manage_guild=True)
async def feud_reset_scores(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True
        )
        return

    guild_key = str(interaction.guild.id)

    if guild_key in SERVER_SCORES:
        del SERVER_SCORES[guild_key]
        save_server_scores(SERVER_SCORES)

    await interaction.response.send_message(
        "🧹 This server's Family Fortunes lifetime scores have been reset.",
        ephemeral=True
    )


@feud_reset_scores.error
async def feud_reset_scores_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "You need the **Manage Server** permission to reset scores.",
        ephemeral=True
    )

@bot.tree.command(name="feud_leaderboard", description="Show the server Family Fortunes leaderboard.")
@app_commands.describe(period="Choose lifetime, weekly, or daily.")
@app_commands.choices(period=[
    app_commands.Choice(name="Lifetime", value="lifetime"),
    app_commands.Choice(name="Weekly", value="weekly"),
    app_commands.Choice(name="Daily", value="daily")
])
async def feud_leaderboard(interaction: discord.Interaction, period: app_commands.Choice[str] = None):
    if not interaction.guild:
        await interaction.response.send_message(
            "Lifetime scores only work inside a server.",
            ephemeral=True
        )
        return

    embed = create_lifetime_leaderboard_embed(
        guild_id=interaction.guild.id,
        limit=10,
        period=period.value if period else "lifetime"
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="feud_start", description="Start a casual Family Fortunes round.")
@app_commands.describe(category="Choose a question category.")
@app_commands.autocomplete(category=category_autocomplete)
@app_commands.describe(mode="Choose a game mode.")
@app_commands.autocomplete(mode=mode_autocomplete)
@app_commands.describe(difficulty="Choose question difficulty.")
@app_commands.autocomplete(difficulty=difficulty_autocomplete)
async def feud_start(
    interaction: discord.Interaction,
    category: str = "random",
    mode: str = "classic",
    difficulty: str = "any"
):
    channel_id = interaction.channel_id
    category = normalize_category(category)
    mode = normalize_mode(mode)
    difficulty = normalize_category(difficulty)

    if channel_id in active_games:
        await interaction.response.send_message(
            "A Family Fortunes round is already active in this channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    if interaction.channel:
        started = await start_new_round_in_channel(
            interaction.channel,
            category=category,
            mode=mode,
            difficulty=difficulty
        )
    else:
        started = False

    await interaction.followup.send("The board is live." if started else "No board was started.", ephemeral=True)

@bot.tree.command(name="feud_next", description="Start the next Family Fortunes round.")
@app_commands.describe(category="Choose a question category.")
@app_commands.autocomplete(category=category_autocomplete)
@app_commands.describe(mode="Choose a game mode.")
@app_commands.autocomplete(mode=mode_autocomplete)
@app_commands.describe(difficulty="Choose question difficulty.")
@app_commands.autocomplete(difficulty=difficulty_autocomplete)
async def feud_next(
    interaction: discord.Interaction,
    category: str = "random",
    mode: str = "classic",
    difficulty: str = "any"
):
    channel_id = interaction.channel_id
    category = normalize_category(category)
    mode = normalize_mode(mode)
    difficulty = normalize_category(difficulty)

    if channel_id in active_games:
        await interaction.response.send_message(
            "A Family Fortunes round is already active in this channel.",
            ephemeral=True
        )
        return

    # If there is a waiting next-round vote, inherit its category unless user chooses one.
    if category == "random" and channel_id in next_round_votes:
        category = next_round_votes[channel_id].category

    await interaction.response.defer()

    if interaction.channel:
        started = await start_new_round_in_channel(
            interaction.channel,
            starter_text=(
                f"🎬 **Next round started!**\n"
                f"📂 **Category:** `{format_category_name(category)}`\n"
                f"🎮 **Mode:** `{format_category_name(mode)}`\n"
                f"🎚️ **Difficulty:** `{format_category_name(difficulty)}`\n"
                "Join a team with `/feud_join red` or `/feud_join blue`."
            ),
            category=category,
            mode=mode,
            difficulty=difficulty
        )
    else:
        started = False

    await interaction.followup.send("Next round started." if started else "No next round was started.", ephemeral=True)

@bot.tree.command(name="feud_board", description="Show the current Family Fortunes board.")
async def feud_board(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round in this channel.",
            ephemeral=True
        )
        return

    game = active_games[channel_id]
    board_file_path = render_board_image(game)

    if board_file_path:
        await interaction.response.send_message(
            embed=create_board_embed(game, compact=True),
            file=discord.File(board_file_path, filename="family_fortunes_board.png")
        )
    else:
        await interaction.response.send_message(embed=create_board_embed(game))


@bot.tree.command(name="feud_score", description="Show the current Family Fortunes scores.")
async def feud_score(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round in this channel.",
            ephemeral=True
        )
        return

    game = active_games[channel_id]
    embed = create_score_embed(game)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="feud_stop", description="Stop the current Family Fortunes round.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_stop(interaction: discord.Interaction):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round to stop.",
            ephemeral=True
        )
        return

    game = active_games[channel_id]
    final_embed = create_final_embed(
        game,
        "🛑 The host stopped the round."
    )

    end_active_game(channel_id, game)

    await interaction.response.send_message(embed=final_embed)


@feud_stop.error
async def feud_stop_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "You need the **Manage Messages** permission to stop a round.",
        ephemeral=True
    )

@bot.tree.command(name="feud_skip", description="Skip the current question and start a new one.")
@app_commands.describe(category="Choose a new category, or leave blank to keep the current category.")
@app_commands.autocomplete(category=category_autocomplete)
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_skip(
    interaction: discord.Interaction,
    category: Optional[str] = None
):
    channel_id = interaction.channel_id

    if channel_id not in active_games:
        await interaction.response.send_message(
            "There is no active Family Fortunes round to skip.",
            ephemeral=True
        )
        return

    old_game = active_games[channel_id]
    update_question_analytics(old_game.guild_id, old_game.question, "skips")

    if category is None:
        category = old_game.question.category

    category = normalize_category(category)

    question = pick_question(category, guild_id=interaction.guild.id if interaction.guild else None)

    if question is None:
        await interaction.response.send_message(
            f"❌ No questions found for category **{format_category_name(category)}**.",
            ephemeral=True
        )
        return

    game = ChannelGame(
        channel_id=channel_id,
        question=question,
        revealed=[False for _ in question.answers],
        guild_id=interaction.guild.id if interaction.guild else None,
        mode=old_game.mode
    )

    active_games[channel_id] = game

    await interaction.response.send_message(
        f"⏭️ **Question skipped. New round started!**\n"
        f"📂 **Category:** `{format_category_name(question.category)}`\n"
        "Join a team with `/feud_join red` or `/feud_join blue`.",
        view=TeamJoinView(channel_id)
    )

    board_file_path = render_board_image(game)

    if board_file_path:
        board_message = await interaction.channel.send(
            embed=create_board_embed(game, compact=True),
            file=discord.File(board_file_path, filename="family_fortunes_board.png")
        )
    else:
        board_message = await interaction.channel.send(embed=create_board_embed(game))

    game.board_message_id = board_message.id
    save_active_games()


@feud_skip.error
async def feud_skip_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "You need the **Manage Messages** permission to skip a round.",
        ephemeral=True
    )


# ----------------------------
# RUN BOT
# ----------------------------

bot.run(TOKEN)
