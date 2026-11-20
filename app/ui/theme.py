"""Application styling.

A calm, light "document scanner" look: neutral greys, one confident blue
accent, generous spacing and large touch-friendly targets.  Kept in one place
so the whole app stays visually consistent.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_PRESSED = "#1e40af"
DANGER = "#dc2626"
TEXT = "#111827"
TEXT_MUTED = "#6b7280"
BORDER = "#d7dbe3"
PANEL = "#ffffff"
CANVAS = "#eef1f5"

_STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QDialog {{
    background: {CANVAS};
}}
QToolBar {{
    background: {PANEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    spacing: 6px;
}}
QToolBar::separator {{
    background: {BORDER};
    width: 1px;
    margin: 6px 6px;
}}
QStatusBar {{
    background: {PANEL};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}
QStatusBar::item {{ border: none; }}

QPushButton {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 14px;
    min-height: 20px;
}}
QPushButton:hover {{ background: #f6f8fb; border-color: #c3c9d4; }}
QPushButton:pressed {{ background: #eceff5; }}
QPushButton:disabled {{ color: #a3a9b4; background: #f7f8fa; border-color: #e5e8ee; }}
QPushButton:checked {{ background: #e8efff; border-color: {ACCENT}; color: {ACCENT_PRESSED}; }}
QPushButton#emptyAddButton, QPushButton[variant="primary"] {{
    background: {ACCENT}; color: white; border: 1px solid {ACCENT};
    font-weight: 600; padding: 9px 20px;
}}
QPushButton#emptyAddButton:hover, QPushButton[variant="primary"]:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#emptyAddButton:pressed, QPushButton[variant="primary"]:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton#emptyAddButton:disabled, QPushButton[variant="primary"]:disabled {{ background: #b9c7e8; border-color: #b9c7e8; color: #f3f6ff; }}
QPushButton[variant="danger"] {{ color: {DANGER}; }}
QPushButton[flat="true"] {{ background: transparent; border: none; padding: 6px 10px; }}
QPushButton[flat="true"]:hover {{ background: #eceff5; }}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 6px 10px;
    color: {TEXT};
}}
QToolButton:hover {{ background: #eef1f6; }}
QToolButton:pressed {{ background: #e3e8f0; }}
QToolButton:checked {{ background: #e8efff; border-color: {ACCENT}; color: {ACCENT_PRESSED}; }}
QToolButton:disabled {{ color: #a3a9b4; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

QComboBox, QLineEdit, QSpinBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 10px;
    min-height: 20px;
    selection-background-color: {ACCENT};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: #c3c9d4; }}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {PANEL}; border: 1px solid {BORDER}; border-radius: 6px;
    selection-background-color: #e8efff; selection-color: {TEXT};
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; background: transparent; border: none; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid #b9c0cc; border-radius: 4px; background: white;
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: none; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}

QSplitter::handle {{ background: transparent; width: 6px; }}
QSplitter::handle:hover {{ background: #dfe4ec; }}

QListWidget {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    border: 1px solid transparent;
    border-radius: 6px;
    margin: 2px 0;
    padding: 0;
}}
QListWidget::item:selected {{ background: #e8efff; border-color: {ACCENT}; color: {TEXT}; }}
QListWidget::item:hover {{ background: #f2f5fa; }}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    background: {PANEL};
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
}}

QLabel[muted="true"] {{ color: {TEXT_MUTED}; }}
QLabel[heading="true"] {{ font-size: 15px; font-weight: 600; }}
QLabel[pill="true"] {{
    background: #eef1f6; border-radius: 9px; padding: 3px 9px;
    color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;
}}

QProgressBar {{
    background: #e9edf3; border: none; border-radius: 4px; height: 6px; text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: #c7cdd8; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #aeb6c4; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 4px; }}
QScrollBar::handle:horizontal {{ background: #c7cdd8; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QMenu {{
    background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px;
}}
QMenu::item {{ padding: 7px 26px 7px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: #eef2f9; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}

QToolTip {{
    background: #1f2937; color: white; border: none; padding: 6px 8px; border-radius: 5px;
}}
QMessageBox {{ background: {PANEL}; }}
QFileDialog QWidget {{ font-size: 13px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(CANVAS))
    palette.setColor(QPalette.ColorRole.Base, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f5f7fa"))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f2937"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setStyleSheet(_STYLESHEET)
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
