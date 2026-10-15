import time
from contextlib import contextmanager

import pytest
from PySide6.QtCore import QRectF, QSizeF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPageSize, QPainter, QPdfWriter, QTransform
from PySide6.QtWidgets import QDialog, QProgressDialog, QPushButton
from PySide6.QtTest import QTest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from pdftool.gui import pages_tab
from pdftool.gui.ocr_dialog import OcrDialog
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.recognition import recognize_pages
from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled, visible_point_size
from pdftool.ocr import find_tesseract, write_with_text_layers
from pdftool.operations import DocumentInfo, PageRef, unlock, write_pages
from tests.test_compare import text_pdf
from tests.test_stamps import dark_pixel_box

TESSERACT = find_tesseract()
pytestmark = pytest.mark.skipif(
    TESSERACT is None or "slk" not in TESSERACT.languages(),
    reason="Tesseract so slovenčinou nie je k dispozícii (pripraví ho build.py)",
)
_SCAN_TEXT = "Žltý kôň úpel ďábelské ódy"


def scanned_pdf(path, text=_SCAN_TEXT, sideways=False, skew=0.0, font_size=60):
    """A PDF page holding only a picture of text, like a scan; `sideways` scans it turned left,
    `skew` turns the sheet slightly (degrees), as when it lies askew on the scanner."""
    image = QImage(1240, 1754, QImage.Format.Format_RGB32)  # A4 at 150 dpi
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.translate(620, 877)
    painter.rotate(skew)
    painter.translate(-620, -877)
    font = QFont("Arial")
    font.setPixelSize(font_size)
    painter.setFont(font)
    painter.drawText(QRectF(100, 200, 1040, 1400), int(Qt.TextFlag.TextWordWrap), text)
    painter.end()
    if sideways:
        image = image.transformed(QTransform().rotate(-90))
    writer = QPdfWriter(str(path))
    writer.setResolution(72)
    writer.setPageSize(QPageSize(QSizeF(image.width() * 72 / 150, image.height() * 72 / 150), QPageSize.Unit.Point))
    painter = QPainter(writer)
    painter.drawImage(QRectF(0, 0, image.width() * 72 / 150, image.height() * 72 / 150), image)
    painter.end()
    return path


def page_texts(path):
    document = open_document(path)
    texts = [" ".join(document.getAllText(page).text().split()) for page in range(document.pageCount())]
    document.close()
    return texts


def test_scans_become_searchable_while_text_pages_and_the_look_stay_the_same(app, tmp_path):
    scan = scanned_pdf(tmp_path / "sken.pdf")
    sideways = scanned_pdf(tmp_path / "bokom.pdf", sideways=True)
    typed = text_pdf(tmp_path / "text.pdf", ["Napísaný text"])[0]
    # The sideways scan is turned upright in the app, as a user would before recognising it.
    pages = [PageRef(scan, 0), typed, PageRef(sideways, 0, rotation=90)]
    output = tmp_path / "ocr.pdf"

    layers = recognize_pages(pages, [0, 2], TESSERACT, "slk", lambda done: True)
    write_with_text_layers(pages, layers, output)

    scanned_text, typed_text, sideways_text = page_texts(output)
    assert _SCAN_TEXT in scanned_text and _SCAN_TEXT in sideways_text
    assert typed_text == "Napísaný text"  # not recognised a second time
    before, after = open_document(scan), open_document(output)
    original = on_white(render_page_scaled(before, 0, 0.5))
    recognised = on_white(render_page_scaled(after, 0, 0.5))
    assert original == recognised  # the text layer is invisible
    for page in (0, 2):  # the text lies on the words in the picture, also on the turned page
        ink_left, _, ink_top, _ = dark_pixel_box(on_white(render_page_scaled(after, page, 1.0)))
        text = after.getAllText(page).boundingRectangle()
        assert abs(text.left() - ink_left) < 3 and abs(text.top() - ink_top) < 8
    before.close()
    after.close()


def test_a_scan_lying_slightly_askew_is_still_recognised(app, tmp_path):
    # Dense 12-point lines turned by 2°: Tesseract's automatic layout analysis finds no text here.
    text = "Objednávateľ uhradí cenu do štrnástich dní od doručenia faktúry. " * 6
    pages = [PageRef(scanned_pdf(tmp_path / "sken.pdf", text, skew=2, font_size=25), 0)]
    output = tmp_path / "ocr.pdf"

    write_with_text_layers(pages, recognize_pages(pages, [0], TESSERACT, "slk", lambda done: True), output)

    words = page_texts(output)[0].split()
    assert words.count("Objednávateľ") >= 5 and words.count("štrnástich") >= 5


def test_cancelling_stops_recognition_at_once(app, tmp_path):
    pages = [PageRef(scanned_pdf(tmp_path / "sken.pdf"), 0)] * 3
    calls = []

    def cancel_during_first_page(done):
        calls.append(done)
        return len(calls) < 3  # cancelled while Tesseract works on page 1

    start = time.perf_counter()
    assert recognize_pages(pages, [0, 1, 2], TESSERACT, "slk", cancel_during_first_page) is None
    assert time.perf_counter() - start < 1.5 and set(calls) == {0}


def test_the_tab_recognises_only_pages_without_text_and_opens_the_result(app, dialogs, tmp_path, monkeypatch):
    scan = scanned_pdf(tmp_path / "sken.pdf")
    dialogs.save_path = tmp_path / "sken_ocr.pdf"
    asked = {}

    def accept(dialog):
        asked["language"] = dialog.language()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(OcrDialog, "exec", accept)
    tab = PagesTab()
    tab.open_file(scan)

    tab._recognize_text()

    assert asked["language"] == "slk"  # Slovak is preselected
    assert tab._source_path == scan and tab.has_unsaved_changes()
    assert not dialogs.save_path.exists()
    tab._save_as()
    assert tab._source_path == dialogs.save_path
    assert _SCAN_TEXT in page_texts(dialogs.save_path)[0]
    tab._recognize_text()  # now every page has text
    assert "už obsahujú text" in dialogs.information[-1]


@pytest.mark.parametrize("sideways", [False, True])
def test_cropped_shifted_pages_keep_their_look_text_alignment_password_and_properties(app, tmp_path, sideways):
    original = scanned_pdf(tmp_path / "original.pdf", sideways=sideways)
    writer = PdfWriter()
    page = writer.add_page(PdfReader(original).pages[0])
    page.cropbox = RectangleObject([5, 7, float(page.mediabox.width) - 5, float(page.mediabox.height) - 7])
    source = tmp_path / "crop.pdf"
    writer.write(source)
    before_bytes = source.read_bytes()
    pages = [PageRef(source, 0, 90 if sideways else 0, (0.02, 0.02, 0.02, 0.02))]
    layers = recognize_pages(pages, [0], TESSERACT, "slk", lambda done: True)
    output = tmp_path / "ocr.pdf"
    write_with_text_layers(pages, layers, output, "tajne", DocumentInfo(title="Sken – Žilina"))
    reader = PdfReader(output)
    assert reader.is_encrypted and reader.decrypt("tajne")
    assert reader.metadata.title == "Sken – Žilina"
    assert unlock(output, "tajne")
    assert _SCAN_TEXT in page_texts(output)[0]
    assert source.read_bytes() == before_bytes
    before, after = open_document(source), open_document(output)
    original_image = on_white(render_page_scaled(before, 0, 0.5, pages[0].rotation, pages[0].crop))
    ocr_image = on_white(render_page_scaled(after, 0, 0.5))
    assert abs(original_image.width() - ocr_image.width()) <= 1
    assert abs(original_image.height() - ocr_image.height()) <= 1
    expected = visible_point_size(before, 0, pages[0].rotation, pages[0].crop)
    actual = visible_point_size(after, 0)
    assert abs(expected.width() - actual.width()) < 0.001
    assert abs(expected.height() - actual.height()) < 0.001
    # The visible raster stays the same, apart from subpixel differences at the new crop boundary.
    ink_left, _, ink_top, _ = dark_pixel_box(on_white(render_page_scaled(after, 0, 1.0)))
    text = after.getAllText(0).boundingRectangle()
    assert abs(text.left() - ink_left) < 3 and abs(text.top() - ink_top) < 8
    before.close()
    after.close()


def test_dialog_range_limits_ocr_and_keeps_existing_text(app, dialogs, tmp_path, monkeypatch):
    scan = scanned_pdf(tmp_path / "scan.pdf")
    typed = text_pdf(tmp_path / "typed.pdf", ["Napísaný text"])[0]
    source = tmp_path / "mixed.pdf"
    write_pages([PageRef(scan, 0), PageRef(scan, 0), typed], source)
    dialogs.save_path = tmp_path / "ocr.pdf"
    def accept(dialog):
        dialog._ranges_edit.setText("2-3")
        assert dialog.recognition_rows() == [1]
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(OcrDialog, "exec", accept)
    tab = PagesTab()
    tab.open_file(source)
    tab._recognize_text()
    assert tab._source_path == source and tab.has_unsaved_changes()
    assert not dialogs.save_path.exists()
    tab._save_current()
    assert tab._source_path == source and not tab.has_unsaved_changes()
    first, second, third = page_texts(source)
    assert not first and _SCAN_TEXT in second and third == "Napísaný text"


def test_clicking_cancel_in_the_real_progress_dialog_keeps_work_and_existing_output(app, dialogs, tmp_path, monkeypatch):
    source = scanned_pdf(tmp_path / "scan.pdf")
    original_bytes = source.read_bytes()
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"previous output")
    dialogs.save_path = output
    monkeypatch.setattr(OcrDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    real_progress = pages_tab.progress_dialog
    @contextmanager
    def cancelling_progress(parent, title, *args, **kwargs):
        with real_progress(parent, title, *args, **kwargs) as report:
            if title == "Rozpoznávanie textu":
                dialog = next(child for child in parent.findChildren(QProgressDialog) if child.windowTitle() == title)
                button = dialog.findChild(QPushButton)
                QTimer.singleShot(0, lambda: QTest.mouseClick(button, Qt.MouseButton.LeftButton))
            yield report
    monkeypatch.setattr(pages_tab, "progress_dialog", cancelling_progress)
    tab = PagesTab()
    tab.open_file(source)
    before_pages = tab._current_pages()
    tab._recognize_text()
    assert tab._current_pages() == before_pages and tab._source_path == source
    assert output.read_bytes() == b"previous output" and source.read_bytes() == original_bytes
    assert not dialogs.successes


@pytest.mark.parametrize(("language", "text"), [
    ("eng", "The quick brown fox jumps over the lazy dog"),
    ("ces", "Příliš žluťoučký kůň úpěl ďábelské ódy"),
    ("deu", "Fünf große Bücher für Köln"),
])
def test_other_bundled_languages_recognise_their_text(app, tmp_path, language, text):
    if language not in TESSERACT.languages():
        pytest.skip(f"Language model {language} is not installed")
    source = scanned_pdf(tmp_path / "scan.pdf", text)
    pages = [PageRef(source, 0)]
    output = tmp_path / "ocr.pdf"
    layers = recognize_pages(pages, [0], TESSERACT, language, lambda done: True)
    write_with_text_layers(pages, layers, output)
    # OCR capitalisation is heuristic; wording and diacritics must still match.
    assert text.casefold() in page_texts(output)[0].casefold()
