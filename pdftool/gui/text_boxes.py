"""Text typed onto pages anywhere, e.g. to fill in a scanned form that has no form fields.

The text is drawn into the page content (with an embedded font, see stamp_layer),
so it prints and shows the same everywhere but cannot be edited as a form field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter

from pdftool.gui.stamp_layer import stamp_font, write_pages_with_overlay
from pdftool.operations import DocumentInfo, PageRef, PdfToolError

DEFAULT_FONT_SIZE = 11  # points, like typical form text
# Text flags shared by measuring and drawing, so the box drawn around the text fits it.
_FLAGS = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


@dataclass(frozen=True)
class TextBox:
    """Text on one page; its top left corner as fractions of the visible page (after rotation and crop)."""

    text: str
    left: float
    top: float
    font_size: int = DEFAULT_FONT_SIZE  # points

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


def _font(box: TextBox) -> QFont:
    font = stamp_font()
    font.setPixelSize(box.font_size)  # pixel = point, see stamp_layer.draw_stamp
    return font


def text_rect(page_size: QSizeF, box: TextBox) -> QRectF:
    """The area the text covers on a page of `page_size` points; an empty box has the size of one letter."""
    metrics = QFontMetricsF(_font(box))
    size = metrics.boundingRect(QRectF(0, 0, 1e6, 1e6), _FLAGS, box.text or "M").size()
    return QRectF(QPointF(box.left * page_size.width(), box.top * page_size.height()), size)


def keep_on_page(box: TextBox, page_size: QSizeF) -> TextBox:
    """`box` moved as little as needed for its whole text to lie on the page (top left first if too big)."""
    rect = text_rect(page_size, box)
    width, height = max(page_size.width(), 1.0), max(page_size.height(), 1.0)
    left = max(0.0, min(box.left, 1 - rect.width() / width))
    top = max(0.0, min(box.top, 1 - rect.height() / height))
    return replace(box, left=left, top=top)


def box_at(page_size: QSizeF, boxes: Sequence[TextBox], point: QPointF) -> int | None:
    """The index of the topmost box under `point` (in points), if any."""
    for index in reversed(range(len(boxes))):
        if text_rect(page_size, boxes[index]).contains(point):
            return index
    return None


def draw_text_boxes(painter: QPainter, page_size: QSizeF, boxes: Sequence[TextBox]) -> None:
    """Draw `boxes` on a page of `page_size` points, both for the preview and into the PDF."""
    painter.save()
    painter.setPen(QColor("black"))
    for box in boxes:
        if box.is_empty:
            continue
        painter.setFont(_font(box))
        painter.drawText(text_rect(page_size, box), _FLAGS, box.text)
    painter.restore()


def write_text_pdf(
    pages: Sequence[PageRef],
    boxes: Mapping[int, Sequence[TextBox]],
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` to `output_path` with the text `boxes` on the pages they belong to (by 0-based row)."""
    filled = {row: [box for box in row_boxes if not box.is_empty] for row, row_boxes in boxes.items()}
    rows = sorted(row for row, row_boxes in filled.items() if row_boxes)
    if not rows:
        raise PdfToolError("Nie je zadaný žiadny text.")
    write_pages_with_overlay(
        pages,
        rows,
        lambda painter, size, number: draw_text_boxes(painter, size, filled[rows[number]]),
        output_path,
        password,
        info,
    )
