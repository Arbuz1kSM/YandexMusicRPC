from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def run() -> int:

    sys._yandex_rpc_launcher = str(Path(__file__).resolve().parents[1] / "YandexMusicRPC.exe")
    from main import main

    return main()


def report_startup_error() -> None:
    directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Arbuz1k_SM/YandexMusicRPC/logs"
    path = directory / "startup-error.log"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(traceback.format_exc(), encoding="utf-8")
        message = f"Не удалось запустить Yandex Music RPC.\nПодробности ошибки: {path}"
    except OSError:
        message = "Не удалось запустить Yandex Music RPC. Попробуйте переустановить приложение."
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "Yandex Music RPC", 0x10)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception:
        report_startup_error()
        raise SystemExit(1) from None
