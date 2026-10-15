"""Dialog for choosing which pages of another PDF to insert, and where."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.widgets import set_invalid
from pdftool.page_ranges import PageRangeError, parse_page_ranges
from pdftool.plural import format_page_count


class InsertDialog(QDialog):
    """Asks for the pages to take from `source_path`, and whether they go before or after the selection.

    Without a selection in the document the pages are appended at its end, so
    the position choice is hidden.
    """

    def __init__(
        self, source_path: Path, page_count: int, has_selection: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vložiť strany z iného PDF")
        self.setMinimumWidth(440)
        self._page_count = page_count

        title = QLabel(f"{source_path.name}  ·  {format_page_count(page_count)}")
        title.setObjectName("fileTitle")
        title.setToolTip(str(source_path))
        self._ranges_edit = QLineEdit()
        self._ranges_edit.setPlaceholderText("napr. 1-3, 5, 8-  (prázdne = všetky strany)")

        self._after_radio = QRadioButton("Za vybrané strany")
        self._after_radio.setChecked(True)
        self._before_radio = QRadioButton("Pred vybrané strany")
        end_hint = QLabel("Strany sa vložia na koniec dokumentu.")
        end_hint.setObjectName("hint")
        for widget in (self._after_radio, self._before_radio):
            widget.setVisible(has_selection)
        end_hint.setVisible(not has_selection)

        self._summary = QLabel()
        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._insert_button = self._buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._insert_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Strany na vloženie:"))
        layout.addWidget(self._ranges_edit)
        layout.addSpacing(8)
        layout.addWidget(self._after_radio)
        layout.addWidget(self._before_radio)
        layout.addWidget(end_hint)
        layout.addSpacing(8)
        layout.addWidget(self._summary)
        layout.addWidget(self._error)
        layout.addWidget(self._buttons)

        self._ranges_edit.textChanged.connect(self._update_state)
        self._update_state()

    def pages(self) -> list[int]:
        """The 0-based indices of the pages to insert, in order; raises PageRangeError if invalid."""
        return parse_page_ranges(self._ranges_edit.text(), self._page_count)

    def insert_before(self) -> bool:
        return self._before_radio.isChecked()

    def _update_state(self) -> None:
        pages: list[int] = []
        error = ""
        try:
            pages = self.pages()
        except PageRangeError as exc:
            error = str(exc)

        set_invalid(self._ranges_edit, bool(error))
        self._insert_button.setEnabled(not error)
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._summary.setText("" if error else f"Vloží sa {format_page_count(len(pages))}.")
        self._summary.setVisible(not error)
