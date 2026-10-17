from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config.manager import ConfigError, ConfigManager
from media.models import TrackInfo
from yandex.cache import TrackCache
from yandex.matcher import YandexCandidate


class ConfigTests(unittest.TestCase):
    def test_round_trip_and_default_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            manager = ConfigManager(path)
            manager.load()
            manager.set("discord.compact_field", "album")
            loaded = ConfigManager(path)
            loaded.load()
            self.assertEqual(loaded.get("discord.compact_field"), "album")
            self.assertIn("application", loaded.snapshot())

    def test_default_discord_application_id_is_bundled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = ConfigManager(Path(directory) / "config.json")
            manager.load()
            self.assertEqual(manager.get("discord.application_id"), "1539198053570060299")

    def test_legacy_update_and_album_toggle_are_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "application": {"check_updates": True},
                        "discord": {"show_album": False},
                    }
                ),
                encoding="utf-8",
            )
            manager = ConfigManager(path)
            manager.load()
            snapshot = manager.snapshot()
            self.assertNotIn("check_updates", snapshot["application"])
            self.assertNotIn("show_album", snapshot["discord"])
            self.assertEqual(snapshot["discord"]["album_template"], "")
            self.assertEqual(snapshot["config_version"], 7)

    def test_legacy_poll_interval_is_reset_to_internal_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"config_version": 2, "source": {"poll_interval_ms": 850}}),
                encoding="utf-8",
            )
            manager = ConfigManager(path)
            manager.load()
            self.assertEqual(manager.get("source.poll_interval_ms"), 850)

    def test_invalid_config_is_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            manager = ConfigManager(path)
            with self.assertRaises(ConfigError):
                manager.load()
            self.assertTrue(path.exists())
            self.assertTrue(path.with_suffix(".broken.json").exists())
            json.loads(path.read_text(encoding="utf-8"))

    def test_position_never_enters_cache_key(self) -> None:
        first = TrackInfo("A", "B", duration=100, position=1)
        second = TrackInfo("A", "B", duration=100, position=99)
        self.assertEqual(TrackCache.key(first), TrackCache.key(second))

    def test_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracks.json"
            track = TrackInfo("A", "B", album="C", duration=100)
            candidate = YandexCandidate("1:2", "A", "B", "C", 100)
            cache = TrackCache(path)
            cache.put(track, candidate, 0.98)
            restored = TrackCache(path)
            restored.load()
            result = restored.get(track)
            self.assertIsNotNone(result)
            self.assertEqual(result[0].track_id, "1:2")


if __name__ == "__main__":
    unittest.main()
