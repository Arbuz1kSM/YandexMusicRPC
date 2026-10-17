from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from pathlib import Path

from media.models import TrackInfo
from utils.text import normalize_text
from yandex.matcher import YandexCandidate


class TrackCache:
    def __init__(self, path: Path | None, ttl_seconds: int = 30 * 24 * 60 * 60):
        self.path = path
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, dict] = {}

    @staticmethod
    def key(track: TrackInfo) -> str:
        duration = round(track.duration) if track.duration else ""
        return "|".join(
            (
                normalize_text(track.title),
                normalize_text(track.artist),
                normalize_text(track.album),
                str(duration),
            )
        )

    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._items = raw
        except (OSError, json.JSONDecodeError, ValueError):
            self._items = {}

    def get(self, track: TrackInfo) -> tuple[YandexCandidate, float] | None:
        item = self._items.get(self.key(track))
        if not item:
            return None
        if time.time() - float(item.get("created_at", 0)) > self.ttl_seconds:
            self._items.pop(self.key(track), None)
            return None
        try:
            return YandexCandidate.from_dict(item["candidate"]), float(item["confidence"])
        except (KeyError, TypeError, ValueError):
            self._items.pop(self.key(track), None)
            return None

    def put(self, track: TrackInfo, candidate: YandexCandidate, confidence: float) -> None:
        self._items[self.key(track)] = {
            "created_at": time.time(),
            "confidence": confidence,
            "candidate": candidate.to_dict(),
        }
        self._trim()
        self.save()

    def _trim(self, maximum: int = 1000) -> None:
        if len(self._items) <= maximum:
            return
        ordered = sorted(
            self._items.items(), key=lambda pair: pair[1].get("created_at", 0), reverse=True
        )
        self._items = dict(ordered[:maximum])

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._items, ensure_ascii=False, separators=(",", ":"))
        fd, temp_name = tempfile.mkstemp(prefix=".tracks.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(temp_name)
            raise

    def clear(self) -> None:
        self._items.clear()
        self.save()
