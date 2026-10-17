from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _local_app_data() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def _roaming_app_data() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


@dataclass(frozen=True, slots=True)
class AppPaths:
    config_dir: Path
    cache_dir: Path
    log_dir: Path
    config_file: Path
    track_cache_file: Path
    log_file: Path

    @classmethod
    def discover(cls) -> AppPaths:
        config_dir = _roaming_app_data() / "Arbuz1k_SM" / "YandexMusicRPC"
        state_dir = _local_app_data() / "Arbuz1k_SM" / "YandexMusicRPC"
        return cls(
            config_dir=config_dir,
            cache_dir=state_dir / "cache",
            log_dir=state_dir / "logs",
            config_file=config_dir / "config.json",
            track_cache_file=state_dir / "cache" / "tracks.json",
            log_file=state_dir / "logs" / "app.log",
        )

    def ensure(self) -> None:
        for directory in (self.config_dir, self.cache_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)


def resource_path(*parts: str) -> Path:

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parts)
