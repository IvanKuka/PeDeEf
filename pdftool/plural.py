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


def format_page_count_genitive(count: int) -> str:
    """E.g. "1 strany", "3 strán" – the form used after nouns such as "Odstránenie"."""
    return format_count(count, "strany", "strán", "strán")


def format_page_count_locative(count: int) -> str:
    """E.g. "1 strane", "3 stranách" – the form used after "na"."""
    return format_count(count, "strane", "stranách", "stranách")


def format_file_count(count: int) -> str:
    return format_count(count, "súbor", "súbory", "súborov")
