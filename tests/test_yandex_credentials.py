from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from yandex.credentials import (
    MIGRATION_MARKER_DONE,
    MIGRATION_MARKER_USERNAME,
    SERVICE,
    USERNAME,
    CredentialStore,
)


class FakeKeyring:
    def __init__(self, initial=None) -> None:
        self.values = dict(initial or {})

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        key = (service, username)
        if key not in self.values:
            raise RuntimeError("missing")
        del self.values[key]

    def module(self):
        return SimpleNamespace(
            get_password=self.get_password,
            set_password=self.set_password,
            delete_password=self.delete_password,
        )


class CredentialStoreTests(unittest.TestCase):
    def test_legacy_token_is_imported_once(self) -> None:
        fake = FakeKeyring({("WinYandexMusicRPC", "token"): " legacy-token "})
        with patch.dict(sys.modules, {"keyring": fake.module()}):
            store = CredentialStore()
            self.assertEqual(store.get_token(), "legacy-token")
            self.assertEqual(fake.values[(SERVICE, USERNAME)], "legacy-token")
            self.assertEqual(
                fake.values[(SERVICE, MIGRATION_MARKER_USERNAME)], MIGRATION_MARKER_DONE
            )

    def test_sign_out_does_not_resurrect_legacy_token(self) -> None:
        fake = FakeKeyring({("WinYandexMusicRPC", "token"): "legacy-token"})
        with patch.dict(sys.modules, {"keyring": fake.module()}):
            store = CredentialStore()
            self.assertEqual(store.get_token(), "legacy-token")
            store.delete_token()
            self.assertNotIn((SERVICE, USERNAME), fake.values)
            self.assertEqual(
                fake.values[(SERVICE, MIGRATION_MARKER_USERNAME)], MIGRATION_MARKER_DONE
            )
            self.assertEqual(fake.values[("WinYandexMusicRPC", "token")], "legacy-token")
            self.assertIsNone(store.get_token())

    def test_existing_token_gets_migration_marker(self) -> None:
        fake = FakeKeyring({(SERVICE, USERNAME): "already-imported"})
        with patch.dict(sys.modules, {"keyring": fake.module()}):
            self.assertEqual(CredentialStore().get_token(), "already-imported")
            self.assertEqual(
                fake.values[(SERVICE, MIGRATION_MARKER_USERNAME)], MIGRATION_MARKER_DONE
            )


if __name__ == "__main__":
    unittest.main()
