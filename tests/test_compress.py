import random

from pypdf import PdfReader
from PySide6.QtCore import QBuffer, QIODevice, QMarginsF, QRectF
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from pdftool.gui.images import jpeg_recompressor
from pdftool.gui.stamp_layer import write_stamp_layer
from pdftool.gui.thumbnails import on_white, open_document, render_page_scaled
from pdftool.operations import PageRef, write_optimized
from pdftool.stamps import StampSpec
from tests.helpers import make_pdf


def test_compression_is_pending_until_final_save_and_does_not_repeat_rotation(app, dialogs, tmp_path, monkeypatch):
    from pdftool.gui import pages_tab
    source = make_pdf(tmp_path / "source.pdf", [101, 102])
    original = source.read_bytes()
    tab = pages_tab.PagesTab()
    tab.open_file(source)
    tab._list.item(0).setSelected(True)
    tab._rotate_selected(90)
    monkeypatch.setattr(pages_tab.CompressDialog, "exec", lambda self: self.DialogCode.Accepted)
    dialogs.save_path = source
    tab._compress()
    assert tab.has_unsaved_changes()
    assert source.read_bytes() == original
    assert tab._current_pages()[0].rotation == 0
    next_save = tmp_path / "again.pdf"
    assert tab._write(tab._current_pages(), next_save)
    assert [page.rotation for page in PdfReader(next_save).pages] == [90, 0]


def make_scan_pdf(path):
    """Three pages drawn from images: a colour scan, a grey scan and a picture with transparency."""
    rng = random.Random(1)

    def scan(image_format, background):
        image = QImage(2480, 3508, image_format)
        image.fill(QColor(background))
        painter = QPainter(image)
        for _ in range(3000):
            painter.fillRect(rng.randrange(2480), rng.randrange(3508), rng.randrange(4, 60), 6, QColor("#202020"))
        painter.end()
        return image

    transparent = QImage(600, 600, QImage.Format.Format_ARGB32)
    transparent.fill(QColor(0, 0, 0, 0))
    painter = QPainter(transparent)
    painter.fillRect(100, 100, 400, 400, QColor(200, 30, 30, 160))
    painter.end()

    writer = QPdfWriter(str(path))
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF()))
    painter = QPainter(writer)
    images = [scan(QImage.Format.Format_RGB32, "#f4f1ea"), scan(QImage.Format.Format_Grayscale8, "#eeeeee"), transparent]
    for number, image in enumerate(images):
        if number:
            writer.newPage()
        painter.drawImage(QRectF(0, 0, writer.width(), writer.width() * image.height() / image.width()), image)
    painter.end()
    return path


def page_images(path):
    reader = PdfReader(path)
    found = []
    for page in reader.pages:
        for reference in page["/Resources"]["/XObject"].values():
            image = reference.get_object()
            found.append((image["/Filter"], image["/ColorSpace"], image["/Width"], "/SMask" in image))
    return found


def test_lossless_optimisation_shrinks_text_documents_without_touching_the_text(app, tmp_path):
    source = tmp_path / "text.pdf"
    write_stamp_layer([(595, 842)] * 20, ["Zmluva o dielo – Žilina, článok " * 15] * 20, StampSpec("x"), source)
    output = tmp_path / "small.pdf"

    report = write_optimized([PageRef(source, index) for index in range(20)], output)

    assert report.after < report.before
    assert report.after == output.stat().st_size
    reader = PdfReader(output)
    assert len(reader.pages) == 20
    assert "Žilina" in reader.pages[7].extract_text()


def test_image_profile_shrinks_scans_and_keeps_grey_and_transparent_pictures_right(app, tmp_path):
    source = make_scan_pdf(tmp_path / "scan.pdf")
    output = tmp_path / "small.pdf"
    before_images = page_images(source)

    report = write_optimized([PageRef(source, index) for index in range(3)], output, jpeg_recompressor(1754, 75))

    assert report.after < report.before / 2
    after_images = page_images(output)
    assert [image[0] for image in after_images[:2]] == ["/DCTDecode", "/DCTDecode"]
    assert [image[1] for image in after_images[:2]] == [image[1] for image in before_images[:2]]
    assert [image[2] for image in after_images[:2]] == [1240, 1240]  # 2480 pixels wide before, now ~150 dpi
    assert after_images[2] == before_images[2]  # the picture with transparency is not a plain JPEG: kept as it was
    document = open_document(output)
    corner = on_white(render_page_scaled(document, 2, 0.5)).pixelColor(150, 150)
    assert corner.red() > corner.green() + 50  # the semi-transparent red square still shows
    document.close()


def test_grey_jpeg_pictures_stay_grey(app):
    grey = QImage(3000, 2000, QImage.Format.Format_Grayscale8)
    grey.fill(QColor("#777777"))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    grey.save(buffer, "JPG", 95)

    data, width, height = jpeg_recompressor(1500, 75)(bytes(buffer.data()), "/DeviceGray")

    result = QImage.fromData(data, "JPG")
    assert (width, height) == (1500, 1000) == result.size().toTuple()
    assert result.isGrayscale() and result.format() == QImage.Format.Format_Grayscale8


def test_a_file_that_cannot_shrink_is_reported_and_never_grows(app, tmp_path):
    source = make_pdf(tmp_path / "tiny.pdf", [101])
    output = tmp_path / "out.pdf"

    report = write_optimized([PageRef(source, 0)], output, jpeg_recompressor(1170, 60))

    assert report.after <= report.before  # at worst the plain save, never bigger
    assert output.stat().st_size == report.after
