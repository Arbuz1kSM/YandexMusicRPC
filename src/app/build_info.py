from __future__ import annotations

import json

from utils.paths import resource_path


def apply_embedded_defaults(config) -> None:

    path = resource_path("resources", "build.json")
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return
    application_id = str(values.get("discord_application_id", "")).strip()
    if application_id and not config.get("discord.application_id"):
        config.set("discord.application_id", application_id)
        activity_name = str(values.get("discord_activity_name", "")).strip()
        if activity_name:
            config.set("discord.registered_activity_name", activity_name)
