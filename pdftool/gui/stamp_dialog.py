"""Dialog for page numbers and text stamps, with a preview of the first stamped page."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.stamp_layer import draw_stamp, render_preview
from pdftool.gui.thumbnails import open_document
from pdftool.gui.widgets import set_invalid
from pdftool.operations import PageRef
from pdftool.page_ranges import PageRangeError, format_page_ranges, parse_page_ranges
from pdftool.plural import format_page_count
from pdftool.stamps import Position, StampSpec, stamp_texts

_TEMPLATES = ("{n} / {total}", "Strana {n} z {total}", "{n}", "KÓPIA", "{date}")
_POSITIONS = (
    (Position.BOTTOM_CENTER, "Dole v strede"),
    (Position.BOTTOM_RIGHT, "Dole vpravo"),
    (Position.BOTTOM_LEFT, "Dole vľavo"),
    (Position.TOP_CENTER, "Hore v strede"),
    (Position.TOP_RIGHT, "Hore vpravo"),
    (Position.TOP_LEFT, "Hore vľavo"),
    (Position.CENTER, "V strede strany"),
)
# Portrait-shaped, as most pages are; large enough to read a page number.
_PREVIEW_WIDTH, _PREVIEW_HEIGHT = 360, 500


class StampDialog(QDialog):
    def __init__(self, pages: Sequence[PageRef], selected_rows: list[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Číslovanie strán a pečiatka")
        self._pages = list(pages)
        self._preview_document: QPdfDocument | None = None
        self._preview_path = None

        self._template_combo = QComboBox()
        self._template_combo.setEditable(True)
        self._template_combo.addItems(_TEMPLATES)
        template_hint = QLabel("{n} = číslo strany, {total} = posledné číslo, {date} = dnešný dátum")
        template_hint.setObjectName("hint")
        self._first_number_spin = QSpinBox()
        self._first_number_spin.setRange(0, 99999)
        self._first_number_spin.setValue(1)
        self._position_combo = QComboBox()
        for position, label in _POSITIONS:
            self._position_combo.addItem(label, position)
        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 96)
        self._size_spin.setValue(11)
        self._size_spin.setSuffix(" bodov")
        self._ranges_edit = QLineEdit(format_page_ranges(selected_rows))
        self._ranges_edit.setPlaceholderText("všetky strany, alebo napr. 2-10")

        form = QFormLayout()
        form.addRow("Text:", self._template_combo)
        form.addRow("", template_hint)
        form.addRow("Prvé číslo:", self._first_number_spin)
        form.addRow("Poloha:", self._position_combo)
        form.addRow("Veľkosť písma:", self._size_spin)
        form.addRow("Strany:", self._ranges_edit)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)
        save_hint = QLabel("Text sa zapíše do nového súboru; zdrojové súbory sa nezmenia.")
        save_hint.setObjectName("hint")
        save_hint.setWordWrap(True)

        self._preview = QLabel()
        self._preview.setFixedSize(_PREVIEW_WIDTH, _PREVIEW_HEIGHT)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet("background: #9ca3af;")

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = self._buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        settings_column = QVBoxLayout()
        settings_column.addLayout(form)
        settings_column.addWidget(self._summary)
        settings_column.addWidget(self._error)
        settings_column.addStretch()
        settings_column.addWidget(save_hint)
        columns = QHBoxLayout()
        columns.addLayout(settings_column, stretch=1)
        columns.addWidget(self._preview)
        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(self._buttons)

        self._template_combo.editTextChanged.connect(self._update_state)
        for spin in (self._first_number_spin, self._size_spin):
            spin.valueChanged.connect(self._update_state)
        self._position_combo.currentIndexChanged.connect(self._update_state)
        self._ranges_edit.textChanged.connect(self._update_state)
        self._update_state()

    def spec(self) -> StampSpec:
        return StampSpec(
            template=self._template_combo.currentText(),
            position=self._position_combo.currentData(),
            font_size=self._size_spin.value(),
            first_number=self._first_number_spin.value(),
        )

    def stamped_rows(self) -> list[int]:
        """0-based positions of the pages to stamp, ascending; raises PageRangeError if invalid."""
        return sorted(set(parse_page_ranges(self._ranges_edit.text(), len(self._pages))))

    def done(self, result: int) -> None:
        if self._preview_document is not None:
            self._preview_document.close()
        super().done(result)

    def _update_state(self) -> None:
        rows: list[int] = []
        error = "" if self._template_combo.currentText().strip() else "Zadajte text."
        try:
            rows = self.stamped_rows()
        except PageRangeError as exc:
            error = error or str(exc)
            set_invalid(self._ranges_edit, True)
        else:
            set_invalid(self._ranges_edit, False)

        self._accept_button.setEnabled(not error)
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._summary.setText("" if error else f"Text sa zapíše na {format_page_count(len(rows))}.")
        self._summary.setVisible(not error)
        if rows and not error:
            self._show_preview(rows[0], stamp_texts(self.spec(), len(rows))[0])
        else:
            self._preview.setPixmap(QPixmap())

    def _show_preview(self, row: int, text: str) -> None:
        page = self._pages[row]
        if self._preview_path != page.path:
            if self._preview_document is not None:
                self._preview_document.close()
            self._preview_document = open_document(page.path, self)
            self._preview_path = page.path
        if self._preview_document is None:
            self._preview.setText("Náhľad nie je k dispozícii.")
            return
        spec = self.spec()
        self._preview.setPixmap(
            render_preview(
                self._preview_document,
                page,
                QSize(_PREVIEW_WIDTH - 8, _PREVIEW_HEIGHT - 8),
                lambda painter, size: draw_stamp(painter, size, text, spec),
            )
        )
