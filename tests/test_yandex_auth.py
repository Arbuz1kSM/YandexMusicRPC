from __future__ import annotations

import unittest
from types import SimpleNamespace

from yandex.auth import poll_device_token, request_device_code


class FakeDeviceClient:
    def __init__(self) -> None:
        self.requested_name = None
        self.polled = []
        self.token = None

    def request_device_code(self, *, device_name=None):
        self.requested_name = device_name
        return SimpleNamespace(
            device_code="device-secret",
            user_code="ABCD-EFGH",
            verification_url="https://oauth.yandex.ru/device",
            expires_in=600,
            interval=5,
        )

    def poll_device_token(self, device_code):
        self.polled.append(device_code)
        return self.token


class YandexAuthTests(unittest.TestCase):
    def test_request_device_code_maps_library_model(self) -> None:
        client = FakeDeviceClient()
        code = request_device_code(client)
        self.assertEqual(client.requested_name, "YandexMusicRPC")
        self.assertEqual(code.device_code, "device-secret")
        self.assertEqual(code.user_code, "ABCD-EFGH")
        self.assertEqual(code.verification_url, "https://oauth.yandex.ru/device")
        self.assertEqual(code.expires_in, 600)
        self.assertEqual(code.interval, 5.0)

    def test_poll_device_token_returns_none_while_pending(self) -> None:
        client = FakeDeviceClient()
        self.assertIsNone(poll_device_token(client, "device-secret"))
        self.assertEqual(client.polled, ["device-secret"])

    def test_poll_device_token_extracts_access_token(self) -> None:
        client = FakeDeviceClient()
        client.token = SimpleNamespace(access_token="  oauth-token  ")
        self.assertEqual(poll_device_token(client, "device-secret"), "oauth-token")


if __name__ == "__main__":
    unittest.main()
