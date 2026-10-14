"""Dialog for choosing how to split a document into several files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.widgets import set_invalid
from pdftool.operations import split_output_paths
from pdftool.page_ranges import PageRangeError, chunk_pages, parse_page_groups
from pdftool.plural import format_file_count


class SplitDialog(QDialog):
    def __init__(self, source_path: Path, page_count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rozdeliť PDF")
        self.setMinimumWidth(480)
        self._source_path = source_path
        self._page_count = page_count

        self._each_page_radio = QRadioButton("Každú stranu do samostatného súboru")
        self._each_page_radio.setChecked(True)
        self._chunk_radio = QRadioButton("Po")
        self._chunk_spin = QSpinBox()
        self._chunk_spin.setRange(1, max(1, page_count))
        self._chunk_spin.setValue(min(2, page_count))
        self._ranges_radio = QRadioButton("Podľa rozsahov:")
        self._ranges_edit = QLineEdit()
        self._ranges_edit.setPlaceholderText("napr. 1-3, 4-6, 7-")
        ranges_hint = QLabel("Každá časť oddelená čiarkou bude samostatný súbor.")
        ranges_hint.setObjectName("hint")

        chunk_row = QHBoxLayout()
        chunk_row.addWidget(self._chunk_radio)
        chunk_row.addWidget(self._chunk_spin)
        chunk_row.addWidget(QLabel("stranách"))
        chunk_row.addStretch()

        mode_layout = QGridLayout()
        mode_layout.addWidget(self._each_page_radio, 0, 0, 1, 2)
        mode_layout.addLayout(chunk_row, 1, 0, 1, 2)
        mode_layout.addWidget(self._ranges_radio, 2, 0)
        mode_layout.addWidget(self._ranges_edit, 2, 1)
        mode_layout.addWidget(ranges_hint, 3, 1)

        self._folder_edit = QLineEdit(str(source_path.parent))
        browse_button = QPushButton("Vybrať…")
        browse_button.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(browse_button)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)
        rotation_hint = QLabel("Otočenia strán vykonané v náhľade sa prenesú aj do rozdelených súborov.")
        rotation_hint.setObjectName("hint")
        rotation_hint.setWordWrap(True)

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._split_button = self._buttons.addButton("Rozdeliť", QDialogButtonBox.ButtonRole.AcceptRole)
        self._split_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(mode_layout)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Uložiť do priečinka:"))
        layout.addLayout(folder_row)
        layout.addSpacing(8)
        layout.addWidget(self._summary)
        layout.addWidget(self._error)
        layout.addWidget(rotation_hint)
        layout.addWidget(self._buttons)

        for radio in (self._each_page_radio, self._chunk_radio, self._ranges_radio):
            radio.toggled.connect(self._update_state)
        self._chunk_spin.valueChanged.connect(self._update_state)
        self._ranges_edit.textChanged.connect(self._update_state)
        self._folder_edit.textChanged.connect(self._update_state)
        self._update_state()

    def page_groups(self) -> list[list[int]]:
        """The 0-based page indices of each output file; raises PageRangeError if invalid."""
        if self._chunk_radio.isChecked():
            return chunk_pages(self._page_count, self._chunk_spin.value())
        if self._ranges_radio.isChecked():
            if not self._ranges_edit.text().strip():
                raise PageRangeError("Zadajte rozsahy strán.")
            return parse_page_groups(self._ranges_edit.text(), self._page_count)
        return chunk_pages(self._page_count, 1)

    def output_dir(self) -> Path:
        return Path(self._folder_edit.text().strip())

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Vyberte priečinok", self._folder_edit.text())
        if folder:
            self._folder_edit.setText(folder)

    def _update_state(self) -> None:
        self._chunk_spin.setEnabled(self._chunk_radio.isChecked())
        self._ranges_edit.setEnabled(self._ranges_radio.isChecked())

        groups: list[list[int]] = []
        range_error = ""
        try:
            groups = self.page_groups()
        except PageRangeError as exc:
            range_error = str(exc)
        folder_error = "" if self.output_dir().is_dir() else "Zvolený priečinok neexistuje."
        error = range_error or folder_error

        set_invalid(self._ranges_edit, bool(range_error))
        set_invalid(self._folder_edit, bool(folder_error))
        self._split_button.setEnabled(not error)
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._summary.setText("" if error else self._describe_output(groups))
        self._summary.setVisible(not error)

    def _describe_output(self, groups: list[list[int]]) -> str:
        paths = split_output_paths(self._source_path, len(groups), self.output_dir())
        names = paths[0].name if len(paths) == 1 else f"{paths[0].name} … {paths[-1].name}"
        return f"Vytvorí sa {format_file_count(len(paths))}: {names}"
