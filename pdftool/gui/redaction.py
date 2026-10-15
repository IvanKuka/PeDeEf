"""Permanent redaction: blacking out areas so that what was under them is gone from the file.

A black rectangle drawn over a page is not enough – the text, pictures and
hidden layers under it stay in the file and can be copied out. Instead, every
page with an area is rendered to a picture (as the page is shown in the
application, without comments and form fields), the areas are filled black in
the picture, and the page is replaced by a page holding only that picture.
Nothing of the original page remains. Pages without areas are copied unchanged.

Before the result replaces the target file it is checked: the redacted pages
must contain no text and no annotations.
"""

from __future__ import annotations

import tempfile
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled, visible_point_size
from pdftool.operations import DocumentInfo, PageRef, PdfToolError, write_file_atomically, write_pages

# Rectangles as fractions of the visible page (after rotation and crop), keyed by the 0-based row.
RedactionAreas = Mapping[int, Sequence[QRectF]]

REDACTION_DPI = (150, 300)


def blacken(image: QImage, areas: Sequence[QRectF]) -> QImage:
    """A copy of the page `image` with `areas` (fractions of the image) filled black."""
    result = on_white(image)  # also a copy: the original image is left as it was
    painter = QPainter(result)
    for area in areas:
        painter.fillRect(_pixel_rect(area, result.width(), result.height()), QColor("black"))
    painter.end()
    return result


def _pixel_rect(area: QRectF, width: int, height: int) -> QRectF:
    # Rounded outwards, so the edge of a character on the border of the area cannot stay visible.
    left = math.floor(area.left() * width)
    top = math.floor(area.top() * height)
    right = math.ceil(area.right() * width)
    bottom = math.ceil(area.bottom() * height)
    return QRectF(left, top, right - left, bottom - top)


def write_redacted_pdf(
    pages: Sequence[PageRef],
    areas: RedactionAreas,
    dpi: int,
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` to `output_path` with `areas` permanently blacked out (see the module docstring)."""
    rows = sorted(row for row, row_areas in areas.items() if row_areas)
    if not rows:
        raise PdfToolError("Nie je označená žiadna oblasť na začiernenie.")
    output_path = Path(output_path)
    # Intermediate files live next to the output, so a full disk or missing rights fail early.
    with tempfile.TemporaryDirectory(dir=output_path.parent) as temp_dir:
        pictures = Path(temp_dir) / "redacted_pages.pdf"
        _write_picture_pages([pages[row] for row in rows], [areas[row] for row in rows], dpi, pictures)
        result_pages = list(pages)
        for number, row in enumerate(rows):
            result_pages[row] = PageRef(pictures, number)
        result = Path(temp_dir) / "result.pdf"
        write_pages(result_pages, result, password, info)
        _check_redacted(result, rows, password)
        data = result.read_bytes()
    write_file_atomically(lambda stream: stream.write(data), output_path)


def _write_picture_pages(
    pages: Sequence[PageRef], page_areas: Sequence[Sequence[QRectF]], dpi: int, output_path: Path
) -> None:
    writer = QPdfWriter(str(output_path))
    writer.setResolution(72)  # one unit is one point; the picture keeps its own, higher resolution
    painter = QPainter()
    documents: dict[Path, QPdfDocument] = {}
    try:
        for number, (page, areas) in enumerate(zip(pages, page_areas, strict=True)):
            document = documents.get(page.path)
            if document is None:
                document = open_document(page.path)
                if document is None:
                    raise PdfToolError(f"Stranu zo súboru „{page.path.name}“ sa nepodarilo vykresliť.")
                documents[page.path] = document
            size = visible_point_size(document, page.index, page.rotation, page.crop)
            image = render_page_scaled(document, page.index, dpi / 72, page.rotation, page.crop)
            if image.isNull():
                raise PdfToolError(f"Stranu {page.index + 1} zo súboru „{page.path.name}“ sa nepodarilo vykresliť.")
            picture = blacken(image, areas)

            layout_size = QPageSize(QSizeF(size), QPageSize.Unit.Point, "", QPageSize.SizeMatchPolicy.ExactMatch)
            writer.setPageLayout(QPageLayout(layout_size, QPageLayout.Orientation.Portrait, QMarginsF()))
            if number == 0:
                if not painter.begin(writer):
                    raise PdfToolError("Začiernené strany sa nepodarilo vytvoriť.")
            else:
                writer.newPage()
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(0, 0, size.width(), size.height()), picture)
    finally:
        if painter.isActive():
            painter.end()
        for document in documents.values():
            document.close()


def _check_redacted(path: Path, rows: Sequence[int], password: str | None) -> None:
    """Make sure the redacted pages hold nothing but the picture; raise instead of saving otherwise."""
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            reader.decrypt(password or "")
        for row in rows:
            page = reader.pages[row]
            # Qt writes an annotation list even when it is empty, possibly as a reference.
            annotations = page.get("/Annots")
            if page.extract_text().strip() or (annotations is not None and annotations.get_object()):
                raise PdfToolError(
                    f"Kontrola výsledku zlyhala: strana {row + 1} stále obsahuje text alebo komentáre. "
                    "Súbor nebol uložený."
                )
    except (PdfReadError, ValueError) as exc:
        raise PdfToolError(f"Výsledok sa nepodarilo skontrolovať, súbor nebol uložený: {exc}") from exc
