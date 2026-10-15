"""Finding pages by their text (no GUI dependencies).

Matching ignores letter case and diacritics, so "zilina" finds "Žilina": people
often type without diacritics, and PDFs sometimes store letters decomposed.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence


def normalize(text: str) -> str:
    """Lower-case `text`, drop diacritics and collapse whitespace (line breaks included)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.split())


def find_pages(normalized_texts: Sequence[str], query: str) -> list[int]:
    """Positions of the pages whose text contains `query`; an empty query finds nothing.

    The page texts must already be passed through `normalize`, so that callers can
    normalize each page once and search it many times.
    """
    needle = normalize(query)
    if not needle:
        return []
    return [position for position, text in enumerate(normalized_texts) if needle in text]


def next_match(matches: Sequence[int], current: int, step: int) -> int:
    """The match after (`step` 1) or before (`step` -1) position `current`, wrapping around.

    `current` may be -1 when nothing is selected; the search then starts at the beginning
    (or, going back, at the end).
    """
    if not matches:
        raise ValueError("No matches to move between")
    if step > 0:
        return next((match for match in matches if match > current), matches[0])
    return next((match for match in reversed(matches) if match < current), matches[-1])
