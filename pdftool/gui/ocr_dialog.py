"""Dialog for text recognition (OCR): the language and what will be recognised."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from pdftool.ocr import language_name
from pdftool.plural import format_page_count_locative
from pdftool.page_ranges import PageRangeError, format_page_ranges, parse_page_ranges
from pdftool.gui.widgets import set_invalid

# Preferred in this order when installed: the application is made for Slovak documents.
_DEFAULT_LANGUAGES = ("slk", "ces", "eng")


class OcrDialog(QDialog):
    def __init__(
        self, languages: Sequence[str], scanned_rows: Sequence[int], page_count: int, parent: QWidget | None = None,
        *, selected_rows: Sequence[int] = (),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rozpoznať text (OCR)")
        self.setMinimumWidth(480)
        self._scanned_rows = set(scanned_rows)
        self._page_count = page_count

        self._language_combo = QComboBox()
        for code in languages:
            self._language_combo.addItem(language_name(code), code)
        default = next((code for code in _DEFAULT_LANGUAGES if code in languages), None)
        if default is not None:
            self._language_combo.setCurrentIndex(languages.index(default))
        form = QFormLayout()
        form.addRow("Jazyk dokumentu:", self._language_combo)
        self._ranges_edit = QLineEdit(format_page_ranges(list(selected_rows)))
        self._ranges_edit.setPlaceholderText("Všetky strany, alebo napr. 1-3, 5")
        form.addRow("Strany:", self._ranges_edit)

        self._scope = QLabel()
        self._scope.setWordWrap(True)
        self._error = QLabel()
        self._error.setWordWrap(True)
        self._error.setObjectName("error")
        notes = QLabel(
            "Vzhľad strán sa nezmení – pod obraz sa vloží neviditeľný text, ktorý sa dá vyhľadať a kopírovať. "
            "Rozpoznávanie nie je bezchybné, najmä pri zlých skenoch. Strany otočené nabok najprv otočte "
            "v náhľade. Veľmi veľké strany sa rozpoznajú v menšom rozlíšení, aby sa nezaplnila pamäť. "
            "Spracovanie možno zrušiť bez uloženia výsledku."
        )
        notes.setObjectName("hint")
        notes.setWordWrap(True)

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._scope)
        layout.addWidget(self._error)
        layout.addWidget(notes)
        layout.addWidget(buttons)
        self._ranges_edit.textChanged.connect(self._update_state)
        self._language_combo.currentIndexChanged.connect(self._update_state)
        self._update_state()

    def language(self) -> str:
        return self._language_combo.currentData()

    def recognition_rows(self) -> list[int]:
        selected = set(parse_page_ranges(self._ranges_edit.text(), self._page_count))
        return sorted(selected & self._scanned_rows)

    def _update_state(self) -> None:
        error = ""
        rows = []
        try:
            rows = self.recognition_rows()
        except PageRangeError as exc:
            error = str(exc)
        set_invalid(self._ranges_edit, bool(error))
        if not error and not rows:
            error = "Vo vybranom rozsahu nie sú žiadne strany bez textu."
        if not self._language_combo.count():
            error = "Nie je nainštalovaný žiadny jazyk OCR. Doplňte jazykové dáta Tesseractu."
        self._accept_button.setEnabled(not error)
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._scope.setText(
            f"Text sa rozpozná na {format_page_count_locative(len(rows))} bez textu (z {self._page_count}). "
            "Strany, ktoré text už majú, sa preskočia, aby sa text nezdvojil."
        )
