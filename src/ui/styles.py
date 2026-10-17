from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

PALETTES = {
    "dark": {
        "bg": "#0d0f14",
        "sidebar": "#11141b",
        "surface": "#171b24",
        "surface2": "#1d2330",
        "border": "#2a3140",
        "text": "#f4f6fb",
        "muted": "#8f98aa",
        "accent": "#ff3b5c",
        "accent2": "#ff8a38",
        "success": "#45d483",
        "warning": "#ffbd4a",
        "danger": "#ff5d6c",
    },
    "midnight": {
        "bg": "#080c16",
        "sidebar": "#0b1120",
        "surface": "#111a2b",
        "surface2": "#17233a",
        "border": "#253654",
        "text": "#f1f6ff",
        "muted": "#8ea0bc",
        "accent": "#4d8dff",
        "accent2": "#69b7ff",
        "success": "#42d69a",
        "warning": "#f4c45d",
        "danger": "#ff687e",
    },
    "graphite": {
        "bg": "#111214",
        "sidebar": "#17181b",
        "surface": "#1d1f23",
        "surface2": "#25282d",
        "border": "#363a40",
        "text": "#f4f4f4",
        "muted": "#9da1a8",
        "accent": "#ff8b3d",
        "accent2": "#ffb15c",
        "success": "#55cf82",
        "warning": "#f2bd52",
        "danger": "#ff6464",
    },
    "ocean": {
        "bg": "#071317",
        "sidebar": "#0a1a20",
        "surface": "#10262d",
        "surface2": "#17343d",
        "border": "#27515d",
        "text": "#ecfbff",
        "muted": "#89aeb8",
        "accent": "#20c7d9",
        "accent2": "#4de3c1",
        "success": "#49d49b",
        "warning": "#ffd166",
        "danger": "#ff667a",
    },
    "violet": {
        "bg": "#100b17",
        "sidebar": "#160f20",
        "surface": "#21152f",
        "surface2": "#2c1d3e",
        "border": "#49305f",
        "text": "#fbf4ff",
        "muted": "#b29ac1",
        "accent": "#a866ff",
        "accent2": "#e461c7",
        "success": "#5bd69d",
        "warning": "#f4bf62",
        "danger": "#ff668c",
    },
    "forest": {
        "bg": "#09130f",
        "sidebar": "#0e1a14",
        "surface": "#14251c",
        "surface2": "#1d3227",
        "border": "#345241",
        "text": "#effaf3",
        "muted": "#94b3a0",
        "accent": "#43c982",
        "accent2": "#7adc9b",
        "success": "#43c982",
        "warning": "#e8c05d",
        "danger": "#ff6c70",
    },
    "sunset": {
        "bg": "#160d0d",
        "sidebar": "#1e1112",
        "surface": "#2a1718",
        "surface2": "#382021",
        "border": "#593334",
        "text": "#fff6f2",
        "muted": "#c2a19b",
        "accent": "#ff5d67",
        "accent2": "#ff9b52",
        "success": "#55d18b",
        "warning": "#ffc55f",
        "danger": "#ff5d67",
    },
    "light": {
        "bg": "#f4f6fa",
        "sidebar": "#ffffff",
        "surface": "#ffffff",
        "surface2": "#edf0f6",
        "border": "#dce1ea",
        "text": "#161922",
        "muted": "#687184",
        "accent": "#e7284b",
        "accent2": "#f47d2b",
        "success": "#159b55",
        "warning": "#b97800",
        "danger": "#d52f45",
    },
}


def apply_palette(app, theme: str = "dark") -> None:

    c = PALETTES.get(theme, PALETTES["dark"])
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["bg"]))
    palette.setColor(QPalette.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.Base, QColor(c["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["surface2"]))
    palette.setColor(QPalette.Text, QColor(c["text"]))
    palette.setColor(QPalette.Button, QColor(c["surface2"]))
    palette.setColor(QPalette.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.Highlight, QColor(c["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    app.setPalette(palette)


def stylesheet(theme: str = "dark") -> str:
    c = PALETTES.get(theme, PALETTES["dark"])
    return f"""
    * {{ font-family: 'Segoe UI Variable', 'Segoe UI'; font-size: 13px; }}
    QMainWindow, QDialog, QWidget#Root {{ background: {c["bg"]}; color: {c["text"]}; }}
    QWidget {{ color: {c["text"]}; }}
    QFrame#Sidebar {{ background: {c["sidebar"]}; border-right: 1px solid {c["border"]}; }}
    QFrame#Card {{ background: {c["surface"]}; border: 1px solid {c["border"]}; border-radius: 14px; }}
    QFrame#SubtleCard {{ background: {c["surface2"]}; border: 1px solid {c["border"]}; border-radius: 11px; }}
    QLabel#PageTitle {{ font-size: 26px; font-weight: 700; }}
    QLabel#PageSubtitle, QLabel#Muted {{ color: {c["muted"]}; }}
    QLabel#SectionTitle {{ font-size: 16px; font-weight: 650; }}
    QLabel#TrackTitle {{ font-size: 23px; font-weight: 700; }}
    QLabel#TrackArtist {{ font-size: 16px; color: {c["muted"]}; }}
    QLabel#Badge {{ background: {c["surface2"]}; color: {c["muted"]}; border: 1px solid {c["border"]}; border-radius: 7px; padding: 3px 8px; font-size: 10px; font-weight: 700; }}
    QLabel#StatusConnected {{ color: {c["success"]}; font-weight: 650; }}
    QLabel#StatusWarning {{ color: {c["warning"]}; font-weight: 650; }}
    QLabel#StatusError {{ color: {c["danger"]}; font-weight: 650; }}
    QPushButton {{ color: {c["text"]}; background-color: {c["surface2"]}; border: 1px solid {c["border"]}; border-radius: 9px; padding: 8px 13px; font-weight: 600; }}
    QPushButton:hover {{ border-color: {c["accent"]}; background: {c["surface"]}; }}
    QPushButton:pressed {{ background: {c["border"]}; }}
    QPushButton#Primary {{ color: #ffffff; background-color: {c["accent"]}; border: 1px solid {c["accent"]}; padding: 10px 18px; }}
    QPushButton#Primary:hover {{ background-color: {c["accent2"]}; border-color: {c["accent2"]}; }}
    QPushButton#Primary:disabled {{ color: {c["muted"]}; background-color: {c["surface2"]}; border: 1px solid {c["border"]}; }}
    QPushButton#Danger {{ color: #ffffff; background-color: {c["danger"]}; border: 1px solid {c["danger"]}; padding: 9px 16px; }}
    QPushButton#Danger:hover {{ background-color: {c["accent2"]}; border-color: {c["accent2"]}; }}
    QPushButton#Danger:disabled {{ color: {c["muted"]}; background-color: {c["surface2"]}; border: 1px solid {c["border"]}; }}
    QPushButton#Nav {{ text-align: left; border: none; background: transparent; color: {c["muted"]}; padding: 10px 13px; font-size: 14px; }}
    QPushButton#Nav:hover {{ color: {c["text"]}; background: {c["surface2"]}; }}
    QPushButton#Nav:checked {{ color: {c["text"]}; background: {c["surface2"]}; border-left: 3px solid {c["accent"]}; }}
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{ background: {c["surface2"]}; border: 1px solid {c["border"]}; border-radius: 8px; padding: 7px 9px; selection-background-color: {c["accent"]}; }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {c["accent"]}; }}
    QComboBox::drop-down {{ border: none; width: 25px; }}
    QComboBox QAbstractItemView {{ color: {c["text"]}; background-color: {c["surface"]}; border: 1px solid {c["border"]}; selection-color: #ffffff; selection-background-color: {c["accent"]}; outline: 0; }}
    QComboBox QAbstractItemView::item {{ color: {c["text"]}; background-color: {c["surface"]}; min-height: 28px; padding: 4px 8px; }}
    QComboBox QAbstractItemView::item:selected {{ color: #ffffff; background-color: {c["accent"]}; }}
    QCheckBox, QRadioButton {{ spacing: 9px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; border: 1px solid {c["border"]}; background: {c["surface2"]}; }}
    QCheckBox::indicator:checked {{ background: {c["accent"]}; border-color: {c["accent"]}; }}
    QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 10px; border: 2px solid {c["border"]}; background: {c["surface2"]}; }}
    QRadioButton::indicator:checked {{ background: {c["accent"]}; border: 4px solid {c["surface2"]}; }}
    QProgressBar {{ background: {c["surface2"]}; border: none; border-radius: 4px; height: 7px; }}
    QProgressBar::chunk {{ background: {c["accent"]}; border-radius: 4px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QWidget#ScrollContent {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c["border"]}; border-radius: 4px; min-height: 30px; }}
    QToolTip {{ background: {c["surface"]}; color: {c["text"]}; border: 1px solid {c["border"]}; padding: 6px; }}
    """
