from __future__ import annotations

from urllib.parse import urlparse

from media.models import CoverKind, TrackInfo

DISCORD_IMAGE_MAX_LENGTH = 300


def is_public_https(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def is_asset_key(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip()
    return 1 <= len(value) <= 300 and all(char not in value for char in "/\\:")


def _discord_cover_url(value: str | None) -> str | None:
    if not is_public_https(value):
        return None
    source = value.strip()
    return source if len(source) <= DISCORD_IMAGE_MAX_LENGTH else None


def resolve_large_image(track: TrackInfo, settings: dict) -> str | None:
    mode = settings.get("cover_mode", "track")
    if mode == "none":
        return None
    if mode == "custom":
        return _discord_cover_url(settings.get("custom_cover_url"))
    if track.cover.kind == CoverKind.URL and isinstance(track.cover.value, str):
        return _discord_cover_url(track.cover.value)
    return None
