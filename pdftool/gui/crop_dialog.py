"""Dialog for cropping page margins, previewed on the first selected page."""

from __future__ import annotations

from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.page_preview import PageView
from pdftool.gui.thumbnails import open_document, visible_point_size
from pdftool.operations import CropMargins, PageRef, is_valid_crop
from pdftool.plural import format_page_count

_POINTS_PER_MM = 72 / 25.4
_SIDES = (("left", "Vľavo:"), ("top", "Hore:"), ("right", "Vpravo:"), ("bottom", "Dole:"))


class CropDialog(QDialog):
    """Margins in millimetres of the previewed page; the result is kept as fractions of the page."""

    def __init__(self, page: PageRef, page_count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Orezať okraje")
        self.resize(760, 640)
        self._document: QPdfDocument | None = open_document(page.path, self)
        # Margins are entered for the page as displayed, i.e. after the pending rotation.
        size = visible_point_size(self._document, page.index, page.rotation) if self._document else None
        self._width_mm = size.width() / _POINTS_PER_MM if size else 210.0
        self._height_mm = size.height() / _POINTS_PER_MM if size else 297.0

        self._spins: list[QDoubleSpinBox] = []
        form = QFormLayout()
        current = page.crop or (0.0, 0.0, 0.0, 0.0)
        for side, ((_, label), fraction) in enumerate(zip(_SIDES, current, strict=True)):
            spin = QDoubleSpinBox()
            extent = self._width_mm if side % 2 == 0 else self._height_mm
            spin.setRange(0, extent)
            spin.setDecimals(1)
            spin.setSuffix(" mm")
            spin.setValue(fraction * extent)
            spin.valueChanged.connect(self._update_state)
            form.addRow(label, spin)
            self._spins.append(spin)
        reset_button = QPushButton("Pôvodný orez")
        reset_button.setToolTip("Zruší orez nastavený v tejto aplikácii")
        reset_button.clicked.connect(lambda: [spin.setValue(0) for spin in self._spins])
        form.addRow("", reset_button)

        scope = QLabel(
            f"Orez sa použije na {format_page_count(page_count)}. Na stranách inej veľkosti sa okraje prenesú pomerne."
        )
        scope.setWordWrap(True)
        warning = QLabel(
            "Orez obsah len skryje – v súbore zostane a dá sa obnoviť. Na odstránenie citlivých údajov nestačí."
        )
        warning.setObjectName("hint")
        warning.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)

        self._view = PageView()
        self._view.show_page(self._document, page.index, page.rotation)

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._apply_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._apply_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        settings = QVBoxLayout()
        settings.addLayout(form)
        settings.addWidget(scope)
        settings.addWidget(warning)
        settings.addWidget(self._error)
        settings.addStretch()
        columns = QHBoxLayout()
        columns.addLayout(settings)
        columns.addWidget(self._view, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(columns, stretch=1)
        layout.addWidget(buttons)
        self._update_state()

    def crop(self) -> CropMargins | None:
        """The margins as fractions of the page; None when nothing is cropped."""
        extents = (self._width_mm, self._height_mm, self._width_mm, self._height_mm)
        margins = tuple(spin.value() / extent for spin, extent in zip(self._spins, extents, strict=True))
        return None if not any(margins) else margins  # type: ignore[return-value]

    def done(self, result: int) -> None:
        if self._document is not None:
            self._document.close()
        super().done(result)

    def _update_state(self) -> None:
        crop = self.crop()
        valid = crop is None or is_valid_crop(crop)
        self._error.setText("" if valid else "Po orezaní by zo strany nezostalo takmer nič.")
        self._error.setVisible(not valid)
        self._apply_button.setEnabled(valid)
        self._view.set_crop_overlay(crop if valid else None)
