"""Dialog for typing text anywhere on pages: click in the preview, type, drag to adjust."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from PySide6.QtCore import QPointF, QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.text_boxes import DEFAULT_FONT_SIZE, TextBox, box_at, draw_text_boxes, keep_on_page, text_rect
from pdftool.gui.widgets import PageCanvas
from pdftool.gui.zoomed_page import ZoomedPageView
from pdftool.operations import PageRef
from pdftool.plural import format_count, format_page_count_locative

_KEY_STEP = 1.0  # one arrow key press moves the text by one point


class _TextCanvas(PageCanvas):
    """The page preview: a click selects text or starts a new one, dragging moves it."""

    pressed = Signal(QPointF)  # fractions of the page
    dragged = Signal(QPointF)
    nudged = Signal(QPointF)  # a shift in points

    def __init__(self) -> None:
        super().__init__(420, 560)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setAccessibleName("Náhľad strany na vpisovanie textu")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        fraction = self.page_fraction(event.position())
        if fraction is not None and 0 <= fraction.x() <= 1 and 0 <= fraction.y() <= 1:
            self.pressed.emit(fraction)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        fraction = self.page_fraction(event.position())
        if fraction is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.dragged.emit(fraction)

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


class TextBoxDialog(QDialog):
    def __init__(self, pages: Sequence[PageRef], row: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vpísať text")
        self.resize(1100, 780)
        self._pages = list(pages)
        self._boxes: dict[int, list[TextBox]] = {}
        self._selected: int | None = None  # index into the current page's boxes
        self._drag_offset = QPointF()  # from the text's corner to where it was grabbed, in points

        explanation = QLabel(
            "Kliknite do náhľadu tam, kde má text začínať, a píšte. Text presuniete ťahaním, "
            "presnejšie šípkami. Text sa vpíše natrvalo do strany; ak má dokument formulárové "
            "polia, použite radšej Vyplniť formulár."
        )
        explanation.setWordWrap(True)

        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, len(self._pages))
        self._page_spin.setValue(row + 1)
        self._page_spin.setSuffix(f" z {len(self._pages)}")
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("Najprv kliknite do náhľadu strany.")
        self._editor.setAccessibleName("Text")
        self._editor.setFixedHeight(96)
        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(DEFAULT_FONT_SIZE)
        self._size_spin.setSuffix(" bodov")
        self._delete_button = QPushButton("Odstrániť text")
        self._delete_button.clicked.connect(self._delete_selected)

        self._canvas = _TextCanvas()
        self._view = ZoomedPageView(self._canvas)
        form = QFormLayout()
        form.addRow("Strana:", self._page_spin)
        form.addRow("Priblíženie:", self._view.zoom_combo)
        form.addRow("Text:", self._editor)
        form.addRow("Veľkosť písma:", self._size_spin)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        save_hint = QLabel("Zdrojové súbory sa nezmenia.")
        save_hint.setObjectName("hint")
        save_hint.setWordWrap(True)

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        settings_column = QVBoxLayout()
        settings_column.addWidget(explanation)
        settings_column.addLayout(form)
        settings_column.addWidget(self._delete_button)
        settings_column.addWidget(self._summary)
        settings_column.addStretch()
        settings_column.addWidget(save_hint)
        settings_widget = QWidget()
        settings_widget.setLayout(settings_column)
        settings_widget.setMaximumWidth(340)
        columns = QHBoxLayout()
        columns.addWidget(settings_widget)
        columns.addWidget(self._view, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(columns, stretch=1)
        layout.addWidget(buttons)

        self._page_spin.valueChanged.connect(lambda: self._select(None))
        self._editor.textChanged.connect(self._edit_text)
        self._size_spin.valueChanged.connect(self._edit_size)
        self._canvas.pressed.connect(self._press)
        self._canvas.dragged.connect(self._drag)
        self._canvas.nudged.connect(self._nudge)
        self._select(None)

    def boxes(self) -> dict[int, list[TextBox]]:
        """The typed texts by 0-based row; empty texts and rows without text are left out."""
        result = {row: [box for box in boxes if not box.is_empty] for row, boxes in self._boxes.items()}
        return {row: boxes for row, boxes in result.items() if boxes}

    def done(self, result: int) -> None:
        self._view.close_document()
        super().done(result)

    def _row(self) -> int:
        return self._page_spin.value() - 1

    def _page_boxes(self) -> list[TextBox]:
        return self._boxes.setdefault(self._row(), [])

    def _press(self, fraction: QPointF) -> None:
        size = self._view.visible_size()
        if size is None:
            return
        point = QPointF(fraction.x() * size.width(), fraction.y() * size.height())
        boxes = self._page_boxes()
        hit = box_at(size, boxes, point)
        if hit is None:
            # The click marks the middle of the first line, where people point when filling a blank.
            new = TextBox("", fraction.x(), fraction.y(), self._size_spin.value())
            line_height = text_rect(size, new).height()
            new = keep_on_page(replace(new, top=fraction.y() - line_height / 2 / size.height()), size)
            self._select(None)
            boxes = self._page_boxes()
            boxes.append(new)
            hit = len(boxes) - 1
        self._drag_offset = point - text_rect(size, boxes[hit]).topLeft()
        self._select(hit)
        self._editor.setFocus()

    def _drag(self, fraction: QPointF) -> None:
        size = self._view.visible_size()
        if size is None or self._selected is None:
            return
        corner = QPointF(fraction.x() * size.width(), fraction.y() * size.height()) - self._drag_offset
        self._move_selected(corner.x() / size.width(), corner.y() / size.height())

    def _nudge(self, shift: QPointF) -> None:
        size = self._view.visible_size()
        if size is None or self._selected is None:
            return
        box = self._page_boxes()[self._selected]
        self._move_selected(box.left + shift.x() / size.width(), box.top + shift.y() / size.height())

    def _move_selected(self, left: float, top: float) -> None:
        self._replace_selected(lambda box: replace(box, left=left, top=top))

    def _edit_text(self) -> None:
        self._replace_selected(lambda box: replace(box, text=self._editor.toPlainText()))

    def _edit_size(self, size: int) -> None:
        self._replace_selected(lambda box: replace(box, font_size=size))

    def _replace_selected(self, change) -> None:
        if self._selected is None:
            return
        size = self._view.visible_size()
        boxes = self._page_boxes()
        box = change(boxes[self._selected])
        # What is saved is what is shown: text never sticks out of the page.
        boxes[self._selected] = keep_on_page(box, size) if size is not None else box
        self._update_state()

    def _delete_selected(self) -> None:
        if self._selected is not None:
            del self._page_boxes()[self._selected]
            self._selected = None
        self._select(None)
        self._canvas.setFocus()

    def _select(self, index: int | None) -> None:
        kept = self._page_boxes()[index] if index is not None else None
        # A text left empty is dropped once something else is selected.
        for boxes in self._boxes.values():
            boxes[:] = [box for box in boxes if box is kept or not box.is_empty]
        self._selected = None if kept is None else next(
            position for position, box in enumerate(self._page_boxes()) if box is kept
        )
        self._editor.blockSignals(True)
        self._editor.setPlainText(kept.text if kept is not None else "")
        self._editor.blockSignals(False)
        if kept is not None:
            self._size_spin.blockSignals(True)
            self._size_spin.setValue(kept.font_size)
            self._size_spin.blockSignals(False)
        self._editor.setEnabled(kept is not None)
        self._delete_button.setEnabled(kept is not None)
        self._update_state()

    def _update_state(self) -> None:
        typed = self.boxes()
        count = sum(len(boxes) for boxes in typed.values())
        self._accept_button.setEnabled(bool(typed))
        self._summary.setText(
            f"Vpísané: {format_count(count, 'text', 'texty', 'textov')} na {format_page_count_locative(len(typed))}."
            if typed
            else "Zatiaľ nie je vpísaný žiadny text."
        )
        boxes = list(self._page_boxes())
        selected = self._selected

        def draw(painter: QPainter, size: QSizeF) -> None:
            draw_text_boxes(painter, size, boxes)
            if selected is not None:
                # Only in the preview: shows which text the editor and arrow keys change.
                pen = QPen(QColor("#2563eb"), 0, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(text_rect(size, boxes[selected]).adjusted(-1, -1, 1, 1))

        self._view.show_page(self._pages[self._row()], draw)
