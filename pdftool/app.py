"""Application entry point."""

from __future__ import annotations

import logging
import sys
from types import TracebackType

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from pdftool import APP_NAME
from pdftool.gui.main_window import MainWindow
from pdftool.gui.settings import Settings
from pdftool.gui.style import app_icon

logger = logging.getLogger(__name__)

# Hidden command-line flag: start the app, then quit immediately (used by build.py).
SMOKE_TEST_FLAG = "--smoke-test"
OCR_SMOKE_TEST_FLAG = "--ocr-smoke-test"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    if sys.platform == "win32":
        # Qt's default on Windows is the older 9 pt font; macOS already uses its native UI font.
        app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(app_icon())
    sys.excepthook = _report_unexpected_error

    arguments = argv[1:]
    smoke_test = SMOKE_TEST_FLAG in arguments
    files = [argument for argument in arguments if argument not in (SMOKE_TEST_FLAG, OCR_SMOKE_TEST_FLAG)]
    if OCR_SMOKE_TEST_FLAG in arguments:
        try:
            _smoke_test_ocr()
        except Exception:
            logger.exception("Smoke test OCR zlyhal")
            return 1
        return 0

    window = MainWindow(Settings.for_application())
    window.show()
    # Files passed on the command line (e.g. via "Open with" or Explorer's "Send to") go to the merge list.
    if files:
        window.merge_tab.add_files(files)
    if not smoke_test:
        window.check_for_updates()
    if smoke_test:
        # build.py checks the packaged app this way: it must get as far as a running
        # event loop and then exit cleanly with code 0.
        QTimer.singleShot(0, app.quit)
    return app.exec()


def _smoke_test_ocr() -> None:
    """Exercise the real OCR executable, its DLLs and language data in the packaged app."""
    import io
    from pathlib import Path
    from pypdf import PdfReader
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QColor, QImage, QPainter
    from pdftool.ocr import find_tesseract, recognize_page

    tesseract = find_tesseract()
    if tesseract is None or "eng" not in tesseract.languages():
        raise RuntimeError("Tesseract s angličtinou nie je k dispozícii.")
    if getattr(sys, "frozen", False):
        bundled = Path(sys.executable).parent / "tesseract"
        if tesseract.executable.parent.resolve() != bundled.resolve():
            raise RuntimeError("V zostavenej aplikácii chýba pribalený Tesseract.")
    image = QImage(900, 240, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    font = QFont("Arial")
    font.setPixelSize(60)
    painter.setFont(font)
    painter.setPen(QColor("black"))
    painter.drawText(30, 140, "PDF OCR 12345")
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Skúšobný obrázok OCR sa nepodarilo vytvoriť.")
    layer = recognize_page(tesseract, bytes(buffer.data()), "eng", 300, lambda: False)
    if layer is None or "12345" not in PdfReader(io.BytesIO(layer)).pages[0].extract_text():
        raise RuntimeError("Pribalený Tesseract nerozpoznal skúšobný text.")


def _report_unexpected_error(
    exc_type: type[BaseException], exc: BaseException, traceback: TracebackType | None
) -> None:
    # PySide only prints exceptions raised inside slots to stderr, which does not
    # exist in the windowed build – without this hook such errors would be invisible.
    logger.error("Neočakávaná chyba", exc_info=(exc_type, exc, traceback))
    QMessageBox.critical(None, APP_NAME, f"Nastala neočakávaná chyba:\n{exc_type.__name__}: {exc}")
