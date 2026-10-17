from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.pages.about import AboutPage
from ui.pages.home import HomePage
from ui.pages.logs import LogsPage
from ui.pages.presence import PresencePage
from ui.pages.settings import SettingsPage
from ui.pages.source import SourcePage
from ui.styles import apply_palette, stylesheet
from utils.paths import resource_path
from utils.version import APP_VERSION


class MainWindow(QMainWindow):
    NAV = (
        ("⌂", "nav.home", HomePage),
        ("♫", "nav.presence", PresencePage),
        ("⌁", "nav.source", SourcePage),
        ("⚙", "nav.settings", SettingsPage),
        ("≡", "nav.logs", LogsPage),
        ("ⓘ", "nav.about", AboutPage),
    )

    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n
        self._quitting = False
        self.setWindowTitle(i18n.t("app.title"))
        self.setWindowIcon(QIcon(str(resource_path("resources", "app_icon.ico"))))
        self.resize(1000, 680)
        self.setMinimumSize(760, 520)
        self._tray_available = False
        self._root = QWidget()
        self._root.setObjectName("Root")
        self.setCentralWidget(self._root)
        self.root_layout = QHBoxLayout(self._root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self._build()
        self.apply_theme(controller.config.get("application.theme", "dark"))
        controller.theme_changed.connect(self.apply_theme)
        controller.language_changed.connect(lambda _language: self.rebuild())
        controller.setting_changed.connect(self._setting_changed)

    def _build(self, selected: int = 0) -> None:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 22, 14, 18)
        sidebar_layout.setSpacing(6)
        brand = QLabel("♫  Yandex RPC")
        brand.setStyleSheet("font-size: 17px; font-weight: 750; padding: 8px;")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(14)

        self.stack = QStackedWidget()
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        for index, (icon, key, page_type) in enumerate(self.NAV):
            button = QPushButton(f"{icon}   {self.i18n.t(key)}")
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(
                lambda _checked=False, value=index: self.stack.setCurrentIndex(value)
            )
            self.buttons.addButton(button, index)
            sidebar_layout.addWidget(button)
            page = page_type(self.controller, self.i18n)
            self.stack.addWidget(page)
        sidebar_layout.addStretch(1)
        footer = QLabel(f"v{APP_VERSION}")
        footer.setObjectName("Muted")
        footer.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(footer)
        self.root_layout.addWidget(self.sidebar)
        self.root_layout.addWidget(self.stack, 1)
        selected = max(0, min(selected, len(self.NAV) - 1))
        self.buttons.button(selected).setChecked(True)
        self.stack.setCurrentIndex(selected)

    def rebuild(self) -> None:
        selected = self.stack.currentIndex()
        old_sidebar, old_stack = self.sidebar, self.stack
        self.root_layout.removeWidget(old_sidebar)
        self.root_layout.removeWidget(old_stack)
        old_sidebar.deleteLater()
        old_stack.deleteLater()
        self.setWindowTitle(self.i18n.t("app.title"))
        self._build(selected)

    def _setting_changed(self, key: str, _value) -> None:
        if key == "*":
            self.rebuild()

    def apply_theme(self, theme: str) -> None:
        resolved = theme
        if theme == "system":
            try:
                resolved = (
                    "light"
                    if QApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Light
                    else "dark"
                )
            except AttributeError:
                resolved = "dark"
        app = QApplication.instance()
        apply_palette(app, resolved)
        app.setStyleSheet(stylesheet(resolved))

    def set_tray_available(self, available: bool) -> None:
        self._tray_available = bool(available)

    def show_window(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting:
            event.accept()
            return
        if self._tray_available and self.controller.config.get("application.close_to_tray", True):
            event.ignore()
            self.hide()
        else:
            event.ignore()
            self.controller.exit()

    def force_close(self) -> None:
        self._quitting = True
        self.close()
