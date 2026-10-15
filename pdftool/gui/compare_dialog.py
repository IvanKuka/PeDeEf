"""Dialog showing the result of comparing two documents page by page."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.compare import PagePair, Verdict

_DESCRIPTIONS = {
    Verdict.EQUAL: "zhodná",
    Verdict.DIFFERENT: "rozdielna",
    Verdict.OTHER_SIZE: "iný rozmer strany",
    Verdict.ONLY_FIRST: "len v tomto dokumente",
    Verdict.ONLY_SECOND: "len v porovnávanom",
}
_MARKS = {Verdict.EQUAL: "=", Verdict.DIFFERENT: "≠", Verdict.OTHER_SIZE: "≠", Verdict.ONLY_FIRST: "+", Verdict.ONLY_SECOND: "−"}


class CompareDialog(QDialog):
    def __init__(self, pairs: Sequence[PagePair], first_name: str, second_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Porovnanie dokumentov")
        self.resize(1100, 760)
        self._pairs = list(pairs)

        differences = sum(1 for pair in self._pairs if pair.differs)
        summary = QLabel(
            "Dokumenty vyzerajú rovnako." if not differences else f"Rozdielne strany: {differences} z {len(self._pairs)}"
        )
        summary.setObjectName("fileTitle")
        limits = QLabel(
            "Porovnávajú sa strany na rovnakých pozíciách: ak bola strana vložená alebo odstránená, ďalšie strany "
            "sa ukážu ako rozdielne. Vizuálny rozdiel nemusí znamenať zmenu obsahu."
        )
        limits.setObjectName("hint")
        limits.setWordWrap(True)

        self._list = QListWidget()
        self._list.setFixedWidth(240)
        for pair in self._pairs:
            text = f"{_MARKS[pair.verdict]}  Strana {pair.position + 1} – {_DESCRIPTIONS[pair.verdict]}"
            if pair.verdict is Verdict.DIFFERENT:
                # Two decimals: a changed word is only a few hundredths of a percent of the page.
                text += f" ({pair.changed_ratio * 100:.2f} %)".replace(".", ",")
            self._list.addItem(QListWidgetItem(text))
        self._list.currentRowChanged.connect(self._show)

        self._first_label, self._second_label = self._page_label(), self._page_label()
        self._first_title = QLabel(f"Tento dokument: {first_name}  (zmeny červenou)")
        self._second_title = QLabel(f"Porovnávaný: {second_name}")

        previous_button = QPushButton("◀  Predchádzajúci rozdiel")
        previous_button.setToolTip("Shift+F3")
        previous_button.clicked.connect(lambda: self.go_to_difference(-1))
        next_button = QPushButton("Ďalší rozdiel  ▶")
        next_button.setToolTip("F3")
        next_button.clicked.connect(lambda: self.go_to_difference(1))
        for button in (previous_button, next_button):
            button.setEnabled(bool(differences))
        QShortcut(QKeySequence("F3"), self, activated=lambda: self.go_to_difference(1))
        QShortcut(QKeySequence("Shift+F3"), self, activated=lambda: self.go_to_difference(-1))
        close_button = QPushButton("Zavrieť")
        close_button.clicked.connect(self.accept)

        pages = QHBoxLayout()
        for title, label in ((self._first_title, self._first_label), (self._second_title, self._second_label)):
            column = QVBoxLayout()
            column.addWidget(title)
            column.addWidget(label, stretch=1)
            pages.addLayout(column, stretch=1)
        body = QHBoxLayout()
        body.addWidget(self._list)
        body.addLayout(pages, stretch=1)
        buttons = QHBoxLayout()
        buttons.addWidget(previous_button)
        buttons.addWidget(next_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(limits)
        layout.addLayout(body, stretch=1)
        layout.addLayout(buttons)

        first_difference = next((index for index, pair in enumerate(self._pairs) if pair.differs), 0)
        self._list.setCurrentRow(first_difference)

    def current_position(self) -> int:
        return self._list.currentRow()

    def go_to_difference(self, step: int) -> None:
        """Select the next (1) or previous (-1) differing page, wrapping around."""
        count = len(self._pairs)
        for offset in range(1, count + 1):
            index = (self._list.currentRow() + step * offset) % count
            if self._pairs[index].differs:
                self._list.setCurrentRow(index)
                return

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._show(self._list.currentRow())

    def _show(self, index: int) -> None:
        if not 0 <= index < len(self._pairs):
            return
        pair = self._pairs[index]
        for label, image in ((self._first_label, pair.first), (self._second_label, pair.second)):
            if image is None:
                label.setPixmap(QPixmap())
                label.setText("(strana chýba)")
                continue
            target = label.size() - QSize(8, 8)
            label.setPixmap(
                QPixmap.fromImage(image).scaled(
                    target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )

    @staticmethod
    def _page_label() -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background: #9ca3af;")
        label.setMinimumSize(200, 200)
        # The label must not grow to the pixmap's size, or the dialog would keep growing on resize.
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        return label
