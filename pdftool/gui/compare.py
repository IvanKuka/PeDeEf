"""Visual comparison of two documents, page by page at the same positions.

Both pages are rendered the same way and subtracted pixel by pixel. Pages that
differ only by rendering noise count as equal; a visual difference is not proof
of a change in meaning, and an inserted page shifts every page after it - the
dialog says so.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QSizeF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled, visible_point_size
from pdftool.operations import PageRef

# 72 dpi: enough to see changed words, fast enough for long documents.
_PIXELS_PER_POINT = 1.0
# Colour distance (0-255) above which a pixel counts as changed; anti-aliasing stays below it.
_CHANGED_LEVEL = 64
# Changed pixels a page may have and still count as the same. Identical pages render with no
# differences at all, while one changed character is about 40 pixels at this resolution, so a
# share of the page would hide it; a small absolute allowance only absorbs rendering noise.
_EQUAL_PIXELS = 4
# Sizes within this many points count as the same page size.
_SIZE_TOLERANCE = 1.0
_CHANGED_TABLE = bytes(255 if value > _CHANGED_LEVEL else 0 for value in range(256))
_HIGHLIGHT = QColor(220, 38, 38)


class Verdict(Enum):
    EQUAL = "equal"
    DIFFERENT = "different"
    OTHER_SIZE = "other-size"
    ONLY_FIRST = "only-first"
    ONLY_SECOND = "only-second"


@dataclass(frozen=True)
class PagePair:
    position: int  # 0-based
    verdict: Verdict
    changed_ratio: float = 0.0
    first: QImage | None = None  # with the changes highlighted
    second: QImage | None = None

    @property
    def differs(self) -> bool:
        return self.verdict is not Verdict.EQUAL


def compare_documents(
    first: Sequence[PageRef], second: Sequence[PageRef], on_progress: Callable[[int], bool] | None = None
) -> list[PagePair] | None:
    """Compare the pages at each position; `on_progress(done)` returning False cancels (None is returned)."""
    documents: dict[Path, QPdfDocument | None] = {}

    def render(page: PageRef) -> tuple[QImage, QSizeF] | None:
        if page.path not in documents:
            documents[page.path] = open_document(page.path)
        document = documents[page.path]
        if document is None:
            return None
        size = visible_point_size(document, page.index, page.rotation, page.crop)
        image = render_page_scaled(document, page.index, _PIXELS_PER_POINT, page.rotation, page.crop)
        return on_white(image), size

    pairs = []
    try:
        for position in range(max(len(first), len(second))):
            if on_progress is not None and not on_progress(position):
                return None
            left = render(first[position]) if position < len(first) else None
            right = render(second[position]) if position < len(second) else None
            pairs.append(_compare_pair(position, left, right))
    finally:
        for document in documents.values():
            if document is not None:
                document.close()
                document.deleteLater()
    return pairs


def _compare_pair(position: int, left, right) -> PagePair:
    if right is None:
        return PagePair(position, Verdict.ONLY_FIRST, first=left[0] if left else None)
    if left is None:
        return PagePair(position, Verdict.ONLY_SECOND, second=right[0])
    (left_image, left_size), (right_image, right_size) = left, right
    if (
        abs(left_size.width() - right_size.width()) > _SIZE_TOLERANCE
        or abs(left_size.height() - right_size.height()) > _SIZE_TOLERANCE
    ):
        return PagePair(position, Verdict.OTHER_SIZE, first=left_image, second=right_image)

    # Equal sizes can still render one pixel apart; compare on the common area.
    right_image = right_image.scaled(left_image.size())
    mask, changed = _changed_pixels(left_image, right_image)
    ratio = changed / max(1, left_image.width() * left_image.height())
    if changed <= _EQUAL_PIXELS:
        return PagePair(position, Verdict.EQUAL, ratio, left_image, right_image)
    return PagePair(position, Verdict.DIFFERENT, ratio, _highlight(left_image, mask), right_image)


def _changed_pixels(first: QImage, second: QImage) -> tuple[QImage, int]:
    """A mask of the pixels that differ (255) and how many there are."""
    difference = first.convertToFormat(QImage.Format.Format_RGB32)
    painter = QPainter(difference)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Difference)
    painter.drawImage(0, 0, second.convertToFormat(QImage.Format.Format_RGB32))
    painter.end()
    gray = difference.convertToFormat(QImage.Format.Format_Grayscale8)
    data = gray.constBits().tobytes()
    line = gray.bytesPerLine()
    # translate/count run in C; each row is cut to the width to skip the line padding.
    rows = [data[row * line : row * line + gray.width()].translate(_CHANGED_TABLE) for row in range(gray.height())]
    mask_bytes = b"".join(rows)
    mask = QImage(mask_bytes, gray.width(), gray.height(), gray.width(), QImage.Format.Format_Grayscale8).copy()
    return mask, mask_bytes.count(255)


def _highlight(image: QImage, mask: QImage) -> QImage:
    overlay = QImage(image.size(), QImage.Format.Format_ARGB32)
    overlay.fill(_HIGHLIGHT)
    overlay.setAlphaChannel(mask)
    result = image.convertToFormat(QImage.Format.Format_RGB32)
    painter = QPainter(result)
    painter.setOpacity(0.75)
    painter.drawImage(0, 0, overlay)
    painter.end()
    return result
