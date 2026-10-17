from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from config.defaults import DEFAULT_POLL_INTERVAL_MS
from config.manager import ConfigManager
from discord.presence_builder import PresenceBuilder
from discord.rpc import (
    DiscordApplicationIdMissing,
    DiscordRPC,
    DiscordStatus,
)
from media.models import PlaybackState, TrackInfo, detect_change
from media.session_manager import EnrichmentCoordinator, EnrichmentResult
from media.windows_media import WindowsMediaSource, WindowsMediaUnavailable
from utils.paths import AppPaths
from utils.system_volume import get_master_volume_percent
from yandex.cache import TrackCache
from yandex.client import YandexMusicEnricher
from yandex.credentials import CredentialStore

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EngineCallbacks:
    track: Callable[[TrackInfo | None], None] = field(default=lambda _value: None)
    discord_status: Callable[[DiscordStatus, str | None], None] = field(
        default=lambda _status, _error: None
    )
    api_status: Callable[[str, float | None], None] = field(
        default=lambda _status, _confidence: None
    )
    media_status: Callable[[str, str | None], None] = field(default=lambda _status, _detail: None)
    rpc_enabled: Callable[[bool], None] = field(default=lambda _enabled: None)


class ApplicationEngine:
    RECONNECT_BACKOFF = (1, 2, 5, 10, 30)

    def __init__(
        self,
        config: ConfigManager,
        paths: AppPaths,
        callbacks: EngineCallbacks | None = None,
    ) -> None:
        self.config = config
        self.paths = paths
        self.callbacks = callbacks or EngineCallbacks()
        self.discord = DiscordRPC()
        self._session_listened_seconds = 0.0
        self._session_clock_at = time.monotonic()
        self.builder = PresenceBuilder(
            volume_provider=get_master_volume_percent,
            session_seconds_provider=lambda: self.session_listening_seconds,
        )
        self.credentials = CredentialStore()

        with contextlib.suppress(OSError):
            paths.track_cache_file.unlink(missing_ok=True)
        self.cache = TrackCache(None)
        self.coordinator = EnrichmentCoordinator()

        self.media: WindowsMediaSource | None = None
        self.enricher: YandexMusicEnricher | None = None
        self.current: TrackInfo | None = None
        self._base_track: TrackInfo | None = None
        self._running = False
        self._runner_task: asyncio.Task | None = None
        self._connect_task: asyncio.Task | None = None
        self._empty_since: float | None = None
        self._paused_since: float | None = None
        self._pause_hidden = False
        self._last_payload = None
        self._last_discord_update = 0.0
        self._last_discord_update_at: float | None = None
        self._last_dynamic_publish = 0.0
        self._settings_dirty = True
        self._source_dirty = True
        self._api_status = "disabled"
        self._api_confidence: float | None = None
        self._rpc_enabled = bool(self.config.get("discord.enabled", True))
        self._connection_authorized = True
        self.config.subscribe(self._on_config_changed)

    @property
    def rpc_enabled(self) -> bool:
        return self._rpc_enabled

    @property
    def session_listening_seconds(self) -> float:
        value = self._session_listened_seconds
        if self.current is not None and self.current.playback_state == PlaybackState.PLAYING:
            value += max(0.0, time.monotonic() - self._session_clock_at)
        return value

    def _advance_session_clock(self, now: float) -> None:
        elapsed = max(0.0, now - self._session_clock_at)
        if self.current is not None and self.current.playback_state == PlaybackState.PLAYING:
            self._session_listened_seconds += elapsed
        self._session_clock_at = now

    def _on_config_changed(self, key: str, _value: Any) -> None:
        self._settings_dirty = True
        if key == "*" or key.startswith("source."):
            self._source_dirty = True
        if key == "discord.application_id":
            self._schedule_reconnect()

    def _set_api_status(self, status: str, confidence: float | None = None) -> None:
        self._api_status = status
        self._api_confidence = confidence
        self.callbacks.api_status(status, confidence)

    def _new_media_source(self) -> WindowsMediaSource:
        return WindowsMediaSource(
            session_hints=list(self.config.get("source.session_hints", [])),
            accept_any_session=bool(self.config.get("source.accept_any_media_session", False)),
        )

    async def _rebuild_source(self) -> None:
        if self.media:
            await self.media.close()
        self.media = self._new_media_source()
        try:
            await self.media.start()
            self.callbacks.media_status("connected", None)
        except WindowsMediaUnavailable as exc:
            self.callbacks.media_status("error", str(exc))
            LOGGER.error("Windows Media Control unavailable: %s", exc)
        self._source_dirty = False
        await self._rebuild_enricher()

    async def _rebuild_enricher(self) -> None:
        self.coordinator.cancel()
        if self.enricher is not None:
            self.enricher.close()
            self.enricher = None
        if self.config.get("source.mode", "windows") != "windows_yandex":
            self._set_api_status("disabled")
            return
        token = await asyncio.to_thread(self.credentials.get_token)
        self.enricher = YandexMusicEnricher(
            self.cache,
            token=token,
            timeout_seconds=float(self.config.get("source.api_timeout_seconds", 7)),
        )
        self._set_api_status("ready")
        if self._base_track is not None:
            self.coordinator.switch_to(self._base_track)
            self._start_enrichment(self._base_track)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.callbacks.rpc_enabled(self._rpc_enabled)
        self._runner_task = asyncio.create_task(self._run(), name="application-engine")
        if self._rpc_enabled and self._connection_authorized:
            self._schedule_reconnect()

    async def _run(self) -> None:
        while self._running:
            if self._source_dirty or self.media is None:
                await self._rebuild_source()
            sample = None
            sample_valid = True
            if self.media is not None:
                try:
                    sample = await asyncio.wait_for(self.media.sample(), timeout=3.0)
                except TimeoutError:
                    sample_valid = False
                    self._source_dirty = True
                    LOGGER.warning("Windows Media Control poll timed out; reconnecting")
                    self.callbacks.media_status("error", "timeout")
                except Exception as exc:
                    sample_valid = False
                    LOGGER.warning("Media polling recovered from: %s", type(exc).__name__)
                    self.callbacks.media_status("error", type(exc).__name__)
            self._advance_session_clock(time.monotonic())
            if sample_valid:
                await self._process_sample(sample)
            if self._settings_dirty and self.current is not None:
                self._settings_dirty = False
                await self._publish()
            if self.current is not None:
                settings = self.config.snapshot().get("discord", {})
                update_interval = DEFAULT_POLL_INTERVAL_MS / 1000
                if (
                    self.builder.uses_dynamic_templates(settings)
                    and time.monotonic() - self._last_dynamic_publish >= update_interval
                ):
                    await self._publish()
            delay = DEFAULT_POLL_INTERVAL_MS / 1000
            await asyncio.sleep(delay)

    async def _process_sample(self, sample: TrackInfo | None) -> None:
        now = time.monotonic()
        if sample is None:
            if self._empty_since is None:
                self._empty_since = now
            grace = int(self.config.get("source.empty_metadata_grace_ms", 2500)) / 1000
            if self.current is not None and now - self._empty_since >= grace:
                self.current = None
                self._base_track = None
                self.coordinator.cancel()
                self._paused_since = None
                self.callbacks.track(None)
                await self._clear_presence()
            return

        self._empty_since = None
        if self._base_track is None or self._base_track.identity != sample.identity:
            self._base_track = sample
            self.current = sample
            self.coordinator.switch_to(sample)
            self._paused_since = now if sample.playback_state == PlaybackState.PAUSED else None
            self._pause_hidden = False
            self.callbacks.track(self.current)
            await self._publish()
            self._start_enrichment(sample)
            return

        change = detect_change(self._base_track, sample)
        self._base_track = sample
        if self.current is None:
            self.current = sample
        else:
            self.current = self.current.with_realtime(sample)
        self.callbacks.track(self.current)

        if sample.playback_state == PlaybackState.PAUSED:
            self._paused_since = self._paused_since or now
        else:
            if self._paused_since is not None or self._pause_hidden:
                change = type(change)(
                    track_changed=change.track_changed,
                    playback_changed=True,
                    seeked=change.seeked,
                    metadata_changed=change.metadata_changed,
                )
            self._paused_since = None
            self._pause_hidden = False

        if change.should_update_presence:
            await self._publish()
        await self._apply_pause_hide_delay(now)

    def _start_enrichment(self, base_track: TrackInfo) -> None:
        if self.enricher is None:
            return
        self._set_api_status("searching")
        generation = self.coordinator.generation
        enricher = self.enricher

        async def lookup(track: TrackInfo) -> TrackInfo | None:
            result = await enricher.enrich(track)
            if result is None and self.coordinator.is_current(track, generation):
                self._set_api_status(enricher.last_status)
            return result

        async def accept(result: EnrichmentResult) -> None:
            if self.current is None or self._base_track is None:
                return

            self.current = self.current.merge_enrichment(result.track)
            self.callbacks.track(self.current)
            self._set_api_status("matched", self.current.match_confidence)
            await self._publish()

        self.coordinator.start(base_track, lookup, accept)

    async def _apply_pause_hide_delay(self, now: float) -> None:
        if (
            self.current is None
            or self.current.playback_state != PlaybackState.PAUSED
            or self.config.get("discord.pause_behavior", "show") != "hide"
            or self._paused_since is None
            or self._pause_hidden
        ):
            return
        delay = max(0, int(self.config.get("discord.pause_hide_delay_seconds", 0)))
        if now - self._paused_since >= delay:
            await self._clear_presence()
            self._pause_hidden = True

    async def _publish(self, force: bool = False) -> None:
        if not self._rpc_enabled or self.current is None:
            return
        if self._pause_hidden:
            return
        if self.discord.status != DiscordStatus.CONNECTED:
            if self._connection_authorized:
                self._schedule_reconnect()
            return
        payload = self.builder.build(self.current, self.config.snapshot())
        if not force and payload == self._last_payload:
            return
        try:
            await self.discord.update(payload)
        except Exception:
            self.callbacks.discord_status(self.discord.status, self.discord.last_error)
            self._schedule_reconnect()
            return
        self._last_payload = payload
        self._last_discord_update = time.monotonic()
        self._last_discord_update_at = time.time()
        self._last_dynamic_publish = time.monotonic()
        self.callbacks.discord_status(DiscordStatus.CONNECTED, None)

    async def _clear_presence(self) -> None:
        if self.discord.status == DiscordStatus.CONNECTED:
            await self.discord.clear()
        self._last_payload = None

    def _schedule_reconnect(self) -> None:
        if not self._running or not self._rpc_enabled or not self._connection_authorized:
            return
        if self._connect_task and not self._connect_task.done():
            return
        self._connect_task = asyncio.create_task(
            self._connect_supervisor(), name="discord-reconnect"
        )

    async def _connect_supervisor(self) -> None:
        application_id = str(self.config.get("discord.application_id", ""))
        for delay in self.RECONNECT_BACKOFF:
            if not self._running or not self._rpc_enabled or not self._connection_authorized:
                return
            self.callbacks.discord_status(DiscordStatus.RECONNECTING, None)
            try:
                await self.discord.connect(application_id)
                self.callbacks.discord_status(DiscordStatus.CONNECTED, None)
                await self._publish(force=True)
                return
            except DiscordApplicationIdMissing as exc:
                self.callbacks.discord_status(DiscordStatus.ERROR, str(exc))
                return
            except Exception:
                self.callbacks.discord_status(self.discord.status, self.discord.last_error)
                await asyncio.sleep(delay)
        while self._running and self._rpc_enabled and self._connection_authorized:
            await asyncio.sleep(30)
            try:
                await self.discord.connect(application_id)
                self.callbacks.discord_status(DiscordStatus.CONNECTED, None)
                await self._publish(force=True)
                return
            except Exception:
                self.callbacks.discord_status(self.discord.status, self.discord.last_error)

    async def set_rpc_enabled(self, enabled: bool) -> None:
        self._rpc_enabled = bool(enabled)
        self.config.set("discord.enabled", self._rpc_enabled)
        self.callbacks.rpc_enabled(self._rpc_enabled)
        if self._rpc_enabled:
            self._connection_authorized = True
            self._schedule_reconnect()
        else:
            if self._connect_task:
                self._connect_task.cancel()
            await self._clear_presence()
            await self.discord.disconnect()
            self.callbacks.discord_status(DiscordStatus.DISABLED, None)

    async def reconnect_discord(self) -> None:
        if not self._rpc_enabled:
            return
        self._connection_authorized = True
        if self._connect_task:
            self._connect_task.cancel()
        await self.discord.disconnect()
        self._connect_task = None
        self._schedule_reconnect()

    async def refresh_yandex_credentials(self) -> None:
        await self._rebuild_enricher()

    async def stop(self) -> None:
        self._running = False
        self.coordinator.cancel()
        for task in (self._connect_task, self._runner_task):
            if task and not task.done():
                task.cancel()
        if self.media:
            await self.media.close()
        if self.enricher:
            self.enricher.close()
            self.enricher = None
        await self.discord.dispose()
