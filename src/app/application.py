from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from app.engine import ApplicationEngine, EngineCallbacks
from app.startup import set_start_with_windows
from config.manager import ConfigManager
from discord.rpc import DiscordStatus
from localization.translator import I18n
from media.models import TrackInfo
from utils.logging import LogRecordView, ObservableLogHandler
from utils.paths import AppPaths
from utils.version import PROJECT_URL
from yandex.auth import create_device_auth_client, poll_device_token, request_device_code

LOGGER = logging.getLogger(__name__)


class ApplicationController(QObject):
    track_changed = Signal(object)
    discord_status_changed = Signal(str, object)
    api_status_changed = Signal(str, object)
    media_status_changed = Signal(str, object)
    rpc_enabled_changed = Signal(bool)
    log_added = Signal(object)
    setting_changed = Signal(str, object)
    theme_changed = Signal(str)
    language_changed = Signal(str)
    token_result = Signal(bool, str)
    yandex_auth_code = Signal(str, str, int)
    yandex_auth_status = Signal(bool, object)
    yandex_auth_busy = Signal(bool)
    request_exit = Signal()

    def __init__(
        self,
        config: ConfigManager,
        paths: AppPaths,
        i18n: I18n,
        log_handler: ObservableLogHandler,
    ) -> None:
        super().__init__()
        self.config = config
        self.paths = paths
        self.i18n = i18n
        self.log_handler = log_handler
        self.current_track: TrackInfo | None = None
        self.log_handler.subscribers.append(self.log_added.emit)
        self.config.subscribe(self._config_changed)

        callbacks = EngineCallbacks(
            track=self._track,
            discord_status=lambda status, error: self.discord_status_changed.emit(
                status.value, error
            ),
            api_status=lambda status, confidence: self.api_status_changed.emit(status, confidence),
            media_status=lambda status, detail: self.media_status_changed.emit(status, detail),
            rpc_enabled=self.rpc_enabled_changed.emit,
        )
        self.engine = ApplicationEngine(config, paths, callbacks)
        self._yandex_auth_task: asyncio.Task | None = None

    def _track(self, track: TrackInfo | None) -> None:
        self.current_track = track
        self.track_changed.emit(track)

    def _config_changed(self, key: str, value) -> None:
        self.setting_changed.emit(key, value)
        if key == "application.theme":
            self.theme_changed.emit(str(value))
        elif key == "application.language":
            self.i18n.set_language(str(value))
            self.language_changed.emit(str(value))

    async def start(self) -> None:
        await self.engine.start()
        await self._emit_yandex_auth_status()

    def set_setting(self, key: str, value) -> None:
        self.config.set(key, value)
        if key == "application.start_with_windows":
            set_start_with_windows(bool(value))

    def toggle_rpc(self) -> None:
        asyncio.create_task(
            self.engine.set_rpc_enabled(not self.engine.rpc_enabled), name="toggle-rpc"
        )

    def reconnect_discord(self) -> None:
        asyncio.create_task(self.engine.reconnect_discord(), name="manual-discord-reconnect")

    async def _emit_yandex_auth_status(self) -> None:
        token = await asyncio.to_thread(self.engine.credentials.get_token)
        self.yandex_auth_status.emit(bool(token), None)

    def refresh_yandex_auth_status(self) -> None:
        asyncio.create_task(self._emit_yandex_auth_status(), name="yandex-auth-status")

    def start_yandex_login(self) -> None:
        if self._yandex_auth_task is not None and not self._yandex_auth_task.done():
            return

        async def authorize() -> None:
            self.yandex_auth_busy.emit(True)
            try:
                client = await asyncio.to_thread(create_device_auth_client)
                code = await asyncio.to_thread(request_device_code, client)
                self.yandex_auth_code.emit(code.user_code, code.verification_url, code.expires_in)

                QTimer.singleShot(
                    0,
                    lambda url=code.verification_url: QDesktopServices.openUrl(QUrl(url)),
                )

                deadline = time.monotonic() + code.expires_in
                token: str | None = None
                while time.monotonic() < deadline:
                    if asyncio.current_task() is not self._yandex_auth_task:
                        return
                    token = await asyncio.to_thread(poll_device_token, client, code.device_code)
                    if token:
                        break
                    await asyncio.sleep(code.interval)

                if not token:
                    self.token_result.emit(False, "yandex_auth_timeout")
                    return

                await asyncio.to_thread(self.engine.credentials.set_token, token)
                await self.engine.refresh_yandex_credentials()
                await self._emit_yandex_auth_status()
                self.token_result.emit(True, "signed_in")
                LOGGER.info("Yandex Music authorization completed")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.warning("Yandex Music authorization failed: %s", type(exc).__name__)
                self.token_result.emit(False, type(exc).__name__)
            finally:
                self.yandex_auth_busy.emit(False)

        self._yandex_auth_task = asyncio.create_task(authorize(), name="yandex-device-auth")

    def cancel_yandex_login(self) -> None:
        task = self._yandex_auth_task
        if task is not None and not task.done():
            task.cancel()
        self._yandex_auth_task = None
        self.yandex_auth_busy.emit(False)

    def save_token(self, token: str) -> None:
        async def save() -> None:
            try:
                await asyncio.to_thread(self.engine.credentials.set_token, token)
                await self.engine.refresh_yandex_credentials()
                await self._emit_yandex_auth_status()
                self.token_result.emit(True, "saved")
            except Exception as exc:
                LOGGER.warning("Could not store credential: %s", type(exc).__name__)
                self.token_result.emit(False, type(exc).__name__)

        asyncio.create_task(save(), name="save-yandex-token")

    def delete_token(self) -> None:
        self.cancel_yandex_login()

        async def delete() -> None:
            await asyncio.to_thread(self.engine.credentials.delete_token)
            await self.engine.refresh_yandex_credentials()
            await self._emit_yandex_auth_status()
            self.token_result.emit(True, "deleted")

        asyncio.create_task(delete(), name="delete-yandex-token")

    @staticmethod
    def open_url(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def open_path(path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_project(self) -> None:
        self.open_url(PROJECT_URL)

    def exit(self) -> None:
        self.request_exit.emit()

    async def shutdown(self) -> None:
        self.cancel_yandex_login()
        await self.engine.stop()

    @property
    def log_records(self) -> tuple[LogRecordView, ...]:
        return tuple(self.log_handler.records)

    @property
    def discord_status(self) -> DiscordStatus:
        return self.engine.discord.status
