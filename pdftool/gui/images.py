"""Conversions between images and PDF pages, built on Qt only (no extra imaging library).

Qt decodes JPG and PNG (honouring the EXIF orientation of photos), writes PDF
pages with QPdfWriter and renders PDF pages with QtPdf. All raised
`PdfToolError` messages are user-facing (Slovak).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.operations import ImageRecompressor, PageRef, PdfToolError

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
IMAGE_FILE_FILTER = "Obrázky (*.jpg *.jpeg *.png)"

_A4_MARGIN_MM = 10
_PDF_RESOLUTION = 300
# Exported images are capped so that a huge page at a high resolution cannot exhaust memory
# (8000 x 8000 pixels is about 256 MB).
MAX_EXPORT_SIDE = 8000


class PageFormat(Enum):
    A4 = "a4"  # A4 with margins, portrait or landscape to suit the image
    IMAGE = "image"  # no margins, page in the proportions of the image


def is_image(path: Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


def load_image(path: Path) -> QImage:
    """Read an image, turned upright according to its EXIF orientation."""
    path = Path(path)
    if not path.is_file():
        raise PdfToolError(f"Súbor neexistuje: {path}")
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise PdfToolError(f"Obrázok „{path.name}“ sa nepodarilo načítať: {reader.errorString()}")
    return image


def images_to_pdf(image_paths: Sequence[Path], output_path: Path, page_format: PageFormat) -> None:
    """Write one PDF page per image, in order; the image keeps its proportions."""
    if not image_paths:
        raise PdfToolError("Nie je vybraný žiadny obrázok.")
    images = [load_image(path) for path in image_paths]  # all checked before anything is written

    output_path = Path(output_path)
    # Written next to the target and swapped in afterwards, like every other output of the app.
    try:
        fd, temp_name = tempfile.mkstemp(suffix=".tmp", dir=output_path.parent)
    except OSError as exc:
        raise PdfToolError(f"Do priečinka „{output_path.parent}“ nie je možné zapisovať: {exc}") from exc
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        writer = QPdfWriter(str(temp_path))
        writer.setResolution(_PDF_RESOLUTION)
        # A page layout applies to the page started after it is set, so set it before each page.
        writer.setPageLayout(_page_layout(images[0], page_format))
        painter = QPainter()
        if not painter.begin(writer):
            raise PdfToolError(f"Súbor „{output_path.name}“ sa nepodarilo vytvoriť.")
        for number, image in enumerate(images):
            if number:
                writer.setPageLayout(_page_layout(image, page_format))
                writer.newPage()
            _draw_fitted(painter, writer, image)
        painter.end()
        os.replace(temp_path, output_path)
    except PermissionError as exc:
        raise PdfToolError(
            f"Súbor „{output_path.name}“ nie je možné prepísať – nie je otvorený v inom programe?"
        ) from exc
    except OSError as exc:
        raise PdfToolError(f"Súbor „{output_path.name}“ sa nepodarilo uložiť: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def jpeg_recompressor(max_side: int, quality: int) -> ImageRecompressor:
    """Re-encode JPEG pictures at `quality` (0-100), shrinking those larger than `max_side` pixels."""

    def recompress(data: bytes, colour_space: str) -> tuple[bytes, int, int] | None:
        image = QImage.fromData(QByteArray(data), "JPG")
        if image.isNull():
            return None
        if max(image.width(), image.height()) > max_side:
            image = image.scaled(
                max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        # Grey stays grey: a colour JPEG of a grey page would be bigger and need another colour space.
        gray = colour_space == "/DeviceGray"
        image = image.convertToFormat(QImage.Format.Format_Grayscale8 if gray else QImage.Format.Format_RGB888)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "JPG", quality):
            return None
        return bytes(buffer.data()), image.width(), image.height()

    return recompress


def export_output_paths(name_source: Path, positions: Sequence[int], output_dir: Path) -> list[Path]:
    """File names `export_pages_as_png` will create for the given 0-based page positions."""
    width = max(3, len(str(max(positions, default=0) + 1)))
    return [Path(output_dir) / f"{Path(name_source).stem}_strana_{position + 1:0{width}d}.png" for position in positions]


def export_pages_as_png(
    pages: Sequence[PageRef], positions: Sequence[int], name_source: Path, output_dir: Path, dpi: int
) -> tuple[list[Path], bool]:
    """Render `pages` (shown at `positions` in the document) to PNG files.

    Returns the created files and whether any page had to be rendered smaller
    than requested because of `MAX_EXPORT_SIDE`.
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise PdfToolError(f"Priečinok neexistuje: {output_dir}")
    documents: dict[Path, QPdfDocument] = {}
    created: list[Path] = []
    reduced = False
    try:
        for page, output_path in zip(pages, export_output_paths(name_source, positions, output_dir), strict=True):
            document = documents.get(page.path) or open_document(page.path)
            if document is None:
                raise PdfToolError(f"Súbor „{page.path.name}“ sa nepodarilo vykresliť.")
            documents[page.path] = document
            size = document.pagePointSize(page.index)
            pixels_per_point = dpi / 72
            longest = max(size.width(), size.height(), 1.0)
            if longest * pixels_per_point > MAX_EXPORT_SIDE:
                pixels_per_point = MAX_EXPORT_SIDE / longest
                reduced = True
            image = on_white(render_page_scaled(document, page.index, pixels_per_point, page.rotation, page.crop))
            _save_atomically(image, output_path)
            created.append(output_path)
    finally:
        for document in documents.values():
            document.close()
            document.deleteLater()
    return created, reduced


def _page_layout(image: QImage, page_format: PageFormat) -> QPageLayout:
    landscape = image.width() > image.height()
    orientation = QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait
    if page_format is PageFormat.A4:
        margins = QMarginsF(_A4_MARGIN_MM, _A4_MARGIN_MM, _A4_MARGIN_MM, _A4_MARGIN_MM)
        return QPageLayout(QPageSize(QPageSize.PageSizeId.A4), orientation, margins, QPageLayout.Unit.Millimeter)
    # The longer side matches A4's, so photos come out at a familiar print size.
    long_side = 297.0
    short_side = long_side * min(image.width(), image.height()) / max(image.width(), image.height())
    size = QSizeF(short_side, long_side)
    page_size = QPageSize(size, QPageSize.Unit.Millimeter, "", QPageSize.SizeMatchPolicy.ExactMatch)
    return QPageLayout(page_size, orientation, QMarginsF(), QPageLayout.Unit.Millimeter)


def _draw_fitted(painter: QPainter, writer: QPdfWriter, image: QImage) -> None:
    # The printable area excludes the margins; scale without distortion and centre.
    area_width, area_height = writer.width(), writer.height()
    scale = min(area_width / image.width(), area_height / image.height())
    width, height = image.width() * scale, image.height() * scale
    target = QRectF((area_width - width) / 2, (area_height - height) / 2, width, height)
    # Transparent parts of PNGs would show whatever is behind the page; paper is white.
    painter.fillRect(target, QColor("white"))
    painter.drawImage(target, image)


def _save_atomically(image: QImage, output_path: Path) -> None:
    try:
        fd, temp_name = tempfile.mkstemp(suffix=".png", dir=output_path.parent)
    except OSError as exc:
        raise PdfToolError(f"Do priečinka „{output_path.parent}“ nie je možné zapisovať: {exc}") from exc
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        if not image.save(str(temp_path), "PNG"):
            raise PdfToolError(f"Obrázok „{output_path.name}“ sa nepodarilo uložiť.")
        os.replace(temp_path, output_path)
    except OSError as exc:
        raise PdfToolError(f"Obrázok „{output_path.name}“ sa nepodarilo uložiť: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
