from __future__ import annotations

import asyncio
import unittest
from dataclasses import replace

from media.models import TrackInfo
from media.session_manager import EnrichmentCoordinator


class StaleEnrichmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_result_is_discarded_after_track_switch(self) -> None:
        coordinator = EnrichmentCoordinator()
        track_a = TrackInfo("Track A", "Artist")
        track_b = TrackInfo("Track B", "Artist")
        accepted = []
        started = asyncio.Event()
        release = asyncio.Event()

        async def lookup(track):
            started.set()
            await release.wait()
            return replace(track, album="Enriched")

        async def accept(result):
            accepted.append(result)

        coordinator.switch_to(track_a)
        task = coordinator.start(track_a, lookup, accept)
        await started.wait()
        coordinator.switch_to(track_b)
        release.set()
        await asyncio.sleep(0)
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(accepted, [])

    async def test_current_result_is_accepted(self) -> None:
        coordinator = EnrichmentCoordinator()
        track = TrackInfo("Track A", "Artist")
        accepted = []

        async def lookup(value):
            return replace(value, album="Album")

        async def accept(result):
            accepted.append(result.track.album)

        coordinator.switch_to(track)
        await coordinator.start(track, lookup, accept)
        self.assertEqual(accepted, ["Album"])


if __name__ == "__main__":
    unittest.main()
