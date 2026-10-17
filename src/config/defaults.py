from __future__ import annotations

import copy
import locale

from utils.version import PROJECT_URL

CONFIG_VERSION = 7
DEFAULT_DISCORD_APPLICATION_ID = "1539198053570060299"

DEFAULT_POLL_INTERVAL_MS = 850


def detect_language() -> str:
    language = (locale.getlocale()[0] or "").lower()
    return "ru" if language.startswith("ru") else "en"


DEFAULTS: dict = {
    "config_version": CONFIG_VERSION,
    "source": {
        "mode": "windows_yandex",
        "accept_any_media_session": False,
        "session_hints": ["yandex", "яндекс", "ru.yandex.desktop.music"],
        "poll_interval_ms": DEFAULT_POLL_INTERVAL_MS,
        "empty_metadata_grace_ms": 2500,
        "api_timeout_seconds": 7,
    },
    "discord": {
        "application_id": DEFAULT_DISCORD_APPLICATION_ID,
        "registered_activity_name": "Яндекс Музыка",
        "enabled": True,
        "compact_field": "artist",
        "compact_custom_text": "Яндекс Музыка",
        "title_template": "{title}",
        "artist_template": "{artist}",
        "album_template": "{album}",
        "show_progress": True,
        "pause_behavior": "show",
        "pause_hide_delay_seconds": 0,
        "pause_status_text": "На паузе",
        "show_pause_text": True,
        "cover_mode": "track",
        "custom_cover_url": "",
        "pause_asset_key": "pause",
        "music_links_enabled": True,
        "music_link_text": True,
        "music_link_button": True,
        "cover_text_mode": "album",
        "cover_text_template": "{artist} • {title}",
        "button_github": True,
        "github_url": PROJECT_URL,
    },
    "application": {
        "start_with_windows": False,
        "start_minimized": False,
        "close_to_tray": True,
        "language": detect_language(),
        "theme": "dark",
    },
    "logging": {
        "level": "INFO",
        "retention_days": 1,
    },
}


def new_defaults() -> dict:
    return copy.deepcopy(DEFAULTS)


def migrate_stored(stored: dict) -> dict:

    data = copy.deepcopy(stored)
    data.pop("first_run", None)
    application = data.get("application")
    if isinstance(application, dict):
        application.pop("check_updates", None)
        application.pop("auto_connect_discord", None)
        application.pop("auto_start_rpc", None)

    source = data.get("source")
    if isinstance(source, dict):
        source["poll_interval_ms"] = DEFAULT_POLL_INTERVAL_MS

    discord = data.get("discord")
    if isinstance(discord, dict):
        discord.pop("activity_type", None)
        if discord.get("compact_custom_text") == "Слушает Яндекс музыку":
            discord["compact_custom_text"] = "Яндекс Музыка"
        mode = discord.pop("track_link_mode", None)
        if mode not in {"button", "text", "both", "none"}:
            mode = "both" if discord.get("button_track", True) else "none"
        discord.setdefault("music_links_enabled", mode != "none")

        discord.setdefault("music_link_text", mode in {"text", "both", "none"})
        discord.setdefault("music_link_button", mode in {"button", "both", "none"})
        discord.pop("button_track", None)
        if "album_template" not in discord:
            discord["album_template"] = "{album}" if discord.get("show_album", True) else ""
        discord.pop("show_album", None)

        if discord.get("cover_mode") == "logo":
            discord["cover_mode"] = "track"

    logging_settings = data.get("logging")
    if isinstance(logging_settings, dict):
        logging_settings.pop("max_bytes", None)
        logging_settings.pop("backup_count", None)
        logging_settings["retention_days"] = 1

    data["config_version"] = CONFIG_VERSION
    return data


def merge_defaults(stored: dict, defaults: dict | None = None) -> dict:
    result = copy.deepcopy(DEFAULTS if defaults is None else defaults)
    for key, value in stored.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_defaults(value, result[key])
        else:
            result[key] = value
    return result
