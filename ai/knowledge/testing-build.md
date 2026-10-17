# Testing and Build

`pyproject.toml` configures pytest to use `tests/` and repository-root imports. `requirements-dev.txt` includes runtime requirements, pytest and PyInstaller.

`tests/conftest.py` sets offscreen Qt and font discovery, provides one session QApplication, destroys test windows safely, clears PDF password caches and replaces dialogs with recorders. Reuse these fixtures; do not create competing QApplication instances. `tests/helpers.py` contains shared helpers.

Run an affected test module first, then broader tests when shared behavior changes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pending_edits.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

`build.py` prepares platform-specific OCR, runs tests, builds with PyInstaller, smoke-tests the packaged executable and creates installers/archives. `tests/test_build_ocr.py` covers build support; `tests/test_ocr_engine.py` exercises OCR integration. Do not report an OCR integration path as verified if it was skipped for missing tooling.

`.github/workflows/build.yml` builds Windows, Apple Silicon macOS and Intel macOS. Tag-triggered releases include checksums used by the updater. Read `ai/deployment/README.md` before packaging/release changes.
