"""Factories and inspectors for the small PDFs used in tests."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def make_pdf(path: Path, widths: list[int], password: str | None = None) -> Path:
    """Create a PDF whose pages are identifiable by their width."""
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=500)
    if password is not None:
        writer.encrypt(user_password=password, algorithm="AES-128")
    writer.write(path)
    return path


def page_widths(path: Path) -> list[int]:
    return [int(page.mediabox.width) for page in PdfReader(path).pages]


def page_rotations(path: Path) -> list[int]:
    return [page.rotation for page in PdfReader(path).pages]
