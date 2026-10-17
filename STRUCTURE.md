# Project Structure

PDF Nastroje is a Python desktop PDF editor for Windows and macOS. The documentation hierarchy follows the FinanceApp pattern while retaining this project's Python/Qt architecture.

```text
AdobeNew/
|-- AGENTS.md                 AI coding instructions
|-- CLAUDE.md                 Identical instruction mirror
|-- STRUCTURE.md              Canonical repository map
|-- README.md                 User guide, setup and development commands
|-- ai/
|   |-- index.json            Machine-readable task routing
|   |-- structure.md          AI documentation map
|   |-- task-routing.md       Task-to-module routing
|   |-- conventions.md        Implementation conventions
|   |-- workflows.md          Change and verification workflows
|   |-- spec.md               Cross-module invariants
|   |-- spec-interview.md      Larger-feature clarification process
|   |-- prompt-templates.md   Reusable task prompts
|   |-- operations-security.md
|   |-- knowledge/            Current module ownership and entry points
|   |-- specs/                Current reusable GUI/behavior contracts
|   |-- deployment/           Build, packaging and release guidance
|   `-- archive/              Historical feature proposals
|-- pdftool/                  Core PDF logic and application entry point
|   `-- gui/                  Qt workspaces, dialogs, rendering and settings
|-- tests/                    Core and offscreen GUI tests
|-- installer/                Inno Setup script and OCR license notices
|-- .github/workflows/        Windows/macOS build and release automation
|-- pyproject.toml            Project metadata and pytest configuration
|-- requirements.txt          Runtime dependencies
|-- requirements-dev.txt      Test/build dependencies
|-- run_app.py                PyInstaller launcher
`-- build.py                  Platform-native build and packaging
```

## Source ownership

| Area | Entry points |
|---|---|
| Startup and application shell | `pdftool/__main__.py`, `pdftool/app.py`, `pdftool/gui/main_window.py` |
| PDF reading, writing, page references, crops and metadata | `pdftool/operations.py`, `pdftool/page_ranges.py`, `pdftool/pdf_resources.py` |
| Editing workspace and history | `pdftool/gui/pages_tab.py`, `pdftool/history.py`, `pdftool/working_document.py`, `pdftool/project.py` |
| Merge and batch | `pdftool/gui/merge_tab.py`, `pdftool/batch.py`, `pdftool/gui/batch_tab.py` |
| Preview, selection and commands | `pdftool/gui/page_grid.py`, `pdftool/gui/thumbnails.py`, `pdftool/gui/page_preview.py`, `pdftool/gui/zoomed_page.py`, `pdftool/gui/command_bar.py` |
| Overlays and forms | `pdftool/stamps.py`, `pdftool/forms.py`, `pdftool/gui/stamp_layer.py`, `pdftool/gui/text_boxes.py`, `pdftool/gui/signature.py`, `pdftool/gui/form_filling.py` |
| OCR, redaction and image operations | `pdftool/ocr.py`, `pdftool/gui/recognition.py`, `pdftool/gui/redaction.py`, `pdftool/gui/images.py` |
| Search, comparison and blank pages | `pdftool/text_search.py`, `pdftool/gui/search_bar.py`, `pdftool/gui/compare.py`, `pdftool/gui/blank_pages.py` |
| Certificate signatures | `pdftool/signing.py`, `pdftool/gui/digital_signature_dialog.py` |
| Shared UI and preferences | `pdftool/gui/widgets.py`, `pdftool/gui/style.py`, `pdftool/gui/icons.py`, `pdftool/gui/settings.py`, `pdftool/gui/settings_dialog.py` |
| Updates | `pdftool/updates.py`, `pdftool/gui/update_check.py` |

Feature dialogs are adjacent to their GUI implementation (`*_dialog.py`). Tests use matching `tests/test_*.py` files; `tests/conftest.py` supplies Qt and dialog fixtures, and `tests/helpers.py` supplies shared helpers.

## Local and generated files

`.venv/`, `build/`, `dist/`, `__pycache__/` and pytest caches are local/generated, not architecture templates. Historical untracked `docs/features/` proposals have moved to `ai/archive/feature-proposals/`. New design documentation belongs in `ai/` and is versioned.
