"""Whether a newer release of the application is published on GitHub (no network code here).

Releases are created by the build workflow from tags such as "v2.0.1", with the
installers and a SHA256SUMS.txt listing their checksums. Only the public release
information is read; nothing about the user or their documents is sent.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

LATEST_RELEASE_API = "https://api.github.com/repos/IvanKuka/PeDeEf/releases/latest"
# Downloads are only ever taken from this repository's releases.
_DOWNLOAD_PREFIX = "https://github.com/IvanKuka/PeDeEf/releases/download/"
WINDOWS_INSTALLER = "PDF-Nastroje-Setup.exe"
CHECKSUMS = "SHA256SUMS.txt"

_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_CHECKSUM_LINE = re.compile(r"([0-9a-fA-F]{64}) [ *](.+)")


class UpdateError(Exception):
    """A failed update step; the message can be shown to the user as-is (Slovak)."""


@dataclass(frozen=True)
class Release:
    version: str  # e.g. "2.1.0"
    url: str  # the release page, where the installers are
    installer_url: str | None = None  # the Windows installer, if the release has one
    checksums_url: str | None = None


def parse_version(text: str) -> tuple[int, int, int] | None:
    """(major, minor, patch) of "2.0.1" or "v2.0.1"; None for anything else (e.g. "v2.1.0-beta")."""
    match = _VERSION.fullmatch(text.strip())
    return tuple(int(part) for part in match.groups()) if match else None  # type: ignore[return-value]


def newer_release(response: bytes, current_version: str) -> Release | None:
    """The release described by GitHub's "latest release" `response`, if it is newer than `current_version`.

    Anything unexpected – drafts, pre-releases, malformed answers – counts as no update:
    a failed check must never bother the user.
    """
    try:
        data = json.loads(response)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag, url = data.get("tag_name"), data.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str) or not url.startswith("https://github.com/"):
        return None
    latest, current = parse_version(tag), parse_version(current_version)
    if latest is None or current is None or latest <= current:
        return None
    downloads = {}
    for asset in data.get("assets") or ():
        if isinstance(asset, dict):
            name, link = asset.get("name"), asset.get("browser_download_url")
            if isinstance(name, str) and isinstance(link, str) and link.startswith(_DOWNLOAD_PREFIX):
                downloads[name] = link
    return Release(".".join(map(str, latest)), url, downloads.get(WINDOWS_INSTALLER), downloads.get(CHECKSUMS))


def verify_download(data: bytes, checksums: bytes, file_name: str) -> None:
    """Raise `UpdateError` unless `data` matches the checksum of `file_name` in a SHA256SUMS listing.

    Guards against a damaged or incomplete download before it is run.
    """
    expected = None
    for line in checksums.decode("utf-8", "replace").splitlines():
        match = _CHECKSUM_LINE.fullmatch(line.strip())
        if match and match.group(2) == file_name:
            expected = match.group(1).lower()
    if expected is None:
        raise UpdateError(f"Kontrolný súčet súboru {file_name} v novej verzii chýba.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise UpdateError("Stiahnutý inštalátor je poškodený (nesedí kontrolný súčet). Skúste to znova neskôr.")
