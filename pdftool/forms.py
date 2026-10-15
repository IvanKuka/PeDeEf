"""Interactive form fields (AcroForm): what can be filled in and where it lies on the pages.

Fields are read from the widget annotations of the pages themselves, not from
the document's form dictionary: pages are copied one by one when edited, which
keeps their widgets but not the form dictionary. Filled-in values are drawn
into the pages (see gui/form_filling.py), so they look the same in every viewer
and need no fonts from the form – PDF form fonts often lack Slovak letters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, DictionaryObject

from pdftool.operations import Box, PageRef, PdfToolError, cropped_box, open_pdf, page_box

# Field flags (PDF 32000-1:2008, tables 221, 226, 228, 230).
_READ_ONLY = 1 << 0
_MULTILINE = 1 << 12
_PASSWORD = 1 << 13
_RADIO = 1 << 15
_PUSHBUTTON = 1 << 16
_EDITABLE_CHOICE = 1 << 18
_FILE_SELECT = 1 << 20
# Annotation flags: hidden and not shown on screen.
_HIDDEN = 1 << 1
_NO_VIEW = 1 << 5
# Malformed files can have /Parent cycles.
_MAX_DEPTH = 32

_FONT_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s+Tf")

Color = tuple[float, float, float]  # RGB, each 0–1


class FieldKind(Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    CHOICE = "choice"


@dataclass(frozen=True)
class FieldWidget:
    """One place on a page where a field is shown; a field may have several."""

    row: int  # 0-based page of the document as edited
    annotation: int  # position in the page's annotation array
    # left, top, width, height as fractions of the visible page (after rotation and crop)
    area: tuple[float, float, float, float]
    turn: int  # clockwise degrees by which the field's text is turned on the visible page
    on_state: str = ""  # checkbox or radio button: the value it stands for when selected
    background: Color | None = None
    border: Color | None = None
    border_width: float = 1.0


@dataclass(frozen=True)
class FormField:
    name: str  # the fully qualified field name, unique in the document
    label: str  # what to show to the user: the field's description if it has one
    kind: FieldKind
    # TEXT and CHOICE: the text; CHECKBOX: whether checked; RADIO: the selected on-state or "".
    value: str | bool
    widgets: tuple[FieldWidget, ...]
    options: tuple[str, ...] = ()  # CHOICE and RADIO
    multiline: bool = False
    read_only: bool = False
    editable_choice: bool = False  # a combo box that also accepts own text
    font_size: float = 0.0  # points; 0 means fit the field
    alignment: int = 0  # 0 left, 1 centred, 2 right


def read_form_fields(pages: Sequence[PageRef]) -> list[FormField]:
    """The fillable fields on `pages`, in the order of their first widget.

    Signature, push-button, password and file fields are left out: they cannot be
    filled with text. A page that appears several times shows its fields each time.
    """
    readers: dict[Path, PdfReader] = {}
    found: dict[str, _FieldBuilder] = {}
    for row, ref in enumerate(pages):
        path = Path(ref.path)
        if path not in readers:
            readers[path] = open_pdf(path)
        try:
            page = readers[path].pages[ref.index]
            rotation = (page.rotation + ref.rotation) % 360
            box = page_box(page.cropbox)
            if ref.crop is not None:
                box = cropped_box(box, rotation, ref.crop)
            annotations = page.get("/Annots")
            annotations = annotations.get_object() if annotations is not None else ArrayObject()
            for position, annotation in enumerate(annotations):
                widget = annotation.get_object()
                if isinstance(widget, DictionaryObject):
                    _collect(found, widget, row, position, box, rotation)
        except (PdfReadError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise PdfToolError(f"Formulárové polia súboru „{path.name}“ sa nepodarilo načítať: {exc}") from exc
    return [builder.build() for builder in found.values()]


@dataclass
class _FieldBuilder:
    name: str
    label: str
    kind: FieldKind
    flags: int
    value: str | bool
    options: list[str]
    font_size: float
    alignment: int
    widgets: list[FieldWidget]

    def build(self) -> FormField:
        options = self.options
        if self.kind is FieldKind.RADIO:
            options = list(dict.fromkeys(widget.on_state for widget in self.widgets))
        return FormField(
            name=self.name,
            label=self.label,
            kind=self.kind,
            value=self.value,
            widgets=tuple(self.widgets),
            options=tuple(options),
            multiline=self.kind is FieldKind.TEXT and bool(self.flags & _MULTILINE),
            read_only=bool(self.flags & _READ_ONLY),
            editable_choice=self.kind is FieldKind.CHOICE and bool(self.flags & _EDITABLE_CHOICE),
            font_size=self.font_size,
            alignment=self.alignment,
        )


def _collect(
    found: dict[str, _FieldBuilder], widget: DictionaryObject, row: int, position: int, box: Box, rotation: int
) -> None:
    if widget.get("/Subtype") != "/Widget" or "/Rect" not in widget or int(widget.get("/F", 0)) & (_HIDDEN | _NO_VIEW):
        return
    field_type = _inherited(widget, "/FT")
    flags = int(_inherited(widget, "/Ff") or 0)
    kind = _kind(field_type, flags)
    name = _full_name(widget)
    if kind is None or not name:
        return
    on_state = _on_state(widget) if kind in (FieldKind.CHECKBOX, FieldKind.RADIO) else ""
    characteristics = widget.get("/MK")
    characteristics = characteristics.get_object() if characteristics is not None else DictionaryObject()
    border_style = widget.get("/BS")
    border_width = float(border_style.get_object().get("/W", 1)) if border_style is not None else 1.0
    area, turn = _visible_area(widget, box, rotation, int(characteristics.get("/R", 0)))
    placed = FieldWidget(
        row=row,
        annotation=position,
        area=area,
        turn=turn,
        on_state=on_state,
        background=_color(characteristics.get("/BG")),
        border=_color(characteristics.get("/BC")),
        border_width=border_width,
    )
    if name in found:
        found[name].widgets.append(placed)
        return
    found[name] = _FieldBuilder(
        name=name,
        label=str(_inherited(widget, "/TU") or name),
        kind=kind,
        flags=flags,
        value=_value(kind, _inherited(widget, "/V"), widget),
        options=_options(_inherited(widget, "/Opt")) if kind is FieldKind.CHOICE else [],
        font_size=_font_size(_inherited(widget, "/DA")),
        alignment=int(_inherited(widget, "/Q") or 0),
        widgets=[placed],
    )


def _kind(field_type, flags: int) -> FieldKind | None:
    if field_type == "/Tx" and not flags & (_PASSWORD | _FILE_SELECT):
        return FieldKind.TEXT
    if field_type == "/Btn" and not flags & _PUSHBUTTON:
        return FieldKind.RADIO if flags & _RADIO else FieldKind.CHECKBOX
    if field_type == "/Ch":
        return FieldKind.CHOICE
    return None  # signatures and anything unknown


def _inherited(widget: DictionaryObject, key: str):
    """An attribute of the field, which may be set on the widget or any of its parent fields."""
    node = widget
    for _ in range(_MAX_DEPTH):
        if key in node:
            return node[key].get_object()
        parent = node.get("/Parent")
        if parent is None:
            return None
        node = parent.get_object()
    return None


def _full_name(widget: DictionaryObject) -> str:
    parts = []
    node = widget
    for _ in range(_MAX_DEPTH):
        if "/T" in node:
            parts.append(str(node["/T"].get_object()))
        parent = node.get("/Parent")
        if parent is None:
            break
        node = parent.get_object()
    return ".".join(reversed(parts))


def _on_state(widget: DictionaryObject) -> str:
    """The appearance name a checkbox or radio button has when selected (e.g. "Yes")."""
    appearances = widget.get("/AP")
    normal = appearances.get_object().get("/N") if appearances is not None else None
    normal = normal.get_object() if normal is not None else None
    if isinstance(normal, DictionaryObject):
        for state in normal:
            if state != "/Off":
                return str(state).removeprefix("/")
    return "Yes"


def _value(kind: FieldKind, value, widget: DictionaryObject) -> str | bool:
    if kind is FieldKind.CHECKBOX:
        state = value if value is not None else widget.get("/AS")
        return state is not None and str(state) != "/Off"
    if kind is FieldKind.RADIO:
        return "" if value is None or str(value) == "/Off" else str(value).removeprefix("/")
    if isinstance(value, ArrayObject):  # a list box with several selected entries
        value = value[0] if value else None
    return "" if value is None else str(value)


def _options(options) -> list[str]:
    result = []
    for option in options or ():
        option = option.get_object()
        # An option is either its text or a pair [export value, text shown].
        if isinstance(option, ArrayObject):
            option = option[-1].get_object() if option else ""
        result.append(str(option))
    return result


def _font_size(appearance) -> float:
    match = _FONT_SIZE.search(str(appearance or ""))
    return float(match.group(1)) if match else 0.0


def _color(components) -> Color | None:
    values = [float(value) for value in components.get_object()] if components is not None else []
    if len(values) == 1:
        return values[0], values[0], values[0]
    if len(values) == 3:
        return values[0], values[1], values[2]
    if len(values) == 4:
        cyan, magenta, yellow, black = values
        return tuple((1 - min(1.0, value + black)) for value in (cyan, magenta, yellow))  # type: ignore[return-value]
    return None  # no colour: transparent


def _visible_area(
    widget: DictionaryObject, box: Box, rotation: int, appearance_rotation: int
) -> tuple[tuple[float, float, float, float], int]:
    """The widget's rectangle as fractions of the visible page, and the clockwise turn of its text.

    A viewer shows the page's crop box turned clockwise by `rotation`; this maps page
    coordinates to that view (origin top left, y down), as `apply_overlay` does in reverse.
    """
    left, bottom, right, top = box
    width, height = right - left, top - bottom
    if rotation % 180:
        width, height = height, width
    x0, y0, x1, y1 = (float(value) for value in widget["/Rect"])
    corners = []
    for x, y in ((x0, y0), (x1, y1)):
        # (u, v): position on the visible page with the origin at its bottom left.
        u, v = {
            0: (x - left, y - bottom),
            90: (y - bottom, right - x),
            180: (right - x, top - y),
            270: (top - y, x - left),
        }[rotation]
        corners.append((u, height - v))
    (a_x, a_y), (b_x, b_y) = corners
    area = (min(a_x, b_x) / width, min(a_y, b_y) / height, abs(a_x - b_x) / width, abs(a_y - b_y) / height)
    # The page's text runs along its x axis, which the viewer turns with the page; a widget
    # rotated counter-clockwise (/MK /R) usually compensates for the page's own rotation.
    return area, (rotation - appearance_rotation) % 360
