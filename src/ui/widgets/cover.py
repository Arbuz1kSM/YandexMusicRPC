from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QLabel

from media.models import CoverKind, CoverRef
from utils.paths import resource_path


class CoverLabel(QLabel):
    def __init__(self, size: int = 132, radius: int = 14, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._radius = radius
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: #242936; border-radius: 14px;")
        self._placeholder_pixmap = QPixmap(str(resource_path("resources", "app_icon.png")))
        self._network = QNetworkAccessManager(self)
        self._network.finished.connect(self._downloaded)
        self._pending_url = ""
        self._current_key: tuple | None = None
        self._reply: QNetworkReply | None = None
        self._placeholder()

    @staticmethod
    def _key(cover: CoverRef | None) -> tuple | None:
        if cover is None or not cover.value:
            return None
        if isinstance(cover.value, bytes):
            return (cover.kind.value, len(cover.value), hash(cover.value))
        return (cover.kind.value, str(cover.value))

    def set_cover(self, cover: CoverRef | None) -> None:
        key = self._key(cover)
        if key == self._current_key:
            return
        self._current_key = key
        if self._reply is not None:
            self._reply.abort()
            self._reply = None
        self._pending_url = ""
        if cover is None or not cover.value:
            self._placeholder()
            return
        if cover.kind == CoverKind.BYTES and isinstance(cover.value, bytes):
            pixmap = QPixmap()
            if pixmap.loadFromData(QByteArray(cover.value)):
                self._set_pixmap(pixmap)
                return
        if cover.kind == CoverKind.URL and isinstance(cover.value, str):
            self._pending_url = cover.value
            request = QNetworkRequest(QUrl(cover.value))
            request.setRawHeader(b"User-Agent", b"YandexMusicRPC/1.0.0")
            self._placeholder()
            self._reply = self._network.get(request)
            self._reply.setProperty("cover_url", cover.value)
            return
        self._placeholder()

    def _downloaded(self, reply: QNetworkReply) -> None:
        requested_url = str(reply.property("cover_url") or "")
        is_current = requested_url and requested_url == self._pending_url
        if reply is self._reply:
            self._reply = None
        if reply.error() == QNetworkReply.NoError and is_current:
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()):
                self._set_pixmap(pixmap)
        reply.deleteLater()

    def _placeholder(self) -> None:
        if not self._placeholder_pixmap.isNull():
            self._set_pixmap(self._placeholder_pixmap)
        else:
            self.clear()

    def _set_pixmap(self, source: QPixmap) -> None:
        scaled = source.scaled(
            self._size,
            self._size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        result = QPixmap(self._size, self._size)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self._size, self._size, self._radius, self._radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.setText("")
        self.setPixmap(result)
