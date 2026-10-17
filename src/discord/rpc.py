from __future__ import annotations

import asyncio
import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum

from discord.presence_builder import ActivityPayload
from utils.logging import rpc

LOGGER = logging.getLogger(__name__)


class DiscordStatus(StrEnum):
    DISABLED = "disabled"
    CONNECTED = "connected"
    NOT_FOUND = "not_found"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class DiscordApplicationIdMissing(ValueError):
    pass


class DiscordRPC:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="discord-rpc")
        self._presence = None
        self._application_id: str | None = None
        self.status = DiscordStatus.DISABLED
        self.last_error: str | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _validate_application_id(application_id: str) -> str:
        value = str(application_id or "").strip()
        if not value.isdigit() or not (17 <= len(value) <= 20):
            raise DiscordApplicationIdMissing("Discord Application ID is not configured")
        return value

    def _connect_sync(self, application_id: str) -> None:
        from pypresence import Presence

        self._presence = Presence(application_id, connection_timeout=4, response_timeout=3)
        self._presence.connect()

    def _close_sync(self) -> None:
        if self._presence is None:
            return
        with contextlib.suppress(Exception):
            self._presence.close()
        self._presence = None

    def _update_sync(self, payload: ActivityPayload) -> None:
        if self._presence is None:
            raise RuntimeError("Discord RPC is not connected")
        from pypresence.types import ActivityType, StatusDisplayType

        status_types = {
            "name": StatusDisplayType.NAME,
            "state": StatusDisplayType.STATE,
            "details": StatusDisplayType.DETAILS,
        }
        kwargs = {
            "activity_type": ActivityType.LISTENING,
            "status_display_type": status_types[payload.status_display_type],
            "name": payload.name,
            "details": payload.details,
            "details_url": payload.details_url,
            "state": payload.state,
            "state_url": payload.state_url,
            "start": payload.start,
            "end": payload.end,
            "large_image": payload.large_image,
            "large_text": payload.large_text,
            "small_image": payload.small_image,
            "small_text": payload.small_text,
            "buttons": payload.buttons or None,
        }
        self._presence.update(**kwargs)

    def _clear_sync(self) -> None:
        if self._presence is not None:
            self._presence.clear()

    async def _worker(self, callback, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, callback, *args)

    async def connect(self, application_id: str) -> None:
        application_id = self._validate_application_id(application_id)
        async with self._lock:
            if self.status == DiscordStatus.CONNECTED and self._application_id == application_id:
                return
            await self._worker(self._close_sync)
            self.status = DiscordStatus.RECONNECTING
            try:
                await self._worker(self._connect_sync, application_id)
            except Exception as exc:
                self.last_error = type(exc).__name__
                self.status = DiscordStatus.NOT_FOUND
                raise
            self._application_id = application_id
            self.last_error = None
            self.status = DiscordStatus.CONNECTED
            rpc(LOGGER, "Discord connected")

    async def update(self, payload: ActivityPayload) -> None:
        async with self._lock:
            try:
                await self._worker(self._update_sync, payload)
            except Exception as exc:
                self.last_error = type(exc).__name__
                self.status = DiscordStatus.ERROR
                await self._worker(self._close_sync)
                raise
            rpc(LOGGER, "Presence updated")

    async def clear(self) -> None:
        async with self._lock:
            try:
                await self._worker(self._clear_sync)
            except Exception:
                self.status = DiscordStatus.ERROR

    async def disconnect(self) -> None:
        async with self._lock:
            await self._worker(self._close_sync)
            self.status = DiscordStatus.DISABLED

    async def dispose(self) -> None:
        await self.disconnect()
        self._executor.shutdown(wait=False, cancel_futures=True)
