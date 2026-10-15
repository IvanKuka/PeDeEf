from datetime import date

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from pdftool.gui.stamp_dialog import StampDialog
from pdftool.gui.stamp_layer import write_stamped_pdf
from pdftool.gui.thumbnails import open_document, render_page_scaled
from pdftool.operations import PageRef
from pdftool.stamps import Position, StampSpec, stamp_texts
from tests.helpers import make_pdf
import pytest


def test_stamp_texts_number_only_the_stamped_pages():
    spec = StampSpec("Strana {n} z {total}, {date} {x}", first_number=5)

    texts = stamp_texts(spec, 3, today=date(2026, 3, 9))

    assert texts == [
        "Strana 5 z 7, 09. 03. 2026 {x}",  # unknown placeholders are kept as typed
        "Strana 6 z 7, 09. 03. 2026 {x}",
        "Strana 7 z 7, 09. 03. 2026 {x}",
    ]


def test_stamped_pdf_has_exact_text_with_diacritics_only_on_chosen_pages(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [300, 301, 302])
    pages = [PageRef(source, 2), PageRef(source, 0, rotation=90), PageRef(source, 1)]
    output = tmp_path / "out.pdf"

    write_stamped_pdf(pages, [1, 2], StampSpec("{n}/{total} KÓPIA ľščťž"), output)

    # pypdf reports some word gaps as tabs; only the words and their letters matter here.
    texts = [" ".join(page.extract_text().split()) for page in PdfReader(output).pages]
    assert texts == ["", "1/2 KÓPIA ľščťž", "2/2 KÓPIA ľščťž"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["doc.pdf", "out.pdf"]  # no temporary files left


def dark_pixel_box(image):
    points = [
        (x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() and image.pixelColor(x, y).lightness() < 128
    ]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), max(xs), min(ys), max(ys)


def test_stamp_lands_on_the_visible_page_of_rotated_and_cropped_pages(app, tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=500).rotate(90)  # shown 500 wide, 300 high
    cropped = writer.add_blank_page(width=400, height=600)
    cropped.cropbox = RectangleObject([50, 100, 350, 500])  # shown 300 x 400, away from the origin
    source = tmp_path / "doc.pdf"
    writer.write(source)
    output = tmp_path / "out.pdf"

    write_stamped_pdf([PageRef(source, 0), PageRef(source, 1)], [0, 1], StampSpec("12", Position.BOTTOM_RIGHT), output)

    document = open_document(output)
    for number, (width, height) in enumerate([(500, 300), (300, 400)]):
        image = render_page_scaled(document, number, 1.0)
        assert image.size().toTuple() == (width, height)
        left, right, top, bottom = dark_pixel_box(image)
        # Bottom right, inside the 10 mm (about 28 point) margin.
        assert width - 40 < right <= width - 28 and height - 40 < bottom <= height - 28
    document.close()


def test_stamp_dialog_prefills_the_selection_and_validates_the_range(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [300] * 6)
    dialog = StampDialog([PageRef(source, index) for index in range(6)], [1, 2, 3, 5])

    assert dialog._ranges_edit.text() == "2-4, 6"
    assert dialog.stamped_rows() == [1, 2, 3, 5]
    assert not dialog._preview.pixmap().isNull()

    dialog._ranges_edit.setText("9")
    assert not dialog._accept_button.isEnabled()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_overlay_on_one_duplicate_does_not_modify_the_other_or_its_annotation(app, tmp_path, rotation):
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=600)
    page.rotate(rotation)
    page.cropbox = RectangleObject([20, 30, 380, 570])
    annotation = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Text"),
        NameObject("/Rect"): RectangleObject([50, 60, 70, 80]), NameObject("/Contents"): TextStringObject("Note"),
    })
    page[NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
    source = tmp_path / "source.pdf"
    writer.write(source)
    pages = [PageRef(source, 0), PageRef(source, 0)]
    output = tmp_path / "stamped.pdf"
    write_stamped_pdf(pages, [1], StampSpec("STAMP", Position.BOTTOM_RIGHT), output)
    result = PdfReader(output)
    assert not result.pages[0].extract_text().strip()
    assert result.pages[1].extract_text().strip() == "STAMP"
    assert result.pages[1].rotation == rotation
    assert list(result.pages[1]["/Annots"][0].get_object()["/Rect"]) == [50, 60, 70, 80]
    document = open_document(output)
    image = render_page_scaled(document, 1, 1)
    _, right, _, bottom = dark_pixel_box(image)
    assert image.width() - 40 < right <= image.width() - 28
    assert image.height() - 40 < bottom <= image.height() - 28
    document.close()
