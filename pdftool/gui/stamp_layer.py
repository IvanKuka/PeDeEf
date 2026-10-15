"""Draws on pages with Qt: into a PDF layer merged onto the pages, and onto preview images.

Page numbers and text stamps are drawn here; other drawings (such as a signature
picture) reuse the same layer and preview functions. Writing and preview use the
same drawing function, so the preview shows exactly what will be written. Text
is drawn with Arial or the system font, which QPdfWriter embeds (as a subset),
so Slovak diacritics come out right in any viewer.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPageLayout, QPageSize, QPainter, QPdfWriter, QPixmap
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import device_pixel_ratio, render_page_scaled, visible_point_size
from pdftool.operations import (
    DocumentInfo,
    PageRef,
    PdfToolError,
    apply_overlay,
    visible_page_sizes,
    write_pages,
)
from pdftool.stamps import Position, StampSpec, stamp_texts

# 10 mm from the edges of the visible page, in points.
_MARGIN = 10 / 25.4 * 72

_ALIGNMENT = {
    Position.TOP_LEFT: Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
    Position.TOP_CENTER: Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
    Position.TOP_RIGHT: Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    Position.CENTER: Qt.AlignmentFlag.AlignCenter,
    Position.BOTTOM_LEFT: Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
    Position.BOTTOM_CENTER: Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
    Position.BOTTOM_RIGHT: Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
}


def stamp_font() -> QFont:
    # Arial ships with both Windows and macOS and its licence allows embedding in documents;
    # the macOS system UI font is licensed for Apple platforms only. Qt itself also honours
    # a font's embedding restrictions when writing the PDF.
    if "Arial" in QFontDatabase.families():
        return QFont("Arial")
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)


def draw_stamp(painter: QPainter, page_size: QSizeF, text: str, spec: StampSpec) -> None:
    """Draw `text` on a page of `page_size` points; the painter must map one unit to one point."""
    font = stamp_font()
    font.setPixelSize(spec.font_size)  # pixel = point here, see the docstring
    painter.save()
    painter.setFont(font)
    painter.setPen(QColor("black"))
    area = QRectF(_MARGIN, _MARGIN, page_size.width() - 2 * _MARGIN, page_size.height() - 2 * _MARGIN)
    painter.drawText(area, int(_ALIGNMENT[spec.position] | Qt.TextFlag.TextWordWrap), text)
    painter.restore()


# Draws on one page of an overlay: (painter in points, visible page size, number of the overlay page).
DrawPage = Callable[[QPainter, QSizeF, int], None]


def write_overlay_layer(page_sizes: Sequence[tuple[float, float]], draw: DrawPage, output_path: Path) -> None:
    """Write a PDF with one transparent page per size, drawn by `draw` in point coordinates."""
    if not page_sizes:
        raise PdfToolError("Nie je vybraná žiadna strana.")
    writer = QPdfWriter(str(Path(output_path)))
    # At 72 dpi one device pixel is one PDF point, which is what the drawing functions expect.
    writer.setResolution(72)
    painter = QPainter()
    for number, (width, height) in enumerate(page_sizes):
        size = QPageSize(QSizeF(width, height), QPageSize.Unit.Point, "", QPageSize.SizeMatchPolicy.ExactMatch)
        writer.setPageLayout(QPageLayout(size, QPageLayout.Orientation.Portrait, QMarginsF()))
        if number == 0:
            if not painter.begin(writer):
                raise PdfToolError("Vrstvu na strany sa nepodarilo vytvoriť.")
        else:
            writer.newPage()
        draw(painter, QSizeF(width, height), number)
    painter.end()


def render_preview(
    document: QPdfDocument, page: PageRef, box: QSize, draw: Callable[[QPainter, QSizeF], None]
) -> QPixmap:
    """`page` as it will be saved, fitted into `box` (logical pixels), with `draw` applied on top.

    `draw` gets a painter in points and the visible page size – the same as when
    writing the layer – so the preview shows exactly what will be written.
    """
    visible = visible_point_size(document, page.index, page.rotation, page.crop)
    ratio = device_pixel_ratio()
    pixels_per_point = ratio * min(box.width() / max(visible.width(), 1.0), box.height() / max(visible.height(), 1.0))
    image = render_page_scaled(document, page.index, pixels_per_point, page.rotation, page.crop)
    canvas = QPixmap(image.size())
    canvas.fill(Qt.GlobalColor.white)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.drawImage(0, 0, image)
    painter.scale(pixels_per_point, pixels_per_point)
    draw(painter, QSizeF(visible.width(), visible.height()))
    painter.end()
    canvas.setDevicePixelRatio(ratio)
    return canvas


def write_stamp_layer(
    page_sizes: Sequence[tuple[float, float]], texts: Sequence[str], spec: StampSpec, output_path: Path
) -> None:
    """Write a PDF with one transparent page per text, sized like the page it will be drawn on."""
    if len(page_sizes) != len(texts):
        raise ValueError("one text per page is needed")
    write_overlay_layer(
        page_sizes, lambda painter, size, number: draw_stamp(painter, size, texts[number], spec), output_path
    )


def write_pages_with_overlay(
    pages: Sequence[PageRef],
    rows: Sequence[int],
    draw: DrawPage,
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
    removed_widgets: Mapping[int, Sequence[int]] | None = None,
) -> None:
    """Write `pages` to `output_path`, drawing on the pages at `rows` (0-based, ascending) as they will look.

    The drawing gets the size of each page as displayed – after rotation and crop – so
    what is drawn upright and in place on screen lands the same way in the file.
    `removed_widgets` are form widgets to remove from those pages (see `apply_overlay`).
    """
    if not rows:
        raise PdfToolError("Nie je vybraná žiadna strana.")
    # Intermediate files live next to the output, so a full disk or missing rights fail early.
    with tempfile.TemporaryDirectory(dir=Path(output_path).parent) as temp_dir:
        base = Path(temp_dir) / "pages.pdf"
        write_pages(pages, base)
        sizes = visible_page_sizes(base)
        layer = Path(temp_dir) / "layer.pdf"
        write_overlay_layer([sizes[row] for row in rows], draw, layer)
        apply_overlay(
            base, layer, {row: number for number, row in enumerate(rows)}, output_path, password, info, removed_widgets
        )


def write_stamped_pdf(
    pages: Sequence[PageRef],
    stamped_rows: Sequence[int],
    spec: StampSpec,
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` to `output_path` with the stamp on the pages at `stamped_rows` (0-based, ascending)."""
    texts = stamp_texts(spec, len(stamped_rows))
    write_pages_with_overlay(
        pages,
        stamped_rows,
        lambda painter, size, number: draw_stamp(painter, size, texts[number], spec),
        output_path,
        password,
        info,
    )
