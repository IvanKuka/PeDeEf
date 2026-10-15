import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
from PySide6.QtCore import QPoint, QSize, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPageSize, QPainter, QPdfWriter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QLabel

from pdftool.gui import pages_tab
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.signature import SignaturePlacement, keep_on_page, write_signed_pdf
from pdftool.gui.signature_dialog import SignatureDialog
from pdftool.gui.thumbnails import open_document, render_page_scaled
from pdftool.operations import PageRef, has_digital_signature


def blue_pdf(path, width, height):
    writer = QPdfWriter(str(path))
    writer.setResolution(72)
    writer.setPageSize(QPageSize(QSizeF(width, height), QPageSize.Unit.Point))
    painter = QPainter(writer)
    painter.fillRect(0, 0, 10_000, 10_000, QColor("blue"))
    painter.end()
    return path


def half_transparent_signature():
    """200 x 100 pixels: left half transparent, right half red."""
    image = QImage(200, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.fillRect(100, 0, 100, 100, QColor("red"))
    painter.end()
    return image


def colour_at(image, x, y):
    color = image.pixelColor(x, y)
    return "red" if color.red() > 200 and color.blue() < 60 else "blue" if color.blue() > 200 else "other"


def test_signature_lands_where_placed_on_a_rotated_page_and_keeps_transparency(app, tmp_path):
    source = blue_pdf(tmp_path / "doc.pdf", 400, 600)
    output = tmp_path / "out.pdf"
    # Turned to landscape: the visible page is 600 wide and 400 high.
    pages = [PageRef(source, 0), PageRef(source, 0, rotation=90)]
    placement = SignaturePlacement(center_x=0.5, center_y=0.75, width=0.4)

    write_signed_pdf(pages, 1, half_transparent_signature(), placement, output)

    document = open_document(output)
    untouched = render_page_scaled(document, 0, 1.0)
    signed = render_page_scaled(document, 1, 1.0)
    document.close()
    assert colour_at(untouched, 200, 450) == "blue"
    assert signed.size().toTuple() == (600, 400)
    # The picture is 240 x 120 points around (300, 300): x 180–420, y 240–360.
    assert colour_at(signed, 390, 300) == "red"
    assert colour_at(signed, 210, 300) == "blue"  # the transparent half shows the page
    assert colour_at(signed, 430, 300) == "blue" and colour_at(signed, 390, 230) == "blue"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["doc.pdf", "out.pdf"]


def test_dragging_in_the_preview_places_the_signature_and_the_tab_saves_it(app, dialogs, tmp_path, monkeypatch):
    source = blue_pdf(tmp_path / "doc.pdf", 400, 600)
    picture = tmp_path / "podpis.png"
    half_transparent_signature().save(str(picture))
    dialogs.save_path = tmp_path / "doc_podpisane.pdf"
    monkeypatch.setattr(pages_tab.QFileDialog, "getOpenFileName", lambda *args: (str(picture), ""))
    placed = {}

    def place_and_accept(dialog):
        preview = dialog._preview
        page = preview.pixmap().deviceIndependentSize()
        left, top = (preview.width() - page.width()) / 2, (preview.height() - page.height()) / 2
        # Drag the picture to the upper left quarter of the page.
        target = QPoint(round(left + page.width() * 0.3), round(top + page.height() * 0.25))
        QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=target)
        placed["placement"] = dialog.placement()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SignatureDialog, "exec", place_and_accept)
    tab = PagesTab()
    tab.open_file(source)

    tab._place_signature()

    assert tab._source_path == source and tab.has_unsaved_changes()
    assert not dialogs.save_path.exists()
    tab._save_as()

    assert placed["placement"].center_x == pytest.approx(0.3, abs=0.01)
    assert placed["placement"].center_y == pytest.approx(0.25, abs=0.01)
    assert tab._source_path == dialogs.save_path  # the signed document is now the open one
    document = open_document(dialogs.save_path)
    signed = render_page_scaled(document, 0, 1.0)
    document.close()
    # 25 % of 400 points wide (100 x 50), centred at (120, 150): its red half is x 120–170.
    assert colour_at(signed, 145, 150) == "red" and colour_at(signed, 95, 150) == "blue"


def test_a_digitally_signed_document_is_recognised_and_the_dialog_says_what_the_picture_is(app, tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=600)
    signature_field = writer._add_object(
        DictionaryObject(
            {
                NameObject("/FT"): NameObject("/Sig"),
                NameObject("/T"): TextStringObject("Podpis1"),
                NameObject("/V"): DictionaryObject({NameObject("/Type"): NameObject("/Sig")}),  # signed
            }
        )
    )
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject(
        {NameObject("/Fields"): ArrayObject([signature_field])}
    )
    signed = tmp_path / "podpisany.pdf"
    writer.write(signed)
    plain = blue_pdf(tmp_path / "doc.pdf", 400, 600)

    assert has_digital_signature(signed) and not has_digital_signature(plain)
    dialog = SignatureDialog([PageRef(signed, 0)], 0, half_transparent_signature(), digitally_signed=True)
    texts = " ".join(label.text() for label in dialog.findChildren(QLabel) if label.isVisibleTo(dialog))
    assert "nie je to elektronický ani certifikovaný digitálny podpis" in texts.lower()
    assert "digitálny podpis nebude platný" in texts


def test_placement_is_kept_on_the_page():
    page, picture = QSizeF(600, 400), QSize(200, 100)

    moved = keep_on_page(SignaturePlacement(0.99, 0.01, 0.4), page, picture)

    # 40 % of the width is 240 x 120 points: its centre must stay 120 / 60 points from the edges.
    assert (round(moved.center_x, 3), round(moved.center_y, 3)) == (0.8, 0.15)
    huge = keep_on_page(SignaturePlacement(0.1, 0.9, 1.0), page, QSize(100, 200))
    assert (huge.center_x, huge.center_y) == (0.5, 0.5)  # taller than the page: centred
