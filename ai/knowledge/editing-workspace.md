# Editing Workspace and History

`pdftool/gui/pages_tab.py` coordinates opening, page selection, page actions, feature dialogs, history and saving. It is a broad orchestrator: inspect the relevant action and its collaborators rather than reading it as the implementation of every tool.

- `pdftool/history.py` owns UI-independent snapshots and undo/redo.
- `pdftool/working_document.py` owns private temporary PDFs, original source mappings and cleanup.
- `pdftool/project.py` owns a versioned project format, source validation and SHA-256 fingerprints. Inspect call sites before assuming a project capability is exposed in the GUI.
- `pdftool/gui/page_grid.py` owns page-grid interactions; thumbnail and preview modules own rendering.

`_apply_document_edit` writes a protected private copy, validates it and commits one undoable step. Original files remain untouched until a save action. `_save_current` confirms replacement and preserves protection; `_save` coordinates Save As. A failed save must retain both the old file and pending work.

Read `ai/specs/document-editing.md` and `ai/specs/preview-and-dialogs.md`. Tests: `tests/test_pending_edits.py`, `tests/test_history.py`, `tests/test_gui.py`, `tests/test_project.py`.
