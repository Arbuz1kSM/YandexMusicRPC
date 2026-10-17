from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from discord.rpc import DiscordStatus
from media.models import DataSource, PlaybackState, TrackInfo
from ui.widgets.common import Card, page_header
from ui.widgets.cover import CoverLabel


def _time(value: float | None) -> str:
    if value is None:
        return "--:--"
    value = max(0, int(value))
    return f"{value // 60:02d}:{value % 60:02d}"


class HomePage(QWidget):
    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n
        self._rpc_enabled = controller.engine.rpc_enabled
        self._discord_status = controller.discord_status.value
        self._api_status = "disabled"
        self._track: TrackInfo | None = None
        self._track_received_at = time.monotonic()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)
        header, header_layout = page_header(i18n.t("home.title"), i18n.t("home.subtitle"))
        status_row = QHBoxLayout()
        self.status = QLabel()
        self.rpc_button = QPushButton()
        self.rpc_button.setObjectName("Primary")
        self.rpc_button.clicked.connect(controller.toggle_rpc)
        status_row.addWidget(self.status)
        status_row.addStretch(1)
        status_row.addWidget(self.rpc_button)
        header_layout.addLayout(status_row)
        root.addWidget(header)

        card = Card()
        card.setMaximumWidth(1120)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content = QHBoxLayout()
        content.setSpacing(20)
        self.cover = CoverLabel(164, 18)
        content.addWidget(self.cover, 0, Qt.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(7)
        self.track_title = QLabel(i18n.t("home.no_track"))
        self.track_title.setObjectName("TrackTitle")
        self.track_title.setWordWrap(True)
        self.artist = QLabel(i18n.t("home.waiting"))
        self.artist.setObjectName("TrackArtist")
        self.album = QLabel("")
        self.album.setObjectName("Muted")
        right.addWidget(self.track_title)
        right.addWidget(self.artist)
        right.addWidget(self.album)
        right.addSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        times = QHBoxLayout()
        self.position = QLabel("--:--")
        self.duration = QLabel("--:--")
        self.position.setObjectName("Muted")
        self.duration.setObjectName("Muted")
        times.addWidget(self.position)
        times.addStretch(1)
        times.addWidget(self.duration)
        right.addWidget(self.progress)
        right.addLayout(times)
        right.addSpacing(6)
        self.playback = QLabel("")
        self.source = QLabel("")
        self.source.setObjectName("Muted")
        self.discord_line = QLabel("")
        self.discord_line.setObjectName("Muted")
        right.addWidget(self.playback)
        right.addWidget(self.source)
        right.addWidget(self.discord_line)

        badges = QHBoxLayout()
        self.windows_badge = QLabel(i18n.t("badge.windows"))
        self.yandex_badge = QLabel(i18n.t("badge.yandex"))
        self.discord_badge = QLabel(i18n.t("badge.discord"))
        for badge in (self.windows_badge, self.yandex_badge, self.discord_badge):
            badge.setObjectName("Badge")
            badges.addWidget(badge)
        badges.addStretch(1)
        right.addLayout(badges)
        content.addLayout(right, 1)
        card.layout_box.addLayout(content)
        root.addWidget(card, 0, Qt.AlignTop | Qt.AlignHCenter)
        root.addStretch(1)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(250)
        self._progress_timer.timeout.connect(self._refresh_progress)
        self._progress_timer.start()

        controller.track_changed.connect(self.set_track)
        controller.discord_status_changed.connect(self.set_discord_status)
        controller.api_status_changed.connect(self.set_api_status)
        controller.rpc_enabled_changed.connect(self.set_rpc_enabled)
        self.set_rpc_enabled(self._rpc_enabled)
        self.set_discord_status(self._discord_status, None)
        if controller.current_track:
            self.set_track(controller.current_track)

    def set_rpc_enabled(self, enabled: bool) -> None:
        self._rpc_enabled = enabled
        self.rpc_button.setText(
            self.i18n.t("home.rpc_on") if enabled else self.i18n.t("home.rpc_off")
        )
        if not enabled:
            self._show_status("home.rpc_disabled", "StatusWarning")

    def _show_status(self, key: str, object_name: str) -> None:
        self.status.setText("● " + self.i18n.t(key))
        self.status.setObjectName(object_name)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def set_discord_status(self, status: str, _error) -> None:
        self._discord_status = status
        if not self._rpc_enabled or status == DiscordStatus.DISABLED.value:
            self._show_status("home.rpc_disabled", "StatusWarning")
        elif status == DiscordStatus.CONNECTED.value:
            self._show_status("home.connected", "StatusConnected")
        elif status == DiscordStatus.RECONNECTING.value:
            self._show_status("home.reconnecting", "StatusWarning")
        elif status == DiscordStatus.NOT_FOUND.value:
            self._show_status("home.not_found", "StatusError")
        else:
            self._show_status("home.error", "StatusError")
        connected = status == DiscordStatus.CONNECTED.value
        self.discord_line.setText(
            self.i18n.t("home.discord_connected")
            if connected
            else self.i18n.t("home.discord_disconnected")
        )
        self.discord_badge.setVisible(connected)

    def set_track(self, track: TrackInfo | None) -> None:
        self._track = track
        self._track_received_at = time.monotonic()
        if track is None:
            self.cover.set_cover(None)
            self.track_title.setText(self.i18n.t("home.no_track"))
            self.artist.setText(self.i18n.t("home.waiting"))
            self.album.setText("")
            self.progress.setValue(0)
            self.position.setText("--:--")
            self.duration.setText("--:--")
            self.playback.setText("")
            self.source.setText("")
            self.yandex_badge.hide()
            return
        self.cover.set_cover(track.cover)
        self.track_title.setText(track.display_title)
        self.artist.setText(track.artist)
        self.album.setText(self.i18n.t("home.album", album=track.album) if track.album else "")
        self._refresh_progress()
        playback_key = {
            PlaybackState.PLAYING: "home.playing",
            PlaybackState.PAUSED: "home.paused",
            PlaybackState.STOPPED: "home.stopped",
        }.get(track.playback_state, "home.stopped")
        self.playback.setText(self.i18n.t(playback_key))
        advanced = track.source == DataSource.WINDOWS_YANDEX
        if (
            self.controller.config.get("source.mode") == "windows_yandex"
            and self._api_status == "unavailable"
        ):
            self.source.setText(self.i18n.t("home.api_unavailable"))
        else:
            self.source.setText(
                self.i18n.t("home.source_yandex")
                if advanced
                else self.i18n.t("home.source_windows")
            )
        self.yandex_badge.setVisible(advanced)

    def _refresh_progress(self) -> None:
        track = self._track
        if track is None:
            return
        position = track.position
        if position is not None and track.playback_state == PlaybackState.PLAYING:
            position += max(0.0, time.monotonic() - self._track_received_at)
        if position is not None and track.duration:
            position = min(position, track.duration)
            self.progress.setValue(int(min(1.0, position / track.duration) * 1000))
        else:
            self.progress.setValue(0)
        self.position.setText(_time(position))
        self.duration.setText(_time(track.duration))

    def set_api_status(self, status: str, _confidence) -> None:
        self._api_status = status
        if self.controller.current_track:
            self.set_track(self.controller.current_track)
