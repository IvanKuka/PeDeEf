"""Asks GitHub in the background whether a newer version is available, and installs it on Windows.

Qt's network stack is used rather than urllib: it uses the operating system's TLS
and certificate store on both Windows and macOS, while a packaged Python on macOS
has no certificates of its own.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QProcess, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QWidget

from pdftool import __version__
from pdftool.gui.widgets import progress_dialog
from pdftool.updates import (
    LATEST_RELEASE_API,
    WINDOWS_INSTALLER,
    Release,
    UpdateError,
    newer_release,
    verify_download,
)

logger = logging.getLogger(__name__)

_TIMEOUT_MS = 10_000


class UpdateChecker(QObject):
    update_available = Signal(Release)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)

    def check(self) -> None:
        """Start the check; `update_available` is emitted only if a newer release exists."""
        request = _request(LATEST_RELEASE_API, _TIMEOUT_MS)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        reply = self._network.get(request)
        reply.finished.connect(lambda: self._finished(reply))

    def _finished(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                # Offline, blocked or rate-limited: nothing to tell the user, the next start tries again.
                logger.info("Kontrola novej verzie zlyhala: %s", reply.errorString())
                return
            release = newer_release(bytes(reply.readAll().data()), __version__)
            if release is not None:
                self.update_available.emit(release)
        finally:
            reply.deleteLater()


def _request(url: str, timeout_ms: int) -> QNetworkRequest:
    request = QNetworkRequest(QUrl(url))
    # GitHub rejects requests without a User-Agent.
    request.setRawHeader(b"User-Agent", f"PDF-Nastroje/{__version__}".encode("ascii"))
    request.setTransferTimeout(timeout_ms)
    return request


def can_install_in_place(release: Release) -> bool:
    """Whether this copy can update itself: the installed Windows app, with a verifiable installer.

    On macOS the app is not signed by Apple, so replacing it in place would run into
    Gatekeeper; there (and when run from source) the release page is opened instead.
    """
    return (
        sys.platform == "win32"
        and getattr(sys, "frozen", False)
        and release.installer_url is not None
        and release.checksums_url is not None
    )


def download_installer(parent: QWidget, release: Release) -> Path | None:
    """Download and verify the Windows installer of `release`; None if the user cancels."""
    assert release.installer_url is not None and release.checksums_url is not None
    network = QNetworkAccessManager()
    checksums = _download(network, release.checksums_url, None)
    with progress_dialog(parent, "Aktualizácia", f"Sťahuje sa verzia {release.version}…", 100, minimum_duration=0) as report:
        installer = _download(network, release.installer_url, report)
    if installer is None or checksums is None:
        return None
    verify_download(installer, checksums, WINDOWS_INSTALLER)
    path = Path(tempfile.mkdtemp(prefix="pdf-nastroje-update-")) / f"PDF-Nastroje-Setup-{release.version}.exe"
    try:
        path.write_bytes(installer)
    except OSError as exc:
        raise UpdateError(f"Inštalátor sa nepodarilo uložiť: {exc}") from exc
    return path


def _download(network: QNetworkAccessManager, url: str, report) -> bytes | None:
    """The content at `url`; None if cancelled through `report` (see widgets.progress_dialog)."""
    # Release files are served through a redirect to GitHub's download servers; Qt 6 follows
    # it as long as it stays on HTTPS.
    reply = network.get(_request(url, 60_000))
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    cancelled = False
    if report is not None:
        def progress(received: int, total: int) -> None:
            nonlocal cancelled
            if not report(round(received * 100 / total) if total > 0 else 0):
                cancelled = True
                reply.abort()

        reply.downloadProgress.connect(progress)
    if not reply.isFinished():
        loop.exec()
    try:
        if cancelled:
            return None
        if reply.error() != QNetworkReply.NetworkError.NoError:
            raise UpdateError(f"Novú verziu sa nepodarilo stiahnuť: {reply.errorString()}")
        return bytes(reply.readAll().data())
    finally:
        reply.deleteLater()


def start_installer(path: Path) -> None:
    """Run the installer without questions; it replaces the closed app and starts it again."""
    # /update=1 makes the installer start the app afterwards (see installer/pdf_nastroje.iss);
    # /SILENT still shows its progress, so the user sees that something is happening.
    arguments = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/update=1"]
    started, _pid = QProcess.startDetached(str(path), arguments)
    if not started:
        raise UpdateError("Inštalátor novej verzie sa nepodarilo spustiť.")
