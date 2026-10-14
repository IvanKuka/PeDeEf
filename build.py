"""Build the standalone application for the current platform and package it.

Usage (from the project root, with requirements-dev.txt installed):
    python build.py

Windows: dist/PDF Nastroje/ (folder with the .exe), dist/PDF-Nastroje-windows.zip
         and the installer dist/PDF-Nastroje-Setup.exe (requires Inno Setup 6)
macOS:   dist/PDF Nastroje.app, dist/PDF-Nastroje-macos-<arch>.zip
         and the disk image dist/PDF-Nastroje-macos-<arch>.dmg, where <arch> is
         "apple-silicon" or "intel" depending on the Mac the build runs on

Before packaging, the built app is started once (smoke test) to catch packaging
problems that the tests, which run from source, cannot see.

PyInstaller cannot cross-compile, so each platform must be built on that platform
(the GitHub Actions workflow in .github/workflows/build.yml does both).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from pdftool import __version__

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
APP_NAME = "PDF Nastroje"
BUNDLE_ID = "sk.pdfnastroje"
IS_MAC = sys.platform == "darwin"
# An app built on an Apple Silicon Mac does not run on an Intel Mac and vice versa,
# so each architecture is built separately and named so users can tell them apart.
MAC_ARTIFACT_NAME = "PDF-Nastroje-macos-" + ("intel" if platform.machine() == "x86_64" else "apple-silicon")
IS_WINDOWS = sys.platform == "win32"
SMOKE_TEST_TIMEOUT_SECONDS = 120


def main() -> None:
    if not (IS_MAC or IS_WINDOWS):
        sys.exit(f"Nepodporovaná platforma: {sys.platform} (podporované: Windows, macOS)")

    run([sys.executable, "-m", "pytest", "-q"])
    BUILD_DIR.mkdir(exist_ok=True)
    icon = export_icon(BUILD_DIR / ("app.icns" if IS_MAC else "app.ico"))
    run_pyinstaller(icon)
    smoke_test()
    outputs = [build_zip()]
    outputs.append(build_dmg() if IS_MAC else build_windows_installer(icon))
    print("\nHotovo:", *outputs, sep="\n  ")


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


def built_executable() -> Path:
    if IS_MAC:
        return DIST_DIR / f"{APP_NAME}.app" / "Contents" / "MacOS" / APP_NAME
    return DIST_DIR / APP_NAME / f"{APP_NAME}.exe"


def smoke_test() -> None:
    """Start the packaged app with --smoke-test; it must start and exit cleanly.

    A missing library or Qt plugin only shows up in the packaged app. The offscreen
    platform needs no display, which CI runners do not have. A hang (e.g. an error
    dialog of the windowed build waiting for a click) ends in a timeout.
    """
    command = [str(built_executable()), "--smoke-test"]
    print("+", " ".join(command), flush=True)
    try:
        result = subprocess.run(
            command,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            text=True,
            errors="replace",
            timeout=SMOKE_TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        sys.exit(f"Zostavená aplikácia sa do {SMOKE_TEST_TIMEOUT_SECONDS} s neukončila (zamrznutá alebo chybové okno).")
    if result.returncode != 0:
        sys.exit(f"Zostavená aplikácia sa nespustila (kód {result.returncode}):\n{result.stdout}{result.stderr}")
    print("Smoke test: zostavená aplikácia sa úspešne spustila.")


def build_zip() -> Path:
    if IS_MAC:
        archive = DIST_DIR / f"{MAC_ARTIFACT_NAME}.zip"
        archive.unlink(missing_ok=True)
        # ditto, unlike shutil, preserves the symlinks and permissions inside the .app
        # bundle (Qt frameworks rely on them); a bundle zipped otherwise may not start.
        run(["ditto", "-c", "-k", "--keepParent", str(DIST_DIR / f"{APP_NAME}.app"), str(archive)])
        return archive

    archive_base = DIST_DIR / "PDF-Nastroje-windows"
    return Path(shutil.make_archive(str(archive_base), "zip", root_dir=DIST_DIR, base_dir=APP_NAME))


def build_dmg() -> Path:
    """Create the macOS disk image: the app plus a shortcut to /Applications to drag it onto.

    This is the usual way Mac apps are installed; Finder copies the app with a
    progress bar, and the app cannot be started half-copied from inside the image.
    """
    staging = BUILD_DIR / "dmg"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    run(["ditto", str(DIST_DIR / f"{APP_NAME}.app"), str(staging / f"{APP_NAME}.app")])
    (staging / "Applications").symlink_to("/Applications")

    dmg = DIST_DIR / f"{MAC_ARTIFACT_NAME}.dmg"
    command = [
        "hdiutil", "create",
        "-volname", "PDF Nástroje",
        "-srcfolder", str(staging),
        "-fs", "HFS+",
        "-format", "UDZO",
        "-ov", str(dmg),
    ]
    # hdiutil intermittently fails with "Resource busy" on CI runners; retrying is the
    # widely used workaround.
    for attempt in range(1, 4):
        try:
            run(command)
            break
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            print(f"hdiutil zlyhal, pokus {attempt + 1}/3…", flush=True)
            time.sleep(5)
    run(["hdiutil", "verify", str(dmg)])
    return dmg


def build_windows_installer(icon: Path) -> Path:
    iscc = find_iscc()
    run([
        str(iscc),
        f"/DAppVersion={__version__}",
        f"/DSourceDir={DIST_DIR / APP_NAME}",
        f"/DIconFile={icon}",
        f"/DOutputDir={DIST_DIR}",
        str(ROOT / "installer" / "pdf_nastroje.iss"),
    ])
    return DIST_DIR / "PDF-Nastroje-Setup.exe"


def find_iscc() -> Path:
    """Locate the Inno Setup compiler (per-user or machine-wide install, or the ISCC env variable)."""
    candidates = [
        os.environ.get("ISCC"),
        shutil.which("iscc"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6/ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6/ISCC.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    sys.exit(
        "Inno Setup 6 sa nenašiel, inštalátor nie je možné zostaviť.\n"
        "Nainštalujte ho príkazom: winget install --id JRSoftware.InnoSetup --scope user\n"
        "alebo nastavte premennú prostredia ISCC na cestu k ISCC.exe."
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Build zlyhal pri príkaze: {' '.join(map(str, exc.cmd))}")
