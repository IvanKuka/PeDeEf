"""Placing a picture of a handwritten signature (or a stamp) on a page.

This is a graphic signature only – a picture on the page, not an electronic or
certified digital signature. The picture is read into memory when chosen and
never stored or remembered by the application.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter

from pdftool.gui.stamp_layer import write_pages_with_overlay
from pdftool.operations import DocumentInfo, PageRef, PdfToolError

SIGNATURE_IMAGE_FILTER = "Obrázky (*.png *.jpg *.jpeg)"
# About 600 dpi for a signature 8 cm wide: sharper than any print, while a large photo or
# scan does not make the output file needlessly big.
_MAX_IMAGE_WIDTH = 2000


@dataclass(frozen=True)
class SignaturePlacement:
    """Where the picture goes, as fractions of the visible page (after rotation and crop)."""

    center_x: float
    center_y: float
    width: float  # of the page width; the height follows from the picture's proportions


def load_signature_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)  # photos taken by phones carry their orientation separately
    image = reader.read()
    if image.isNull():
        raise PdfToolError(f"Obrázok „{Path(path).name}“ sa nepodarilo načítať: {reader.errorString()}")
    if image.width() > _MAX_IMAGE_WIDTH:
        image = image.scaledToWidth(_MAX_IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation)
    # Keeps the transparency of PNG pictures, so the page shows through around the signature.
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def signature_rect(page_size: QSizeF, image_size: QSize, placement: SignaturePlacement) -> QRectF:
    """The area of the picture on a page of `page_size`, in the same units as the page size."""
    width = placement.width * page_size.width()
    height = width * image_size.height() / max(image_size.width(), 1)
    return QRectF(
        placement.center_x * page_size.width() - width / 2,
        placement.center_y * page_size.height() - height / 2,
        width,
        height,
    )


def keep_on_page(placement: SignaturePlacement, page_size: QSizeF, image_size: QSize) -> SignaturePlacement:
    """`placement` moved as little as needed for the whole picture to lie on the page."""
    rect = signature_rect(page_size, image_size, placement)
    half_width = rect.width() / 2 / max(page_size.width(), 1.0)
    half_height = rect.height() / 2 / max(page_size.height(), 1.0)
    return SignaturePlacement(
        _clamp(placement.center_x, half_width, 1 - half_width),
        _clamp(placement.center_y, half_height, 1 - half_height),
        placement.width,
    )


def _clamp(value: float, low: float, high: float) -> float:
    if low > high:  # the picture is larger than the page in this direction: centre it
        return 0.5
    return min(max(value, low), high)


def draw_signature(painter: QPainter, page_size: QSizeF, image: QImage, placement: SignaturePlacement) -> None:
    """Draw the picture on a page of `page_size`, both for the preview and into the PDF."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(signature_rect(page_size, image.size(), placement), image)
    painter.restore()


def write_signed_pdf(
    pages: Sequence[PageRef],
    row: int,
    image: QImage,
    placement: SignaturePlacement,
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` to `output_path` with the picture on the page at `row` (0-based)."""
    write_pages_with_overlay(
        pages,
        [row],
        lambda painter, size, _number: draw_signature(painter, size, image, placement),
        output_path,
        password,
        info,
    )
