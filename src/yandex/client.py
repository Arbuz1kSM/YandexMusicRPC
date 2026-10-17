from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

from media.models import CoverKind, CoverRef, DataSource, TrackInfo
from utils.logging import api
from yandex.cache import TrackCache
from yandex.matcher import MatchResult, TrackMatcher, YandexCandidate

LOGGER = logging.getLogger(__name__)


def _error_kind(exc: BaseException) -> str:

    root: BaseException = exc
    visited: set[int] = set()
    while id(root) not in visited:
        visited.add(id(root))
        next_error = root.__cause__ or root.__context__
        if not isinstance(next_error, BaseException):
            break
        root = next_error
    parts = [type(exc).__name__]
    if type(root) is not type(exc):
        parts.append(type(root).__name__)
    winerror = getattr(root, "winerror", None)
    if isinstance(winerror, int):
        parts.append(f"WinError {winerror}")
    return " / ".join(parts)


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _attribute(value: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(value, name, default)
    except Exception:
        return default


def _cover_url(uri: str | None) -> str | None:
    if not uri:
        return None
    uri = uri.replace("%%", "400x400")
    if uri.startswith("//"):
        return "https:" + uri
    if uri.startswith("http://"):
        return "https://" + uri.removeprefix("http://")
    if uri.startswith("https://"):
        return uri
    return "https://" + uri.lstrip("/")


def candidate_from_api(track: Any) -> YandexCandidate | None:
    title = _string(_attribute(track, "title"))
    track_id = _string(_attribute(track, "id"))
    if not title or not track_id:
        return None

    artists = _attribute(track, "artists", []) or []
    artist = ", ".join(name for item in artists if (name := _string(_attribute(item, "name"))))

    artist_id = next(
        (
            value
            for item in artists
            if (value := _string(_attribute(item, "id"))) and value.isdecimal() and int(value) > 0
        ),
        None,
    )
    artist_url = f"https://music.yandex.ru/artist/{artist_id}" if artist_id else None
    albums = _attribute(track, "albums", []) or []
    album_object = albums[0] if albums else None
    album = _string(_attribute(album_object, "title"))
    album_id = _string(_attribute(album_object, "id"))

    meta_data = _attribute(track, "meta_data")
    version = _string(_attribute(track, "version")) or _string(_attribute(meta_data, "version"))
    subtitle = _string(_attribute(track, "subtitle"))
    duration_ms = _attribute(track, "duration_ms")
    try:
        duration = float(duration_ms) / 1000 if duration_ms else None
    except (TypeError, ValueError):
        duration = None

    cover = _cover_url(_string(_attribute(track, "og_image"))) or _cover_url(
        _string(_attribute(track, "cover_uri"))
    )
    if album_id:
        url = f"https://music.yandex.ru/album/{album_id}/track/{track_id}"
        compound_id = f"{track_id}:{album_id}"
    else:
        url = f"https://music.yandex.ru/track/{track_id}"
        compound_id = track_id
    return YandexCandidate(
        track_id=compound_id,
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        version=version,
        subtitle=subtitle,
        cover_url=cover,
        track_url=url,
        artist_url=artist_url,
    )


class YandexMusicEnricher:
    def __init__(
        self,
        cache: TrackCache,
        token: str | None = None,
        timeout_seconds: float = 10.0,
        minimum_confidence: float = 0.68,
    ) -> None:
        self.cache = cache
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.minimum_confidence = minimum_confidence
        self.matcher = TrackMatcher()
        self._client = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="yandex-api")
        self._closed = False
        self.last_status = "ready"

    def _ensure_client_blocking(self):
        if self._client is not None:
            return self._client
        from yandex_music import Client

        client = Client(token=self.token) if self.token else Client()
        self._client = client.init()
        return self._client

    @staticmethod
    def _query(source: TrackInfo) -> str:
        return " ".join(part for part in (source.artist, source.title) if part).strip()

    def _search_blocking(self, source: TrackInfo) -> list[YandexCandidate]:
        client = self._ensure_client_blocking()
        query = self._query(source)
        if not query:
            return []

        queries = [query.replace("'", " ")]
        if queries[0] != query:
            queries.append(query)

        for current_query in queries:
            result = client.search(
                current_query,
                type_="track",
                page=0,
                nocorrect=True,
            )
            tracks_page = _attribute(result, "tracks")
            tracks = _attribute(tracks_page, "results", []) or []
            candidates = [
                converted
                for item in tracks[:10]
                if (converted := candidate_from_api(item)) is not None
            ]
            if candidates:
                return candidates
        return []

    async def _search(self, source: TrackInfo) -> list[YandexCandidate]:
        if self._closed:
            return []
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._executor, self._search_blocking, source)
        return await asyncio.wait_for(future, timeout=self.timeout_seconds)

    @staticmethod
    def _to_track(source: TrackInfo, match: MatchResult) -> TrackInfo:
        candidate = match.candidate
        cover = (
            CoverRef(CoverKind.URL, candidate.cover_url) if candidate.cover_url else source.cover
        )
        return replace(
            source,
            title=candidate.title,
            artist=candidate.artist or source.artist,
            album=candidate.album or source.album,
            version=candidate.version,
            subtitle=candidate.subtitle,
            duration=source.duration or candidate.duration,
            cover=cover,
            track_url=candidate.track_url,
            artist_url=candidate.artist_url,
            source=DataSource.WINDOWS_YANDEX,
            match_confidence=match.confidence,
            metadata={**source.metadata, "match_breakdown": match.breakdown},
        )

    async def enrich(self, source: TrackInfo) -> TrackInfo | None:
        cached = self.cache.get(source)
        if cached:
            self.last_status = "matched"
            candidate, confidence = cached
            api(LOGGER, "Cache match: %.0f%%", confidence * 100)
            return self._to_track(source, MatchResult(candidate, confidence, {"cache": 1.0}))

        self.last_status = "searching"
        api(LOGGER, "Searching Yandex Music")
        try:
            candidates = await self._search(source)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.warning("Yandex Music API unavailable: %s", _error_kind(exc))

            self._client = None
            self.last_status = "unavailable"
            return None

        match = self.matcher.best(source, candidates, self.minimum_confidence)
        if not match:
            api(LOGGER, "No reliable match")
            self.last_status = "no_match"
            return None
        api(LOGGER, "Match: %.0f%%", match.confidence * 100)
        self.last_status = "matched"
        self.cache.put(source, match.candidate, match.confidence)
        return self._to_track(source, match)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._client = None
        self._executor.shutdown(wait=False, cancel_futures=True)
