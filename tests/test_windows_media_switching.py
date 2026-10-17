from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from media.models import CoverKind, CoverRef
from media.windows_media import WindowsMediaSource


class _Session:
    source_app_user_model_id = "ru.yandex.desktop.music"

    def __init__(self) -> None:
        self.thumbnail = object()

    async def try_get_media_properties_async(self):
        return SimpleNamespace(
            title="New Track",
            artist="Artist",
            album_title="Album",
            album_artist="Artist",
            thumbnail=self.thumbnail,
        )

    def get_playback_info(self):
        return SimpleNamespace(playback_status="Playing")

    def get_timeline_properties(self):
        return SimpleNamespace(
            position=timedelta(seconds=1),
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=180),
            last_updated_time=datetime.now(UTC),
        )


class _Manager:
    def __init__(self, session) -> None:
        self.session = session

    def get_sessions(self):
        return [self.session]

    def get_current_session(self):
        return self.session


class WindowsMediaSwitchingTests(unittest.IsolatedAsyncioTestCase):
    async def test_hanging_thumbnail_does_not_delay_new_track(self) -> None:
        source = WindowsMediaSource(session_hints=["ru.yandex.desktop.music"])
        source._manager = _Manager(_Session())
        started = asyncio.Event()

        async def hanging_thumbnail(_reference):
            started.set()
            await asyncio.sleep(30)
            return CoverRef(CoverKind.BYTES, b"never")

        source._read_thumbnail = hanging_thumbnail
        track = await asyncio.wait_for(source.sample(), timeout=0.25)

        self.assertEqual(track.title, "New Track")
        self.assertEqual(track.artist, "Artist")
        self.assertEqual(track.cover.kind, CoverKind.NONE)
        await asyncio.wait_for(started.wait(), timeout=0.25)
        await source.close()


if __name__ == "__main__":
    unittest.main()
