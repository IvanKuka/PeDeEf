"""End-to-end tests of the GUI tabs, run on Qt's offscreen platform with dialogs stubbed out."""

import os
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import shiboken6
from pypdf import PdfReader
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from pdftool.gui import merge_tab, pages_tab
from pdftool.gui.merge_tab import MergeTab
from pdftool.gui.pages_tab import PagesTab
from tests.helpers import make_pdf, page_rotations, page_widths


@pytest.fixture(scope="session")
def qapp():
    # One QApplication for the whole session: creating a second one after the first is destroyed crashes Qt.
    return QApplication.instance() or QApplication([])


@pytest.fixture
def app(qapp):
    yield qapp
    # Destroy the test's widgets while the QApplication still exists. Left to Python's
    # garbage collector, they may be destroyed after it at interpreter exit, which
    # intermittently crashes the test process.
    for widget in qapp.topLevelWidgets():
        shiboken6.delete(widget)


@pytest.fixture
def dialogs(monkeypatch):
    """Replace modal dialogs with recorders.

    Tests set `save_path` to answer save dialogs and `confirm_answer` to answer confirmations.
    """

    class Recorder:
        def __init__(self):
            self.save_path = None
            self.confirm_answer = True
            self.confirmations: list[str] = []
            self.warnings: list[str] = []
            self.information: list[str] = []
            self.successes: list[str] = []

        def confirm(self, parent, title, text, confirm_label):
            self.confirmations.append(text)
            return self.confirm_answer

    recorder = Recorder()
    for module in (merge_tab, pages_tab):
        monkeypatch.setattr(module, "ask_save_pdf_path", lambda *args: recorder.save_path)
        monkeypatch.setattr(module, "report_success", lambda parent, message, target: recorder.successes.append(message))
        monkeypatch.setattr(module.QMessageBox, "warning", lambda parent, title, text: recorder.warnings.append(text))
        monkeypatch.setattr(module.QMessageBox, "information", lambda parent, title, text: recorder.information.append(text))
        monkeypatch.setattr(module.QMessageBox, "critical", lambda parent, title, text: pytest.fail(text))
    monkeypatch.setattr(pages_tab, "confirm", recorder.confirm)
    return recorder


def stub_split_dialog(monkeypatch, groups, output_dir):
    """Make the split dialog immediately accept with the given (visible-position) page groups."""

    class AcceptingSplitDialog:
        DialogCode = pages_tab.SplitDialog.DialogCode

        def __init__(self, source_path, page_count, parent):
            self.page_count = page_count

        def exec(self):
            return self.DialogCode.Accepted

        def page_groups(self):
            return groups

        def output_dir(self):
            return output_dir

    monkeypatch.setattr(pages_tab, "SplitDialog", AcceptingSplitDialog)


def select_pages(tab, *rows):
    tab._list.clearSelection()
    for row in rows:
        tab._list.item(row).setSelected(True)


def visible_labels(tab):
    return [tab._list.item(row).text() for row in range(tab._list.count())]


def test_merge_tab_merges_selected_ranges_in_list_order(app, dialogs, tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101, 102, 103])
    second = make_pdf(tmp_path / "b.pdf", [201, 202])
    tab = MergeTab()

    tab.add_files([first, second])
    tab._list.setCurrentRow(0)
    tab._on_range_edited("3, 1")
    tab._move_current(1)  # a.pdf now comes after b.pdf
    dialogs.save_path = tmp_path / "out.pdf"
    tab._merge()

    assert page_widths(dialogs.save_path) == [201, 202, 103, 101]
    assert dialogs.successes


def test_merge_tab_reports_files_it_cannot_open(app, dialogs, tmp_path):
    good = make_pdf(tmp_path / "a.pdf", [101])
    bad = tmp_path / "notes.txt"
    bad.write_text("not a pdf")
    tab = MergeTab()

    tab.add_files([good, bad])

    assert tab._list.count() == 1
    assert "notes.txt" in dialogs.warnings[0]


def test_merge_tab_blocks_merge_with_invalid_range(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101])
    tab = MergeTab()
    tab.add_files([source])
    tab._on_range_edited("5")
    dialogs.save_path = tmp_path / "out.pdf"

    tab._merge()

    assert not dialogs.save_path.exists()
    assert "Strana 5" in dialogs.warnings[0]


def drop_files(widget, paths) -> None:
    """Deliver a drop of local files to the list's viewport, as Explorer drag & drop does."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    viewport = widget._list.viewport()
    assert viewport.acceptDrops(), "Qt would not deliver drops to this list at all"
    buttons, modifiers = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    # Qt only delivers a drop to a widget that accepted the preceding drag-enter.
    # PySide flags the only QDragEnterEvent constructor as deprecated, without a replacement.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        enter = QDragEnterEvent(viewport.rect().center(), Qt.DropAction.CopyAction, mime, buttons, modifiers)
    QApplication.sendEvent(viewport, enter)
    drop = QDropEvent(QPointF(viewport.rect().center()), Qt.DropAction.CopyAction, mime, buttons, modifiers)
    QApplication.sendEvent(viewport, drop)


def test_merge_tab_accepts_dropped_files(app, dialogs, tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101])
    second = make_pdf(tmp_path / "b.pdf", [201])
    tab = MergeTab()

    drop_files(tab, [first, second])

    assert tab._list.count() == 2


def test_pages_tab_opens_dropped_file(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    tab = PagesTab()

    drop_files(tab, [source])

    assert tab._source_path == source
    assert tab._list.count() == 2


def test_pages_tab_extracts_rotated_selection(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)

    tab._list.item(2).setSelected(True)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    tab._list.item(0).setSelected(False)
    dialogs.save_path = tmp_path / "selection.pdf"
    tab._extract_selected()

    assert page_widths(dialogs.save_path) == [103]
    assert page_rotations(dialogs.save_path) == [90]
    assert tab.has_unsaved_changes()


def test_pages_tab_save_as_bakes_in_rotation_and_reopens(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    tab = PagesTab()
    tab.open_file(source)

    tab._list.item(1).setSelected(True)
    tab._rotate_selected(-90)
    dialogs.save_path = source  # overwrite the open document
    tab._save_as()

    assert page_rotations(source) == [0, 270]
    assert not tab.has_unsaved_changes()
    assert tab._list.count() == 2


def test_pages_tab_split_writes_one_file_per_group(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)

    stub_split_dialog(monkeypatch, [[0, 1], [2]], tmp_path)
    tab._split()

    assert page_widths(tmp_path / "doc_01.pdf") == [101, 102]
    assert page_widths(tmp_path / "doc_02.pdf") == [103]
    assert len(PdfReader(source).pages) == 3


def test_pages_tab_deleted_pages_are_left_out_when_saving(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103, 104])
    tab = PagesTab()
    tab.open_file(source)

    select_pages(tab, 0, 2)
    tab._delete_selected()

    assert visible_labels(tab) == ["1", "2"]
    assert tab.has_unsaved_changes()
    assert page_widths(source) == [101, 102, 103, 104]  # nothing written before saving

    dialogs.save_path = tmp_path / "out.pdf"
    tab._save_as()

    assert page_widths(dialogs.save_path) == [102, 104]
    assert not tab.has_unsaved_changes()


def test_pages_tab_split_uses_visible_positions_after_delete(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103, 104])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 1)
    tab._delete_selected()

    # "1-2, 3" in the dialog refers to the pages as shown: 101, 103 | 104.
    stub_split_dialog(monkeypatch, [[0, 1], [2]], tmp_path)
    tab._split()

    assert page_widths(tmp_path / "doc_01.pdf") == [101, 103]
    assert page_widths(tmp_path / "doc_02.pdf") == [104]


def test_pages_tab_rotation_survives_deleting_other_pages(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)

    select_pages(tab, 2)
    tab._rotate_selected(90)
    select_pages(tab, 0)
    tab._delete_selected()
    dialogs.save_path = tmp_path / "out.pdf"
    tab._save_as()

    assert page_widths(dialogs.save_path) == [102, 103]
    assert page_rotations(dialogs.save_path) == [0, 90]


def test_pages_tab_refuses_to_delete_every_page(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    tab = PagesTab()
    tab.open_file(source)

    tab._list.selectAll()
    tab._delete_selected()

    assert tab._list.count() == 2
    assert dialogs.information


def test_pages_tab_discard_changes_restores_all_pages(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 1)
    tab._delete_selected()

    tab._discard_changes()

    assert visible_labels(tab) == ["1", "2", "3"]
    assert not tab.has_unsaved_changes()


def test_pages_tab_close_file_asks_before_discarding_changes(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    tab._delete_selected()

    dialogs.confirm_answer = False
    tab.close_file()
    assert tab._source_path == source

    dialogs.confirm_answer = True
    tab.close_file()
    assert tab._source_path is None
    assert tab._list.count() == 0
    assert len(dialogs.confirmations) == 2


def test_pages_tab_close_without_changes_does_not_ask(app, dialogs, tmp_path):
    tab = PagesTab()
    tab.open_file(make_pdf(tmp_path / "doc.pdf", [101]))

    tab.close_file()

    assert tab._source_path is None
    assert dialogs.confirmations == []
