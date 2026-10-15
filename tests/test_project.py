import shutil
import json

import pytest

from pdftool.operations import DocumentInfo, PageRef, PdfToolError
from pdftool.project import Project, load_project, save_project
from tests.helpers import make_pdf


def never_asked(problem):
    pytest.fail(f"unexpected question about {problem}")


@pytest.mark.parametrize("invalid", [[], None, 1, "project"])
def test_non_object_project_is_reported_as_invalid(tmp_path, invalid):
    path = tmp_path / "invalid.pdfprojekt"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(PdfToolError, match="nie je platný projekt"):
        load_project(path, never_asked)


@pytest.mark.parametrize(("key", "value"), [
    ("crop", [0.1, 0.1, 0.1]), ("crop", [-0.1, 0, 0, 0]),
    ("crop", [float("nan"), 0, 0, 0]), ("crop", [0.9, 0, 0.9, 0]),
    ("rotation", 45), ("source", -1), ("index", "0"),
])
def test_invalid_legacy_project_page_is_rejected(tmp_path, key, value):
    source = make_pdf(tmp_path / "doc.pdf", [101, 102])
    path = tmp_path / "invalid.pdfprojekt"
    save_project(Project(source, (PageRef(source, 0),)), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pages"][0][key] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PdfToolError):
        load_project(path, never_asked)


def test_project_round_trip_restores_order_rotation_crop_and_properties(tmp_path):
    first = make_pdf(tmp_path / "zmluva.pdf", [101, 102])
    second = make_pdf(tmp_path / "príloha.pdf", [201])
    pages = (PageRef(second, 0, 90), PageRef(first, 1, 0, (0.1, 0, 0, 0.2)), PageRef(first, 1, 270))
    project = Project(first, pages, DocumentInfo(title="Zmluva – Žilina"))

    save_project(project, tmp_path / "praca.pdfprojekt")

    assert load_project(tmp_path / "praca.pdfprojekt", never_asked) == project


def test_a_moved_folder_is_found_and_a_changed_source_is_not_used_silently(tmp_path):
    folder = tmp_path / "zakazka"
    folder.mkdir()
    source = make_pdf(folder / "doc.pdf", [101, 102, 103])
    save_project(Project(source, (PageRef(source, 2),)), folder / "praca.pdfprojekt")

    moved = tmp_path / "presunuta"
    shutil.move(folder, moved)  # project and document moved together
    restored = load_project(moved / "praca.pdfprojekt", never_asked)
    assert restored.pages == (PageRef(moved / "doc.pdf", 2),)

    make_pdf(moved / "doc.pdf", [101])  # replaced by a different, shorter document
    questions = []
    assert load_project(moved / "praca.pdfprojekt", lambda problem: questions.append(problem)) is None
    assert [problem.missing for problem in questions] == [False]
    with pytest.raises(PdfToolError, match="nemá stranu 3"):
        load_project(moved / "praca.pdfprojekt", lambda problem: problem.stored_path)  # "use it anyway"


def test_a_missing_source_can_be_located_by_the_user(tmp_path):
    source = make_pdf(tmp_path / "doc.pdf", [101])
    save_project(Project(source, (PageRef(source, 0),)), tmp_path / "praca.pdfprojekt")
    new_place = tmp_path / "archiv" / "doc.pdf"
    new_place.parent.mkdir()
    shutil.move(source, new_place)  # moved away from the project

    restored = load_project(tmp_path / "praca.pdfprojekt", lambda problem: new_place if problem.missing else None)

    assert restored.pages == (PageRef(new_place, 0),)


def test_opening_a_broken_legacy_project_is_rejected(tmp_path):
    broken = tmp_path / "zly.pdfprojekt"
    broken.write_text("{ not json", encoding="utf-8")
    with pytest.raises(PdfToolError, match="nepodarilo načítať"):
        load_project(broken, never_asked)


def test_document_interface_has_no_project_actions(app):
    from PySide6.QtGui import QAction
    from pdftool.gui.pages_tab import PagesTab
    tab = PagesTab()
    assert all("projekt" not in action.text().casefold() for action in tab.findChildren(QAction))
    from PySide6.QtWidgets import QLabel
    assert all("projekt" not in label.text().casefold()
               for label in tab._ribbon.findChildren(QLabel, "commandCaption"))
