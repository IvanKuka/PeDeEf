"""Tab for merging several PDF files (optionally only selected pages) into one."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.thumbnails import placeholder_image, render_first_page, thumbnail_icon
from pdftool.gui.widgets import (
    PDF_FILE_FILTER,
    PdfDropListWidget,
    ask_save_pdf_path,
    busy_cursor,
    report_success,
    set_invalid,
)
from pdftool.operations import PageSelection, PdfToolError, page_count, write_pdf
from pdftool.page_ranges import PageRangeError, parse_page_ranges
from pdftool.plural import format_page_count

_ENTRY_ROLE = Qt.ItemDataRole.UserRole
_THUMBNAIL_SIDE = 64


@dataclass(frozen=True)
class MergeEntry:
    path: Path
    page_count: int
    # User-entered page range, e.g. "1-3, 5"; empty means all pages.
    range_spec: str = ""

    def selected_pages(self) -> list[int]:
        return parse_page_ranges(self.range_spec, self.page_count)


class MergeTab(QWidget):
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_dir = Path.home()

        self._list = PdfDropListWidget("Pretiahnite sem PDF súbory\nalebo kliknite na „Pridať súbory…“")
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setIconSize(QSize(_THUMBNAIL_SIDE, _THUMBNAIL_SIDE))
        self._list.setSpacing(2)
        self._list.files_dropped.connect(self.add_files)
        self._list.currentItemChanged.connect(self._on_current_item_changed)
        # rowsMoved covers drag & drop reordering, which changes the enabled state of Up/Down.
        self._list.model().rowsMoved.connect(self._update_buttons)

        self._add_button = QPushButton("Pridať súbory…")
        self._add_button.clicked.connect(self._choose_files)
        self._up_button = QPushButton("▲  Posunúť hore")
        self._up_button.clicked.connect(lambda: self._move_current(-1))
        self._down_button = QPushButton("▼  Posunúť dole")
        self._down_button.clicked.connect(lambda: self._move_current(1))
        self._remove_button = QPushButton("Odstrániť")
        self._remove_button.clicked.connect(self._remove_current)
        self._clear_button = QPushButton("Odstrániť všetko")
        self._clear_button.clicked.connect(self._clear)

        self._range_edit = QLineEdit()
        self._range_edit.setPlaceholderText("všetky strany")
        self._range_edit.textEdited.connect(self._on_range_edited)
        range_hint = QLabel("Napr. 1-3, 5, 8-\nPrázdne pole = všetky strany.")
        range_hint.setObjectName("hint")
        self._range_error = QLabel()
        self._range_error.setObjectName("error")
        self._range_error.setWordWrap(True)

        range_box = QGroupBox("Strany z vybraného súboru")
        range_layout = QVBoxLayout(range_box)
        range_layout.addWidget(self._range_edit)
        range_layout.addWidget(range_hint)
        range_layout.addWidget(self._range_error)

        self._merge_button = QPushButton("Zlúčiť a uložiť…")
        self._merge_button.setObjectName("primary")
        self._merge_button.clicked.connect(self._merge)

        side_panel = QVBoxLayout()
        side_panel.addWidget(self._add_button)
        side_panel.addSpacing(8)
        side_panel.addWidget(self._up_button)
        side_panel.addWidget(self._down_button)
        side_panel.addWidget(self._remove_button)
        side_panel.addWidget(self._clear_button)
        side_panel.addWidget(range_box)
        side_panel.addStretch()
        side_panel.addWidget(self._merge_button)

        hint = QLabel("Poradie súborov zmeníte pretiahnutím myšou alebo tlačidlami vpravo.")
        hint.setObjectName("hint")
        list_column = QVBoxLayout()
        list_column.addWidget(self._list)
        list_column.addWidget(hint)

        layout = QHBoxLayout(self)
        layout.addLayout(list_column, stretch=1)
        layout.addLayout(side_panel)

        self._update_buttons()

    def add_files(self, paths: Iterable[Path | str]) -> None:
        added = 0
        errors: list[str] = []
        with busy_cursor():
            for path in map(Path, paths):
                try:
                    count = page_count(path)
                except PdfToolError as exc:
                    errors.append(str(exc))
                    continue
                self._list.addItem(self._create_item(MergeEntry(path, count)))
                self._last_dir = path.parent
                added += 1

        if added:
            self._list.setCurrentRow(self._list.count() - 1)
            self.status_message.emit(f"Pridané súbory: {added}")
        if errors:
            QMessageBox.warning(self, "Niektoré súbory neboli pridané", "\n\n".join(errors))
        self._update_buttons()

    def _create_item(self, entry: MergeEntry) -> QListWidgetItem:
        image = render_first_page(entry.path, _THUMBNAIL_SIDE) or placeholder_image(_THUMBNAIL_SIDE)
        item = QListWidgetItem(thumbnail_icon(image, _THUMBNAIL_SIDE), "")
        item.setToolTip(str(entry.path))
        self._set_entry(item, entry)
        return item

    @staticmethod
    def _entry(item: QListWidgetItem) -> MergeEntry:
        return item.data(_ENTRY_ROLE)

    @staticmethod
    def _set_entry(item: QListWidgetItem, entry: MergeEntry) -> None:
        item.setData(_ENTRY_ROLE, entry)
        pages = f"strany {entry.range_spec}" if entry.range_spec.strip() else "všetky strany"
        item.setText(f"{entry.path.name}\n{format_page_count(entry.page_count)}  ·  {pages}")

    def _choose_files(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Vyberte PDF súbory", str(self._last_dir), PDF_FILE_FILTER
        )
        if file_names:
            self.add_files(file_names)

    def _move_current(self, offset: int) -> None:
        row = self._list.currentRow()
        target = row + offset
        if row < 0 or not 0 <= target < self._list.count():
            return
        item = self._list.takeItem(row)
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)

    def _remove_current(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
        self._update_buttons()

    def _clear(self) -> None:
        self._list.clear()
        self._update_buttons()

    def _on_current_item_changed(self, current: QListWidgetItem | None, _previous) -> None:
        self._range_edit.setText(self._entry(current).range_spec if current else "")
        self._validate_range_input()
        self._update_buttons()

    def _on_range_edited(self, text: str) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        # The spec is stored even while invalid so the user's typing is never lost;
        # validity is enforced again before merging.
        self._set_entry(item, replace(self._entry(item), range_spec=text))
        self._validate_range_input()

    def _validate_range_input(self) -> None:
        item = self._list.currentItem()
        error = ""
        if item is not None:
            try:
                self._entry(item).selected_pages()
            except PageRangeError as exc:
                error = str(exc)
        set_invalid(self._range_edit, bool(error))
        self._range_error.setText(error)
        self._range_error.setVisible(bool(error))

    def _update_buttons(self) -> None:
        row = self._list.currentRow()
        count = self._list.count()
        has_current = row >= 0
        self._up_button.setEnabled(has_current and row > 0)
        self._down_button.setEnabled(has_current and row < count - 1)
        self._remove_button.setEnabled(has_current)
        self._clear_button.setEnabled(count > 0)
        self._range_edit.setEnabled(has_current)
        self._merge_button.setEnabled(count > 0)

    def _merge(self) -> None:
        selections = self._collect_selections()
        if selections is None:
            return
        output = ask_save_pdf_path(self, "Uložiť zlúčené PDF", self._last_dir / "zlucene.pdf")
        if output is None:
            return

        try:
            with busy_cursor():
                write_pdf(selections, output)
        except PdfToolError as exc:
            QMessageBox.critical(self, "Zlúčenie zlyhalo", str(exc))
            return

        self._last_dir = output.parent
        self.status_message.emit(f"Uložené: {output}")
        report_success(self, f"Zlúčené PDF bolo uložené:\n{output}", output)

    def _collect_selections(self) -> list[PageSelection] | None:
        """Build the merge input; on an invalid page range, select that file and return None."""
        selections = []
        for row in range(self._list.count()):
            entry = self._entry(self._list.item(row))
            try:
                pages = entry.selected_pages()
            except PageRangeError as exc:
                self._list.setCurrentRow(row)
                QMessageBox.warning(self, "Neplatný rozsah strán", f"{entry.path.name}:\n{exc}")
                return None
            selections.append(PageSelection(entry.path, pages))
        return selections
