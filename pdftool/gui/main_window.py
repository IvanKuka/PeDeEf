from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QTabWidget, QToolButton, QWidget

from pdftool import APP_NAME, __version__
from pdftool.gui.batch_tab import BatchTab
from pdftool.gui.icons import command_icon
from pdftool.gui.merge_tab import MergeTab
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.settings import Settings
from pdftool.gui.settings_dialog import SettingsDialog
from pdftool.gui.style import apply_theme
from pdftool.gui.update_check import UpdateChecker, can_install_in_place, download_installer, start_installer
from pdftool.gui.widgets import busy_cursor, confirm
from pdftool.updates import Release, UpdateError

_STATUS_TIMEOUT_MS = 8000


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self._settings = settings or Settings()
        self._applying_theme = False
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1100, 720)
        self.setMinimumSize(800, 540)
        self._settings.restore_window(self)

        self._settings_action = QAction("Nastavenia", self)
        self._settings_action.setIcon(command_icon("settings"))
        self._settings_action.triggered.connect(self._show_settings)

        self.merge_tab = MergeTab(self._settings)
        self.pages_tab = PagesTab(self._settings)
        self.batch_tab = BatchTab(self._settings)
        for tab in (self.merge_tab, self.pages_tab, self.batch_tab):
            tab.status_message.connect(lambda message: self.statusBar().showMessage(message, _STATUS_TIMEOUT_MS))

        tabs = QTabWidget()
        tabs.setObjectName("workspaceTabs")
        tabs.setDocumentMode(True)
        tabs.tabBar().setDrawBase(False)
        tabs.addTab(self.merge_tab, command_icon("merge"), "Zlúčiť PDF")
        tabs.addTab(self.pages_tab, command_icon("properties"), "Upraviť strany")
        tabs.addTab(self.batch_tab, command_icon("batch"), "Dávkové úpravy")
        # One application row: workspaces on the left, global commands on the right.
        global_commands = QWidget()
        global_commands.setObjectName("globalCommands")
        global_layout = QHBoxLayout(global_commands)
        global_layout.setContentsMargins(6, 4, 8, 4)
        global_layout.setSpacing(6)
        self.pages_tab._open_button.clicked.disconnect(self.pages_tab._choose_file)
        self.pages_tab._open_button.clicked.connect(self._open_pdf)
        global_layout.addWidget(self.pages_tab._open_button)
        self._update_button = QToolButton()
        self._update_button.setObjectName("updateButton")
        self._update_button.hide()
        self._release: Release | None = None
        self._update_button.clicked.connect(self._update)
        global_layout.addWidget(self._update_button)
        settings_button = QToolButton()
        settings_button.setDefaultAction(self._settings_action)
        settings_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        global_layout.addWidget(settings_button)
        tabs.setCornerWidget(global_commands, Qt.Corner.TopRightCorner)
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Pripravené")
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        self._apply_theme()

    def check_for_updates(self) -> None:
        """Look for a newer release in the background, if the user allows it; silent unless one exists."""
        if not self._settings.check_for_updates():
            return
        checker = UpdateChecker(self)
        checker.update_available.connect(self._show_update)
        checker.check()

    def _show_update(self, release: Release) -> None:
        self._release = release
        if can_install_in_place(release):
            self._update_button.setText(f"Aktualizovať na verziu {release.version}")
            self._update_button.setToolTip("Stiahne a nainštaluje novú verziu; aplikácia sa potom sama znova spustí.")
        else:
            self._update_button.setText(f"Nová verzia {release.version} – stiahnuť")
            self._update_button.setToolTip(f"Otvorí stránku verzie {release.version} s inštalátormi na GitHube")
        self._update_button.show()
        self.statusBar().showMessage(f"K dispozícii je nová verzia {release.version}.", _STATUS_TIMEOUT_MS)

    def _update(self) -> None:
        release = self._release
        if release is None:
            return
        if not can_install_in_place(release):
            QDesktopServices.openUrl(QUrl(release.url))
            return
        if not confirm(
            self,
            "Aktualizácia",
            f"Stiahne sa a nainštaluje verzia {release.version}. Aplikácia sa počas inštalácie zavrie "
            "a potom sa sama znova spustí.",
            "Aktualizovať",
        ):
            return
        try:
            installer = download_installer(self, release)
        except UpdateError as exc:
            QMessageBox.warning(self, "Aktualizácia", f"{exc}\n\nNovú verziu si môžete stiahnuť aj ručne z GitHubu.")
            return
        if installer is None or not self.close():  # cancelled, or unsaved work the user keeps
            return
        try:
            start_installer(installer)
        except UpdateError as exc:
            QMessageBox.critical(None, "Aktualizácia", str(exc))

    def _open_pdf(self) -> None:
        self.centralWidget().setCurrentWidget(self.pages_tab)
        self.pages_tab._choose_file()

    def _apply_theme(self) -> None:
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            apply_theme(QApplication.instance(), self._settings.theme())
        finally:
            self._applying_theme = False

    def _system_theme_changed(self, scheme) -> None:
        if self._settings.theme() == "system":
            self._apply_theme()

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self._apply_theme()
            self.pages_tab.apply_preferences()
            self.merge_tab.apply_preferences()
        dialog.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.pages_tab.has_unsaved_changes() and not confirm(
            self,
            "Neuložené zmeny",
            "Úpravy strán nie sú uložené. Naozaj chcete aplikáciu zavrieť?",
            "Zavrieť bez uloženia",
        ):
            event.ignore()
            return
        if self.batch_tab.is_running():
            if not confirm(
                self,
                "Dávka ešte beží",
                "Dávkové spracovanie ešte nie je dokončené. Zrušiť ho a zavrieť aplikáciu?\n"
                "Už uložené súbory zostanú zachované.",
                "Zrušiť dávku a zavrieť",
            ):
                event.ignore()
                return
            # The file being written is finished first, so no half-written output is left behind.
            with busy_cursor():
                self.batch_tab.stop_and_wait()
        self._settings.save_window(self)
        self.pages_tab._reset()
        event.accept()
