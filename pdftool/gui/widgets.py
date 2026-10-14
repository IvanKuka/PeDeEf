"""Small widgets and helpers shared by the application tabs."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QPainter
from PySide6.QtWidgets import QApplication, QFileDialog, QListWidget, QMessageBox, QWidget

PDF_FILE_FILTER = "PDF súbory (*.pdf)"

# Qt maps "Ctrl" in shortcuts to the Command key on macOS; texts shown to the user must match.
MULTI_SELECT_KEY = "⌘" if sys.platform == "darwin" else "Ctrl"


def native_shortcut_text(shortcut: str) -> str:
    """Render a shortcut such as "Ctrl+L" the way the platform shows it (e.g. "⌘L" on macOS)."""
    return QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)


class PdfDropListWidget(QListWidget):
    """List widget that accepts files dragged from Explorer and shows a hint while empty.

    Drops carrying file URLs are reported through `files_dropped`; any other
    drop (internal reordering) keeps the default QListWidget behaviour.
    """

    files_dropped = Signal(list)

    def __init__(self, empty_hint: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._empty_hint = empty_hint
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return
        event.acceptProposedAction()
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.count():
            return
        painter = QPainter(self.viewport())
        painter.setPen(QColor("#9ca3af"))
        painter.drawText(
            self.viewport().rect().adjusted(24, 24, -24, -24),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self._empty_hint,
        )


def set_invalid(widget: QWidget, invalid: bool) -> None:
    """Toggle the `invalid` style (red border, see style.py) on an input widget."""
    if widget.property("invalid") == invalid:
        return
    widget.setProperty("invalid", invalid)
    # Qt does not re-evaluate property selectors automatically.
    widget.style().unpolish(widget)
    widget.style().polish(widget)


@contextmanager
def busy_cursor() -> Iterator[None]:
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def ask_save_pdf_path(parent: QWidget, title: str, suggested: Path) -> Path | None:
    """Ask for an output PDF path; returns None when cancelled. Always ends in .pdf."""
    file_name, _ = QFileDialog.getSaveFileName(parent, title, str(suggested), PDF_FILE_FILTER)
    if not file_name:
        return None
    path = Path(file_name)
    return path if path.suffix.lower() == ".pdf" else path.with_name(path.name + ".pdf")


def confirm(parent: QWidget, title: str, text: str, confirm_label: str) -> bool:
    """Ask a yes/cancel question with explicit Slovak button labels.

    Qt's bundled Slovak translation does not cover the standard dialog buttons,
    so the labels are set here instead of using QMessageBox.StandardButton.
    """
    box = QMessageBox(QMessageBox.Icon.Question, title, text, parent=parent)
    confirm_button = box.addButton(confirm_label, QMessageBox.ButtonRole.AcceptRole)
    cancel_button = box.addButton("Zrušiť", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel_button)
    box.exec()
    return box.clickedButton() is confirm_button


def report_success(parent: QWidget, message: str, open_target: Path) -> None:
    """Show a success message offering to open the created file or folder."""
    box = QMessageBox(QMessageBox.Icon.Information, "Hotovo", message, parent=parent)
    open_button = box.addButton("Otvoriť", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Zavrieť", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is open_button:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(open_target)))
