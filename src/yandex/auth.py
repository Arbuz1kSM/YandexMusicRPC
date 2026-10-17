from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeviceAuthorizationCode:
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: float


def create_device_auth_client():

    from yandex_music import Client

    return Client()


def request_device_code(client: Any) -> DeviceAuthorizationCode:
    code = client.request_device_code(device_name="YandexMusicRPC")
    return DeviceAuthorizationCode(
        device_code=str(code.device_code),
        user_code=str(code.user_code),
        verification_url=str(code.verification_url),
        expires_in=max(1, int(code.expires_in)),
        interval=max(1.0, float(code.interval)),
    )


def poll_device_token(client: Any, device_code: str) -> str | None:
    token = client.poll_device_token(device_code)
    if token is None:
        return None
    access_token = str(getattr(token, "access_token", "") or "").strip()
    return access_token or None
