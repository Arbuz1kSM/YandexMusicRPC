from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pypresence.payloads import Payload
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from config.defaults import new_defaults
from config.manager import ConfigManager
from discord.presence_builder import PresenceBuilder
from discord.rpc import DiscordRPC
from localization.translator import I18n
from media.models import CoverKind, CoverRef, TrackInfo
from ui.pages.presence import PresencePage


class CardFieldTests(unittest.TestCase):
    def setUp(self):
        self.track = TrackInfo(
            "Track",
            "Artist",
            album="Real album",
            cover=CoverRef(CoverKind.URL, "https://example.org/cover.png"),
            track_url="https://music.yandex.ru/track/1",
        )
        self.config = new_defaults()
        self.config["application"]["language"] = "ru"
        self.builder = PresenceBuilder()

    def test_album_template_formats_cover_text(self):
        self.config["discord"].update(album_template="Album: {album}", cover_text_mode="album")
        payload = self.builder.build(self.track, self.config)
        self.assertEqual(payload.large_text, "Album: Real album")

    def test_empty_album_template_hides_album_hover_text(self):
        self.config["discord"].update(album_template="", cover_text_mode="album")
        payload = self.builder.build(self.track, self.config)
        self.assertIsNone(payload.large_text)

    def test_new_button_caption_is_exactly_32_utf8_bytes(self):
        payload = self.builder.build(self.track, self.config)
        self.assertEqual(payload.buttons[0]["label"], "Открыть в ЯМузыке")
        self.assertEqual(len(payload.buttons[0]["label"].encode("utf-8")), 32)

    def test_rpc_always_sends_listening_with_default_and_legacy_settings(self):
        rpc = DiscordRPC()
        rpc._presence = Mock()
        try:
            for previous_mode in (None, "playing", "listening"):
                with self.subTest(previous_mode=previous_mode):
                    self.config = new_defaults()
                    self.config["discord"]["cover_text_mode"] = "artist"
                    if previous_mode is not None:
                        self.config["discord"]["activity_type"] = previous_mode
                    payload = self.builder.build(self.track, self.config)
                    rpc._update_sync(payload)
                    wire = Payload.set_activity(**rpc._presence.update.call_args.kwargs).data[
                        "args"
                    ]["activity"]
                    self.assertEqual(wire["type"], 2)
                    self.assertEqual(wire["assets"]["large_text"], "Artist")
        finally:
            rpc._executor.shutdown(wait=True)


class Controller(QObject):
    setting_changed = Signal(str, object)

    def __init__(self, config):
        super().__init__()
        self.config = config
        config.subscribe(self.setting_changed.emit)

    def set_setting(self, name, value):
        self.config.set(name, value)


class LinkAndCardControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_master_toggle_restores_independent_checkbox_choices_on_reload(self):
        for language in ("ru", "en"):
            with tempfile.TemporaryDirectory() as directory:
                config = ConfigManager(Path(directory) / "config.json")
                config.load()
                controller = Controller(config)
                page = PresencePage(controller, I18n(language))
                page.link_text.setChecked(False)
                page.link_button.setChecked(True)
                page.links_enabled.setChecked(False)
                self.assertTrue(page.link_options.isHidden())
                reloaded = ConfigManager(config.path)
                reloaded.load()
                controller2 = Controller(reloaded)
                page2 = PresencePage(controller2, I18n(language))
                self.assertFalse(page2.links_enabled.isChecked())
                self.assertFalse(page2.link_text.isChecked())
                self.assertTrue(page2.link_button.isChecked())
                page2.links_enabled.setChecked(True)
                self.assertFalse(page2.link_options.isHidden())
                self.assertFalse(page2.link_text.isChecked())
                self.assertTrue(page2.link_button.isChecked())
                page.close()
                page2.close()

    def test_album_and_hover_controls_are_available_without_a_mode_selector(self):
        with tempfile.TemporaryDirectory() as directory:
            config = ConfigManager(Path(directory) / "config.json")
            config.load()
            controller = Controller(config)
            page = PresencePage(controller, I18n("ru"))
            self.assertFalse(page.hover_controls.isHidden())
            self.assertFalse(page.album_row.isHidden())
            self.assertFalse(hasattr(page, "activity_type"))
            page.cover_text_mode.setCurrentIndex(page.cover_text_mode.findData("custom"))
            self.assertFalse(page.hover_row.isHidden())
            page.close()


if __name__ == "__main__":
    unittest.main()
