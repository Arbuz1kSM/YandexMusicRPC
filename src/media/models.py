from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from utils.text import normalize_text


class PlaybackState(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class DataSource(StrEnum):
    WINDOWS = "windows"
    WINDOWS_YANDEX = "windows_yandex"


class CoverKind(StrEnum):
    NONE = "none"
    BYTES = "bytes"
    URL = "url"
    LOCAL_FILE = "local_file"
    ASSET_KEY = "asset_key"


@dataclass(frozen=True, slots=True)
class CoverRef:
    kind: CoverKind = CoverKind.NONE
    value: str | bytes | None = None
    mime_type: str | None = None

    @classmethod
    def none(cls) -> CoverRef:
        return cls()


@dataclass(frozen=True, slots=True)
class TrackIdentity:
    title: str
    artist: str
    duration_bucket: int | None


@dataclass(frozen=True, slots=True)
class TrackInfo:
    title: str
    artist: str
    album: str | None = None
    version: str | None = None
    subtitle: str | None = None
    duration: float | None = None
    position: float | None = None
    playback_state: PlaybackState = PlaybackState.UNKNOWN
    cover: CoverRef = field(default_factory=CoverRef.none)
    track_url: str | None = None
    source: DataSource = DataSource.WINDOWS
    session_id: str | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    match_confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
    artist_url: str | None = None

    @property
    def identity(self) -> TrackIdentity:

        bucket = round(self.duration) if self.duration and self.duration > 0 else None
        return TrackIdentity(normalize_text(self.title), normalize_text(self.artist), bucket)

    @property
    def display_title(self) -> str:
        if self.version and normalize_text(self.version) not in normalize_text(self.title):
            return f"{self.title} ({self.version})"
        return self.title

    @property
    def is_playing(self) -> bool:
        return self.playback_state == PlaybackState.PLAYING

    def with_realtime(self, realtime: TrackInfo) -> TrackInfo:

        cover = self.cover
        if cover.kind == CoverKind.NONE and realtime.cover.kind != CoverKind.NONE:
            cover = realtime.cover
        return replace(
            self,
            position=realtime.position,
            duration=realtime.duration or self.duration,
            playback_state=realtime.playback_state,
            session_id=realtime.session_id,
            observed_at=realtime.observed_at,
            cover=cover,
            metadata={**self.metadata, **realtime.metadata},
        )

    def merge_enrichment(self, enriched: TrackInfo) -> TrackInfo:
        return replace(
            self,
            title=enriched.title or self.title,
            artist=enriched.artist or self.artist,
            album=enriched.album or self.album,
            version=enriched.version or self.version,
            subtitle=enriched.subtitle or self.subtitle,
            duration=self.duration or enriched.duration,
            cover=enriched.cover if enriched.cover.kind != CoverKind.NONE else self.cover,
            track_url=enriched.track_url or self.track_url,
            artist_url=enriched.artist_url or self.artist_url,
            source=DataSource.WINDOWS_YANDEX,
            match_confidence=enriched.match_confidence,
            metadata={**self.metadata, **enriched.metadata},
        )


@dataclass(frozen=True, slots=True)
class TrackChange:
    track_changed: bool = False
    playback_changed: bool = False
    seeked: bool = False
    metadata_changed: bool = False

    @property
    def should_update_presence(self) -> bool:
        return any((self.track_changed, self.playback_changed, self.seeked, self.metadata_changed))


def detect_change(previous: TrackInfo | None, current: TrackInfo) -> TrackChange:
    if previous is None or previous.identity != current.identity:
        return TrackChange(track_changed=True)
    playback_changed = previous.playback_state != current.playback_state
    metadata_changed = any(
        (
            previous.album != current.album,
            previous.version != current.version,
            previous.track_url != current.track_url,
            previous.artist_url != current.artist_url,
            previous.cover != current.cover,
        )
    )
    seeked = False
    previous_marker = previous.metadata.get("windows_timeline_marker")
    current_marker = current.metadata.get("windows_timeline_marker")
    previous_raw = previous.metadata.get("windows_timeline_position")
    current_raw = current.metadata.get("windows_timeline_position")
    if all(
        isinstance(value, (int, float))
        for value in (previous_marker, current_marker, previous_raw, current_raw)
    ):
        if current_marker != previous_marker:
            marker_elapsed = max(0.0, float(current_marker) - float(previous_marker))
            expected = float(previous_raw)
            if previous.playback_state == PlaybackState.PLAYING:
                expected += marker_elapsed
            seeked = abs(float(current_raw) - expected) >= 3.0
    elif (
        previous.position is not None
        and current.position is not None
        and previous.playback_state == PlaybackState.PLAYING
    ):
        elapsed = max(0.0, (current.observed_at - previous.observed_at).total_seconds())
        expected = previous.position + elapsed
        seeked = abs(current.position - expected) >= 3.0
    return TrackChange(
        playback_changed=playback_changed,
        seeked=seeked,
        metadata_changed=metadata_changed,
    )
