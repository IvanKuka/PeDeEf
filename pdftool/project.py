"""Work-in-progress projects: the pages being assembled, saved to continue later (no GUI dependencies).

A project refers to its source files – it does not contain them – and records a
fingerprint of each, so a source that changed since is detected instead of its
old page numbers being applied to a different document. Passwords are never
stored. All raised `PdfToolError` messages are user-facing (Slovak).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from pdftool.operations import DocumentInfo, PageRef, PdfToolError, is_valid_crop, page_count

PROJECT_SUFFIX = ".pdfprojekt"
_FORMAT = "pdf-nastroje-projekt"
_VERSION = 1


@dataclass(frozen=True)
class Project:
    main_source: Path  # the document the project was started from, used for names of outputs
    pages: tuple[PageRef, ...]
    info: DocumentInfo | None = None


@dataclass(frozen=True)
class SourceProblem:
    """A source file that is missing or no longer the one the project was made with."""

    stored_path: Path
    missing: bool  # False: the file exists but changed since the project was saved


# Called for each problem; returns the file to use instead (for a missing source), the same
# path to use the changed file anyway, or None to give up loading the project.
ResolveSource = Callable[[SourceProblem], Path | None]


def save_project(project: Project, path: Path) -> None:
    path = Path(path)
    sources = list(dict.fromkeys([project.main_source, *(page.path for page in project.pages)]))
    data = {
        "format": _FORMAT,
        "version": _VERSION,
        "main_source": 0,
        "sources": [_describe_source(source, path.parent) for source in sources],
        "pages": [
            {
                "source": sources.index(page.path),
                "index": page.index,
                "rotation": page.rotation,
                "crop": list(page.crop) if page.crop else None,
            }
            for page in project.pages
        ],
        "info": None if project.info is None else asdict(project.info),
    }
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)  # an interrupted save never damages an existing project
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise PdfToolError(f"Projekt „{path.name}“ sa nepodarilo uložiť: {exc}") from exc


def load_project(
    path: Path, resolve: ResolveSource, count_pages: Callable[[Path], int] = page_count
) -> Project | None:
    """Read and check a project; None when the user gave up on a missing or changed source.

    `count_pages` lets the GUI ask for the password of a protected source.
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise PdfToolError(f"Projekt „{path.name}“ sa nepodarilo načítať: {exc}") from exc
    try:
        return _read(data, path.parent, resolve, count_pages)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise PdfToolError(f"Súbor „{path.name}“ nie je platný projekt tejto aplikácie.") from exc


def _read(data: dict, project_dir: Path, resolve: ResolveSource, count_pages: Callable[[Path], int]) -> Project | None:
    _validate_data(data)
    if data.get("format") != _FORMAT:
        raise ValueError("not a project")
    if data.get("version") != _VERSION:
        raise PdfToolError("Projekt pochádza z inej verzie aplikácie a nedá sa otvoriť.")

    sources: list[Path] = []
    for entry in data["sources"]:
        source = _locate(entry, project_dir, resolve)
        if source is None:
            return None
        sources.append(source)

    counts = {source: count_pages(source) for source in set(sources)}
    pages = []
    for entry in data["pages"]:
        source = sources[int(entry["source"])]
        index = int(entry["index"])
        if not 0 <= index < counts[source]:
            raise PdfToolError(f"Súbor „{source.name}“ už nemá stranu {index + 1}, ktorú projekt používa.")
        crop = entry.get("crop")
        pages.append(
            PageRef(source, index, int(entry.get("rotation", 0)) % 360, tuple(float(m) for m in crop) if crop else None)
        )
    if not pages:
        raise ValueError("no pages")
    info = data.get("info")
    return Project(
        sources[int(data.get("main_source", 0))], tuple(pages), DocumentInfo(**info) if info is not None else None
    )


def _validate_data(data: object) -> None:
    """Validate the entire file before resolving sources or changing the open document."""
    if not isinstance(data, dict):
        raise ValueError("project must be an object")
    if data.get("format") != _FORMAT or data.get("version") != _VERSION:
        # Format/version diagnostics are handled by _read.
        return
    sources, pages = data.get("sources"), data.get("pages")
    if not isinstance(sources, list) or not sources or not isinstance(pages, list) or not pages:
        raise ValueError("sources and pages must be nonempty lists")
    for entry in sources:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not entry["path"]:
            raise ValueError("invalid source path")
        if entry.get("relative_path") is not None and not isinstance(entry["relative_path"], str):
            raise ValueError("invalid relative path")
        fingerprint = entry.get("sha256")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
            raise ValueError("invalid source fingerprint")
    def source_index(value: object) -> bool:
        return type(value) is int and 0 <= value < len(sources)

    if not source_index(data.get("main_source", 0)):
        raise ValueError("invalid main source")
    for entry in pages:
        if not isinstance(entry, dict) or not source_index(entry.get("source")):
            raise ValueError("invalid page source")
        if type(entry.get("index")) is not int or entry["index"] < 0:
            raise ValueError("invalid page index")
        rotation = entry.get("rotation", 0)
        if type(rotation) is not int or rotation % 90:
            raise ValueError("invalid rotation")
        crop = entry.get("crop")
        if crop is not None:
            if not isinstance(crop, list) or len(crop) != 4:
                raise ValueError("crop needs four margins")
            if any(type(m) not in (int, float) or not 0 <= m <= 1 or not math.isfinite(m) for m in crop) or not is_valid_crop(tuple(crop)):
                raise ValueError("invalid crop margins")
    info = data.get("info")
    if info is not None and (
        not isinstance(info, dict)
        or any(key not in DocumentInfo.__dataclass_fields__ or not isinstance(value, str) for key, value in info.items())
    ):
        raise ValueError("invalid document properties")


def _locate(entry: dict, project_dir: Path, resolve: ResolveSource) -> Path | None:
    stored = Path(entry["path"])
    # A project moved together with its documents still finds them through the relative path.
    candidates = [stored, project_dir / entry["relative_path"]] if entry.get("relative_path") else [stored]
    found = next((candidate for candidate in candidates if candidate.is_file()), None)
    while True:
        if found is None:
            found = resolve(SourceProblem(stored, missing=True))
            if found is None:
                return None
            continue
        if _fingerprint(found) == entry["sha256"]:
            return found
        # Changed since the project was saved: its page numbers may now point elsewhere.
        decision = resolve(SourceProblem(found, missing=False))
        if decision is None:
            return None
        if Path(decision) == found:
            return found
        found = Path(decision)


def _describe_source(source: Path, project_dir: Path) -> dict:
    source = Path(source).resolve()
    try:
        relative = os.path.relpath(source, project_dir.resolve())
    except ValueError:  # another drive on Windows
        relative = None
    return {"path": str(source), "relative_path": relative, "sha256": _fingerprint(source)}


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise PdfToolError(f"Súbor „{Path(path).name}“ sa nepodarilo prečítať: {exc}") from exc
    return digest.hexdigest()

