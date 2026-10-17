from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from discord.assets import is_asset_key, is_public_https, resolve_large_image
from media.models import PlaybackState, TrackInfo
from utils.text import clip_discord, safe_template

DYNAMIC_FIELDS = ("{time}", "{date}", "{volume}", "{session_time}")
DISCORD_LINK_MAX_LENGTH = 512


def _line(value: str | None) -> str | None:
    value = clip_discord(value)
    if value and len(value) == 1:
        return value + "\u200b"
    return value


def _link(value: str | None) -> str | None:
    if not is_public_https(value):
        return None
    value = str(value).strip()
    return value if len(value) <= DISCORD_LINK_MAX_LENGTH else None


def _duration_text(seconds: float | int | None) -> str:
    value = max(0, int(seconds or 0))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass(frozen=True, slots=True)
class ActivityPayload:
    status_display_type: str = "state"
    name: str | None = None
    details: str | None = None
    details_url: str | None = None
    state: str | None = None
    state_url: str | None = None
    start: int | None = None
    end: int | None = None
    large_image: str | None = None
    large_text: str | None = None
    small_image: str | None = None
    small_text: str | None = None
    buttons: list[dict[str, str]] = field(default_factory=list)


class PresenceBuilder:
    def __init__(
        self,
        now: Callable[[], float] | None = None,
        *,
        current_datetime: Callable[[], datetime] | None = None,
        volume_provider: Callable[[], int | None] | None = None,
        session_seconds_provider: Callable[[], float] | None = None,
    ) -> None:
        self._now = now or time.time
        self._current_datetime = current_datetime or datetime.now
        self._volume_provider = volume_provider or (lambda: None)
        self._session_seconds_provider = session_seconds_provider or (lambda: 0.0)

    @staticmethod
    def uses_dynamic_templates(settings: dict) -> bool:
        templates = (
            str(settings.get("title_template", "")),
            str(settings.get("artist_template", "")),
            str(settings.get("album_template", "")),
            str(settings.get("cover_text_template", ""))
            if settings.get("cover_text_mode") == "custom"
            else "",
        )
        return any(marker in template for marker in DYNAMIC_FIELDS for template in templates)

    def _values(self, track: TrackInfo, template: str, language: str) -> dict[str, str]:

        title_value = track.title if "{version}" in template else track.display_title
        now = self._current_datetime()
        volume = self._volume_provider() if "{volume}" in template else None
        date_text = now.strftime("%d.%m.%Y") if language == "ru" else now.strftime("%Y-%m-%d")
        return {
            "title": title_value,
            "artist": track.artist,
            "album": track.album or "",
            "version": track.version or "",
            "time": now.strftime("%H:%M"),
            "date": date_text,
            "volume": f"{volume}%" if volume is not None else "?",
            "session_time": _duration_text(self._session_seconds_provider()),
        }

    def _render(self, template: str, track: TrackInfo, language: str) -> str:
        return safe_template(template, self._values(track, template, language))

    def _card_lines(
        self, track: TrackInfo, settings: dict, language: str
    ) -> tuple[str, str, str, str, str]:
        title_template = str(settings.get("title_template", "{title}"))
        artist_template = str(settings.get("artist_template", "{artist}"))
        album_template = str(settings.get("album_template", "{album}"))

        title = self._render(title_template, track, language) or track.display_title
        artist = self._render(artist_template, track, language) or track.artist
        album = self._render(album_template, track, language) if album_template else ""
        compact = settings.get("compact_field", "artist")

        details = title
        state = artist
        activity_name = settings.get("registered_activity_name") or "Yandex Music"
        display_type = "state"
        if compact == "title":
            display_type = "details"
        elif compact == "album" and album:
            activity_name = album
            display_type = "name"
        elif compact == "custom":
            activity_name = settings.get("compact_custom_text") or "Listening to music"
            display_type = "name"
        return details, state, album, activity_name, display_type

    def build(self, track: TrackInfo, config: dict) -> ActivityPayload:
        settings = config.get("discord", config)
        language = config.get("application", {}).get("language", "ru")
        details, state, album_line, activity_name, display_type = self._card_lines(
            track, settings, language
        )

        paused = track.playback_state == PlaybackState.PAUSED
        pause_text = settings.get("pause_status_text", "Paused")
        start = end = None
        if (
            settings.get("show_progress", True)
            and track.playback_state == PlaybackState.PLAYING
            and track.position is not None
            and track.duration is not None
            and track.duration > 0
        ):
            now = int(self._now())
            position = max(0.0, min(track.position, track.duration))
            start = int(now - position)
            end = int(start + track.duration)

        large_image = resolve_large_image(track, settings)
        hover_mode = settings.get("cover_text_mode", "album")
        hover_text = {
            "album": album_line,
            "title": track.display_title,
            "artist": track.artist,
        }.get(hover_mode)
        if hover_mode == "custom":
            hover_text = self._render(
                str(settings.get("cover_text_template", "{artist} • {title}")), track, language
            )
        large_text = hover_text if large_image else None
        small_image = None
        small_text = None
        if paused:
            pause_key = settings.get("pause_asset_key")
            if is_asset_key(pause_key):
                small_image = pause_key.strip()
            if settings.get("show_pause_text", True):
                small_text = pause_text

        links_enabled = settings.get("music_links_enabled", True)
        track_url = _link(track.track_url)
        text_links = links_enabled and settings.get("music_link_text", True)
        details_url = track_url if text_links else None
        state_url = _link(track.artist_url) if text_links else None
        buttons: list[dict[str, str]] = []
        track_label = "Открыть в ЯМузыке" if language == "ru" else "Open in Yandex Music"
        if links_enabled and settings.get("music_link_button", True) and track_url:
            buttons.append({"label": track_label, "url": track_url})

        github = settings.get("github_url")
        github_label = "GitHub проекта" if language == "ru" else "Project GitHub"
        if settings.get("button_github", True) and (github_url := _link(github)):
            buttons.append({"label": github_label, "url": github_url})

        return ActivityPayload(
            status_display_type=display_type,
            name=_line(activity_name),
            details=_line(details),
            details_url=details_url,
            state=_line(state),
            state_url=state_url,
            start=start,
            end=end,
            large_image=large_image,
            large_text=_line(large_text),
            small_image=small_image,
            small_text=_line(small_text),
            buttons=buttons[:2],
        )
