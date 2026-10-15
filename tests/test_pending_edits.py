"""Multiple document edits stay undoable until the user's single final save."""

import pytest
from pypdf import PdfReader
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QDialog

from pdftool.gui import pages_tab
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.redaction_dialog import RedactionDialog
from pdftool.gui.stamp_dialog import StampDialog
from pdftool.operations import PdfToolError, open_pdf, password_for, write_pages
from tests.helpers import make_pdf


def test_stamp_redaction_undo_redo_and_final_save_keep_the_source_intact(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "source.pdf", [595, 595])
    original = source.read_bytes()
    output = tmp_path / "finished.pdf"
    dialogs.save_path = output
    tab = PagesTab()
    tab.open_file(source)
    monkeypatch.setattr(StampDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    tab._stamp()
    stamped = tab._current_pages()
    assert open_pdf(stamped[0].path).pages[0].extract_text().split() == ["1", "/", "2"]
    def redact(dialog):
        dialog._add_area(QRectF(0, 0, 1, 1))
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(RedactionDialog, "exec", redact)
    tab._redact()
    redacted = tab._current_pages()
    assert not open_pdf(redacted[0].path).pages[0].extract_text().strip()
    assert open_pdf(redacted[1].path).pages[1].extract_text().split() == ["2", "/", "2"]
    assert source.read_bytes() == original and not output.exists()
    assert tab._undo_button.text() == "Späť" and tab._redo_button.text() == "Znova"
    tab._undo_button.click()
    assert tab._current_pages() == stamped
    tab._redo_button.click()
    assert tab._current_pages() == redacted
    tab._list.item(1).setSelected(True)
    tab._rotate_selected(90)
    working_paths = tuple(tab._working.sources)
    tab._save_as()
    reader = PdfReader(output)
    assert not reader.pages[0].extract_text().strip()
    assert reader.pages[1].extract_text().split() == ["2", "/", "2"] and reader.pages[1].rotation == 90
    assert source.read_bytes() == original and not tab.has_unsaved_changes()
    assert all(not path.exists() and password_for(path) is None for path in working_paths)


def test_internal_encryption_does_not_prompt_but_original_protection_is_kept_at_save(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "protected.pdf", [595], password="original-password")
    dialogs.passwords = ["original-password"]
    tab = PagesTab()
    tab.open_file(source)
    prompts = []
    def final_password(parent, sources, always=False):
        prompts.append(tuple(sources))
        return True, "final-password"
    monkeypatch.setattr(pages_tab, "output_password", final_password)
    for _ in range(2):
        pages = tab._current_pages()
        tab._apply_document_edit("Edit", lambda output, password, info: write_pages(pages, output, password, info))
    assert prompts == []
    working = tab._current_pages()[0].path
    assert PdfReader(working).is_encrypted
    dialogs.save_path = tmp_path / "final.pdf"
    tab._save_as()
    assert prompts == [(source,)]
    reader = PdfReader(dialogs.save_path)
    assert reader.is_encrypted and reader.decrypt("final-password")


@pytest.mark.parametrize("cancel", [False, True])
def test_failed_or_cancelled_edit_keeps_document_history_and_existing_files(app, dialogs, tmp_path, monkeypatch, cancel):
    source = make_pdf(tmp_path / "source.pdf", [595])
    original = source.read_bytes()
    tab = PagesTab()
    tab.open_file(source)
    before = tab._current_pages()
    attempted = []
    errors = []
    monkeypatch.setattr(pages_tab.QMessageBox, "critical", lambda parent, title, text: errors.append(text))
    def failed(output, password, info):
        attempted.append(output)
        write_pages(before, output, password, info)
        raise pages_tab._Cancelled() if cancel else PdfToolError("Expected failure")
    tab._apply_document_edit("Edit", failed)
    assert tab._current_pages() == before and not tab.has_unsaved_changes()
    assert not tab._history.can_undo and not tab._working.sources
    assert all(not path.exists() for path in attempted)
    assert source.read_bytes() == original
    assert errors == ([] if cancel else ["Expected failure"])


def test_closing_pending_document_can_be_cancelled_then_releases_working_copies(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "source.pdf", [595])
    tab = PagesTab()
    tab.open_file(source)
    pages = tab._current_pages()
    tab._apply_document_edit("Edit", lambda output, password, info: write_pages(pages, output, password, info))
    working = tab._current_pages()[0].path
    dialogs.confirm_answer = False
    tab.close_file()
    assert working.exists() and tab.has_unsaved_changes()
    dialogs.confirm_answer = True
    tab.close_file()
    assert not working.exists() and password_for(working) is None
    assert tab._source_path is None and not tab.has_unsaved_changes()


def test_redaction_zoom_keeps_normalized_coordinates_and_accepts_multiple_pages(app, tmp_path):
    source = make_pdf(tmp_path / "source.pdf", [595, 595])
    from pdftool.operations import PageRef
    dialog = RedactionDialog([PageRef(source, 0), PageRef(source, 1)], 0)
    dialog.resize(1000, 700)
    dialog.show()
    app.processEvents()
    area = QRectF(0.1, 0.2, 0.3, 0.4)
    dialog._add_area(area)
    dialog._zoom.setCurrentIndex(dialog._zoom.findData(2))
    assert dialog.areas() == {0: [area]}
    dialog._page_spin.setValue(2)
    dialog._add_area(area)
    assert dialog.areas() == {0: [area], 1: [area]}
    assert dialog._preview_scroll.verticalScrollBar().maximum() > 0
    dialog.reject()


def test_ok_applies_multiple_edits_and_save_replaces_current_pdf_without_a_file_dialog(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "source.pdf", [595, 595])
    original = source.read_bytes()
    tab = PagesTab()
    tab.open_file(source)
    monkeypatch.setattr(pages_tab, "ask_save_pdf_path", lambda *args: pytest.fail("Unexpected Save As dialog"))
    monkeypatch.setattr(StampDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    tab._stamp()
    def redact(dialog):
        dialog._add_area(QRectF(0, 0, 1, 1))
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(RedactionDialog, "exec", redact)
    tab._redact()
    tab._list.item(1).setSelected(True)
    tab._rotate_selected(90)
    assert source.read_bytes() == original
    assert tab._source_path == source and tab.has_unsaved_changes()
    tab._save_button.click()
    reader = PdfReader(source)
    assert not reader.pages[0].extract_text().strip()
    assert reader.pages[1].extract_text().split() == ["2", "/", "2"]
    assert reader.pages[1].rotation == 90
    assert tab._source_path == source and not tab.has_unsaved_changes()
    assert not tab._save_button.isEnabled() and tab._save_as_button.isEnabled()
    assert list(tmp_path.iterdir()) == [source]


def test_save_current_keeps_existing_password_without_prompting(app, dialogs, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "protected.pdf", [595], password="original-password")
    dialogs.passwords = ["original-password"]
    tab = PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    monkeypatch.setattr(pages_tab, "output_password", lambda *args: pytest.fail("Password already known"))
    monkeypatch.setattr(pages_tab, "ask_save_pdf_path", lambda *args: pytest.fail("Unexpected Save As dialog"))
    tab._save_current()
    reader = PdfReader(source)
    assert reader.is_encrypted and reader.decrypt("original-password")
    assert reader.pages[0].rotation == 90 and not tab.has_unsaved_changes()


def test_failed_overwrite_keeps_source_and_pending_edits_for_retry(app, dialogs, tmp_path, monkeypatch):
    from pdftool import operations
    source = make_pdf(tmp_path / "source.pdf", [595])
    original = source.read_bytes()
    tab = PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    errors = []
    monkeypatch.setattr(pages_tab.QMessageBox, "critical", lambda parent, title, text: errors.append(text))
    def fail_replace(*args):
        raise PermissionError("File locked")
    with monkeypatch.context() as locked:
        locked.setattr(operations.os, "replace", fail_replace)
        tab._save_current()
    assert errors and source.read_bytes() == original and tab.has_unsaved_changes()
    assert tab._current_pages()[0].rotation == 90
    tab._save_current()
    assert PdfReader(source).pages[0].rotation == 90 and not tab.has_unsaved_changes()


def test_cancelling_overwrite_confirmation_keeps_source_and_work(app, dialogs, tmp_path):
    source = make_pdf(tmp_path / "source.pdf", [595])
    original = source.read_bytes()
    tab = PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    dialogs.confirm_answer = False
    tab._save_current()
    assert source.read_bytes() == original and tab.has_unsaved_changes()
    assert tab._current_pages()[0].rotation == 90
    assert len(dialogs.confirmations) == 1 and str(source) in dialogs.confirmations[0]
    dialogs.confirm_answer = True
    tab._save_current()
    assert PdfReader(source).pages[0].rotation == 90 and not tab.has_unsaved_changes()
