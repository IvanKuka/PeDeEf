"""Tab for working with the pages of a document: reorder, duplicate, insert, rotate, delete, extract and split."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field, replace
from pathlib import Path
import tempfile
import secrets

from PySide6.QtCore import QItemSelectionModel, QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.blank_pages import measure_pages
from pdftool.gui.compare import compare_documents
from pdftool.gui.compare_dialog import CompareDialog
from pdftool.gui.command_bar import CommandBar
from pdftool.gui.compress_dialog import CompressDialog
from pdftool.gui.crop_dialog import CropDialog
from pdftool.gui.blank_pages_dialog import BlankPagesDialog
from pdftool.gui.export_dialog import ExportDialog
from pdftool.gui.digital_signature_dialog import DigitalSignatureDialog
from pdftool.gui.images import export_output_paths, export_pages_as_png
from pdftool.gui.icons import command_icon
from pdftool.gui.insert_dialog import InsertDialog
from pdftool.gui.interleave_dialog import InterleaveDialog
from pdftool.gui.page_grid import PageGridWidget
from pdftool.gui.ocr_dialog import OcrDialog
from pdftool.gui.page_preview import PagePreviewDialog
from pdftool.gui.properties_dialog import PropertiesDialog
from pdftool.gui.passwords import output_password, page_count_unlocking
from pdftool.gui.settings import Settings
from pdftool.gui.recognition import recognize_pages
from pdftool.gui.redaction import write_redacted_pdf
from pdftool.gui.redaction_dialog import RedactionDialog
from pdftool.gui.search_bar import SearchBar
from pdftool.gui.form_dialog import FormDialog
from pdftool.gui.form_filling import write_filled_pdf
from pdftool.gui.signature import SIGNATURE_IMAGE_FILTER, load_signature_image, write_signed_pdf
from pdftool.gui.signature_dialog import SignatureDialog
from pdftool.gui.split_dialog import SplitDialog
from pdftool.gui.stamp_dialog import StampDialog
from pdftool.gui.stamp_layer import write_stamped_pdf
from pdftool.gui.text_box_dialog import TextBoxDialog
from pdftool.gui.text_boxes import write_text_pdf
from pdftool.gui.thumbnails import PageThumbnailRenderer, open_document, placeholder_image, thumbnail_icon
from pdftool.gui.widgets import (
    MULTI_SELECT_KEY,
    PDF_FILE_FILTER,
    ask_save_pdf_path,
    busy_cursor,
    confirm,
    native_shortcut_text,
    progress_dialog,
    report_success,
)
from pdftool.forms import read_form_fields
from pdftool.history import History
from pdftool.ocr import find_tesseract, write_with_text_layers
from pdftool.working_document import WorkingDocument
from pdftool.operations import (
    DocumentInfo,
    PageRef,
    PdfToolError,
    has_digital_signature,
    read_properties,
    password_for,
    rotate_crop,
    split_output_paths,
    split_pages,
    unlock,
    write_optimized,
    write_pages,
)
from pdftool.text_search import find_pages, next_match, normalize
from pdftool.signing import inspect_signatures, sign_pdf
from pdftool.plural import (
    format_count,
    format_file_count,
    format_page_count,
    format_page_count_genitive,
)

# Each list item carries the `PageRef` it stands for; the list order is the document order.
_PAGE_ROLE = Qt.ItemDataRole.UserRole
_THUMBNAIL_SIDE = 150
_ROTATE_LEFT_SHORTCUT = "Ctrl+L"
_ROTATE_RIGHT_SHORTCUT = "Ctrl+R"
_DUPLICATE_SHORTCUT = "Ctrl+D"


class _Cancelled(Exception):
    """The user stopped a long save; nothing was written."""


@dataclass(frozen=True)
class _ViewState:
    """What an undo step restores: the pages in display order, the selection and the properties to save."""

    pages: tuple[PageRef, ...]
    # Not part of the comparison: selecting different pages is not an edit.
    selected_rows: tuple[int, ...] = field(default=(), compare=False)
    # Properties written into saved files; None until the user sets them (then nothing is carried over).
    info: DocumentInfo | None = None


class PagesTab(QWidget):
    """Shows one document as a grid of pages.

    Reordering, duplicating, inserting, rotating and deleting pages are only
    pending edits on the view; the source file is untouched until the user
    saves. Page numbers shown in the grid (and used by the split dialog) always
    refer to the pages as currently visible.
    """

    status_message = Signal(str)

    def __init__(self, settings: Settings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings or Settings()
        self._source_path: Path | None = None
        # Every edit is recorded in the history, so its current state always mirrors the list;
        # the document has unsaved changes when that state differs from the pages as loaded.
        self._history = History(_ViewState(()))
        self._pristine: tuple[PageRef, ...] = ()
        self._working = WorkingDocument()
        self.destroyed.connect(self._working.close)
        # List items per (document, page index), so a rendered thumbnail reaches its pages
        # (several when duplicated) without scanning the whole list.
        self._items_by_page: dict[tuple[Path, int], list[QListWidgetItem]] = {}
        # Rendered thumbnails by (document, 0-based page index), shared by duplicates of a page.
        self._images: dict[tuple[Path, int], QImage] = {}
        self._renderers: dict[Path, PageThumbnailRenderer] = {}
        # Normalized text of each source page, read once and searched many times; it does not
        # depend on rotation or position, so results always follow the pages as edited.
        self._page_texts: dict[tuple[Path, int], str] = {}
        self._placeholder = placeholder_image(_THUMBNAIL_SIDE)

        self._open_button = QPushButton("Otvoriť PDF…")
        self._open_button.clicked.connect(self._choose_file)
        self._close_button = QPushButton("Zavrieť")
        self._close_button.setToolTip("Zavrie otvorený súbor bez uloženia zmien")
        self._close_button.clicked.connect(self.close_file)
        self._title = QLabel()
        self._title.setObjectName("fileTitle")
        # A long file name is cut off instead of widening the window; the tooltip has the full path.
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._rotate_left_button = QToolButton(text="⟲  Doľava")
        self._rotate_left_button.setToolTip(f"Otočiť vybrané strany doľava ({native_shortcut_text(_ROTATE_LEFT_SHORTCUT)})")
        self._rotate_left_button.clicked.connect(lambda: self._rotate_selected(-90))
        self._rotate_right_button = QToolButton(text="⟳  Doprava")
        self._rotate_right_button.setToolTip(
            f"Otočiť vybrané strany doprava ({native_shortcut_text(_ROTATE_RIGHT_SHORTCUT)})"
        )
        self._rotate_right_button.clicked.connect(lambda: self._rotate_selected(90))
        self._delete_button = QToolButton(text="Odstrániť")
        self._delete_button.setToolTip("Odstrániť vybrané strany (Delete)")
        self._delete_button.clicked.connect(self._delete_selected)
        self._duplicate_button = QToolButton(text="Duplikovať")
        self._duplicate_button.setToolTip(
            f"Vloží kópie vybraných strán hneď za ne ({native_shortcut_text(_DUPLICATE_SHORTCUT)})"
        )
        self._duplicate_button.clicked.connect(self._duplicate_selected)
        self._insert_button = QToolButton(text="Vložiť z PDF…")
        self._insert_button.setToolTip("Vloží strany z iného PDF pred alebo za vybrané strany")
        self._insert_button.clicked.connect(self._insert_from_pdf)
        # Actions keep their full descriptions in tooltips; ribbon labels stay short.
        self._preview_action = self._tool_action("Náhľad strany (aj dvojklik)", self._preview_selected)
        self._stamp_action = self._tool_action("Číslovanie a pečiatka…", self._stamp)
        self._text_action = self._tool_action("Vpísať text kamkoľvek na stranu…", self._type_text)
        self._form_action = self._tool_action("Vyplniť formulárové polia…", self._fill_form)
        self._signature_action = self._tool_action("Vložiť obrázok podpisu…", self._place_signature)
        self._digital_signature_action = self._tool_action("Digitálne podpísať certifikátom P12/PFX…", self._sign_certificate)
        self._verify_signatures_action = self._tool_action("Overiť integritu digitálnych podpisov…", self._verify_signatures)
        self._redact_action = self._tool_action("Trvalo začierniť údaje…", self._redact)
        self._ocr_action = self._tool_action("Rozpoznať text (OCR)…", self._recognize_text)
        self._blank_action = self._tool_action("Prázdne strany…", self._find_blank_pages)
        self._export_action = self._tool_action("Exportovať vybrané ako PNG…", self._export_selected)
        self._search_action = self._tool_action(
            f"Hľadať text… ({native_shortcut_text(QKeySequence(QKeySequence.StandardKey.Find).toString())})",
            self._open_search,
        )
        self._interleave_action = self._tool_action("Spojiť predné a zadné skeny…", self._interleave_scans)
        self._save_protected_action = self._tool_action("Uložiť s heslom…", lambda: self._save(always_protect=True))
        self._properties_action = self._tool_action("Vlastnosti dokumentu…", self._edit_properties)
        self._crop_action = self._tool_action("Orezať okraje…", self._crop_selected)
        self._compress_action = self._tool_action("Zmenšiť veľkosť…", self._compress)
        self._compare_action = self._tool_action("Porovnať s iným PDF…", self._compare)
        self._undo_button = QPushButton("Späť")
        self._undo_button.setAccessibleName("Späť")
        self._undo_button.clicked.connect(self._undo)
        self._redo_button = QPushButton("Znova")
        self._redo_button.setAccessibleName("Znova")
        self._redo_button.clicked.connect(self._redo)
        for button, icon in ((self._undo_button, "undo"), (self._redo_button, "redo")):
            button.setIcon(command_icon(icon))
        self._select_all_button = QPushButton("Vybrať všetko")

        self._search_bar = SearchBar()
        self._search_bar.hide()
        self._search_bar.search_requested.connect(self._search)
        self._search_bar.select_all_requested.connect(self._select_all_matches)

        self._list = PageGridWidget("Pretiahnite sem PDF súbor\nalebo kliknite na „Otvoriť PDF…“")
        self._list.setIconSize(QSize(_THUMBNAIL_SIDE, _THUMBNAIL_SIDE))
        self._list.setGridSize(QSize(_THUMBNAIL_SIDE + 30, _THUMBNAIL_SIDE + 40))
        self._list.setUniformItemSizes(True)
        self._list.files_dropped.connect(self._on_files_dropped)
        self._list.rows_moved.connect(self._move_rows)
        self._list.itemSelectionChanged.connect(self._update_selection_buttons)
        # Activation is a double-click, or Enter on the current page.
        self._list.itemActivated.connect(lambda item: self._preview_row(self._list.row(item)))
        self._select_all_button.clicked.connect(self._list.selectAll)

        QShortcut(QKeySequence(_ROTATE_LEFT_SHORTCUT), self, activated=lambda: self._rotate_selected(-90))
        QShortcut(QKeySequence(_ROTATE_RIGHT_SHORTCUT), self, activated=lambda: self._rotate_selected(90))
        QShortcut(QKeySequence(_DUPLICATE_SHORTCUT), self, activated=self._duplicate_selected)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self, activated=self._open_search)
        # Standard keys follow the platform: Ctrl+Z and Ctrl+Y on Windows, ⌘Z and ⇧⌘Z on macOS.
        QShortcut(QKeySequence(QKeySequence.StandardKey.Undo), self, activated=self._undo)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Redo), self, activated=self._redo)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Save), self, activated=self._save_current)
        QShortcut(QKeySequence(QKeySequence.StandardKey.SaveAs), self, activated=self._save_as)
        # Backspace too: the "delete" key on Mac keyboards sends Backspace.
        for key in (QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)):
            QShortcut(key, self._list, activated=self._delete_selected)

        hint = QLabel(
            f"Viac strán vyberiete s {MULTI_SELECT_KEY} alebo Shift, presúvajú sa myšou, dvojklik zobrazí "
            "stranu vo veľkom. Úpravy sa zapíšu až pri uložení."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        self._discard_button = QToolButton(text="Zahodiť zmeny")
        self._discard_button.setToolTip("Vráti všetky úpravy strán")
        self._discard_button.clicked.connect(self._discard_changes)
        self._save_button = QPushButton("Uložiť")
        self._save_button.setObjectName("primary")
        self._save_button.setToolTip("Zapísať rozpracované úpravy do aktuálneho PDF (Ctrl+S)")
        self._save_button.clicked.connect(self._save_current)
        self._save_as_button = QPushButton("Uložiť ako…")
        self._save_as_button.setToolTip("Uložiť kópiu PDF pod iným názvom")
        self._save_as_button.clicked.connect(self._save_as)
        self._extract_button = QToolButton(text="Extrahovať vybrané…")
        self._extract_button.clicked.connect(self._extract_selected)
        self._split_button = QToolButton(text="Rozdeliť…")
        self._split_button.clicked.connect(self._split)

        document_bar = QHBoxLayout()
        document_bar.setContentsMargins(4, 0, 0, 0)
        document_bar.setSpacing(8)
        # MainWindow moves this same button to its global navigation row.
        document_bar.addWidget(self._open_button)
        document_bar.addWidget(self._title, stretch=1)
        self._close_button.setText("Zavrieť dokument")
        self._close_button.setAccessibleName("Zavrieť dokument")
        self._close_button.setToolTip("Zavrieť dokument")
        document_bar.addWidget(self._close_button)
        document_bar.addWidget(self._select_all_button)

        self._ribbon = CommandBar()
        self._ribbon.setObjectName("commandRibbon")
        self._ribbon.setAccessibleName("Príkazy dokumentu")
        self._command_panel = QWidget()
        self._command_panel.setObjectName("commandPanel")
        self._command_layout = QHBoxLayout(self._command_panel)
        self._command_layout.setContentsMargins(10, 6, 10, 6)
        self._command_layout.setSpacing(12)
        self._ribbon.setWidget(self._command_panel)
        self._document_actions = QWidget()
        self._document_actions.setObjectName("documentActions")
        quick_actions = QHBoxLayout(self._document_actions)
        quick_actions.setContentsMargins(8, 0, 0, 4)
        quick_actions.setSpacing(5)
        quick_actions.addWidget(self._undo_button)
        quick_actions.addWidget(self._redo_button)
        quick_actions.addWidget(self._save_as_button)
        quick_actions.addWidget(self._save_button)
        document_bar.addWidget(self._document_actions)
        for button, name in (
            (self._open_button, "open"), (self._close_button, "close"),
            (self._save_button, "save"), (self._select_all_button, "select"),
        ):
            button.setIcon(command_icon(name))
        self._add_command_section("Dokument", [
            (self._properties_action, "Vlastnosti\ndokumentu", "properties"),
            (self._discard_button, "Zahodiť\nzmeny", "undo"),
            (self._interleave_action, "Spojiť predné\na zadné skeny", "interleave"),
        ])
        self._add_command_section("Strany", [
            (self._rotate_left_button, "Otočiť\ndoľava", "rotate-left"),
            (self._rotate_right_button, "Otočiť\ndoprava", "rotate-right"),
            (self._duplicate_button, "Duplikovať", "copy"),
            (self._delete_button, "Odstrániť", "delete"),
            (self._extract_button, "Extrahovať", "extract"),
            (self._split_button, "Rozdeliť", "split"),
            (self._crop_action, "Orezať\nokraje", "crop"),
            (self._preview_action, "Veľký\nnáhľad", "preview"),
        ])
        self._add_command_section("Vložiť a podpis", [
            (self._insert_button, "Vložiť strany\nz iného PDF", "insert"),
            (self._text_action, "Vpísať\ntext", "text"),
            (self._form_action, "Vyplniť\nformulár", "form"),
            (self._stamp_action, "Číslovanie\na pečiatka", "stamp"),
            (self._signature_action, "Obrázok\npodpisu", "signature"),
            (self._digital_signature_action, "Digitálny podpis\nP12 / PFX", "certificate"),
            (self._verify_signatures_action, "Overiť\npodpisy", "verify"),
        ])
        self._add_command_section("Nástroje a ochrana", [
            (self._search_action, "Hľadať\ntext", "search"),
            (self._compare_action, "Porovnať\nPDF", "compare"),
            (self._blank_action, "Prázdne\nstrany", "blank"),
            (self._ocr_action, "Rozpoznať\ntext (OCR)", "ocr"),
            (self._redact_action, "Trvalo\nzačierniť", "redact"),
            (self._save_protected_action, "Uložiť\ns heslom", "lock"),
            (self._compress_action, "Zmenšiť\nPDF", "compress"),
            (self._export_action, "Export\nPNG", "image"),
        ])
        self._command_layout.addStretch()
        self._ribbon.fit_height()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._ribbon)
        layout.addLayout(document_bar)
        self._signature_notice = QLabel(
            "Dokument je digitálne podpísaný. Bežné úpravy a export strán podpis nezachovajú. "
            "Ďalší digitálny podpis pridajte k nezmenenému dokumentu."
        )
        self._signature_notice.setObjectName("error")
        self._signature_notice.setWordWrap(True)
        self._signature_notice.hide()
        layout.addWidget(self._signature_notice)
        layout.addWidget(self._search_bar)
        layout.addWidget(self._list, stretch=1)
        layout.addWidget(hint)

        self.apply_preferences()

        self._update_title()
        self._update_buttons()

    def _tool_action(self, text: str, slot) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        return action

    def _add_command_section(self, title: str, commands: list) -> None:
        if self._command_layout.count():
            divider = QFrame()
            divider.setObjectName("commandDivider")
            divider.setFrameShape(QFrame.Shape.VLine)
            self._command_layout.addWidget(divider)
        section = QWidget()
        group = QVBoxLayout(section)
        group.setContentsMargins(0, 0, 0, 0)
        group.setSpacing(4)
        caption = QLabel(title)
        caption.setObjectName("commandCaption")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group.addWidget(caption)
        row = QHBoxLayout()
        row.setSpacing(3)
        for command, label, icon in commands:
            if isinstance(command, QAction):
                command.setIcon(command_icon(icon))
                command.setIconText(label)
                button = QToolButton()
                button.setDefaultAction(command)
                button.setToolTip(command.text())
            else:
                button = command
                button.setText(label)
                button.setIcon(command_icon(icon))
            button.setObjectName("commandButton")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(28, 28))
            label_width = max(button.fontMetrics().horizontalAdvance(line) for line in label.splitlines())
            button.setMinimumWidth(max(78, label_width + 24))
            row.addWidget(button)
        group.addLayout(row)
        self._command_layout.addWidget(section)

    def apply_preferences(self) -> None:
        side = self._settings.thumbnail_size()
        previous = self._list.iconSize().width()
        self._list.setIconSize(QSize(side, side))
        self._list.setGridSize(QSize(side + 30, side + 40))
        if previous != side and self._list.count():
            for renderer in self._renderers.values():
                renderer.stop()
                renderer.deleteLater()
            self._renderers.clear()
            self._images.clear()
            for row in range(self._list.count()):
                item = self._list.item(row)
                item.setIcon(self._icon_for(item.data(_PAGE_ROLE)))
            self._request_thumbnails(self._current_pages())

    def has_unsaved_changes(self) -> bool:
        return self._history.current.pages != self._pristine or self._history.current.info is not None

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
        for renderer in self._renderers.values():
            renderer.stop()
            renderer.deleteLater()
        self._renderers.clear()
        self._clear_list()
        self._page_texts.clear()
        self._search_bar.hide()
        self._pristine = ()
        self._history = History(_ViewState(()))
        self._working.close()
        self._images.clear()
        self._source_path = None
        self._signature_notice.hide()

    def _load(self, path: Path) -> None:
        """Show `path` with no pending changes; on failure the current view is kept."""
        try:
            count = page_count_unlocking(self, path)
        except PdfToolError as exc:
            QMessageBox.warning(self, "Súbor sa nepodarilo otvoriť", str(exc))
            return

        self._reset()
        self._source_path = path
        self._settings.remember_directory(path)
        self._pristine = tuple(PageRef(path, index) for index in range(count))
        self._insert_pages(0, list(self._pristine))
        self._history = History(self._snapshot())
        try:
            self._signature_notice.setVisible(has_digital_signature(path))
        except PdfToolError:
            self._signature_notice.hide()

        if path in self._renderers:
            self.status_message.emit(f"Otvorené: {path}")
        else:
            self.status_message.emit("Náhľady strán sa nepodarilo vykresliť, súbor je však možné upravovať.")
        self._update_title()
        self._update_buttons()

    def _choose_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Otvoriť PDF", str(self._start_directory()), PDF_FILE_FILTER)
        if file_name:
            self.open_file(Path(file_name))

    def _interleave_scans(self) -> None:
        dialog = InterleaveDialog(self._start_directory(), self)
        if dialog.exec() != InterleaveDialog.DialogCode.Accepted or not self._confirm_discard_changes():
            return
        pages = dialog.pages()
        front_path = dialog.front_path()
        # The front sides become the document; interleaving them with the back sides is
        # its first (undoable) edit, and nothing is written until the user saves.
        self._load(front_path)
        if self._source_path != front_path:
            return
        self._clear_list()
        self._insert_pages(0, pages)
        self._commit("Preloženie skenov", [])
        self.status_message.emit(f"Preložené: {format_page_count(len(pages))} (zatiaľ neuložené)")

    def _start_directory(self) -> Path:
        # Files usually come from the same place, so start next to the open document if there is one.
        return self._source_path.parent if self._source_path else self._settings.last_directory()

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
            "Úpravy strán nie sú uložené. Chcete ich zahodiť?",
            "Zahodiť zmeny",
        )

    def _discard_changes(self) -> None:
        if self._source_path is not None and self._confirm_discard_changes():
            self._load(self._source_path)

    def _current_pages(self) -> list[PageRef]:
        """The pages of the document as shown, in display order."""
        return [self._list.item(row).data(_PAGE_ROLE) for row in range(self._list.count())]

    def _selected_rows(self) -> list[int]:
        return sorted(self._list.row(item) for item in self._list.selectedItems())

    def _icon_for(self, page: PageRef) -> QIcon:
        image = self._images.get((page.path, page.index), self._placeholder)
        return thumbnail_icon(image, self._settings.thumbnail_size(), page.rotation, page.crop)

    def _insert_pages(self, row: int, pages: list[PageRef]) -> list[QListWidgetItem]:
        """Insert `pages` before `row` (the page count appends them) and start rendering their thumbnails."""
        items = []
        for offset, page in enumerate(pages):
            item = QListWidgetItem(self._icon_for(page), "")
            item.setData(_PAGE_ROLE, page)
            self._list.insertItem(row + offset, item)
            self._items_by_page.setdefault((page.path, page.index), []).append(item)
            items.append(item)
        self._request_thumbnails(pages)
        self._renumber_pages()
        return items

    def _request_thumbnails(self, pages: list[PageRef]) -> None:
        missing: dict[Path, set[int]] = {}
        for page in pages:
            if (page.path, page.index) not in self._images:
                missing.setdefault(page.path, set()).add(page.index)

        for path, indices in missing.items():
            renderer = self._renderers.get(path)
            if renderer is not None:
                renderer.request(sorted(indices))
                continue
            renderer = PageThumbnailRenderer(self)
            renderer.page_rendered.connect(lambda index, image, path=path: self._on_page_rendered(path, index, image))
            if renderer.start(path, self._settings.thumbnail_size(), sorted(indices)):
                self._renderers[path] = renderer
            else:
                renderer.deleteLater()

    def _on_page_rendered(self, path: Path, index: int, image: QImage) -> None:
        self._images[(path, index)] = image
        # Deleted pages are only taken out of the list, so their items are skipped here.
        items = [item for item in self._items_by_page.get((path, index), []) if item.listWidget() is self._list]
        self._items_by_page[(path, index)] = items
        for item in items:
            item.setIcon(self._icon_for(item.data(_PAGE_ROLE)))

    def _clear_list(self) -> None:
        self._list.clear()
        # The cleared items are deleted by Qt, so nothing may refer to them any more.
        self._items_by_page.clear()

    def _rotate_selected(self, degrees: int) -> None:
        selected_before = self._selected_rows()
        for item in self._list.selectedItems():
            page = item.data(_PAGE_ROLE)
            # A crop is given on the page as seen, so it turns with the page.
            page = replace(page, rotation=(page.rotation + degrees) % 360, crop=rotate_crop(page.crop, degrees))
            item.setData(_PAGE_ROLE, page)
            item.setIcon(self._icon_for(page))
        self._commit(f"Otočenie {format_page_count_genitive(len(selected_before))}", selected_before)

    def _delete_selected(self) -> None:
        rows = self._selected_rows()
        if rows:
            self._delete_rows(rows, f"Odstránenie {format_page_count_genitive(len(rows))}", rows)

    def _delete_rows(self, rows: list[int], label: str, selected_before: list[int]) -> None:
        if len(rows) == self._list.count():
            QMessageBox.information(
                self,
                "Nie je možné odstrániť všetky strany",
                "Dokument musí obsahovať aspoň jednu stranu.\n"
                "Ak ste otvorili nesprávny súbor, použite tlačidlo „Zavrieť“.",
            )
            return

        for row in reversed(rows):
            self._list.takeItem(row)
        self._commit(label, selected_before)
        self.status_message.emit(f"Odstránené: {format_page_count(len(rows))} (zatiaľ neuložené)")

    def _open_search(self) -> None:
        if self._source_path is not None:
            self._search_bar.open()

    def _search_matches(self) -> list[int] | None:
        """Rows matching the search query; None (with a message in the bar) when there is nothing to show."""
        if not normalize(self._search_bar.query()):
            self._search_bar.show_status("")
            return None
        texts = self._texts_of(self._current_pages())
        if texts is None:
            return None
        if not any(texts):
            self._search_bar.show_status("Dokument neobsahuje text (napr. sken) – hľadať v ňom by išlo až po OCR.")
            return None
        matches = find_pages(texts, self._search_bar.query())
        if not matches:
            self._search_bar.show_status("Nenájdené")
            return None
        return matches

    def _search(self, step: int) -> None:
        matches = self._search_matches()
        if matches is None:
            return
        current = self._list.currentRow() if self._list.currentItem() and self._list.currentItem().isSelected() else -1
        row = next_match(matches, current, step)
        item = self._list.item(row)
        self._select_items([item])
        # The next search continues from here.
        self._list.setCurrentItem(item, QItemSelectionModel.SelectionFlag.NoUpdate)
        self._search_bar.show_status(f"Strana {row + 1}  ·  {matches.index(row) + 1} z {len(matches)}")

    def _select_all_matches(self) -> None:
        matches = self._search_matches()
        if matches is not None:
            self._select_items([self._list.item(row) for row in matches])
            self._search_bar.show_status(f"Vybrané: {format_page_count(len(matches))}")

    def _texts_of(self, pages: list[PageRef]) -> list[str] | None:
        """Normalized text of `pages`, reading pages not seen yet; None if the user cancelled."""
        missing = [page for page in dict.fromkeys(pages) if (page.path, page.index) not in self._page_texts]
        if missing:
            with progress_dialog(self, "Hľadať text", "Číta sa text strán…", len(missing)) as report:
                documents = {}
                try:
                    for done, page in enumerate(missing):
                        if not report(done):
                            return None
                        if page.path not in documents:
                            documents[page.path] = open_document(page.path, self)
                        document = documents[page.path]
                        text = document.getAllText(page.index).text() if document is not None else ""
                        self._page_texts[(page.path, page.index)] = normalize(text)
                finally:
                    for document in documents.values():
                        if document is not None:
                            document.close()
                            document.deleteLater()
        return [self._page_texts[(page.path, page.index)] for page in pages]

    def _find_blank_pages(self) -> None:
        pages = self._current_pages()
        with progress_dialog(self, "Prázdne strany", "Posudzujú sa strany…", len(pages)) as report:
            measured = measure_pages(pages, report)
        if measured is None:
            return
        dialog = BlankPagesDialog(measured, self)
        if dialog.exec() == BlankPagesDialog.DialogCode.Accepted and (rows := dialog.rows_to_remove()):
            self._delete_rows(rows, f"Odstránenie prázdnych strán ({len(rows)})", self._selected_rows())

    def _duplicate_selected(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        pages = [self._list.item(row).data(_PAGE_ROLE) for row in rows]
        self._select_items(self._insert_pages(rows[-1] + 1, pages))
        self._commit(f"Duplikovanie {format_page_count_genitive(len(pages))}", rows)
        self.status_message.emit(f"Duplikované: {format_page_count(len(pages))} (zatiaľ neuložené)")

    def _insert_from_pdf(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Vložiť strany z PDF", str(self._start_directory()), PDF_FILE_FILTER
        )
        if not file_name:
            return
        path = Path(file_name)
        # The document is only changed once the file is known to open, so a bad file never disturbs it.
        try:
            count = page_count_unlocking(self, path)
        except PdfToolError as exc:
            QMessageBox.warning(self, "Súbor sa nepodarilo otvoriť", str(exc))
            return

        rows = self._selected_rows()
        dialog = InsertDialog(path, count, bool(rows), self)
        if dialog.exec() != InsertDialog.DialogCode.Accepted:
            return

        if not rows:
            row = self._list.count()
        elif dialog.insert_before():
            row = rows[0]
        else:
            row = rows[-1] + 1
        pages = [PageRef(path, index) for index in dialog.pages()]
        self._select_items(self._insert_pages(row, pages))
        self._commit(f"Vloženie {format_page_count_genitive(len(pages))}", rows)
        self.status_message.emit(f"Vložené: {format_page_count(len(pages))} z {path.name} (zatiaľ neuložené)")

    def _preview_selected(self) -> None:
        current = self._list.currentItem()
        if current is not None and current.isSelected():
            self._preview_row(self._list.row(current))
        elif rows := self._selected_rows():
            self._preview_row(rows[0])

    def _preview_row(self, row: int) -> None:
        assert self._source_path is not None
        dialog = PagePreviewDialog(self._current_pages(), row, self._source_path, self)
        dialog.exec()
        # Continue in the grid where the preview ended.
        self._select_items([self._list.item(dialog.current_row())])
        dialog.deleteLater()

    def _move_rows(self, rows: list[int], target: int) -> None:
        """Move the pages at `rows` (ascending) so that they come before the page that was at `target`."""
        if not rows:
            return
        # Dropping a contiguous block onto itself or right next to itself changes nothing.
        if rows == list(range(rows[0], rows[-1] + 1)) and rows[0] <= target <= rows[-1] + 1:
            return

        items = [self._list.takeItem(row) for row in reversed(rows)]
        items.reverse()
        # Taking the moved pages out shifted every page after them up.
        target -= sum(1 for row in rows if row < target)
        for offset, item in enumerate(items):
            self._list.insertItem(target + offset, item)
        self._select_items(items)
        self._commit(f"Presunutie {format_page_count_genitive(len(items))}", rows)
        self.status_message.emit(f"Presunuté: {format_page_count(len(items))} (zatiaľ neuložené)")

    def _select_items(self, items: list[QListWidgetItem]) -> None:
        # One selection-changed notification for the whole batch instead of one per page.
        self._list.blockSignals(True)
        try:
            self._list.clearSelection()
            for item in items:
                item.setSelected(True)
        finally:
            self._list.blockSignals(False)
        self._update_selection_buttons()
        if items:
            self._list.scrollToItem(items[0])

    def _snapshot(self) -> _ViewState:
        return _ViewState(tuple(self._current_pages()), tuple(self._selected_rows()), self._history.current.info)

    def _commit(self, label: str, selected_before: list[int]) -> None:
        """Finish an edit of the page list: refresh the view and make the edit undoable.

        `selected_before` are the rows that were selected when the edit started;
        undoing the edit selects them again, so the same action can be repeated.
        """
        self._history.replace_current(replace(self._history.current, selected_rows=tuple(selected_before)))
        self._renumber_pages()
        self._history.record(self._snapshot(), label)
        self._update_title()
        self._update_buttons()

    def _undo(self) -> None:
        if self._history.can_undo:
            label = self._history.undo_label
            self._restore(self._history.undo())
            self.status_message.emit(f"Späť: {label}")

    def _redo(self) -> None:
        if self._history.can_redo:
            label = self._history.redo_label
            self._restore(self._history.redo())
            self.status_message.emit(f"Znova: {label}")

    def _restore(self, state: _ViewState) -> None:
        """Show `state` again; thumbnails come from the cache, so nothing is re-rendered."""
        # Without a selection to scroll to, stay where the user was instead of jumping to the top.
        scroll_position = self._list.verticalScrollBar().value()
        self._clear_list()
        items = self._insert_pages(0, list(state.pages))
        self._select_items([items[row] for row in state.selected_rows])
        if not state.selected_rows:
            self._list.verticalScrollBar().setValue(scroll_position)
        self._update_title()
        self._update_buttons()

    def _renumber_pages(self) -> None:
        # Labels follow the visible order, so they match the ranges typed in the split dialog.
        for row in range(self._list.count()):
            item = self._list.item(row)
            page = item.data(_PAGE_ROLE)
            item.setText(str(row + 1))
            if page.path in self._working.sources:
                item.setToolTip("Rozpracované úpravy dokumentu")
            elif page.path != self._source_path:
                item.setToolTip(f"{page.path.name}, strana {page.index + 1}")
            else:
                item.setToolTip("" if page.index == row else f"Pôvodne strana {page.index + 1}")

    def _update_title(self) -> None:
        if self._source_path is None:
            self._title.setText("Nie je otvorený žiadny súbor")
            self._title.setToolTip("")
            return
        text = f"{self._source_path.name}  ·  {format_page_count(self._list.count())}"
        if self.has_unsaved_changes():
            text += "  ·  neuložené zmeny"
        self._title.setText(text)
        self._title.setToolTip(str(self._source_path))

    def _update_buttons(self) -> None:
        has_document = self._source_path is not None
        self._close_button.setEnabled(has_document)
        self._insert_button.setEnabled(has_document)
        self._select_all_button.setEnabled(has_document)
        self._discard_button.setEnabled(self.has_unsaved_changes())
        self._undo_button.setEnabled(self._history.can_undo)
        self._undo_button.setToolTip(self._history_tooltip("Späť", self._history.undo_label, QKeySequence.StandardKey.Undo))
        self._redo_button.setEnabled(self._history.can_redo)
        self._redo_button.setToolTip(self._history_tooltip("Znova", self._history.redo_label, QKeySequence.StandardKey.Redo))
        self._save_button.setEnabled(has_document and self.has_unsaved_changes())
        self._save_as_button.setEnabled(has_document)
        self._stamp_action.setEnabled(has_document)
        self._text_action.setEnabled(has_document)
        self._form_action.setEnabled(has_document)
        self._signature_action.setEnabled(has_document)
        self._digital_signature_action.setEnabled(has_document)
        self._verify_signatures_action.setEnabled(has_document)
        self._redact_action.setEnabled(has_document)
        self._ocr_action.setEnabled(has_document)
        self._search_action.setEnabled(has_document)
        self._save_protected_action.setEnabled(has_document)
        self._properties_action.setEnabled(has_document)
        self._compress_action.setEnabled(has_document)
        self._compare_action.setEnabled(has_document)
        self._blank_action.setEnabled(has_document)
        self._split_button.setEnabled(has_document)
        self._update_selection_buttons()

    def _update_selection_buttons(self) -> None:
        # Runs on every selection change, so it must stay cheap even for very long documents.
        has_selection = bool(self._list.selectedItems())
        for control in (
            self._rotate_left_button,
            self._rotate_right_button,
            self._delete_button,
            self._duplicate_button,
            self._extract_button,
            self._export_action,
            self._preview_action,
            self._crop_action,
        ):
            control.setEnabled(has_selection)

    @staticmethod
    def _history_tooltip(action: str, label: str, key: QKeySequence.StandardKey) -> str:
        shortcut = QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)
        return f"{action}: {label} ({shortcut})" if label else f"{action} ({shortcut})"

    def _compare(self) -> None:
        assert self._source_path is not None
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Porovnať s PDF", str(self._start_directory()), PDF_FILE_FILTER
        )
        if not file_name:
            return
        other = Path(file_name)
        try:
            count = page_count_unlocking(self, other)
        except PdfToolError as exc:
            QMessageBox.warning(self, "Súbor sa nepodarilo otvoriť", str(exc))
            return
        pages = self._current_pages()
        with progress_dialog(self, "Porovnanie", "Porovnávajú sa strany…", max(len(pages), count)) as report:
            pairs = compare_documents(pages, [PageRef(other, index) for index in range(count)], report)
        if pairs is None:
            return
        dialog = CompareDialog(pairs, self._source_path.name, other.name, self)
        dialog.exec()
        dialog.deleteLater()

    def _compress(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        dialog = CompressDialog(self)
        if dialog.exec() != CompressDialog.DialogCode.Accepted:
            return
        self._apply_document_edit(
            "Zmenšenie PDF",
            lambda output, password, info: write_optimized(pages, output, dialog.recompressor(), password, info),
        )

    def _crop_selected(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        dialog = CropDialog(self._list.item(rows[0]).data(_PAGE_ROLE), len(rows), self)
        if dialog.exec() != CropDialog.DialogCode.Accepted:
            return
        crop = dialog.crop()
        for row in rows:
            item = self._list.item(row)
            page = replace(item.data(_PAGE_ROLE), crop=crop)
            item.setData(_PAGE_ROLE, page)
            item.setIcon(self._icon_for(page))
        label = "Zrušenie orezu" if crop is None else "Orezanie"
        self._commit(f"{label} {format_page_count_genitive(len(rows))}", rows)

    def _edit_properties(self) -> None:
        assert self._source_path is not None
        try:
            source = read_properties(self._source_path)
        except PdfToolError as exc:
            QMessageBox.warning(self, "Vlastnosti dokumentu", str(exc))
            return
        dialog = PropertiesDialog(self._source_path.name, source, self._history.current.info, self)
        if dialog.exec() != PropertiesDialog.DialogCode.Accepted:
            return
        selected = self._selected_rows()
        self._history.replace_current(replace(self._history.current, selected_rows=tuple(selected)))
        self._history.record(replace(self._snapshot(), info=dialog.info()), "Zmena vlastností dokumentu")
        self._update_title()
        self._update_buttons()
        self.status_message.emit("Vlastnosti sa zapíšu pri uložení.")

    def _save_current(self) -> None:
        """Replace the open PDF atomically, only at the user's explicit final save."""
        if self._source_path is None or not self.has_unsaved_changes():
            return
        pages = self._current_pages()
        output = self._source_path
        password = password_for(output)
        # Keep the current file's password. A protected attachment must still get
        # the usual protection choice when the current file was unprotected.
        if not password:
            proceed, password = output_password(self, self._working.original_sources(pages))
            if not proceed:
                return
        if not confirm(
            self,
            "Prepísať aktuálne PDF?",
            f"Chcete prepísať aktuálny súbor rozpracovanými úpravami?\n\n{output}",
            "Prepísať a uložiť",
        ):
            return
        if not self._write(pages, output, password):
            return
        self._open_saved(output, password)
        self.status_message.emit(f"Uložené: {output}")

    def _save_as(self) -> None:
        self._save(always_protect=False)

    def _save(self, always_protect: bool) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        proceed, password = output_password(self, self._working.original_sources(pages), always_protect)
        if not proceed:
            return
        suggested = self._source_path.with_name(f"{self._source_path.stem}_upravene.pdf")
        output = ask_save_pdf_path(self, "Uložiť PDF", suggested)
        if output is None or not self._write(pages, output, password):
            return
        self._open_saved(output, password)
        report_success(self, f"PDF bolo uložené:\n{output}", output)

    def _open_saved(self, output: Path, password: str | None) -> None:
        # Show the saved file: its edits are now part of the document, so the view
        # must not keep them as pending changes (also when the source was overwritten).
        if password:
            unlock(output, password)  # the user just chose it; do not ask for it again
        self._load(output)

    def _extract_selected(self) -> None:
        assert self._source_path is not None
        pages = [self._list.item(row).data(_PAGE_ROLE) for row in self._selected_rows()]
        proceed, password = output_password(self, self._working.original_sources(pages))
        if not proceed:
            return
        suggested = self._source_path.with_name(f"{self._source_path.stem}_vyber.pdf")
        output = ask_save_pdf_path(self, "Uložiť vybrané strany", suggested)
        if output is not None and self._uses_source(output):
            QMessageBox.warning(
                self, "Zdrojový súbor sa používa",
                "Výber strán uložte pod iným názvom. Prepísanie zdroja by zneplatnilo ostatné rozpracované strany.",
            )
            return
        if output is not None and self._write(pages, output, password):
            self._settings.remember_directory(output)
            report_success(self, f"Uložené ({format_page_count(len(pages))}):\n{output}", output)

    def _uses_source(self, output: Path) -> bool:
        key = str(output.resolve()).casefold()
        return any(str(page.path.resolve()).casefold() == key for page in self._current_pages())

    def _write(self, pages: list[PageRef], output: Path, password: str | None = None) -> bool:
        try:
            with busy_cursor():
                write_pages(pages, output, password, self._history.current.info)
        except PdfToolError as exc:
            QMessageBox.critical(self, "Uloženie zlyhalo", str(exc))
            return False
        self.status_message.emit(f"Uložené: {output}")
        return True

    def _stamp(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        dialog = StampDialog(pages, self._selected_rows(), self)
        if dialog.exec() != StampDialog.DialogCode.Accepted:
            return
        self._apply_document_edit(
            "Číslovanie a pečiatka",
            lambda output, password, info: write_stamped_pdf(
                pages, dialog.stamped_rows(), dialog.spec(), output, password, info
            ),
        )

    def _type_text(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        selected = self._selected_rows()
        dialog = TextBoxDialog(pages, selected[0] if selected else 0, self)
        if dialog.exec() != TextBoxDialog.DialogCode.Accepted:
            return
        boxes = dialog.boxes()
        self._apply_document_edit(
            "Vpísanie textu",
            lambda output, password, info: write_text_pdf(pages, boxes, output, password, info),
        )

    def _fill_form(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        try:
            with busy_cursor():
                fields = read_form_fields(pages)
                signed = any(has_digital_signature(path) for path in self._working.original_sources(pages))
        except PdfToolError as exc:
            QMessageBox.warning(self, "Vyplniť formulár", str(exc))
            return
        if not fields:
            QMessageBox.information(
                self,
                "Vyplniť formulár",
                "Dokument neobsahuje formulárové polia na vyplnenie. Text môžete vpísať kamkoľvek "
                "na stranu príkazom Vpísať text.",
            )
            return
        selected = self._selected_rows()
        dialog = FormDialog(pages, fields, selected[0] if selected else 0, signed, self)
        if dialog.exec() != FormDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        self._apply_document_edit(
            "Vyplnenie formulára",
            lambda output, password, info: write_filled_pdf(pages, fields, values, output, password, info),
        )

    def _place_signature(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        # The picture is only read into memory: neither it nor its location is remembered.
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Vybrať obrázok podpisu", str(self._source_path.parent), SIGNATURE_IMAGE_FILTER
        )
        if not file_name:
            return
        try:
            with busy_cursor():
                image = load_signature_image(Path(file_name))
                signed = any(has_digital_signature(path) for path in self._working.original_sources(pages))
        except PdfToolError as exc:
            QMessageBox.warning(self, "Obrázok podpisu", str(exc))
            return
        selected = self._selected_rows()
        dialog = SignatureDialog(pages, selected[0] if selected else 0, image, signed, self)
        if dialog.exec() != SignatureDialog.DialogCode.Accepted:
            return
        self._apply_document_edit(
            "Vloženie obrázka podpisu",
            lambda output, password, info: write_signed_pdf(
                pages, dialog.row(), image, dialog.placement(), output, password, info
            ),
        )

    def _sign_certificate(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        edited = tuple(pages) != self._pristine or self._history.current.info is not None
        try:
            if edited and any(has_digital_signature(path) for path in self._working.original_sources(pages)):
                QMessageBox.warning(
                    self, "Dokument už obsahuje podpis",
                    "Rozpracované úpravy by zneplatnili pôvodné podpisy. Na pridanie podpisu otvorte nezmenené finálne PDF.",
                )
                return
        except PdfToolError as exc:
            QMessageBox.warning(self, "Podpisovanie", str(exc))
            return
        dialog = DigitalSignatureDialog(self)
        try:
            if dialog.exec() != dialog.DialogCode.Accepted:
                return
            output = ask_save_pdf_path(
                self, "Uložiť digitálne podpísané PDF", self._source_path.with_name(f"{self._source_path.stem}_podpisane.pdf")
            )
            if output is None:
                return
            if self._uses_source(output):
                QMessageBox.warning(self, "Zdrojový súbor sa používa", "Podpísané PDF uložte pod iným názvom než zdroj.")
                return
            password = password_for(self._source_path)
            if edited:
                proceed, password = output_password(self, self._working.original_sources(pages))
                if not proceed:
                    return
            with busy_cursor():
                if edited:
                    with tempfile.TemporaryDirectory(dir=output.parent) as folder:
                        final = Path(folder) / "final.pdf"
                        write_pages(pages, final, password, self._history.current.info)
                        sign_pdf(final, dialog.identity(), output, dialog.reason(), password)
                else:
                    sign_pdf(self._source_path, dialog.identity(), output, dialog.reason(), password)
            self._open_saved(output, password)
            report_success(
                self, f"Digitálne podpísané PDF bolo uložené:\n{output}\n\nIntegrita podpisu bola skontrolovaná. "
                "Dôvera certifikátu, zneplatnenie a časová pečiatka neboli overené.", output,
            )
        except (PdfToolError, OSError) as exc:
            QMessageBox.critical(self, "Podpisovanie zlyhalo", str(exc))
        finally:
            dialog.release_identity()
            dialog.deleteLater()

    def _verify_signatures(self) -> None:
        assert self._source_path is not None
        try:
            with busy_cursor():
                results = inspect_signatures(self._source_path, password_for(self._source_path))
        except PdfToolError as exc:
            QMessageBox.warning(self, "Podpisy sa nepodarilo overiť", str(exc))
            return
        lines = [f"Kontrola uloženého súboru: {self._source_path.name}", "Rozpracované úpravy nie sú súčasťou kontroly.", ""]
        for number, result in enumerate(results, 1):
            if not result.intact or not result.valid:
                verdict = "integrita podpisu nesedí"
            elif result.coverage.name not in ("ENTIRE_FILE", "ENTIRE_REVISION"):
                verdict = "podpis sedí, ale rozsah pokrytia nie je bezpečne overený"
            elif not result.allowed_changes:
                verdict = "podpísaná revízia je neporušená; následné zmeny nie sú povolené alebo overiteľné"
            else:
                verdict = "integrita je v poriadku"
            scope = "celý súbor" if result.coverage.name == "ENTIRE_FILE" else "staršia revízia alebo čiastočné pokrytie"
            lines.extend([f"{number}. {result.subject}: {verdict}", f"Pokrytie: {scope}", ""])
        if not results:
            lines.append("Dokument neobsahuje digitálny podpis.")
        lines.append("Offline kontrola: dôvera certifikátu, zneplatnenie a časová pečiatka neboli overené.")
        box = QMessageBox(self)
        box.setWindowTitle("Digitálne podpisy")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText("\n".join(lines))
        box.addButton("Zavrieť", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        box.deleteLater()

    def _redact(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        selected = self._selected_rows()
        dialog = RedactionDialog(pages, selected[0] if selected else 0, self)
        if dialog.exec() != RedactionDialog.DialogCode.Accepted:
            return
        self._apply_document_edit(
            "Trvalé začiernenie",
            lambda output, password, info: write_redacted_pdf(
                pages, dialog.areas(), dialog.dpi(), output, password, info
            ),
        )

    def _recognize_text(self) -> None:
        assert self._source_path is not None
        tesseract = find_tesseract()
        if tesseract is None:
            QMessageBox.warning(
                self,
                "Rozpoznávanie textu",
                "Tesseract s jazykovými dátami sa nenašiel. Na Windows aplikáciu preinštalujte. "
                "Na macOS nainštalujte Tesseract a jazyky príkazom brew install tesseract tesseract-lang.",
            )
            return
        pages = self._current_pages()
        texts = self._texts_of(pages)
        if texts is None:
            return
        # Pages that have text already would get it twice, which breaks search and copying.
        rows = [row for row, text in enumerate(texts) if not text]
        if not rows:
            QMessageBox.information(
                self, "Rozpoznávanie textu", "Všetky strany už obsahujú text, nie je čo rozpoznať."
            )
            return
        dialog = OcrDialog(tesseract.languages(), rows, len(pages), self, selected_rows=self._selected_rows())
        if dialog.exec() != OcrDialog.DialogCode.Accepted:
            return
        language = dialog.language()
        rows = dialog.recognition_rows()

        def write(output: Path, password: str | None, info: DocumentInfo | None) -> None:
            with progress_dialog(
                self, "Rozpoznávanie textu", "Rozpoznáva sa text strán…", len(rows), minimum_duration=0
            ) as report:
                layers = recognize_pages(pages, rows, tesseract, language, report)
            if layers is None:
                raise _Cancelled
            with busy_cursor():
                write_with_text_layers(pages, layers, output, password, info)

        self._apply_document_edit("Rozpoznanie textu OCR", write, shows_progress=True)

    def _apply_document_edit(
        self,
        label: str,
        write: Callable[[Path, str | None, DocumentInfo | None], object],
        shows_progress: bool = False,
    ) -> None:
        """Apply a checked working copy as one undoable step, without asking for a file.

        The random encryption password lives only in the session. Original sources
        are retained separately so final saving still asks about their protection.
        """
        pages = self._current_pages()
        selected = self._selected_rows()
        output: Path | None = None
        try:
            output = self._working.new_path()
            password = secrets.token_urlsafe(32)
            with nullcontext() if shows_progress else busy_cursor():
                write(output, password, self._history.current.info)
                if not unlock(output, password) or page_count_unlocking(self, output) != len(pages):
                    raise PdfToolError("Pracovnú verziu PDF sa nepodarilo skontrolovať.")
        except _Cancelled:
            self.status_message.emit("Zrušené – dokument zostal bez zmeny.")
            if output is not None:
                self._working.discard(output)
            return
        except (PdfToolError, OSError) as exc:
            if output is not None:
                self._working.discard(output)
            QMessageBox.critical(self, "Úprava zlyhala", str(exc))
            return
        self._working.sources[output] = self._working.original_sources(pages)
        self._clear_list()
        items = self._insert_pages(0, [PageRef(output, row) for row in range(len(pages))])
        self._select_items([items[row] for row in selected])
        self._commit(label, selected)
        self.status_message.emit(f"{label}: použité. Dokument môžete ďalej upravovať a uložiť na konci.")

    def _export_selected(self) -> None:
        assert self._source_path is not None
        rows = self._selected_rows()
        pages = [self._list.item(row).data(_PAGE_ROLE) for row in rows]
        dialog = ExportDialog(self._source_path, rows, self._source_path.parent, self)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return
        output_dir = dialog.output_dir()
        existing = [path for path in export_output_paths(self._source_path, rows, output_dir) if path.exists()]
        if existing and not self._confirm_overwrite(existing):
            return

        try:
            with busy_cursor():
                created, reduced = export_pages_as_png(pages, rows, self._source_path, output_dir, dialog.dpi())
        except PdfToolError as exc:
            QMessageBox.critical(self, "Export zlyhal", str(exc))
            return

        self._settings.remember_directory(output_dir)
        count = format_count(len(created), "obrázok", "obrázky", "obrázkov")
        message = f"Vytvorené: {count} v priečinku:\n{output_dir}"
        if reduced:
            message += "\n\nNiektoré veľké strany boli uložené v menšom rozlíšení, aby obrázky nezabrali príliš veľa pamäte."
        self.status_message.emit(f"Vytvorené: {count} v {output_dir}")
        report_success(self, message, output_dir)

    def _split(self) -> None:
        assert self._source_path is not None
        pages = self._current_pages()
        dialog = SplitDialog(self._source_path, len(pages), self)
        if dialog.exec() != SplitDialog.DialogCode.Accepted:
            return
        # The dialog works with visible page positions; map them back to the pages shown there.
        groups = [[pages[position] for position in group] for group in dialog.page_groups()]
        output_dir = dialog.output_dir()
        proceed, password = output_password(self, self._working.original_sources(pages))
        if not proceed:
            return

        existing = [
            path for path in split_output_paths(self._source_path, len(groups), output_dir) if path.exists()
        ]
        if any(self._uses_source(path) for path in split_output_paths(self._source_path, len(groups), output_dir)):
            QMessageBox.warning(self, "Zdrojový súbor sa používa", "Vyberte iný priečinok. Výstup rozdelenia by prepísal používaný zdroj.")
            return
        if existing and not self._confirm_overwrite(existing):
            return

        try:
            with busy_cursor():
                created = split_pages(self._source_path, groups, output_dir, password, self._history.current.info)
        except PdfToolError as exc:
            QMessageBox.critical(self, "Rozdelenie zlyhalo", str(exc))
            return

        self._settings.remember_directory(output_dir)
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
