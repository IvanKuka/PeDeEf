"""Small widgets and helpers shared by the application tabs."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

PDF_FILE_FILTER = "PDF súbory (*.pdf)"

# Qt maps "Ctrl" in shortcuts to the Command key on macOS; texts shown to the user must match.
MULTI_SELECT_KEY = "⌘" if sys.platform == "darwin" else "Ctrl"


def native_shortcut_text(shortcut: str) -> str:
    """Render a shortcut such as "Ctrl+L" the way the platform shows it (e.g. "⌘L" on macOS)."""
    return QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)


class PageCanvas(QLabel):
    """A page preview to point at: positions are reported as fractions of the page shown."""

    def __init__(self, width: int, height: int) -> None:
        super().__init__()
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #9ca3af;")

    def page_fraction(self, position: QPointF) -> QPointF | None:
        """`position` in the widget as fractions of the page (may lie outside 0–1), or None without a page."""
        pixmap = self.pixmap()
        if pixmap.isNull():
            return None
        page = pixmap.deviceIndependentSize()
        # The page is centred in the label (see setAlignment).
        left = (self.width() - page.width()) / 2
        top = (self.height() - page.height()) / 2
        return QPointF((position.x() - left) / page.width(), (position.y() - top) / page.height())


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


@contextmanager
def progress_dialog(
    parent: QWidget, title: str, label: str, maximum: int, *, minimum_duration: int = 400
) -> Iterator[Callable[[int], bool]]:
    """Show a cancellable progress dialog; yields `report(done) -> bool` (False once cancelled).

    The dialog appears only if the work takes a moment, so short jobs show nothing.
    """
    dialog = QProgressDialog(label, "Zrušiť", 0, maximum, parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumDuration(minimum_duration)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)
    if minimum_duration == 0:
        dialog.show()

    def report(done: int) -> bool:
        if dialog.wasCanceled():
            return False
        dialog.setValue(done)
        # OCR can report the same page repeatedly while its child process runs.
        # Qt's setValue() skips event processing when the value has not changed.
        QApplication.processEvents()
        return not dialog.wasCanceled()

    try:
        yield report
    finally:
        dialog.close()
        dialog.deleteLater()


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
    """Show a success message offering to open the created file (or its folder) or folder."""
    box = QMessageBox(QMessageBox.Icon.Information, "Hotovo", message, parent=parent)
    open_button = box.addButton("Otvoriť", QMessageBox.ButtonRole.AcceptRole)
    folder_button = None
    if not open_target.is_dir():
        folder_button = box.addButton("Zobraziť priečinok", QMessageBox.ButtonRole.ActionRole)
    box.addButton("Zavrieť", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is open_button:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(open_target)))
    elif folder_button is not None and box.clickedButton() is folder_button:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(open_target.parent)))
