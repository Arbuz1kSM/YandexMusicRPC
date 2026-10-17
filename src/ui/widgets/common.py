from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class NoWheelComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view().setAutoFillBackground(True)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, *, subtle: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("SubtleCard" if subtle else "Card")
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(18, 16, 18, 16)
        self.layout_box.setSpacing(12)


def page_header(title: str, subtitle: str = "") -> tuple[QWidget, QVBoxLayout]:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    heading = QLabel(title)
    heading.setObjectName("PageTitle")
    layout.addWidget(heading)
    if subtitle:
        description = QLabel(subtitle)
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)
        layout.addWidget(description)
    return container, layout


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionTitle")
    return label


def muted(text: str, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(wrap)
    return label


def row(label_text: str, control: QWidget, hint: str | None = None) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    left = QVBoxLayout()
    label = QLabel(label_text)
    label.setWordWrap(True)
    left.addWidget(label)
    if hint:
        left.addWidget(muted(hint))
    layout.addLayout(left, 1)
    layout.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
    return widget
