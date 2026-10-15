"""Dialog for filling in a document's form fields, with a preview of the page being filled."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QSizeF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdftool.forms import FieldKind, FormField
from pdftool.gui.form_filling import FieldValue, changed_fields, draw_field, widget_rect
from pdftool.gui.widgets import PageCanvas
from pdftool.gui.zoomed_page import ZoomedPageView
from pdftool.operations import PageRef
from pdftool.plural import format_count

_NOT_SELECTED = "(nevybrané)"


class _FieldCanvas(PageCanvas):
    clicked = Signal(QPointF)  # fractions of the page

    def __init__(self) -> None:
        super().__init__(420, 560)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("Náhľad strany s formulárovými poľami")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        fraction = self.page_fraction(event.position())
        if fraction is not None:
            self.clicked.emit(fraction)


class FormDialog(QDialog):
    def __init__(
        self,
        pages: Sequence[PageRef],
        fields: Sequence[FormField],
        row: int,
        digitally_signed: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vyplniť formulár")
        self.resize(1150, 800)
        self._pages = list(pages)
        self._fields = list(fields)
        self._inputs: dict[str, QWidget] = {}
        self._current: FormField | None = None  # the field being edited, highlighted in the preview

        explanation = QLabel(
            "Vyplnené hodnoty sa vpíšu natrvalo do strán: v novom súbore už vyplnené polia nebude "
            "možné meniť, zato budú vyzerať rovnako v každom programe aj s diakritikou. "
            "Polia, ktoré nezmeníte, zostanú tak, ako sú."
        )
        explanation.setWordWrap(True)
        signed_warning = QLabel("Dokument je digitálne podpísaný. V novom súbore už digitálny podpis nebude platný.")
        signed_warning.setObjectName("error")
        signed_warning.setWordWrap(True)
        signed_warning.setVisible(digitally_signed)

        field_form = QFormLayout()
        for field in self._fields:
            editor = self._editor_for(field)
            self._inputs[field.name] = editor
            label = QLabel(field.label)
            label.setWordWrap(True)
            label.setToolTip(field.name)
            label.setBuddy(editor)
            field_form.addRow(label, editor)
        fields_widget = QWidget()
        fields_widget.setLayout(field_form)
        self._fields_scroll = QScrollArea()
        self._fields_scroll.setWidget(fields_widget)
        self._fields_scroll.setWidgetResizable(True)

        self._page_spin = QSpinBox()
        self._page_spin.setRange(1, len(self._pages))
        self._page_spin.setValue(row + 1)
        self._page_spin.setSuffix(f" z {len(self._pages)}")
        self._canvas = _FieldCanvas()
        self._canvas.clicked.connect(self._focus_field_at)
        self._view = ZoomedPageView(self._canvas)
        page_form = QFormLayout()
        page_form.addRow("Strana:", self._page_spin)
        page_form.addRow("Priblíženie:", self._view.zoom_combo)
        preview_hint = QLabel("Kliknutím na pole v náhľade prejdete na jeho vyplnenie.")
        preview_hint.setObjectName("hint")
        preview_hint.setWordWrap(True)

        self._summary = QLabel()
        save_hint = QLabel("Zdrojové súbory sa nezmenia.")
        save_hint.setObjectName("hint")

        buttons = QDialogButtonBox()
        buttons.addButton("Zrušiť", QDialogButtonBox.ButtonRole.RejectRole)
        self._accept_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        settings_column = QVBoxLayout()
        settings_column.addWidget(explanation)
        settings_column.addWidget(signed_warning)
        settings_column.addWidget(self._fields_scroll, stretch=1)
        settings_column.addWidget(self._summary)
        settings_column.addWidget(save_hint)
        settings_widget = QWidget()
        settings_widget.setLayout(settings_column)
        settings_widget.setMinimumWidth(360)
        settings_widget.setMaximumWidth(460)
        preview_column = QVBoxLayout()
        preview_column.addLayout(page_form)
        preview_column.addWidget(preview_hint)
        preview_column.addWidget(self._view, stretch=1)
        columns = QHBoxLayout()
        columns.addWidget(settings_widget)
        columns.addLayout(preview_column, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(columns, stretch=1)
        layout.addWidget(buttons)

        self._page_spin.valueChanged.connect(self._update_state)
        self._update_state()

    def values(self) -> dict[str, FieldValue]:
        """The value of every field as currently entered (changed or not)."""
        return {field.name: self._value_of(field) for field in self._fields}

    def done(self, result: int) -> None:
        self._view.close_document()
        super().done(result)

    def _editor_for(self, field: FormField) -> QWidget:
        editor: QWidget
        if field.kind is FieldKind.CHECKBOX:
            editor = QCheckBox()
            editor.setChecked(bool(field.value))
            editor.toggled.connect(self._update_state)
        elif field.kind in (FieldKind.RADIO, FieldKind.CHOICE):
            editor = QComboBox()
            editor.setEditable(field.editable_choice)
            editor.addItem(_NOT_SELECTED, "")
            for option in field.options:
                editor.addItem(option, option)
            if field.value and editor.findData(field.value) < 0:
                # A value outside the options (e.g. an export value) stays selectable, so that
                # opening the dialog does not count as changing it.
                editor.addItem(str(field.value), field.value)
            editor.setCurrentIndex(editor.findData(field.value))
            editor.currentIndexChanged.connect(self._update_state)
            editor.editTextChanged.connect(self._update_state)
        elif field.multiline:
            editor = QPlainTextEdit(str(field.value))
            editor.setFixedHeight(72)
            editor.setTabChangesFocus(True)
            editor.textChanged.connect(self._update_state)
        else:
            editor = QLineEdit(str(field.value))
            editor.textChanged.connect(self._update_state)
        editor.setAccessibleName(field.label)
        if field.read_only:
            editor.setEnabled(False)
            editor.setToolTip("Pole je len na čítanie.")
        # Focusing a field shows its page; FocusIn is filtered, as these widgets have no focus signal.
        editor.installEventFilter(self)
        return editor

    def _value_of(self, field: FormField) -> FieldValue:
        editor = self._inputs[field.name]
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, QComboBox):
            if editor.isEditable():
                text = editor.currentText()
                return "" if text == _NOT_SELECTED else text
            return editor.currentData()
        if isinstance(editor, QPlainTextEdit):
            return editor.toPlainText()
        return editor.text()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == event.Type.FocusIn:
            for field in self._fields:
                if self._inputs[field.name] is watched:
                    self._show_field(field)
                    break
        return super().eventFilter(watched, event)

    def _show_field(self, field: FormField) -> None:
        self._current = field
        rows = [widget.row for widget in field.widgets]
        if self._page_spin.value() - 1 not in rows:
            self._page_spin.setValue(rows[0] + 1)  # redraws the preview
        else:
            self._update_state()

    def _focus_field_at(self, fraction: QPointF) -> None:
        row = self._page_spin.value() - 1
        for field in reversed(self._fields):
            for widget in field.widgets:
                left, top, width, height = widget.area
                if widget.row == row and left <= fraction.x() <= left + width and top <= fraction.y() <= top + height:
                    editor = self._inputs[field.name]
                    self._fields_scroll.ensureWidgetVisible(editor)
                    editor.setFocus()
                    self._show_field(field)
                    return

    def _update_state(self) -> None:
        values = self.values()
        changed = changed_fields(self._fields, values)
        self._accept_button.setEnabled(bool(changed))
        self._summary.setText(
            f"Zmenené: {format_count(len(changed), 'pole', 'polia', 'polí')}." if changed else "Zatiaľ nie je nič zmenené."
        )
        row = self._page_spin.value() - 1
        placed = [(field, widget) for field in self._fields for widget in field.widgets if widget.row == row]
        changed_names = {field.name for field in changed}
        current = self._current

        def draw(painter: QPainter, size: QSizeF) -> None:
            for field, widget in placed:
                if field.name not in changed_names:
                    # Unchanged fields keep their own look in the file, which the preview cannot
                    # show (QtPdf leaves form fields out), so they are only tinted.
                    painter.fillRect(widget_rect(size, widget), QColor(37, 99, 235, 28))
                draw_field(painter, size, field, widget, values[field.name])
            for field, widget in placed:
                if field is current:
                    painter.setPen(QPen(QColor("#2563eb"), 0))  # cosmetic pen: one pixel at any zoom
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(widget_rect(size, widget))

        self._view.show_page(self._pages[row], draw)
