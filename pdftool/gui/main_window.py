from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget

from pdftool import APP_NAME
from pdftool.gui.merge_tab import MergeTab
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.widgets import confirm

_STATUS_TIMEOUT_MS = 8000


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 720)
        self.setMinimumSize(800, 540)

        self.merge_tab = MergeTab()
        self.pages_tab = PagesTab()
        for tab in (self.merge_tab, self.pages_tab):
            tab.status_message.connect(lambda message: self.statusBar().showMessage(message, _STATUS_TIMEOUT_MS))

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self.merge_tab, "Zlúčiť PDF")
        tabs.addTab(self.pages_tab, "Upraviť strany")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Pripravené")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.pages_tab.has_unsaved_changes() and not confirm(
            self,
            "Neuložené zmeny",
            "Otočenie alebo odstránenie strán nebolo uložené. Naozaj chcete aplikáciu zavrieť?",
            "Zavrieť bez uloženia",
        ):
            event.ignore()
            return
        event.accept()
