"""Question indexing helpers for faster large-pack lookup.

This module deliberately works with plain question-like objects. The main bot owns the
actual FeudQuestion dataclass; this helper only expects `.category` and `.pack` fields.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Optional, Sequence


class QuestionIndex:
    """Small in-memory index for category/pack lookups.

    For 5k+ questions, repeatedly scanning the full list is still workable, but this
    keeps `/feud_start`, category previews, and Game Night category selection snappy.
    """

    def __init__(self, questions: Sequence[object], normalise: Callable[[str], str]):
        self._normalise = normalise
        self._questions = list(questions)
        self._by_category: dict[str, list[object]] = defaultdict(list)
        self._by_pack: dict[str, list[object]] = defaultdict(list)

        for question in self._questions:
            category = self._normalise(getattr(question, "category", "general"))
            pack = self._normalise(getattr(question, "pack", "base"))
            self._by_category[category].append(question)
            self._by_pack[pack].append(question)

    @classmethod
    def build(cls, questions: Sequence[object], normalise: Callable[[str], str]) -> "QuestionIndex":
        return cls(questions, normalise)

    def all(self) -> list[object]:
        return list(self._questions)

    def categories(self) -> set[str]:
        return set(self._by_category.keys())

    def packs(self) -> set[str]:
        return set(self._by_pack.keys())

    def for_category(self, category: str) -> list[object]:
        category = self._normalise(category)
        if category == "random":
            return self.all()
        return list(self._by_category.get(category, []))

    def for_pack(self, pack: str, pack_categories: Optional[Iterable[str]] = None) -> list[object]:
        pack = self._normalise(pack)
        selected: list[object] = []
        seen: set[int] = set()

        for question in self._by_pack.get(pack, []):
            marker = id(question)
            if marker not in seen:
                selected.append(question)
                seen.add(marker)

        for category in pack_categories or []:
            for question in self.for_category(category):
                marker = id(question)
                if marker not in seen:
                    selected.append(question)
                    seen.add(marker)

        return selected
