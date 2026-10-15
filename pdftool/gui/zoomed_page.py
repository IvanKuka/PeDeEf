"""A zoomable page preview for dialogs that place things on a page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, QSizeF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QComboBox, QScrollArea, QVBoxLayout, QWidget

from pdftool.gui.stamp_layer import render_preview
from pdftool.gui.thumbnails import open_document, visible_point_size
from pdftool.gui.widgets import PageCanvas
from pdftool.operations import PageRef

# Draws over the page: (painter in points, visible page size).
DrawOverlay = Callable[[QPainter, QSizeF], None]
# Very large pages would make huge pixmaps at high zoom.
_MAX_SIDE_PIXELS = 2200


class ZoomedPageView(QWidget):
    """`canvas` in a scroll area, showing one page at the zoom chosen in `zoom_combo`.

    The page is rendered once per page and size; the overlay is redrawn on a copy,
    so dragging something over the page stays smooth.
    """

    def __init__(self, canvas: PageCanvas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.zoom_combo = QComboBox()
        for label, scale in (("Prispôsobiť oknu", 0), ("100 %", 1), ("150 %", 1.5), ("200 %", 2)):
            self.zoom_combo.addItem(label, scale)
        self.zoom_combo.currentIndexChanged.connect(self.refresh)
        self._scroll = QScrollArea()
        self._scroll.setWidget(canvas)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setMinimumSize(300, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        self._document: QPdfDocument | None = None
        self._document_path = None
        self._page: PageRef | None = None
        self._overlay: DrawOverlay = lambda painter, size: None
        self._base: QPixmap | None = None
        self._base_key = None

    def show_page(self, page: PageRef, overlay: DrawOverlay) -> None:
        self._page, self._overlay = page, overlay
        self.refresh()

    def visible_size(self) -> QSizeF | None:
        """The shown page's size in points as it will be saved, or None if it cannot be shown."""
        if self._page is None or self._open(self._page) is None:
            return None
        return visible_point_size(self._document, self._page.index, self._page.rotation, self._page.crop)

    def close_document(self) -> None:
        if self._document is not None:
            self._document.close()
        self._document = self._document_path = None
        self._base = None
        self.canvas.clear()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.refresh()

    def refresh(self) -> None:
        if self._page is None:
            return
        page = self._page
        document = self._open(page)
        if document is None:
            self.canvas.setText("Náhľad nie je k dispozícii.")
            return
        size = visible_point_size(document, page.index, page.rotation, page.crop)
        zoom = self.zoom_combo.currentData()
        if zoom:
            scale = zoom * 96 / 72
        else:
            viewport = self._scroll.viewport()
            scale = min(max(1, viewport.width() - 12) / size.width(), max(1, viewport.height() - 12) / size.height())
        scale = min(scale, _MAX_SIDE_PIXELS / max(size.width(), size.height()))
        box = QSize(max(1, round(size.width() * scale)), max(1, round(size.height() * scale)))
        self.canvas.setFixedSize(box)
        key = (page, box.width(), box.height())
        if self._base is None or key != self._base_key:
            self._base = render_preview(document, page, box, lambda painter, size: None)
            self._base_key = key
        preview = QPixmap(self._base)
        painter = QPainter(preview)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        shown = preview.deviceIndependentSize()
        painter.scale(shown.width() / size.width(), shown.height() / size.height())
        self._overlay(painter, size)
        painter.end()
        self.canvas.setPixmap(preview)

    def _open(self, page: PageRef) -> QPdfDocument | None:
        if self._document_path != page.path:
            if self._document is not None:
                self._document.close()
            self._document = open_document(page.path, self)
            self._document_path = page.path
            self._base = None
        return self._document
