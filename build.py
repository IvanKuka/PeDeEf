"""Build the standalone application for the current platform and package it.

Usage (from the project root, with requirements-dev.txt installed):
    python build.py

Windows: dist/PDF Nastroje/ (folder with the .exe), dist/PDF-Nastroje-windows.zip
         and the installer dist/PDF-Nastroje-Setup.exe (requires Inno Setup 6)
macOS:   dist/PDF Nastroje.app, dist/PDF-Nastroje-macos-<arch>.zip
         and the disk image dist/PDF-Nastroje-macos-<arch>.dmg, where <arch> is
         "apple-silicon" or "intel" depending on the Mac the build runs on

On Windows, OCR (Tesseract) is bundled: it is copied from a Tesseract installation
into build/tesseract (see prepare_tesseract), where the app also finds it when run
from source, and into the dist folder next to the executable.

Before packaging, the built app is started once (smoke test) to catch packaging
problems that the tests, which run from source, cannot see.

PyInstaller cannot cross-compile, so each platform must be built on that platform
(the GitHub Actions workflow in .github/workflows/build.yml does both).
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
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
TESSERACT_BUILD_DIR = BUILD_DIR / "tesseract"
# Fast models: a fraction of the size of the "best" ones and much quicker, with similar
# accuracy on printed documents. Apache 2.0, like Tesseract. Pinned and verified.
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/{}.traineddata"
TESSDATA_SHA256 = {
    "slk": "fbcc400a9c74c6a13d922fcb1211b655d1b165387b675ed75cd2dbd756b974a5",
    "ces": "934bcaf97ef3348413263331131c9fa7f55f30db333c711929c124fb635f7e1b",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
    "deu": "19d219bbb6672c869d20a9636c6816a81eb9a71796cb93ebe0cb1530e2cdb22d",
}


def main() -> None:
    if not (IS_MAC or IS_WINDOWS):
        sys.exit(f"Nepodporovaná platforma: {sys.platform} (podporované: Windows, macOS)")

    BUILD_DIR.mkdir(exist_ok=True)
    # Before the tests: they use this copy, so OCR is tested with what will be shipped.
    tesseract = prepare_tesseract()
    run([sys.executable, "-m", "pytest", "-q"])
    icon = export_icon(BUILD_DIR / ("app.icns" if IS_MAC else "app.ico"))
    run_pyinstaller(icon)
    if tesseract is not None:
        # Next to the executable, where pdftool.ocr looks for the application's own copy.
        shutil.copytree(tesseract, DIST_DIR / APP_NAME / "tesseract")
    smoke_test(check_ocr=tesseract is not None)
    outputs = [build_zip()]
    outputs.append(build_dmg() if IS_MAC else build_windows_installer(icon))
    print("\nHotovo:", *outputs, sep="\n  ")


def prepare_tesseract() -> Path | None:
    """Put the OCR program with the libraries it loads and the language data into build/tesseract.

    The program is taken from a Tesseract installation (Windows: UB Mannheim build, by default
    in Program Files, or the folder in the TESSERACT_DIR environment variable). Only the files
    tesseract.exe really loads are copied: the installation also holds training tools that
    would more than double the size. Returns None where OCR is not bundled yet (macOS).
    """
    if not IS_WINDOWS:
        print("OCR (Tesseract) sa do balíka pre macOS zatiaľ nepribaľuje; aplikácia použije Tesseract z Homebrew.")
        return None
    source = Path(os.environ.get("TESSERACT_DIR") or Path(os.environ.get("ProgramFiles", "")) / "Tesseract-OCR")
    if not (source / "tesseract.exe").is_file():
        sys.exit(
            f"Tesseract sa v „{source}“ nenašiel, OCR nie je možné pribaliť.\n"
            "Nainštalujte ho príkazom: winget install --id UB-Mannheim.TesseractOCR --exact\n"
            "alebo nastavte premennú prostredia TESSERACT_DIR na jeho priečinok."
        )
    # Reuse only verified models when rebuilding offline; the executable and DLLs
    # are always copied afresh from the installed Tesseract.
    models = {}
    for language, sha256 in TESSDATA_SHA256.items():
        previous = TESSERACT_BUILD_DIR / "tessdata" / f"{language}.traineddata"
        if previous.is_file():
            data = previous.read_bytes()
            if hashlib.sha256(data).hexdigest() == sha256:
                models[language] = data
    shutil.rmtree(TESSERACT_BUILD_DIR, ignore_errors=True)
    tessdata = TESSERACT_BUILD_DIR / "tessdata"
    tessdata.mkdir(parents=True)
    for name in ["tesseract.exe", *_needed_libraries(source / "tesseract.exe")]:
        shutil.copy2(source / name, TESSERACT_BUILD_DIR / name)
    shutil.copy2(source / "tessdata" / "pdf.ttf", tessdata / "pdf.ttf")  # the invisible font of the text layer
    for language, sha256 in TESSDATA_SHA256.items():
        target = tessdata / f"{language}.traineddata"
        if language in models:
            target.write_bytes(models[language])
        else:
            download_verified(TESSDATA_URL.format(language), sha256, target)
    shutil.copy2(source / "doc" / "LICENSE", TESSERACT_BUILD_DIR / "LICENSE-tesseract.txt")
    shutil.copy2(ROOT / "installer" / "tesseract-notices.txt", TESSERACT_BUILD_DIR / "NOTICES.txt")
    return TESSERACT_BUILD_DIR


def _needed_libraries(executable: Path) -> list[str]:
    """DLLs from the executable's folder that it loads, directly or through other DLLs."""
    import pefile  # installed with PyInstaller on Windows

    folder = executable.parent
    available = {path.name.lower(): path.name for path in folder.glob("*.dll")}
    needed: set[str] = set()
    pending = [executable]
    while pending:
        binary = pefile.PE(str(pending.pop()), fast_load=True)
        binary.parse_data_directories(
            directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ]
        )
        entries = getattr(binary, "DIRECTORY_ENTRY_IMPORT", []) + getattr(binary, "DIRECTORY_ENTRY_DELAY_IMPORT", [])
        for entry in entries:
            name = entry.dll.decode().lower()
            if name in available and available[name] not in needed:
                needed.add(available[name])
                pending.append(folder / available[name])
        binary.close()
    return sorted(needed)


def download_verified(url: str, sha256: str, target: Path) -> None:
    """Download `url` to `target`, failing unless the content has the expected SHA-256."""
    print("+ stiahnuť", url, flush=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != sha256.lower():
        sys.exit(f"Stiahnutý súbor {url} nemá očakávaný kontrolný súčet – build sa zastavil.")
    target.write_bytes(data)


def run(command: list[str], **kwargs) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=ROOT, **kwargs)


def export_icon(target: Path) -> Path:
    # The icon is drawn by the same code the app uses at runtime, so the repository
    # has no image assets to keep in sync.
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from PySide6.QtGui import QGuiApplication\n"
        "app = QGuiApplication([])\n"
        "from pdftool.gui.style import save_app_icon\n"
        "save_app_icon(Path(sys.argv[1]))\n"
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


def smoke_test(check_ocr: bool = False) -> None:
    """Start the packaged app with --smoke-test; it must start and exit cleanly.

    A missing library or Qt plugin only shows up in the packaged app. The offscreen
    platform needs no display, which CI runners do not have. A hang (e.g. an error
    dialog of the windowed build waiting for a click) ends in a timeout.
    """
    flags = ["--smoke-test"]
    if check_ocr:
        flags.append("--ocr-smoke-test")
    environment = {key: value for key, value in os.environ.items() if key != "PDFTOOL_TESSERACT"}
    environment["QT_QPA_PLATFORM"] = "offscreen"
    # Offscreen Qt needs an explicit font directory to render a recognisable test image.
    for folder in (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path("/System/Library/Fonts")):
        if folder.is_dir():
            environment.setdefault("QT_QPA_FONTDIR", str(folder))
            break
    for flag in flags:
        command = [str(built_executable()), flag]
        print("+", " ".join(command), flush=True)
        try:
            result = subprocess.run(
                command, env=environment, capture_output=True, text=True, errors="replace",
                timeout=SMOKE_TEST_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            sys.exit(f"Smoke test {flag} sa do {SMOKE_TEST_TIMEOUT_SECONDS} s neukončil.")
        if result.returncode != 0:
            sys.exit(f"Smoke test {flag} zlyhal (kód {result.returncode}):\n{result.stdout}{result.stderr}")
        print(f"Smoke test {flag}: úspešný.")


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
