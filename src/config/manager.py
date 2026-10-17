from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from config.defaults import merge_defaults, migrate_stored, new_defaults


class ConfigError(RuntimeError):
    pass


class ConfigManager:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._data = new_defaults()
        self._subscribers: list[Callable[[str, Any], None]] = []

    def load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                self._data = new_defaults()
                self.save()
                return self.snapshot()
            try:
                stored = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(stored, dict):
                    raise ValueError("configuration root is not an object")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                broken = self.path.with_suffix(".broken.json")
                with contextlib.suppress(OSError):
                    os.replace(self.path, broken)
                self._data = new_defaults()
                self.save()
                raise ConfigError(f"Invalid configuration was replaced: {exc}") from exc
            self._data = merge_defaults(migrate_stored(stored))
            self.save()
            return self.snapshot()

    def snapshot(self) -> dict:
        with self._lock:
            return json.loads(json.dumps(self._data, ensure_ascii=False))

    def get(self, dotted_key: str, default: Any = None) -> Any:
        with self._lock:
            current: Any = self._data
            for part in dotted_key.split("."):
                if not isinstance(current, dict) or part not in current:
                    return default
                current = current[part]
            return current

    def set(self, dotted_key: str, value: Any, *, save: bool = True) -> None:
        with self._lock:
            parts = dotted_key.split(".")
            current = self._data
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            if current.get(parts[-1]) == value:
                return
            current[parts[-1]] = value
            if save:
                self.save()
        for callback in tuple(self._subscribers):
            callback(dotted_key, value)

    def replace(self, data: dict) -> None:
        with self._lock:
            self._data = merge_defaults(data)
            self.save()
        for callback in tuple(self._subscribers):
            callback("*", self.snapshot())

    def reset(self) -> None:
        self.replace(new_defaults())

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        self._subscribers.append(callback)

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self._data, ensure_ascii=False, indent=2) + "\n"
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            except Exception:
                with contextlib.suppress(OSError):
                    os.unlink(temp_name)
                raise
