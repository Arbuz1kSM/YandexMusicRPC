from __future__ import annotations

import unittest

from media.models import TrackInfo
from yandex.matcher import TrackMatcher, YandexCandidate, split_terminal_qualifier


class MatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = TrackMatcher()

    def source(self, **changes) -> TrackInfo:
        values = dict(
            title="Somebody",
            artist="Depeche Mode",
            album="The Singles",
            duration=240,
        )
        values.update(changes)
        return TrackInfo(**values)

    def candidate(self, **changes) -> YandexCandidate:
        values = dict(
            track_id="1:2",
            title="Somebody",
            artist="Depeche Mode",
            album="The Singles",
            duration=240,
        )
        values.update(changes)
        return YandexCandidate(**values)

    def test_exact_match_is_high_confidence(self) -> None:
        result = self.matcher.best(self.source(), [self.candidate()])
        self.assertIsNotNone(result)
        self.assertGreater(result.confidence, 0.98)

    def test_arbitrary_version_is_preserved_and_matched(self) -> None:
        source = self.source(title="Somebody (Midnight Balcony Cut)", duration=211)
        candidates = [
            self.candidate(track_id="wrong", version="Radio Edit", duration=211),
            self.candidate(track_id="right", version="Midnight Balcony Cut", duration=211),
        ]
        result = self.matcher.best(source, candidates)
        self.assertEqual(result.candidate.track_id, "right")

    def test_duration_disambiguates_same_title_versions(self) -> None:
        source = self.source(album=None, duration=181)
        candidates = [
            self.candidate(track_id="long", album="Other", duration=310),
            self.candidate(track_id="short", album="Other", duration=182),
        ]
        result = self.matcher.best(source, candidates)
        self.assertEqual(result.candidate.track_id, "short")

    def test_album_disambiguates_when_duration_missing(self) -> None:
        source = self.source(duration=None, album="Acoustic Nights")
        candidates = [
            self.candidate(track_id="wrong", duration=None, album="Greatest Hits"),
            self.candidate(track_id="right", duration=None, album="Acoustic Nights"),
        ]
        result = self.matcher.best(source, candidates)
        self.assertEqual(result.candidate.track_id, "right")

    def test_wrong_artist_is_rejected(self) -> None:
        result = self.matcher.best(
            self.source(),
            [self.candidate(artist="Completely Different Person")],
        )
        self.assertIsNone(result)

    def test_empty_candidates(self) -> None:
        self.assertIsNone(self.matcher.best(self.source(), []))

    def test_unicode_and_punctuation(self) -> None:
        source = self.source(title="Ёлка - Live!", artist="ЛСП & PHARAOH")
        candidate = self.candidate(title="Ёлка Live", artist="ЛСП, PHARAOH", album="The Singles")
        self.assertIsNotNone(self.matcher.best(source, [candidate], 0.6))

    def test_qualifier_parser_is_generic(self) -> None:
        base, version = split_terminal_qualifier("Track [Orchestral Dawn Take]")
        self.assertEqual(base, "Track")
        self.assertEqual(version, "Orchestral Dawn Take")


if __name__ == "__main__":
    unittest.main()
