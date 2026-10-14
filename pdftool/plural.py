"""Slovak plural forms for user-facing counts."""

from __future__ import annotations


def format_count(count: int, one: str, few: str, many: str) -> str:
    """Return e.g. "1 strana", "3 strany", "5 strán" – Slovak uses separate forms for 1, 2–4 and the rest."""
    if count == 1:
        word = one
    elif 2 <= count <= 4:
        word = few
    else:
        word = many
    return f"{count} {word}"


def format_page_count(count: int) -> str:
    return format_count(count, "strana", "strany", "strán")


def format_file_count(count: int) -> str:
    return format_count(count, "súbor", "súbory", "súborov")
