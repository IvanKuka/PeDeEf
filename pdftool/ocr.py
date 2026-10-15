"""Text recognition (OCR) with Tesseract, run as a separate program (no GUI dependencies).

Tesseract reads a picture of a page and returns a PDF page holding only invisible
text at the positions of the recognised words. Laid over the original page, it
makes a scan searchable and copyable without changing how the page looks.
Pictures and results are passed through pipes, so no picture of the document is
written to disk. All raised `PdfToolError` messages are user-facing (Slovak).
"""

from __future__ import annotations

import io
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from pdftool.operations import DocumentInfo, PageRef, PdfToolError, apply_overlay, visible_page_sizes, write_pages

# Tesseract's own name for the language data next to what the user sees.
LANGUAGE_NAMES = {
    "slk": "slovenčina",
    "ces": "čeština",
    "eng": "angličtina",
    "deu": "nemčina",
    "hun": "maďarčina",
    "pol": "poľština",
    "ukr": "ukrajinčina",
    "fra": "francúzština",
    "ita": "taliančina",
    "spa": "španielčina",
}
# Data that is not a language: orientation and script detection.
_NOT_LANGUAGES = {"osd"}
_EXECUTABLE = "tesseract.exe" if sys.platform == "win32" else "tesseract"
# How often a running recognition checks whether the user cancelled, in seconds.
_CANCEL_CHECK_INTERVAL = 0.1


@dataclass(frozen=True)
class Tesseract:
    executable: Path
    tessdata: Path  # language data and pdf.ttf, the invisible font of the text layer

    def languages(self) -> list[str]:
        """Installed languages, as Tesseract codes (e.g. "slk"), sorted by their Slovak names."""
        codes = []
        for path in self.tessdata.glob("*.traineddata"):
            try:
                if path.stem not in _NOT_LANGUAGES and path.is_file() and path.stat().st_size > 0:
                    codes.append(path.stem)
            except OSError:
                continue  # an unavailable or concurrently removed model is not an installed language
        return sorted(codes, key=lambda code: LANGUAGE_NAMES.get(code, code))


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def find_tesseract() -> Tesseract | None:
    """The Tesseract to use: the application's own copy first, then a system installation."""
    for executable, tessdata in _candidates():
        candidate = Tesseract(executable, tessdata)
        try:
            font = tessdata / "pdf.ttf"
            if executable.is_file() and font.is_file() and font.stat().st_size > 0 and candidate.languages():
                return candidate
        except OSError:
            continue
    return None


def _candidates() -> Iterator[tuple[Path, Path]]:
    if directory := os.environ.get("PDFTOOL_TESSERACT"):
        yield Path(directory) / _EXECUTABLE, Path(directory) / "tessdata"
    if getattr(sys, "frozen", False):
        own = Path(sys.executable).parent / "tesseract"  # bundled by build.py
    else:
        own = Path(__file__).resolve().parents[1] / "build" / "tesseract"  # prepared by build.py
    yield own / _EXECUTABLE, own / "tessdata"
    if sys.platform == "win32":
        installs = []
        if program_files := os.environ.get("ProgramFiles"):
            installs.append(Path(program_files) / "Tesseract-OCR")
        if local_app_data := os.environ.get("LOCALAPPDATA"):
            installs.append(Path(local_app_data) / "Programs" / "Tesseract-OCR")  # installed for one user
        for installed in installs:
            yield installed / _EXECUTABLE, installed / "tessdata"
    else:
        for prefix in (Path("/opt/homebrew"), Path("/usr/local"), Path("/usr")):
            yield prefix / "bin" / _EXECUTABLE, prefix / "share" / "tessdata"
    if found := shutil.which("tesseract"):
        executable = Path(found).resolve()
        yield executable, executable.parent / "tessdata"
        yield executable, executable.parent.parent / "share" / "tessdata"


def recognize_page(
    tesseract: Tesseract, png: bytes, language: str, dpi: int, is_cancelled: Callable[[], bool]
) -> bytes | None:
    """Recognise the text in a PNG picture of a page; returns a one-page PDF with only the text.

    The PDF page has the size of the picture at `dpi`. Returns None when `is_cancelled`
    became true; the program is stopped then.
    """
    if is_cancelled():
        return None
    if not png or not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise PdfToolError("Obrázok strany na rozpoznanie textu nie je platný PNG.")
    if language not in tesseract.languages():
        raise PdfToolError("Vybraný jazyk OCR nie je nainštalovaný. Vyberte dostupný jazyk alebo aplikáciu preinštalujte.")
    if type(dpi) is not int or dpi <= 0:
        raise PdfToolError("Rozlíšenie strany na rozpoznanie textu musí byť kladné celé číslo.")
    layer = None
    for layout in _LAYOUTS:
        layer = _run_tesseract(tesseract, png, language, dpi, layout, is_cancelled)
        if layer is None or _has_text(layer):
            return layer
    return layer  # a page without any text, such as an empty back side


# Page layouts to try, by Tesseract's page segmentation mode. Automatic layout analysis keeps
# columns apart, but finds no lines at all on some skewed scans with dense lines (seen with
# 2° on 12-point text); reading the page as one block of text still recognises those.
_LAYOUTS = ("3", "6")


def _read_layer(layer: bytes):
    try:
        reader = PdfReader(io.BytesIO(layer))
        if len(reader.pages) != 1:
            raise PdfToolError("Výsledok OCR jednej strany musí obsahovať práve jednu stranu.")
        page = reader.pages[0]
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if not all(math.isfinite(size) and size > 0 for size in (width, height)):
            raise PdfToolError("Výsledok OCR má neplatné rozmery strany.")
        return page
    except (PdfReadError, ValueError, IndexError) as exc:
        raise PdfToolError(f"Výsledok rozpoznávania textu sa nepodarilo načítať: {exc}") from exc


def _has_text(layer: bytes) -> bool:
    try:
        return bool(_read_layer(layer).extract_text().strip())
    except (PdfReadError, ValueError) as exc:
        raise PdfToolError("Text vo výsledku OCR sa nepodarilo načítať.") from exc


def _run_tesseract(
    tesseract: Tesseract, png: bytes, language: str, dpi: int, layout: str, is_cancelled: Callable[[], bool]
) -> bytes | None:
    if is_cancelled():
        return None
    command = [
        str(tesseract.executable), "stdin", "stdout",
        "--tessdata-dir", str(tesseract.tessdata),
        "-l", language,
        "--dpi", str(dpi),
        "--psm", layout,
        "-c", "tessedit_create_pdf=1",
        "-c", "textonly_pdf=1",  # the text layer alone: the original page stays as it is
    ]
    # A windowed application would otherwise flash a console window for every page on Windows.
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags
        )
    except OSError as exc:
        raise PdfToolError(f"Program na rozpoznávanie textu (Tesseract) sa nepodarilo spustiť: {exc}") from exc
    completed = threading.Event()
    result: list[tuple[bytes, bytes]] = []
    failures: list[Exception] = []

    def exchange() -> None:
        try:
            result.append(process.communicate(png))
        except Exception as exc:
            failures.append(exc)
        finally:
            completed.set()

    # On Windows communicate(input, timeout=...) can block while writing stdin, before
    # the timeout is observed. Only pipe I/O runs on this thread; Qt stays on its own thread.
    worker = threading.Thread(target=exchange, name="ocr-pipes")
    try:
        worker.start()
    except RuntimeError as exc:
        process.kill()
        process.wait()
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        raise PdfToolError("Spracovanie OCR sa nepodarilo spustiť. Skúste operáciu znova.") from exc
    try:
        while not completed.wait(_CANCEL_CHECK_INTERVAL):
            if is_cancelled():
                return None
        if is_cancelled():
            return None
        if failures:
            raise PdfToolError("S programom na rozpoznávanie textu sa nepodarilo komunikovať.") from failures[0]
        output, errors = result[0]
    finally:
        if process.poll() is None:
            process.kill()
        worker.join()  # the process and both pipe readers are gone before returning, also on cancellation
        process.wait()
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
    if process.returncode != 0 or not output.startswith(b"%PDF"):
        detail = errors.decode("utf-8", errors="replace").strip()[:2000] or f"kód {process.returncode}"
        raise PdfToolError(f"Rozpoznávanie textu zlyhalo: {detail}")
    return output


def write_with_text_layers(
    pages: Sequence[PageRef],
    layers: Mapping[int, bytes],
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write `pages` with the recognised text (from `recognize_page`) laid over the pages at its keys (rows).

    Each layer must have the visible size of its page (after rotation and crop).
    """
    if not layers:
        raise PdfToolError("Nie je čo rozpoznať.")
    if any(type(row) is not int or not 0 <= row < len(pages) for row in layers):
        raise PdfToolError("Výsledok OCR odkazuje na stranu, ktorá v dokumente neexistuje.")
    rows = sorted(layers)
    output_path = Path(output_path)
    # Intermediate files live next to the output, so a full disk or missing rights fail early.
    try:
        with tempfile.TemporaryDirectory(dir=output_path.parent) as temp_dir:
            base = Path(temp_dir) / "pages.pdf"
            write_pages(pages, base)
            sizes = visible_page_sizes(base)
            combined = PdfWriter()
            page_map = {}
            for row in rows:
                page = _read_layer(layers[row])
                if not page.extract_text().strip():
                    continue  # an empty back side needs no text layer
                page = combined.add_page(page)
                page.transfer_rotation_to_content()
                # Pixel rounding and the memory cap can change the OCR page's physical size.
                # Match the original exactly, without scaling or rasterising its visible content.
                page.scale_to(*sizes[row])
                page_map[row] = len(combined.pages) - 1
            if not page_map:
                raise PdfToolError(
                    "Na vybraných stranách sa nepodarilo rozpoznať žiadny text. Nič sa neuložilo. "
                    "Skontrolujte jazyk, kvalitu a otočenie skenu."
                )
            layer_path = Path(temp_dir) / "text.pdf"
            with open(layer_path, "wb") as stream:
                combined.write(stream)
            apply_overlay(base, layer_path, page_map, output_path, password, info)
    except (OSError, PdfReadError, ValueError) as exc:
        raise PdfToolError(f"PDF s rozpoznaným textom sa nepodarilo pripraviť: {exc}") from exc
