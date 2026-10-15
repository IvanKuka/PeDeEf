"""Tab for applying one operation to many PDF files at once."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.batch import BatchResult, Operation, Status, collect_pdfs, rotate_operation, run_batch, unique_sources
from pdftool.gui.settings import Settings
from pdftool.gui.widgets import PDF_FILE_FILTER, PdfDropListWidget, set_invalid
from pdftool.page_ranges import PageRangeError, validate_page_spec
from pdftool.plural import format_file_count

_PATH_ROLE = Qt.ItemDataRole.UserRole
_ROTATIONS = (("Doprava o 90°", 90), ("Doľava o 90°", 270), ("O 180°", 180))
# Symbols rather than colours: they survive the stylesheet and do not rely on colour vision.
_STATUS_MARKS = {Status.DONE: "✓", Status.SKIPPED: "⚠", Status.FAILED: "✗", Status.CANCELLED: "–"}


class _BatchThread(QThread):
    """Runs the batch off the GUI thread; results arrive through `result_ready`, one per file."""

    result_ready = Signal(object)

    def __init__(self, sources: list[Path], output_dir: Path, operation: Operation, parent: QWidget) -> None:
        super().__init__(parent)
        self._sources = sources
        self._output_dir = output_dir
        self._operation = operation

    def run(self) -> None:
        run_batch(self._sources, self._output_dir, self._operation, self.isInterruptionRequested, self.result_ready.emit)


class BatchTab(QWidget):
    status_message = Signal(str)

    def __init__(self, settings: Settings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings or Settings()
        self._thread: _BatchThread | None = None
        self._results: list[BatchResult] = []

        self._list = PdfDropListWidget("Pretiahnite sem PDF súbory alebo priečinky\nalebo použite tlačidlá vpravo")
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.files_dropped.connect(self._on_dropped)
        self._list.itemSelectionChanged.connect(self._update_state)

        self._add_files_button = QPushButton("Pridať súbory…")
        self._add_files_button.clicked.connect(self._choose_files)
        self._add_folder_button = QPushButton("Pridať priečinok…")
        self._add_folder_button.clicked.connect(self._choose_folder)
        self._recursive_check = QCheckBox("Vrátane podpriečinkov")
        self._remove_button = QPushButton("Odstrániť zo zoznamu")
        self._remove_button.clicked.connect(self._remove_selected)
        self._clear_button = QPushButton("Odstrániť všetko")
        self._clear_button.clicked.connect(self._clear)

        self._pages_edit = QLineEdit()
        self._pages_edit.setPlaceholderText("všetky strany, alebo napr. 1 alebo 2-3")
        self._pages_edit.textChanged.connect(self._update_state)
        self._rotation_combo = QComboBox()
        for label, degrees in _ROTATIONS:
            self._rotation_combo.addItem(label, degrees)
        rotation_hint = QLabel("Súbor, ktorý niektorú zo strán nemá, sa preskočí a zostane bez zmeny.")
        rotation_hint.setObjectName("hint")
        rotation_hint.setWordWrap(True)
        operation_box = QGroupBox("Otočiť strany")
        operation_form = QFormLayout(operation_box)
        operation_form.addRow("Strany:", self._pages_edit)
        operation_form.addRow("Smer:", self._rotation_combo)
        operation_form.addRow(rotation_hint)

        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("vyberte priečinok")
        self._output_edit.textChanged.connect(self._update_state)
        output_button = QPushButton("Vybrať…")
        output_button.clicked.connect(self._choose_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_edit, stretch=1)
        output_row.addWidget(output_button)
        output_hint = QLabel("Zdrojové súbory sa nemenia. Ak súbor s rovnakým názvom už existuje, nový dostane číslo, napr. „zmluva (2).pdf“.")
        output_hint.setObjectName("hint")
        output_hint.setWordWrap(True)
        output_box = QGroupBox("Výstupný priečinok")
        output_layout = QVBoxLayout(output_box)
        output_layout.addLayout(output_row)
        output_layout.addWidget(output_hint)

        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._start_button = QPushButton("Spustiť")
        self._start_button.setObjectName("primary")
        self._start_button.clicked.connect(self._start)
        self._cancel_button = QPushButton("Zrušiť")
        self._cancel_button.setToolTip("Dokončí rozpracovaný súbor a ostatné nespracuje")
        self._cancel_button.clicked.connect(self._cancel)

        side_panel = QVBoxLayout()
        side_panel.addWidget(self._add_files_button)
        side_panel.addWidget(self._add_folder_button)
        side_panel.addWidget(self._recursive_check)
        side_panel.addWidget(self._remove_button)
        side_panel.addWidget(self._clear_button)
        side_panel.addSpacing(8)
        side_panel.addWidget(operation_box)
        side_panel.addWidget(output_box)
        side_panel.addStretch()
        side_panel.addWidget(self._error)
        side_panel.addWidget(self._progress)
        buttons = QHBoxLayout()
        buttons.addWidget(self._cancel_button)
        buttons.addWidget(self._start_button, stretch=1)
        side_panel.addLayout(buttons)

        side_widget = QWidget()
        side_widget.setLayout(side_panel)
        sidebar = QScrollArea()
        sidebar.setWidgetResizable(True)
        sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar.setFrameShape(QFrame.Shape.NoFrame)
        sidebar.setFixedWidth(360)
        sidebar.setWidget(side_widget)
        layout = QHBoxLayout(self)
        layout.addWidget(self._list, stretch=1)
        layout.addWidget(sidebar)

        self._update_state()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def stop_and_wait(self) -> None:
        """Cancel a running batch and wait until the file being written is finished."""
        if self._thread is not None:
            self._thread.requestInterruption()
            self._thread.wait()

    def add_paths(self, paths: Iterable[Path]) -> None:
        """Add PDF files, and the PDFs inside added folders, skipping files already in the list."""
        files: list[Path] = []
        for path in map(Path, paths):
            if path.is_dir():
                files.extend(collect_pdfs(path, self._recursive_check.isChecked()))
            elif path.suffix.lower() == ".pdf":
                files.append(path)
        known = self._sources()
        new = unique_sources([*known, *files])[len(known) :]
        for path in new:
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(_PATH_ROLE, path)
            self._list.addItem(item)
        if new:
            self._settings.remember_directory(new[-1])
        ignored = len(files) - len(new)
        message = f"Pridané: {format_file_count(len(new))}"
        if ignored:
            message += f" ({format_file_count(ignored)} už v zozname)"
        self.status_message.emit(message)
        self._results = []
        self._update_state()

    def _sources(self) -> list[Path]:
        return [self._list.item(row).data(_PATH_ROLE) for row in range(self._list.count())]

    def _on_dropped(self, paths: list[Path]) -> None:
        if not self.is_running():
            self.add_paths(paths)

    def _choose_files(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Vyberte PDF súbory", str(self._settings.last_directory()), PDF_FILE_FILTER
        )
        self.add_paths(Path(name) for name in file_names)

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Vyberte priečinok s PDF", str(self._settings.last_directory()))
        if folder:
            self.add_paths([Path(folder)])

    def _choose_output(self) -> None:
        start = self._output_edit.text() or str(self._settings.last_directory())
        folder = QFileDialog.getExistingDirectory(self, "Vyberte výstupný priečinok", start)
        if folder:
            self._output_edit.setText(folder)

    def _remove_selected(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self._update_state()

    def _clear(self) -> None:
        self._list.clear()
        self._update_state()

    def _pages_error(self) -> str:
        try:
            validate_page_spec(self._pages_edit.text())
        except PageRangeError as exc:
            return str(exc)
        return ""

    def _output_error(self) -> str:
        folder = self._output_edit.text().strip()
        if not folder:
            return "Vyberte výstupný priečinok."
        return "" if Path(folder).is_dir() else "Výstupný priečinok neexistuje."

    def _update_state(self) -> None:
        running = self.is_running()
        pages_error = self._pages_error()
        set_invalid(self._pages_edit, bool(pages_error))
        # Nothing to complain about while the list is still empty.
        error = (pages_error or self._output_error()) if self._list.count() else ""
        self._error.setText(error)
        self._error.setVisible(bool(error))
        for widget in (
            self._add_files_button,
            self._add_folder_button,
            self._recursive_check,
            self._pages_edit,
            self._rotation_combo,
            self._output_edit,
            self._clear_button,
        ):
            widget.setEnabled(not running)
        self._remove_button.setEnabled(not running and bool(self._list.selectedItems()))
        self._start_button.setEnabled(not running and self._list.count() > 0 and not error)
        self._cancel_button.setEnabled(running)

    def _start(self) -> None:
        sources = self._sources()
        output_dir = Path(self._output_edit.text().strip())
        operation = rotate_operation(self._pages_edit.text(), self._rotation_combo.currentData())
        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setText(item.data(_PATH_ROLE).name)
        self._results = []
        self._progress.setRange(0, len(sources))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._settings.remember_directory(output_dir)

        self._thread = _BatchThread(sources, output_dir, operation, self)
        self._thread.result_ready.connect(self._on_result)
        self._thread.finished.connect(self._on_finished)
        self._thread.start()
        self.status_message.emit(f"Spracúva sa {format_file_count(len(sources))}…")
        self._update_state()

    def _cancel(self) -> None:
        if self._thread is not None:
            self._thread.requestInterruption()
            self.status_message.emit("Dávka sa ruší – rozpracovaný súbor sa ešte dokončí…")

    def _on_result(self, result: BatchResult) -> None:
        item = self._list.item(len(self._results))
        self._results.append(result)
        item.setText(f"{_STATUS_MARKS[result.status]}  {result.source.name}  —  {result.message}")
        self._progress.setValue(len(self._results))

    def _on_finished(self) -> None:
        self._thread = None
        counts = Counter(result.status for result in self._results)
        parts = [f"hotovo: {counts[Status.DONE]}"]
        if counts[Status.SKIPPED]:
            parts.append(f"preskočené: {counts[Status.SKIPPED]}")
        if counts[Status.FAILED]:
            parts.append(f"chyby: {counts[Status.FAILED]}")
        if counts[Status.CANCELLED]:
            parts.append(f"nespracované: {counts[Status.CANCELLED]}")
        summary = "Dávka skončila – " + ", ".join(parts)
        self.status_message.emit(summary)
        self._update_state()
        if counts[Status.FAILED] or counts[Status.SKIPPED]:
            QMessageBox.information(
                self, "Dávka skončila", f"{summary}.\n\nPri nespracovaných súboroch je dôvod uvedený v zozname."
            )
