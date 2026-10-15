import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from pdftool.gui import pages_tab
from pdftool.gui.crop_dialog import CropDialog
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.operations import PageRef, PdfToolError, rotate_crop, write_pages


def make_marked_pdf(path, own_rotation=0):
    """A 200 x 400 point page with a black square in its bottom-left corner (in PDF coordinates)."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=400)
    stream = DecodedStreamObject()
    stream.set_data(b"0 0 0 rg 0 0 50 50 re f")
    page[NameObject("/Contents")] = writer._add_object(stream)
    if own_rotation:
        page.rotate(own_rotation)
    writer.write(path)
    return path


def shown(path):
    """(width, height, marker visible) of the saved page as a viewer shows it."""
    document = open_document(path)
    # Unpainted areas are transparent black; on paper they are white.
    image = on_white(render_page_scaled(document, 0, 1.0))
    document.close()
    dark = sum(
        1 for y in range(0, image.height(), 2) for x in range(0, image.width(), 2) if image.pixelColor(x, y).lightness() < 100
    )
    return image.width(), image.height(), dark > 0


@pytest.mark.parametrize(
    ("own_rotation", "pending_rotation", "crop", "expected"),
    [
        # Upright page: the marker is at the bottom left.
        (0, 0, (0.5, 0, 0, 0), (100, 400, False)),
        (0, 0, (0, 0, 0.5, 0), (100, 400, True)),
        # Turned 90° clockwise in the editor: the marker is now at the top left of the page as seen.
        (0, 90, (0, 0.5, 0, 0), (400, 100, False)),
        (0, 90, (0, 0, 0, 0.5), (400, 100, True)),
        # The same, but the turn is stored in the source file itself.
        (90, 0, (0, 0.5, 0, 0), (400, 100, False)),
        # Both: 180° in total, the marker is at the top right.
        (90, 90, (0, 0, 0.5, 0), (100, 400, False)),
    ],
)
def test_crop_cuts_the_page_as_the_user_sees_it(app, tmp_path, own_rotation, pending_rotation, crop, expected):
    source = make_marked_pdf(tmp_path / "doc.pdf", own_rotation)
    output = tmp_path / "out.pdf"

    write_pages([PageRef(source, 0, rotation=pending_rotation, crop=crop)], output)

    assert shown(output) == expected


def test_a_crop_turns_with_its_page(app, tmp_path):
    source = make_marked_pdf(tmp_path / "doc.pdf")
    crop = (0.5, 0, 0, 0)  # cuts the marker away on the upright page
    turned = tmp_path / "turned.pdf"

    write_pages([PageRef(source, 0, rotation=90, crop=rotate_crop(crop, 90))], turned)

    assert rotate_crop(crop, 90) == (0, 0.5, 0, 0)
    assert shown(turned) == (400, 100, False)  # the same part of the page is still cut away


def test_a_crop_that_leaves_nothing_is_refused(app, tmp_path):
    source = make_marked_pdf(tmp_path / "doc.pdf")

    with pytest.raises(PdfToolError):
        write_pages([PageRef(source, 0, crop=(0.5, 0, 0.5, 0))], tmp_path / "out.pdf")

    dialog = CropDialog(PageRef(source, 0), 1)
    dialog._spins[0].setValue(40)  # mm; the page is about 70 mm wide
    dialog._spins[2].setValue(40)
    assert not dialog._apply_button.isEnabled()


def test_pages_tab_crop_is_an_undoable_edit_of_the_selected_pages(app, dialogs, tmp_path, monkeypatch):
    source = make_marked_pdf(tmp_path / "doc.pdf")

    class Cropping:
        DialogCode = CropDialog.DialogCode

        def __init__(self, page, page_count, parent):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def crop(self):
            return (0.5, 0, 0, 0)

    monkeypatch.setattr(pages_tab, "CropDialog", Cropping)
    tab = PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)

    tab._crop_selected()
    assert tab.has_unsaved_changes()
    tab._undo()
    assert not tab.has_unsaved_changes()
    tab._redo()

    dialogs.save_path = tmp_path / "out.pdf"
    tab._save_as()
    box = PdfReader(dialogs.save_path).pages[0].cropbox
    assert (float(box.left), float(box.right)) == (100, 200)
