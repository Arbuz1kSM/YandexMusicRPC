from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from media.models import TrackInfo
from utils.text import redact_secrets, safe_template
from yandex.cache import TrackCache
from yandex.client import YandexMusicEnricher, candidate_from_api


class TextAndMappingTests(unittest.TestCase):
    def test_unknown_template_field_is_rejected(self) -> None:
        result = safe_template("{title} {password}", {"title": "Track"})
        self.assertEqual(result, "")

    def test_dynamic_template_fields_are_allowed(self) -> None:
        result = safe_template(
            "{time} {date} {volume} {session_time}",
            {"time": "18:45", "date": "22.08.2026", "volume": "42%", "session_time": "01:02"},
        )
        self.assertEqual(result, "18:45 22.08.2026 42% 01:02")

    def test_secret_is_redacted(self) -> None:
        message = redact_secrets("access_token=AQAAAA-secret")
        self.assertNotIn("AQAAAA-secret", message)

    def test_yandex_mapping_reads_both_version_fields(self) -> None:
        track = SimpleNamespace(
            id="12",
            title="Track",
            artists=[SimpleNamespace(name="Artist")],
            albums=[SimpleNamespace(id="34", title="Album")],
            duration_ms=123000,
            version=None,
            meta_data=SimpleNamespace(version="Obscure Sunrise Cut"),
            subtitle=None,
            cover_uri="avatars.yandex.net/example/%%",
        )
        result = candidate_from_api(track)
        self.assertEqual(result.version, "Obscure Sunrise Cut")
        self.assertEqual(result.duration, 123)
        self.assertTrue(result.cover_url.startswith("https://"))
        self.assertIn("/album/34/track/12", result.track_url)


class ApiTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_client_search_is_used_without_proxy_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            enricher = YandexMusicEnricher(TrackCache(Path(directory) / "cache.json"))
            source = TrackInfo("Track", "Artist", duration=123)
            api_track = SimpleNamespace(
                id="12",
                title="Track",
                artists=[SimpleNamespace(name="Artist")],
                albums=[SimpleNamespace(id="34", title="Album")],
                duration_ms=123000,
                version="Radio Edit",
                meta_data=None,
                subtitle=None,
                og_image="avatars.yandex.net/example/%%",
                cover_uri=None,
            )
            fake_client = SimpleNamespace(
                search=lambda *args, **kwargs: SimpleNamespace(
                    tracks=SimpleNamespace(results=[api_track])
                )
            )
            enricher._ensure_client_blocking = lambda: fake_client

            result = await enricher.enrich(source)

            self.assertIsNotNone(result)
            self.assertEqual(result.album, "Album")
            self.assertEqual(result.version, "Radio Edit")
            self.assertEqual(result.cover.value, "https://avatars.yandex.net/example/400x400")
            enricher.close()

    async def test_api_failure_does_not_break_windows_track(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            enricher = YandexMusicEnricher(TrackCache(Path(directory) / "cache.json"))
            source = TrackInfo("Track", "Artist", duration=123)

            async def broken_search(_source):
                raise OSError("blocked")

            enricher._search = broken_search
            result = await enricher.enrich(source)

            self.assertIsNone(result)
            self.assertEqual(enricher.last_status, "unavailable")
            enricher.close()


if __name__ == "__main__":
    unittest.main()
