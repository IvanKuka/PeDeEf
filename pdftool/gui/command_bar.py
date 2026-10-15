"""A single horizontal command strip, scrollable with a mouse or trackpad."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QToolButton

_MIN_BUTTON_HEIGHT = 76


class CommandBar(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setToolTip("Ďalšie nástroje zobrazíte kolieskom myši alebo spodným posuvníkom.")

    def setWidget(self, widget) -> None:
        super().setWidget(widget)
        widget.installEventFilter(self)

    def fit_height(self) -> None:
        if self.widget() is not None:
            self._fit_buttons()
            self.setFixedHeight(self.widget().sizeHint().height()
                                + self.horizontalScrollBar().sizeHint().height() + 2 * self.frameWidth())

    def _fit_buttons(self) -> None:
        # One height for all buttons, fitted to the tallest label once styled: a fixed height cut
        # off two-line labels (diacritics, descenders) with larger system fonts or display scaling.
        buttons = self.widget().findChildren(QToolButton, "commandButton")
        height = max([_MIN_BUTTON_HEIGHT] + [button.sizeHint().height() for button in buttons])
        for button in buttons:
            button.setFixedHeight(height)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.fit_height()
        return super().eventFilter(watched, event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange):
            self.fit_height()

    def wheelEvent(self, event) -> None:
        bar = self.horizontalScrollBar()
        if bar.maximum() == 0:
            super().wheelEvent(event)
            return
        pixels = event.pixelDelta()
        angle = event.angleDelta()
        distance = (pixels.x() or pixels.y()) if not pixels.isNull() else (angle.x() or angle.y())
        bar.setValue(bar.value() - distance)
        event.accept()
