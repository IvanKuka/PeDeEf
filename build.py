"""Build the standalone application for the current platform and pack it into a zip.

Usage (from the project root, with requirements-dev.txt installed):
    python build.py

Windows: dist/PDF Nastroje/ (folder with the .exe)  + dist/PDF-Nastroje-windows.zip
macOS:   dist/PDF Nastroje.app                       + dist/PDF-Nastroje-macos.zip

PyInstaller cannot cross-compile, so each platform must be built on that platform
(the GitHub Actions workflow in .github/workflows/build.yml does both).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
APP_NAME = "PDF Nastroje"
BUNDLE_ID = "sk.pdfnastroje"
IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"


def main() -> None:
    if not (IS_MAC or IS_WINDOWS):
        sys.exit(f"Nepodporovaná platforma: {sys.platform} (podporované: Windows, macOS)")

    run([sys.executable, "-m", "pytest", "-q"])
    BUILD_DIR.mkdir(exist_ok=True)
    icon = export_icon(BUILD_DIR / ("app.icns" if IS_MAC else "app.ico"))
    run_pyinstaller(icon)
    archive = package()
    print(f"\nHotovo: {archive}")


def run(command: list[str], **kwargs) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=ROOT, **kwargs)


def export_icon(target: Path) -> Path:
    # The icon is drawn by the same code the app uses at runtime, so the repository
    # has no image assets to keep in sync. Qt writes both .ico and .icns.
    script = (
        "import sys\n"
        "from PySide6.QtGui import QGuiApplication\n"
        "app = QGuiApplication([])\n"
        "from pdftool.gui.style import app_icon\n"
        "sys.exit(0 if app_icon().pixmap(256, 256).save(sys.argv[1]) else 1)\n"
    )
    # Offscreen: no window system is needed (and none exists on CI runners).
    run([sys.executable, "-c", script, str(target)], env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    return target


def run_pyinstaller(icon: Path) -> None:
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed",
        "--name", APP_NAME,
        "--icon", str(icon),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
    ]
    if IS_MAC:
        command += ["--osx-bundle-identifier", BUNDLE_ID]
    run([*command, str(ROOT / "run_app.py")])


def package() -> Path:
    if IS_MAC:
        archive = DIST_DIR / "PDF-Nastroje-macos.zip"
        archive.unlink(missing_ok=True)
        # ditto, unlike shutil, preserves the symlinks and permissions inside the .app
        # bundle (Qt frameworks rely on them); a bundle zipped otherwise may not start.
        run(["ditto", "-c", "-k", "--keepParent", str(DIST_DIR / f"{APP_NAME}.app"), str(archive)])
        return archive

    archive_base = DIST_DIR / "PDF-Nastroje-windows"
    return Path(shutil.make_archive(str(archive_base), "zip", root_dir=DIST_DIR, base_dir=APP_NAME))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Build zlyhal pri príkaze: {' '.join(map(str, exc.cmd))}")
