"""Grid of page thumbnails whose selected pages can be reordered by dragging."""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QPainter
from PySide6.QtWidgets import QAbstractItemView, QListView, QWidget

from pdftool.gui.style import ACCENT
from pdftool.gui.widgets import PdfDropListWidget

_REORDER_MIME = "application/x-pdftool-page-rows"
_EDGE_SCROLL_MARGIN = 30
_EDGE_SCROLL_STEP = 24
_EDGE_SCROLL_INTERVAL_MS = 40
_INDICATOR_COLOR = QColor(ACCENT)
_INDICATOR_WIDTH = 3


class PageGridWidget(PdfDropListWidget):
    """Icon grid that reports drag-and-drop reordering instead of performing it.

    Qt's built-in internal move cannot reorder an icon view with static
    positions, and it removes the dragged items from the source after the drop.
    The widget therefore runs the drag itself and only emits `rows_moved`
    (the dragged rows and the row they should be inserted before, both in
    the numbering before the move); the owner changes the order. Files dropped
    from outside keep the behaviour of `PdfDropListWidget`.
    """

    rows_moved = Signal(list, int)

    def __init__(self, empty_hint: str, parent: QWidget | None = None) -> None:
        super().__init__(empty_hint, parent)
        self._drop_row: int | None = None
        # -1 / +1 while a reorder drag rests near the top / bottom edge, 0 otherwise.
        self._edge_scroll_direction = 0
        self._edge_scroll_timer = QTimer(self)
        self._edge_scroll_timer.setInterval(_EDGE_SCROLL_INTERVAL_MS)
        self._edge_scroll_timer.timeout.connect(self._scroll_step)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setMovement(QListView.Movement.Static)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        # setMovement(Static) turns off drops on the viewport, which is where Qt delivers
        # drag events; re-enable it so reordering and PDFs dropped from Explorer both work.
        self.viewport().setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def insertion_row(self, position: QPoint) -> int:
        """The row a drop at `position` (viewport coordinates) inserts before; `count()` means the end."""
        for row in range(self.count()):
            rect = self.visualItemRect(self.item(row))
            # Above this item's line, or on its line and left of its centre.
            if position.y() < rect.top() or (position.y() <= rect.bottom() and position.x() < rect.center().x()):
                return row
        return self.count()

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        rows = sorted(index.row() for index in self.selectedIndexes())
        if not rows:
            return
        mime = QMimeData()
        mime.setData(_REORDER_MIME, b"")  # the dragged rows are the selection, which cannot change mid-drag
        drag = QDrag(self)
        drag.setMimeData(mime)
        icon_size = self.iconSize() if self.iconSize().isValid() else QSize(64, 64)
        drag.setPixmap(self.item(rows[0]).icon().pixmap(icon_size))
        drag.setHotSpot(QPoint(icon_size.width() // 2, icon_size.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)
        self._stop_drag_feedback()

    def dragEnterEvent(self, event) -> None:
        if self._is_reorder(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if not self._is_reorder(event):
            super().dragMoveEvent(event)
            return
        event.acceptProposedAction()
        position = event.position().toPoint()
        self._set_drop_row(self.insertion_row(position))
        self._update_edge_scroll(position)

    def dragLeaveEvent(self, event) -> None:
        self._stop_drag_feedback()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        if not self._is_reorder(event):
            super().dropEvent(event)
            return
        event.acceptProposedAction()
        row = self.insertion_row(event.position().toPoint())
        self._stop_drag_feedback()
        self.rows_moved.emit(sorted(index.row() for index in self.selectedIndexes()), row)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._drop_row is None or not self.count():
            return
        # The marker sits at the left edge of the page the dragged pages will precede,
        # or at the right edge of the last page when they go to the end.
        if self._drop_row < self.count():
            rect = self.visualItemRect(self.item(self._drop_row))
            x = rect.left()
        else:
            rect = self.visualItemRect(self.item(self.count() - 1))
            x = rect.right()
        painter = QPainter(self.viewport())
        painter.fillRect(x - _INDICATOR_WIDTH // 2, rect.top(), _INDICATOR_WIDTH, rect.height(), _INDICATOR_COLOR)

    def _is_reorder(self, event) -> bool:
        return event.source() is self and event.mimeData().hasFormat(_REORDER_MIME)

    def _set_drop_row(self, row: int | None) -> None:
        if row != self._drop_row:
            self._drop_row = row
            self.viewport().update()

    def _stop_drag_feedback(self) -> None:
        self._set_drop_row(None)
        self._edge_scroll_direction = 0
        self._edge_scroll_timer.stop()

    def _update_edge_scroll(self, position: QPoint) -> None:
        # Qt's own auto-scroll is bypassed because the drag events are handled here. A timer
        # keeps scrolling while the mouse rests at the edge: Windows reports drag moves only
        # when the mouse actually moves.
        if position.y() < _EDGE_SCROLL_MARGIN:
            self._edge_scroll_direction = -1
        elif position.y() > self.viewport().height() - _EDGE_SCROLL_MARGIN:
            self._edge_scroll_direction = 1
        else:
            self._edge_scroll_direction = 0
        if self._edge_scroll_direction and not self._edge_scroll_timer.isActive():
            self._scroll_step()
            self._edge_scroll_timer.start()
        elif not self._edge_scroll_direction:
            self._edge_scroll_timer.stop()

    def _scroll_step(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.value() + self._edge_scroll_direction * _EDGE_SCROLL_STEP)
