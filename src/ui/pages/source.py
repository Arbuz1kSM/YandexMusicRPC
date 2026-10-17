from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.common import Card, muted, page_header, row, section_title


class SourcePage(QWidget):
    def __init__(self, controller, i18n, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.i18n = i18n
        self._verification_url = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        header, _ = page_header(i18n.t("source.title"), i18n.t("source.subtitle"))
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

        mode_card = Card()
        self.group = QButtonGroup(self)
        self.windows = QRadioButton(i18n.t("source.windows"))
        self.advanced = QRadioButton(i18n.t("source.advanced"))
        self.group.addButton(self.windows)
        self.group.addButton(self.advanced)
        mode = controller.config.get("source.mode", "windows")
        self.windows.setChecked(mode == "windows")
        self.advanced.setChecked(mode == "windows_yandex")
        mode_card.layout_box.addWidget(self.windows)
        mode_card.layout_box.addWidget(muted(i18n.t("source.windows_desc")))
        mode_card.layout_box.addSpacing(5)
        mode_card.layout_box.addWidget(self.advanced)
        mode_card.layout_box.addWidget(muted(i18n.t("source.advanced_desc")))
        mode_card.layout_box.addWidget(muted("✓ " + i18n.t("source.fallback")))
        content_layout.addWidget(mode_card)
        self.windows.toggled.connect(self._mode_changed)

        auth_card = Card()
        auth_card.layout_box.addWidget(section_title(i18n.t("source.yandex_auth")))
        auth_card.layout_box.addWidget(muted(i18n.t("source.yandex_auth_hint")))

        self.auth_status = QLabel(i18n.t("source.auth_checking"))
        self.auth_status.setObjectName("Muted")
        self.auth_status.setWordWrap(True)
        auth_card.layout_box.addWidget(self.auth_status)

        auth_actions = QHBoxLayout()
        self.sign_in = QPushButton(i18n.t("source.sign_in"))
        self.sign_in.setObjectName("Primary")
        self.sign_out = QPushButton(i18n.t("source.sign_out"))
        self.sign_out.hide()
        self.sign_in.clicked.connect(controller.start_yandex_login)
        self.sign_out.clicked.connect(controller.delete_token)
        auth_actions.addWidget(self.sign_in)
        auth_actions.addWidget(self.sign_out)
        auth_actions.addStretch(1)
        auth_card.layout_box.addLayout(auth_actions)

        self.code_box = QWidget()
        code_layout = QVBoxLayout(self.code_box)
        code_layout.setContentsMargins(0, 4, 0, 0)
        code_layout.setSpacing(8)
        self.code_hint = QLabel(i18n.t("source.auth_code_hint"))
        self.code_hint.setWordWrap(True)
        code_layout.addWidget(self.code_hint)
        code_row = QHBoxLayout()
        self.auth_code = QLineEdit()
        self.auth_code.setReadOnly(True)
        self.auth_code.setPlaceholderText("XXXX-XXXX")
        self.copy_code = QPushButton(i18n.t("source.copy_code"))
        self.open_auth = QPushButton(i18n.t("source.open_auth"))
        self.copy_code.clicked.connect(self._copy_code)
        self.open_auth.clicked.connect(self._open_auth)
        code_row.addWidget(self.auth_code, 1)
        code_row.addWidget(self.copy_code)
        code_row.addWidget(self.open_auth)
        code_layout.addLayout(code_row)
        self.code_box.hide()
        auth_card.layout_box.addWidget(self.code_box)

        self.manual_toggle = QPushButton(i18n.t("source.auth_advanced"))
        self.manual_toggle.setCheckable(True)
        auth_card.layout_box.addWidget(self.manual_toggle)

        self.manual_box = QWidget()
        manual_layout = QVBoxLayout(self.manual_box)
        manual_layout.setContentsMargins(0, 2, 0, 0)
        manual_layout.setSpacing(8)
        manual_layout.addWidget(muted(i18n.t("source.manual_token_hint")))
        token_row = QHBoxLayout()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText(i18n.t("source.token_placeholder"))
        save_token = QPushButton(i18n.t("source.save_token"))
        save_token.clicked.connect(lambda: controller.save_token(self.token.text()))
        token_row.addWidget(self.token, 1)
        token_row.addWidget(save_token)
        manual_layout.addLayout(token_row)
        self.manual_box.hide()
        self.manual_toggle.toggled.connect(self._manual_auth_toggled)
        auth_card.layout_box.addWidget(self.manual_box)
        content_layout.addWidget(auth_card)

        controller.token_result.connect(self._token_result)
        controller.yandex_auth_code.connect(self._auth_code_ready)
        controller.yandex_auth_status.connect(self._auth_status_changed)
        controller.yandex_auth_busy.connect(self._auth_busy_changed)
        QTimer.singleShot(0, controller.refresh_yandex_auth_status)

        discord_card = Card()
        discord_card.layout_box.addWidget(section_title(i18n.t("source.discord_section")))
        self.app_id = QLineEdit(str(controller.config.get("discord.application_id", "")))
        self.app_id.setMinimumWidth(320)
        self.app_id.setPlaceholderText("123456789012345678")
        self.app_id.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,20}")))
        self.registered_name = QLineEdit(
            str(controller.config.get("discord.registered_activity_name", "Яндекс Музыка"))
        )
        self.registered_name.setMinimumWidth(280)
        self.registered_name.setMaxLength(128)
        controller.setting_changed.connect(self._sync_activity_name)
        discord_card.layout_box.addWidget(row(i18n.t("source.application_id"), self.app_id))
        discord_card.layout_box.addWidget(
            row(i18n.t("source.registered_name"), self.registered_name)
        )
        actions = QHBoxLayout()
        portal = QPushButton(i18n.t("source.open_portal"))
        self.save_id = QPushButton(i18n.t("source.save_id"))
        self.save_id.setMinimumHeight(38)
        portal.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://discord.com/developers/applications"))
        )
        self.save_id.clicked.connect(self._save_id)
        actions.addWidget(portal)
        actions.addStretch(1)
        actions.addWidget(self.save_id)
        discord_card.layout_box.addLayout(actions)
        content_layout.addWidget(discord_card)
        content_layout.addStretch(1)
        self._save_pending = False
        controller.discord_status_changed.connect(self._save_connection_status)

    def _sync_activity_name(self, key, value) -> None:
        if key == "discord.registered_activity_name":
            self.registered_name.setText(str(value))

    def _mode_changed(self, windows_checked: bool) -> None:
        self.controller.set_setting(
            "source.mode", "windows" if windows_checked else "windows_yandex"
        )

    def _save_id(self) -> None:
        application_id = self.app_id.text().strip()
        if not application_id.isdigit() or not 17 <= len(application_id) <= 20:
            QMessageBox.warning(
                self,
                self.i18n.t("dialog.error"),
                self.i18n.t("source.invalid_application_id"),
            )
            return

        self._save_pending = True
        self.save_id.setEnabled(False)
        self.save_id.setText(self.i18n.t("source.reconnecting"))
        self.controller.set_setting("discord.application_id", application_id)
        self.controller.set_setting(
            "discord.registered_activity_name",
            self.registered_name.text().strip() or "Яндекс Музыка",
        )
        self.controller.reconnect_discord()
        QTimer.singleShot(10_000, self._finish_save)

    def _save_connection_status(self, status: str, _error) -> None:
        if not self._save_pending:
            return
        if status == "connected":
            self.save_id.setText(self.i18n.t("source.saved_reconnected"))
            QTimer.singleShot(1200, self._finish_save)
        elif status in {"error", "not_found"}:
            self._finish_save()

    def _finish_save(self) -> None:
        if not getattr(self, "_save_pending", False):
            return
        self._save_pending = False
        self.save_id.setEnabled(True)
        self.save_id.setText(self.i18n.t("source.save_id"))

    def _copy_code(self) -> None:
        code = self.auth_code.text().strip()
        if code:
            QApplication.clipboard().setText(code)

    def _open_auth(self) -> None:
        if self._verification_url:
            QDesktopServices.openUrl(QUrl(self._verification_url))

    def _auth_code_ready(self, code: str, verification_url: str, expires_in: int) -> None:
        self._verification_url = verification_url
        self.auth_code.setText(code)
        self.code_hint.setText(
            self.i18n.t("source.auth_code_hint").replace("{seconds}", str(expires_in))
        )
        self.code_box.show()
        self.auth_status.setText(self.i18n.t("source.auth_waiting"))

    def _set_auth_controls(self, authorized: bool) -> None:
        self.sign_in.setVisible(not authorized)
        self.sign_out.setVisible(authorized)
        self.sign_out.setEnabled(authorized)

    def _auth_status_changed(self, authorized: bool, _detail) -> None:
        if authorized:
            self.auth_status.setText("● " + self.i18n.t("source.auth_authorized"))
            self.code_box.hide()
        else:
            self.auth_status.setText("○ " + self.i18n.t("source.auth_not_authorized"))
        self._set_auth_controls(authorized)

    def _auth_busy_changed(self, busy: bool) -> None:
        if busy:
            self.sign_out.hide()
            self.sign_in.show()
            self.sign_in.setEnabled(False)
            self.sign_in.setText(self.i18n.t("source.auth_waiting_button"))
        else:
            self.sign_in.setEnabled(True)
            self.sign_in.setText(self.i18n.t("source.sign_in"))

    def _manual_auth_toggled(self, expanded: bool) -> None:
        self.manual_box.setVisible(expanded)
        self.manual_toggle.setText(
            self.i18n.t("source.auth_hide_advanced")
            if expanded
            else self.i18n.t("source.auth_advanced")
        )

    def _token_result(self, success: bool, action: str) -> None:
        if success:
            self.token.clear()
            if action == "deleted":
                self.auth_status.setText("○ " + self.i18n.t("source.auth_not_authorized"))
                self.code_box.hide()
                self._set_auth_controls(False)
            elif action == "signed_in":
                self.auth_status.setText("● " + self.i18n.t("source.auth_authorized"))
                self.code_box.hide()
                self._set_auth_controls(True)
            else:
                self.auth_status.setText("● " + self.i18n.t("source.token_saved"))
                self.controller.refresh_yandex_auth_status()
        else:
            if action == "yandex_auth_timeout":
                message = self.i18n.t("source.auth_timeout")
            else:
                message = self.i18n.t("source.auth_failed").replace("{error}", action)
            self.auth_status.setText("⚠ " + message)
