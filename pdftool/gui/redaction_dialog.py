"""Dialog for marking areas to black out permanently, by dragging rectangles over page previews."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRectF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.redaction import REDACTION_DPI
from pdftool.gui.stamp_layer import render_preview
from pdftool.gui.thumbnails import open_document, visible_point_size
from pdftool.gui.widgets import PageCanvas
from pdftool.operations import PageRef
from pdftool.plural import format_count, format_page_count_locative

_PREVIEW_WIDTH, _PREVIEW_HEIGHT = 420, 560
# Smaller drags are taken as accidental clicks (fraction of the page side).
_MIN_SIDE = 0.005


class _AreaCanvas(PageCanvas):
    """The page preview; dragging with the mouse marks a rectangle."""

    area_drawn = Signal(QRectF)  # fractions of the page
    dragging = Signal(QRectF)  # the rectangle being drawn, to show it while dragging

    def __init__(self) -> None:
        super().__init__(_PREVIEW_WIDTH, _PREVIEW_HEIGHT)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAccessibleName("Náhľad strany na označenie oblastí")
        self._start: QPointF | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._start = self._clamped_fraction(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        current = self._clamped_fraction(event.position())
        if self._start is not None and current is not None:
            self.dragging.emit(QRectF(self._start, current).normalized())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        end = self._clamped_fraction(event.position())
        start, self._start = self._start, None
        if start is None or end is None:
            return
        area = QRectF(start, end).normalized()
        if area.width() >= _MIN_SIDE and area.height() >= _MIN_SIDE:
            self.area_drawn.emit(area)
        else:
            self.dragging.emit(QRectF())

    def _clamped_fraction(self, position: QPointF) -> QPointF | None:
        fraction = self.page_fraction(position)
        if fraction is None:
            return None
        return QPointF(min(max(fraction.x(), 0.0), 1.0), min(max(fraction.y(), 0.0), 1.0))


class RedactionDialog(QDialog):
    def __init__(self, pages: Sequence[PageRef], row: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trvalé začiernenie")
        self.resize(1100, 780)
        self._pages = list(pages)
        self._areas: dict[int, list[QRectF]] = {}
        self._dragging = QRectF()
        self._document: QPdfDocument | None = None
        self._document_path = None
        self._preview_key = None
        self._preview_base: QPixmap | None = None

        explanation = QLabel(
            "Ťahaním myšou označte, čo sa má natrvalo odstrániť. Strany s označením sa uložia ako obrázok: "
            "z označených miest nezostane v súbore nič, ale text na celej strane už nepôjde označiť ani "
            "vyhľadať a komentáre či formulárové polia na nej zaniknú. Ostatné strany zostanú bezo zmeny – "
            "ak sa údaj nachádza aj na nich, označte ho aj tam (pomôže Hľadať text)."
        )
        explanation.setWordWrap(True)

        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, len(self._pages))
        self._page_spin.setValue(row + 1)
        self._page_spin.setSuffix(f" z {len(self._pages)}")
        self._dpi_combo = QComboBox()
        for dpi, label in zip(REDACTION_DPI, ("menší súbor", "ostrejšie"), strict=True):
            self._dpi_combo.addItem(f"{dpi} dpi ({label})", dpi)
        form = QFormLayout()
        form.addRow("Strana:", self._page_spin)
        form.addRow("Kvalita strán:", self._dpi_combo)

        self._undo_button = QPushButton("Zrušiť poslednú oblasť")
        self._undo_button.clicked.connect(self._remove_last_area)
        self._clear_button = QPushButton("Zrušiť oblasti na strane")
        self._clear_button.clicked.connect(self._clear_page)
        area_buttons = QVBoxLayout()
        area_buttons.addWidget(self._undo_button)
        area_buttons.addWidget(self._clear_button)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        save_hint = QLabel(
            "Výsledok sa pred uložením skontroluje: na začiernených stranách nesmie zostať text. "
            "Zdrojové súbory sa nezmenia."
        )
        save_hint.setObjectName("hint")
        save_hint.setWordWrap(True)

        self._zoom = QComboBox()
        for label, scale in (("Prispôsobiť oknu", 0), ("100 %", 1), ("150 %", 1.5), ("200 %", 2)):
            self._zoom.addItem(label, scale)
        form.addRow("Priblíženie:", self._zoom)
        self._canvas = _AreaCanvas()
        self._canvas.area_drawn.connect(self._add_area)
        self._canvas.dragging.connect(self._show_dragging)
        self._preview_scroll = QScrollArea()
        self._preview_scroll.setWidget(self._canvas)
        self._preview_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_scroll.setMinimumSize(300, 300)
        self._zoom.currentIndexChanged.connect(self._update_preview)

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        settings_column = QVBoxLayout()
        settings_column.addWidget(explanation)
        settings_column.addLayout(form)
        settings_column.addLayout(area_buttons)
        settings_column.addWidget(self._summary)
        settings_column.addStretch()
        settings_column.addWidget(save_hint)
        columns = QHBoxLayout()
        settings_widget = QWidget()
        settings_widget.setLayout(settings_column)
        settings_widget.setMaximumWidth(320)
        columns.addWidget(settings_widget)
        columns.addWidget(self._preview_scroll, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(columns, stretch=1)
        layout.addWidget(buttons)

        self._page_spin.valueChanged.connect(self._update_state)
        self._update_state()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_preview_scroll"):
            self._update_preview()

    def areas(self) -> dict[int, list[QRectF]]:
        """Marked rectangles as fractions of the visible page, by 0-based row; rows without areas omitted."""
        return {row: list(areas) for row, areas in self._areas.items() if areas}

    def dpi(self) -> int:
        return self._dpi_combo.currentData()

    def done(self, result: int) -> None:
        if self._document is not None:
            self._document.close()
        self._preview_base = None
        self._canvas.clear()
        super().done(result)

    def _row(self) -> int:
        return self._page_spin.value() - 1

    def _add_area(self, area: QRectF) -> None:
        self._areas.setdefault(self._row(), []).append(area)
        self._dragging = QRectF()
        self._update_state()

    def _remove_last_area(self) -> None:
        if self._areas.get(self._row()):
            self._areas[self._row()].pop()
        self._update_state()

    def _clear_page(self) -> None:
        self._areas.pop(self._row(), None)
        self._update_state()

    def _show_dragging(self, area: QRectF) -> None:
        self._dragging = area
        self._update_preview()

    def _update_state(self) -> None:
        marked = self.areas()
        area_count = sum(len(areas) for areas in marked.values())
        on_page = len(self._areas.get(self._row(), []))
        self._undo_button.setEnabled(on_page > 0)
        self._clear_button.setEnabled(on_page > 0)
        self._accept_button.setEnabled(bool(marked))
        self._summary.setText(
            f"Označené: {format_count(area_count, 'oblasť', 'oblasti', 'oblastí')} "
            f"na {format_page_count_locative(len(marked))}."
            if marked
            else "Zatiaľ nie je nič označené."
        )
        self._update_preview()

    def _update_preview(self) -> None:
        page = self._pages[self._row()]
        if self._document_path != page.path:
            if self._document is not None:
                self._document.close()
            self._document = open_document(page.path, self)
            self._document_path = page.path
        if self._document is None:
            self._canvas.setText("Náhľad nie je k dispozícii.")
            return
        areas = list(self._areas.get(self._row(), []))
        dragging = self._dragging
        size = visible_point_size(self._document, page.index, page.rotation, page.crop)
        zoom = self._zoom.currentData()
        if not zoom:
            scale = min(max(1, self._preview_scroll.viewport().width() - 12) / size.width(),
                        max(1, self._preview_scroll.viewport().height() - 12) / size.height())
        else:
            scale = zoom * 96 / 72
        scale = min(scale, 2200 / max(size.width(), size.height()))
        box = QSize(max(1, round(size.width() * scale)), max(1, round(size.height() * scale)))
        self._canvas.setFixedSize(box)
        key = (page, box.width(), box.height())
        if self._preview_base is None or key != self._preview_key:
            # Moving the selection rectangle must not render the PDF again on each mouse event.
            self._preview_base = render_preview(
                self._document,
                page,
                box,
                lambda painter, size: None,
            )
            self._preview_key = key
        preview = QPixmap(self._preview_base)
        painter = QPainter(preview)
        _draw_areas(painter, preview.deviceIndependentSize(), areas, dragging)
        painter.end()
        self._canvas.setPixmap(preview)


def _draw_areas(painter: QPainter, page_size: QSizeF, areas: list[QRectF], dragging: QRectF) -> None:
    def on_page(area: QRectF) -> QRectF:
        return QRectF(
            area.x() * page_size.width(),
            area.y() * page_size.height(),
            area.width() * page_size.width(),
            area.height() * page_size.height(),
        )

    for area in areas:  # as they will look in the saved file
        painter.fillRect(on_page(area), QColor("black"))
    if not dragging.isEmpty():
        painter.setPen(QPen(QColor("#dc2626"), 0))  # cosmetic pen: one pixel at any zoom
        painter.drawRect(on_page(dragging))
