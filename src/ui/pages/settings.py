from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.common import Card, NoWheelComboBox, muted, page_header, row, section_title


class SettingsPage(QWidget):
    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        header, _ = page_header(i18n.t("settings.title"), i18n.t("settings.subtitle"))
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setObjectName("ScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(14)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        general = Card()
        general.layout_box.addWidget(section_title(i18n.t("settings.general")))
        options = [
            ("application.start_with_windows", "settings.start_windows"),
            ("application.start_minimized", "settings.start_minimized"),
            ("application.close_to_tray", "settings.close_tray"),
        ]
        for key, label_key in options:
            box = QCheckBox(i18n.t(label_key))
            box.setChecked(bool(controller.config.get(key)))
            box.toggled.connect(lambda value, name=key: controller.set_setting(name, value))
            general.layout_box.addWidget(box)

        language = NoWheelComboBox()
        language.setMinimumWidth(170)
        language.addItem(i18n.t("settings.russian"), "ru")
        language.addItem(i18n.t("settings.english"), "en")
        language.setCurrentIndex(
            max(0, language.findData(controller.config.get("application.language")))
        )
        language.currentIndexChanged.connect(
            lambda: controller.set_setting("application.language", language.currentData())
        )
        general.layout_box.addWidget(row(i18n.t("settings.language"), language))

        theme = NoWheelComboBox()
        theme.setMinimumWidth(170)
        themes = [
            ("settings.theme_system", "system"),
            ("settings.theme_dark", "dark"),
            ("settings.theme_midnight", "midnight"),
            ("settings.theme_graphite", "graphite"),
            ("settings.theme_ocean", "ocean"),
            ("settings.theme_violet", "violet"),
            ("settings.theme_forest", "forest"),
            ("settings.theme_sunset", "sunset"),
            ("settings.theme_light", "light"),
        ]
        for key, value in themes:
            theme.addItem(i18n.t(key), value)
        theme.setCurrentIndex(max(0, theme.findData(controller.config.get("application.theme"))))
        theme.currentIndexChanged.connect(
            lambda: controller.set_setting("application.theme", theme.currentData())
        )
        general.layout_box.addWidget(row(i18n.t("settings.theme"), theme))

        content_layout.addWidget(general)

        reset_card = Card()
        reset_card.layout_box.addWidget(section_title(i18n.t("settings.reset_section")))
        reset_card.layout_box.addWidget(muted(i18n.t("settings.reset_hint")))
        actions = QHBoxLayout()
        actions.addStretch(1)
        reset = QPushButton(i18n.t("settings.reset"))
        reset.setObjectName("Danger")
        reset.clicked.connect(self._reset)
        actions.addWidget(reset)
        reset_card.layout_box.addLayout(actions)
        content_layout.addWidget(reset_card)
        content_layout.addStretch(1)

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            self.i18n.t("settings.reset"),
            self.i18n.t("settings.reset_confirm"),
        )
        if answer == QMessageBox.Yes:
            self.controller.config.reset()
