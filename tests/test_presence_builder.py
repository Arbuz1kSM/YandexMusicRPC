from __future__ import annotations

import unittest

from discord.assets import resolve_large_image
from discord.presence_builder import PresenceBuilder
from media.models import CoverKind, CoverRef, PlaybackState, TrackInfo


class PresenceBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = PresenceBuilder(now=lambda: 1_000_000)
        self.track = TrackInfo(
            title="Шиншиллы",
            artist="ЛСП",
            album="Magic City",
            duration=204,
            position=97,
            playback_state=PlaybackState.PLAYING,
            cover=CoverRef(CoverKind.URL, "https://example.com/cover.jpg"),
            track_url="https://music.yandex.ru/album/1/track/2",
        )
        self.settings = {
            "registered_activity_name": "Яндекс Музыка",
            "compact_field": "artist",
            "compact_custom_text": "Кайфует",
            "title_template": "{title}",
            "artist_template": "{artist}",
            "album_template": "{album}",
            "show_progress": True,
            "show_pause_text": True,
            "pause_status_text": "На паузе",
            "pause_asset_key": "pause",
            "cover_mode": "track",
            "music_link_text": False,
            "music_link_button": True,
            "button_github": False,
        }

    def build(self, **changes):
        settings = {**self.settings, **changes}
        return self.builder.build(self.track, {"discord": settings})

    def test_windows_position_builds_timestamps(self) -> None:
        payload = self.build()
        self.assertEqual(payload.start, 1_000_000 - 97)
        self.assertEqual(payload.end, 1_000_000 - 97 + 204)

    def test_artist_compact_uses_state(self) -> None:
        payload = self.build(compact_field="artist")
        self.assertEqual(payload.status_display_type, "state")
        self.assertEqual(payload.details, "Шиншиллы")
        self.assertEqual(payload.state, "ЛСП")
        self.assertEqual(payload.large_text, "Magic City")

    def test_title_compact_uses_details(self) -> None:
        payload = self.build(compact_field="title")
        self.assertEqual(payload.status_display_type, "details")

    def test_album_compact_preserves_fixed_card_lines(self) -> None:
        payload = self.build(compact_field="album")
        self.assertEqual(payload.status_display_type, "name")
        self.assertEqual(payload.name, "Magic City")
        self.assertEqual(payload.details, "Шиншиллы")
        self.assertEqual(payload.state, "ЛСП")

    def test_custom_compact_does_not_move_artist(self) -> None:
        payload = self.build(compact_field="custom", compact_custom_text="Кайфует")
        self.assertEqual(payload.status_display_type, "name")
        self.assertEqual(payload.name, "Кайфует")
        self.assertEqual(payload.details, "Шиншиллы")
        self.assertEqual(payload.state, "ЛСП")

    def test_pause_stops_timer(self) -> None:
        from dataclasses import replace

        paused = replace(self.track, playback_state=PlaybackState.PAUSED)
        payload = self.builder.build(paused, {"discord": self.settings})
        self.assertIsNone(payload.start)
        self.assertIsNone(payload.end)
        self.assertEqual(payload.small_image, "pause")
        self.assertEqual(payload.small_text, "На паузе")
        self.assertEqual(payload.state, "ЛСП")

    def test_missing_album_does_not_break_card(self) -> None:
        from dataclasses import replace

        payload = self.builder.build(replace(self.track, album=None), {"discord": self.settings})
        self.assertEqual(payload.state, "ЛСП")
        self.assertIsNone(payload.large_text)

    def test_empty_album_template_removes_album_without_rearranging_lines(self) -> None:
        payload = self.build(album_template="")
        self.assertEqual(payload.details, "Шиншиллы")
        self.assertEqual(payload.state, "ЛСП")
        self.assertIsNone(payload.large_text)

    def test_external_cover_url_is_used(self) -> None:
        self.assertEqual(self.build().large_image, "https://example.com/cover.jpg")

    def test_yandex_cover_is_sent_directly(self) -> None:
        from dataclasses import replace

        source = "https://avatars.yandex.net/get-music-content/123/cover/400x400"
        self.track = replace(self.track, cover=CoverRef(CoverKind.URL, source))
        payload = self.build()
        self.assertEqual(payload.large_image, source)

    def test_non_yandex_external_cover_stays_direct(self) -> None:
        self.assertEqual(self.build().large_image, "https://example.com/cover.jpg")

    def test_local_windows_bytes_do_not_send_an_unknown_asset(self) -> None:
        from dataclasses import replace

        track = replace(self.track, cover=CoverRef(CoverKind.BYTES, b"jpeg"))
        payload = self.builder.build(track, {"discord": self.settings})
        self.assertIsNone(payload.large_image)

    def test_custom_cover_only_accepts_https_url(self) -> None:
        settings = {
            **self.settings,
            "cover_mode": "custom",
            "custom_cover_url": "https://example.com/custom.png",
        }
        self.assertEqual(
            resolve_large_image(self.track, settings), "https://example.com/custom.png"
        )

    def test_custom_cover_rejects_local_path(self) -> None:
        settings = {
            **self.settings,
            "cover_mode": "custom",
            "custom_cover_url": r"C:\\covers\\secret.png",
        }
        self.assertIsNone(resolve_large_image(self.track, settings))

    def test_legacy_logo_mode_falls_back_to_track_cover(self) -> None:
        self.assertEqual(self.build(cover_mode="logo").large_image, "https://example.com/cover.jpg")

    def test_explicit_version_placeholder_uses_raw_title_once(self) -> None:
        from dataclasses import replace

        track = replace(self.track, title="Song", version="Radio Edit")
        settings = {**self.settings, "title_template": "{title} - {version}"}
        payload = self.builder.build(track, {"discord": settings})
        self.assertEqual(payload.details, "Song - Radio Edit")

    def test_album_placeholder_uses_enriched_album(self) -> None:
        settings = {**self.settings, "artist_template": "{artist} - {album}"}
        payload = self.builder.build(self.track, {"discord": settings})
        self.assertEqual(payload.state, "ЛСП - Magic City")

    def test_track_link_uses_visible_yandex_button(self) -> None:
        payload = self.build()
        self.assertIsNone(payload.details_url)
        self.assertEqual(
            payload.buttons,
            [{"label": "Открыть в ЯМузыке", "url": "https://music.yandex.ru/album/1/track/2"}],
        )

    def test_disabled_track_link_has_no_yandex_button(self) -> None:
        payload = self.build(music_links_enabled=False)
        self.assertIsNone(payload.details_url)
        self.assertEqual(payload.buttons, [])

    def test_dynamic_template_fields_are_rendered(self) -> None:
        from datetime import datetime

        builder = PresenceBuilder(
            now=lambda: 1_000_000,
            current_datetime=lambda: datetime(2026, 8, 22, 18, 45),
            volume_provider=lambda: 42,
            session_seconds_provider=lambda: 3661,
        )
        settings = {
            **self.settings,
            "title_template": "{title} | {time} | {volume}",
            "artist_template": "{artist} | {date}",
            "album_template": "{album} | {session_time}",
        }
        payload = builder.build(
            self.track,
            {"discord": settings, "application": {"language": "ru"}},
        )
        self.assertEqual(payload.details, "Шиншиллы | 18:45 | 42%")
        self.assertEqual(payload.state, "ЛСП | 22.08.2026")
        self.assertEqual(payload.large_text, "Magic City | 01:01:01")


if __name__ == "__main__":
    unittest.main()
