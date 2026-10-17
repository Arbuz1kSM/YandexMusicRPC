from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from media.models import (
    CoverKind,
    CoverRef,
    DataSource,
    PlaybackState,
    TrackInfo,
    detect_change,
)


class TrackModelTests(unittest.TestCase):
    def track(self, **changes) -> TrackInfo:
        base = TrackInfo(
            title="Somebody",
            artist="Artist",
            album="Album",
            duration=204.2,
            position=50,
            playback_state=PlaybackState.PLAYING,
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        return replace(base, **changes)

    def test_position_is_not_part_of_identity(self) -> None:
        self.assertEqual(self.track(position=1).identity, self.track(position=190).identity)

    def test_small_duration_correction_keeps_identity(self) -> None:
        self.assertEqual(self.track(duration=204.1).identity, self.track(duration=204.4).identity)

    def test_version_is_rendered_without_hardcoded_list(self) -> None:
        track = self.track(version="Moonlight Session 2026")
        self.assertEqual(track.display_title, "Somebody (Moonlight Session 2026)")

    def test_existing_version_is_not_duplicated(self) -> None:
        track = self.track(title="Somebody (Radio Edit)", version="Radio Edit")
        self.assertEqual(track.display_title, "Somebody (Radio Edit)")

    def test_seek_detection(self) -> None:
        previous = self.track(position=20)
        current = self.track(
            position=80,
            observed_at=previous.observed_at + timedelta(seconds=1),
        )
        self.assertTrue(detect_change(previous, current).seeked)

    def test_normal_progress_is_not_seek(self) -> None:
        previous = self.track(position=20)
        current = self.track(
            position=21.2,
            observed_at=previous.observed_at + timedelta(seconds=1),
        )
        self.assertFalse(detect_change(previous, current).seeked)

    def test_same_windows_timeline_snapshot_is_not_a_seek(self) -> None:
        metadata = {
            "windows_timeline_position": 20.0,
            "windows_timeline_marker": 1_700_000_000.0,
        }
        previous = self.track(position=20.1, metadata=metadata)
        current = self.track(
            position=25.0,
            observed_at=previous.observed_at + timedelta(seconds=5),
            metadata=metadata,
        )
        self.assertFalse(detect_change(previous, current).seeked)

    def test_new_windows_timeline_snapshot_detects_seek(self) -> None:
        previous = self.track(
            position=20,
            metadata={
                "windows_timeline_position": 20.0,
                "windows_timeline_marker": 1_700_000_000.0,
            },
        )
        current = self.track(
            position=80,
            observed_at=previous.observed_at + timedelta(seconds=1),
            metadata={
                "windows_timeline_position": 80.0,
                "windows_timeline_marker": 1_700_000_001.0,
            },
        )
        self.assertTrue(detect_change(previous, current).seeked)

    def test_realtime_merge_preserves_enrichment(self) -> None:
        enriched = self.track(
            version="Live",
            source=DataSource.WINDOWS_YANDEX,
            cover=CoverRef(CoverKind.URL, "https://example.com/cover.jpg"),
        )
        windows = self.track(position=99, playback_state=PlaybackState.PAUSED)
        merged = enriched.with_realtime(windows)
        self.assertEqual(merged.version, "Live")
        self.assertEqual(merged.position, 99)
        self.assertEqual(merged.playback_state, PlaybackState.PAUSED)


if __name__ == "__main__":
    unittest.main()
