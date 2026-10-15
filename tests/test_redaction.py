from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, IndirectObject, NameObject, NumberObject
from PySide6.QtGui import QColor, QImage
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.redaction import blacken, write_redacted_pdf
from pdftool.gui.redaction_dialog import RedactionDialog
from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.operations import PageRef, unlock
from tests.test_compare import text_pdf

_SECRET = "Rodné číslo 855212/1234, účet SK31 1200 0000 1987 4263 7541"


def test_redaction_covers_fractional_right_and_bottom_edges(app):
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    result = blacken(image, [QRectF(0.11, 0.11, 0.18, 0.18)])
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        assert result.pixelColor(x, y) == QColor("black")
    assert image.pixelColor(2, 2) == QColor("red")


def test_shared_resources_do_not_retain_a_redacted_scan_and_nested_forms_still_render(app, tmp_path):
    writer = PdfWriter()
    resources = DictionaryObject()
    xobjects = DictionaryObject()
    resources[NameObject("/XObject")] = writer._add_object(xobjects)
    secret_data = bytes([255, 0, 0]) * 100
    for name, data in (("/SecretScan", secret_data), ("/PublicScan", bytes([0, 255, 0]) * 100)):
        image = DecodedStreamObject()
        image.set_data(data)
        image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                      NameObject("/Width"): NumberObject(10), NameObject("/Height"): NumberObject(10),
                      NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
        xobjects[NameObject(name)] = writer._add_object(image)
    form = DecodedStreamObject()
    form.set_data(b"/PublicScan Do")
    from pypdf.generic import RectangleObject
    form.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"),
                 NameObject("/BBox"): RectangleObject([0, 0, 1, 1])})
    xobjects[NameObject("/PublicForm")] = writer._add_object(form)
    resource_ref = writer._add_object(resources)
    for name in ("/SecretScan", "/PublicForm"):
        page = writer.add_blank_page(width=100, height=100)
        page[NameObject("/Resources")] = resource_ref
        content = DecodedStreamObject()
        content.set_data(f"q 100 0 0 100 0 0 cm {name} Do Q".encode())
        page[NameObject("/Contents")] = writer._add_object(content)
    source, output = tmp_path / "source.pdf", tmp_path / "redacted.pdf"
    writer.write(source)
    write_redacted_pdf([PageRef(source, 0), PageRef(source, 1)], {0: [QRectF(0, 0, 1, 1)]}, 150, output)
    reader = PdfReader(output)
    for generation, entries in reader.xref.items():
        for number in entries:
            if not number:
                continue
            obj = reader.get_object(IndirectObject(number, generation, reader))
            if hasattr(obj, "get_data"):
                assert obj.get_data() != secret_data
    document = open_document(output)
    public = on_white(render_page_scaled(document, 1, 1)).pixelColor(50, 50)
    document.close()
    assert public.green() > 200 and public.red() < 30


def all_text(path, password=None):
    """The document's text as two independent engines see it: pypdf and PDFium (QtPdf)."""
    reader = PdfReader(path)
    if password:
        reader.decrypt(password)
        unlock(path, password)
    document = open_document(path)
    # Whitespace normalised: pypdf reports some word gaps as tabs.
    texts = [
        (" ".join(page.extract_text().split()), " ".join(document.getAllText(number).text().split()))
        for number, page in enumerate(reader.pages)
    ]
    document.close()
    return texts


def test_redacted_text_is_gone_for_any_tool_and_the_rest_is_kept(app, tmp_path):
    pages = text_pdf(tmp_path / "zmluva.pdf", [_SECRET, "Verejná príloha"])
    output = tmp_path / "zaciernene.pdf"
    secret_area = QRectF(0, 0, 1, 0.1)  # the text is at the top left of the page

    write_redacted_pdf(pages, {0: [secret_area]}, 150, output, password="heslo")

    (redacted_pypdf, redacted_pdfium), (kept_pypdf, kept_pdfium) = all_text(output, "heslo")
    assert redacted_pypdf.strip() == "" and redacted_pdfium.strip() == ""
    assert "Verejná príloha" in kept_pypdf and "Verejná príloha" in kept_pdfium
    assert "855212" not in str(all_text(output, "heslo"))
    document = open_document(output)
    image = on_white(render_page_scaled(document, 0, 1.0))
    document.close()
    assert image.pixelColor(40, 30).lightness() < 20  # blacked out
    assert image.pixelColor(300, 400).lightness() > 235  # the rest of the page is still white paper
    assert sorted(path.name for path in tmp_path.iterdir()) == ["zaciernene.pdf", "zmluva.pdf"]


def test_marking_areas_in_the_dialog_and_saving_from_the_tab(app, dialogs, tmp_path, monkeypatch):
    pages = text_pdf(tmp_path / "zmluva.pdf", ["Verejný úvod", _SECRET])
    dialogs.save_path = tmp_path / "zmluva_zaciernene.pdf"
    marked = {}

    def mark_and_accept(dialog):
        assert not dialog._accept_button.isEnabled()  # nothing marked yet
        dialog._page_spin.setValue(2)
        canvas = dialog._canvas
        page = canvas.pixmap().deviceIndependentSize()
        left, top = (canvas.width() - page.width()) / 2, (canvas.height() - page.height()) / 2
        # Drag from the top left corner of the page to 100 % across and 10 % down.
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(round(left) - 5, round(top) - 5))
        end = QPoint(round(left + page.width()) + 5, round(top + page.height() * 0.1))
        QTest.mouseMove(canvas, end)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
        marked.update(dialog.areas())
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(RedactionDialog, "exec", mark_and_accept)
    tab = PagesTab()
    tab.open_file(pages[0].path)

    tab._redact()

    assert tab._source_path == pages[0].path and tab.has_unsaved_changes()
    assert not dialogs.save_path.exists()
    tab._save_as()

    assert list(marked) == [1]
    area = marked[1][0]
    assert (area.left(), area.top(), area.right()) == (0, 0, 1) and abs(area.bottom() - 0.1) < 0.01
    assert tab._source_path == dialogs.save_path  # the redacted document is now the open one
    (first, _), (second, _) = all_text(dialogs.save_path)
    assert "Verejný úvod" in first and second.strip() == ""
