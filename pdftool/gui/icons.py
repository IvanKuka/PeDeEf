"""Small, consistent vector icons for document commands; no external assets required."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_PATHS = {
    "open": "M3 7h7l2 2h9l-3 11H3z M3 7V4h7l2 3",
    "save": "M4 3h14l3 3v15H3V3z M7 3v6h10V3 M7 21v-8h10v8",
    "close": "M6 6l12 12 M18 6L6 18",
    "undo": "M8 4L3 9l5 5 M3 9h10a7 7 0 0 1 7 7v3",
    "redo": "M16 4l5 5-5 5 M21 9h-10a7 7 0 0 0-7 7v3",
    "rotate-left": "M3 3v6h6 M3 9a9 9 0 1 1 0 6",
    "rotate-right": "M21 3v6h-6 M21 9a9 9 0 1 0 0 6",
    "copy": "M9 8h12v13H9z M15 8V3H3v13h6",
    "delete": "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7",
    "insert": "M13 21H4V3h10l5 5v4 M14 3v5h5 M18 15v6 M15 18h6",
    "extract": "M12 21H4V3h10l5 5v3 M14 3v5h5 M13 16h9 M18 12l4 4-4 4",
    "split": "M8 3H3v18h5 M16 3h5v18h-5 M12 3v3 M12 10v4 M12 18v3",
    "crop": "M7 3v14h14 M3 7h14v14",
    "preview": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
    "stamp": "M8 14v-3a6 6 0 0 0 0-3 4 4 0 1 1 8 0 6 6 0 0 0 0 3v3 M5 14h14l2 5H3z M5 22h14",
    "text": "M4 7V4h16v3 M12 4v16 M9 20h6",
    "form": "M4 3h16v18H4z M7 7h10 M7 11h3 M12 10h5v3h-5z M7 16h3 M12 15h5v3h-5z",
    "signature": "M3 17l2-5L16 1l5 5L10 17l-5 2z M13 4l5 5 M3 23c4-6 6 3 10-2s5 3 8-1",
    "certificate": "M13 21H4V3h10l5 5v3 M14 3v5h5 M21 16a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M14 19v4l3-2 3 2v-4",
    "verify": "M12 2l8 3v6c0 6-8 11-8 11S4 17 4 11V5z M8 11l3 3 5-6",
    "search": "M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0 M15 15l6 6",
    "compare": "M3 3h7v18H3z M14 3h7v18h-7z M6 8h1 M6 12h1 M17 8h1 M17 16h1",
    "blank": "M4 3h10l6 6v12H4z M14 3v6h6",
    "compress": "M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M3 3l6 6 M21 3l-6 6 M21 21l-6-6 M3 21l6-6",
    "redact": "M4 3h16v18H4z M7 7h10 M7 11h10 M7 15h10 M7 17h10",
    "lock": "M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4 M12 14v3",
    "image": "M3 3h18v18H3z M3 17l6-6 4 4 3-3 5 5 M17 7h.01",
    "ocr": "M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M8 8h8 M12 8v8 M9 16h6",
    "interleave": "M3 4h7v6H3z M14 14h7v6h-7z M14 4h7 M18 1l3 3-3 3 M10 17H3 M6 14l-3 3 3 3 M8 10l8 4",
    "properties": "M4 3h16v18H4z M8 7h8 M8 12h8 M8 17h5",
    "select": "M3 3h18v18H3z M7 12l4 4 6-8",
    "settings": "M12 3v3 M12 18v3 M3 12h3 M18 12h3 M5 5l3 3 M16 16l3 3 M5 19l3-3 M16 8l3-3 M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0 M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
    "merge": "M4 3v5l8 6v7 M20 3v5l-8 6 M8 17l4 4 4-4",
    "batch": "M8 3h13v14 M3 8h13v13H3z M6 12h7 M6 16h7",
}


def command_icon(name: str) -> QIcon:
    icon = QIcon()
    for mode, color in ((QIcon.Mode.Normal, "#64748b"), (QIcon.Mode.Disabled, "#a1aab8")):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            f'<path d="{_PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode("ascii")))
        for size in (20, 28, 40, 56):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pixmap, mode)
    return icon
