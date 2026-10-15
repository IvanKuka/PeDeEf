"""Page numbers and text stamps: what to write on which page (no drawing, no GUI).

The text layer itself is drawn by the GUI layer (see gui/stamp_layer.py) and
merged into the document by `operations.apply_overlay`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

PAGE_NUMBER_TOKEN = "{n}"
PAGE_TOTAL_TOKEN = "{total}"
DATE_TOKEN = "{date}"


class Position(Enum):
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    CENTER = "center"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


@dataclass(frozen=True)
class StampSpec:
    """A text written on a range of pages, e.g. "{n} / {total}" at the bottom centre."""

    template: str
    position: Position = Position.BOTTOM_CENTER
    font_size: int = 11  # points
    first_number: int = 1


def stamp_texts(spec: StampSpec, page_count: int, today: date | None = None) -> list[str]:
    """The text for each of `page_count` stamped pages, in order.

    Numbering counts only the stamped pages, starting at `first_number`, so a
    range such as pages 3–10 can be numbered 1–8; `{total}` is the last number.
    Unknown text in braces is kept as typed.
    """
    today = today or date.today()
    last_number = spec.first_number + page_count - 1
    texts = []
    for offset in range(page_count):
        text = spec.template.replace(PAGE_NUMBER_TOKEN, str(spec.first_number + offset))
        text = text.replace(PAGE_TOTAL_TOKEN, str(last_number))
        texts.append(text.replace(DATE_TOKEN, today.strftime("%d. %m. %Y")))
    return texts
