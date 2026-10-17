# Application Shell

Owners: `pdftool/gui/main_window.py`, `pdftool/gui/command_bar.py`, `pdftool/gui/pages_tab.py`, `pdftool/gui/settings_dialog.py`.

- The main window contains Merge, Pages and Batch workspaces, with global open/settings/update controls.
- Page editing commands are grouped into a horizontally scrollable command band. Undo, redo, save and document close remain available beside the document identity.
- Keep labels, shortcuts, icon usage, enabled states and shared theme behavior consistent.
- Opening another document, closing or updating must retain existing handling of unsaved changes.
- Preferences are applied through existing settings/theme paths; invalid persisted values must not prevent startup.

Verify affected behavior in `tests/test_gui.py` and `tests/test_settings.py`; inspect update tests when update controls change.
