"""Large preview of single pages: a zoomable page view and a dialog to browse the document with it."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.style import ACCENT
from pdftool.gui.thumbnails import (
    device_pixel_ratio,
    on_white,
    open_document,
    render_page_scaled,
    visible_point_size,
)
from pdftool.gui.widgets import native_shortcut_text
from pdftool.operations import CropMargins, PageRef

# 100 % shows a page at its printed size on a standard 96 dpi screen (a PDF point is 1/72 inch).
_PIXELS_PER_POINT_AT_100 = 96 / 72
_MIN_ZOOM = 0.1
_MAX_ZOOM = 4.0
_ZOOM_STEP = 1.25
# Caps the rendered image (and so memory and render time) for very large pages or high zoom:
# 5000 x 3536 pixels is about 70 MB.
_MAX_RENDER_SIDE = 5000
_FIT_MARGIN = 16


class PageView(QScrollArea):
    """Shows one page rendered at the current zoom, either fitted to the view or at a fixed zoom.

    Rendering is deferred to the event loop, so several quick requests (fast
    paging, resizing) render only the last one. The view can be panned by
    dragging and zoomed with Ctrl + mouse wheel.
    """

    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document: QPdfDocument | None = None
        self._page = 0
        self._rotation = 0
        self._crop: CropMargins | None = None
        self._crop_overlay: CropMargins | None = None
        self._zoom = 1.0
        self._fit = True
        self._pan_origin: QPoint | None = None

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # QtPdf leaves unpainted page areas transparent; real pages are white.
        self._label.setStyleSheet("background: white; padding: 0;")
        self.setWidget(self._label)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("QScrollArea { background: #9ca3af; border: none; }")
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)
        self._render_timer.timeout.connect(self._render)

    def zoom(self) -> float:
        return self._zoom

    def is_fitted(self) -> bool:
        return self._fit

    def show_page(
        self, document: QPdfDocument | None, page: int, rotation: int, crop: CropMargins | None = None
    ) -> None:
        """Show `page` of `document` (None when QtPdf cannot render it) turned clockwise by `rotation`
        and cut to `crop`."""
        self._document, self._page, self._rotation, self._crop = document, page, rotation, crop
        self._render_timer.start()

    def set_crop_overlay(self, crop: CropMargins | None) -> None:
        """Shade the parts of the (whole) page that `crop` would cut away; None removes the shading."""
        self._crop_overlay = crop
        self._render_timer.start()

    def set_zoom(self, zoom: float) -> None:
        self._fit = False
        self._zoom = min(max(zoom, _MIN_ZOOM), _MAX_ZOOM)
        self._render_timer.start()

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * _ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / _ZOOM_STEP)

    def fit_to_window(self) -> None:
        self._fit = True
        self._render_timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit:
            self._render_timer.start()

    def wheelEvent(self, event) -> None:
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        if event.angleDelta().y() > 0:
            self.zoom_in()
        elif event.angleDelta().y() < 0:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pan_origin = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_origin is not None:
            position = event.position().toPoint()
            delta = position - self._pan_origin
            self._pan_origin = position
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._pan_origin = None
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _render(self) -> None:
        if self._document is None or not 0 <= self._page < self._document.pageCount():
            self._label.setPixmap(QPixmap())
            self._label.setText("Stranu sa nepodarilo vykresliť.")
            self._label.adjustSize()
            return

        page_size = visible_point_size(self._document, self._page, self._rotation, self._crop)
        # The whole page is rendered before cropping, so the size cap applies to it.
        whole_page = visible_point_size(self._document, self._page, self._rotation)
        longest_side = max(whole_page.width(), whole_page.height(), 1.0)
        ratio = device_pixel_ratio()
        if self._fit:
            width = max(1, self.viewport().width() - 2 * _FIT_MARGIN)
            height = max(1, self.viewport().height() - 2 * _FIT_MARGIN)
            self._zoom = min(
                width / (max(page_size.width(), 1.0) * _PIXELS_PER_POINT_AT_100),
                height / (max(page_size.height(), 1.0) * _PIXELS_PER_POINT_AT_100),
                _MAX_ZOOM,
            )
        pixels_per_point = min(
            self._zoom * _PIXELS_PER_POINT_AT_100 * ratio,
            _MAX_RENDER_SIDE / longest_side,
        )
        # Report the zoom actually shown when the size cap reduced it.
        self._zoom = pixels_per_point / (_PIXELS_PER_POINT_AT_100 * ratio)
        image = render_page_scaled(self._document, self._page, pixels_per_point, self._rotation, self._crop)
        if self._crop_overlay is not None:
            image = _shade_outside(on_white(image), self._crop_overlay)
        image.setDevicePixelRatio(ratio)
        self._label.setText("")
        self._label.setPixmap(QPixmap.fromImage(image))
        self._label.adjustSize()
        self.zoom_changed.emit(self._zoom)


def _shade_outside(image: QImage, crop: CropMargins) -> QImage:
    left, top, right, bottom = crop
    width, height = image.width(), image.height()
    kept = QRectF(width * left, height * top, width * (1 - left - right), height * (1 - top - bottom))
    painter = QPainter(image)
    outside = QPainterPath()
    outside.addRect(QRectF(0, 0, width, height))
    outside.addRect(kept)  # the odd-even fill leaves the kept area out
    painter.fillPath(outside, QColor(17, 24, 39, 140))
    painter.setPen(QPen(QColor(ACCENT), max(2.0, width / 400)))
    painter.drawRect(kept)
    painter.end()
    return image


class PagePreviewDialog(QDialog):
    """Browses the pages of a document one at a time, as they currently are (order and rotation)."""

    def __init__(
        self, pages: Sequence[PageRef], row: int, source_path: Path, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Náhľad strany")
        self._pages = list(pages)
        self._row = row
        self._source_path = source_path
        # Each source file is opened for rendering once, on first use.
        self._documents: dict[Path, QPdfDocument | None] = {}

        self._view = PageView()
        self._view.zoom_changed.connect(self._update_zoom_label)
        self._previous_button = QPushButton("◀  Predchádzajúca")
        self._previous_button.clicked.connect(lambda: self.show_row(self._row - 1))
        self._next_button = QPushButton("Nasledujúca  ▶")
        self._next_button.clicked.connect(lambda: self.show_row(self._row + 1))
        self._position_label = QLabel()
        self._position_label.setObjectName("fileTitle")
        self._origin_label = QLabel()
        self._origin_label.setObjectName("hint")

        zoom_out_button = QPushButton("−")
        zoom_out_button.setToolTip(f"Zmenšiť ({native_shortcut_text('Ctrl+-')})")
        zoom_out_button.clicked.connect(self._view.zoom_out)
        self._zoom_label = QLabel()
        self._zoom_label.setMinimumWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_in_button = QPushButton("+")
        zoom_in_button.setToolTip(f"Zväčšiť ({native_shortcut_text('Ctrl++')})")
        zoom_in_button.clicked.connect(self._view.zoom_in)
        fit_button = QPushButton("Prispôsobiť oknu")
        fit_button.setToolTip(f"Celá strana v okne ({native_shortcut_text('Ctrl+0')})")
        fit_button.clicked.connect(self._view.fit_to_window)
        actual_size_button = QPushButton("100 %")
        actual_size_button.clicked.connect(lambda: self._view.set_zoom(1.0))

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._previous_button)
        toolbar.addWidget(self._next_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._position_label)
        toolbar.addWidget(self._origin_label, stretch=1)
        toolbar.addWidget(zoom_out_button)
        toolbar.addWidget(self._zoom_label)
        toolbar.addWidget(zoom_in_button)
        toolbar.addWidget(fit_button)
        toolbar.addWidget(actual_size_button)

        hint = QLabel("← → listovanie, Ctrl + koliesko zoom, ťahaním myšou posun, Esc zatvorí")
        hint.setObjectName("hint")

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._view, stretch=1)
        layout.addWidget(hint)

        # Shortcuts take precedence over the scroll area, which would otherwise use the arrows to scroll.
        navigation = {
            Qt.Key.Key_Left: -1,
            Qt.Key.Key_Right: 1,
            Qt.Key.Key_PageUp: -1,
            Qt.Key.Key_PageDown: 1,
        }
        for key, step in navigation.items():
            QShortcut(QKeySequence(key), self, activated=lambda step=step: self.show_row(self._row + step))
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, activated=lambda: self.show_row(0))
        QShortcut(QKeySequence(Qt.Key.Key_End), self, activated=lambda: self.show_row(len(self._pages) - 1))
        for keys in ("Ctrl++", "Ctrl+="):  # "=" is the unshifted "+" key on many layouts
            QShortcut(QKeySequence(keys), self, activated=self._view.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self._view.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._view.fit_to_window)

        self._resize_to_screen()
        self.show_row(row)

    def current_row(self) -> int:
        return self._row

    def show_row(self, row: int) -> None:
        """Show the page at `row` of the document; rows past either end are clamped."""
        self._row = min(max(row, 0), len(self._pages) - 1)
        page = self._pages[self._row]
        self._view.show_page(self._document_for(page.path), page.index, page.rotation, page.crop)

        self._position_label.setText(f"Strana {self._row + 1} z {len(self._pages)}")
        if page.path != self._source_path:
            origin = f"{page.path.name}, strana {page.index + 1}"
        elif page.index != self._row:
            origin = f"pôvodne strana {page.index + 1}"
        else:
            origin = ""
        self._origin_label.setText(origin)
        self._previous_button.setEnabled(self._row > 0)
        self._next_button.setEnabled(self._row < len(self._pages) - 1)

    def done(self, result: int) -> None:
        # Release the in-memory copies of the documents as soon as the preview closes.
        for document in self._documents.values():
            if document is not None:
                document.close()
        self._documents.clear()
        super().done(result)

    def _document_for(self, path: Path) -> QPdfDocument | None:
        if path not in self._documents:
            self._documents[path] = open_document(path, self)
        return self._documents[path]

    def _update_zoom_label(self, zoom: float) -> None:
        self._zoom_label.setText(f"{round(zoom * 100)} %")

    def _resize_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(900, 1000)
            return
        available = screen.availableGeometry()
        self.resize(min(1000, round(available.width() * 0.8)), round(available.height() * 0.9))
