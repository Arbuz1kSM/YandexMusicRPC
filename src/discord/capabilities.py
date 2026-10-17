from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscordCapabilities:
    compact_field_selection: bool = True
    external_https_assets: bool = True
    local_file_assets: bool = False
    runtime_activity_name: bool = False
    buttons: bool = True
    pause_timestamps: bool = True


CAPABILITIES = DiscordCapabilities()
