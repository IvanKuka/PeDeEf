from pypdf import PdfReader, PdfWriter

from pdftool.gui import pages_tab
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.properties_dialog import format_pdf_date
from pdftool.operations import DocumentInfo, read_properties


def make_described_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=500)
    writer.add_metadata(
        {"/Title": "Zmluva", "/Author": "Ján Novák", "/Creator": "Microsoft Word", "/CreationDate": "D:20240315093000+01'00'"}
    )
    writer.write(path)
    return path


def saved_metadata(path):
    return {key: str(value) for key, value in (PdfReader(path).metadata or {}).items()}


def test_source_properties_are_read_for_review(tmp_path):
    properties = read_properties(make_described_pdf(tmp_path / "doc.pdf"))

    assert properties.info == DocumentInfo(title="Zmluva", author="Ján Novák")
    assert properties.other["Creator"] == "Microsoft Word"
    assert format_pdf_date(properties.other["CreationDate"]) == "15. 03. 2024 09:30"
    assert not properties.has_xmp


def test_edited_properties_are_saved_undoable_and_nothing_else_is_carried_over(app, dialogs, tmp_path, monkeypatch):
    source = make_described_pdf(tmp_path / "doc.pdf")
    tab = PagesTab()
    tab.open_file(source)

    # Without editing, saving keeps today's behaviour: no metadata of the source.
    dialogs.save_path = tmp_path / "plain.pdf"
    tab._save_as()
    assert set(saved_metadata(dialogs.save_path)) == {"/Producer"}

    class EditingDialog:
        DialogCode = pages_tab.PropertiesDialog.DialogCode

        def __init__(self, file_name, source_properties, current, parent):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def info(self):
            return DocumentInfo(title="Zmluva o dielo – Žilina", keywords="zmluva, 2026")

    monkeypatch.setattr(pages_tab, "PropertiesDialog", EditingDialog)
    tab._edit_properties()
    assert tab.has_unsaved_changes()
    tab._undo()
    assert not tab.has_unsaved_changes()
    tab._redo()

    dialogs.save_path = tmp_path / "described.pdf"
    tab._save_as()
    metadata = saved_metadata(dialogs.save_path)
    assert metadata["/Title"] == "Zmluva o dielo – Žilina"
    assert metadata["/Keywords"] == "zmluva, 2026"
    assert "/Author" not in metadata and "/Creator" not in metadata  # the author was cleared, Word is not mentioned
