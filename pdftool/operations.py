"""PDF operations (merge, extract, split, rotate, reorder) built on pypdf.

This module has no GUI dependencies so it can be tested and reused on its own.
All raised `PdfToolError` messages are user-facing (Slovak).
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.errors import DependencyError, PdfReadError
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    RectangleObject,
    StreamObject,
)

from pdftool.pdf_resources import prune_unused_resources

logger = logging.getLogger(__name__)

# Rotation is stored as degrees clockwise, always a multiple of 90.
Rotations = Mapping[int, int]

# Crop margins as fractions of the page as the user sees it (after rotation):
# (left, top, right, bottom), each from 0 to below 1.
CropMargins = tuple[float, float, float, float]


class PdfToolError(Exception):
    """An expected failure whose message can be shown to the user as-is."""


class PasswordRequired(PdfToolError):
    """The document needs a password to open; the GUI can ask for it and call `unlock`."""

    def __init__(self, message: str, path: Path) -> None:
        super().__init__(message)
        self.path = Path(path)


# Passwords the user typed in this session, by file. Kept in memory only – never written to
# settings, logs or disk – so that every later read of the file (thumbnails, saving, …) works.
_passwords: dict[str, str] = {}


@dataclass(frozen=True)
class PageSelection:
    """Pages taken from one source document, in output order."""

    path: Path
    # 0-based page indices; None means all pages in document order.
    pages: Sequence[int] | None = None
    # Extra clockwise rotation per source page index, added to the page's existing rotation.
    rotations: Rotations = field(default_factory=dict)


@dataclass(frozen=True)
class PageRef:
    """One page of the result: a page of a source document plus its own pending rotation.

    Unlike `PageSelection`, every reference carries its own rotation, so the same
    source page can appear several times with different rotations.
    """

    path: Path
    index: int  # 0-based page index in the source document
    rotation: int = 0  # extra clockwise rotation, added to the page's existing rotation
    crop: CropMargins | None = None  # pending crop of the visible page; None keeps the page's own


def rotate_crop(crop: CropMargins | None, degrees: int) -> CropMargins | None:
    """Turn crop margins with their page: after 90° clockwise, the old left margin is at the top."""
    if crop is None:
        return None
    steps = (degrees // 90) % 4
    return tuple(crop[(side - steps) % 4] for side in range(4))  # type: ignore[return-value]


def is_valid_crop(crop: CropMargins) -> bool:
    """Whether some of the page would remain visible (at least 5 % in each direction)."""
    left, top, right, bottom = crop
    return all(margin >= 0 for margin in crop) and left + right <= 0.95 and top + bottom <= 0.95


@dataclass(frozen=True)
class DocumentInfo:
    """The document properties a user can see and edit; empty means "not set"."""

    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""


@dataclass(frozen=True)
class SourceProperties:
    """What a source file reveals about itself, for review before sharing it."""

    info: DocumentInfo
    # Other classic metadata entries (e.g. "Creator" -> "Microsoft Word"), names without the slash.
    other: dict[str, str]
    has_xmp: bool  # an XMP metadata stream, which may repeat or extend the classic entries


_INFO_KEYS = {"title": "/Title", "author": "/Author", "subject": "/Subject", "keywords": "/Keywords"}


def read_properties(path: Path) -> SourceProperties:
    reader = open_pdf(path)
    try:
        metadata = reader.metadata or {}
        values = {key: str(value) for key, value in metadata.items() if value is not None}
        info = DocumentInfo(**{field_name: values.pop(key, "") for field_name, key in _INFO_KEYS.items()})
        has_xmp = reader.xmp_metadata is not None
    except (PdfReadError, ValueError) as exc:
        raise PdfToolError(f"Vlastnosti súboru „{Path(path).name}“ sa nepodarilo načítať: {exc}") from exc
    return SourceProperties(info, {key.lstrip("/"): value for key, value in values.items()}, has_xmp)


def has_digital_signature(path: Path) -> bool:
    """Whether the document contains a signed digital-signature field.

    Saving writes a new file, whose bytes the signature no longer covers, so the user
    can be told that the result will not be validly signed.
    """
    reader = open_pdf(path)
    try:
        fields = reader.get_fields() or {}
    except (PdfReadError, ValueError) as exc:
        raise PdfToolError(f"Formulárové polia súboru „{Path(path).name}“ sa nepodarilo načítať: {exc}") from exc
    return any(field.get("/FT") == "/Sig" and field.get("/V") is not None for field in fields.values())


def open_pdf(path: Path, *, use_cached_password: bool = True) -> PdfReader:
    """Open a PDF, translating errors; noninteractive callers can disable session passwords."""
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
            if not decrypted and use_cached_password and (password := password_for(path)):
                decrypted = reader.decrypt(password)
        except DependencyError as exc:
            raise PdfToolError(
                f"Súbor „{path.name}“ je šifrovaný a chýba knižnica na dešifrovanie: {exc}"
            ) from exc
        if not decrypted:
            raise PasswordRequired(f"Súbor „{path.name}“ je chránený heslom.", path)
    return reader


def unlock(path: Path, password: str) -> bool:
    """Check `password` for `path`; if it opens the file, remember it for this session.

    An empty password never counts: it is always tried automatically, so asking the
    user for it only happens when it does not work.
    """
    if not password:
        return False
    try:
        reader = PdfReader(Path(path))
        if not reader.is_encrypted or not reader.decrypt(password):
            return False
    except (PdfReadError, OSError, ValueError, DependencyError):
        return False
    _passwords[_password_key(path)] = password
    return True


def password_for(path: Path) -> str | None:
    """The password the user gave for `path` in this session, if any."""
    return _passwords.get(_password_key(path))


def forget_passwords() -> None:
    _passwords.clear()


def forget_password(path: Path) -> None:
    """Release a session password when a temporary document is discarded."""
    _passwords.pop(_password_key(path), None)


def _password_key(path: Path) -> str:
    # Windows and macOS file systems ignore letter case.
    return str(Path(path).resolve()).casefold()


def page_count(path: Path) -> int:
    reader = open_pdf(path)
    try:
        return len(reader.pages)
    except PdfReadError as exc:
        raise PdfToolError(f"Súbor „{Path(path).name}“ je poškodený: {exc}") from exc


def write_pdf(
    selections: Sequence[PageSelection],
    output_path: Path,
    bookmark_titles: Sequence[str] | None = None,
    password: str | None = None,
    *,
    use_cached_password: bool = True,
) -> None:
    """Write the selected pages of one or more documents, in order, into a single PDF.

    Used for merging, extracting pages and saving rotated documents alike. With
    `bookmark_titles` (one per selection), each selection gets a bookmark on its
    first page in the output. Bookmarks of the source documents are not copied:
    pages are taken one by one, so their targets would not survive page ranges.
    """
    if bookmark_titles is not None and len(bookmark_titles) != len(selections):
        raise ValueError("bookmark_titles needs one title per selection")
    writer = PdfWriter()
    first_pages: list[int] = []
    for selection in selections:
        reader = open_pdf(selection.path, use_cached_password=use_cached_password)
        pages = range(len(reader.pages)) if selection.pages is None else selection.pages
        first_pages.append(len(writer.pages))
        _append_pages(writer, reader, selection.path, pages, selection.rotations)

    if not writer.pages:
        raise PdfToolError("Výsledný dokument by neobsahoval žiadne strany.")
    if bookmark_titles:
        for title, first_page, selection in zip(bookmark_titles, first_pages, selections, strict=True):
            # A selection without pages has nothing to point to.
            if title and (selection.pages is None or selection.pages):
                writer.add_outline_item(title, first_page)
        writer.page_mode = "/UseOutlines"  # open with the bookmarks panel visible
    _write_atomically(writer, Path(output_path), password)


def write_pages(
    pages: Sequence[PageRef],
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> None:
    """Write the referenced pages, in order, into a single PDF.

    Pages may come from several documents and may repeat; each document is opened once.
    With `password`, the output can only be opened with it (AES-256). The output gets
    the properties in `info` and no metadata of the sources (pages are copied one by one).
    """
    if not pages:
        raise PdfToolError("Výsledný dokument by neobsahoval žiadne strany.")
    writer = PdfWriter()
    _append_refs(writer, pages)
    _write_atomically(writer, Path(output_path), password, info)


def interleave_pages(
    front_path: Path, front_count: int, back_path: Path, back_count: int, reverse_back: bool
) -> list[PageRef]:
    """Merge separately scanned front and back sides into reading order: F1, B1, F2, B2, …

    A scanner without duplex produces one file of front sides and one of back
    sides; the back sides are usually scanned with the stack turned over, so
    they come in reverse order. The last sheet may be printed on one side only,
    so there may be one back side fewer than front sides – never more.
    """
    if front_count < 1 or back_count < 1:
        raise PdfToolError("Predné aj zadné strany musia obsahovať aspoň jednu stranu.")
    if back_count not in (front_count, front_count - 1):
        raise PdfToolError(
            f"Počet zadných strán ({back_count}) nezodpovedá počtu predných strán ({front_count}). "
            "Zadných strán musí byť rovnako veľa alebo o jednu menej."
        )
    back_indices = list(range(back_count))
    if reverse_back:
        back_indices.reverse()

    pages = []
    for front_index in range(front_count):
        pages.append(PageRef(Path(front_path), front_index))
        if front_index < back_count:
            pages.append(PageRef(Path(back_path), back_indices[front_index]))
    return pages


def visible_page_sizes(path: Path) -> list[tuple[float, float]]:
    """Width and height in points of each page as a viewer shows it (crop box, after rotation)."""
    reader = open_pdf(path)
    try:
        sizes = []
        for page in reader.pages:
            width, height = float(page.cropbox.width), float(page.cropbox.height)
            sizes.append((height, width) if page.rotation % 180 else (width, height))
        return sizes
    except PdfReadError as exc:
        raise PdfToolError(f"Súbor „{Path(path).name}“ je poškodený: {exc}") from exc


def apply_overlay(
    base_path: Path,
    overlay_path: Path,
    page_map: Mapping[int, int],
    output_path: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
    removed_widgets: Mapping[int, Sequence[int]] | None = None,
) -> None:
    """Draw pages of `overlay_path` over pages of `base_path` and write the result.

    `page_map` maps a 0-based page of the base document to the overlay page drawn
    on it. Overlay pages must have the visible size of their base page (see
    `visible_page_sizes`). The overlay is mapped into the base page's coordinates;
    its existing rotation, crop box and annotation positions stay intact.
    `removed_widgets` lists, per base page, positions in its annotation array of form
    widgets to remove, because the overlay draws their filled-in values instead.
    """
    reader = open_pdf(base_path)
    overlay = open_pdf(overlay_path)
    try:
        writer = PdfWriter(clone_from=reader)
        for base_index, overlay_index in page_map.items():
            page = writer.pages[base_index]
            _detach_overlay_target(page, writer)
            _remove_widgets(page, (removed_widgets or {}).get(base_index, ()))
            box = page.cropbox
            left, bottom, right, top = map(float, (box.left, box.bottom, box.right, box.top))
            # Inverse of the viewer's clockwise rotation, including an offset crop origin.
            transforms = {
                0: (1, 0, 0, 1, left, bottom),
                90: (0, 1, -1, 0, right, bottom),
                180: (-1, 0, 0, -1, right, top),
                270: (0, -1, 1, 0, left, top),
            }
            page.merge_transformed_page(overlay.pages[overlay_index], Transformation(transforms[page.rotation % 360]))
    except (PdfReadError, IndexError) as exc:
        raise PdfToolError(f"Text sa do súboru „{Path(base_path).name}“ nepodarilo vložiť: {exc}") from exc
    _write_atomically(writer, Path(output_path), password, info)


def _remove_widgets(page, positions: Sequence[int]) -> None:
    if not positions:
        return
    annotations = page.get("/Annots", ArrayObject())  # a private copy, see _detach_overlay_target
    for position in positions:
        if not 0 <= position < len(annotations) or annotations[position].get_object().get("/Subtype") != "/Widget":
            # The pages were written from the same references a moment ago; anything else is a bug,
            # and drawing the value without removing the field would show both on top of each other.
            raise PdfToolError("Formulárové pole sa v strane nepodarilo nájsť. Dokument zostal bez zmeny.")
    removed = set(positions)
    page[NameObject("/Annots")] = ArrayObject(
        annotation for position, annotation in enumerate(annotations) if position not in removed
    )


def _detach_overlay_target(page, writer: PdfWriter) -> None:
    """Keep an overlay local to one occurrence of a duplicated source page.

    pypdf mutates the existing content object and resource tables when merging.
    Those can still be shared by other pages, even though their page dictionaries differ.
    """
    contents = page.get_contents()
    if contents is not None:
        stream = DecodedStreamObject()
        stream.set_data(contents.get_data())
        page[NameObject("/Contents")] = writer._add_object(stream)
    resources = page.get("/Resources")
    if resources is not None:
        copied = DictionaryObject()
        for name, value in resources.get_object().items():
            resolved = value.get_object()
            if isinstance(resolved, DictionaryObject) and not isinstance(resolved, StreamObject):
                value = DictionaryObject(resolved)
            elif isinstance(resolved, ArrayObject):
                value = ArrayObject(resolved)
            copied[name] = value
        page[NameObject("/Resources")] = copied
    annotations = page.get("/Annots")
    if annotations is not None:
        page[NameObject("/Annots")] = ArrayObject(annotations.get_object())


# Re-encodes one JPEG image: (JPEG data, colour space name) -> (new JPEG data, width, height),
# or None to keep the image. Supplied by the GUI layer, which decodes images with Qt.
ImageRecompressor = Callable[[bytes, str], tuple[bytes, int, int] | None]


@dataclass(frozen=True)
class SizeReport:
    before: int  # bytes of the document saved without optimisation
    after: int  # bytes of what was written

    @property
    def saved(self) -> int:
        return self.before - self.after


def write_optimized(
    pages: Sequence[PageRef],
    output_path: Path,
    recompress_image: ImageRecompressor | None = None,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> SizeReport:
    """Write `pages` as small as possible and report the real sizes before and after.

    Lossless steps always run: page contents are recompressed and identical objects
    merged. With `recompress_image`, JPEG pictures are additionally re-encoded (lossy).
    Text is never turned into images. If optimising does not help, the plain version
    is written, so the result is never larger than a normal save.
    """
    if not pages:
        raise PdfToolError("Výsledný dokument by neobsahoval žiadne strany.")
    plain = PdfWriter()
    _append_refs(plain, pages)
    plain_bytes = _to_bytes(_finish(plain, password, info))

    optimized = PdfWriter()
    _append_refs(optimized, pages)
    for page in optimized.pages:
        page.compress_content_streams(level=9)
    if recompress_image is not None:
        _recompress_images(optimized, recompress_image)
    optimized.compress_identical_objects()
    optimized_bytes = _to_bytes(_finish(optimized, password, info))

    result = optimized_bytes if len(optimized_bytes) < len(plain_bytes) else plain_bytes
    write_file_atomically(lambda stream: stream.write(result), Path(output_path))
    return SizeReport(before=len(plain_bytes), after=len(result))


def _to_bytes(writer: PdfWriter) -> bytes:
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _recompress_images(writer: PdfWriter, recompress_image: ImageRecompressor) -> None:
    """Replace JPEG images on the pages by re-encoded ones where that makes them smaller.

    Only the simple, common case is touched – a plain JPEG (one DCTDecode filter, 8 bits,
    RGB or grey, no decode array), as produced by scanners and cameras. Anything else
    (CMYK, masks drawn from the image itself, other filters) is kept unchanged.
    """
    replaced: dict[int, IndirectObject] = {}
    for page in writer.pages:
        resources = page.get("/Resources")
        xobjects = resources.get_object().get("/XObject") if resources else None
        if not xobjects:
            continue
        xobjects = xobjects.get_object()
        for name, reference in list(xobjects.items()):
            if not isinstance(reference, IndirectObject):
                continue
            if reference.idnum in replaced:
                xobjects[NameObject(name)] = replaced[reference.idnum]
                continue
            image = reference.get_object()
            if not _is_plain_jpeg(image):
                continue
            try:
                result = recompress_image(image.get_data(), str(image["/ColorSpace"]))
            except Exception:  # noqa: BLE001 – a picture that cannot be re-encoded is simply kept
                logger.warning("Obrázok %s sa nepodarilo prekódovať", name, exc_info=True)
                continue
            if result is None or len(result[0]) >= len(image.get_data()):
                continue
            data, width, height = result
            new_image = DecodedStreamObject()
            new_image.set_data(data)
            for key, value in image.items():
                if key not in ("/Length", "/Width", "/Height", "/Filter", "/DecodeParms"):
                    new_image[NameObject(key)] = value
            new_image[NameObject("/Width")] = NumberObject(width)
            new_image[NameObject("/Height")] = NumberObject(height)
            new_image[NameObject("/Filter")] = NameObject("/DCTDecode")
            # pypdf has no public call for adding a new object; _add_object is what its own docs use.
            new_reference = writer._add_object(new_image)
            replaced[reference.idnum] = new_reference
            xobjects[NameObject(name)] = new_reference


def _is_plain_jpeg(image) -> bool:
    return (
        image.get("/Subtype") == "/Image"
        and image.get("/Filter") == "/DCTDecode"
        and image.get("/BitsPerComponent") == 8
        and image.get("/ColorSpace") in ("/DeviceRGB", "/DeviceGray")
        and "/Decode" not in image
        and "/ImageMask" not in image
    )


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
    rotations = rotations or {}
    ref_groups = [
        [PageRef(Path(source_path), index, rotations.get(index, 0)) for index in group] for group in groups
    ]
    return split_pages(source_path, ref_groups, output_dir)


def split_pages(
    name_source: Path,
    groups: Sequence[Sequence[PageRef]],
    output_dir: Path,
    password: str | None = None,
    info: DocumentInfo | None = None,
) -> list[Path]:
    """Write each group of page references into its own PDF named after `name_source`."""
    if not groups:
        raise PdfToolError("Nie je zadaná žiadna časť na rozdelenie.")
    # Validated up front so that an invalid request never leaves partial output behind.
    if not all(groups):
        raise PdfToolError("Niektorá z častí neobsahuje žiadne strany.")
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise PdfToolError(f"Priečinok neexistuje: {output_dir}")

    output_paths = split_output_paths(name_source, len(groups), output_dir)
    readers: dict[Path, PdfReader] = {}
    for refs, output_path in zip(groups, output_paths, strict=True):
        writer = PdfWriter()
        _append_refs(writer, refs, readers)
        _write_atomically(writer, output_path, password, info)
    return output_paths


def _append_refs(writer: PdfWriter, refs: Sequence[PageRef], readers: dict[Path, PdfReader] | None = None) -> None:
    # `readers` lets several outputs share already opened documents.
    readers = {} if readers is None else readers
    for ref in refs:
        path = Path(ref.path)
        if path not in readers:
            readers[path] = open_pdf(path)
        _append_pages(writer, readers[path], path, [ref.index], {ref.index: ref.rotation})
        if ref.crop is not None:
            _apply_crop(writer.pages[-1], ref.crop)


def _apply_crop(page, crop: CropMargins) -> None:
    """Set the page's crop box from margins given on the page as displayed (after its rotation)."""
    page.cropbox = RectangleObject(cropped_box(page_box(page.cropbox), page.rotation, crop))


# A page area in the page's own, unrotated PDF coordinates: (left, bottom, right, top).
Box = tuple[float, float, float, float]


def page_box(rectangle: RectangleObject) -> Box:
    return float(rectangle.left), float(rectangle.bottom), float(rectangle.right), float(rectangle.top)


def cropped_box(box: Box, rotation: int, crop: CropMargins) -> Box:
    """`box` cut by margins given on the page as displayed, turned clockwise by `rotation`."""
    if not is_valid_crop(crop):
        raise PdfToolError("Orez by zo strany nenechal takmer nič viditeľné.")
    # The box is in the page's own, unrotated coordinates: a viewer showing the page turned
    # 90° clockwise displays its left edge at the top, so the margins shift by one side per 90°.
    steps = (rotation % 360) // 90
    left, top, right, bottom = (crop[(side + steps) % 4] for side in range(4))
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    return x0 + left * width, y0 + bottom * height, x1 - right * width, y1 - top * height


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
            _keep_field_parents(source_pages[index], page, writer)
            rotation = rotations.get(index, 0) % 360
            if rotation:
                page.rotate(rotation)
    except PdfReadError as exc:
        raise PdfToolError(f"Súbor „{Path(source_path).name}“ je poškodený: {exc}") from exc


def _keep_field_parents(source_page, page, writer: PdfWriter) -> None:
    """Link the copied form widgets of `page` to copies of their parent fields again.

    add_page leaves out every /Parent while copying, and with it the field a widget
    belongs to: its name, type and value often live in the parent (radio buttons
    always). Parents are copied without their /Kids, which would bring along the
    widgets – and pages – of the whole form.
    """
    source_annotations = source_page.get("/Annots")
    annotations = page.get("/Annots")
    if source_annotations is None or annotations is None:
        return
    # The copy keeps the annotations in their order.
    for source, target in zip(source_annotations.get_object(), annotations.get_object(), strict=False):
        source, target = source.get_object(), target.get_object()
        if not isinstance(source, DictionaryObject) or source.get("/Subtype") != "/Widget":
            continue
        for _ in range(32):  # malformed files can have /Parent cycles
            parent_reference = source.get("/Parent")
            if not isinstance(parent_reference, IndirectObject) or "/Parent" in target:
                break  # no parent, or already linked through a widget copied earlier
            parent_source = parent_reference.get_object()
            if not isinstance(parent_source, DictionaryObject):
                break
            parent = parent_source.clone(writer, ignore_fields=("/Kids", "/Parent"))
            target[NameObject("/Parent")] = parent.indirect_reference
            source, target = parent_source, parent


def _finish(writer: PdfWriter, password: str | None, info: DocumentInfo | None) -> PdfWriter:
    """Remove what the output must not carry, apply the properties and the password.

    The last step before writing; returns the writer to write, which may be a new one.
    """
    writer = _without_other_pages(writer)
    if info is not None:
        writer.add_metadata(
            {key: getattr(info, field_name) for field_name, key in _INFO_KEYS.items() if getattr(info, field_name)}
        )
    if password:
        # Only the user password is set: anyone with it gets full access, nobody without it.
        writer.encrypt(user_password=password, algorithm="AES-256")
    return writer


def _without_other_pages(writer: PdfWriter) -> PdfWriter:
    """`writer` without hidden copies of pages that are not part of the output.

    Copying a page copies everything it refers to: a link to another page of the
    source, or a form field whose other parts lie on other pages, brings those pages
    into the file with all their content – invisible, but extractable. Leaving pages
    out (extracting, splitting, redacting) must really leave them out, so such
    references are cut and the document is rebuilt from what is still reachable.
    """
    try:
        pruned = prune_unused_resources(writer)
    except (PdfReadError, ValueError, TypeError) as exc:
        raise PdfToolError("Zdroje strán sa nepodarilo bezpečne skontrolovať. Výsledok nebol uložený.") from exc
    if not _cut_references_to_other_pages(writer) and not pruned:
        return writer  # the usual case: nothing to remove, no extra work
    buffer = io.BytesIO()
    writer.write(buffer)
    # Cloning copies only the objects reachable from the document root.
    return PdfWriter(clone_from=PdfReader(buffer))


def _cut_references_to_other_pages(writer: PdfWriter) -> bool:
    """Replace references to pages outside the output, and to their annotations, with null.

    Returns whether anything was cut.
    """
    own_pages = {page.indirect_reference.idnum for page in writer.pages}
    own_annotations = set()
    for page in writer.pages:
        annotations = page.get("/Annots")
        for annotation in annotations.get_object() if annotations is not None else ():
            if isinstance(annotation, IndirectObject):
                own_annotations.add(annotation.idnum)

    def is_foreign(reference: IndirectObject) -> bool:
        target = reference.get_object()
        if not isinstance(target, DictionaryObject):
            return False
        if target.get("/Type") == "/Page":
            return reference.idnum not in own_pages
        if "/Subtype" in target and "/Rect" in target:  # an annotation, e.g. a form widget
            return reference.idnum not in own_annotations
        return False

    cut = False
    visited: set[int] = set()
    containers: list[DictionaryObject | ArrayObject] = [writer.root_object]
    while containers:
        container = containers.pop()
        entries = list(container.items()) if isinstance(container, DictionaryObject) else list(enumerate(container))
        for key, value in entries:
            if isinstance(value, IndirectObject):
                if is_foreign(value):
                    container[key] = NullObject()
                    cut = True
                    continue
                if value.idnum in visited:
                    continue
                visited.add(value.idnum)
                value = value.get_object()
            if isinstance(value, (DictionaryObject, ArrayObject)):
                containers.append(value)
    return cut


def _write_atomically(
    writer: PdfWriter, output_path: Path, password: str | None = None, info: DocumentInfo | None = None
) -> None:
    writer = _finish(writer, password, info)
    write_file_atomically(writer.write, output_path)


def write_file_atomically(write: Callable[[BinaryIO], object], output_path: Path) -> None:
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
            write(stream)
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
