"""Parsing of human-friendly page range specifications such as "1-3, 5, 8-".

Users type 1-based page numbers; every function here returns 0-based page
indices, which is what the PDF libraries expect.
"""

from __future__ import annotations

from pdftool.plural import format_page_count


class PageRangeError(ValueError):
    """Raised when a page range specification is invalid for the given document.

    The message is user-facing (Slovak), so the GUI can display it directly.
    """


def parse_page_groups(spec: str, page_count: int) -> list[list[int]]:
    """Parse a comma-separated spec into groups of 0-based page indices.

    Each comma-separated part becomes one group, which lets the same syntax
    describe both a page selection and a split ("1-3, 4-6" -> two files).

    Supported parts: "N", "N-M" (a descending range such as "5-3" reverses the
    pages), "N-" (to the last page) and "-M" (from the first page).
    An empty spec selects the whole document as a single group.
    """
    if page_count < 1:
        raise PageRangeError("Dokument neobsahuje žiadne strany.")
    if not spec.strip():
        return [list(range(page_count))]

    # Empty parts are skipped so that a trailing comma ("1, 2,") is tolerated.
    groups = [
        _parse_part(part.strip(), page_count)
        for part in spec.split(",")
        if part.strip()
    ]
    if not groups:
        raise PageRangeError(f"Neplatný rozsah strán: „{spec.strip()}“.")
    return groups


def parse_page_ranges(spec: str, page_count: int) -> list[int]:
    """Parse a spec into a flat, ordered list of 0-based page indices."""
    return [page for group in parse_page_groups(spec, page_count) for page in group]


def chunk_pages(page_count: int, chunk_size: int) -> list[list[int]]:
    """Split all pages into consecutive groups of at most `chunk_size` pages."""
    if chunk_size < 1:
        raise PageRangeError("Počet strán v jednej časti musí byť aspoň 1.")
    return [
        list(range(start, min(start + chunk_size, page_count)))
        for start in range(0, page_count, chunk_size)
    ]


def _parse_part(part: str, page_count: int) -> list[int]:
    if "-" in part:
        start_text, _, end_text = part.partition("-")
        start = _parse_page_number(start_text, page_count) if start_text.strip() else 1
        end = _parse_page_number(end_text, page_count) if end_text.strip() else page_count
    else:
        start = end = _parse_page_number(part, page_count)

    step = 1 if end >= start else -1
    return list(range(start - 1, end - 1 + step, step))


def _parse_page_number(text: str, page_count: int) -> int:
    text = text.strip()
    # isascii() guards against Unicode digits such as "²", which isdigit() accepts but int() rejects.
    if not (text.isascii() and text.isdigit()):
        raise PageRangeError(f"Neplatné číslo strany: „{text}“.")
    number = int(text)
    if not 1 <= number <= page_count:
        raise PageRangeError(
            f"Strana {number} neexistuje – dokument má {format_page_count(page_count)}."
        )
    return number

