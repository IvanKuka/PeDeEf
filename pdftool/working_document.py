"""Private working copies retained for undo; user files are written only on save."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import tempfile
from uuid import uuid4

from pdftool.operations import PageRef, forget_password


class WorkingDocument:
    def __init__(self) -> None:
        self._directory: tempfile.TemporaryDirectory | None = None
        self.sources: dict[Path, tuple[Path, ...]] = {}

    def new_path(self) -> Path:
        if self._directory is None:
            self._directory = tempfile.TemporaryDirectory(prefix="pdftool-edit-")
        return Path(self._directory.name) / f"{uuid4().hex}.pdf"

    def original_sources(self, pages: Iterable[PageRef]) -> tuple[Path, ...]:
        return tuple(dict.fromkeys(source for page in pages for source in self.sources.get(page.path, (page.path,))))

    def close(self) -> None:
        if self._directory is not None:
            self._directory.cleanup()
            self._directory = None
        for path in self.sources:
            forget_password(path)
        self.sources.clear()

    def discard(self, path: Path) -> None:
        path.unlink(missing_ok=True)
        forget_password(path)
        self.sources.pop(path, None)
