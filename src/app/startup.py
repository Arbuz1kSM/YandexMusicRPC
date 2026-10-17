from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ArbuzYandexMusicRPC"


def _command(executable: Path | None = None) -> str:
    executable = executable or Path(getattr(sys, "_yandex_rpc_launcher", sys.executable))
    return f'"{executable}" --minimized'


def set_start_with_windows(enabled: bool, executable: Path | None = None) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command(executable))
            else:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, VALUE_NAME)
        return True
    except OSError as exc:
        LOGGER.warning("Could not change Windows startup: %s", type(exc).__name__)
        return False


def is_start_with_windows_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False
