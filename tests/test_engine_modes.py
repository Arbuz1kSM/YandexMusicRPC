from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from app.engine import ApplicationEngine
from config.manager import ConfigManager
from discord.presence_builder import PresenceBuilder
from discord.rpc import DiscordStatus
from media.models import PlaybackState, TrackInfo
from utils.paths import AppPaths


def _paths(root: Path) -> AppPaths:
    return AppPaths(
        config_dir=root / "config",
        cache_dir=root / "cache",
        log_dir=root / "logs",
        config_file=root / "config" / "config.json",
        track_cache_file=root / "cache" / "tracks.json",
        log_file=root / "logs" / "app.log",
    )


class EngineModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_windows_only_never_reads_yandex_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _paths(Path(directory))
            config = ConfigManager(paths.config_file)
            config.load()
            config.set("source.mode", "windows")
            engine = ApplicationEngine(config, paths)

            def unexpected_token_read():
                raise AssertionError("Windows-only mode touched Yandex credentials")

            engine.credentials.get_token = unexpected_token_read
            await engine._rebuild_enricher()
            self.assertIsNone(engine.enricher)
            await engine.stop()

    async def test_removed_startup_flags_no_longer_block_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _paths(Path(directory))
            config = ConfigManager(paths.config_file)
            config.load()
            config.set("application.auto_connect_discord", False)
            config.set("application.auto_start_rpc", False)
            engine = ApplicationEngine(config, paths)
            engine._connect_supervisor = AsyncMock()
            engine._running = True
            engine._schedule_reconnect()
            self.assertTrue(engine.rpc_enabled)
            self.assertIsNotNone(engine._connect_task)
            await engine._connect_task
            engine._connect_supervisor.assert_awaited_once()
            await engine.stop()

    async def test_identical_presence_is_not_sent_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _paths(Path(directory))
            config = ConfigManager(paths.config_file)
            config.load()
            engine = ApplicationEngine(config, paths)
            engine.builder = PresenceBuilder(now=lambda: 1_000_000)
            engine.current = TrackInfo(
                "Title",
                "Artist",
                duration=180,
                position=30,
                playback_state=PlaybackState.PLAYING,
            )
            engine.discord.status = DiscordStatus.CONNECTED
            engine.discord.update = AsyncMock()

            await engine._publish()
            await engine._publish()

            self.assertEqual(engine.discord.update.await_count, 1)
            await engine.stop()


if __name__ == "__main__":
    unittest.main()
