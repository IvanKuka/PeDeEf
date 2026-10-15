"""Dialog listing the pages that look blank, for the user to confirm before they are removed."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdftool.gui.blank_pages import SENSITIVITY_LEVELS, PageInk
from pdftool.gui.thumbnails import thumbnail_icon
from pdftool.plural import format_page_count, format_page_count_genitive

_ROW_ROLE = Qt.ItemDataRole.UserRole
_ICON_SIDE = 120


class BlankPagesDialog(QDialog):
    def __init__(self, measured: Sequence[PageInk], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prázdne strany")
        self.resize(760, 560)
        self._measured = list(measured)
        # Pages the user unticked stay unticked when the sensitivity changes.
        self._unticked: set[int] = set()

        self._level_combo = QComboBox()
        for label, threshold in SENSITIVITY_LEVELS:
            self._level_combo.addItem(label, threshold)
        self._level_combo.currentIndexChanged.connect(self._show_candidates)
        level_row = QHBoxLayout()
        level_row.addWidget(QLabel("Považovať za prázdne:"))
        level_row.addWidget(self._level_combo, stretch=1)

        hint = QLabel(
            "Ide o odhad podľa vzhľadu strán. Skontrolujte náhľady a odznačte strany, ktoré chcete ponechať. "
            "Odstránenie sa dá vrátiť tlačidlom Späť."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        self._list = QListWidget()
        self._list.setViewMode(QListView.ViewMode.IconMode)
        self._list.setMovement(QListView.Movement.Static)
        self._list.setResizeMode(QListView.ResizeMode.Adjust)
        self._list.setIconSize(QSize(_ICON_SIDE, _ICON_SIDE))
        self._list.setGridSize(QSize(_ICON_SIDE + 40, _ICON_SIDE + 48))
        self._list.itemChanged.connect(self._on_item_changed)
        self._empty_label = QLabel("Žiadna strana nevyzerá prázdna. Skúste voľnejšie nastavenie.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._unrenderable = QLabel()
        self._unrenderable.setObjectName("hint")
        unrenderable = sum(1 for page in self._measured if page.ink_ratio is None)
        self._unrenderable.setText(
            f"Neposúdené, lebo sa nedali vykresliť: {format_page_count(unrenderable)}" if unrenderable else ""
        )
        self._unrenderable.setVisible(bool(unrenderable))

        self._buttons = QDialogButtonBox()
        self._buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._remove_button = self._buttons.addButton("Odstrániť", QDialogButtonBox.ButtonRole.AcceptRole)
        self._remove_button.setObjectName("primary")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(level_row)
        layout.addWidget(hint)
        layout.addWidget(self._list, stretch=1)
        layout.addWidget(self._empty_label, stretch=1)
        layout.addWidget(self._unrenderable)
        layout.addWidget(self._buttons)
        self._show_candidates()

    def rows_to_remove(self) -> list[int]:
        """Document rows of the ticked candidates, ascending."""
        return sorted(
            self._list.item(index).data(_ROW_ROLE)
            for index in range(self._list.count())
            if self._list.item(index).checkState() == Qt.CheckState.Checked
        )

    def _show_candidates(self) -> None:
        threshold = self._level_combo.currentData()
        self._list.blockSignals(True)
        self._list.clear()
        for row, page in enumerate(self._measured):
            if page.ink_ratio is None or page.ink_ratio > threshold:
                continue
            percent = f"{page.ink_ratio * 100:.3f}".replace(".", ",")
            item = QListWidgetItem(thumbnail_icon(page.preview, _ICON_SIDE), f"Strana {row + 1}\n{percent} % obsahu")
            item.setData(_ROW_ROLE, row)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked if row in self._unticked else Qt.CheckState.Checked)
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._list.setVisible(self._list.count() > 0)
        self._empty_label.setVisible(self._list.count() == 0)
        self._update_button()

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        row = item.data(_ROW_ROLE)
        if item.checkState() == Qt.CheckState.Checked:
            self._unticked.discard(row)
        else:
            self._unticked.add(row)
        self._update_button()

    def _update_button(self) -> None:
        count = len(self.rows_to_remove())
        self._remove_button.setEnabled(count > 0)
        self._remove_button.setText(f"Odstrániť {format_page_count_genitive(count)}" if count else "Odstrániť")
