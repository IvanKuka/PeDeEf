import pytest

from pdftool.page_ranges import (
    PageRangeError,
    chunk_pages,
    parse_page_groups,
    parse_page_ranges,
)
from pdftool.plural import format_file_count, format_page_count


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("", [0, 1, 2, 3, 4]),
        ("   ", [0, 1, 2, 3, 4]),
        ("1", [0]),
        ("1-3", [0, 1, 2]),
        ("1-3, 5", [0, 1, 2, 4]),
        ("4-", [3, 4]),
        ("-2", [0, 1]),
        ("5-3", [4, 3, 2]),
        ("2, 2", [1, 1]),
        (" 1 - 2 ,", [0, 1]),
    ],
)
def test_parse_page_ranges(spec, expected):
    assert parse_page_ranges(spec, page_count=5) == expected


def test_parse_page_groups_keeps_parts_separate():
    assert parse_page_groups("1-2, 3, 4-", page_count=5) == [[0, 1], [2], [3, 4]]


def test_empty_spec_is_single_group_of_all_pages():
    assert parse_page_groups("", page_count=3) == [[0, 1, 2]]


@pytest.mark.parametrize("spec", ["0", "6", "1-6", "a", "1-2-3", "²", "1.5", ",", "-x"])
def test_invalid_specs_raise(spec):
    with pytest.raises(PageRangeError):
        parse_page_ranges(spec, page_count=5)


def test_document_without_pages_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("", page_count=0)


def test_chunk_pages():
    assert chunk_pages(5, 2) == [[0, 1], [2, 3], [4]]
    assert chunk_pages(2, 10) == [[0, 1]]


def test_chunk_pages_rejects_non_positive_size():
    with pytest.raises(PageRangeError):
        chunk_pages(5, 0)


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "1 strana"), (2, "2 strany"), (4, "4 strany"), (5, "5 strán"), (0, "0 strán")],
)
def test_format_page_count(count, expected):
    assert format_page_count(count) == expected


def test_format_file_count():
    assert [format_file_count(n) for n in (1, 3, 12)] == ["1 súbor", "3 súbory", "12 súborov"]
