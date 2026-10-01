"""Family Feud Fortune Bot local healthcheck.

Run before game night or deployment:

    python tools/healthcheck.py

The script checks source files, question JSON, optional runtime state, SQLite,
board-template assets, and whether main.py can compile.
It does not connect to Discord and does not need a real bot token.
"""

from __future__ import annotations

import ast
import json
import os
import py_compile
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILES = [
    "main.py",
    "question_manager.py",
    "requirements.txt",
    "questions.json",
    "extra_questions.json",
    "mega_questions.json",
]

QUESTION_FILES = [
    "questions.json",
    "extra_questions.json",
    "mega_questions.json",
]

RUNTIME_JSON_FILES = [
    "active_games.json",
    "engagement_state.json",
    "server_scores.json",
    "custom_questions.json",
    "server_settings.json",
]

OPTIONAL_ASSETS = [
    "assets/game_board_template.png",
]

SQLITE_FILE = "fortune_bot.sqlite3"
ENV_FILE = ".env"
ENV_EXAMPLE_FILE = ".env.example"
MAIN_FILE = "main.py"
VERSION_FILE = "VERSION"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ok(name: str, detail: str) -> CheckResult:
    return CheckResult(name, "OK", detail)


def warn(name: str, detail: str) -> CheckResult:
    return CheckResult(name, "WARN", detail)


def fail(name: str, detail: str) -> CheckResult:
    return CheckResult(name, "FAIL", detail)


def check_source_files() -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative in SOURCE_FILES:
        path = PROJECT_ROOT / relative
        if path.exists():
            results.append(ok(f"source:{relative}", f"found ({path.stat().st_size:,} bytes)"))
        else:
            results.append(fail(f"source:{relative}", "missing required source file"))
    return results


def check_env() -> list[CheckResult]:
    results: list[CheckResult] = []
    env_example = PROJECT_ROOT / ENV_EXAMPLE_FILE
    env_file = PROJECT_ROOT / ENV_FILE

    if env_example.exists():
        results.append(ok("env:example", ".env.example found"))
    else:
        results.append(warn("env:example", ".env.example missing"))

    if not env_file.exists():
        results.append(warn("env:token", ".env missing; create it from .env.example before running the bot"))
        return results

    token_value = ""
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("DISCORD_BOT_TOKEN="):
            token_value = line.split("=", 1)[1].strip()
            break

    if token_value and token_value != "your_discord_bot_token_here":
        results.append(ok("env:token", "DISCORD_BOT_TOKEN appears to be set"))
    else:
        results.append(fail("env:token", "DISCORD_BOT_TOKEN is missing or still set to the placeholder"))

    return results


def check_compile() -> list[CheckResult]:
    main_path = PROJECT_ROOT / MAIN_FILE
    if not main_path.exists():
        return [fail("python:compile", "main.py missing")]

    try:
        py_compile.compile(str(main_path), doraise=True)
    except py_compile.PyCompileError as error:
        return [fail("python:compile", str(error))]

    return [ok("python:compile", "main.py compiles")]


def check_question_file(relative: str) -> CheckResult:
    path = PROJECT_ROOT / relative
    if not path.exists():
        return fail(f"questions:{relative}", "missing")

    try:
        data = read_json(path)
    except json.JSONDecodeError as error:
        return fail(f"questions:{relative}", f"invalid JSON: {error}")

    if not isinstance(data, list):
        return fail(f"questions:{relative}", "expected a JSON list")

    issues: list[str] = []
    categories: set[str] = set()
    answer_total = 0

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            issues.append(f"#{index} is not an object")
            continue

        question = str(item.get("question", "")).strip()
        category = str(item.get("category", "general")).strip() or "general"
        answers = item.get("answers", [])
        categories.add(category)

        if not question:
            issues.append(f"#{index} missing question text")
        if not isinstance(answers, list) or len(answers) < 2:
            issues.append(f"#{index} has fewer than two answers")
            continue

        seen_answers: set[str] = set()
        for answer in answers:
            answer_total += 1
            if not isinstance(answer, dict):
                issues.append(f"#{index} has a non-object answer")
                continue
            text = str(answer.get("text", "")).strip().lower()
            points = answer.get("points")
            if not text:
                issues.append(f"#{index} has blank answer text")
            if text in seen_answers:
                issues.append(f"#{index} duplicate answer {text!r}")
            seen_answers.add(text)
            try:
                if int(points) <= 0:
                    issues.append(f"#{index} answer {text!r} has non-positive points")
            except (TypeError, ValueError):
                issues.append(f"#{index} answer {text!r} has invalid points")

        if len(issues) >= 10:
            break

    if issues:
        return warn(
            f"questions:{relative}",
            f"{len(data):,} questions, {len(categories):,} categories, first issues: " + "; ".join(issues[:5]),
        )

    return ok(
        f"questions:{relative}",
        f"{len(data):,} questions, {len(categories):,} categories, {answer_total:,} answers",
    )


def check_questions() -> list[CheckResult]:
    return [check_question_file(relative) for relative in QUESTION_FILES]


def check_runtime_json() -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative in RUNTIME_JSON_FILES:
        path = PROJECT_ROOT / relative
        if not path.exists():
            results.append(ok(f"runtime:{relative}", "not present; will be created when needed"))
            continue
        try:
            read_json(path)
        except json.JSONDecodeError as error:
            results.append(fail(f"runtime:{relative}", f"invalid JSON: {error}"))
        else:
            results.append(ok(f"runtime:{relative}", "valid JSON"))
    return results


def check_sqlite() -> list[CheckResult]:
    path = PROJECT_ROOT / SQLITE_FILE
    if not path.exists():
        return [ok("sqlite", "database not present; bot will create it on startup")]

    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
    except sqlite3.DatabaseError as error:
        return [fail("sqlite", f"database error: {error}")]

    tables = ", ".join(row[0] for row in rows) or "no tables"
    return [ok("sqlite", f"opened successfully; tables: {tables}")]


def check_assets() -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative in OPTIONAL_ASSETS:
        path = PROJECT_ROOT / relative
        if path.exists():
            results.append(ok(f"asset:{relative}", f"found ({path.stat().st_size:,} bytes)"))
        else:
            results.append(warn(f"asset:{relative}", "missing; bot will fall back to embed-only boards"))
    return results


def check_command_surface() -> list[CheckResult]:
    main_path = PROJECT_ROOT / MAIN_FILE
    if not main_path.exists():
        return [fail("commands", "main.py missing")]

    try:
        tree = ast.parse(main_path.read_text(encoding="utf-8"))
    except SyntaxError as error:
        return [fail("commands", f"cannot parse main.py: {error}")]

    commands: list[str] = []
    for node in ast.walk(tree):
        decorators = getattr(node, "decorator_list", [])
        for decorator in decorators:
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "command":
                    for keyword in decorator.keywords:
                        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                            commands.append(str(keyword.value.value))

    if not commands:
        return [warn("commands", "no slash commands detected by static scan")]

    return [ok("commands", f"detected {len(commands)} slash commands: {', '.join(sorted(commands)[:12])}{'...' if len(commands) > 12 else ''}")]


def check_version() -> list[CheckResult]:
    path = PROJECT_ROOT / VERSION_FILE
    if not path.exists():
        return [warn("version", "VERSION file missing")]
    return [ok("version", path.read_text(encoding="utf-8").strip() or "blank")]


def run_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    checks = [
        check_version,
        check_source_files,
        check_env,
        check_compile,
        check_questions,
        check_runtime_json,
        check_sqlite,
        check_assets,
        check_command_surface,
    ]
    for check in checks:
        results.extend(check())
    return results


def print_results(results: list[CheckResult]) -> int:
    width = max(len(result.name) for result in results) if results else 10
    failures = 0
    warnings = 0

    print("Family Feud Fortune Bot Healthcheck")
    print("=" * 39)
    print(f"Project: {PROJECT_ROOT}")
    print()

    for result in results:
        if result.status == "FAIL":
            failures += 1
        elif result.status == "WARN":
            warnings += 1
        print(f"[{result.status:<4}] {result.name:<{width}}  {result.detail}")

    print()
    print(f"Summary: {failures} failure(s), {warnings} warning(s), {len(results)} checks")

    if failures:
        return 1
    return 0


def main() -> int:
    return print_results(run_checks())


if __name__ == "__main__":
    raise SystemExit(main())
