"""Shared fixtures for the GUI tests, which run on Qt's offscreen platform."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# The offscreen platform has no fonts of its own; without the system's, text is drawn as
# empty boxes and tests cannot check what was written (e.g. page numbers with diacritics).
for font_dir in ("C:/Windows/Fonts", "/System/Library/Fonts", "/usr/share/fonts"):
    if Path(font_dir).is_dir():
        os.environ.setdefault("QT_QPA_FONTDIR", font_dir)
        break

import pytest
import shiboken6
from PySide6.QtWidgets import QApplication

from pdftool.gui import merge_tab, pages_tab, passwords
from pdftool.operations import forget_passwords


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
        # Only parentless windows: others, such as a combo box's popup, are owned and
        # deleted by their parent, and deleting them a second time aborts the process.
        if shiboken6.isValid(widget) and widget.parentWidget() is None:
            shiboken6.delete(widget)


@pytest.fixture(autouse=True)
def _forget_passwords():
    # Passwords typed in one test must not unlock files in another (they live for the session).
    yield
    forget_passwords()


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
            # Answers to "enter the password" prompts, in order; None means the user cancels.
            self.passwords: list[str | None] = []
            self.password_prompts: list[bool] = []

        def ask_open_password(self, parent, path, wrong):
            self.password_prompts.append(wrong)
            return self.passwords.pop(0) if self.passwords else None

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
    monkeypatch.setattr(passwords, "ask_open_password", recorder.ask_open_password)
    return recorder
