"""Remove unused PDF resources without changing rendered content.

Pages often share a resource dictionary containing scans of *all* source pages.
Copying only selected pages is therefore insufficient to remove excluded content.
Usage is collected across shared scopes before pruning, including nested forms,
patterns, Type 3 fonts, soft masks and annotation appearances.
"""

from pypdf.generic import ContentStream, DictionaryObject, NameObject, StreamObject
from pypdf import PdfWriter

_RESOURCE_OPERATORS = {
    b"Do": ("/XObject", 0), b"Tf": ("/Font", 0), b"gs": ("/ExtGState", 0),
    b"CS": ("/ColorSpace", 0), b"cs": ("/ColorSpace", 0),
    b"SCN": ("/Pattern", -1), b"scn": ("/Pattern", -1),
    b"sh": ("/Shading", 0), b"BDC": ("/Properties", 1), b"DP": ("/Properties", 1),
}
_RESOURCE_CATEGORIES = frozenset(category for category, _ in _RESOURCE_OPERATORS.values())


def prune_unused_resources(writer: PdfWriter) -> bool:
    scopes: dict[int, tuple[DictionaryObject, dict[str, set[str]]]] = {}
    # Keep the objects alive: page.get_contents() can create temporary ContentStreams,
    # and using only id() would let a later stream reuse an earlier stream's identity.
    visited: dict[tuple[int, int], object] = {}
    visited_appearances: set[tuple[int, int]] = set()

    def visit_font(font, resources):
        font = font.get_object()
        if font.get("/Subtype") == "/Type3":
            glyphs = font.get("/CharProcs")
            if glyphs is not None:
                for glyph in glyphs.get_object().values():
                    visit(glyph.get_object(), font.get("/Resources", resources))

    def use(resources, category, name):
        if not isinstance(name, NameObject):
            return
        table = resources.get(category)
        if table is None or name not in table.get_object():
            return  # predefined colour spaces do not live in the resource dictionary
        used = scopes[id(resources)][1].setdefault(category, set())
        if name in used:
            return
        used.add(name)
        target = table.get_object()[name].get_object()
        if isinstance(target, StreamObject) and (
            (category == "/XObject" and target.get("/Subtype") == "/Form")
            or (category == "/Pattern" and target.get("/PatternType") == 1)
        ):
            visit(target, target.get("/Resources", resources))
        elif category == "/Font":
            visit_font(target, resources)
        elif category == "/ExtGState":
            mask = target.get("/SMask")
            if mask is not None and isinstance(mask.get_object(), DictionaryObject):
                group = mask.get_object().get("/G")
                if group is not None:
                    group = group.get_object()
                    visit(group, group.get("/Resources", resources))
            if "/Font" in target:
                visit_font(target["/Font"][0], resources)

    def visit(stream, resources):
        resources = resources.get_object()
        scopes.setdefault(id(resources), (resources, {}))
        if stream is None:
            return
        key = (id(stream), id(resources))
        if key in visited:
            return
        visited[key] = stream
        for operands, operator in ContentStream(stream, writer).operations:
            if operator == b"INLINE IMAGE":
                settings = operands["settings"]
                use(resources, "/ColorSpace", settings.get("/CS", settings.get("/ColorSpace")))
            elif operator in _RESOURCE_OPERATORS:
                category, index = _RESOURCE_OPERATORS[operator]
                if operands and -len(operands) <= index < len(operands):
                    use(resources, category, operands[index])

    def visit_appearances(appearance, resources):
        appearance = appearance.get_object()
        key = (id(appearance), id(resources))
        if key in visited_appearances:
            return
        visited_appearances.add(key)
        if isinstance(appearance, StreamObject):
            visit(appearance, appearance.get("/Resources", resources))
        elif isinstance(appearance, DictionaryObject):
            for value in appearance.values():
                visit_appearances(value, resources)

    for page in writer.pages:
        resources = page.get("/Resources", DictionaryObject()).get_object()
        visit(page.get_contents(), resources)
        annotations = page.get("/Annots")
        for annotation in annotations.get_object() if annotations is not None else ():
            annotation = annotation.get_object()
            if isinstance(annotation, DictionaryObject) and "/AP" in annotation:
                visit_appearances(annotation["/AP"], resources)

    changed = False
    for resources, used in scopes.values():
        for category in _RESOURCE_CATEGORIES:
            if category not in resources:
                continue
            table = resources[category]
            kept = DictionaryObject({name: value for name, value in table.items() if name in used.get(category, ())})
            if len(kept) != len(table):
                # Replace the table: distinct resource dictionaries can share the same table.
                resources[NameObject(category)] = kept
                changed = True
    return changed
