"""Light and dark application themes, plus the generated app icon."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPalette, QPixmap

ACCENT = "#dc2626"
ACCENT_HOVER = "#b91c1c"


def _theme_colors(dark: bool) -> dict[str, str]:
    values = {
        "text": ("#1f2937", "#e5e7eb"), "background": ("#f5f6f8", "#141b25"),
        "surface": ("#ffffff", "#202936"), "muted": ("#6b7280", "#a8b3c5"),
        "hover_text": ("#374151", "#e5e7eb"), "border": ("#e5e7eb", "#364152"),
        "button_border": ("#d1d5db", "#445064"), "hover": ("#f3f4f6", "#2c3848"),
        "selection": ("#fee2e2", "#572b35"), "disabled_surface": ("#f9fafb", "#1b2430"),
        "disabled_text": ("#9ca3af", "#8995a8"), "error_surface": ("#fef2f2", "#452631"),
        "status": ("#4b5563", "#bac4d3"), "error_text": (ACCENT_HOVER, "#fb7185"),
        "accent_text": (ACCENT, "#fb7185"),
    }
    return {name: pair[1 if dark else 0] for name, pair in values.items()}


def build_stylesheet(base_point_size: float, dark: bool = False) -> str:
    """Return the application stylesheet scaled to the platform's base font size.

    The font family is deliberately not set here: each platform keeps its own UI
    font (see app.py), and secondary text sizes are derived from the base size
    because the usual size differs between platforms (10 pt on Windows, 13 pt on macOS).
    """
    colors = _theme_colors(dark)
    small = round(base_point_size * 0.9, 1)
    large = round(base_point_size * 1.1, 1)
    stylesheet = f"""
QWidget {{
    color: {colors["text"]};
}}
QMainWindow, QDialog {{
    background: {colors["background"]};
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 10px 22px;
    color: {colors["muted"]};
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {colors["accent_text"]};
    border-bottom-color: {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: {colors["hover_text"]};
}}
QTabWidget#workspaceTabs > QTabBar::tab {{
    padding: 12px 16px;
}}
QListWidget {{
    background: {colors["surface"]};
    border: 1px solid {colors["border"]};
    border-radius: 10px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    border-radius: 6px;
    padding: 6px;
    color: {colors["text"]};
}}
QListWidget::item:hover {{
    background: {colors["hover"]};
}}
QListWidget::item:selected {{
    background: {colors["selection"]};
}}
QPushButton {{
    background: {colors["surface"]};
    border: 1px solid {colors["button_border"]};
    border-radius: 6px;
    padding: 7px 14px;
}}
QToolButton {{
    background: {colors["surface"]};
    border: 1px solid {colors["button_border"]};
    border-radius: 6px;
    padding: 7px 14px;
}}
QToolButton:hover {{
    background: {colors["hover"]};
}}
QToolButton::menu-indicator {{
    image: none;
}}
QPushButton:hover {{
    background: {colors["hover"]};
}}
QPushButton:pressed {{
    background: {colors["border"]};
}}
QPushButton:disabled {{
    color: {colors["disabled_text"]};
    background: {colors["disabled_surface"]};
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
    background: {colors["surface"]};
    border: 1px solid {colors["button_border"]};
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
    background: {colors["hover"]};
    color: {colors["disabled_text"]};
}}
QLineEdit[invalid="true"] {{
    border-color: {ACCENT};
    background: {colors["error_surface"]};
}}
QGroupBox {{
    background: {colors["surface"]};
    border: 1px solid {colors["border"]};
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
    color: {colors["muted"]};
    font-size: {small}pt;
}}
QLabel#error {{
    color: {colors["error_text"]};
    font-size: {small}pt;
}}
QLabel#fileTitle {{
    font-size: {large}pt;
    font-weight: 600;
}}
QProgressBar {{
    background: {colors["border"]};
    border: none;
    border-radius: 4px;
    min-height: 8px;
    max-height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 4px;
}}
QStatusBar {{
    color: {colors["status"]};
}}
QScrollArea#commandRibbon {{
    background: {colors["surface"]};
    border: 1px solid {colors["border"]};
    border-radius: 8px;
}}
QWidget#commandPanel {{
    background: {colors["surface"]};
}}
QToolButton#updateButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 5px 10px;
    font-weight: 600;
}}
QToolButton#updateButton:hover {{
    background: #b91c1c;
}}
QToolButton#commandButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 9px;
}}
QToolButton#commandButton:hover {{
    background: {colors["hover"]};
    border-color: {colors["border"]};
}}
QToolButton#commandButton:pressed {{
    background: {colors["selection"]};
}}
QToolButton#commandButton:focus {{
    border-color: {ACCENT};
}}
QLabel#commandCaption {{
    color: {colors["muted"]};
    font-size: {small}pt;
    font-weight: 600;
}}
QFrame#commandDivider {{
    color: {colors["border"]};
    max-width: 1px;
}}
QComboBox {{
    background: {colors["surface"]};
    border: 1px solid {colors["button_border"]};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
}}
QComboBox:disabled {{
    color: {colors["disabled_text"]};
}}
QToolButton:disabled {{
    color: {colors["disabled_text"]};
}}
QToolBar {{
    border: none;
    spacing: 8px;
    padding: 6px 12px;
}}
"""
    return stylesheet


def apply_theme(app, theme: str) -> None:
    scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(theme, Qt.ColorScheme.Unknown)
    app.styleHints().setColorScheme(scheme)
    dark = theme == "dark" or (theme == "system" and app.styleHints().colorScheme() == Qt.ColorScheme.Dark)
    palette = QPalette()
    values = {
        QPalette.ColorRole.Window: ("#f5f6f8", "#141b25"),
        QPalette.ColorRole.WindowText: ("#1f2937", "#e5e7eb"),
        QPalette.ColorRole.Base: ("#ffffff", "#202936"),
        QPalette.ColorRole.AlternateBase: ("#f3f4f6", "#2c3848"),
        QPalette.ColorRole.Text: ("#1f2937", "#e5e7eb"),
        QPalette.ColorRole.Button: ("#ffffff", "#202936"),
        QPalette.ColorRole.ButtonText: ("#1f2937", "#e5e7eb"),
        QPalette.ColorRole.Highlight: (ACCENT, ACCENT),
        QPalette.ColorRole.HighlightedText: ("#ffffff", "#ffffff"),
        QPalette.ColorRole.ToolTipBase: ("#ffffff", "#202936"),
        QPalette.ColorRole.ToolTipText: ("#1f2937", "#e5e7eb"),
        QPalette.ColorRole.PlaceholderText: ("#6b7280", "#a8b3c5"),
    }
    for role, colors in values.items():
        palette.setColor(role, QColor(colors[dark]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#8995a8" if dark else "#9ca3af"))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(app.font().pointSizeF(), dark))


_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def app_icon() -> QIcon:
    """Draw the application icon at runtime so the app ships without image assets."""
    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(_draw_app_icon(size))
    return icon


def _draw_app_icon(size: int) -> QPixmap:
    # Shapes only, no text: the icon file is made at build time without a window system,
    # where no fonts are available (letters came out as empty boxes).
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ACCENT))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    # A white page with its top right corner folded over.
    left, top, right, bottom = size * 0.25, size * 0.15, size * 0.75, size * 0.85
    fold = size * 0.16
    page = QPainterPath(QPointF(left, top))
    page.lineTo(right - fold, top)
    page.lineTo(right, top + fold)
    page.lineTo(right, bottom)
    page.lineTo(left, bottom)
    page.closeSubpath()
    painter.setBrush(QColor("white"))
    painter.drawPath(page)
    corner = QPainterPath(QPointF(right - fold, top))
    corner.lineTo(right - fold, top + fold)
    corner.lineTo(right, top + fold)
    corner.closeSubpath()
    painter.setBrush(QColor("#fca5a5"))
    painter.drawPath(corner)
    if size >= 24:  # text lines only where they stay distinct
        painter.setBrush(QColor(ACCENT))
        line = max(1.0, size * 0.055)
        for y, width in ((0.42, 0.34), (0.54, 0.34), (0.66, 0.22)):
            painter.drawRoundedRect(QRectF(left + size * 0.08, size * y, size * width, line), line / 2, line / 2)
    painter.end()
    return pixmap


def save_app_icon(target: Path) -> None:
    """Write the icon for the packaged app: a Windows .ico with every size, or a macOS .icns."""
    if target.suffix.lower() != ".ico":
        if not _draw_app_icon(1024).save(str(target)):
            raise OSError(f"Ikonu sa nepodarilo uložiť: {target}")
        return
    # Qt's ICO writer stores a single size, which Windows then scales blurrily in small views;
    # an ICO file can hold PNG images of each size instead.
    images = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        _draw_app_icon(size).save(buffer, "PNG")
        images.append((size, bytes(data.data())))
    offset = 6 + 16 * len(images)
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    for size, png in images:
        # Width and height 0 mean 256 in the ICO directory.
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    target.write_bytes(header + entries + b"".join(png for _, png in images))
