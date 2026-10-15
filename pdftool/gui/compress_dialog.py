"""Dialog for choosing how much to shrink a document."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QRadioButton, QVBoxLayout, QWidget

from pdftool.gui.images import jpeg_recompressor
from pdftool.operations import ImageRecompressor

# (label, explanation, (longest side in pixels, JPEG quality) or None for lossless only).
# The pixel limits correspond to about 150 and 100 dpi on an A4 page.
PROFILES = (
    ("Bez straty kvality", "Iba bezstratové úpravy. Na skenoch a fotkách zvyčajne ušetrí málo.", None),
    (
        "Menšie obrázky – na e-mail",
        "Obrázky a skeny približne na 150 dpi. Text zostáva ostrý, fotky mierne stratia na kvalite.",
        (1754, 75),
    ),
    (
        "Najmenší súbor",
        "Obrázky približne na 100 dpi s vyššou kompresiou. Drobné písmo v skenoch môže byť horšie čitateľné.",
        (1170, 60),
    ),
)


class CompressDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Zmenšiť veľkosť")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        self._radios: list[QRadioButton] = []
        for label, explanation, _ in PROFILES:
            radio = QRadioButton(label)
            hint = QLabel(explanation)
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            hint.setContentsMargins(24, 0, 0, 6)
            layout.addWidget(radio)
            layout.addWidget(hint)
            self._radios.append(radio)
        self._radios[1].setChecked(True)

        note = QLabel(
            "Úprava sa použije v rozpracovanom dokumente. Uložíte ho až na konci. Text sa nikdy nemení na obrázok. "
            "Upravujú sa len bežné obrázky JPEG, ostatné zostanú bez zmeny."
        )
        note.setWordWrap(True)
        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        accept = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        accept.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(8)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def recompressor(self) -> ImageRecompressor | None:
        settings = next(profile for radio, profile in zip(self._radios, PROFILES, strict=True) if radio.isChecked())[2]
        return None if settings is None else jpeg_recompressor(*settings)
