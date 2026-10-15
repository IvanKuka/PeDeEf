"""Estimating which pages are blank, from how they look when rendered.

A missing text layer says nothing (scans are images), so pages are rendered
and the share of dark pixels ("ink") is measured. Rendering at a low resolution
averages away dust specks; a thin border is ignored because scanners leave dark
edges. The result is an estimate: the user always confirms what is removed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.operations import PageRef

# 72 dpi: noise and show-through vanish, a small page number or a pencil note still counts.
_PIXELS_PER_POINT = 1.0
_DARK_LEVEL = 160  # grey values below this (0-255) count as ink
_IGNORED_BORDER = 0.03  # share of the width/height ignored on each side
_PREVIEW_SIDE = 120
_INK_TABLE = bytes(1 if value < _DARK_LEVEL else 0 for value in range(256))

# Highest ink ratio still considered blank, from strict to lenient. Measured on sample scans:
# blank pages with dust and show-through 0 %, a lone page number or pencil note about 0.006 %,
# three lines of text about 0.6 %.
SENSITIVITY_LEVELS = (
    ("Len úplne prázdne", 0.00001),
    ("Aj s drobnosťou, napr. číslom strany", 0.0003),
    ("Aj s malým množstvom textu", 0.01),
)


@dataclass(frozen=True)
class PageInk:
    ink_ratio: float | None  # None when the page could not be rendered
    preview: QImage


def ink_ratio(image: QImage) -> float:
    """Share of dark pixels in `image`, ignoring a thin border."""
    gray = image.convertToFormat(QImage.Format.Format_Grayscale8)
    border_x, border_y = round(gray.width() * _IGNORED_BORDER), round(gray.height() * _IGNORED_BORDER)
    gray = gray.copy(border_x, border_y, gray.width() - 2 * border_x, gray.height() - 2 * border_y)
    if gray.isNull() or not gray.width() or not gray.height():
        return 0.0
    data = gray.constBits().tobytes()
    line = gray.bytesPerLine()
    # translate/count run in C; rows are cut to the image width to skip the line padding.
    dark = sum(
        data[row * line : row * line + gray.width()].translate(_INK_TABLE).count(1) for row in range(gray.height())
    )
    return dark / (gray.width() * gray.height())


def measure_pages(pages: Sequence[PageRef], on_progress: Callable[[int], bool] | None = None) -> list[PageInk] | None:
    """Measure every page; `on_progress(done)` may return False to cancel, which returns None."""
    documents: dict[Path, QPdfDocument | None] = {}
    results = []
    try:
        for done, page in enumerate(pages):
            if on_progress is not None and not on_progress(done):
                return None
            if page.path not in documents:
                documents[page.path] = open_document(page.path)
            document = documents[page.path]
            if document is None:
                results.append(PageInk(None, QImage()))
                continue
            # Judged as saved: content cut away by a pending crop does not count.
            image = on_white(render_page_scaled(document, page.index, _PIXELS_PER_POINT, page.rotation, page.crop))
            preview = image.scaled(_PREVIEW_SIDE, _PREVIEW_SIDE, Qt.AspectRatioMode.KeepAspectRatio)
            results.append(PageInk(ink_ratio(image), preview))
    finally:
        for document in documents.values():
            if document is not None:
                document.close()
                document.deleteLater()
    return results
