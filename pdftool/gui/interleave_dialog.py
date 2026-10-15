"""Dialog for combining separately scanned front and back sides into one document."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.widgets import PDF_FILE_FILTER
from pdftool.gui.passwords import page_count_unlocking
from pdftool.operations import PageRef, PdfToolError, interleave_pages
from pdftool.plural import format_page_count

# How many pages of the resulting order are spelled out in the preview.
_PREVIEW_PAGES = 8


class InterleaveDialog(QDialog):
    """Asks for the front-side and back-side scans and shows the resulting page order."""

    def __init__(self, start_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spojiť predné a zadné skeny")
        self.setMinimumWidth(560)
        self._start_dir = start_dir
        # Per side: (path, page count), or None until a readable file is chosen.
        self._files: dict[str, tuple[Path, int] | None] = {"front": None, "back": None}
        self._file_errors: dict[str, str] = {"front": "", "back": ""}
        self._edits: dict[str, QLineEdit] = {}

        files = QGridLayout()
        for row, (side, label) in enumerate((("front", "Predné strany:"), ("back", "Zadné strany:"))):
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setPlaceholderText("vyberte PDF súbor")
            button = QPushButton("Vybrať…")
            button.clicked.connect(lambda _checked=False, side=side: self._choose(side))
            files.addWidget(QLabel(label), row, 0)
            files.addWidget(edit, row, 1)
            files.addWidget(button, row, 2)
            self._edits[side] = edit

        self._reverse_check = QCheckBox("Zadné strany sú v opačnom poradí")
        self._reverse_check.setChecked(True)
        reverse_hint = QLabel(
            "Platí, ak ste po skenovaní predných strán otočili celý stoh a skenovali od posledného listu."
        )
        reverse_hint.setObjectName("hint")
        reverse_hint.setWordWrap(True)
        self._reverse_check.toggled.connect(self._update_state)

        self._order = QLabel()
        self._order.setWordWrap(True)
        self._error = QLabel()
        self._error.setObjectName("error")
        self._error.setWordWrap(True)

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = self._buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        help_text = QLabel("Vyberte dve PDF: jedno s prednými a druhé so zadnými stranami. Aplikácia ich striedavo poskladá; sama strany nerozoznáva.")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        layout.addLayout(files)
        layout.addSpacing(8)
        layout.addWidget(self._reverse_check)
        layout.addWidget(reverse_hint)
        layout.addSpacing(8)
        layout.addWidget(self._order)
        layout.addWidget(self._error)
        layout.addWidget(self._buttons)
        self._update_state()

    def set_file(self, side: str, path: Path) -> None:
        """Use `path` for `side` ("front" or "back"); an unreadable file is reported in the dialog."""
        # The name and page count are what the user needs to recognise the scan; the full path is in the tooltip.
        self._edits[side].setToolTip(str(path))
        try:
            count = page_count_unlocking(self, path)
            self._files[side] = (path, count)
            self._file_errors[side] = ""
            self._edits[side].setText(f"{path.name}  ·  {format_page_count(count)}")
        except PdfToolError as exc:
            self._files[side] = None
            self._file_errors[side] = str(exc)
            self._edits[side].setText(path.name)
        self._update_state()

    def pages(self) -> list[PageRef]:
        """The interleaved pages; raises PdfToolError while the input is incomplete or invalid."""
        front, back = self._files["front"], self._files["back"]
        if front is None or back is None:
            raise PdfToolError("Vyberte súbor s prednými aj so zadnými stranami.")
        return interleave_pages(front[0], front[1], back[0], back[1], self._reverse_check.isChecked())

    def front_path(self) -> Path:
        front = self._files["front"]
        assert front is not None
        return front[0]

    def _choose(self, side: str) -> None:
        chosen = self._files["front"] or self._files["back"]
        start_dir = chosen[0].parent if chosen else self._start_dir
        file_name, _ = QFileDialog.getOpenFileName(self, "Vyberte PDF", str(start_dir), PDF_FILE_FILTER)
        if file_name:
            self.set_file(side, Path(file_name))

    def _update_state(self) -> None:
        pages: list[PageRef] = []
        error = self._file_errors["front"] or self._file_errors["back"]
        front, back = self._files["front"], self._files["back"]
        if not error and front and back and front[0] == back[0]:
            error = "Predné a zadné strany musia byť v dvoch rôznych súboroch."
        elif not error and front and back:
            try:
                pages = self.pages()
            except PdfToolError as exc:
                error = str(exc)

        self._accept_button.setEnabled(bool(pages))
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._order.setText(self._describe(pages) if pages else "")
        self._order.setVisible(bool(pages))

    def _describe(self, pages: list[PageRef]) -> str:
        front_path = self.front_path()
        labels = [f"{'P' if page.path == front_path else 'Z'}{page.index + 1}" for page in pages[:_PREVIEW_PAGES]]
        order = ", ".join(labels) + (", …" if len(pages) > _PREVIEW_PAGES else "")
        return f"Výsledok: {format_page_count(len(pages))} v poradí {order}  (P = predná, Z = zadná strana)"
