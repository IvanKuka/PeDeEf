"""Dialog for exporting selected pages as PNG images."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.images import export_output_paths
from pdftool.gui.widgets import set_invalid
from pdftool.plural import format_count

_RESOLUTIONS = ((72, "72 dpi – na obrazovku"), (150, "150 dpi – bežné použitie"), (300, "300 dpi – tlač"))
_DEFAULT_DPI = 150


class ExportDialog(QDialog):
    def __init__(
        self, name_source: Path, positions: list[int], start_dir: Path, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportovať strany ako PNG")
        self.setMinimumWidth(480)
        self._name_source = name_source
        self._positions = positions

        self._dpi_combo = QComboBox()
        for dpi, label in _RESOLUTIONS:
            self._dpi_combo.addItem(label, dpi)
        self._dpi_combo.setCurrentIndex(self._dpi_combo.findData(_DEFAULT_DPI))

        self._folder_edit = QLineEdit(str(start_dir))
        browse_button = QPushButton("Vybrať…")
        browse_button.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Rozlíšenie:", self._dpi_combo)
        form.addRow("Uložiť do priečinka:", folder_row)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")
        rotation_hint = QLabel("Otočenia strán vykonané v náhľade sa prenesú aj do obrázkov.")
        rotation_hint.setObjectName("hint")

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._export_button = self._buttons.addButton("Exportovať", QDialogButtonBox.ButtonRole.AcceptRole)
        self._export_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addSpacing(8)
        layout.addWidget(self._summary)
        layout.addWidget(self._error)
        layout.addWidget(rotation_hint)
        layout.addWidget(self._buttons)

        self._folder_edit.textChanged.connect(self._update_state)
        self._update_state()

    def dpi(self) -> int:
        return self._dpi_combo.currentData()

    def output_dir(self) -> Path:
        return Path(self._folder_edit.text().strip())

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Vyberte priečinok", self._folder_edit.text())
        if folder:
            self._folder_edit.setText(folder)

    def _update_state(self) -> None:
        folder_ok = self.output_dir().is_dir()
        set_invalid(self._folder_edit, not folder_ok)
        self._export_button.setEnabled(folder_ok)
        self._error.setText("" if folder_ok else "Zvolený priečinok neexistuje.")
        self._error.setVisible(not folder_ok)
        if folder_ok:
            paths = export_output_paths(self._name_source, self._positions, self.output_dir())
            names = paths[0].name if len(paths) == 1 else f"{paths[0].name} … {paths[-1].name}"
            count = format_count(len(paths), "obrázok", "obrázky", "obrázkov")
            self._summary.setText(f"Vytvorí sa {count}: {names}")
        self._summary.setVisible(folder_ok)
