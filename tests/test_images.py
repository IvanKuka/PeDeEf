from pathlib import Path

import pytest
from pypdf import PdfReader
from PySide6.QtGui import QColor, QImage, QImageIOHandler, QImageWriter

from pdftool.gui import merge_tab
from pdftool.gui.images import PageFormat, export_pages_as_png, images_to_pdf
from pdftool.gui.merge_tab import MergeTab
from pdftool.operations import PageRef, PdfToolError
from tests.helpers import make_pdf, page_widths


def make_image(path: Path, width: int, height: int, exif_rotate_90: bool = False) -> Path:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#3366aa"))
    writer = QImageWriter(str(path))
    if exif_rotate_90:
        # Stored sideways with an EXIF orientation tag, as phone cameras do.
        writer.setTransformation(QImageIOHandler.Transformation.TransformationRotate90)
    assert writer.write(image), writer.errorString()
    return path


def page_sizes(path: Path) -> list[tuple[int, int]]:
    return [(round(float(page.mediabox.width)), round(float(page.mediabox.height))) for page in PdfReader(path).pages]


def test_images_become_upright_pages_without_distortion(app, tmp_path):
    photo = make_image(tmp_path / "photo.jpg", 400, 200, exif_rotate_90=True)  # upright it is 200 x 400
    scan = make_image(tmp_path / "scan.png", 300, 200)
    output = tmp_path / "out.pdf"

    images_to_pdf([photo, scan], output, PageFormat.A4)
    assert page_sizes(output) == [(595, 842), (842, 595)]  # A4 portrait for the upright photo, landscape for the scan

    images_to_pdf([photo], output, PageFormat.IMAGE)
    width, height = page_sizes(output)[0]
    assert width / height == pytest.approx(200 / 400, abs=0.01)


def test_unreadable_image_gives_a_clear_message_and_writes_nothing(app, tmp_path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not really a jpeg")
    output = tmp_path / "out.pdf"

    with pytest.raises(PdfToolError, match="broken.jpg"):
        images_to_pdf([make_image(tmp_path / "ok.png", 10, 10), broken], output, PageFormat.A4)
    assert not output.exists()


def test_merge_tab_merges_images_with_pdfs(app, tmp_path, monkeypatch):
    document = make_pdf(tmp_path / "doc.pdf", [101, 102])
    photo = make_image(tmp_path / "photo.png", 300, 200)
    output = tmp_path / "out.pdf"
    monkeypatch.setattr(merge_tab, "ask_save_pdf_path", lambda *args: output)
    monkeypatch.setattr(merge_tab, "report_success", lambda *args: None)
    tab = MergeTab()

    tab.add_files([photo, document])
    tab._list.setCurrentRow(0)
    assert not tab._range_edit.isEnabled()  # an image is a single page, it has no page range
    tab._merge()

    assert page_widths(output) == [842, 101, 102]  # the landscape photo on an A4 landscape page
    assert sorted(tmp_path.iterdir()) == sorted([document, photo, output])  # no temporary files left


def test_export_renders_pages_as_edited_and_caps_huge_pages(app, tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [200, 14000])  # pages are 500 points high
    out_dir = tmp_path / "png"
    out_dir.mkdir()

    created, reduced = export_pages_as_png(
        [PageRef(source, 0, rotation=90), PageRef(source, 1)], [0, 4], source, out_dir, dpi=72
    )

    assert [path.name for path in created] == ["doc_strana_001.png", "doc_strana_005.png"]
    assert QImage(str(created[0])).size().toTuple() == (500, 200)  # turned like in the editor
    assert max(QImage(str(created[1])).size().toTuple()) <= 8000
    assert reduced


def test_merge_tab_bookmarks_each_file_by_name_when_enabled(app, tmp_path, monkeypatch):
    document = make_pdf(tmp_path / "Zmluva – Žilina.pdf", [101, 102])
    photo = make_image(tmp_path / "občiansky preukaz.png", 300, 200)
    output = tmp_path / "out.pdf"
    monkeypatch.setattr(merge_tab, "ask_save_pdf_path", lambda *args: output)
    monkeypatch.setattr(merge_tab, "report_success", lambda *args: None)
    tab = MergeTab()
    tab.add_files([document, photo])

    tab._merge()
    reader = PdfReader(output)
    assert [(item.title, reader.get_destination_page_number(item)) for item in reader.outline] == [
        ("Zmluva – Žilina", 0),
        ("občiansky preukaz", 2),  # the image's name, not the temporary file it was converted to
    ]

    tab._bookmarks_check.setChecked(False)
    tab._merge()
    assert PdfReader(output).outline == []
