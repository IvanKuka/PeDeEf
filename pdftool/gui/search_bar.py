"""Search bar shown above the page grid (Ctrl+F)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class SearchBar(QWidget):
    """Query field with previous/next buttons; the owner does the searching.

    `search_requested(step)` asks for the next (1) or previous (-1) match,
    `select_all_requested` for selecting every matching page.
    """

    search_requested = Signal(int)
    select_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Hľadať text v dokumente (bez ohľadu na diakritiku)")
        self._edit.returnPressed.connect(lambda: self.search_requested.emit(1))
        previous_button = QPushButton("◀")
        previous_button.setToolTip("Predchádzajúci výskyt (Shift+Enter)")
        previous_button.setAccessibleName("Predchádzajúci výskyt")
        previous_button.clicked.connect(lambda: self.search_requested.emit(-1))
        next_button = QPushButton("▶")
        next_button.setToolTip("Ďalší výskyt (Enter)")
        next_button.setAccessibleName("Ďalší výskyt")
        next_button.clicked.connect(lambda: self.search_requested.emit(1))
        self._select_all_button = QPushButton("Vybrať všetky nájdené")
        self._select_all_button.clicked.connect(self.select_all_requested)
        self._status = QLabel()
        self._status.setObjectName("hint")
        close_button = QPushButton("✕")
        close_button.setToolTip("Zavrieť hľadanie (Esc)")
        close_button.setAccessibleName("Zavrieť hľadanie")
        close_button.clicked.connect(self.hide)

        QShortcut(QKeySequence("Shift+Return"), self._edit, activated=lambda: self.search_requested.emit(-1))
        QShortcut(QKeySequence("Shift+Enter"), self._edit, activated=lambda: self.search_requested.emit(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, stretch=1)
        layout.addWidget(previous_button)
        layout.addWidget(next_button)
        layout.addWidget(self._select_all_button)
        layout.addWidget(self._status)
        layout.addWidget(close_button)

    def query(self) -> str:
        return self._edit.text()

    def open(self) -> None:
        self.show()
        self._edit.setFocus()
        self._edit.selectAll()

    def show_status(self, text: str) -> None:
        self._status.setText(text)
