from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from media.models import TrackInfo


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    track: TrackInfo
    generation: int


class EnrichmentCoordinator:
    def __init__(self) -> None:
        self._generation = 0
        self._identity = None
        self._task: asyncio.Task | None = None

    @property
    def generation(self) -> int:
        return self._generation

    def switch_to(self, track: TrackInfo) -> int:
        self._generation += 1
        self._identity = track.identity
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        return self._generation

    def is_current(self, track: TrackInfo, generation: int) -> bool:
        return generation == self._generation and track.identity == self._identity

    def start(
        self,
        base_track: TrackInfo,
        lookup: Callable[[TrackInfo], Awaitable[TrackInfo | None]],
        on_current_result: Callable[[EnrichmentResult], Awaitable[None]],
    ) -> asyncio.Task:
        generation = self._generation

        async def run() -> None:
            try:
                result = await lookup(base_track)
            except asyncio.CancelledError:
                return
            if result is None or not self.is_current(base_track, generation):
                return
            await on_current_result(EnrichmentResult(result, generation))

        self._task = asyncio.create_task(run(), name=f"yandex-enrichment-{generation}")
        return self._task

    def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
