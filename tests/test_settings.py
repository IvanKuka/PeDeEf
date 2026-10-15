from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget

from pdftool.gui import merge_tab
from pdftool.gui.main_window import MainWindow
from pdftool.gui.merge_tab import MergeTab
from pdftool.gui.settings import Settings
from pdftool.gui.settings_dialog import SettingsDialog
from pdftool.gui.style import apply_theme
from tests.helpers import make_pdf


@pytest.fixture
def settings(tmp_path):
    # A real QSettings backend, but in a file of the test's own, never the user's profile.
    return Settings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


def test_last_directory_survives_restart_and_falls_back_when_gone(tmp_path):
    store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    folder = tmp_path / "scans"
    folder.mkdir()
    Settings(store).remember_directory(folder / "doc.pdf")

    assert Settings(store).last_directory() == folder
    folder.rmdir()  # e.g. an unplugged drive
    assert Settings(store).last_directory() == Path.home()


def test_corrupt_settings_do_not_prevent_start(app, tmp_path):
    ini = tmp_path / "settings.ini"
    ini.write_text("[window]\ngeometry=@ByteArray(garbage)\n[paths]\nlast_directory=1, 2, 3\n", encoding="utf-8")
    settings = Settings(QSettings(str(ini), QSettings.Format.IniFormat))

    window = MainWindow(settings)

    assert window.size().width() >= 800
    assert settings.last_directory() == Path.home()


def test_window_geometry_is_restored_but_never_off_screen(app, settings):
    window = QWidget()
    window.resize(640, 480)
    window.move(50000, 50000)  # e.g. saved on a second monitor that is no longer connected
    settings.save_window(window)

    restored = QWidget()
    settings.restore_window(restored)

    assert restored.size().width() == 640
    screen = QApplication.primaryScreen().availableGeometry()
    assert screen.intersects(restored.frameGeometry())


def test_tabs_share_the_remembered_folder(app, settings, tmp_path, monkeypatch):
    folder = tmp_path / "invoices"
    folder.mkdir()
    window = MainWindow(settings)
    window.pages_tab.open_file(make_pdf(folder / "doc.pdf", [101]))
    start_dirs = []
    monkeypatch.setattr(
        merge_tab.QFileDialog, "getOpenFileNames", lambda parent, title, start, *rest: (start_dirs.append(start), ([], ""))[1]
    )

    MergeTab(settings)._choose_files()

    assert start_dirs == [str(folder)]


def test_preferences_persist_and_apply_to_open_tabs(app, tmp_path):
    path = str(tmp_path / "preferences.ini")
    settings = Settings(QSettings(path, QSettings.Format.IniFormat))
    dialog = SettingsDialog(settings)
    dialog._theme.setCurrentIndex(dialog._theme.findData("dark"))
    dialog._thumbnails.setCurrentIndex(dialog._thumbnails.findData(190))
    dialog._images.setCurrentIndex(dialog._images.findData("image"))
    dialog.accept()
    restored = Settings(QSettings(path, QSettings.Format.IniFormat))
    assert (restored.theme(), restored.thumbnail_size(), restored.image_format()) == ("dark", 190, "image")
    window = MainWindow(restored)
    assert window.pages_tab._list.iconSize().width() == 190
    assert window.merge_tab._page_format_combo.isEnabled()
    assert window.merge_tab._page_format_combo.currentData().value == "image"
    from PySide6.QtGui import QPalette
    assert app.palette().color(QPalette.ColorRole.Base).lightness() < 100
    apply_theme(app, "light")


def test_cancelled_settings_do_not_change_preferences(app):
    settings = Settings()
    dialog = SettingsDialog(settings)
    dialog._theme.setCurrentIndex(dialog._theme.findData("dark"))
    dialog.reject()
    assert settings.theme() == "light"


def test_merge_image_format_is_available_before_adding_images(app, tmp_path):
    tab = MergeTab()
    assert tab._page_format_combo.isEnabled()
    tab._page_format_combo.setCurrentIndex(1)
    tab.add_files([make_pdf(tmp_path / "doc.pdf", [101])])
    assert tab._page_format_combo.isEnabled() and tab._page_format_combo.currentIndex() == 1


def test_resizing_thumbnails_keeps_pending_edits_and_selection(app, tmp_path):
    from pdftool.gui.pages_tab import PagesTab
    settings = Settings()
    tab = PagesTab(settings)
    tab.open_file(make_pdf(tmp_path / "doc.pdf", [101, 102]))
    tab._list.item(1).setSelected(True)
    tab._rotate_selected(90)
    before = tab._current_pages()
    settings.set_preferences("light", 190, "a4")
    tab.apply_preferences()
    for _ in range(4):
        app.processEvents()
    assert tab._current_pages() == before and tab._selected_rows() == [1]
    assert tab.has_unsaved_changes() and tab._history.can_undo
    assert tab._list.iconSize().width() == 190


def test_corrupt_appearance_preferences_have_safe_defaults():
    class CorruptStore:
        def value(self, key, defaultValue=None):
            return ["unexpected", "value"]
        def setValue(self, key, value):
            pass
    settings = Settings(CorruptStore())
    assert (settings.theme(), settings.thumbnail_size(), settings.image_format()) == ("light", 150, "a4")
