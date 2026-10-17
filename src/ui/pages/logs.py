from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.common import NoWheelComboBox, page_header


class LogsPage(QWidget):
    LEVELS = ("DEBUG", "INFO", "MEDIA", "API", "RPC", "WARNING", "ERROR")

    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n
        self._records = list(controller.log_records)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        header, _ = page_header(i18n.t("logs.title"), i18n.t("logs.subtitle"))
        root.addWidget(header)

        tools = QHBoxLayout()
        self.level = NoWheelComboBox()
        self.level.addItem(i18n.t("common.all"), "*")
        for level in self.LEVELS:
            self.level.addItem(level, level)
        self.level.currentIndexChanged.connect(self._rebuild)
        self.autoscroll = QCheckBox(i18n.t("logs.autoscroll"))
        self.autoscroll.setChecked(True)
        clear = QPushButton(i18n.t("common.clear"))
        copy = QPushButton(i18n.t("logs.copy"))
        open_file = QPushButton(i18n.t("logs.open_file"))
        save = QPushButton(i18n.t("logs.save"))
        clear.clicked.connect(self._clear)
        copy.clicked.connect(self._copy)
        open_file.clicked.connect(lambda: controller.open_path(controller.paths.log_file))
        save.clicked.connect(self._save)
        tools.addWidget(self.level)
        tools.addWidget(self.autoscroll)
        tools.addStretch(1)
        tools.addWidget(clear)
        tools.addWidget(copy)
        tools.addWidget(open_file)
        tools.addWidget(save)
        root.addLayout(tools)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setStyleSheet("font-family: 'Cascadia Mono', Consolas; font-size: 12px;")
        root.addWidget(self.editor, 1)
        controller.log_added.connect(self._append)
        self._rebuild()

    def _allowed(self, record) -> bool:
        selected = self.level.currentData()
        return selected == "*" or record.level == selected

    def _append(self, record) -> None:
        self._records.append(record)
        if self._allowed(record):
            self.editor.appendPlainText(record.line)
            if self.autoscroll.isChecked():
                self.editor.moveCursor(QTextCursor.End)

    def _rebuild(self) -> None:
        self.editor.setPlainText(
            "\n".join(item.line for item in self._records if self._allowed(item))
        )
        if self.autoscroll.isChecked():
            self.editor.moveCursor(QTextCursor.End)

    def _clear(self) -> None:
        self._records.clear()
        self.editor.clear()

    def _copy(self) -> None:
        self.editor.selectAll()
        self.editor.copy()
        self.editor.moveCursor(QTextCursor.End)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, self.i18n.t("dialog.save_log"), "YandexMusicRPC-log.txt", "Text (*.txt)"
        )
        if path:
            Path(path).write_text(self.editor.toPlainText() + "\n", encoding="utf-8")
