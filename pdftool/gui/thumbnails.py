"""Page thumbnails rendered with QtPdf (PDFium).

Rendering is kept separate from pypdf: pypdf manipulates documents, QtPdf only
draws them. Thumbnails are a convenience, so a document QtPdf cannot render
is still fully usable with placeholder images.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QRect, QSize, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPixmap, QTransform
from PySide6.QtPdf import QPdfDocument

_FRAME_COLOR = QColor("#d1d5db")


def device_pixel_ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def render_first_page(path: Path, max_side: int) -> QImage | None:
    """Render page 1 of the document, or return None if QtPdf cannot open it."""
    document = QPdfDocument()
    try:
        if _load_into_memory(document, path) is None or document.pageCount() == 0:
            return None
        return _render_page(document, 0, max_side)
    finally:
        document.close()


def placeholder_image(max_side: int) -> QImage:
    """A blank A4-proportioned page shown until (or instead of) the real thumbnail."""
    ratio = device_pixel_ratio()
    height = round(max_side * ratio)
    image = QImage(round(height / 1.414), height, QImage.Format.Format_RGB32)
    image.fill(QColor("#f9fafb"))
    image.setDevicePixelRatio(ratio)
    return image


def thumbnail_icon(image: QImage, side: int, rotation: int = 0) -> QIcon:
    """Turn a rendered page into a square list icon, applying the pending rotation.

    The page is centred on a fixed `side` x `side` canvas so portrait, landscape
    and rotated pages line up identically in lists.
    """
    if rotation % 360:
        image = image.transformed(QTransform().rotate(rotation), Qt.TransformationMode.SmoothTransformation)

    ratio = image.devicePixelRatio()
    canvas_side = round(side * ratio)
    page = image.size().scaled(canvas_side - 2, canvas_side - 2, Qt.AspectRatioMode.KeepAspectRatio)
    left = (canvas_side - page.width()) // 2
    top = (canvas_side - page.height()) // 2

    canvas = QPixmap(canvas_side, canvas_side)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    # The frame keeps white pages visible against the white list background.
    painter.fillRect(left - 1, top - 1, page.width() + 2, page.height() + 2, _FRAME_COLOR)
    # QtPdf renders unpainted page areas as transparent; real pages are white.
    painter.fillRect(left, top, page.width(), page.height(), QColor("white"))
    painter.drawImage(QRect(left, top, page.width(), page.height()), image)
    painter.end()
    canvas.setDevicePixelRatio(ratio)
    icon = QIcon(canvas)
    # Without an explicit Selected pixmap, Qt tints selected icons dark grey.
    icon.addPixmap(canvas, QIcon.Mode.Selected)
    return icon


class PageThumbnailRenderer(QObject):
    """Renders every page of one document, one page per event-loop iteration.

    QPdfDocument must stay on the GUI thread, so instead of a worker thread the
    pages are rendered from a zero-interval timer. This keeps the window
    responsive even for documents with hundreds of pages.
    """

    page_rendered = Signal(int, QImage)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._document = QPdfDocument(self)
        self._buffer: QBuffer | None = None
        self._pending: deque[int] = deque()
        self._max_side = 0
        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._render_next)

    def start(self, path: Path, max_side: int) -> bool:
        """Begin rendering `path`; return False if QtPdf cannot open the document."""
        self.stop()
        self._document.close()
        if self._buffer is not None:
            # Release the previous document's bytes; the buffer is parented to the document.
            self._buffer.deleteLater()
        self._buffer = _load_into_memory(self._document, path)
        if self._buffer is None:
            return False
        self._max_side = max_side
        self._pending.extend(range(self._document.pageCount()))
        self._timer.start()
        return True

    def stop(self) -> None:
        self._timer.stop()
        self._pending.clear()

    def _render_next(self) -> None:
        if not self._pending:
            self._timer.stop()
            return
        page = self._pending.popleft()
        self.page_rendered.emit(page, _render_page(self._document, page, self._max_side))


def _load_into_memory(document: QPdfDocument, path: Path) -> QBuffer | None:
    """Load the document from an in-memory copy; return the backing buffer, or None on failure.

    Loading by file name makes QtPdf keep the file open, and Windows then refuses
    to overwrite it - which breaks saving over the document being viewed. The
    buffer is parented to `document`, so it lives as long as the document does.
    """
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    buffer = QBuffer(document)
    buffer.setData(QByteArray(data))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    document.load(buffer)
    if document.error() != QPdfDocument.Error.None_:
        buffer.deleteLater()
        return None
    return buffer


def _render_page(document: QPdfDocument, page: int, max_side: int) -> QImage:
    # Render at physical pixel size so thumbnails stay sharp on high-DPI displays.
    ratio = device_pixel_ratio()
    image = document.render(page, _fit(document.pagePointSize(page), round(max_side * ratio)))
    image.setDevicePixelRatio(ratio)
    return image


def _fit(page_size: QSizeF, max_side: int) -> QSize:
    longest = max(page_size.width(), page_size.height())
    if longest <= 0:
        return QSize(max_side, max_side)
    scale = max_side / longest
    return QSize(max(1, round(page_size.width() * scale)), max(1, round(page_size.height() * scale)))
