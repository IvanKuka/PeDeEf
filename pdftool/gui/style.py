"""Visual theme: a light stylesheet with a red accent, plus the generated app icon."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

ACCENT = "#dc2626"
ACCENT_HOVER = "#b91c1c"


def build_stylesheet(base_point_size: float) -> str:
    """Return the application stylesheet scaled to the platform's base font size.

    The font family is deliberately not set here: each platform keeps its own UI
    font (see app.py), and secondary text sizes are derived from the base size
    because the usual size differs between platforms (10 pt on Windows, 13 pt on macOS).
    """
    small = round(base_point_size * 0.9, 1)
    large = round(base_point_size * 1.1, 1)
    return f"""
QWidget {{
    color: #1f2937;
}}
QMainWindow, QDialog {{
    background: #f5f6f8;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 10px 22px;
    color: #6b7280;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom-color: {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: #374151;
}}
QListWidget {{
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    border-radius: 6px;
    padding: 6px;
    color: #1f2937;
}}
QListWidget::item:hover {{
    background: #f3f4f6;
}}
QListWidget::item:selected {{
    background: #fee2e2;
}}
QPushButton {{
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background: #f3f4f6;
}}
QPushButton:pressed {{
    background: #e5e7eb;
}}
QPushButton:disabled {{
    color: #9ca3af;
    background: #f9fafb;
}}
QPushButton#primary {{
    background: {ACCENT};
    border: none;
    color: white;
    font-weight: 600;
    padding: 10px 22px;
}}
QPushButton#primary:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton#primary:disabled {{
    background: #fca5a5;
}}
QLineEdit {{
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 8px;
}}
QSpinBox QLineEdit {{
    /* QSpinBox keeps the native Fusion look (styling its frame breaks the inner
       editor's layout); its internal editor must not inherit the QLineEdit rules. */
    border: none;
    padding: 0;
    background: transparent;
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled {{
    background: #f3f4f6;
    color: #9ca3af;
}}
QLineEdit[invalid="true"] {{
    border-color: {ACCENT};
    background: #fef2f2;
}}
QGroupBox {{
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
QLabel#hint {{
    color: #6b7280;
    font-size: {small}pt;
}}
QLabel#error {{
    color: {ACCENT_HOVER};
    font-size: {small}pt;
}}
QLabel#fileTitle {{
    font-size: {large}pt;
    font-weight: 600;
}}
QStatusBar {{
    color: #4b5563;
}}
"""


def app_icon() -> QIcon:
    """Draw the application icon at runtime so the app ships without image assets."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT))
        painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.2, size * 0.2)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(max(6, round(size * 0.3)))
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "PDF")
        painter.end()
        icon.addPixmap(pixmap)
    return icon
