"""Running one operation over many PDF files (no GUI dependencies).

Every file gets its own result, so one bad file never hides the others. Output
files never overwrite sources or existing files, and each output is written
atomically by the operation, so cancelling between files leaves only complete
results behind. All messages are user-facing (Slovak).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pdftool.operations import PageSelection, PdfToolError, open_pdf, write_pdf
from pdftool.page_ranges import PageRangeError, parse_page_ranges

logger = logging.getLogger(__name__)

# Writes the result of processing a source file (first argument) to an output path (second).
Operation = Callable[[Path, Path], None]


class BatchSkip(Exception):
    """Raised by an operation for a file it deliberately leaves alone; the message says why."""


class Status(Enum):
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class BatchResult:
    source: Path
    status: Status
    message: str = ""
    output: Path | None = None


def collect_pdfs(folder: Path, recursive: bool) -> list[Path]:
    """PDF files in `folder` (and its subfolders only when `recursive`), sorted by path."""
    pattern = "**/*" if recursive else "*"
    return sorted(path for path in Path(folder).glob(pattern) if path.is_file() and path.suffix.lower() == ".pdf")


def plan_outputs(sources: Sequence[Path], output_dir: Path) -> list[Path]:
    """Output path for each source: same file name in `output_dir`, made unique.

    A name already taken – by an existing file, another output of this batch or
    one of the sources – gets " (2)", " (3)", … so nothing is ever overwritten.
    """
    taken = {_key(path) for path in sources}
    outputs = []
    for source in sources:
        candidate = Path(output_dir) / source.name
        number = 2
        while _key(candidate) in taken or candidate.exists():
            candidate = Path(output_dir) / f"{source.stem} ({number}){source.suffix}"
            number += 1
        taken.add(_key(candidate))
        outputs.append(candidate)
    return outputs


def run_batch(
    sources: Sequence[Path],
    output_dir: Path,
    operation: Operation,
    is_cancelled: Callable[[], bool] = lambda: False,
    on_result: Callable[[BatchResult], None] | None = None,
) -> list[BatchResult]:
    """Apply `operation` to every source; return (and report via `on_result`) one result per source."""
    if not Path(output_dir).is_dir():
        raise PdfToolError(f"Priečinok neexistuje: {output_dir}")
    results = []
    for source, output in zip(sources, plan_outputs(sources, output_dir), strict=True):
        if is_cancelled():
            result = BatchResult(source, Status.CANCELLED, "Nespracované – dávka bola zrušená.")
        else:
            result = _process(source, output, operation)
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results


def rotate_operation(page_spec: str, degrees: int) -> Operation:
    """Rotate the pages in `page_spec` ("" = all, numbers as typed by the user) by `degrees` clockwise.

    A file that does not have all of those pages is skipped as a whole: rotating
    only some of the requested pages would be easy to miss in a long batch.
    """

    def rotate(source: Path, output: Path) -> None:
        # A password entered in another tab is not consent to create an unprotected batch copy.
        count = len(open_pdf(source, use_cached_password=False).pages)
        try:
            pages = parse_page_ranges(page_spec, count)
        except PageRangeError as exc:
            raise BatchSkip(f"Preskočené: {exc}") from exc
        write_pdf(
            [PageSelection(source, rotations={page: degrees for page in pages})], output,
            use_cached_password=False,
        )

    return rotate


def _process(source: Path, output: Path, operation: Operation) -> BatchResult:
    try:
        operation(source, output)
    except BatchSkip as exc:
        return BatchResult(source, Status.SKIPPED, str(exc))
    except PdfToolError as exc:
        return BatchResult(source, Status.FAILED, str(exc))
    except Exception as exc:  # noqa: BLE001 – one unusual file must not stop the whole batch
        logger.exception("Neočakávaná chyba pri spracovaní %s", source)
        return BatchResult(source, Status.FAILED, f"Neočakávaná chyba: {exc}")
    return BatchResult(source, Status.DONE, f"Uložené ako {output.name}", output)


def _key(path: Path) -> str:
    # Windows and macOS file systems ignore letter case, so "A.pdf" and "a.pdf" collide.
    return str(Path(path).resolve()).casefold()


def unique_sources(paths: Iterable[Path]) -> list[Path]:
    """`paths` without repeats (the same file added twice is processed once), in order."""
    seen: set[str] = set()
    unique = []
    for path in paths:
        if _key(path) not in seen:
            seen.add(_key(path))
            unique.append(Path(path))
    return unique
