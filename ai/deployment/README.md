# Desktop Build and Release

This project distributes desktop installers rather than a server deployment. `build.py` and `.github/workflows/build.yml` are authoritative; do not import FinanceApp's Docker/database deployment setup.

## Local build

Use Python 3.11+ and install `requirements-dev.txt` into the local virtual environment. Run from repository root:

```powershell
.\.venv\Scripts\python.exe build.py
```

Build on the target platform: PyInstaller does not cross-compile. Windows requires Tesseract and Inno Setup 6. macOS creates a native app, ZIP and DMG for the host architecture; CI installs Tesseract and language data for OCR integration tests.

The script prepares OCR, runs pytest, builds, starts the packaged app with `--smoke-test`, and on Windows verifies bundled OCR with `--ocr-smoke-test` before packaging. Preserve pinned language-data checksums and `installer/tesseract-notices.txt`.

## Outputs and CI

- Windows: `dist/PDF-Nastroje-Setup.exe`, `dist/PDF-Nastroje-windows.zip`.
- macOS: architecture-specific `PDF-Nastroje-macos-<arch>.dmg` and `.zip` in `dist/`.
- CI builds all three platform/architecture variants and uploads artifacts.
- A pushed `v*` tag triggers the release job, which publishes six distribution files plus `SHA256SUMS.txt`. Creating/pushing a release tag is a publication action, not a local verification step.

For update protocol changes inspect `pdftool/updates.py`, `pdftool/gui/update_check.py` and `tests/test_updates.py` together. For end-user installation instructions see root `README.md`.
