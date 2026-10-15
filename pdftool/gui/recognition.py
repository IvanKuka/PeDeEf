"""Renders pages for text recognition (OCR) and runs it page by page, with progress and cancelling."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtPdf import QPdfDocument

from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.ocr import Tesseract, recognize_page
from pdftool.operations import PageRef, PdfToolError

# The resolution Tesseract is trained for; lower loses small print and diacritics.
OCR_DPI = 300
MAX_OCR_SIDE = 6000
MAX_OCR_PIXELS = 25_000_000


def recognize_pages(
    pages: Sequence[PageRef],
    rows: Sequence[int],
    tesseract: Tesseract,
    language: str,
    on_progress: Callable[[int], bool],
) -> dict[int, bytes] | None:
    """Text layers for the pages at `rows`, keyed by row; None when `on_progress(done)` returned False.

    Each page is recognised as shown – turned and cropped – so its text layer fits
    the visible page (see `ocr.write_with_text_layers`).
    """
    layers: dict[int, bytes] = {}
    documents: dict[Path, QPdfDocument] = {}
    if not rows or any(type(row) is not int or not 0 <= row < len(pages) for row in rows):
        raise PdfToolError("Vyberte existujúce strany na rozpoznanie textu.")
    try:
        for done, row in enumerate(rows):
            if not on_progress(done):
                return None
            page = pages[row]
            document = documents.get(page.path)
            if document is None:
                document = open_document(page.path)
                if document is None:
                    raise PdfToolError(f"Strany zo súboru „{page.path.name}“ sa nepodarilo vykresliť.")
                documents[page.path] = document
            size = document.pagePointSize(page.index)
            scale = _render_scale(size.width(), size.height())
            image = render_page_scaled(document, page.index, scale, page.rotation, page.crop)
            if image.isNull():
                raise PdfToolError(f"Stranu {row + 1} sa nepodarilo vykresliť na rozpoznanie textu.")
            image = on_white(image)
            layer = recognize_page(tesseract, _png(image), language, max(1, round(scale * 72)), lambda: not on_progress(done))
            if layer is None:
                return None
            layers[row] = layer
        return layers if on_progress(len(rows)) else None
    finally:
        for document in documents.values():
            document.close()
            document.deleteLater()


def _render_scale(width: float, height: float) -> float:
    if not all(math.isfinite(size) and size > 0 for size in (width, height)):
        raise PdfToolError("Strana má neplatné rozmery a nedá sa rozpoznať.")
    return min(OCR_DPI / 72, MAX_OCR_SIDE / max(width, height), math.sqrt(MAX_OCR_PIXELS / (width * height)))


def _png(image) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise PdfToolError("Obrázok strany na rozpoznanie textu sa nepodarilo pripraviť.")
    return bytes(buffer.data())
