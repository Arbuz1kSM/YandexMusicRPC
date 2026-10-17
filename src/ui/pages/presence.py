from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QLayout,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.common import Card, NoWheelComboBox, muted, page_header, row, section_title


class PresencePage(QWidget):
    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        header, _ = page_header(i18n.t("presence.title"), i18n.t("presence.subtitle"))
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")

        content = QWidget()
        content.setObjectName("ScrollContent")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(14)
        self.content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._compact_card()
        self._lines_card()
        self._cover_card()
        self._pause_card()
        self._buttons_card()
        self.content_layout.addStretch(1)

    def _save(self, key: str, value) -> None:
        self.controller.set_setting(key, value)

    def _combo(self, items: list[tuple[str, object]], current) -> NoWheelComboBox:
        combo = NoWheelComboBox()
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(current)
        combo.setCurrentIndex(max(0, index))
        return combo

    def _compact_card(self) -> None:
        card = Card()
        card.layout_box.addWidget(section_title(self.i18n.t("presence.compact_section")))
        self.compact = self._combo(
            [
                (self.i18n.t("presence.compact_artist"), "artist"),
                (self.i18n.t("presence.compact_title"), "title"),
                (self.i18n.t("presence.compact_album"), "album"),
                (self.i18n.t("presence.compact_custom"), "custom"),
            ],
            self.controller.config.get("discord.compact_field"),
        )
        card.layout_box.addWidget(row(self.i18n.t("presence.compact_label"), self.compact))
        self.custom_text = QLineEdit(
            str(self.controller.config.get("discord.compact_custom_text", ""))
        )
        self.custom_text.setMinimumWidth(280)
        self.custom_row = row(self.i18n.t("presence.custom_text"), self.custom_text)
        card.layout_box.addWidget(self.custom_row)
        self.compact.currentIndexChanged.connect(self._compact_changed)
        self.custom_text.editingFinished.connect(
            lambda: self._save("discord.compact_custom_text", self.custom_text.text())
        )
        self.custom_row.setVisible(self.compact.currentData() == "custom")

        activity = QLineEdit(
            str(self.controller.config.get("discord.registered_activity_name", "Яндекс Музыка"))
        )
        self.activity_name = activity
        activity.setMaxLength(128)
        activity.setMinimumWidth(280)
        card.layout_box.addWidget(row(self.i18n.t("presence.activity_name"), activity))
        activity.editingFinished.connect(
            lambda: self._save(
                "discord.registered_activity_name",
                activity.text().strip() or "Яндекс Музыка",
            )
        )
        self.controller.setting_changed.connect(self._sync_activity_name)
        self.content_layout.addWidget(card)

    def _sync_activity_name(self, key, value) -> None:
        if key == "discord.registered_activity_name":
            self.activity_name.setText(str(value))

    def _compact_changed(self) -> None:
        value = self.compact.currentData()
        self.custom_row.setVisible(value == "custom")
        self._save("discord.compact_field", value)

    def _lines_card(self) -> None:
        card = Card()
        card.layout_box.addWidget(section_title(self.i18n.t("presence.lines_section")))
        card.layout_box.addWidget(muted(self.i18n.t("presence.templates_hint")))
        variables = muted(self.i18n.t("presence.templates_variables"))
        variables.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card.layout_box.addWidget(variables)

        title = QLineEdit(str(self.controller.config.get("discord.title_template", "{title}")))
        artist = QLineEdit(str(self.controller.config.get("discord.artist_template", "{artist}")))
        album = QLineEdit(str(self.controller.config.get("discord.album_template", "{album}")))
        for control in (title, artist, album):
            control.setMinimumWidth(280)

        card.layout_box.addWidget(row(self.i18n.t("presence.title_template"), title))
        card.layout_box.addWidget(row(self.i18n.t("presence.artist_template"), artist))
        self.album_row = row(self.i18n.t("presence.album_template"), album)
        card.layout_box.addWidget(self.album_row)
        title.editingFinished.connect(
            lambda: self._save("discord.title_template", title.text() or "{title}")
        )
        artist.editingFinished.connect(
            lambda: self._save("discord.artist_template", artist.text() or "{artist}")
        )
        album.editingFinished.connect(lambda: self._save("discord.album_template", album.text()))

        progress = QCheckBox(self.i18n.t("presence.progress"))
        progress.setChecked(bool(self.controller.config.get("discord.show_progress")))
        progress.toggled.connect(lambda value: self._save("discord.show_progress", value))
        card.layout_box.addWidget(progress)
        self.content_layout.addWidget(card)

    def _cover_card(self) -> None:
        card = Card()
        card.layout_box.addWidget(section_title(self.i18n.t("presence.cover_section")))
        self.cover_mode = self._combo(
            [
                (self.i18n.t("presence.cover_track"), "track"),
                (self.i18n.t("presence.cover_custom"), "custom"),
                (self.i18n.t("presence.cover_none"), "none"),
            ],
            self.controller.config.get("discord.cover_mode"),
        )
        card.layout_box.addWidget(self.cover_mode)

        self.cover_custom = QWidget()
        custom_layout = QVBoxLayout(self.cover_custom)
        custom_layout.setContentsMargins(0, 4, 0, 0)
        self.cover_url = QLineEdit(str(self.controller.config.get("discord.custom_cover_url", "")))
        self.cover_url.setPlaceholderText("https://example.com/cover.png")
        custom_layout.addWidget(row(self.i18n.t("presence.image_url"), self.cover_url))
        card.layout_box.addWidget(self.cover_custom)

        self.cover_custom.setVisible(self.cover_mode.currentData() == "custom")
        self.cover_mode.currentIndexChanged.connect(self._cover_mode_changed)
        self.cover_url.editingFinished.connect(
            lambda: self._save("discord.custom_cover_url", self.cover_url.text().strip())
        )
        self.cover_text_mode = self._combo(
            [
                (self.i18n.t("presence.hover_" + name), name)
                for name in ("album", "title", "artist", "custom", "none")
            ],
            self.controller.config.get("discord.cover_text_mode", "album"),
        )
        self.hover_controls = QWidget()
        hover_layout = QVBoxLayout(self.hover_controls)
        hover_layout.setContentsMargins(0, 0, 0, 0)
        hover_layout.addWidget(row(self.i18n.t("presence.hover_label"), self.cover_text_mode))
        self.hover_template = QLineEdit(
            str(self.controller.config.get("discord.cover_text_template", "{artist} • {title}"))
        )
        self.hover_template.setMinimumWidth(280)
        self.hover_row = row(self.i18n.t("presence.hover_custom_label"), self.hover_template)
        hover_layout.addWidget(self.hover_row)
        card.layout_box.addWidget(self.hover_controls)
        self.hover_row.setVisible(self.cover_text_mode.currentData() == "custom")
        self.cover_text_mode.currentIndexChanged.connect(self._hover_mode_changed)
        self.hover_template.editingFinished.connect(
            lambda: self._save("discord.cover_text_template", self.hover_template.text())
        )
        self.content_layout.addWidget(card)

    def _hover_mode_changed(self) -> None:
        mode = self.cover_text_mode.currentData()
        self.hover_row.setVisible(mode == "custom")
        self._save("discord.cover_text_mode", mode)

    def _cover_mode_changed(self) -> None:
        value = self.cover_mode.currentData()
        self.cover_custom.setVisible(value == "custom")
        self._save("discord.cover_mode", value)

    def _pause_card(self) -> None:
        card = Card()
        card.layout_box.addWidget(section_title(self.i18n.t("presence.pause_section")))
        pause = self._combo(
            [
                (self.i18n.t("presence.pause_show"), "show"),
                (self.i18n.t("presence.pause_hide"), "hide"),
            ],
            self.controller.config.get("discord.pause_behavior"),
        )
        card.layout_box.addWidget(pause)
        delay = self._combo(
            [
                (self.i18n.t("presence.immediately"), 0),
                (self.i18n.t("presence.seconds", value=10), 10),
                (self.i18n.t("presence.seconds", value=30), 30),
                (self.i18n.t("presence.minute"), 60),
                (self.i18n.t("presence.minutes", value=5), 300),
            ],
            self.controller.config.get("discord.pause_hide_delay_seconds"),
        )
        delay_row = row(self.i18n.t("presence.hide_after"), delay)
        card.layout_box.addWidget(delay_row)
        delay_row.setVisible(pause.currentData() == "hide")
        pause_text = QCheckBox(self.i18n.t("presence.show_pause_text"))
        pause_text.setChecked(bool(self.controller.config.get("discord.show_pause_text")))
        card.layout_box.addWidget(pause_text)
        pause.currentIndexChanged.connect(
            lambda: (
                delay_row.setVisible(pause.currentData() == "hide"),
                self._save("discord.pause_behavior", pause.currentData()),
            )
        )
        delay.currentIndexChanged.connect(
            lambda: self._save("discord.pause_hide_delay_seconds", delay.currentData())
        )
        pause_text.toggled.connect(lambda value: self._save("discord.show_pause_text", value))
        self.content_layout.addWidget(card)

    def _buttons_card(self) -> None:
        card = Card()
        card.layout_box.addWidget(section_title(self.i18n.t("presence.buttons_section")))
        self.links_enabled = QCheckBox(self.i18n.t("presence.links_enabled"))
        self.links_enabled.setChecked(
            bool(self.controller.config.get("discord.music_links_enabled", True))
        )
        card.layout_box.addWidget(self.links_enabled)
        self.link_options = QWidget()
        options = QVBoxLayout(self.link_options)
        options.setContentsMargins(20, 0, 0, 0)
        self.link_text = QCheckBox(self.i18n.t("presence.links_text"))
        self.link_button = QCheckBox(self.i18n.t("presence.links_button"))
        self.link_text.setChecked(bool(self.controller.config.get("discord.music_link_text", True)))
        self.link_button.setChecked(
            bool(self.controller.config.get("discord.music_link_button", True))
        )
        options.addWidget(self.link_text)
        options.addWidget(self.link_button)
        card.layout_box.addWidget(self.link_options)
        self.link_options.setVisible(self.links_enabled.isChecked())
        self.links_enabled.toggled.connect(self._music_links_toggled)
        self.link_text.toggled.connect(lambda value: self._save("discord.music_link_text", value))
        self.link_button.toggled.connect(
            lambda value: self._save("discord.music_link_button", value)
        )
        github = QCheckBox(self.i18n.t("presence.button_github"))
        github.setChecked(bool(self.controller.config.get("discord.button_github", True)))
        github.toggled.connect(lambda value: self._save("discord.button_github", value))
        card.layout_box.addWidget(github)
        self.content_layout.addWidget(card)

    def _music_links_toggled(self, enabled: bool) -> None:
        self.link_options.setVisible(enabled)
        self._save("discord.music_links_enabled", enabled)
