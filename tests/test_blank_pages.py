import random
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from pdftool.gui import pages_tab
from pdftool.gui.blank_pages import SENSITIVITY_LEVELS, measure_pages
from pdftool.gui.blank_pages_dialog import BlankPagesDialog
from pdftool.gui.pages_tab import PagesTab
from pdftool.operations import PageRef

_WIDTH, _HEIGHT = 595, 842


def _dust(painter):
    rng = random.Random(1)
    painter.setPen(QColor("#555555"))
    for _ in range(400):
        painter.drawPoint(rng.uniform(0, _WIDTH), rng.uniform(0, _HEIGHT))


def _text(painter, colour, size, rect, text, lines=1):
    font = QFont("Arial")
    font.setPixelSize(size)
    painter.setFont(font)
    painter.setPen(QColor(colour))
    for line in range(lines):
        painter.drawText(rect.translated(0, line * (size + 3)), 0, text)


# Scanned-looking pages: what a blank-page finder must and must not propose.
SAMPLES = {
    "blank": lambda p: None,
    "dust": _dust,
    "show-through": lambda p: (_dust(p), _text(p, "#e6e6e6", 11, QRectF(60, 60, 480, 14), "Lorem ipsum dolor sit amet", 50)),
    "scanner edge": lambda p: (_dust(p), p.fillRect(QRectF(0, 0, 6, _HEIGHT), QColor("#404040"))),
    "page number": lambda p: _text(p, "black", 9, QRectF(290, _HEIGHT - 40, 20, 12), "12"),
    "pencil note": lambda p: _text(p, "#8a8a8a", 10, QRectF(80, 300, 300, 14), "pozri str. 4"),
    "text": lambda p: _text(p, "black", 11, QRectF(60, 60, 480, 14), "Tri riadky skutočného textu na strane.", 3),
}


def make_scans(path: Path) -> Path:
    writer = QPdfWriter(str(path))
    writer.setResolution(150)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF()))
    painter = QPainter(writer)
    for number, draw in enumerate(SAMPLES.values()):
        if number:
            writer.newPage()
        scan = QImage(1240, 1754, QImage.Format.Format_RGB32)
        scan.fill(QColor("white"))
        scan_painter = QPainter(scan)
        scan_painter.scale(1240 / _WIDTH, 1754 / _HEIGHT)
        draw(scan_painter)
        scan_painter.end()
        painter.drawImage(QRectF(0, 0, writer.width(), writer.height()), scan)  # pages are images, like scans
    painter.end()
    return path


def test_only_truly_blank_scans_count_as_blank_by_default(app, tmp_path):
    source = make_scans(tmp_path / "scans.pdf")

    measured = measure_pages([PageRef(source, index) for index in range(len(SAMPLES))])

    strict = SENSITIVITY_LEVELS[0][1]
    blank = {name for name, page in zip(SAMPLES, measured) if page.ink_ratio <= strict}
    assert blank == {"blank", "dust", "show-through", "scanner edge"}
    # The more lenient level also proposes the page number and the pencil note, never real text.
    lenient = SENSITIVITY_LEVELS[1][1]
    assert {name for name, page in zip(SAMPLES, measured) if page.ink_ratio <= lenient} == blank | {"page number", "pencil note"}


def test_dialog_keeps_unticked_pages_across_sensitivity_changes(app, tmp_path):
    source = make_scans(tmp_path / "scans.pdf")
    dialog = BlankPagesDialog(measure_pages([PageRef(source, index) for index in range(len(SAMPLES))]))
    assert dialog.rows_to_remove() == [0, 1, 2, 3]

    dialog._list.item(1).setCheckState(Qt.CheckState.Unchecked)  # the user keeps the dusty page
    dialog._level_combo.setCurrentIndex(1)

    assert dialog.rows_to_remove() == [0, 2, 3, 4, 5]
    assert dialog._remove_button.text() == "Odstrániť 5 strán"


def test_pages_tab_removes_confirmed_blank_pages_as_an_undoable_step(app, tmp_path, monkeypatch):
    source = make_scans(tmp_path / "scans.pdf")

    class AcceptingDialog:
        DialogCode = BlankPagesDialog.DialogCode

        def __init__(self, measured, parent):
            self._rows = [row for row, page in enumerate(measured) if page.ink_ratio <= SENSITIVITY_LEVELS[0][1]]

        def exec(self):
            return self.DialogCode.Accepted

        def rows_to_remove(self):
            return self._rows

    monkeypatch.setattr(pages_tab, "BlankPagesDialog", AcceptingDialog)
    tab = PagesTab()
    tab.open_file(source)

    tab._find_blank_pages()
    assert [page.index for page in tab._current_pages()] == [4, 5, 6]
    tab._undo()
    assert tab._list.count() == len(SAMPLES)
