"""Reusable health and diagnostics helpers for Family Feud Fortune Bot.

These helpers are intentionally independent from the Discord runtime where possible.
They can be used by local tools, tests, and the in-Discord /feud_health command.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SOURCE_FILES = [
    "main.py",
    "questions.json",
    "extra_questions.json",
    "mega_questions.json",
    "requirements.txt",
]

RUNTIME_JSON_FILES = [
    "active_games.json",
    "server_scores.json",
    "engagement_state.json",
    "custom_questions.json",
    "server_settings.json",
]


@dataclass
class HealthCheck:
    name: str
    ok: bool
    detail: str
    severity: str = "error"

    @property
    def emoji(self) -> str:
        if self.ok:
            return "✅"
        return "⚠️" if self.severity == "warning" else "❌"


@dataclass
class HealthReport:
    checks: list[HealthCheck] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(check.ok or check.severity == "warning" for check in self.checks)

    @property
    def hard_failures(self) -> list[HealthCheck]:
        return [check for check in self.checks if not check.ok and check.severity != "warning"]

    @property
    def warnings(self) -> list[HealthCheck]:
        return [check for check in self.checks if not check.ok and check.severity == "warning"]

    def add(self, name: str, ok: bool, detail: str, severity: str = "error") -> None:
        self.checks.append(HealthCheck(name=name, ok=ok, detail=detail, severity=severity))

    def lines(self, limit: int | None = None) -> list[str]:
        checks = self.checks if limit is None else self.checks[:limit]
        return [f"{check.emoji} **{check.name}:** {check.detail}" for check in checks]


def load_json(path: Path) -> tuple[bool, Any, str]:
    if not path.exists():
        return True, None, "missing; will be created at runtime"

    try:
        with path.open("r", encoding="utf-8") as file:
            return True, json.load(file), "valid JSON"
    except json.JSONDecodeError as error:
        return False, None, f"invalid JSON: {error}"


def count_question_file(path: Path) -> tuple[bool, int, str]:
    ok, data, detail = load_json(path)
    if not ok:
        return False, 0, detail
    if data is None:
        return False, 0, "missing question file"
    if not isinstance(data, list):
        return False, 0, "question file must contain a JSON array"

    problems = 0
    for index, item in enumerate(data[:50], start=1):
        if not isinstance(item, dict):
            problems += 1
            continue
        if not item.get("question") or not isinstance(item.get("answers"), list):
            problems += 1

    if problems:
        return False, len(data), f"{len(data)} question(s), sampled {problems} structural issue(s)"
    return True, len(data), f"{len(data)} question(s)"


def main_py_compiles(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "main.py missing"
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return True, "syntax OK"
    except SyntaxError as error:
        return False, f"syntax error at line {error.lineno}: {error.msg}"


def detect_slash_commands(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r'@bot\.tree\.command\(name=["\']([^"\']+)["\']', text)))


def sqlite_status(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "missing; will be created at runtime"
    try:
        with sqlite3.connect(path) as connection:
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        return True, "readable"
    except sqlite3.Error as error:
        return False, f"sqlite error: {error}"


def build_health_report(repo_root: str | Path = ".") -> HealthReport:
    root = Path(repo_root)
    report = HealthReport()

    for filename in SOURCE_FILES:
        path = root / filename
        report.add(filename, path.exists(), "present" if path.exists() else "missing")

    compile_ok, compile_detail = main_py_compiles(root / "main.py")
    report.add("main.py compile", compile_ok, compile_detail)

    total_questions = 0
    for filename in ["questions.json", "extra_questions.json", "mega_questions.json"]:
        ok, count, detail = count_question_file(root / filename)
        total_questions += count
        report.add(filename, ok, detail)
    report.metrics["question_count"] = total_questions

    for filename in RUNTIME_JSON_FILES:
        ok, _, detail = load_json(root / filename)
        report.add(filename, ok, detail, severity="warning" if ok else "error")

    db_ok, db_detail = sqlite_status(root / "fortune_bot.sqlite3")
    report.add("fortune_bot.sqlite3", db_ok, db_detail, severity="warning" if db_ok else "error")

    board_template = root / "assets" / "game_board_template.png"
    report.add(
        "board template",
        board_template.exists(),
        "present" if board_template.exists() else "missing; bot will fall back to embed boards",
        severity="warning",
    )

    commands = detect_slash_commands(root / "main.py")
    report.metrics["slash_commands"] = commands
    report.add("slash commands", bool(commands), f"{len(commands)} detected")

    env_path = root / ".env"
    example_path = root / ".env.example"
    report.add(".env", env_path.exists(), "present" if env_path.exists() else "missing; copy .env.example", severity="warning")
    report.add(".env.example", example_path.exists(), "present" if example_path.exists() else "missing")

    return report


def runtime_summary(
    *,
    version: str,
    questions: Iterable[Any],
    custom_questions: dict[str, list[Any]],
    server_scores: dict[str, Any],
    engagement_state: dict[str, Any],
    active_games: dict[Any, Any],
    database_file: str,
    board_template_file: str,
) -> dict[str, Any]:
    custom_count = sum(len(items) for items in custom_questions.values())
    db_ok, db_detail = sqlite_status(Path(database_file))
    return {
        "version": version,
        "questions": len(list(questions)) if not isinstance(questions, list) else len(questions),
        "custom_questions": custom_count,
        "score_servers": len(server_scores),
        "engagement_sections": len(engagement_state),
        "active_rounds": len(active_games),
        "database_ok": db_ok,
        "database_detail": db_detail,
        "board_template_present": os.path.exists(board_template_file),
    }
