from __future__ import annotations

import contextlib
import logging

LOGGER = logging.getLogger(__name__)
SERVICE = "Arbuz1k_SM.YandexMusicRPC"
USERNAME = "yandex_oauth_token"
MIGRATION_MARKER_USERNAME = "legacy_yandex_token_import"
MIGRATION_MARKER_DONE = "done"


LEGACY_CREDENTIALS: tuple[tuple[str, str], ...] = (("WinYandexMusicRPC", "token"),)


class CredentialStore:
    @staticmethod
    def _mark_legacy_import_done(keyring) -> None:
        try:
            keyring.set_password(SERVICE, MIGRATION_MARKER_USERNAME, MIGRATION_MARKER_DONE)
        except Exception as exc:
            LOGGER.debug(
                "Could not persist legacy credential import marker: %s",
                type(exc).__name__,
            )

    @staticmethod
    def _legacy_import_done(keyring) -> bool:
        try:
            return keyring.get_password(SERVICE, MIGRATION_MARKER_USERNAME) == MIGRATION_MARKER_DONE
        except Exception:
            return False

    def get_token(self) -> str | None:
        try:
            import keyring

            token = keyring.get_password(SERVICE, USERNAME)
            if token and token.strip():
                self._mark_legacy_import_done(keyring)
                return token.strip()

            if self._legacy_import_done(keyring):
                return None

            for legacy_service, legacy_username in LEGACY_CREDENTIALS:
                legacy = keyring.get_password(legacy_service, legacy_username)
                if not legacy or not legacy.strip():
                    continue
                legacy = legacy.strip()
                try:
                    keyring.set_password(SERVICE, USERNAME, legacy)
                    self._mark_legacy_import_done(keyring)
                    LOGGER.info(
                        "Imported Yandex Music authorization from legacy WinYandexMusicRPC credentials"
                    )
                except Exception as exc:
                    LOGGER.warning(
                        "Could not persist imported Yandex Music authorization: %s",
                        type(exc).__name__,
                    )
                return legacy
            return None
        except Exception as exc:
            LOGGER.warning("Credential storage is unavailable: %s", type(exc).__name__)
            return None

    def set_token(self, token: str) -> None:
        import keyring

        token = token.strip()
        if token:
            keyring.set_password(SERVICE, USERNAME, token)

            self._mark_legacy_import_done(keyring)
        else:
            self.delete_token()

    def delete_token(self) -> None:
        try:
            import keyring

            self._mark_legacy_import_done(keyring)
            with contextlib.suppress(Exception):
                keyring.delete_password(SERVICE, USERNAME)
        except Exception:
            pass
