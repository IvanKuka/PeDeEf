"""OCR failure paths and UI contracts that run even without an installed Tesseract."""

import io
import subprocess
import sys
import time
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QProgressDialog, QWidget

from pdftool import ocr
from pdftool.gui import recognition
from pdftool.gui.ocr_dialog import OcrDialog
from pdftool.gui.widgets import progress_dialog
from pdftool.operations import PageRef, PdfToolError
from tests.helpers import make_pdf
from tests.test_compare import text_pdf


def blank_layer(count=1):
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=100, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_language_discovery_rejects_osd_empty_models_and_missing_font(tmp_path, monkeypatch):
    executable = tmp_path / "tesseract.exe"
    executable.touch()
    data = tmp_path / "tessdata"
    data.mkdir()
    (data / "pdf.ttf").write_bytes(b"font")
    (data / "osd.traineddata").write_bytes(b"orientation")
    (data / "eng.traineddata").touch()
    monkeypatch.setattr(ocr, "_candidates", lambda: iter([(executable, data)]))
    assert ocr.find_tesseract() is None
    (data / "eng.traineddata").write_bytes(b"language model")
    assert ocr.find_tesseract().languages() == ["eng"]
    (data / "pdf.ttf").unlink()
    assert ocr.find_tesseract() is None


@pytest.mark.parametrize("callback_error", [False, True])
def test_cancel_or_callback_failure_kills_child_even_when_stdin_is_blocked(tmp_path, monkeypatch, callback_error):
    real_popen = subprocess.Popen
    children = []
    def sleeping_child(command, **kwargs):
        child = real_popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(ocr.subprocess, "Popen", sleeping_child)
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        if calls > 1 and callback_error:
            raise ValueError("callback failed")
        return calls > 1
    started = time.perf_counter()
    engine = ocr.Tesseract(Path(sys.executable), tmp_path)
    if callback_error:
        with pytest.raises(ValueError, match="callback failed"):
            ocr._run_tesseract(engine, b"x" * 2_000_000, "eng", 300, "3", cancel)
    else:
        assert ocr._run_tesseract(engine, b"x" * 2_000_000, "eng", 300, "3", cancel) is None
    assert time.perf_counter() - started < 3
    assert len(children) == 1 and children[0].poll() is not None
    assert all(pipe.closed for pipe in (children[0].stdin, children[0].stdout, children[0].stderr))


def test_engine_errors_are_reported_and_precancel_does_not_spawn(tmp_path, monkeypatch):
    real_popen = subprocess.Popen
    monkeypatch.setattr(ocr.subprocess, "Popen", lambda command, **kw: real_popen(
        [sys.executable, "-c", "import sys; sys.stderr.write('missing language'); sys.exit(2)"], **kw
    ))
    engine = ocr.Tesseract(Path(sys.executable), tmp_path)
    assert ocr._run_tesseract(engine, b"", "eng", 300, "3", lambda: True) is None
    with pytest.raises(PdfToolError, match="missing language"):
        ocr._run_tesseract(engine, b"", "eng", 300, "3", lambda: False)


def test_ocr_dialog_ranges_follow_visible_positions_and_skip_existing_text(app):
    dialog = OcrDialog(["eng", "slk"], [0, 2, 4], 5, selected_rows=[1, 2])
    assert dialog.language() == "slk" and dialog.recognition_rows() == [2]
    dialog._ranges_edit.setText("5, 1-3, 1")
    assert dialog.recognition_rows() == [0, 2, 4]
    dialog._ranges_edit.setText("2")
    assert not dialog._accept_button.isEnabled()
    dialog._ranges_edit.setText("6")
    assert not dialog._accept_button.isEnabled() and dialog._ranges_edit.property("invalid")
    dialog._ranges_edit.clear()
    assert dialog._accept_button.isEnabled() and dialog.recognition_rows() == [0, 2, 4]
    assert not OcrDialog([], [0], 1)._accept_button.isEnabled()


def test_unchanged_progress_values_process_cancel_events_and_completion_keeps_cancellation(app):
    parent = QWidget()
    with progress_dialog(parent, "OCR", "Recognising", 1, minimum_duration=0) as report:
        dialog = parent.findChild(QProgressDialog)
        assert report(0)
        QTimer.singleShot(0, dialog.cancel)
        assert not report(0)
        assert not report(1)  # reaching maximum must not reset wasCanceled


@pytest.mark.parametrize(("width", "height"), [(595, 842), (4000, 6000), (9000, 9000), (20000, 100)])
def test_ocr_raster_dimensions_are_bounded(width, height):
    scale = recognition._render_scale(width, height)
    assert max(round(width * scale), round(height * scale)) <= recognition.MAX_OCR_SIDE
    assert round(width * scale) * round(height * scale) <= recognition.MAX_OCR_PIXELS + 6000
    if width == 595:
        assert scale == recognition.OCR_DPI / 72


def test_cancellation_on_final_progress_discards_all_layers(app, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "source.pdf", [101])
    monkeypatch.setattr(recognition, "recognize_page", lambda *args: blank_layer())
    result = recognition.recognize_pages([PageRef(source, 0)], [0], None, "eng", lambda done: done < 1)
    assert result is None


@pytest.mark.parametrize("layer", [b"not pdf", blank_layer(0), blank_layer(2), blank_layer()])
def test_bad_or_empty_layers_preserve_existing_output(tmp_path, layer):
    source = make_pdf(tmp_path / "source.pdf", [101])
    output = tmp_path / "out.pdf"
    output.write_bytes(b"keep existing result")
    before = source.read_bytes()
    with pytest.raises(PdfToolError):
        ocr.write_with_text_layers([PageRef(source, 0)], {0: layer}, output)
    assert output.read_bytes() == b"keep existing result" and source.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["out.pdf", "source.pdf"]


def test_text_layer_is_scaled_to_the_visible_base_size(app, tmp_path):
    # Simulate OCR rendered at a lower DPI due to a large page or pixel rounding.
    layer_path = text_pdf(tmp_path / "layer.pdf", ["OCR result"])[0].path
    source = make_pdf(tmp_path / "source.pdf", [800])
    output = tmp_path / "out.pdf"
    ocr.write_with_text_layers([PageRef(source, 0)], {0: layer_path.read_bytes()}, output)
    reader = PdfReader(output)
    assert float(reader.pages[0].mediabox.width) == 800
    assert "OCR result" in " ".join(reader.pages[0].extract_text().split())


def test_a_sparse_automatic_layout_is_retried_as_one_block_and_the_fuller_text_kept(tmp_path, monkeypatch):
    # Tesseract 5.5 reads a single line of some askew scans with automatic layout analysis.
    fragment = text_pdf(tmp_path / "fragment.pdf", ["do štrnástich dní"])[0].path.read_bytes()
    full = text_pdf(tmp_path / "full.pdf", ["Objednávateľ uhradí cenu do štrnástich dní. " * 8])[0].path.read_bytes()
    engine = type("Engine", (), {"languages": lambda self: ["slk"]})()
    png = b"\x89PNG\r\n\x1a\n"

    def run(layers):
        calls = []

        def fake(tesseract, image, language, dpi, layout, is_cancelled):
            calls.append(layout)
            return layers[layout]

        monkeypatch.setattr(ocr, "_run_tesseract", fake)
        return ocr.recognize_page(engine, png, "slk", 150, lambda: False), calls

    assert run({"3": fragment, "6": full}) == (full, ["3", "6"])
    assert run({"3": full, "6": fragment}) == (full, ["3"])  # a full page needs no second pass
    assert run({"3": full, "6": None}) == (full, ["3"])
