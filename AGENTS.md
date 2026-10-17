# AI Agent Instructions

## Fast start

- Read `STRUCTURE.md`, then `ai/task-routing.md` (or `ai/index.json`).
- Read only the relevant `ai/knowledge/` module and matching `ai/specs/` document before source.
- Read `ai/conventions.md` before editing; use `ai/spec.md` for cross-module changes and `ai/workflows.md` for larger work.
- Inspect existing code and tests before implementing. Ask when requirements remain unclear; do not invent APIs or placeholder behavior.

## Project

PDF Nastroje is a local Python 3.11+ desktop application using PySide6/QtPdf, pypdf and pyHanko. `pdftool/` owns application code, `pdftool/gui/` owns Qt presentation and rendering, and `tests/` covers both. This is not a web application and has no application database.

## Commands (repository root, PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pdftool
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_operations.py -q
.\.venv\Scripts\python.exe build.py
```

Build only when packaging verification is needed: it prepares OCR, runs tests, packages the app and runs smoke checks. See `ai/deployment/README.md` for prerequisites.

## Engineering rules

- Keep patches small, readable and consistent with existing code. Search before adding an abstraction or dependency.
- Keep PDF/domain logic outside Qt widgets where possible; Qt-specific rasterization stays in `pdftool/gui/`.
- Keep modules cohesive. `operations.py` and `gui/pages_tab.py` are broad orchestration hotspots; avoid adding unrelated responsibilities.
- Preserve behavior unless the task explicitly changes it. Refactor nearby code only when safe and relevant.
- Use useful diagnostics and existing `PdfToolError`/GUI error handling. Never silently discard failures or pending work.
- Preserve atomic output writes, password lifetime rules, undo/redo, and cancel/failure behavior.
- Never log or persist document passwords, private keys, document contents or signing credentials.
- Cropping and overlays do not securely remove content. Permanent redaction must retain its raster replacement and output verification.
- Signature integrity checks are offline and do not establish certificate trust.
- Keep Slovak user-facing text and existing accessibility/keyboard behavior consistent.
- Prefer existing dependencies; PyMuPDF is deliberately excluded because of its AGPL license.
- Run checks proportional to risk, including failure paths for document writes. Report what actually ran and any limitations.

## Documentation maintenance

- Keep `AGENTS.md` and `CLAUDE.md` identical.
- Update `STRUCTURE.md`, `ai/structure.md`, `ai/task-routing.md` and `ai/index.json` together when ownership or navigation changes.
- Update the relevant knowledge/spec document with behavior changes, and `README.md` for user-facing changes.
- `ai/archive/` contains historical proposals, not current requirements. Verify them against code before using them.
- New feature dossiers belong under `ai/feature-<name>/`; archive them after durable decisions are incorporated into knowledge/specs.
- Do not copy framework-specific rules, machine settings, credentials, hooks or generated artifacts from another repository.
