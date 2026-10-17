from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from app.application import ApplicationController
from config.defaults import migrate_stored
from config.manager import ConfigManager
from localization.translator import I18n
from ui.main_window import MainWindow
from utils.logging import ObservableLogHandler
from utils.paths import AppPaths
from utils.version import APP_VERSION, AUTHOR_URL


class ReleaseUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_legacy_card_choice_is_removed_without_losing_templates(self):
        migrated = migrate_stored(
            {
                "discord": {
                    "activity_type": "listening",
                    "album_template": "My {album}",
                    "music_link_text": False,
                }
            }
        )
        self.assertNotIn("activity_type", migrated["discord"])
        self.assertEqual(migrated["discord"]["album_template"], "My {album}")
        self.assertFalse(migrated["discord"]["music_link_text"])

    def test_author_links_and_sidebar_version_in_both_languages(self):
        for language in ("ru", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                paths = AppPaths(
                    root / "config",
                    root / "cache",
                    root / "logs",
                    root / "config/config.json",
                    root / "cache/tracks.json",
                    root / "logs/app.log",
                )
                config = ConfigManager(paths.config_file)
                config.load()
                config.set("application.language", language)
                controller = ApplicationController(
                    config, paths, I18n(language), ObservableLogHandler()
                )
                controller.refresh_yandex_auth_status = lambda: None
                window = MainWindow(controller, controller.i18n)
                try:
                    sidebar = [label.text() for label in window.sidebar.findChildren(QLabel)]
                    self.assertIn("v1.0.0", sidebar)
                    self.assertFalse(any("Arbuz1k_SM" in text for text in sidebar))
                    about = window.stack.widget(5)
                    author_links = [
                        label for label in about.findChildren(QLabel) if AUTHOR_URL in label.text()
                    ]
                    self.assertTrue(author_links)
                    self.assertTrue(all(label.openExternalLinks() for label in author_links))
                    presence = window.stack.widget(1)
                    self.assertFalse(hasattr(presence, "activity_type"))
                    self.assertFalse(presence.album_row.isHidden())
                    self.assertTrue(
                        all(
                            combo.findData("listening") == -1
                            for combo in presence.findChildren(QComboBox)
                        )
                    )
                    self.assertEqual(APP_VERSION, "1.0.0")
                finally:
                    window.force_close()
                    controller.engine.discord._executor.shutdown(wait=True)
