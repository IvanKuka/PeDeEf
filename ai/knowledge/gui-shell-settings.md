# GUI Shell, Settings and Updates

`pdftool/__main__.py` and `run_app.py` call `pdftool/app.py`. Startup configures QApplication, logging, style, settings and smoke-test modes. `pdftool/gui/main_window.py` owns Merge, Pages and Batch workspaces, global commands, settings and update lifecycle.

Shared UI: `gui/widgets.py`, `gui/style.py`, `gui/icons.py`, `gui/command_bar.py`. Rendering: `gui/thumbnails.py`, `gui/page_preview.py`, `gui/zoomed_page.py`; page-grid interactions live in `gui/page_grid.py`. Read `ai/specs/app-shell-navigation.md` and `ai/specs/preview-and-dialogs.md` before changing these contracts.

`gui/settings.py` validates stored values and provides safe defaults. `Settings()` uses memory; `Settings.for_application()` uses native QSettings. `gui/settings_dialog.py` edits preferences. Do not put passwords or document contents into settings.

`pdftool/updates.py` parses versions/releases and verifies checksums; `gui/update_check.py` owns Qt networking, installer download and startup. Preserve optional background checks, platform-specific installation behavior and handling of unsaved changes.

Tests: `tests/test_gui.py`, `tests/test_settings.py`, `tests/test_updates.py`. For installer/release changes read `ai/deployment/README.md`.
