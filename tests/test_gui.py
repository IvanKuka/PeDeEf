"""End-to-end tests of the GUI tabs, run on Qt's offscreen platform (see conftest.py) with dialogs stubbed out."""

import warnings

from pypdf import PdfReader
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pdftool.gui import pages_tab
from pdftool.gui.merge_tab import MergeTab
from pdftool.gui.pages_tab import PagesTab
from pdftool.operations import PageRef, interleave_pages
from tests.helpers import make_pdf, page_rotations, page_widths


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


def test_extraction_cannot_overwrite_a_source_still_used_by_other_pages(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "source.pdf", [101, 102])
    before = source.read_bytes()
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    dialogs.save_path = source
    tab._extract_selected()
    assert source.read_bytes() == before
    assert tab._list.count() == 2
    assert dialogs.warnings


def test_commands_expose_both_signature_types_and_follow_document_state(app, tmp_path):
    from PySide6.QtWidgets import QLabel, QToolButton
    tab = PagesTab()
    labels = [label.text() for label in tab._ribbon.findChildren(QLabel, "commandCaption")]
    assert "Vložiť a podpis" in labels
    texts = [button.text() for button in tab._ribbon.findChildren(QToolButton, "commandButton")]
    assert "Obrázok\npodpisu" in texts and "Digitálny podpis\nP12 / PFX" in texts
    assert not tab._digital_signature_action.isEnabled()
    tab.open_file(make_pdf(tmp_path / "doc.pdf", [101]))
    assert tab._digital_signature_action.isEnabled()
    tab.close_file()
    assert not tab._digital_signature_action.isEnabled()


def test_command_ribbon_keeps_icons_and_readable_labels_in_small_window(app):
    from PySide6.QtWidgets import QToolButton
    from pdftool.gui.main_window import MainWindow

    window = MainWindow()
    window.resize(800, 540)
    window.centralWidget().setCurrentWidget(window.pages_tab)
    window.show()
    scroll = window.pages_tab._ribbon
    buttons = scroll.findChildren(QToolButton, "commandButton")
    assert len(buttons) == 26
    assert len({button.mapTo(scroll.widget(), QPoint(0, 0)).y() for button in buttons}) == 1
    for button in buttons:
        scroll.ensureWidgetVisible(button)
        app.processEvents()
        assert not button.icon().isNull()
        assert button.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        assert button.width() >= max(button.fontMetrics().horizontalAdvance(line)
                                     for line in button.text().splitlines()) + 20
        assert scroll.verticalScrollBar().maximum() == 0
        assert button.mapTo(scroll.viewport(), button.rect().bottomRight()).x() < scroll.viewport().width()
        assert button.mapTo(scroll.viewport(), QPoint(0, 0)).x() >= 0


def test_open_pdf_is_global_and_document_commands_stay_visible(app, monkeypatch):
    from PySide6.QtWidgets import QAbstractButton
    from pdftool.gui.main_window import MainWindow

    window = MainWindow()
    window.resize(800, 540)
    window.show()
    tabs = window.centralWidget()
    requested = []
    monkeypatch.setattr(window.pages_tab, "_choose_file", lambda: requested.append(tabs.currentWidget()))
    for workspace in (window.merge_tab, window.pages_tab, window.batch_tab):
        tabs.setCurrentWidget(workspace)
        app.processEvents()
        assert window.pages_tab._open_button.isVisible()
        window.pages_tab._open_button.click()
        assert tabs.currentWidget() is window.pages_tab
    assert requested == [window.pages_tab] * 3
    assert len([button for button in window.findChildren(QAbstractButton)
                if button.text() == "Otvoriť PDF…"]) == 1
    scroll = window.pages_tab._ribbon
    for position in (0, scroll.horizontalScrollBar().maximum()):
        scroll.horizontalScrollBar().setValue(position)
        app.processEvents()
        for button in (window.pages_tab._undo_button, window.pages_tab._redo_button,
                       window.pages_tab._save_button):
            assert button.isVisible()
            assert not scroll.isAncestorOf(button)


def test_command_bar_scrolls_with_mouse_wheel_without_inner_tabs(app):
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QLabel, QTabWidget, QToolButton
    from pdftool.gui.main_window import MainWindow

    window = MainWindow()
    window.resize(800, 540)
    window.centralWidget().setCurrentWidget(window.pages_tab)
    window.show()
    app.processEvents()
    tab = window.pages_tab
    assert not tab.findChildren(QTabWidget)
    captions = tab._ribbon.findChildren(QLabel, "commandCaption")
    assert [label.text() for label in captions] == ["Dokument", "Strany", "Vložiť a podpis", "Nástroje a ochrana"]
    buttons = tab._ribbon.findChildren(QToolButton, "commandButton")
    assert max(label.mapTo(tab._command_panel, QPoint()).y() for label in captions) < min(
        button.mapTo(tab._command_panel, QPoint()).y() for button in buttons)
    bar = tab._ribbon.horizontalScrollBar()
    assert bar.maximum() > 0
    event = QWheelEvent(QPointF(100, 40), QPointF(100, 40), QPoint(), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(tab._ribbon.viewport(), event)
    assert bar.value() > 0 and event.isAccepted()


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


def stub_insert_dialog(monkeypatch, pages, before=False):
    """Make the insert dialog immediately accept with the given 0-based pages of the chosen file."""

    class AcceptingInsertDialog:
        DialogCode = pages_tab.InsertDialog.DialogCode

        def __init__(self, source_path, page_count, has_selection, parent):
            self.has_selection = has_selection

        def exec(self):
            return self.DialogCode.Accepted

        def pages(self):
            return pages

        def insert_before(self):
            return before

    monkeypatch.setattr(pages_tab, "InsertDialog", AcceptingInsertDialog)


def choose_file_to_insert(monkeypatch, path):
    monkeypatch.setattr(pages_tab.QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))


def saved_widths(tab, dialogs, tmp_path):
    dialogs.save_path = tmp_path / "saved.pdf"
    tab._save_as()
    return page_widths(dialogs.save_path)


def selected_labels(tab):
    return [item.text() for item in tab._list.selectedItems()]


def test_pages_tab_moves_several_pages_keeping_their_order(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103, 104, 105])
    tab = PagesTab()
    tab.open_file(source)

    tab._move_rows([0, 2], 5)  # drop 1st and 3rd page after the last one

    assert visible_labels(tab) == ["1", "2", "3", "4", "5"]
    assert selected_labels(tab) == ["4", "5"]
    assert tab.has_unsaved_changes()
    assert saved_widths(tab, dialogs, tmp_path) == [102, 104, 105, 101, 103]


def test_pages_tab_moving_back_to_the_original_order_is_not_a_change(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)

    tab._move_rows([0], 3)
    assert tab.has_unsaved_changes()
    tab._move_rows([2], 0)

    assert not tab.has_unsaved_changes()


def test_pages_tab_rotation_follows_a_moved_page(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    tab._rotate_selected(90)

    tab._move_rows([0], 3)

    assert saved_widths(tab, dialogs, tmp_path) == [102, 103, 101]
    assert page_rotations(dialogs.save_path) == [0, 0, 90]


def test_pages_tab_split_uses_the_moved_order(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    tab._move_rows([2], 0)

    stub_split_dialog(monkeypatch, [[0], [1, 2]], tmp_path)
    tab._split()

    assert page_widths(tmp_path / "doc_01.pdf") == [103]
    assert page_widths(tmp_path / "doc_02.pdf") == [101, 102]


def test_pages_tab_duplicates_can_be_rotated_independently(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0, 1)

    tab._duplicate_selected()

    assert visible_labels(tab) == ["1", "2", "3", "4", "5"]
    assert selected_labels(tab) == ["3", "4"]  # the copies are selected
    tab._rotate_selected(90)
    assert saved_widths(tab, dialogs, tmp_path) == [101, 102, 101, 102, 103]
    assert page_rotations(dialogs.save_path) == [0, 0, 90, 90, 0]


def test_pages_tab_inserts_pages_from_another_file_after_selection(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    other = make_pdf(tmp_path / "other.pdf", [201, 202, 203])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    choose_file_to_insert(monkeypatch, other)
    stub_insert_dialog(monkeypatch, [2, 0])

    tab._insert_from_pdf()

    assert visible_labels(tab) == ["1", "2", "3", "4", "5"]
    assert selected_labels(tab) == ["2", "3"]
    assert tab._list.item(1).toolTip() == "other.pdf, strana 3"
    assert saved_widths(tab, dialogs, tmp_path) == [101, 203, 201, 102, 103]


def test_pages_tab_inserts_before_selection_and_at_end_without_one(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    other = make_pdf(tmp_path / "other.pdf", [201])
    tab = PagesTab()
    tab.open_file(source)
    choose_file_to_insert(monkeypatch, other)

    select_pages(tab, 1)
    stub_insert_dialog(monkeypatch, [0], before=True)
    tab._insert_from_pdf()
    tab._list.clearSelection()
    tab._insert_from_pdf()

    assert saved_widths(tab, dialogs, tmp_path) == [101, 201, 102, 201]


def test_pages_tab_insert_from_unreadable_file_leaves_document_untouched(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    secret = make_pdf(tmp_path / "secret.pdf", [201], password="tajne")
    tab = PagesTab()
    tab.open_file(source)
    choose_file_to_insert(monkeypatch, secret)

    tab._insert_from_pdf()

    assert "heslo nebolo zadané" in dialogs.warnings[0]
    assert visible_labels(tab) == ["1", "2"]
    assert not tab.has_unsaved_changes()


def test_pages_tab_save_reports_inserted_file_that_disappeared(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101])
    other = make_pdf(tmp_path / "other.pdf", [201])
    tab = PagesTab()
    tab.open_file(source)
    choose_file_to_insert(monkeypatch, other)
    stub_insert_dialog(monkeypatch, [0])
    tab._insert_from_pdf()
    other.unlink()
    errors = []
    monkeypatch.setattr(pages_tab.QMessageBox, "critical", lambda parent, title, text: errors.append(text))

    dialogs.save_path = tmp_path / "out.pdf"
    tab._save_as()

    assert "other.pdf" in errors[0]
    assert not dialogs.save_path.exists()
    assert tab.has_unsaved_changes()


def shown_tab(tmp_path, widths):
    tab = PagesTab()
    tab.resize(900, 600)
    tab.show()
    tab.open_file(make_pdf(tmp_path / "doc.pdf", widths))
    return tab


def test_page_grid_maps_drop_positions_to_insertion_rows(app, dialogs, tmp_path):
    grid = shown_tab(tmp_path, [101, 102, 103])._list
    first, last = (grid.visualItemRect(grid.item(row)) for row in (0, 2))

    assert grid.insertion_row(first.center() - QPoint(20, 0)) == 0  # left half of the first page
    assert grid.insertion_row(first.center() + QPoint(20, 0)) == 1  # right half of the first page
    assert grid.insertion_row(last.center() + QPoint(20, 0)) == 3  # right half of the last page
    assert grid.insertion_row(QPoint(first.center().x(), first.bottom() + 500)) == 3  # empty space below


def test_page_grid_mouse_drag_starts_dragging_the_selected_pages(app, dialogs, tmp_path, monkeypatch):
    grid = shown_tab(tmp_path, [101, 102, 103])._list
    dragged = []
    monkeypatch.setattr(type(grid), "startDrag", lambda self, actions: dragged.append(self.selectedIndexes()))
    start = grid.visualItemRect(grid.item(1)).center()

    QTest.mousePress(grid.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(grid.viewport(), start + QPoint(40, 0))

    assert [[index.row() for index in indexes] for indexes in dragged] == [[1]]


def test_page_grid_dropping_dragged_pages_reports_the_move(app, dialogs, tmp_path, monkeypatch):
    grid = shown_tab(tmp_path, [101, 102, 103])._list
    moves = []
    grid.rows_moved.connect(lambda rows, target: moves.append((rows, target)))
    # A real drag cannot run on the offscreen platform, so treat the drop as coming from the grid itself.
    monkeypatch.setattr(type(grid), "_is_reorder", lambda self, event: True)
    grid.item(0).setSelected(True)
    drop_point = grid.visualItemRect(grid.item(2)).center() + QPoint(20, 0)  # right half of the last page

    mime = QMimeData()
    buttons, modifiers = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        enter = QDragEnterEvent(drop_point, Qt.DropAction.MoveAction, mime, buttons, modifiers)
    QApplication.sendEvent(grid.viewport(), enter)
    drop = QDropEvent(QPointF(drop_point), Qt.DropAction.MoveAction, mime, buttons, modifiers)
    QApplication.sendEvent(grid.viewport(), drop)

    assert moves == [([0], 3)]


def test_insert_dialog_validates_page_ranges(app, tmp_path):
    from pdftool.gui.insert_dialog import InsertDialog

    dialog = InsertDialog(tmp_path / "other.pdf", 4, has_selection=True)

    assert dialog.pages() == [0, 1, 2, 3]  # empty = all pages
    assert dialog._insert_button.isEnabled()
    dialog._ranges_edit.setText("3-1, 4")
    assert dialog.pages() == [2, 1, 0, 3]
    dialog._ranges_edit.setText("9")
    assert not dialog._insert_button.isEnabled()
    assert "Strana 9" in dialog._error.text()
    assert not dialog.insert_before()


def test_pages_tab_can_save_over_a_file_it_inserted_pages_from(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    other = make_pdf(tmp_path / "other.pdf", [201, 202])
    tab = PagesTab()
    tab.open_file(source)
    choose_file_to_insert(monkeypatch, other)
    stub_insert_dialog(monkeypatch, [1])
    tab._insert_from_pdf()

    dialogs.save_path = other
    tab._save_as()

    assert page_widths(other) == [101, 102, 202]
    assert not tab.has_unsaved_changes()


def test_pages_tab_undo_redo_sequence_through_all_edit_kinds(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    other = make_pdf(tmp_path / "other.pdf", [201])
    tab = PagesTab()
    tab.open_file(source)
    choose_file_to_insert(monkeypatch, other)
    stub_insert_dialog(monkeypatch, [0])

    select_pages(tab, 0)
    tab._rotate_selected(90)
    tab._duplicate_selected()  # 4 pages
    tab._move_rows([1], 4)
    tab._insert_from_pdf()  # 5 pages
    select_pages(tab, 2)
    tab._delete_selected()
    final = tab._current_pages()
    assert "Odstránenie 1 strany" in tab._undo_button.toolTip()

    for _ in range(5):
        tab._undo()
    assert tab._current_pages() == [PageRef(source, index) for index in range(3)]
    assert not tab.has_unsaved_changes()  # back at the loaded state
    assert not tab._undo_button.isEnabled()

    for _ in range(5):
        tab._redo()
    assert tab._current_pages() == final


def test_pages_tab_undo_restores_the_selection(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    tab._duplicate_selected()
    assert selected_labels(tab) == ["2"]  # the copy

    tab._undo()
    assert tab._list.count() == 3

    tab._redo()
    assert tab._list.count() == 4
    assert selected_labels(tab) == ["2"]


def test_pages_tab_opening_another_file_or_saving_clears_history(app, dialogs, tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101, 102])
    second = make_pdf(tmp_path / "b.pdf", [201, 202])
    tab = PagesTab()
    tab.open_file(first)
    select_pages(tab, 0)
    tab._delete_selected()
    assert tab._undo_button.isEnabled()

    tab.open_file(second)

    assert not tab._undo_button.isEnabled()
    assert not tab._redo_button.isEnabled()
    tab._undo()
    assert [page.path for page in tab._current_pages()] == [second, second]

    select_pages(tab, 0)
    tab._delete_selected()
    assert saved_widths(tab, dialogs, tmp_path) == [202]
    assert not tab._undo_button.isEnabled()


def render_pending_thumbnails(tab):
    for renderer in tab._renderers.values():
        while renderer._pending:
            renderer._render_next()


def icon_centre_colour(item):
    image = item.icon().pixmap(pages_tab._THUMBNAIL_SIDE).toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2).name()


def test_pages_tab_rendered_thumbnail_reaches_every_copy_of_a_page(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    tab = PagesTab()
    tab.open_file(source)
    select_pages(tab, 0)
    tab._duplicate_selected()  # 101, 101, 102, 103
    select_pages(tab, 2)
    tab._delete_selected()  # a deleted page must not break rendering of the others
    assert icon_centre_colour(tab._list.item(1)) == "#f9fafb"  # placeholder

    render_pending_thumbnails(tab)

    # The blank test pages render white.
    assert [icon_centre_colour(tab._list.item(row)) for row in range(3)] == ["#ffffff"] * 3


def test_pages_tab_undo_to_a_state_without_selection_keeps_the_scroll_position(
    app, dialogs, tmp_path, monkeypatch
):
    other = make_pdf(tmp_path / "other.pdf", [201])
    tab = PagesTab()
    tab.resize(600, 400)
    tab.show()
    tab.open_file(make_pdf(tmp_path / "doc.pdf", [100 + index for index in range(60)]))
    choose_file_to_insert(monkeypatch, other)
    stub_insert_dialog(monkeypatch, [0])
    tab._insert_from_pdf()  # nothing selected: appended at the end and scrolled there
    tab._list.clearSelection()
    bar = tab._list.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)

    tab._undo()

    assert tab._list.count() == 60
    assert bar.value() == bar.maximum() // 2


def shown_preview(pages, row, source):
    from pdftool.gui.page_preview import PagePreviewDialog

    dialog = PagePreviewDialog(pages, row, source)
    dialog.resize(800, 700)
    dialog.show()
    QApplication.processEvents()
    return dialog


def preview_image_size(dialog):
    pixmap = dialog._view._label.pixmap()
    return pixmap.width(), pixmap.height()


def test_preview_shows_pages_as_edited_and_clamps_navigation(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [200, 300])
    other = make_pdf(tmp_path / "other.pdf", [400])
    pages = [PageRef(source, 1, rotation=90), PageRef(other, 0), PageRef(source, 0)]
    dialog = shown_preview(pages, 0, source)

    width, height = preview_image_size(dialog)
    assert width > height  # the 300 x 500 page is shown turned to landscape
    assert dialog._position_label.text() == "Strana 1 z 3"
    assert dialog._origin_label.text() == "pôvodne strana 2"

    QTest.keyClick(dialog, Qt.Key.Key_Right)
    QApplication.processEvents()
    assert dialog._origin_label.text() == "other.pdf, strana 1"
    QTest.keyClick(dialog, Qt.Key.Key_End)
    QTest.keyClick(dialog, Qt.Key.Key_Right)  # already at the last page
    assert dialog.current_row() == 2
    QTest.keyClick(dialog, Qt.Key.Key_Home)
    assert dialog.current_row() == 0


def test_preview_renders_only_the_last_page_of_fast_navigation(app, tmp_path, monkeypatch):
    from pdftool.gui import page_preview

    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103, 104])
    dialog = shown_preview([PageRef(source, index) for index in range(4)], 0, source)
    rendered = []
    original = page_preview.render_page_scaled
    monkeypatch.setattr(
        page_preview, "render_page_scaled", lambda doc, page, *args: rendered.append(page) or original(doc, page, *args)
    )

    for _ in range(3):
        QTest.keyClick(dialog, Qt.Key.Key_Right)
    QApplication.processEvents()

    assert rendered == [3]


def test_preview_zoom_fits_the_window_and_caps_huge_pages(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [400, 14000])  # the second page is 14000 x 500 points
    dialog = shown_preview([PageRef(source, 0), PageRef(source, 1)], 0, source)
    viewport = dialog._view.viewport()

    width, height = preview_image_size(dialog)
    assert width <= viewport.width() and height <= viewport.height()  # fitted
    dialog._view.zoom_in()
    QApplication.processEvents()
    assert not dialog._view.is_fitted()
    assert preview_image_size(dialog)[1] > height

    dialog.show_row(1)
    dialog._view.set_zoom(4.0)
    QApplication.processEvents()
    assert max(preview_image_size(dialog)) <= 5000
    assert dialog._view.zoom() < 4.0  # the label reports the zoom actually shown


def test_preview_of_a_file_that_cannot_be_rendered_shows_a_message(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101])
    pages = [PageRef(source, 0)]
    source.unlink()

    dialog = shown_preview(pages, 0, source)

    assert "nepodarilo vykresliť" in dialog._view._label.text()


def test_pages_tab_preview_opens_activated_page_and_selects_where_it_ended(app, dialogs, tmp_path, monkeypatch):
    opened = []

    class ClosingPreview:
        def __init__(self, pages, row, source_path, parent):
            opened.append(([page.index for page in pages], row))

        def exec(self):
            return 0

        def current_row(self):
            return 2  # the user paged on to the third page

        def deleteLater(self):
            pass

    monkeypatch.setattr(pages_tab, "PagePreviewDialog", ClosingPreview)
    tab = PagesTab()
    tab.open_file(make_pdf(tmp_path / "doc.pdf", [101, 102, 103]))
    tab._move_rows([2], 0)

    tab._list.itemActivated.emit(tab._list.item(1))

    assert opened == [([2, 0, 1], 1)]  # the pages in their current order
    assert selected_labels(tab) == ["3"]


def test_interleave_dialog_reports_counts_that_do_not_pair_up(app, tmp_path):
    from pdftool.gui.interleave_dialog import InterleaveDialog

    front = make_pdf(tmp_path / "front.pdf", [101, 102])
    dialog = InterleaveDialog(tmp_path)
    dialog.set_file("front", front)
    dialog.set_file("back", make_pdf(tmp_path / "back.pdf", [201, 202, 203]))
    assert not dialog._accept_button.isEnabled()
    assert "Počet zadných strán (3)" in dialog._error.text()

    dialog.set_file("back", front)
    assert "dvoch rôznych súboroch" in dialog._error.text()

    dialog.set_file("back", make_pdf(tmp_path / "back.pdf", [201, 202]))
    assert dialog._accept_button.isEnabled()
    assert "P1, Z2, P2, Z1" in dialog._order.text()


def test_pages_tab_interleaves_scans_as_an_undoable_unsaved_edit(app, dialogs, tmp_path, monkeypatch):
    front = make_pdf(tmp_path / "front.pdf", [101, 102, 103])
    back = make_pdf(tmp_path / "back.pdf", [201, 202])

    class AcceptingInterleaveDialog:
        DialogCode = pages_tab.InterleaveDialog.DialogCode

        def __init__(self, start_dir, parent):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def pages(self):
            return interleave_pages(front, 3, back, 2, reverse_back=True)

        def front_path(self):
            return front

    monkeypatch.setattr(pages_tab, "InterleaveDialog", AcceptingInterleaveDialog)
    tab = PagesTab()

    tab._interleave_scans()
    assert tab.has_unsaved_changes()
    tab._undo()
    assert [page.path for page in tab._current_pages()] == [front] * 3  # back to the front sides only
    tab._redo()

    assert saved_widths(tab, dialogs, tmp_path) == [101, 202, 102, 201, 103]
    assert page_widths(front) == [101, 102, 103] and page_widths(back) == [201, 202]  # sources untouched
