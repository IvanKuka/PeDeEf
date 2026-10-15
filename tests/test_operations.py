from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from pypdf.generic import DecodedStreamObject, NameObject

from pdftool.operations import (
    PageRef,
    PageSelection,
    PdfToolError,
    interleave_pages,
    page_count,
    split_output_paths,
    split_pages,
    split_pdf,
    write_pages,
    write_pdf,
)
from tests.helpers import make_pdf, page_rotations, page_widths


def test_pages_left_out_do_not_travel_hidden_in_the_file_through_links(tmp_path):
    writer = PdfWriter()
    secret, public = writer.add_blank_page(400, 600), writer.add_blank_page(400, 600)
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 50 500 Td (TAJNE-987654) Tj ET")  # uncompressed, so the bytes show it
    secret[NameObject("/Contents")] = writer._add_object(content)
    writer.add_annotation(1, Link(rect=(50, 50, 200, 100), target_page_index=0))  # "see page 1"
    source = tmp_path / "doc.pdf"
    writer.write(source)

    write_pages([PageRef(source, 1)], tmp_path / "public.pdf")
    write_pages([PageRef(source, 0), PageRef(source, 1)], tmp_path / "both.pdf")

    assert b"TAJNE" not in (tmp_path / "public.pdf").read_bytes()
    both = PdfReader(tmp_path / "both.pdf")
    link = both.pages[1]["/Annots"][0].get_object()
    assert link["/Dest"][0] == both.pages[0].indirect_reference  # links between kept pages still work


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


def test_write_pages_mixes_documents_and_gives_duplicates_their_own_rotation(tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101, 102])
    second = make_pdf(tmp_path / "b.pdf", [201])
    output = tmp_path / "out.pdf"

    write_pages(
        [PageRef(first, 1), PageRef(second, 0, 90), PageRef(first, 1, 270), PageRef(first, 0)],
        output,
    )

    assert page_widths(output) == [102, 201, 102, 101]
    assert page_rotations(output) == [0, 90, 270, 0]


def test_write_pages_with_a_missing_document_writes_nothing(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", [101])
    output = tmp_path / "out.pdf"

    with pytest.raises(PdfToolError, match="neexistuje"):
        write_pages([PageRef(source, 0), PageRef(tmp_path / "gone.pdf", 0)], output)
    assert not output.exists()


def test_split_pages_names_parts_after_the_given_document(tmp_path):
    first = make_pdf(tmp_path / "doc.pdf", [101, 102])
    second = make_pdf(tmp_path / "other.pdf", [201])
    out_dir = tmp_path / "parts"
    out_dir.mkdir()

    created = split_pages(first, [[PageRef(second, 0), PageRef(first, 1)], [PageRef(first, 0, 90)]], out_dir)

    assert [path.name for path in created] == ["doc_01.pdf", "doc_02.pdf"]
    assert page_widths(created[0]) == [201, 102]
    assert page_rotations(created[1]) == [90]


@pytest.mark.parametrize(
    ("back_count", "reverse_back", "expected"),
    [
        (3, False, ["F1", "B1", "F2", "B2", "F3", "B3"]),
        (3, True, ["F1", "B3", "F2", "B2", "F3", "B1"]),
        (2, True, ["F1", "B2", "F2", "B1", "F3"]),  # the last sheet is printed on one side only
    ],
)
def test_interleave_pages_orders_front_and_back_sides(back_count, reverse_back, expected):
    pages = interleave_pages(Path("F.pdf"), 3, Path("B.pdf"), back_count, reverse_back)

    assert [f"{page.path.stem}{page.index + 1}" for page in pages] == expected


@pytest.mark.parametrize(("front_count", "back_count"), [(3, 4), (3, 1), (0, 0)])
def test_interleave_pages_rejects_counts_that_do_not_pair_up(front_count, back_count):
    with pytest.raises(PdfToolError):
        interleave_pages(Path("F.pdf"), front_count, Path("B.pdf"), back_count, reverse_back=True)


def outline(path):
    reader = PdfReader(path)
    return [(item.title, reader.get_destination_page_number(item)) for item in reader.outline]


def test_merge_bookmarks_point_to_each_inputs_first_page_in_the_output(tmp_path):
    first = make_pdf(tmp_path / "a.pdf", [101, 102, 103])
    second = make_pdf(tmp_path / "b.pdf", [201, 202])
    output = tmp_path / "out.pdf"

    write_pdf(
        [PageSelection(first, pages=[2, 1]), PageSelection(second), PageSelection(first, pages=[0])],
        output,
        bookmark_titles=["Zmluva – Žilina", "Príloha č. 1", ""],  # an empty title adds no bookmark
    )

    assert page_widths(output) == [103, 102, 201, 202, 101]
    assert outline(output) == [("Zmluva – Žilina", 0), ("Príloha č. 1", 2)]
