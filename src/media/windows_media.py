from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from media.models import CoverKind, CoverRef, DataSource, PlaybackState, TrackInfo
from utils.logging import media
from utils.text import normalize_text

LOGGER = logging.getLogger(__name__)


class WindowsMediaUnavailable(RuntimeError):
    pass


def _seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value.total_seconds()))
    except (AttributeError, TypeError, ValueError):
        return None


def _playback_state(status: Any) -> PlaybackState:
    name = str(getattr(status, "name", status)).casefold()
    if "playing" in name:
        return PlaybackState.PLAYING
    if "paused" in name:
        return PlaybackState.PAUSED
    if "stopped" in name or "closed" in name:
        return PlaybackState.STOPPED
    return PlaybackState.UNKNOWN


def _utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class WindowsMediaSource:
    def __init__(
        self,
        session_hints: list[str] | None = None,
        accept_any_session: bool = False,
    ) -> None:
        self.session_hints = [normalize_text(item) for item in (session_hints or [])]
        self.accept_any_session = accept_any_session
        self._manager = None
        self._active_session_id: str | None = None
        self._thumbnail_key: tuple[str, str] | None = None
        self._thumbnail = CoverRef.none()
        self._thumbnail_task: asyncio.Task | None = None

    async def start(self) -> None:
        if sys.platform != "win32":
            raise WindowsMediaUnavailable("Windows Media Control requires Windows 10/11")
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager,
            )

            self._manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        except Exception as exc:
            raise WindowsMediaUnavailable(str(exc)) from exc
        LOGGER.info("Windows Media Control connected")

    @staticmethod
    def _session_id(session: Any) -> str:
        return str(getattr(session, "source_app_user_model_id", "") or "")

    def _matches(self, session: Any) -> bool:
        if self.accept_any_session:
            return True
        source = normalize_text(self._session_id(session))
        return any(hint and hint in source for hint in self.session_hints)

    def _select_session(self) -> Any | None:
        if self._manager is None:
            return None
        sessions = list(self._manager.get_sessions() or [])
        matching = [session for session in sessions if self._matches(session)]
        if not matching:
            return None

        playing = []
        for session in matching:
            try:
                if (
                    _playback_state(session.get_playback_info().playback_status)
                    == PlaybackState.PLAYING
                ):
                    playing.append(session)
            except Exception:
                continue

        current = self._manager.get_current_session()
        if playing:
            if current is not None and current in playing:
                return current
            return playing[0]
        if current is not None and current in matching:
            return current
        return matching[0]

    async def _read_thumbnail(self, thumbnail_reference: Any) -> CoverRef:
        if thumbnail_reference is None:
            return CoverRef.none()
        try:
            from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions

            stream = await thumbnail_reference.open_read_async()
            capacity = min(max(int(getattr(stream, "size", 0) or 0), 64 * 1024), 8_000_000)
            buffer = Buffer(capacity)
            loaded = await stream.read_async(buffer, buffer.capacity, InputStreamOptions.READ_AHEAD)
            reader = DataReader.from_buffer(loaded)
            length = int(loaded.length)
            target = bytearray(length)
            try:
                reader.read_bytes(target)
                data = bytes(target)
            except TypeError:
                data = bytes(reader.read_bytes(length))
            if not data:
                return CoverRef.none()
            mime = str(getattr(stream, "content_type", "") or "") or None
            return CoverRef(CoverKind.BYTES, data, mime)
        except Exception as exc:
            LOGGER.debug("SMTC thumbnail unavailable: %s", type(exc).__name__)
            return CoverRef.none()

    def _start_thumbnail_load(self, key: tuple[str, str], thumbnail_reference: Any) -> None:

        if self._thumbnail_task and not self._thumbnail_task.done():
            self._thumbnail_task.cancel()

        self._thumbnail_key = key
        self._thumbnail = CoverRef.none()
        if thumbnail_reference is None:
            self._thumbnail_task = None
            return

        async def load() -> None:
            try:
                cover = await asyncio.wait_for(
                    self._read_thumbnail(thumbnail_reference), timeout=2.0
                )
            except asyncio.CancelledError:
                return
            except TimeoutError:
                LOGGER.debug("SMTC thumbnail timed out")
                return
            if self._thumbnail_key == key:
                self._thumbnail = cover

        self._thumbnail_task = asyncio.create_task(load(), name="windows-media-thumbnail")

    async def sample(self) -> TrackInfo | None:
        if self._manager is None:
            await self.start()
        session = self._select_session()
        if session is None:
            self._active_session_id = None
            return None

        session_id = self._session_id(session)
        if session_id != self._active_session_id:
            self._active_session_id = session_id
            LOGGER.info("Media session: %s", session_id)
        try:
            properties = await session.try_get_media_properties_async()
            playback = session.get_playback_info()
            timeline = session.get_timeline_properties()
        except Exception as exc:
            LOGGER.warning("Windows Media Control read failed: %s", type(exc).__name__)
            return None

        title = str(getattr(properties, "title", "") or "").strip()
        artist = str(getattr(properties, "artist", "") or "").strip()
        if not title and not artist:
            return None
        album = str(getattr(properties, "album_title", "") or "").strip() or None
        album_artist = str(getattr(properties, "album_artist", "") or "").strip()
        if not artist:
            artist = album_artist

        observed_at = datetime.now(UTC)
        raw_position = _seconds(getattr(timeline, "position", None))
        start_time = _seconds(getattr(timeline, "start_time", None)) or 0.0
        end_time = _seconds(getattr(timeline, "end_time", None))
        duration = max(0.0, end_time - start_time) if end_time else None
        state = _playback_state(getattr(playback, "playback_status", None))
        timeline_updated = _utc_datetime(getattr(timeline, "last_updated_time", None))
        position = raw_position
        if (
            raw_position is not None
            and timeline_updated is not None
            and state == PlaybackState.PLAYING
        ):
            age = max(0.0, (observed_at - timeline_updated).total_seconds())
            maximum_age = max(600.0, (duration or 0.0) + 60.0)
            if age <= maximum_age:
                position = raw_position + age
        if position is not None and duration:
            position = min(position, duration)

        thumbnail_key = (normalize_text(title), normalize_text(artist))
        if thumbnail_key != self._thumbnail_key:
            media(LOGGER, "%s - %s", artist or "?", title or "?")
            self._start_thumbnail_load(thumbnail_key, getattr(properties, "thumbnail", None))

        return TrackInfo(
            title=title or "Unknown title",
            artist=artist or "Unknown artist",
            album=album,
            duration=duration,
            position=position,
            playback_state=state,
            cover=self._thumbnail,
            source=DataSource.WINDOWS,
            session_id=session_id,
            observed_at=observed_at,
            metadata={
                "windows_timeline_position": raw_position,
                "windows_timeline_marker": (
                    timeline_updated.timestamp() if timeline_updated else None
                ),
            },
        )

    async def close(self) -> None:
        task = self._thumbnail_task
        if task and not task.done():
            task.cancel()
        self._thumbnail_task = None
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        self._manager = None
        self._active_session_id = None
