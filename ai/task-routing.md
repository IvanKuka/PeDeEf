# Task Routing

Read the matching knowledge module and relevant spec, then the listed source and tests. Do not scan the whole repository for a local change. `ai/index.json` provides the same routing in machine-readable form.

| Task | Knowledge | Start in source | Tests |
|---|---|---|---|
| PDF read/write, page ranges, crop, metadata, passwords | `ai/knowledge/pdf-core.md` | `pdftool/operations.py`, `pdftool/page_ranges.py` | `tests/test_operations.py`, `tests/test_page_ranges.py`, `tests/test_crop.py`, `tests/test_properties.py`, `tests/test_passwords.py` |
| Page editing, save, undo/redo, projects | `ai/knowledge/editing-workspace.md` | `pdftool/gui/pages_tab.py`, `pdftool/history.py`, `pdftool/working_document.py`, `pdftool/project.py` | `tests/test_gui.py`, `tests/test_history.py`, `tests/test_pending_edits.py`, `tests/test_project.py` |
| Merge and batch | `ai/knowledge/pdf-core.md` | `pdftool/gui/merge_tab.py`, `pdftool/batch.py`, `pdftool/gui/batch_tab.py` | `tests/test_operations.py`, `tests/test_batch.py` |
| Overlays, forms, OCR, redaction, images, signatures, search or comparison | `ai/knowledge/document-tools.md` | Follow the feature/source/test table in that module | Follow the same table |
| Startup, navigation, command bar, preview, theme, settings | `ai/knowledge/gui-shell-settings.md` | `pdftool/app.py`, `pdftool/gui/main_window.py`, `pdftool/gui/command_bar.py`, `pdftool/gui/settings.py` | `tests/test_gui.py`, `tests/test_settings.py` |
| Update checks and installers | `ai/knowledge/gui-shell-settings.md`, `ai/knowledge/testing-build.md` | `pdftool/updates.py`, `pdftool/gui/update_check.py`, `build.py` | `tests/test_updates.py`, `tests/test_build_ocr.py` |
| Build, CI or test infrastructure | `ai/knowledge/testing-build.md` | `build.py`, `.github/workflows/build.yml`, `tests/conftest.py` | Relevant tests and packaged smoke checks |

For UI contracts, consult `ai/specs/README.md`. For output safety, redaction, credentials or signing, also consult `ai/operations-security.md`. Historical proposals are under `ai/archive/`; they are not authoritative implementation docs.
