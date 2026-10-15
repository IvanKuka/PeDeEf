"""Asking for passwords: to open a protected PDF, and for protecting a new one."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.operations import PasswordRequired, PdfToolError, page_count, password_for, unlock


def page_count_unlocking(parent: QWidget, path: Path) -> int:
    """`page_count(path)`, asking for the password of a protected file until it is right.

    Raises PdfToolError for unreadable files and when the user gives up.
    """
    path = Path(path)
    wrong = False
    while True:
        try:
            return page_count(path)
        except PasswordRequired:
            password = ask_open_password(parent, path, wrong)
            if password is None:
                raise PdfToolError(f"Súbor „{path.name}“ sa neotvoril – heslo nebolo zadané.") from None
            wrong = not unlock(path, password)


def output_password(parent: QWidget, sources: Iterable[Path], always: bool = False) -> tuple[bool, str | None]:
    """Decide how a new file made from `sources` is protected: (go on?, password or None).

    A document that needed a password is never saved unprotected without asking;
    with `always`, the user is asked for a password regardless.
    """
    protected = any(password_for(path) for path in set(sources))
    if not protected and not always:
        return True, None
    if protected and not always:
        choice = ask_keep_protection(parent)
        if choice is None:
            return False, None
        if not choice:
            return True, None
    dialog = NewPasswordDialog(parent, "Pôvodný dokument je chránený heslom." if protected else "")
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False, None
    return True, dialog.password()


def ask_keep_protection(parent: QWidget) -> bool | None:
    """True: protect the new file too, False: save it without a password, None: cancel."""
    box = QMessageBox(
        QMessageBox.Icon.Question,
        "Dokument je chránený heslom",
        "Pôvodný dokument je chránený heslom. Má mať heslo aj nový súbor?",
        parent=parent,
    )
    with_password = box.addButton("S heslom…", QMessageBox.ButtonRole.AcceptRole)
    without_password = box.addButton("Bez hesla", QMessageBox.ButtonRole.DestructiveRole)
    box.addButton("Zrušiť", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(with_password)
    box.exec()
    if box.clickedButton() is with_password:
        return True
    if box.clickedButton() is without_password:
        return False
    return None


def ask_open_password(parent: QWidget, path: Path, wrong: bool) -> str | None:
    """Ask for the password that opens `path`; None when the user cancels."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle("PDF chránené heslom")
    prompt = f"Súbor „{path.name}“ je chránený heslom.\nZadajte heslo na otvorenie:"
    dialog.setLabelText(("Nesprávne heslo, skúste to znova.\n\n" if wrong else "") + prompt)
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    # Qt's bundled Slovak translation does not cover the standard buttons (see widgets.confirm).
    dialog.setOkButtonText("Otvoriť")
    dialog.setCancelButtonText("Zrušiť")
    return dialog.textValue() if dialog.exec() == QDialog.DialogCode.Accepted else None


class NewPasswordDialog(QDialog):
    """Asks twice for the password that will protect a new PDF."""

    def __init__(self, parent: QWidget | None = None, reason: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Uložiť s heslom")
        self.setMinimumWidth(420)
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._repeat_edit = QLineEdit()
        self._repeat_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form = QFormLayout()
        form.addRow("Heslo:", self._password_edit)
        form.addRow("Zopakujte heslo:", self._repeat_edit)

        hint = QLabel(
            (reason + "\n\n" if reason else "")
            + "Bez hesla sa súbor neotvorí a heslo nie je možné obnoviť – uschovajte si ho."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._ok_button = self._buttons.addButton("Pokračovať", QDialogButtonBox.ButtonRole.AcceptRole)
        self._ok_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(self._buttons)
        for edit in (self._password_edit, self._repeat_edit):
            edit.textChanged.connect(self._update_state)
        self._update_state()

    def password(self) -> str:
        return self._password_edit.text()

    def _update_state(self) -> None:
        password, repeated = self._password_edit.text(), self._repeat_edit.text()
        mismatch = bool(repeated) and password != repeated
        self._error.setText("Heslá sa nezhodujú." if mismatch else "")
        self._error.setVisible(mismatch)
        self._ok_button.setEnabled(bool(password) and password == repeated)
