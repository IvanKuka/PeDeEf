from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from pdftool.gui.compare import Verdict, compare_documents
from pdftool.gui.compare_dialog import CompareDialog
from pdftool.gui.stamp_layer import write_stamp_layer
from pdftool.operations import PageRef, write_pages
from pdftool.stamps import Position, StampSpec

_TEXT = "Zmluvné strany sa dohodli na cene 1 250 € a lehote 14 dní. " * 3
_SPEC = StampSpec("x", Position.TOP_LEFT, 12)


def text_pdf(path, texts, sizes=None):
    write_stamp_layer(sizes or [(595, 842)] * len(texts), texts, _SPEC, path)
    return [PageRef(path, index) for index in range(len(texts))]


def test_identical_documents_show_no_differences(app, tmp_path):
    original = text_pdf(tmp_path / "a.pdf", [_TEXT, _TEXT + " Príloha.", "Podpisy"])
    copy = tmp_path / "copy.pdf"
    write_pages(original, copy)  # saved again by the app: different file, same look

    pairs = compare_documents(original, [PageRef(copy, index) for index in range(3)])

    assert [pair.verdict for pair in pairs] == [Verdict.EQUAL] * 3


def test_changes_sizes_and_extra_pages_are_told_apart(app, tmp_path):
    first = text_pdf(tmp_path / "a.pdf", [_TEXT, _TEXT, _TEXT, "Dodatok"])
    second = text_pdf(
        tmp_path / "b.pdf",
        [_TEXT, _TEXT.replace("14 dní", "30 dní"), _TEXT],
        sizes=[(595, 842), (595, 842), (612, 792)],  # the third page is US Letter
    )

    pairs = compare_documents(first, second)

    assert [pair.verdict for pair in pairs] == [Verdict.EQUAL, Verdict.DIFFERENT, Verdict.OTHER_SIZE, Verdict.ONLY_FIRST]
    changed = pairs[1].first
    red = sum(
        1
        for y in range(0, changed.height(), 2)
        for x in range(0, changed.width(), 2)
        if changed.pixelColor(x, y).red() > 180 and changed.pixelColor(x, y).green() < 120
    )
    assert red > 0  # the changed number is highlighted


def test_differences_can_be_walked_with_the_keyboard(app, tmp_path):
    first = text_pdf(tmp_path / "a.pdf", ["A", "B", "C", "D"])
    second = text_pdf(tmp_path / "b.pdf", ["A", "X", "C", "Y"])
    dialog = CompareDialog(compare_documents(first, second), "a.pdf", "b.pdf")
    dialog.show()
    QTest.qWaitForWindowActive(dialog)  # window shortcuts only work in the active window

    assert dialog.current_position() == 1  # opens on the first difference
    QTest.keyClick(dialog, Qt.Key.Key_F3)
    assert dialog.current_position() == 3
    QTest.keyClick(dialog, Qt.Key.Key_F3)
    assert dialog.current_position() == 1  # wraps around
    QTest.keyClick(dialog, Qt.Key.Key_F3, Qt.KeyboardModifier.ShiftModifier)
    assert dialog.current_position() == 3
