"""Packaging must verify model caches and exercise the bundled OCR, not a system fallback."""

import hashlib
import subprocess

import pytest

import build


def test_rebuild_reuses_only_verified_models_and_refreshes_native_files(tmp_path, monkeypatch):
    source = tmp_path / "installation"
    (source / "tessdata").mkdir(parents=True)
    (source / "doc").mkdir()
    (source / "tesseract.exe").write_bytes(b"new executable")
    (source / "example.dll").write_bytes(b"native library")
    (source / "tessdata" / "pdf.ttf").write_bytes(b"font")
    (source / "doc" / "LICENSE").write_bytes(b"license")
    target = tmp_path / "build" / "tesseract"
    (target / "tessdata").mkdir(parents=True)
    expected = b"verified model"
    model = target / "tessdata" / "eng.traineddata"
    model.write_bytes(expected)
    monkeypatch.setattr(build, "IS_WINDOWS", True)
    monkeypatch.setattr(build, "TESSERACT_BUILD_DIR", target)
    monkeypatch.setattr(build, "TESSDATA_SHA256", {"eng": hashlib.sha256(expected).hexdigest()})
    monkeypatch.setattr(build, "_needed_libraries", lambda path: ["example.dll"])
    monkeypatch.setenv("TESSERACT_DIR", str(source))
    monkeypatch.setattr(build, "download_verified", lambda *args: pytest.fail("verified cached model should be reused"))
    assert build.prepare_tesseract() == target
    assert model.read_bytes() == expected
    assert (target / "tesseract.exe").read_bytes() == b"new executable"
    assert (target / "example.dll").read_bytes() == b"native library"
    model.write_bytes(b"corrupt cache")
    downloaded = []
    def download(url, checksum, path):
        downloaded.append(url)
        path.write_bytes(expected)
    monkeypatch.setattr(build, "download_verified", download)
    build.prepare_tesseract()
    assert len(downloaded) == 1 and model.read_bytes() == expected


def test_smoke_runs_real_ocr_and_does_not_accept_environment_override(tmp_path, monkeypatch):
    executable = tmp_path / "application.exe"
    monkeypatch.setattr(build, "built_executable", lambda: executable)
    monkeypatch.setenv("PDFTOOL_TESSERACT", "other-installation")
    called = []
    def run(command, **kwargs):
        called.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(build.subprocess, "run", run)
    build.smoke_test(check_ocr=True)
    assert [args[0][1] for args in called] == ["--smoke-test", "--ocr-smoke-test"]
    assert all("PDFTOOL_TESSERACT" not in options["env"] for _, options in called)


def test_failed_packaged_ocr_fails_the_build(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "built_executable", lambda: tmp_path / "application.exe")
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2 if command[-1] == "--ocr-smoke-test" else 0, "", "missing DLL")
    monkeypatch.setattr(build.subprocess, "run", run)
    with pytest.raises(SystemExit, match="missing DLL"):
        build.smoke_test(check_ocr=True)
