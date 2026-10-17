# Implementation Conventions

- Follow existing Python naming, type annotations, dataclasses and `pathlib.Path` usage. Do not introduce a new framework or formatter just for a local change.
- Core PDF/domain modules must not acquire widget responsibilities. Qt rendering, image conversion, signals and dialogs belong in `pdftool/gui/`.
- Reuse `PageRef`, existing page-range parsing, history snapshots and atomic write helpers instead of duplicating them.
- Expected PDF failures use `PdfToolError`; password prompts are coordinated by `pdftool/gui/passwords.py`. Keep cancellation distinct from failure.
- Keep user-facing messages in Slovak. Reuse shared widgets, icons, theme helpers and preview surfaces.
- Use `Settings.for_application()` for persistent application settings; plain `Settings()` has an in-memory store suitable for tests.
- Prefer narrow adjacent feature modules over adding responsibilities to `operations.py` or `gui/pages_tab.py`. Avoid unrelated refactors.
- Tests belong in the corresponding `tests/test_*.py`; reuse `tests/conftest.py` and `tests/helpers.py`. GUI tests use offscreen Qt.
- Do not add dependencies without checking existing capabilities, platform support, distribution size and license compatibility. See `requirements*.txt` and README license guidance.
- Update documentation with the implementation; do not make historical proposals the only description of shipped behavior.
