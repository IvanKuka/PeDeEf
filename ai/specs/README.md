# Reusable UI and Behavior Specs

These documents describe current implementation contracts, not a feature backlog. Read the matching spec before changing a shared pattern; update it when intentional behavior changes.

| Area | Spec | Main source |
|---|---|---|
| Workspace navigation, commands, settings | [Application shell](app-shell-navigation.md) | `pdftool/gui/main_window.py`, `pdftool/gui/command_bar.py`, `pdftool/gui/settings_dialog.py` |
| Edits, undo/redo, save/cancel | [Document editing](document-editing.md) | `pdftool/gui/pages_tab.py`, `pdftool/history.py`, `pdftool/working_document.py` |
| Selection, previews and tool dialogs | [Preview and dialogs](preview-and-dialogs.md) | `pdftool/gui/page_grid.py`, `pdftool/gui/zoomed_page.py`, `pdftool/gui/stamp_layer.py` |

Add a focused spec when a new reusable contract needs documentation. Include owning source, observable behavior, failure/cancel semantics and relevant verification. Historical proposals belong in `ai/archive/`, not this index.
