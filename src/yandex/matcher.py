from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from media.models import TrackInfo
from utils.text import normalize_text

_TERMINAL_QUALIFIER_RE = re.compile(r"^(.*?)\s*[\(\[（]([^\)\]）]{2,80})[\)\]）]\s*$")


@dataclass(frozen=True, slots=True)
class YandexCandidate:
    track_id: str
    title: str
    artist: str
    album: str | None = None
    duration: float | None = None
    version: str | None = None
    subtitle: str | None = None
    cover_url: str | None = None
    track_url: str | None = None
    artist_url: str | None = None

    @property
    def display_title(self) -> str:
        qualifier = self.version or self.subtitle
        if qualifier and normalize_text(qualifier) not in normalize_text(self.title):
            return f"{self.title} ({qualifier})"
        return self.title

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> YandexCandidate:
        return cls(**{field: value.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class MatchResult:
    candidate: YandexCandidate
    confidence: float
    breakdown: dict[str, float]


def split_terminal_qualifier(title: str | None) -> tuple[str, str | None]:
    title = (title or "").strip()
    match = _TERMINAL_QUALIFIER_RE.match(title)
    if not match:
        return title, None
    return match.group(1).strip(), match.group(2).strip()


def _sequence(a: str | None, b: str | None) -> float:
    a_norm, b_norm = normalize_text(a), normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def _token_similarity(a: str | None, b: str | None) -> float:
    left, right = set(normalize_text(a).split()), set(normalize_text(b).split())
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    return (2.0 * intersection) / (len(left) + len(right))


def text_similarity(a: str | None, b: str | None) -> float:
    return max(_sequence(a, b), _token_similarity(a, b))


def _duration_similarity(a: float | None, b: float | None) -> float | None:
    if not a or not b or a <= 0 or b <= 0:
        return None
    difference = abs(a - b)

    return math.exp(-((difference / 10.0) ** 1.35))


class TrackMatcher:
    def score(self, source: TrackInfo, candidate: YandexCandidate) -> MatchResult:
        source_base, source_qualifier = split_terminal_qualifier(source.title)
        candidate_base, title_qualifier = split_terminal_qualifier(candidate.title)
        candidate_qualifier = candidate.version or candidate.subtitle or title_qualifier

        title_base_score = text_similarity(source_base, candidate_base)
        title_display_score = text_similarity(source.title, candidate.display_title)
        title_score = max(title_base_score, title_display_score)
        artist_score = text_similarity(source.artist, candidate.artist)
        album_score = (
            text_similarity(source.album, candidate.album)
            if source.album and candidate.album
            else None
        )
        duration_score = _duration_similarity(source.duration, candidate.duration)

        expected_qualifier = source.version or source.subtitle or source_qualifier
        version_score = (
            text_similarity(expected_qualifier, candidate_qualifier)
            if expected_qualifier and candidate_qualifier
            else None
        )

        weighted: list[tuple[float, float]] = [(title_score, 0.48), (artist_score, 0.32)]
        if album_score is not None:
            weighted.append((album_score, 0.08))
        if duration_score is not None:
            weighted.append((duration_score, 0.12))
        if version_score is not None:
            weighted.append((version_score, 0.12))

        score = sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )

        if title_score < 0.52:
            score *= 0.55
        if artist_score < 0.48:
            score *= 0.5
        if expected_qualifier and candidate_qualifier and (version_score or 0) < 0.45:
            score *= 0.78
        if duration_score is not None and duration_score < 0.10:
            score *= 0.76

        breakdown = {
            "title": title_score,
            "artist": artist_score,
            "album": album_score if album_score is not None else -1.0,
            "duration": duration_score if duration_score is not None else -1.0,
            "version": version_score if version_score is not None else -1.0,
        }
        return MatchResult(candidate, max(0.0, min(score, 1.0)), breakdown)

    def best(
        self,
        source: TrackInfo,
        candidates: Iterable[YandexCandidate],
        minimum_confidence: float = 0.68,
    ) -> MatchResult | None:
        matches = [self.score(source, candidate) for candidate in candidates]
        if not matches:
            return None
        result = max(matches, key=lambda item: item.confidence)
        return result if result.confidence >= minimum_confidence else None
