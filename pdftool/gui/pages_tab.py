"""Tab for working with the pages of a single document: rotate, delete, extract and split."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.split_dialog import SplitDialog
from pdftool.gui.thumbnails import PageThumbnailRenderer, placeholder_image, thumbnail_icon
from pdftool.gui.widgets import (
    MULTI_SELECT_KEY,
    PDF_FILE_FILTER,
    PdfDropListWidget,
    ask_save_pdf_path,
    busy_cursor,
    confirm,
    native_shortcut_text,
    report_success,
)
from pdftool.operations import (
    PageSelection,
    PdfToolError,
    page_count,
    split_output_paths,
    split_pdf,
    write_pdf,
)
from pdftool.plural import format_file_count, format_page_count

_PAGE_INDEX_ROLE = Qt.ItemDataRole.UserRole
_THUMBNAIL_SIDE = 150
_ROTATE_LEFT_SHORTCUT = "Ctrl+L"
_ROTATE_RIGHT_SHORTCUT = "Ctrl+R"


class PagesTab(QWidget):
    """Shows one document as a grid of pages.

    Rotations and deletions are only pending edits on the view; the source file
    is untouched until the user saves. Page numbers shown in the grid (and used
    by the split dialog) always refer to the pages as currently visible.
    """

    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_path: Path | None = None
        self._source_page_count = 0
        # Pages still in the document, keyed by their 0-based index in the source file.
        self._items: dict[int, QListWidgetItem] = {}
        # Pending clockwise rotation per source page index.
        self._rotations: dict[int, int] = {}
        self._images: dict[int, QImage] = {}
        self._placeholder = placeholder_image(_THUMBNAIL_SIDE)

        self._renderer = PageThumbnailRenderer(self)
        self._renderer.page_rendered.connect(self._on_page_rendered)

        self._open_button = QPushButton("Otvoriť PDF…")
        self._open_button.clicked.connect(self._choose_file)
        self._close_button = QPushButton("Zavrieť")
        self._close_button.setToolTip("Zavrie otvorený súbor bez uloženia zmien")
        self._close_button.clicked.connect(self.close_file)
        self._title = QLabel()
        self._title.setObjectName("fileTitle")
        self._rotate_left_button = QPushButton("⟲  Doľava")
        self._rotate_left_button.setToolTip(f"Otočiť vybrané strany doľava ({native_shortcut_text(_ROTATE_LEFT_SHORTCUT)})")
        self._rotate_left_button.clicked.connect(lambda: self._rotate_selected(-90))
        self._rotate_right_button = QPushButton("⟳  Doprava")
        self._rotate_right_button.setToolTip(
            f"Otočiť vybrané strany doprava ({native_shortcut_text(_ROTATE_RIGHT_SHORTCUT)})"
        )
        self._rotate_right_button.clicked.connect(lambda: self._rotate_selected(90))
        self._delete_button = QPushButton("Odstrániť strany")
        self._delete_button.setToolTip("Odstrániť vybrané strany (Delete)")
        self._delete_button.clicked.connect(self._delete_selected)
        self._select_all_button = QPushButton("Vybrať všetko")

        self._list = PdfDropListWidget("Pretiahnite sem PDF súbor\nalebo kliknite na „Otvoriť PDF…“")
        self._list.setViewMode(QListView.ViewMode.IconMode)
        self._list.setMovement(QListView.Movement.Static)
        self._list.setResizeMode(QListView.ResizeMode.Adjust)
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        # setMovement(Static) turns off drops on the viewport, which is where Qt delivers
        # drag events; re-enable it so PDFs can be dropped from Explorer.
        self._list.viewport().setAcceptDrops(True)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setIconSize(QSize(_THUMBNAIL_SIDE, _THUMBNAIL_SIDE))
        self._list.setGridSize(QSize(_THUMBNAIL_SIDE + 30, _THUMBNAIL_SIDE + 40))
        self._list.setUniformItemSizes(True)
        self._list.files_dropped.connect(self._on_files_dropped)
        self._list.itemSelectionChanged.connect(self._update_buttons)
        self._select_all_button.clicked.connect(self._list.selectAll)

        QShortcut(QKeySequence(_ROTATE_LEFT_SHORTCUT), self, activated=lambda: self._rotate_selected(-90))
        QShortcut(QKeySequence(_ROTATE_RIGHT_SHORTCUT), self, activated=lambda: self._rotate_selected(90))
        # Backspace too: the "delete" key on Mac keyboards sends Backspace.
        for key in (QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)):
            QShortcut(key, self._list, activated=self._delete_selected)

        hint = QLabel(
            f"Viac strán vyberiete so stlačeným {MULTI_SELECT_KEY} alebo Shift. "
            "Otočenie a odstránenie strán sa prejaví až pri uložení."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        self._discard_button = QPushButton("Zahodiť zmeny")
        self._discard_button.setToolTip("Vráti všetky otočenia a odstránené strany")
        self._discard_button.clicked.connect(self._discard_changes)
        self._save_button = QPushButton("Uložiť ako…")
        self._save_button.clicked.connect(self._save_as)
        self._extract_button = QPushButton("Extrahovať vybrané…")
        self._extract_button.clicked.connect(self._extract_selected)
        self._split_button = QPushButton("Rozdeliť…")
        self._split_button.setObjectName("primary")
        self._split_button.clicked.connect(self._split)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._open_button)
        toolbar.addWidget(self._close_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._title, stretch=1)
        toolbar.addWidget(self._rotate_left_button)
        toolbar.addWidget(self._rotate_right_button)
        toolbar.addWidget(self._delete_button)
        toolbar.addWidget(self._select_all_button)

        actions = QHBoxLayout()
        actions.addWidget(hint, stretch=1)
        actions.addWidget(self._discard_button)
        actions.addWidget(self._save_button)
        actions.addWidget(self._extract_button)
        actions.addWidget(self._split_button)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._list, stretch=1)
        layout.addLayout(actions)

        self._update_title()
        self._update_buttons()

    def has_unsaved_changes(self) -> bool:
        return len(self._items) < self._source_page_count or any(self._rotations.values())

    def open_file(self, path: Path) -> None:
        if self._confirm_discard_changes():
            self._load(path)

    def close_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        self._reset()
        self._update_title()
        self._update_buttons()

    def _reset(self) -> None:
        self._renderer.stop()
        self._list.clear()
        self._items.clear()
        self._rotations.clear()
        self._images.clear()
        self._source_path = None
        self._source_page_count = 0

    def _load(self, path: Path) -> None:
        """Show `path` with no pending changes; on failure the current view is kept."""
        try:
            with busy_cursor():
                count = page_count(path)
        except PdfToolError as exc:
            QMessageBox.warning(self, "Súbor sa nepodarilo otvoriť", str(exc))
            return

        self._reset()
        self._source_path = path
        self._source_page_count = count
        for index in range(count):
            item = QListWidgetItem(thumbnail_icon(self._placeholder, _THUMBNAIL_SIDE), str(index + 1))
            item.setData(_PAGE_INDEX_ROLE, index)
            self._list.addItem(item)
            self._items[index] = item

        if self._renderer.start(path, _THUMBNAIL_SIDE):
            self.status_message.emit(f"Otvorené: {path}")
        else:
            self.status_message.emit("Náhľady strán sa nepodarilo vykresliť, súbor je však možné upravovať.")
        self._update_title()
        self._update_buttons()

    def _choose_file(self) -> None:
        start_dir = self._source_path.parent if self._source_path else Path.home()
        file_name, _ = QFileDialog.getOpenFileName(self, "Otvoriť PDF", str(start_dir), PDF_FILE_FILTER)
        if file_name:
            self.open_file(Path(file_name))

    def _on_files_dropped(self, paths: list[Path]) -> None:
        if len(paths) > 1:
            self.status_message.emit("Na úpravu strán sa otvára iba prvý pretiahnutý súbor.")
        self.open_file(paths[0])

    def _confirm_discard_changes(self) -> bool:
        if not self.has_unsaved_changes():
            return True
        return confirm(
            self,
            "Neuložené zmeny",
            "Otočenie alebo odstránenie strán nebolo uložené. Chcete zmeny zahodiť?",
            "Zahodiť zmeny",
        )

    def _discard_changes(self) -> None:
        if self._source_path is not None and self._confirm_discard_changes():
            self._load(self._source_path)

    def _on_page_rendered(self, index: int, image: QImage) -> None:
        self._images[index] = image
        if index in self._items:
            self._refresh_icon(index)

    def _refresh_icon(self, index: int) -> None:
        image = self._images.get(index, self._placeholder)
        self._items[index].setIcon(thumbnail_icon(image, _THUMBNAIL_SIDE, self._rotations.get(index, 0)))

    def _kept_pages(self) -> list[int]:
        """Source indices of the pages still in the document, in display order."""
        return sorted(self._items)

    def _selected_pages(self) -> list[int]:
        return sorted(item.data(_PAGE_INDEX_ROLE) for item in self._list.selectedItems())

    def _rotate_selected(self, degrees: int) -> None:
        for index in self._selected_pages():
            self._rotations[index] = (self._rotations.get(index, 0) + degrees) % 360
            self._refresh_icon(index)
        self._update_title()
        self._update_buttons()

    def _delete_selected(self) -> None:
        pages = self._selected_pages()
        if not pages:
            return
        if len(pages) == len(self._items):
            QMessageBox.information(
                self,
                "Nie je možné odstrániť všetky strany",
                "Dokument musí obsahovať aspoň jednu stranu.\n"
                "Ak ste otvorili nesprávny súbor, použite tlačidlo „Zavrieť“.",
            )
            return

        for index in pages:
            self._list.takeItem(self._list.row(self._items.pop(index)))
            self._rotations.pop(index, None)
        self._renumber_pages()
        self.status_message.emit(f"Odstránené: {format_page_count(len(pages))} (zatiaľ neuložené)")
        self._update_title()
        self._update_buttons()

    def _renumber_pages(self) -> None:
        # Labels follow the visible order, so they match the ranges typed in the split dialog.
        for row in range(self._list.count()):
            item = self._list.item(row)
            source_number = item.data(_PAGE_INDEX_ROLE) + 1
            item.setText(str(row + 1))
            item.setToolTip("" if source_number == row + 1 else f"Pôvodne strana {source_number}")

    def _update_title(self) -> None:
        if self._source_path is None:
            self._title.setText("Nie je otvorený žiadny súbor")
            self._title.setToolTip("")
            return
        text = f"{self._source_path.name}  ·  {format_page_count(len(self._items))}"
        if self.has_unsaved_changes():
            text += "  ·  neuložené zmeny"
        self._title.setText(text)
        self._title.setToolTip(str(self._source_path))

    def _update_buttons(self) -> None:
        has_document = self._source_path is not None
        has_selection = bool(self._list.selectedItems())
        self._close_button.setEnabled(has_document)
        self._rotate_left_button.setEnabled(has_selection)
        self._rotate_right_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)
        self._select_all_button.setEnabled(has_document)
        self._discard_button.setEnabled(self.has_unsaved_changes())
        self._save_button.setEnabled(has_document)
        self._extract_button.setEnabled(has_selection)
        self._split_button.setEnabled(has_document)

    def _current_document(self) -> PageSelection:
        assert self._source_path is not None
        return PageSelection(self._source_path, pages=self._kept_pages(), rotations=self._rotations)

    def _save_as(self) -> None:
        assert self._source_path is not None
        suggested = self._source_path.with_name(f"{self._source_path.stem}_upravene.pdf")
        output = ask_save_pdf_path(self, "Uložiť PDF", suggested)
        if output is None or not self._write([self._current_document()], output):
            return
        # Show the saved file: its edits are now part of the document, so the view
        # must not keep them as pending changes (also when the source was overwritten).
        self._load(output)
        report_success(self, f"PDF bolo uložené:\n{output}", output)

    def _extract_selected(self) -> None:
        assert self._source_path is not None
        pages = self._selected_pages()
        suggested = self._source_path.with_name(f"{self._source_path.stem}_vyber.pdf")
        output = ask_save_pdf_path(self, "Uložiť vybrané strany", suggested)
        selection = PageSelection(self._source_path, pages=pages, rotations=self._rotations)
        if output is not None and self._write([selection], output):
            report_success(self, f"Uložené ({format_page_count(len(pages))}):\n{output}", output)

    def _write(self, selections: list[PageSelection], output: Path) -> bool:
        try:
            with busy_cursor():
                write_pdf(selections, output)
        except PdfToolError as exc:
            QMessageBox.critical(self, "Uloženie zlyhalo", str(exc))
            return False
        self.status_message.emit(f"Uložené: {output}")
        return True

    def _split(self) -> None:
        assert self._source_path is not None
        kept_pages = self._kept_pages()
        dialog = SplitDialog(self._source_path, len(kept_pages), self)
        if dialog.exec() != SplitDialog.DialogCode.Accepted:
            return
        # The dialog works with visible page positions; map them back to source pages.
        groups = [[kept_pages[position] for position in group] for group in dialog.page_groups()]
        output_dir = dialog.output_dir()

        existing = [
            path for path in split_output_paths(self._source_path, len(groups), output_dir) if path.exists()
        ]
        if existing and not self._confirm_overwrite(existing):
            return

        try:
            with busy_cursor():
                created = split_pdf(self._source_path, groups, output_dir, self._rotations)
        except PdfToolError as exc:
            QMessageBox.critical(self, "Rozdelenie zlyhalo", str(exc))
            return

        self.status_message.emit(f"Vytvorené: {format_file_count(len(created))} v {output_dir}")
        report_success(self, f"Vytvorené: {format_file_count(len(created))} v priečinku:\n{output_dir}", output_dir)

    def _confirm_overwrite(self, existing: list[Path]) -> bool:
        names = "\n".join(path.name for path in existing[:5])
        if len(existing) > 5:
            names += "\n…"
        return confirm(
            self,
            "Súbory už existujú",
            f"Nasledujúce súbory už existujú a budú prepísané:\n{names}",
            "Prepísať",
        )
