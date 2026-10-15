"""Dialog for placing a signature picture on one page, by dragging it in a preview."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.signature import SignaturePlacement, draw_signature, keep_on_page
from pdftool.gui.stamp_layer import render_preview
from pdftool.gui.thumbnails import open_document, visible_point_size
from pdftool.gui.widgets import PageCanvas
from pdftool.operations import PageRef

_PREVIEW_WIDTH, _PREVIEW_HEIGHT = 420, 560
# Bottom right, where signatures usually go; a quarter of the page width.
_DEFAULT_PLACEMENT = SignaturePlacement(center_x=0.72, center_y=0.85, width=0.25)
_KEY_STEP = 0.01  # one arrow key press moves the picture by 1 % of the page


class _PlacementView(PageCanvas):
    """The page preview; clicking, dragging or arrow keys move the picture."""

    moved = Signal(QPointF)  # the new centre, as fractions of the page
    nudged = Signal(QPointF)  # a shift, as fractions of the page

    def __init__(self) -> None:
        super().__init__(_PREVIEW_WIDTH, _PREVIEW_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAccessibleName("Náhľad strany s podpisom")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._move_to(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._move_to(event.position())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        shifts = {
            Qt.Key.Key_Left: QPointF(-_KEY_STEP, 0),
            Qt.Key.Key_Right: QPointF(_KEY_STEP, 0),
            Qt.Key.Key_Up: QPointF(0, -_KEY_STEP),
            Qt.Key.Key_Down: QPointF(0, _KEY_STEP),
        }
        if event.key() in shifts:
            self.nudged.emit(shifts[event.key()])
        else:
            super().keyPressEvent(event)

    def _move_to(self, position: QPointF) -> None:
        center = self.page_fraction(position)
        if center is not None:
            self.moved.emit(center)


class SignatureDialog(QDialog):
    def __init__(
        self,
        pages: Sequence[PageRef],
        row: int,
        image: QImage,
        digitally_signed: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vložiť obrázok podpisu")
        self._pages = list(pages)
        self._image = image
        self._placement = _DEFAULT_PLACEMENT
        self._document: QPdfDocument | None = None
        self._document_path = None

        # The application must not let anyone mistake the picture for a legally stronger signature.
        notice = QLabel(
            "Vloží sa obrázok podpisu na stranu (grafický podpis). Nie je to elektronický "
            "ani certifikovaný digitálny podpis a neoveruje totožnosť podpisujúceho."
        )
        notice.setWordWrap(True)
        self._signed_warning = QLabel(
            "Dokument je digitálne podpísaný. V novom súbore už digitálny podpis nebude platný."
        )
        self._signed_warning.setObjectName("error")
        self._signed_warning.setWordWrap(True)
        self._signed_warning.setVisible(digitally_signed)

        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, len(self._pages))
        self._page_spin.setValue(row + 1)
        self._page_spin.setSuffix(f" z {len(self._pages)}")
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(5, 80)
        self._size_slider.setValue(round(_DEFAULT_PLACEMENT.width * 100))
        self._size_slider.setAccessibleName("Šírka podpisu v percentách šírky strany")
        self._size_label = QLabel()
        size_row = QHBoxLayout()
        size_row.addWidget(self._size_slider, stretch=1)
        size_row.addWidget(self._size_label)
        form = QFormLayout()
        form.addRow("Strana:", self._page_spin)
        form.addRow("Šírka:", size_row)

        move_hint = QLabel("Podpis presuniete kliknutím alebo ťahaním v náhľade, presnejšie šípkami.")
        move_hint.setObjectName("hint")
        move_hint.setWordWrap(True)
        save_hint = QLabel(
            "Obrázok sa zapíše do nového súboru; zdrojové súbory sa nezmenia a obrázok sa nikam neukladá."
        )
        save_hint.setObjectName("hint")
        save_hint.setWordWrap(True)

        self._preview = _PlacementView()
        self._preview.moved.connect(self._move_to)
        self._preview.nudged.connect(
            lambda shift: self._move_to(
                QPointF(self._placement.center_x + shift.x(), self._placement.center_y + shift.y())
            )
        )

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        settings_column = QVBoxLayout()
        settings_column.addWidget(notice)
        settings_column.addWidget(self._signed_warning)
        settings_column.addLayout(form)
        settings_column.addWidget(move_hint)
        settings_column.addStretch()
        settings_column.addWidget(save_hint)
        columns = QHBoxLayout()
        columns.addLayout(settings_column, stretch=1)
        columns.addWidget(self._preview)
        layout = QVBoxLayout(self)
        layout.addLayout(columns)
        layout.addWidget(buttons)

        self._page_spin.valueChanged.connect(self._update_preview)
        self._size_slider.valueChanged.connect(self._resize)
        self._resize(self._size_slider.value())
        self._preview.setFocus()

    def row(self) -> int:
        return self._page_spin.value() - 1

    def placement(self) -> SignaturePlacement:
        return self._placement

    def done(self, result: int) -> None:
        if self._document is not None:
            self._document.close()
        super().done(result)

    def _resize(self, percent: int) -> None:
        self._size_label.setText(f"{percent} % strany")
        self._placement = SignaturePlacement(self._placement.center_x, self._placement.center_y, percent / 100)
        self._update_preview()

    def _move_to(self, center: QPointF) -> None:
        self._placement = SignaturePlacement(center.x(), center.y(), self._placement.width)
        self._update_preview()

    def _update_preview(self) -> None:
        page = self._pages[self.row()]
        if self._document_path != page.path:
            if self._document is not None:
                self._document.close()
            self._document = open_document(page.path, self)
            self._document_path = page.path
        if self._document is None:
            # Without the page size the picture cannot be placed reliably.
            self._preview.setText("Náhľad nie je k dispozícii.")
            self._accept_button.setEnabled(False)
            return
        self._accept_button.setEnabled(True)
        visible = visible_point_size(self._document, page.index, page.rotation, page.crop)
        # What is saved is what is shown: the picture never sticks out of the page.
        self._placement = keep_on_page(self._placement, QSizeF(visible), self._image.size())
        placement = self._placement
        self._preview.setPixmap(
            render_preview(
                self._document,
                page,
                QSize(_PREVIEW_WIDTH - 8, _PREVIEW_HEIGHT - 8),
                lambda painter, size: draw_signature(painter, size, self._image, placement),
            )
        )
