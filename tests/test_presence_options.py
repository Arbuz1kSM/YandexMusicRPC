from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from config.defaults import migrate_stored, new_defaults
from config.manager import ConfigManager
from discord.presence_builder import PresenceBuilder
from discord.rpc import DiscordRPC
from media.models import CoverKind, CoverRef, PlaybackState, TrackInfo, detect_change
from yandex.cache import TrackCache
from yandex.client import YandexMusicEnricher, candidate_from_api
from yandex.matcher import MatchResult, YandexCandidate


class PresenceOptionsTests(unittest.TestCase):
    def setUp(self):
        self.builder = PresenceBuilder(now=lambda: 1_000_000)
        self.track = TrackInfo(
            title="Песня",
            artist="Исполнитель",
            album="Альбом",
            cover=CoverRef(CoverKind.URL, "https://example.org/cover.png"),
            track_url="https://music.yandex.ru/album/10/track/20",
            artist_url="https://music.yandex.ru/artist/30",
            playback_state=PlaybackState.PLAYING,
        )
        self.config = new_defaults()
        self.config["application"]["language"] = "ru"

    def build(self, **changes):
        self.config["discord"].update(changes)
        return self.builder.build(self.track, self.config)

    def test_all_checkbox_combinations_and_independent_github_switch(self):
        for enabled in (False, True):
            for text in (False, True):
                for button in (False, True):
                    for github in (False, True):
                        with self.subTest(enabled=enabled, text=text, button=button, github=github):
                            payload = self.build(
                                music_links_enabled=enabled,
                                music_link_text=text,
                                music_link_button=button,
                                button_github=github,
                            )
                            self.assertEqual(
                                len(payload.buttons), int(enabled and button) + int(github)
                            )
                            self.assertEqual(
                                payload.details_url,
                                self.track.track_url if enabled and text else None,
                            )
                            self.assertEqual(
                                payload.state_url,
                                self.track.artist_url if enabled and text else None,
                            )

    def test_short_button_labels_in_both_languages(self):
        for language in ("ru", "en"):
            self.config["application"]["language"] = language
            payload = self.build()
            self.assertEqual(len(payload.buttons), 2)
            for button in payload.buttons:
                self.assertTrue(1 <= len(button["label"]) <= 32)
                self.assertLessEqual(len(button["label"].encode("utf-8")), 32)
                self.assertTrue(1 <= len(button["url"]) <= 512)

    def test_missing_links_preserve_activity_and_github(self):
        self.track = replace(self.track, track_url=None, artist_url=None)
        payload = self.build()
        self.assertEqual(payload.details, "Песня")
        self.assertIsNone(payload.details_url)
        self.assertIsNone(payload.state_url)
        self.assertEqual(len(payload.buttons), 1)
        self.assertIn("github.com", payload.buttons[0]["url"])

    def test_invalid_and_oversized_urls_are_not_sent(self):
        for url in ("file:///C:/secret", "http://example.org", "https://example.org/" + "a" * 512):
            with self.subTest(url=url[:30]):
                self.track = replace(self.track, track_url=url, artist_url=url)
                payload = self.build(button_github=False)
                self.assertIsNone(payload.details_url)
                self.assertIsNone(payload.state_url)
                self.assertEqual(payload.buttons, [])

    def test_cover_hover_choices(self):
        for mode, expected in [
            ("album", "Альбом"),
            ("title", "Песня"),
            ("artist", "Исполнитель"),
            ("none", None),
        ]:
            with self.subTest(mode=mode):
                self.assertEqual(self.build(cover_text_mode=mode).large_text, expected)
        self.assertEqual(
            self.build(
                cover_text_mode="custom",
                cover_text_template="{artist} • {title}",
            ).large_text,
            "Исполнитель • Песня",
        )

    def test_no_cover_has_no_hover_text_and_pause_keeps_album(self):
        self.assertIsNone(self.build(cover_mode="none").large_text)
        self.track = replace(self.track, playback_state=PlaybackState.PAUSED)
        self.assertEqual(self.build(cover_mode="track").large_text, "Альбом")

    def test_broken_hover_template_does_not_remove_activity(self):
        payload = self.build(cover_text_mode="custom", cover_text_template="{album")
        self.assertEqual(payload.details, "Песня")
        self.assertIsNone(payload.large_text)

    def test_hover_dynamic_template_updates(self):
        settings = self.config["discord"]
        settings.update(cover_text_mode="custom", cover_text_template="{time}")
        self.assertTrue(self.builder.uses_dynamic_templates(settings))

    def test_rpc_forwards_urls_into_real_pypresence_payload(self):
        from pypresence.payloads import Payload

        payload = self.build()
        rpc = DiscordRPC()
        rpc._presence = Mock()
        try:
            rpc._update_sync(payload)
            kwargs = rpc._presence.update.call_args.kwargs
            wire = Payload.set_activity(**kwargs).data["args"]["activity"]
            self.assertEqual(wire["details_url"], self.track.track_url)
            self.assertEqual(wire["state_url"], self.track.artist_url)
            self.assertEqual(wire["assets"]["large_text"], "Альбом")
            self.assertEqual(len(wire["buttons"]), 2)
        finally:
            rpc._executor.shutdown(wait=True)


class MigrationAndArtistTests(unittest.TestCase):
    def test_new_install_and_legacy_settings_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = ConfigManager(path)
            config.load()
            self.assertTrue(config.get("discord.button_github"))
            self.assertEqual(config.get("discord.cover_text_mode"), "album")
            self.assertEqual(config.get("source.mode"), "windows_yandex")
            path.write_text(
                json.dumps(
                    {
                        "first_run": True,
                        "config_version": 4,
                        "application": {"auto_connect_discord": False, "auto_start_rpc": False},
                        "discord": {
                            "button_track": False,
                            "button_github": False,
                            "title_template": "My {title}",
                        },
                    }
                )
            )
            config.load()
            stored = json.loads(path.read_text())
            self.assertNotIn("first_run", stored)
            self.assertNotIn("auto_start_rpc", stored["application"])
            self.assertNotIn("auto_connect_discord", stored["application"])
            self.assertNotIn("button_track", stored["discord"])
            self.assertFalse(stored["discord"]["music_links_enabled"])
            self.assertNotIn("track_link_mode", stored["discord"])
            self.assertFalse(stored["discord"]["button_github"])
            self.assertEqual(stored["discord"]["title_template"], "My {title}")
            self.assertEqual(migrate_stored(stored), stored)

    def test_existing_music_button_upgrades_and_new_choices_are_preserved(self):
        for mode, enabled, text, button in [
            ("button", True, False, True),
            ("text", True, True, False),
            ("both", True, True, True),
            ("none", False, True, True),
        ]:
            migrated = migrate_stored({"discord": {"track_link_mode": mode}})["discord"]
            self.assertEqual(
                (
                    migrated["music_links_enabled"],
                    migrated["music_link_text"],
                    migrated["music_link_button"],
                ),
                (enabled, text, button),
            )
        new = {
            "discord": {
                "track_link_mode": "both",
                "music_links_enabled": False,
                "music_link_text": False,
                "music_link_button": True,
            }
        }
        migrated = migrate_stored(new)["discord"]
        self.assertFalse(migrated["music_links_enabled"])
        self.assertFalse(migrated["music_link_text"])
        self.assertTrue(migrated["music_link_button"])

    def test_artist_url_survives_api_cache_enrichment_and_realtime(self):
        api = SimpleNamespace(
            id="20", title="Song", artists=[SimpleNamespace(id="30", name="Artist")], albums=[]
        )
        candidate = candidate_from_api(api)
        self.assertEqual(candidate.artist_url, "https://music.yandex.ru/artist/30")
        source = TrackInfo("Song", "Artist")
        with tempfile.TemporaryDirectory() as directory:
            cache = TrackCache(Path(directory) / "cache.json")
            cache.put(source, candidate, 1.0)
            cache.load()
            restored, confidence = cache.get(source)
            enriched = YandexMusicEnricher._to_track(source, MatchResult(restored, confidence, {}))
            merged = source.merge_enrichment(enriched).with_realtime(replace(source, position=5))
            self.assertEqual(merged.artist_url, candidate.artist_url)
            self.assertTrue(
                detect_change(
                    source, replace(source, artist_url=candidate.artist_url)
                ).metadata_changed
            )

    def test_artist_with_no_real_id_does_not_get_an_invented_url(self):
        api = SimpleNamespace(
            id="20", title="Song", artists=[SimpleNamespace(id=0, name="Unknown")], albums=[]
        )
        self.assertIsNone(candidate_from_api(api).artist_url)
        del api.artists
        self.assertIsNone(candidate_from_api(api).artist_url)

    def test_old_cached_candidate_can_be_read(self):
        old = asdict(YandexCandidate("1", "Song", "Artist"))
        del old["artist_url"]
        self.assertIsNone(YandexCandidate.from_dict(old).artist_url)


if __name__ == "__main__":
    unittest.main()
