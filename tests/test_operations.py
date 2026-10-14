from pathlib import Path

import pytest

from pdftool.operations import (
    PageSelection,
    PdfToolError,
    page_count,
    split_output_paths,
    split_pdf,
    write_pdf,
)
from tests.helpers import make_pdf, page_rotations, page_widths


def test_merge_whole_documents_in_order(tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101, 102])
    second = make_pdf(tmp_path / "b.pdf", [201])
    output = tmp_path / "out.pdf"

    write_pdf([PageSelection(second), PageSelection(first)], output)

    assert page_widths(output) == [201, 101, 102]


def test_merge_with_page_selection_and_duplicates(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101, 102, 103])
    output = tmp_path / "out.pdf"

    write_pdf([PageSelection(source, pages=[2, 0, 0])], output)

    assert page_widths(output) == [103, 101, 101]


def test_rotation_applies_only_to_selected_copy(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101, 102])
    output = tmp_path / "out.pdf"

    write_pdf([PageSelection(source, rotations={1: 270})], output)

    assert page_rotations(output) == [0, 270]


def test_rotation_is_normalised_to_full_turn(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101])
    output = tmp_path / "out.pdf"

    write_pdf([PageSelection(source, rotations={0: 450})], output)

    assert page_rotations(output) == [90]


def test_overwriting_a_source_file_is_safe(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101, 102])

    write_pdf([PageSelection(source, rotations={0: 90})], source)

    assert page_widths(source) == [101, 102]
    assert page_rotations(source) == [90, 0]
    assert list(tmp_path.glob("*.tmp")) == []


def test_empty_result_raises_and_writes_nothing(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101])
    output = tmp_path / "out.pdf"

    with pytest.raises(PdfToolError):
        write_pdf([PageSelection(source, pages=[])], output)
    assert not output.exists()


def test_out_of_range_page_raises(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101])

    with pytest.raises(PdfToolError, match="Strana 5"):
        write_pdf([PageSelection(source, pages=[4])], tmp_path / "out.pdf")


def test_missing_file_raises(tmp_path):
    with pytest.raises(PdfToolError, match="neexistuje"):
        page_count(tmp_path / "missing.pdf")


def test_invalid_file_raises(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a pdf")

    with pytest.raises(PdfToolError):
        write_pdf([PageSelection(broken)], tmp_path / "out.pdf")


def test_password_protected_file_raises(tmp_path):
    source = make_pdf(tmp_path / "secret.pdf", [101], password="tajne")

    with pytest.raises(PdfToolError, match="heslom"):
        page_count(source)


def test_file_encrypted_with_empty_password_opens(tmp_path):
    source = make_pdf(tmp_path / "restricted.pdf", [101, 102], password="")

    assert page_count(source) == 2


def test_split_into_groups(tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102, 103])
    out_dir = tmp_path / "parts"
    out_dir.mkdir()

    created = split_pdf(source, [[0, 1], [2]], out_dir, rotations={2: 90})

    assert [path.name for path in created] == ["doc_01.pdf", "doc_02.pdf"]
    assert page_widths(created[0]) == [101, 102]
    assert page_widths(created[1]) == [103]
    assert page_rotations(created[1]) == [90]


def test_split_output_paths_pad_to_part_count(tmp_path):
    paths = split_output_paths(Path("x/report.pdf"), 120, tmp_path)

    assert paths[0].name == "report_001.pdf"
    assert paths[-1].name == "report_120.pdf"


def test_split_with_empty_group_writes_nothing(tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    out_dir = tmp_path / "parts"
    out_dir.mkdir()

    with pytest.raises(PdfToolError):
        split_pdf(source, [[0], []], out_dir)
    assert list(out_dir.iterdir()) == []


def test_split_into_missing_directory_raises(tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101])

    with pytest.raises(PdfToolError, match="Priečinok"):
        split_pdf(source, [[0]], tmp_path / "missing")
