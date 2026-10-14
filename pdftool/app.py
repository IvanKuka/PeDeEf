"""Application entry point."""

from __future__ import annotations

import logging
import sys
from types import TracebackType

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from pdftool import APP_NAME
from pdftool.gui.main_window import MainWindow
from pdftool.gui.style import app_icon, build_stylesheet

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    # The stylesheet is designed for a light theme; without this, the system dark mode
    # would give unstyled widgets (menus, dialogs) a dark palette with clashing colours.
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setStyle("Fusion")
    if sys.platform == "win32":
        # Qt's default on Windows is the older 9 pt font; macOS already uses its native UI font.
        app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(build_stylesheet(app.font().pointSizeF()))
    app.setWindowIcon(app_icon())
    sys.excepthook = _report_unexpected_error

    window = MainWindow()
    window.show()
    # Files passed on the command line (e.g. via "Open with" or Explorer's "Send to") go to the merge list.
    if len(argv) > 1:
        window.merge_tab.add_files(argv[1:])
    return app.exec()


def _report_unexpected_error(
    exc_type: type[BaseException], exc: BaseException, traceback: TracebackType | None
) -> None:
    # PySide only prints exceptions raised inside slots to stderr, which does not
    # exist in the windowed build – without this hook such errors would be invisible.
    logger.error("Neočakávaná chyba", exc_info=(exc_type, exc, traceback))
    QMessageBox.critical(None, APP_NAME, f"Nastala neočakávaná chyba:\n{exc_type.__name__}: {exc}")
