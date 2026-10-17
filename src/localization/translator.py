from __future__ import annotations

import json
from collections.abc import Callable

from utils.paths import resource_path


class I18n:
    def __init__(self, language: str = "ru") -> None:
        self.language = language if language in {"ru", "en"} else "en"
        self._strings: dict[str, str] = {}
        self._subscribers: list[Callable[[], None]] = []
        self._load()

    def _load(self) -> None:
        path = resource_path("localization", f"{self.language}.json")
        self._strings = json.loads(path.read_text(encoding="utf-8"))

    def t(self, key: str, **values) -> str:
        value = self._strings.get(key, key)
        try:
            return value.format(**values)
        except (KeyError, ValueError):
            return value

    def set_language(self, language: str) -> None:
        if language not in {"ru", "en"} or language == self.language:
            return
        self.language = language
        self._load()
        for callback in tuple(self._subscribers):
            callback()

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._subscribers.append(callback)
