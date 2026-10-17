from __future__ import annotations

import sys


def get_master_volume_percent() -> int | None:

    if sys.platform != "win32":
        return None
    try:
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        endpoint = device.EndpointVolume
        value = float(endpoint.GetMasterVolumeLevelScalar())
        return max(0, min(100, round(value * 100)))
    except Exception:
        return None
