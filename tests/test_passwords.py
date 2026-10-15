import pytest

from pdftool.batch import Status, rotate_operation, run_batch
from pdftool.gui import passwords
from pdftool.gui.pages_tab import PagesTab
from pdftool.operations import PageRef, PasswordRequired, open_pdf, page_count, unlock, write_pages
from tests.helpers import make_pdf, page_widths


def test_unlock_accepts_only_the_right_password_and_protects_new_files(tmp_path):
    secret = make_pdf(tmp_path / "secret.pdf", [101, 102], password="tajné heslo")
    with pytest.raises(PasswordRequired):
        page_count(secret)

    assert not unlock(secret, "")  # the empty password is always tried automatically, never asked for
    assert not unlock(secret, "zlé")
    assert unlock(secret, "tajné heslo")
    assert page_count(secret) == 2

    protected = tmp_path / "protected.pdf"
    write_pages([PageRef(secret, 1)], protected, password="nové")
    with pytest.raises(PasswordRequired):
        page_count(protected)
    assert unlock(protected, "nové")
    assert [int(page.mediabox.width) for page in open_pdf(protected).pages] == [102]


def test_pages_tab_asks_again_after_a_wrong_password_and_shows_thumbnails(app, dialogs, tmp_path):
    secret = make_pdf(tmp_path / "secret.pdf", [101, 102], password="tajne")
    dialogs.passwords = ["zle", "tajne"]
    tab = PagesTab()

    tab.open_file(secret)

    assert dialogs.password_prompts == [False, True]  # the second prompt says the first was wrong
    assert tab._list.count() == 2
    assert secret in tab._renderers  # QtPdf opened it with the password too


def test_saving_a_protected_document_offers_to_keep_the_protection(app, dialogs, tmp_path, monkeypatch):
    secret = make_pdf(tmp_path / "secret.pdf", [101, 102], password="tajne")
    dialogs.passwords = ["tajne"]
    tab = PagesTab()
    tab.open_file(secret)

    class NewPassword:
        def __init__(self, parent, reason):
            pass

        def exec(self):
            return passwords.QDialog.DialogCode.Accepted

        def password(self):
            return "nove"

    monkeypatch.setattr(passwords, "NewPasswordDialog", NewPassword)
    monkeypatch.setattr(passwords, "ask_keep_protection", lambda parent: True)
    dialogs.save_path = tmp_path / "kept.pdf"
    tab._save_as()
    with pytest.raises(PasswordRequired):
        page_count(_fresh_copy(dialogs.save_path, tmp_path))
    assert tab._list.count() == 2  # the saved file is open again without asking

    monkeypatch.setattr(passwords, "ask_keep_protection", lambda parent: False)
    dialogs.save_path = tmp_path / "plain.pdf"
    tab._save_as()
    assert page_widths(dialogs.save_path) == [101, 102]  # readable without any password


def _fresh_copy(path, tmp_path):
    # A copy at a new path has no remembered password, like the file seen by someone else.
    copy = tmp_path / "copy.pdf"
    copy.write_bytes(path.read_bytes())
    return copy


def test_batch_never_asks_and_reports_protected_files(tmp_path):
    secret = make_pdf(tmp_path / "secret.pdf", [101], password="tajne")
    out = tmp_path / "out"
    out.mkdir()

    [result] = run_batch([secret], out, rotate_operation("", 90))

    assert result.status is Status.FAILED and "heslom" in result.message


def test_batch_does_not_use_a_password_remembered_by_another_tab(tmp_path):
    secret = make_pdf(tmp_path / "secret.pdf", [101], password="tajne")
    assert unlock(secret, "tajne")
    out = tmp_path / "out"
    out.mkdir()
    [result] = run_batch([secret], out, rotate_operation("", 90))
    assert result.status is Status.FAILED and "heslom" in result.message
    assert list(out.iterdir()) == []
    assert page_count(secret) == 1  # rejecting the batch does not clear the interactive session's password


def test_batch_rechecks_password_policy_if_source_changes_after_counting(tmp_path, monkeypatch):
    from pdftool import batch
    source = make_pdf(tmp_path / "source.pdf", [101], password="tajne")
    assert unlock(source, "tajne")
    protected = source.read_bytes()
    make_pdf(source, [101])
    original_open = batch.open_pdf
    def replace_after_count(path, **kwargs):
        reader = original_open(path, **kwargs)
        source.write_bytes(protected)
        return reader
    monkeypatch.setattr(batch, "open_pdf", replace_after_count)
    out = tmp_path / "out"
    out.mkdir()
    [result] = run_batch([source], out, rotate_operation("", 90))
    assert result.status is Status.FAILED and list(out.iterdir()) == []
