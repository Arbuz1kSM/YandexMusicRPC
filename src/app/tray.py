from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from media.models import TrackInfo
from utils.paths import resource_path


class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller, window, i18n, parent=None) -> None:
        icon = QIcon(str(resource_path("resources", "app_icon.ico")))
        if icon.isNull():
            icon = QIcon(str(resource_path("resources", "app_icon.png")))
        super().__init__(icon, parent)
        self.setIcon(icon)
        self.controller = controller
        self.window = window
        self.i18n = i18n
        self.setToolTip(i18n.t("tray.header"))
        self.menu = QMenu(window)
        self.header = QAction(i18n.t("tray.header"), self.menu)
        self.header.setEnabled(False)
        self.now_playing = QAction(i18n.t("tray.nothing"), self.menu)
        self.now_playing.setEnabled(False)
        self.rpc_state = QAction(i18n.t("tray.rpc_enabled"), self.menu)
        self.rpc_state.setCheckable(True)
        self.rpc_state.setChecked(controller.engine.rpc_enabled)
        self.rpc_state.triggered.connect(controller.toggle_rpc)
        self.open_action = QAction(i18n.t("tray.open"), self.menu)
        self.open_action.triggered.connect(window.show_window)
        self.reconnect = QAction(i18n.t("tray.reconnect"), self.menu)
        self.reconnect.triggered.connect(controller.reconnect_discord)
        self.toggle_rpc = QAction(
            i18n.t("tray.stop") if controller.engine.rpc_enabled else i18n.t("tray.start"),
            self.menu,
        )
        self.toggle_rpc.triggered.connect(controller.toggle_rpc)
        self.exit_action = QAction(i18n.t("tray.exit"), self.menu)
        self.exit_action.triggered.connect(controller.exit)
        self._populate()
        self.setContextMenu(self.menu)
        self.activated.connect(self._activated)
        controller.track_changed.connect(self._track)
        controller.rpc_enabled_changed.connect(self._rpc_enabled)
        controller.language_changed.connect(lambda _language: self.retranslate())

    def _populate(self) -> None:
        self.menu.clear()
        self.menu.addAction(self.header)
        self.menu.addAction(self.now_playing)
        self.menu.addSeparator()
        self.menu.addAction(self.rpc_state)
        self.menu.addSeparator()
        self.menu.addAction(self.open_action)
        self.menu.addAction(self.reconnect)
        self.menu.addAction(self.toggle_rpc)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.window.show_window()

    def retranslate(self) -> None:
        self.header.setText(self.i18n.t("tray.header"))
        if self.controller.current_track:
            self._track(self.controller.current_track)
        else:
            self.now_playing.setText(self.i18n.t("tray.nothing"))
        self.rpc_state.setText(self.i18n.t("tray.rpc_enabled"))
        self.open_action.setText(self.i18n.t("tray.open"))
        self.reconnect.setText(self.i18n.t("tray.reconnect"))
        self.exit_action.setText(self.i18n.t("tray.exit"))
        self._rpc_enabled(self.controller.engine.rpc_enabled)

    def _track(self, track: TrackInfo | None) -> None:
        if track:
            text = f"{track.artist} - {track.display_title}"
            self.now_playing.setText(self.i18n.t("tray.now_playing", track=text))
            self.setToolTip(text)
        else:
            self.now_playing.setText(self.i18n.t("tray.nothing"))
            self.setToolTip(self.i18n.t("tray.header"))

    def _rpc_enabled(self, enabled: bool) -> None:
        self.rpc_state.setChecked(enabled)
        self.toggle_rpc.setText(self.i18n.t("tray.stop") if enabled else self.i18n.t("tray.start"))
