import os
import json
import random
import asyncio
import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


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
MAX_STRIKES = 3
FUZZY_MATCH_THRESHOLD = 0.82
SCORES_FILE = "server_scores.json"
GUESS_COOLDOWN_SECONDS = 30
IDLE_HOST_ENABLED = True
IDLE_HOST_COOLDOWN_SECONDS = 45
IDLE_HOST_RANDOM_CHANCE = 0.08
HOST_NAMES = ["steve", "richard"]
DIRECT_HOST_COOLDOWN_SECONDS = 8
NEXT_ROUND_YES_VOTES_REQUIRED = 1

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
    "random_weird"
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


@dataclass
class ChannelGame:
    channel_id: int
    question: FeudQuestion
    revealed: List[bool]
    strikes: int = 0
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

def load_questions() -> List[FeudQuestion]:
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        raw_questions = json.load(file)

    questions: List[FeudQuestion] = []

    for item in raw_questions:
        answers = [
            FeudAnswer(
                text=answer["text"],
                points=int(answer["points"]),
                aliases=answer.get("aliases", [])
            )
            for answer in item["answers"]
        ]

        questions.append(
            FeudQuestion(
                question=item["question"],
                answers=answers,
                category=normalize_category(item.get("category", "general"))
            )
        )

    if not questions:
        raise RuntimeError("No questions found in questions.json.")

    return questions

def load_server_scores() -> Dict[str, Dict[str, dict]]:
    if not os.path.exists(SCORES_FILE):
        return {}

    with open(SCORES_FILE, "r", encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return {}

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: {SCORES_FILE} is invalid. Starting with empty scores.")
        return {}


def save_server_scores(scores: Dict[str, Dict[str, dict]]) -> None:
    with open(SCORES_FILE, "w", encoding="utf-8") as file:
        json.dump(scores, file, indent=2, ensure_ascii=False)


SERVER_SCORES = load_server_scores()

QUESTIONS = load_questions()


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def get_questions_for_category(category: str) -> List[FeudQuestion]:
    category = normalize_category(category)

    if category == "random":
        return QUESTIONS

    return [
        question
        for question in QUESTIONS
        if normalize_category(question.category) == category
    ]


def pick_question(category: str = "random") -> Optional[FeudQuestion]:
    matching_questions = get_questions_for_category(category)

    if not matching_questions:
        return None

    return random.choice(matching_questions)


def format_category_name(category: str) -> str:
    category = normalize_category(category)

    if category == "random":
        return "Random"

    return category.replace("_", " ").title()


async def category_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    current = normalize_category(current)

    available_categories = sorted({
        normalize_category(question.category)
        for question in QUESTIONS
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

async def start_new_round_in_channel(
    channel: discord.abc.Messageable,
    starter_text: Optional[str] = None,
    category: str = "random"
):
    channel_id = channel.id
    category = normalize_category(category)

    if channel_id in active_games:
        await channel.send("A Family Fortunes round is already active in this channel.")
        return

    # Clear any old next-round vote for this channel.
    if channel_id in next_round_votes:
        del next_round_votes[channel_id]

    question = pick_question(category)

    if question is None:
        await channel.send(
            f"❌ No questions found for category **{format_category_name(category)}**.\n"
            "Try `/feud_start category:random` or add questions with that category to `questions.json`."
        )
        return

    game = ChannelGame(
        channel_id=channel_id,
        question=question,
        revealed=[False for _ in question.answers]
    )

    active_games[channel_id] = game

    category_text = format_category_name(question.category)

    if starter_text:
        await channel.send(starter_text)
    else:
        await channel.send(
            f"🎬 **New Family Fortunes round started!**\n"
            f"📂 **Category:** `{category_text}`\n"
            "Join a team with `/feud_join red` or `/feud_join blue`.\n"
            "Only joined players can guess, so normal chat will not count as strikes."
        )

    board_message = await channel.send(embed=create_board_embed(game))
    game.board_message_id = board_message.id


async def post_next_round_vote(
    channel: discord.abc.Messageable,
    category: str = "random"
):
    channel_id = channel.id
    category = normalize_category(category)

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
            "You can also use `/feud_next` to start the next round."
        ),
        color=discord.Color.green()
    )

    vote_message = await channel.send(embed=embed)

    await vote_message.add_reaction("✅")
    await vote_message.add_reaction("🛑")

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

def get_idle_host_response(message_content: str) -> Optional[str]:
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
        return random.choice(IDLE_HOST_GENERIC_RESPONSES)

    return None

async def maybe_idle_host_comment(message: discord.Message):
    if not IDLE_HOST_ENABLED:
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

    response = get_idle_host_response(message.content)

    if not response:
        return

    last_idle_host_comment[channel_id] = now

    await message.channel.send(response)

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
    limit: int = 10
) -> discord.Embed:
    guild_key = str(guild_id)
    guild_scores = SERVER_SCORES.get(guild_key, {})

    embed = discord.Embed(
        title="🏆 Family Fortunes Server Leaderboard",
        color=discord.Color.purple()
    )

    if not guild_scores:
        embed.description = "No lifetime scores recorded for this server yet."
        return embed

    sorted_scores = sorted(
        guild_scores.items(),
        key=lambda item: item[1].get("total_points", 0),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(sorted_scores[:limit], start=1):
        name = data.get("name", f"Player {user_id}")
        total_points = data.get("total_points", 0)
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
    embed.set_footer(text="Scores are tracked per server.")

    return embed

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
        SERVER_SCORES[guild_key][user_key] = {
            "name": display_name,
            "total_points": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "current_streak": 0,
            "best_streak": 0,
            "rounds_played": 0,
            "achievements": []
        }

    user_data = SERVER_SCORES[guild_key][user_key]

    # Backwards compatibility for old server_scores.json files
    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)
    user_data.setdefault("achievements", [])

    user_data["name"] = display_name
    user_data["total_points"] += points
    user_data["correct_answers"] += 1

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
        SERVER_SCORES[guild_key][user_key] = {
            "name": display_name,
            "total_points": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "current_streak": 0,
            "best_streak": 0,
            "rounds_played": 0
        }

    user_data = SERVER_SCORES[guild_key][user_key]

    # Backwards compatibility for old server_scores.json files
    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)

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
        SERVER_SCORES[guild_key][user_key] = {
            "name": display_name,
            "total_points": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "current_streak": 0,
            "best_streak": 0,
            "rounds_played": 0,
            "achievements": []
        }

    user_data = SERVER_SCORES[guild_key][user_key]

    user_data.setdefault("wrong_answers", 0)
    user_data.setdefault("current_streak", 0)
    user_data.setdefault("best_streak", 0)
    user_data.setdefault("rounds_played", 0)
    user_data.setdefault("achievements", [])

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


def answer_terms(answer: FeudAnswer) -> List[str]:
    terms = [answer.text] + answer.aliases
    return [normalize_text(term) for term in terms]


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

        # Slightly flexible check
        for term in terms:
            similarity = difflib.SequenceMatcher(None, cleaned_guess, term).ratio()

            if similarity >= FUZZY_MATCH_THRESHOLD:
                return index, answer, True

    return None, None, False


def all_answers_revealed(game: ChannelGame) -> bool:
    return all(game.revealed)


def create_board_embed(game: ChannelGame, title: str = "🎤 Family Fortunes") -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=(
            f"📂 **Category:** `{format_category_name(game.question.category)}`\n\n"
            f"**{game.question.question}**"
        ),
        color=discord.Color.gold()
    )

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

    strike_text = "❌" * game.strikes
    empty_text = "⬛" * (MAX_STRIKES - game.strikes)

    embed.add_field(
        name="Strikes",
        value=f"{strike_text}{empty_text} `{game.strikes}/{MAX_STRIKES}`",
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
        text=f"Join with /feud_join red or /feud_join blue. Players can guess once every {GUESS_COOLDOWN_SECONDS} seconds."
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

last_idle_host_comment: Dict[int, float] = {}
last_direct_host_comment: Dict[int, float] = {}

# ----------------------------
# BOT EVENTS
# ----------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}.")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Failed to sync commands: {error}")

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

        if len(vote.yes_votes) >= NEXT_ROUND_YES_VOTES_REQUIRED:
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

    guess = normalize_text(message.content)

    if not guess:
        return

    now = time.time()
    last_guess_time = game.last_guess_times.get(user_id, 0)
    seconds_since_last_guess = now - last_guess_time

    if seconds_since_last_guess < GUESS_COOLDOWN_SECONDS:
        remaining = int(GUESS_COOLDOWN_SECONDS - seconds_since_last_guess)
        await message.add_reaction("⏳")

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
        await message.add_reaction("🔁")
        return

    game.used_guesses.append(guess)
    game.guesses_since_board += 1

    answer_index, answer, fuzzy_used = find_matching_answer(guess, game)

    if answer is not None and answer_index is not None:
        game.revealed[answer_index] = True

        team = game.player_teams.get(user_id)

        game.player_scores[user_id] = game.player_scores.get(user_id, 0) + answer.points
        game.player_names[user_id] = display_name

        if team in game.team_scores:
            game.team_scores[team] += answer.points

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
                points=answer.points
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
                msg = award_achievement(
                    message.guild.id,
                    user_id,
                    display_name,
                    "big_brain"
                )
                if msg:
                    achievement_messages.append(msg)

            # 🧊 Ice Cold — correct after two strikes
            if game.strikes >= 2:
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
        await message.add_reaction("✅")

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
                f"{team_icon} `+{answer.points}` points to **{display_name}** and their team."
                f"{streak_line}"
                f"{achievement_text}\n"
                f"_Accepted as a close match._"
            )
        else:
            response_text = (
                f"{correct_intro}\n"
                f"{team_icon} `+{answer.points}` points to **{display_name}** and their team."
                f"{streak_line}"
                f"{achievement_text}"
            )
        await message.channel.send(response_text)

        await update_board_message(message.channel, game)

        if all_answers_revealed(game):
            final_embed = create_final_embed(
                game,
                "✅ Every answer was found!"
            )
            await message.channel.send(embed=final_embed)
            del active_games[channel_id]
            await post_next_round_vote(message.channel, category=game.question.category)

        return

    # Wrong answer
    game.strikes += 1
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

    await message.add_reaction("❌")
    await message.channel.send(
        f"{wrong_text} Strike `{game.strikes}/{MAX_STRIKES}`\n"
        f"💥 **{display_name}'s streak has been reset.**"
        f"{achievement_text}"
    )
    await update_board_message(message.channel, game)

    if game.strikes >= MAX_STRIKES:
        stealing_team = get_lower_scoring_team(game)

        # If the scores are tied, there is no lower-scoring team to steal.
        if stealing_team is None:
            final_embed = create_final_embed(
                game,
                "❌❌❌ Three strikes! Scores are tied, so there is no steal chance."
            )
            await message.channel.send(embed=final_embed)
            del active_games[channel_id]
            await post_next_round_vote(message.channel, category=game.question.category)
            return

        # If the lower-scoring team has nobody in it, end the round normally.
        stealing_players = [
            user_id
            for user_id, team in game.player_teams.items()
            if team == stealing_team
        ]

        if not stealing_players:
            final_embed = create_final_embed(
                game,
                "❌❌❌ Three strikes! No players are available on the losing team to steal."
            )
            await message.channel.send(embed=final_embed)
            del active_games[channel_id]
            await post_next_round_vote(message.channel, category=game.question.category)
            return

        game.pending_steal = True
        game.stealing_team = stealing_team

        steal_embed = create_steal_embed(game)

        team_text = "🔴 Red Team" if stealing_team == "red" else "🔵 Blue Team"

        await message.channel.send(
            f"🚨 **Three strikes!** {team_text} gets one chance to **steal the board**!"
        )

        await message.channel.send(embed=steal_embed)


async def update_board_message(
    channel: discord.abc.Messageable,
    game: ChannelGame,
    force_new: bool = False
):
    embed = create_board_embed(game)

    # Re-post the board every 4 guesses so it stays visible in chat.
    if force_new or game.guesses_since_board >= 4:
        new_message = await channel.send(embed=embed)
        game.board_message_id = new_message.id
        game.guesses_since_board = 0
        return

    # Otherwise, just edit the latest board message.
    if game.board_message_id:
        try:
            old_message = await channel.fetch_message(game.board_message_id)
            await old_message.edit(embed=embed)
            return
        except Exception:
            pass

    # Fallback if the old board cannot be edited/found.
    new_message = await channel.send(embed=embed)
    game.board_message_id = new_message.id
    game.guesses_since_board = 0

async def handle_steal_guess(message: discord.Message, game: ChannelGame):
    channel_id = message.channel.id
    user_id = message.author.id
    display_name = message.author.display_name
    player_team = game.player_teams.get(user_id)

    if not game.pending_steal or not game.stealing_team:
        return

    if player_team != game.stealing_team:
        await message.add_reaction("⛔")

        try:
            team_name = "Red Team" if game.stealing_team == "red" else "Blue Team"
            await message.channel.send(
                f"⛔ Only **{team_name}** can make the steal guess.",
                delete_after=6
            )
        except discord.Forbidden:
            pass

        return

    guess = normalize_text(message.content)

    if not guess:
        return

    game.used_guesses.append(guess)

    answer_index, answer, fuzzy_used = find_matching_answer(guess, game)

    # ----------------------------
    # SUCCESSFUL STEAL
    # ----------------------------
    if answer is not None and answer_index is not None:
        game.revealed[answer_index] = True

        stealing_team = game.stealing_team
        defending_team = get_other_team(stealing_team)

        board_points = get_revealed_board_points(game)

        # The steal team takes the revealed board pot.
        game.team_scores[stealing_team] = board_points
        game.team_scores[defending_team] = 0

        game.player_scores[user_id] = game.player_scores.get(user_id, 0) + answer.points
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
                points=answer.points
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

        await message.add_reaction("✅")

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
            del active_games[channel_id]

        await post_next_round_vote(message.channel, category=game.question.category)
        return

    # ----------------------------
    # FAILED STEAL
    # ----------------------------
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

    await message.add_reaction("❌")

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
        del active_games[channel_id]

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
    global IDLE_HOST_ENABLED

    IDLE_HOST_ENABLED = not IDLE_HOST_ENABLED

    status = "enabled" if IDLE_HOST_ENABLED else "disabled"

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

    team_icon = "🔴" if chosen_team == "red" else "🔵"
    team_name = "Red Team" if chosen_team == "red" else "Blue Team"

    await interaction.response.send_message(
        f"{team_icon} **{display_name}** joined **{team_name}**!"
    )

    await update_board_message(interaction.channel, game)

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

    await interaction.response.send_message(
        f"👋 **{display_name}** left the round."
    )

    await update_board_message(interaction.channel, game)

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

@bot.tree.command(name="feud_leaderboard", description="Show the server lifetime Family Fortunes leaderboard.")
async def feud_leaderboard(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "Lifetime scores only work inside a server.",
            ephemeral=True
        )
        return

    embed = create_lifetime_leaderboard_embed(
        guild_id=interaction.guild.id,
        limit=10
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="feud_start", description="Start a casual Family Fortunes round.")
@app_commands.describe(category="Choose a question category.")
@app_commands.autocomplete(category=category_autocomplete)
async def feud_start(
    interaction: discord.Interaction,
    category: str = "random"
):
    channel_id = interaction.channel_id
    category = normalize_category(category)

    if channel_id in active_games:
        await interaction.response.send_message(
            "A Family Fortunes round is already active in this channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    if interaction.channel:
        await start_new_round_in_channel(
            interaction.channel,
            category=category
        )

    await interaction.followup.send(
        "The board is live.",
        ephemeral=True
    )

@bot.tree.command(name="feud_next", description="Start the next Family Fortunes round.")
@app_commands.describe(category="Choose a question category.")
@app_commands.autocomplete(category=category_autocomplete)
async def feud_next(
    interaction: discord.Interaction,
    category: str = "random"
):
    channel_id = interaction.channel_id
    category = normalize_category(category)

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
        await start_new_round_in_channel(
            interaction.channel,
            starter_text=(
                f"🎬 **Next round started!**\n"
                f"📂 **Category:** `{format_category_name(category)}`\n"
                "Join a team with `/feud_join red` or `/feud_join blue`."
            ),
            category=category
        )

    await interaction.followup.send(
        "Next round started.",
        ephemeral=True
    )

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
    embed = create_board_embed(game)

    await interaction.response.send_message(embed=embed)


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

    del active_games[channel_id]

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

    if category is None:
        category = old_game.question.category

    category = normalize_category(category)

    question = pick_question(category)

    if question is None:
        await interaction.response.send_message(
            f"❌ No questions found for category **{format_category_name(category)}**.",
            ephemeral=True
        )
        return

    game = ChannelGame(
        channel_id=channel_id,
        question=question,
        revealed=[False for _ in question.answers]
    )

    active_games[channel_id] = game

    await interaction.response.send_message(
        f"⏭️ **Question skipped. New round started!**\n"
        f"📂 **Category:** `{format_category_name(question.category)}`\n"
        "Join a team with `/feud_join red` or `/feud_join blue`."
    )

    board_message = await interaction.channel.send(embed=create_board_embed(game))
    game.board_message_id = board_message.id


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