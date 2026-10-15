import hashlib
import json

import pytest

from pdftool.gui.main_window import MainWindow
from pdftool.gui.settings import Settings
from pdftool.gui.update_check import can_install_in_place
from pdftool.updates import Release, UpdateError, newer_release, parse_version, verify_download


def release_json(tag, **extra):
    return json.dumps({"tag_name": tag, "html_url": f"https://github.com/IvanKuka/PeDeEf/releases/tag/{tag}", **extra}).encode()


def test_only_a_strictly_newer_published_release_counts():
    assert newer_release(release_json("v2.1.0"), "2.0.1") == Release(
        "2.1.0", "https://github.com/IvanKuka/PeDeEf/releases/tag/v2.1.0"
    )
    assert newer_release(release_json("v2.0.10"), "2.0.9") is not None  # numbers, not text
    assert newer_release(release_json("v2.0.1"), "2.0.1") is None
    assert newer_release(release_json("v1.9.9"), "2.0.1") is None
    assert newer_release(release_json("v3.0.0", prerelease=True), "2.0.1") is None
    assert newer_release(release_json("v3.0.0-beta"), "2.0.1") is None
    assert parse_version("v2.0.1") == (2, 0, 1)


def test_unexpected_answers_never_report_an_update():
    assert newer_release(b"<html>rate limited</html>", "2.0.1") is None
    assert newer_release(b'{"message": "Not Found"}', "2.0.1") is None
    elsewhere = json.dumps({"tag_name": "v9.0.0", "html_url": "https://example.com/malware"}).encode()
    assert newer_release(elsewhere, "2.0.1") is None  # the button only ever opens GitHub


def test_window_offers_the_new_version_and_respects_the_setting(app, monkeypatch):
    checks = []
    monkeypatch.setattr("pdftool.gui.main_window.UpdateChecker.check", lambda self: checks.append(self))
    settings = Settings()
    window = MainWindow(settings)

    window.check_for_updates()
    checks[0].update_available.emit(Release("9.0.0", "https://github.com/IvanKuka/PeDeEf/releases/tag/v9.0.0"))

    assert not window._update_button.isHidden() and "9.0.0" in window._update_button.text()
    settings.set_check_for_updates(False)
    window.check_for_updates()
    assert len(checks) == 1 and not settings.check_for_updates()


def test_installer_is_taken_only_from_this_repository_and_must_match_its_checksum():
    base = "https://github.com/IvanKuka/PeDeEf/releases/download/v2.1.0/"
    assets = [
        {"name": "PDF-Nastroje-Setup.exe", "browser_download_url": base + "PDF-Nastroje-Setup.exe"},
        {"name": "SHA256SUMS.txt", "browser_download_url": "https://evil.example/SHA256SUMS.txt"},
    ]
    release = newer_release(release_json("v2.1.0", assets=assets), "2.0.1")
    assert release.installer_url == base + "PDF-Nastroje-Setup.exe"
    assert release.checksums_url is None  # not from this repository: no in-place update
    assert not can_install_in_place(release)

    installer = b"installer bytes"
    checksums = f"{hashlib.sha256(installer).hexdigest()}  PDF-Nastroje-Setup.exe\n".encode()
    verify_download(installer, checksums, "PDF-Nastroje-Setup.exe")
    with pytest.raises(UpdateError, match="poškodený"):
        verify_download(installer + b"!", checksums, "PDF-Nastroje-Setup.exe")
    with pytest.raises(UpdateError, match="chýba"):
        verify_download(installer, checksums, "iny.exe")
