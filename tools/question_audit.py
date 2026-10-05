from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = ["questions.json", "extra_questions.json", "mega_questions.json", "custom_questions.json"]
REPORT_DIR = ROOT / "reports"

KNOWN_CATEGORIES = {
    "random", "general", "mafia", "dude", "uk", "discord", "big_lebowski", "food",
    "drink", "music", "movies", "tv", "gaming", "sports", "football", "christmas",
    "wedding", "family", "work", "school", "history", "geography", "science", "animals",
    "weather", "travel", "cars", "crime", "police", "gangster", "noir", "bowling",
    "pub", "british_slang", "liverpool", "opticians", "internet", "memes", "technology",
    "fantasy", "sci_fi", "horror", "superheroes", "cartoons", "celebrities", "money",
    "love", "pets", "household", "random_weird", "modern_life", "social_media",
    "shopping", "transport", "dating", "office", "parenting", "home", "garden", "hobbies"
}

SURVEY_OPENERS = (
    "name ", "name something", "name someone", "name a ", "name an ", "tell me ",
    "give me ", "what is something", "what's something", "what are things", "what are some"
)

# These are intentionally phrases/whole words, not raw substrings. The first V1.4 audit used
# simple substring checks, so "talking" matched "king" and "checking" matched "king".
FACT_CUES = (
    "capital", "current", "latest", "today", "this year", "president", "prime minister",
    "king", "queen", "ceo", "official", "population", "largest", "smallest", "longest",
    "shortest", "oldest", "youngest", "when did", "what year", "which year", "how many",
    "how much", "winner", "champion", "record", "world record", "highest", "lowest",
    "born", "died", "founded", "released", "price", "cost", "law", "legal"
)

SUSPICIOUS_WORDS = (
    "maybe", "etc", "and stuff", "thingy", "unknown", "none", "n/a", "various", "other"
)


def normalize(text: Any) -> str:
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_category(text: Any) -> str:
    """Normalise a category key without losing underscore-style category names."""
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def contains_fact_cue(question: str) -> bool:
    qnorm = normalize(question)
    for cue in FACT_CUES:
        cue_norm = normalize(cue)
        if re.search(rf"\b{re.escape(cue_norm)}\b", qnorm):
            return True

    # Keep date checks precise so a normal dating question is not treated as a fact question.
    date_patterns = (
        r"\bwhat date\b", r"\bwhich date\b", r"\bdate was\b", r"\bdate is\b",
        r"\brelease date\b", r"\bfounded date\b"
    )
    return any(re.search(pattern, qnorm) for pattern in date_patterns)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_questions(path: Path) -> Iterable[dict[str, Any]]:
    data = load_json(path)
    if isinstance(data, list):
        for index, item in enumerate(data, start=1):
            if isinstance(item, dict):
                yield {"source_file": path.name, "source_index": index, **item}
            else:
                yield {"source_file": path.name, "source_index": index, "_raw_error": f"question row is {type(item).__name__}"}
    elif isinstance(data, dict):
        for guild_id, questions in data.items():
            if not isinstance(questions, list):
                continue
            for index, item in enumerate(questions, start=1):
                if isinstance(item, dict):
                    yield {"source_file": path.name, "source_index": index, "guild_id": guild_id, **item}
    else:
        yield {"source_file": path.name, "source_index": 1, "_raw_error": f"top level is {type(data).__name__}"}


@dataclass
class Finding:
    severity: str
    source_file: str
    source_index: int
    category: str
    question: str
    issue: str
    details: str


def add(findings: list[Finding], severity: str, item: dict[str, Any], issue: str, details: str = "") -> None:
    findings.append(Finding(
        severity=severity,
        source_file=str(item.get("source_file", "unknown")),
        source_index=int(item.get("source_index", 0) or 0),
        category=str(item.get("category", "")),
        question=str(item.get("question", "")),
        issue=issue,
        details=details,
    ))


def audit_question(item: dict[str, Any], findings: list[Finding], seen_questions: Counter[str]) -> None:
    if "_raw_error" in item:
        add(findings, "error", item, "Invalid question row", item["_raw_error"])
        return

    question = str(item.get("question", "")).strip()
    category = normalize_category(item.get("category", "general")) or "general"
    answers = item.get("answers")

    if not question:
        add(findings, "error", item, "Missing question text")
    elif len(question) < 10:
        add(findings, "warning", item, "Very short question", question)

    if category not in KNOWN_CATEGORIES:
        add(findings, "warning", item, "Unknown category", category)

    qkey = f"{category}:{normalize(question)}"
    seen_questions[qkey] += 1
    if seen_questions[qkey] > 1:
        add(findings, "warning", item, "Duplicate question text/category", qkey)

    if not isinstance(answers, list):
        add(findings, "error", item, "Answers must be a list", type(answers).__name__)
        return

    if len(answers) < 2:
        add(findings, "error", item, "Fewer than two answers", f"answer_count={len(answers)}")
    if len(answers) > 8:
        add(findings, "warning", item, "More than eight answers", f"answer_count={len(answers)}")

    normalized_answers: Counter[str] = Counter()
    points: list[int] = []

    for answer_index, answer in enumerate(answers, start=1):
        if not isinstance(answer, dict):
            add(findings, "error", item, "Answer row is not an object", f"answer {answer_index}: {type(answer).__name__}")
            continue

        text = str(answer.get("text", "")).strip()
        norm_text = normalize(text)
        normalized_answers[norm_text] += 1

        if not text:
            add(findings, "error", item, "Empty answer text", f"answer {answer_index}")
        if len(text) > 45:
            add(findings, "warning", item, "Long answer text", f"answer {answer_index}: {text}")
        if len(text.split()) > 7:
            add(findings, "info", item, "Verbose answer text", f"answer {answer_index}: {text}")
        if any(re.search(rf"\b{re.escape(normalize(word))}\b", normalize(text)) for word in SUSPICIOUS_WORDS if normalize(word)):
            add(findings, "warning", item, "Suspicious vague answer", f"answer {answer_index}: {text}")

        try:
            point_value = int(answer.get("points"))
        except (TypeError, ValueError):
            add(findings, "error", item, "Answer points are not an integer", f"answer {answer_index}: {answer.get('points')}")
            continue

        points.append(point_value)
        if point_value <= 0:
            add(findings, "error", item, "Non-positive answer points", f"answer {answer_index}: {point_value}")
        if point_value > 100:
            add(findings, "warning", item, "Answer over 100 points", f"answer {answer_index}: {point_value}")

        aliases = answer.get("aliases", [])
        if aliases is None:
            aliases = []
        if not isinstance(aliases, list):
            add(findings, "warning", item, "Aliases should be a list", f"answer {answer_index}")
        else:
            alias_norms = [normalize(alias) for alias in aliases]
            for alias in alias_norms:
                if alias == norm_text:
                    add(findings, "info", item, "Alias duplicates answer text", f"answer {answer_index}: {text}")
            duplicate_aliases = [alias for alias, count in Counter(alias_norms).items() if alias and count > 1]
            if duplicate_aliases:
                add(findings, "warning", item, "Duplicate aliases", ", ".join(duplicate_aliases[:8]))

    for answer_text, count in normalized_answers.items():
        if answer_text and count > 1:
            add(findings, "warning", item, "Duplicate answer text", answer_text)

    if len(points) >= 2:
        if points != sorted(points, reverse=True):
            add(findings, "warning", item, "Answer points are not descending", f"points={points}")
        total = sum(points)
        if total > 150:
            add(findings, "warning", item, "High board total", f"total={total}")
        if total < 35:
            add(findings, "info", item, "Low board total", f"total={total}")

    qnorm = normalize(question)
    if not qnorm.startswith(SURVEY_OPENERS):
        add(findings, "info", item, "Question is not in classic survey phrasing", question)

    if contains_fact_cue(question):
        add(findings, "review", item, "Fact/current-sensitive wording needs human/web check", question)


def write_reports(findings: list[Finding], questions: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    csv_path = REPORT_DIR / "question_audit_findings.csv"
    md_path = REPORT_DIR / "question_audit_report.md"
    web_path = REPORT_DIR / "question_web_check_candidates.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(Finding.__dataclass_fields__.keys()))
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding.__dict__)

    severity_counts = Counter(finding.severity for finding in findings)
    issue_counts = Counter(finding.issue for finding in findings)
    review_items = [finding for finding in findings if finding.severity == "review"]

    with web_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_file", "source_index", "category", "question", "suggested_search"])
        writer.writeheader()
        for finding in review_items:
            writer.writerow({
                "source_file": finding.source_file,
                "source_index": finding.source_index,
                "category": finding.category,
                "question": finding.question,
                "suggested_search": f"{finding.question} common answers survey Family Feud",
            })

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# Question Audit Report\n\n")
        handle.write(f"Questions scanned: **{len(questions)}**\n\n")
        handle.write("## Findings by Severity\n\n")
        for severity in ["error", "warning", "review", "info"]:
            handle.write(f"- {severity}: **{severity_counts.get(severity, 0)}**\n")
        handle.write("\n## Top Issue Types\n\n")
        for issue, count in issue_counts.most_common(15):
            handle.write(f"- {issue}: **{count}**\n")
        handle.write("\n## Notes\n\n")
        handle.write("This audit checks structure, duplicates, scoring shape, wording, aliases, and fact/current-sensitive cues. ")
        handle.write("Family Feud/Fortunes boards are survey-style prompts, so many answers cannot be proven 'correct' by the internet; they need to feel plausible and be fun/fair. ")
        handle.write("Use `question_web_check_candidates.csv` for the smaller subset that genuinely needs external verification.\n")

    print(f"Scanned {len(questions)} questions.")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {web_path}")
    if severity_counts.get("error", 0):
        print(f"ERROR findings: {severity_counts['error']}")
    if severity_counts.get("warning", 0):
        print(f"WARNING findings: {severity_counts['warning']}")
    if severity_counts.get("review", 0):
        print(f"WEB REVIEW candidates: {severity_counts['review']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Family Feud/Fortunes question packs.")
    parser.add_argument("files", nargs="*", help="Question JSON files to audit. Defaults to known pack files.")
    args = parser.parse_args()

    paths = [ROOT / file_name for file_name in (args.files or DEFAULT_FILES)]
    findings: list[Finding] = []
    questions: list[dict[str, Any]] = []
    seen_questions: Counter[str] = Counter()

    for path in paths:
        if not path.exists():
            continue
        try:
            file_questions = list(iter_questions(path))
        except json.JSONDecodeError as error:
            findings.append(Finding("error", path.name, 0, "", "", "Invalid JSON file", str(error)))
            continue
        questions.extend(file_questions)

    for item in questions:
        audit_question(item, findings, seen_questions)

    write_reports(findings, questions)
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
