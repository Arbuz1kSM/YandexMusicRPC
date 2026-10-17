from __future__ import annotations

import argparse
import asyncio
import contextlib
import ctypes
import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from qasync import QEventLoop

from app.application import ApplicationController
from app.build_info import apply_embedded_defaults
from app.tray import TrayIcon
from config.manager import ConfigError, ConfigManager
from localization.translator import I18n
from ui.main_window import MainWindow
from utils.logging import configure_logging
from utils.paths import AppPaths, resource_path
from utils.version import APP_NAME, APP_VERSION

LOGGER = logging.getLogger(__name__)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--minimized", action="store_true")
    return parser.parse_known_args()[0]


def _set_windows_identity() -> None:
    if sys.platform != "win32":
        return
    with contextlib.suppress(Exception):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Arbuz1k_SM.YandexMusicRPC")


def main() -> int:
    args = _arguments()
    _set_windows_identity()
    paths = AppPaths.discover()
    paths.ensure()
    config = ConfigManager(paths.config_file)
    config_error = None
    try:
        config.load()
    except ConfigError as exc:
        config_error = exc
    apply_embedded_defaults(config)
    log_handler = configure_logging(
        paths.log_file,
        str(config.get("logging.level", "INFO")),
        int(config.get("logging.retention_days", 1)),
    )
    if config_error:
        LOGGER.warning("%s", config_error)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Arbuz1k_SM")
    app.setWindowIcon(QIcon(str(resource_path("resources", "app_icon.ico"))))
    app.setQuitOnLastWindowClosed(False)

    i18n = I18n(str(config.get("application.language", "ru")))
    controller = ApplicationController(config, paths, i18n, log_handler)
    window = MainWindow(controller, i18n)
    tray = (
        TrayIcon(controller, window, i18n, app) if QSystemTrayIcon.isSystemTrayAvailable() else None
    )
    window.set_tray_available(tray is not None)
    if tray:
        tray.show()
        tray.setVisible(True)

    minimized = bool(tray and (args.minimized or config.get("application.start_minimized", False)))
    if not minimized:
        window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    exiting = False

    def request_exit() -> None:
        nonlocal exiting
        if exiting:
            return
        exiting = True

        async def finish() -> None:
            if tray:
                tray.hide()
            await controller.shutdown()
            window.force_close()
            app.quit()

        asyncio.create_task(finish(), name="application-shutdown")

    controller.request_exit.connect(request_exit)

    def exception_hook(exc_type, exc_value, exc_traceback) -> None:
        LOGGER.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = exception_hook

    with loop:
        loop.create_task(controller.start(), name="application-start")
        loop.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
