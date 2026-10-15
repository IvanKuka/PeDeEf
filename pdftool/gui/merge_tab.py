"""Tab for merging several PDF files (optionally only selected pages) and images into one PDF."""

from __future__ import annotations

import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.images import IMAGE_FILE_FILTER, PageFormat, images_to_pdf, is_image, load_image
from pdftool.gui.passwords import output_password, page_count_unlocking
from pdftool.gui.settings import Settings
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

    @property
    def is_image(self) -> bool:
        """An image becomes a single page; it has no page range."""
        return is_image(self.path)

    def selected_pages(self) -> list[int]:
        return parse_page_ranges(self.range_spec, self.page_count)


class MergeTab(QWidget):
    status_message = Signal(str)

    def __init__(self, settings: Settings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings or Settings()

        self._list = PdfDropListWidget("Pretiahnite sem PDF súbory alebo obrázky (JPG, PNG)\nalebo kliknite na „Pridať súbory…“")
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

        self._page_format_combo = QComboBox()
        self._page_format_combo.addItem("A4 s okrajmi", PageFormat.A4)
        self._page_format_combo.addItem("Bez okrajov, podľa obrázka", PageFormat.IMAGE)
        self.apply_preferences()
        self._page_format_combo.setToolTip("Formát strany pri vložení JPG alebo PNG; možno nastaviť aj pred pridaním obrázkov.")
        image_box = QGroupBox("Obrázky")
        image_layout = QVBoxLayout(image_box)
        image_layout.addWidget(QLabel("Veľkosť strany:"))
        image_layout.addWidget(self._page_format_combo)

        range_box = QGroupBox("Strany z vybraného súboru")
        range_layout = QVBoxLayout(range_box)
        range_layout.addWidget(self._range_edit)
        range_layout.addWidget(range_hint)
        range_layout.addWidget(self._range_error)

        self._bookmarks_check = QCheckBox("Vytvoriť záložky podľa názvov súborov")
        self._bookmarks_check.setToolTip(
            "Každý zlúčený súbor dostane záložku na svojej prvej strane. Pôvodné záložky súborov sa neprenášajú."
        )
        self._bookmarks_check.setChecked(True)

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
        side_panel.addWidget(image_box)
        side_panel.addStretch()
        side_panel.addWidget(self._bookmarks_check)
        side_panel.addWidget(self._merge_button)

        hint = QLabel("Poradie súborov zmeníte pretiahnutím myšou alebo tlačidlami vpravo.")
        hint.setObjectName("hint")
        list_column = QVBoxLayout()
        list_column.addWidget(self._list)
        list_column.addWidget(hint)

        layout = QHBoxLayout(self)
        layout.addLayout(list_column, stretch=1)
        side_widget = QWidget()
        side_widget.setLayout(side_panel)
        sidebar = QScrollArea()
        sidebar.setWidgetResizable(True)
        sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar.setFrameShape(QFrame.Shape.NoFrame)
        sidebar.setMinimumWidth(320)
        sidebar.setMaximumWidth(360)
        sidebar.setWidget(side_widget)
        layout.addWidget(sidebar)

        self._update_buttons()

    def add_files(self, paths: Iterable[Path | str]) -> None:
        added = 0
        errors: list[str] = []
        with busy_cursor():
            for path in map(Path, paths):
                try:
                    count = self._check_image(path) if is_image(path) else page_count_unlocking(self, path)
                except PdfToolError as exc:
                    errors.append(str(exc))
                    continue
                self._list.addItem(self._create_item(MergeEntry(path, count)))
                self._settings.remember_directory(path)
                added += 1

        if added:
            self._list.setCurrentRow(self._list.count() - 1)
            self.status_message.emit(f"Pridané súbory: {added}")
        if errors:
            QMessageBox.warning(self, "Niektoré súbory neboli pridané", "\n\n".join(errors))
        self._update_buttons()

    @staticmethod
    def _check_image(path: Path) -> int:
        load_image(path)  # reports an unreadable image right away, not only when merging
        return 1

    def _create_item(self, entry: MergeEntry) -> QListWidgetItem:
        if entry.is_image:
            image = load_image(entry.path).scaled(
                _THUMBNAIL_SIDE * 2, _THUMBNAIL_SIDE * 2, Qt.AspectRatioMode.KeepAspectRatio
            )
        else:
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
        if entry.is_image:
            item.setText(f"{entry.path.name}\nobrázok  ·  1 strana")
            return
        pages = f"strany {entry.range_spec}" if entry.range_spec.strip() else "všetky strany"
        item.setText(f"{entry.path.name}\n{format_page_count(entry.page_count)}  ·  {pages}")

    def _choose_files(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Vyberte PDF súbory alebo obrázky",
            str(self._settings.last_directory()),
            f"PDF a obrázky (*.pdf *.jpg *.jpeg *.png);;{PDF_FILE_FILTER};;{IMAGE_FILE_FILTER}",
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
        current_is_image = has_current and self._entry(self._list.item(row)).is_image
        self._up_button.setEnabled(has_current and row > 0)
        self._down_button.setEnabled(has_current and row < count - 1)
        self._remove_button.setEnabled(has_current)
        self._clear_button.setEnabled(count > 0)
        self._range_edit.setEnabled(has_current and not current_is_image)
        self._merge_button.setEnabled(count > 0)

    def apply_preferences(self) -> None:
        self._page_format_combo.setCurrentIndex(0 if self._settings.image_format() == "a4" else 1)

    def _merge(self) -> None:
        selections = self._collect_selections()
        if selections is None:
            return
        proceed, password = output_password(self, (selection.path for selection in selections))
        if not proceed:
            return
        output = ask_save_pdf_path(self, "Uložiť zlúčené PDF", self._settings.last_directory() / "zlucene.pdf")
        if output is None:
            return

        try:
            # Images are turned into single-page PDFs first; those exist only while merging.
            with busy_cursor(), tempfile.TemporaryDirectory() as temp_dir:
                write_pdf(
                    self._convert_images(selections, Path(temp_dir)), output, self._bookmark_titles(), password
                )
        except PdfToolError as exc:
            QMessageBox.critical(self, "Zlúčenie zlyhalo", str(exc))
            return

        self._settings.remember_directory(output)
        self.status_message.emit(f"Uložené: {output}")
        report_success(self, f"Zlúčené PDF bolo uložené:\n{output}", output)

    def _bookmark_titles(self) -> list[str] | None:
        if not self._bookmarks_check.isChecked():
            return None
        # File names without the extension, e.g. "Zmluva – Žilina".
        return [self._entry(self._list.item(row)).path.stem for row in range(self._list.count())]

    def _convert_images(self, selections: list[PageSelection], temp_dir: Path) -> list[PageSelection]:
        page_format = self._page_format_combo.currentData()
        converted = []
        for number, selection in enumerate(selections):
            if is_image(selection.path):
                pdf_path = temp_dir / f"{number}.pdf"
                images_to_pdf([selection.path], pdf_path, page_format)
                selection = PageSelection(pdf_path, [0])
            converted.append(selection)
        return converted

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
