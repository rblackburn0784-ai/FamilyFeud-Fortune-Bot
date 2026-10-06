from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "main.py"
BACKUP_PATH = ROOT / "main.py.v1_4_4_question_admin_backup"
MARKER = "# ----------------------------\n# V1.4.4 QUESTION ADMIN UI\n# ----------------------------"

PICKER_OLD = """    if not matching_questions:\n        return None\n\n    recent_ids = set(get_recent_question_ids(guild_id))\n"""

PICKER_NEW = """    if not matching_questions:\n        return None\n\n    disabled_ids = get_disabled_question_ids(guild_id) if "get_disabled_question_ids" in globals() else set()\n    if disabled_ids:\n        enabled_questions = [\n            question\n            for question in matching_questions\n            if question_id(question) not in disabled_ids\n        ]\n        matching_questions = enabled_questions or matching_questions\n\n    recent_ids = set(get_recent_question_ids(guild_id))\n"""

QUESTION_ADMIN_CODE = r'''
# ----------------------------
# V1.4.4 QUESTION ADMIN UI
# ----------------------------

QUESTION_ADMIN_STATE_KEY = "question_admin"
QUESTION_REVIEW_PAGE_SIZE = 1
SURVEY_OPENERS = (
    "name ",
    "name something",
    "name someone",
    "name a ",
    "name an ",
    "tell me ",
    "give me ",
    "what is something",
    "what's something",
    "what are things",
    "what are some",
)


def get_question_admin_state(guild_id: Optional[int]) -> dict:
    guild_key = str(guild_id or "global")
    ENGAGEMENT_STATE.setdefault(QUESTION_ADMIN_STATE_KEY, {})
    state = ENGAGEMENT_STATE[QUESTION_ADMIN_STATE_KEY].setdefault(guild_key, {})
    state.setdefault("approved", [])
    state.setdefault("flagged", [])
    state.setdefault("edit_needed", [])
    state.setdefault("disabled", [])
    state.setdefault("review_notes", {})
    return state


def get_disabled_question_ids(guild_id: Optional[int]) -> set:
    state = get_question_admin_state(guild_id)
    global_state = get_question_admin_state(None)
    return set(global_state.get("disabled", [])) | set(state.get("disabled", []))


def set_question_review_status(guild_id: Optional[int], question: FeudQuestion, status: str, note: str = "") -> None:
    state = get_question_admin_state(guild_id)
    qid = question_id(question)

    for bucket in ["approved", "flagged", "edit_needed"]:
        if qid in state[bucket]:
            state[bucket].remove(qid)

    if status in ["approved", "flagged", "edit_needed"] and qid not in state[status]:
        state[status].append(qid)

    if note:
        state.setdefault("review_notes", {})[qid] = note

    save_engagement_state(ENGAGEMENT_STATE)


def disable_question_for_guild(guild_id: Optional[int], question: FeudQuestion) -> None:
    state = get_question_admin_state(guild_id)
    qid = question_id(question)
    if qid not in state["disabled"]:
        state["disabled"].append(qid)
    save_engagement_state(ENGAGEMENT_STATE)


def enable_question_for_guild(guild_id: Optional[int], qid: str) -> None:
    state = get_question_admin_state(guild_id)
    state["disabled"] = [item for item in state.get("disabled", []) if item != qid]
    save_engagement_state(ENGAGEMENT_STATE)


def question_quality_score(question: FeudQuestion) -> Tuple[int, List[str]]:
    score = 100
    notes = []
    answer_count = len(question.answers)

    if answer_count < 4:
        score -= 20
        notes.append("few answers")
    elif answer_count < 6:
        score -= 8
        notes.append("could use more answers")

    points = [answer.points for answer in question.answers]
    if points != sorted(points, reverse=True):
        score -= 20
        notes.append("points not descending")

    category = normalize_category(question.category)
    if category not in FEUD_CATEGORIES:
        score -= 15
        notes.append("unknown category")

    alias_count = sum(1 for answer in question.answers if answer.aliases)
    if answer_count and alias_count < max(1, answer_count // 3):
        score -= 10
        notes.append("low alias coverage")

    qnorm = normalize_text(question.question)
    if not qnorm.startswith(SURVEY_OPENERS):
        score -= 10
        notes.append("not classic survey phrasing")

    duplicate_answers = []
    seen_answers = set()
    for answer in question.answers:
        normalized = normalize_text(answer.text)
        if normalized in seen_answers:
            duplicate_answers.append(answer.text)
        seen_answers.add(normalized)

    if duplicate_answers:
        score -= 25
        notes.append("duplicate answers")

    return max(0, min(100, score)), notes or ["looks good"]


def alias_cleanup_for_question(question: FeudQuestion, apply: bool = False) -> Tuple[int, int]:
    duplicate_aliases = 0
    self_aliases = 0

    for answer in question.answers:
        answer_norm = normalize_text(answer.text)
        cleaned_aliases = []
        seen_aliases = set()

        for alias in answer.aliases:
            alias_norm = normalize_text(alias)
            if not alias_norm:
                continue
            if alias_norm == answer_norm:
                self_aliases += 1
                continue
            if alias_norm in seen_aliases:
                duplicate_aliases += 1
                continue
            seen_aliases.add(alias_norm)
            cleaned_aliases.append(alias)

        if apply:
            answer.aliases = cleaned_aliases

    return duplicate_aliases, self_aliases


def alias_cleanup_summary(questions: List[FeudQuestion], apply: bool = False) -> dict:
    duplicate_aliases = 0
    self_aliases = 0

    for question in questions:
        duplicates, self_refs = alias_cleanup_for_question(question, apply=apply)
        duplicate_aliases += duplicates
        self_aliases += self_refs

    return {
        "duplicate_aliases": duplicate_aliases,
        "self_aliases": self_aliases,
        "total": duplicate_aliases + self_aliases,
    }


def get_reviewable_questions(guild_id: Optional[int]) -> List[FeudQuestion]:
    disabled_ids = get_disabled_question_ids(guild_id)
    questions = [
        question
        for question in get_all_questions(guild_id)
        if question_id(question) not in disabled_ids
    ]
    return sorted(questions, key=lambda question: question_quality_score(question)[0])


def find_question_by_search(guild_id: Optional[int], search: str) -> Optional[FeudQuestion]:
    needle = normalize_text(search)
    if not needle:
        return None

    for question in get_all_questions(guild_id):
        haystack = normalize_text(f"{question.category} {question.question} " + " ".join(answer.text for answer in question.answers))
        if needle in haystack:
            return question

    return None


def make_question_review_embed(question: FeudQuestion, index: int, total: int, guild_id: Optional[int]) -> discord.Embed:
    score, notes = question_quality_score(question)
    qid = question_id(question)
    state = get_question_admin_state(guild_id)
    status = "Unreviewed"

    for bucket, label in [
        ("approved", "Approved"),
        ("flagged", "Flagged"),
        ("edit_needed", "Edit Needed"),
        ("disabled", "Disabled"),
    ]:
        if qid in state.get(bucket, []):
            status = label
            break

    if score >= 85:
        color = discord.Color.green()
    elif score >= 65:
        color = discord.Color.gold()
    else:
        color = discord.Color.orange()

    embed = discord.Embed(
        title="Question Review",
        description=f"**{question.question}**",
        color=color,
    )
    embed.add_field(name="Category", value=f"`{format_category_name(question.category)}`", inline=True)
    embed.add_field(name="Difficulty", value=f"`{format_category_name(question.difficulty)}`", inline=True)
    embed.add_field(name="Quality", value=f"`{score}/100` — {', '.join(notes)}", inline=False)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Position", value=f"`{index + 1}/{total}`", inline=True)

    answer_lines = []
    for answer_index, answer in enumerate(question.answers, start=1):
        alias_hint = f" · aliases `{len(answer.aliases)}`" if answer.aliases else ""
        answer_lines.append(f"**{answer_index}.** {answer.text} — `{answer.points}`{alias_hint}")
    embed.add_field(name="Answers", value="\n".join(answer_lines[:8]), inline=False)
    embed.set_footer(text=f"Question ID: {qid[:80]}")
    return embed


def make_question_report_embed(guild_id: Optional[int]) -> discord.Embed:
    questions = get_all_questions(guild_id)
    categories = Counter(normalize_category(question.category) for question in questions)
    state = get_question_admin_state(guild_id)
    cleanup = alias_cleanup_summary(questions, apply=False)
    disabled = len(state.get("disabled", []))
    flagged = len(state.get("flagged", []))
    edit_needed = len(state.get("edit_needed", []))
    approved = len(state.get("approved", []))
    scores = [question_quality_score(question)[0] for question in questions]
    average_score = round(sum(scores) / len(scores)) if scores else 0
    low_score = sum(1 for score in scores if score < 65)

    embed = discord.Embed(
        title="Question Report",
        description="Question-pack health and review queue summary.",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Total Questions", value=f"`{len(questions)}`", inline=True)
    embed.add_field(name="Categories", value=f"`{len(categories)}`", inline=True)
    embed.add_field(name="Average Quality", value=f"`{average_score}/100`", inline=True)
    embed.add_field(
        name="Review State",
        value=(
            f"Approved: `{approved}`\n"
            f"Flagged: `{flagged}`\n"
            f"Edit needed: `{edit_needed}`\n"
            f"Disabled: `{disabled}`\n"
            f"Low quality score: `{low_score}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="Alias Cleanup",
        value=(
            f"Duplicate aliases: `{cleanup['duplicate_aliases']}`\n"
            f"Aliases duplicating answer text: `{cleanup['self_aliases']}`\n"
            f"Total cleanup candidates: `{cleanup['total']}`"
        ),
        inline=True,
    )
    common = categories.most_common(10)
    embed.add_field(
        name="Most Common Categories",
        value="\n".join(f"`{format_category_name(category)}` — `{count}`" for category, count in common) or "None",
        inline=False,
    )
    return embed


def make_category_list_embed(guild_id: Optional[int]) -> discord.Embed:
    questions = get_all_questions(guild_id)
    categories = Counter(normalize_category(question.category) for question in questions)
    embed = discord.Embed(
        title="Question Categories",
        description=f"`{len(categories)}` categories across `{len(questions)}` questions.",
        color=discord.Color.green(),
    )
    lines = [
        f"**{format_category_name(category)}** — `{count}`"
        for category, count in sorted(categories.items(), key=lambda item: item[0])
    ]
    chunks = [lines[index:index + 20] for index in range(0, len(lines), 20)]
    for chunk_index, chunk in enumerate(chunks[:3], start=1):
        embed.add_field(name=f"Categories {chunk_index}", value="\n".join(chunk), inline=True)
    return embed


def make_category_preview_embed(guild_id: Optional[int], category: str, limit: int = 5) -> discord.Embed:
    category = normalize_category(category)
    questions = get_questions_for_category(category, guild_id)
    disabled_ids = get_disabled_question_ids(guild_id)
    enabled_count = sum(1 for question in questions if question_id(question) not in disabled_ids)
    sample = random.sample(questions, k=min(limit, len(questions))) if questions else []
    embed = discord.Embed(
        title=f"Category Preview: {format_category_name(category)}",
        description=f"Total questions: `{len(questions)}` | Enabled: `{enabled_count}`",
        color=discord.Color.gold(),
    )

    if not sample:
        embed.add_field(name="Preview", value="No questions found for that category.", inline=False)
        return embed

    for index, question in enumerate(sample, start=1):
        score, notes = question_quality_score(question)
        top_answers = ", ".join(answer.text for answer in question.answers[:4])
        embed.add_field(
            name=f"{index}. {question.question[:90]}",
            value=f"Quality `{score}/100` · {', '.join(notes[:2])}\nTop answers: {top_answers}",
            inline=False,
        )
    return embed


class QuestionReviewView(discord.ui.View):
    def __init__(self, guild_id: Optional[int], start_index: int = 0):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.index = max(0, start_index)
        self.questions = get_reviewable_questions(guild_id)

    def current_question(self) -> Optional[FeudQuestion]:
        if not self.questions:
            return None
        self.index = max(0, min(self.index, len(self.questions) - 1))
        return self.questions[self.index]

    async def ensure_host(self, interaction: discord.Interaction) -> bool:
        if await interaction_has_host_permission(interaction):
            return True
        await interaction.response.send_message("Question review needs Manage Messages.", ephemeral=True)
        return False

    async def refresh(self, interaction: discord.Interaction) -> None:
        question = self.current_question()
        if not question:
            await interaction.response.edit_message(content="No questions available for review.", embed=None, view=None)
            return
        await interaction.response.edit_message(embed=make_question_review_embed(question, self.index, len(self.questions), self.guild_id), view=self)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, row=0)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        question = self.current_question()
        if question:
            set_question_review_status(self.guild_id, question, "approved")
            self.index += 1
        await self.refresh(interaction)

    @discord.ui.button(label="Flag", style=discord.ButtonStyle.danger, row=0)
    async def flag_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        question = self.current_question()
        if question:
            set_question_review_status(self.guild_id, question, "flagged")
            self.index += 1
        await self.refresh(interaction)

    @discord.ui.button(label="Edit Needed", style=discord.ButtonStyle.secondary, row=0)
    async def edit_needed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        question = self.current_question()
        if question:
            set_question_review_status(self.guild_id, question, "edit_needed")
            self.index += 1
        await self.refresh(interaction)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=1)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        self.index += 1
        await self.refresh(interaction)

    @discord.ui.button(label="Disable Question", style=discord.ButtonStyle.danger, row=1)
    async def disable_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        question = self.current_question()
        if question:
            disable_question_for_guild(self.guild_id, question)
            self.questions = get_reviewable_questions(self.guild_id)
        await self.refresh(interaction)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=2)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        self.index -= 1
        await self.refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=2)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_host(interaction):
            return
        self.index += 1
        await self.refresh(interaction)


@bot.tree.command(name="feud_question_review", description="Review questions one at a time with admin buttons.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_question_review(interaction: discord.Interaction):
    guild_id = interaction.guild.id if interaction.guild else None
    view = QuestionReviewView(guild_id)
    question = view.current_question()
    if not question:
        await interaction.response.send_message("No questions available for review.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=make_question_review_embed(question, view.index, len(view.questions), guild_id),
        view=view,
        ephemeral=True,
    )


@feud_question_review.error
async def feud_question_review_error(interaction: discord.Interaction, error):
    await interaction.response.send_message("You need Manage Messages to review questions.", ephemeral=True)


@bot.tree.command(name="feud_question_report", description="Show question-pack quality and review stats.")
@app_commands.checks.has_permissions(manage_messages=True)
async def feud_question_report(interaction: discord.Interaction):
    guild_id = interaction.guild.id if interaction.guild else None
    await interaction.response.send_message(embed=make_question_report_embed(guild_id), ephemeral=True)


@bot.tree.command(name="feud_category_list", description="List question categories and counts.")
async def feud_category_list(interaction: discord.Interaction):
    guild_id = interaction.guild.id if interaction.guild else None
    await interaction.response.send_message(embed=make_category_list_embed(guild_id), ephemeral=True)


@bot.tree.command(name="feud_category_preview", description="Preview questions from a category without starting a round.")
@app_commands.describe(category="Category to preview.")
@app_commands.autocomplete(category=category_autocomplete)
async def feud_category_preview(interaction: discord.Interaction, category: str):
    guild_id = interaction.guild.id if interaction.guild else None
    await interaction.response.send_message(embed=make_category_preview_embed(guild_id, category), ephemeral=True)


@bot.tree.command(name="feud_disable_question", description="Disable a question by searching for its text or answer.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(search="Search text from the question or one of its answers.")
async def feud_disable_question(interaction: discord.Interaction, search: str):
    guild_id = interaction.guild.id if interaction.guild else None
    question = find_question_by_search(guild_id, search)
    if not question:
        await interaction.response.send_message("No matching question found.", ephemeral=True)
        return
    disable_question_for_guild(guild_id, question)
    await interaction.response.send_message(
        f"Disabled question: **{question.question}**",
        ephemeral=True,
    )


@bot.tree.command(name="feud_enable_question", description="List or re-enable disabled questions.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(index="Disabled-question number from this command's list.")
async def feud_enable_question(interaction: discord.Interaction, index: Optional[int] = None):
    guild_id = interaction.guild.id if interaction.guild else None
    state = get_question_admin_state(guild_id)
    disabled_ids = list(state.get("disabled", []))

    if not disabled_ids:
        await interaction.response.send_message("No questions are disabled for this server.", ephemeral=True)
        return

    if index is None:
        lines = []
        for position, qid in enumerate(disabled_ids[:20], start=1):
            question = find_question_by_id(qid, guild_id)
            label = question.question[:90] if question else qid[:90]
            lines.append(f"**{position}.** {label}")
        await interaction.response.send_message("Disabled questions:\n" + "\n".join(lines), ephemeral=True)
        return

    if index < 1 or index > len(disabled_ids):
        await interaction.response.send_message("That disabled-question number does not exist.", ephemeral=True)
        return

    qid = disabled_ids[index - 1]
    enable_question_for_guild(guild_id, qid)
    await interaction.response.send_message(f"Re-enabled disabled question `{index}`.", ephemeral=True)


@bot.tree.command(name="feud_alias_cleanup", description="Find or clean duplicate/self-duplicating aliases.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(apply="Set true to apply cleanup to in-memory questions. Default reports only.")
async def feud_alias_cleanup(interaction: discord.Interaction, apply: bool = False):
    guild_id = interaction.guild.id if interaction.guild else None
    questions = get_all_questions(guild_id)
    summary = alias_cleanup_summary(questions, apply=apply)

    if apply:
        # Built-in JSON files are not rewritten here; runtime alias approvals/custom questions are saved where possible.
        save_custom_questions(CUSTOM_QUESTIONS)
        save_engagement_state(ENGAGEMENT_STATE)

    embed = discord.Embed(
        title="Alias Cleanup",
        description="Applied cleanup." if apply else "Dry run only. Re-run with `apply: True` to clean runtime aliases/custom questions.",
        color=discord.Color.green() if apply else discord.Color.gold(),
    )
    embed.add_field(name="Duplicate aliases", value=f"`{summary['duplicate_aliases']}`", inline=True)
    embed.add_field(name="Aliases matching answer text", value=f"`{summary['self_aliases']}`", inline=True)
    embed.add_field(name="Total candidates", value=f"`{summary['total']}`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)
'''


def main() -> int:
    if not MAIN_PATH.exists():
        raise SystemExit("main.py not found. Run this from the project root.")

    text = MAIN_PATH.read_text(encoding="utf-8")

    if MARKER in text:
        print("V1.4.4 question admin UI already appears to be applied.")
        return 0

    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(text, encoding="utf-8")
        print(f"Backup written to {BACKUP_PATH.name}")

    if PICKER_OLD in text and PICKER_NEW not in text:
        text = text.replace(PICKER_OLD, PICKER_NEW, 1)
        print("Patched question picker to skip disabled questions.")
    else:
        print("Question picker disabled-filter patch was not applied; pattern not found or already patched.")

    run_marker = "# ----------------------------\n# RUN BOT\n# ----------------------------"
    if run_marker not in text:
        raise SystemExit("Could not find RUN BOT marker in main.py")

    text = text.replace(run_marker, QUESTION_ADMIN_CODE + "\n\n" + run_marker, 1)
    MAIN_PATH.write_text(text, encoding="utf-8")
    print("Applied V1.4.4 Question Admin & Review UI patch.")
    print("Run tools/healthcheck.py, then restart the bot to sync the new commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
