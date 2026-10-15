from PySide6.QtCore import QPoint, QPointF, QSizeF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog
from pypdf import PdfReader

from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.text_box_dialog import TextBoxDialog
from pdftool.gui.text_boxes import TextBox, keep_on_page, text_rect, write_text_pdf
from pdftool.gui.thumbnails import open_document, render_page_scaled
from pdftool.operations import PageRef, open_pdf
from tests.helpers import make_pdf


def dark_pixel_box(image):
    points = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() and image.pixelColor(x, y).lightness() < 128
    ]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), max(xs), min(ys), max(ys)


def test_text_is_written_where_placed_with_diacritics_only_on_its_pages(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [400, 401])
    output = tmp_path / "out.pdf"
    # The second page is turned to landscape: shown 500 wide and 401 high.
    pages = [PageRef(source, 0), PageRef(source, 1, rotation=90)]
    boxes = {1: [TextBox("Ľubica Šťastná", 0.2, 0.5), TextBox("  ", 0.7, 0.1)]}

    write_text_pdf(pages, boxes, output)

    texts = [" ".join(page.extract_text().split()) for page in PdfReader(output).pages]
    assert texts == ["", "Ľubica Šťastná"]
    document = open_document(output)
    image = render_page_scaled(document, 1, 1.0)
    document.close()
    left, right, top, bottom = dark_pixel_box(image)
    # Upright on the turned page, starting at 20 % of 500 points and 50 % of 401 points.
    assert image.size().toTuple() == (500, 401)
    assert 100 <= left <= 104 and 200 <= top <= 206 and right - left > bottom - top
    assert sorted(path.name for path in tmp_path.iterdir()) == ["doc.pdf", "out.pdf"]


def test_text_is_kept_on_the_page():
    page = QSizeF(300, 200)

    moved = keep_on_page(TextBox("Dlhý text pri okraji", 0.95, 0.99, 20), page)

    rect = text_rect(page, moved)
    assert rect.right() <= 300.001 and rect.bottom() <= 200.001
    assert rect.width() > 100  # the text itself is not cut or shrunk


def click_page(dialog, x, y):
    canvas = dialog._canvas
    page = canvas.pixmap().deviceIndependentSize()
    left, top = (canvas.width() - page.width()) / 2, (canvas.height() - page.height()) / 2
    return QPoint(round(left + page.width() * x), round(top + page.height() * y))


def test_clicking_typing_and_dragging_in_the_dialog_places_text_that_the_tab_applies(app, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [400, 401])
    typed = {}

    def type_and_accept(dialog):
        dialog.resize(900, 700)
        dialog._view.refresh()
        QTest.mouseClick(dialog._canvas, Qt.MouseButton.LeftButton, pos=click_page(dialog, 0.5, 0.5))
        QTest.keyClicks(dialog._editor, "Meno")
        QTest.mouseClick(dialog._canvas, Qt.MouseButton.LeftButton, pos=click_page(dialog, 0.1, 0.9))
        # The second, empty text disappears once the first is grabbed and dragged up.
        QTest.mousePress(dialog._canvas, Qt.MouseButton.LeftButton, pos=click_page(dialog, 0.52, 0.5))
        QTest.mouseMove(dialog._canvas, click_page(dialog, 0.52, 0.2))
        typed["boxes"] = dialog.boxes()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(TextBoxDialog, "exec", type_and_accept)
    tab = PagesTab()
    tab.open_file(source)
    tab._list.item(1).setSelected(True)

    tab._type_text()

    (row, boxes), = typed["boxes"].items()
    assert row == 1 and [box.text for box in boxes] == ["Meno"]
    assert abs(boxes[0].left - 0.5) < 0.02 and boxes[0].top < 0.25
    assert tab.has_unsaved_changes()
    edited = tab._current_pages()
    texts = [" ".join(open_pdf(page.path).pages[page.index].extract_text().split()) for page in edited]
    assert texts == ["", "Meno"]


def test_nothing_typed_leaves_the_dialog_without_a_result(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [400])
    dialog = TextBoxDialog([PageRef(source, 0)], 0)
    dialog._press(QPointF(0.5, 0.5))

    assert dialog.boxes() == {} and not dialog._accept_button.isEnabled()
    QTest.keyClicks(dialog._editor, "x")
    assert dialog._accept_button.isEnabled()
    dialog._delete_selected()
    assert dialog.boxes() == {} and not dialog._accept_button.isEnabled()
