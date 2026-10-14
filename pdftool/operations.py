"""PDF operations (merge, extract, split, rotate) built on pypdf.

This module has no GUI dependencies so it can be tested and reused on its own.
All raised `PdfToolError` messages are user-facing (Slovak).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError, PdfReadError

# Rotation is stored as degrees clockwise, always a multiple of 90.
Rotations = Mapping[int, int]


class PdfToolError(Exception):
    """An expected failure whose message can be shown to the user as-is."""


@dataclass(frozen=True)
class PageSelection:
    """Pages taken from one source document, in output order."""

    path: Path
    # 0-based page indices; None means all pages in document order.
    pages: Sequence[int] | None = None
    # Extra clockwise rotation per source page index, added to the page's existing rotation.
    rotations: Rotations = field(default_factory=dict)


def open_pdf(path: Path) -> PdfReader:
    """Open a PDF for reading, translating library errors into `PdfToolError`."""
    path = Path(path)
    try:
        reader = PdfReader(path)
    except FileNotFoundError:
        raise PdfToolError(f"Súbor neexistuje: {path}") from None
    except (PdfReadError, OSError, ValueError) as exc:
        raise PdfToolError(f"Súbor „{path.name}“ sa nepodarilo načítať: {exc}") from exc

    if reader.is_encrypted:
        # Many PDFs are encrypted with an empty user password and only restrict
        # printing/editing; those can be processed without asking for a password.
        try:
            decrypted = reader.decrypt("")
        except DependencyError as exc:
            raise PdfToolError(
                f"Súbor „{path.name}“ je šifrovaný a chýba knižnica na dešifrovanie: {exc}"
            ) from exc
        if not decrypted:
            raise PdfToolError(f"Súbor „{path.name}“ je chránený heslom.")
    return reader


def page_count(path: Path) -> int:
    reader = open_pdf(path)
    try:
        return len(reader.pages)
    except PdfReadError as exc:
        raise PdfToolError(f"Súbor „{Path(path).name}“ je poškodený: {exc}") from exc


def write_pdf(selections: Sequence[PageSelection], output_path: Path) -> None:
    """Write the selected pages of one or more documents, in order, into a single PDF.

    Used for merging, extracting pages and saving rotated documents alike.
    """
    writer = PdfWriter()
    for selection in selections:
        reader = open_pdf(selection.path)
        pages = range(len(reader.pages)) if selection.pages is None else selection.pages
        _append_pages(writer, reader, selection.path, pages, selection.rotations)

    if not writer.pages:
        raise PdfToolError("Výsledný dokument by neobsahoval žiadne strany.")
    _write_atomically(writer, Path(output_path))


def split_output_paths(source_path: Path, part_count: int, output_dir: Path) -> list[Path]:
    """Return the file names `split_pdf` will create, so callers can check for overwrites first."""
    source_path = Path(source_path)
    # Zero-padding keeps the parts correctly ordered when sorted by name in Explorer.
    width = max(2, len(str(part_count)))
    return [
        Path(output_dir) / f"{source_path.stem}_{number:0{width}d}.pdf"
        for number in range(1, part_count + 1)
    ]


def split_pdf(
    source_path: Path,
    groups: Sequence[Sequence[int]],
    output_dir: Path,
    rotations: Rotations | None = None,
) -> list[Path]:
    """Write each group of 0-based page indices into its own PDF; return the created paths."""
    if not groups:
        raise PdfToolError("Nie je zadaná žiadna časť na rozdelenie.")
    # Validated up front so that an invalid request never leaves partial output behind.
    if not all(groups):
        raise PdfToolError("Niektorá z častí neobsahuje žiadne strany.")
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise PdfToolError(f"Priečinok neexistuje: {output_dir}")

    reader = open_pdf(source_path)
    output_paths = split_output_paths(source_path, len(groups), output_dir)
    for pages, output_path in zip(groups, output_paths, strict=True):
        writer = PdfWriter()
        _append_pages(writer, reader, Path(source_path), pages, rotations or {})
        _write_atomically(writer, output_path)
    return output_paths


def _append_pages(
    writer: PdfWriter,
    reader: PdfReader,
    source_path: Path,
    pages: Sequence[int],
    rotations: Rotations,
) -> None:
    try:
        source_pages = reader.pages
        for index in pages:
            if not 0 <= index < len(source_pages):
                raise PdfToolError(
                    f"Strana {index + 1} v súbore „{Path(source_path).name}“ neexistuje."
                )
            # add_page clones the page, so a page selected twice yields two independent copies.
            page = writer.add_page(source_pages[index])
            rotation = rotations.get(index, 0) % 360
            if rotation:
                page.rotate(rotation)
    except PdfReadError as exc:
        raise PdfToolError(f"Súbor „{Path(source_path).name}“ je poškodený: {exc}") from exc


def _write_atomically(writer: PdfWriter, output_path: Path) -> None:
    # Write to a temporary file next to the target and swap it in afterwards: the
    # target may be one of the source documents, and a failed or interrupted write
    # must never leave a truncated file behind.
    try:
        fd, temp_name = tempfile.mkstemp(suffix=".tmp", dir=output_path.parent)
    except OSError as exc:
        raise PdfToolError(f"Do priečinka „{output_path.parent}“ nie je možné zapisovať: {exc}") from exc

    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            writer.write(stream)
        os.replace(temp_path, output_path)
    except PermissionError as exc:
        temp_path.unlink(missing_ok=True)
        raise PdfToolError(
            f"Súbor „{output_path.name}“ nie je možné prepísať – nie je otvorený v inom programe?"
        ) from exc
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise PdfToolError(f"Súbor „{output_path.name}“ sa nepodarilo uložiť: {exc}") from exc
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
