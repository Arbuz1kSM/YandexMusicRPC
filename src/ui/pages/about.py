from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets.common import Card, muted, page_header, row
from utils.paths import resource_path
from utils.version import APP_VERSION, AUTHOR, AUTHOR_URL


class AboutPage(QWidget):
    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)
        header, _ = page_header(i18n.t("about.title"), i18n.t("about.description"))
        root.addWidget(header)

        card = Card()
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(84, 84)
        pixmap = QPixmap(str(resource_path("resources", "app_icon.png")))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        card.layout_box.addWidget(logo, 0, Qt.AlignHCenter)

        author_markup = (
            f'<a href="{AUTHOR_URL}" style="color:#ff547e;text-decoration:none;">{AUTHOR}</a>'
        )
        author = QLabel(author_markup)
        author.setTextInteractionFlags(Qt.TextBrowserInteraction)
        author.setOpenExternalLinks(True)
        author.setStyleSheet("font-size: 18px; font-weight: 700;")
        author.setAlignment(Qt.AlignCenter)
        card.layout_box.addWidget(author)
        author_link = QLabel(author_markup)
        author_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        author_link.setOpenExternalLinks(True)
        card.layout_box.addWidget(row(i18n.t("about.author"), author_link))
        card.layout_box.addWidget(row(i18n.t("about.version"), QLabel(APP_VERSION)))

        actions = QHBoxLayout()
        open_github = QPushButton(i18n.t("settings.open_github"))
        open_logs = QPushButton(i18n.t("about.open_logs"))
        open_github.clicked.connect(controller.open_project)
        open_logs.clicked.connect(lambda: controller.open_path(controller.paths.log_dir))
        actions.addWidget(open_github)
        actions.addWidget(open_logs)
        card.layout_box.addLayout(actions)
        card.layout_box.addWidget(muted(i18n.t("about.legal")))
        root.addWidget(card)
        root.addStretch(1)
