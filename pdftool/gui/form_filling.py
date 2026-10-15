"""Filling in form fields: the values are drawn into the pages and the filled fields removed.

Drawing the values with Qt (which embeds the font) keeps Slovak letters intact in
every viewer, unlike appearance streams built from the form's own fonts. The
result is a flattened form: filled fields are no longer editable, untouched
fields stay as they were.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen

from pdftool.forms import FieldKind, FieldWidget, FormField
from pdftool.gui.stamp_layer import stamp_font, write_pages_with_overlay
from pdftool.operations import DocumentInfo, PageRef, PdfToolError

FieldValue = str | bool
# Space between the field's edge and its text, in points (as Acrobat leaves).
_PADDING = 2.0
_MAX_AUTO_FONT_SIZE = 12.0
_MIN_FONT_SIZE = 4.0
_MULTILINE_AUTO_FONT_SIZE = 10.0
_ALIGNMENT = {0: Qt.AlignmentFlag.AlignLeft, 1: Qt.AlignmentFlag.AlignHCenter, 2: Qt.AlignmentFlag.AlignRight}


def changed_fields(fields: Sequence[FormField], values: Mapping[str, FieldValue]) -> list[FormField]:
    """The fields whose value in `values` differs from the document; read-only fields never change."""
    return [
        field for field in fields
        if not field.read_only and field.name in values and values[field.name] != field.value
    ]


def widget_rect(page_size: QSizeF, widget: FieldWidget) -> QRectF:
    left, top, width, height = widget.area
    return QRectF(
        left * page_size.width(), top * page_size.height(), width * page_size.width(), height * page_size.height()
    )


def draw_field(painter: QPainter, page_size: QSizeF, field: FormField, widget: FieldWidget, value: FieldValue) -> None:
    """Draw one widget of `field` with `value`, in place of the removed field, on a page of `page_size` points."""
    rect = widget_rect(page_size, widget)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if widget.background is not None:
        painter.fillRect(rect, QColor.fromRgbF(*widget.background))
    if widget.border is not None and widget.border_width > 0:
        pen = QPen(QColor.fromRgbF(*widget.border), widget.border_width)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        inset = widget.border_width / 2
        painter.drawRect(rect.adjusted(inset, inset, -inset, -inset))
    # The field's own coordinates: text runs along x even on a turned page.
    painter.translate(rect.center())
    painter.rotate(widget.turn)
    size = rect.size() if widget.turn % 180 == 0 else rect.size().transposed()
    local = QRectF(QPointF(-size.width() / 2, -size.height() / 2), size)
    painter.setClipRect(local)
    if field.kind is FieldKind.CHECKBOX:
        if value:
            _draw_check(painter, local)
    elif field.kind is FieldKind.RADIO:
        if value and value == widget.on_state:
            diameter = min(local.width(), local.height()) * 0.45
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("black"))
            painter.drawEllipse(local.center(), diameter / 2, diameter / 2)
    elif value:
        _draw_text(painter, local, field, str(value))
    painter.restore()


def _draw_check(painter: QPainter, area: QRectF) -> None:
    side = min(area.width(), area.height()) * 0.7
    square = QRectF(area.center().x() - side / 2, area.center().y() - side / 2, side, side)
    path = QPainterPath(QPointF(square.left(), square.top() + side * 0.55))
    path.lineTo(square.left() + side * 0.38, square.bottom() - side * 0.08)
    path.lineTo(square.right(), square.top() + side * 0.1)
    pen = QPen(QColor("black"), max(side * 0.13, 0.5))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _draw_text(painter: QPainter, area: QRectF, field: FormField, text: str) -> None:
    inner = area.adjusted(_PADDING, _PADDING / 2, -_PADDING, -_PADDING / 2)
    font = stamp_font()
    flags = _ALIGNMENT.get(field.alignment, Qt.AlignmentFlag.AlignLeft)
    if field.multiline:
        size = field.font_size or _MULTILINE_AUTO_FONT_SIZE
        flags |= Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
    else:
        text = " ".join(text.splitlines())
        size = field.font_size or min(_MAX_AUTO_FONT_SIZE, max(inner.height() * 0.75, _MIN_FONT_SIZE))
        flags |= Qt.AlignmentFlag.AlignVCenter
        if not field.font_size:
            # Like Acrobat's automatic size: shrink a long value until it fits the field's width.
            font.setPixelSize(round(size))
            width = QFontMetricsF(font).horizontalAdvance(text)
            if width > inner.width() > 0:
                size = max(_MIN_FONT_SIZE, size * inner.width() / width)
    font.setPixelSize(max(1, round(size)))  # pixel = point, see stamp_layer.draw_stamp
    painter.setFont(font)
    painter.setPen(QColor("black"))
    painter.drawText(inner, int(flags), text)


def write_filled_pdf(
    pages: Sequence[PageRef],
    fields: Sequence[FormField],
    values: Mapping[str, FieldValue],
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` to `output_path` with the changed `values` drawn in place of their fields."""
    changed = changed_fields(fields, values)
    if not changed:
        raise PdfToolError("Žiadne pole nebolo zmenené.")
    by_row: dict[int, list[tuple[FormField, FieldWidget]]] = {}
    for field in changed:
        for widget in field.widgets:
            by_row.setdefault(widget.row, []).append((field, widget))
    rows = sorted(by_row)

    def draw(painter: QPainter, size: QSizeF, number: int) -> None:
        for field, widget in by_row[rows[number]]:
            draw_field(painter, size, field, widget, values[field.name])

    write_pages_with_overlay(
        pages,
        rows,
        draw,
        output_path,
        password,
        info,
        removed_widgets={row: [widget.annotation for _, widget in placed] for row, placed in by_row.items()},
    )
