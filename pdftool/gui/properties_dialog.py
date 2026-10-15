"""Dialog showing a document's metadata and setting what the saved file will contain."""

from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.operations import DocumentInfo, SourceProperties

_FIELDS = (("title", "Názov:"), ("author", "Autor:"), ("subject", "Predmet:"), ("keywords", "Kľúčové slová:"))
_OTHER_LABELS = {
    "Creator": "Vytvorené v programe:",
    "Producer": "PDF vytvoril:",
    "CreationDate": "Vytvorené:",
    "ModDate": "Zmenené:",
}
_PDF_DATE = re.compile(r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?")


def format_pdf_date(value: str) -> str:
    """'D:20240315093000+01'00'' -> '15. 03. 2024 09:30'; other values are returned unchanged."""
    match = _PDF_DATE.match(value)
    if not match:
        return value
    year, month, day, hour, minute = match.groups()
    text = f"{day or '01'}. {month or '01'}. {year}"
    return f"{text} {hour}:{minute or '00'}" if hour else text


class PropertiesDialog(QDialog):
    def __init__(
        self,
        file_name: str,
        source: SourceProperties,
        current: DocumentInfo | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vlastnosti dokumentu")
        self.setMinimumWidth(520)

        original_box = QGroupBox(f"Pôvodný súbor: {file_name}")
        original = QFormLayout(original_box)
        for field_name, label in _FIELDS:
            original.addRow(label, self._value_label(getattr(source.info, field_name)))
        for key, value in source.other.items():
            label = _OTHER_LABELS.get(key, f"{key}:")
            original.addRow(label, self._value_label(format_pdf_date(value) if key.endswith("Date") else value))
        if source.has_xmp:
            original.addRow(QLabel("Obsahuje aj rozšírené metadáta (XMP)."))

        target_box = QGroupBox("Uložený súbor bude obsahovať")
        target = QFormLayout(target_box)
        values = current or source.info
        self._edits: dict[str, QLineEdit] = {}
        for field_name, label in _FIELDS:
            edit = QLineEdit(getattr(values, field_name))
            edit.setPlaceholderText("nevyplnené – neuloží sa")
            target.addRow(label, edit)
            self._edits[field_name] = edit
        clear_button = QPushButton("Vymazať všetko")
        clear_button.clicked.connect(lambda: [edit.clear() for edit in self._edits.values()])
        target.addRow("", clear_button)

        scope = QLabel(
            "Do uloženého súboru sa zapíšu iba tieto údaje a označenie programu (pypdf). Ostatné pôvodné "
            "metadáta vrátane XMP sa neprenášajú.\n"
            "Nekontroluje sa obsah strán, komentáre ani polia formulárov – aj tie môžu obsahovať osobné údaje."
        )
        scope.setObjectName("hint")
        scope.setWordWrap(True)

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        apply_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        apply_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(original_box)
        layout.addWidget(target_box)
        layout.addWidget(scope)
        layout.addWidget(buttons)

    def info(self) -> DocumentInfo:
        return DocumentInfo(**{name: edit.text().strip() for name, edit in self._edits.items()})

    @staticmethod
    def _value_label(value: str) -> QLabel:
        label = QLabel(value or "–")
        label.setWordWrap(True)
        label.setTextInteractionFlags(label.textInteractionFlags() | label.textInteractionFlags().TextSelectableByMouse)
        return label
