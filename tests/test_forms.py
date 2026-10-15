from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QLineEdit
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from pdftool.forms import FieldKind, read_form_fields
from pdftool.gui.form_dialog import FormDialog
from pdftool.gui.form_filling import changed_fields, write_filled_pdf
from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.thumbnails import open_document, render_page_scaled
from pdftool.operations import PageRef, open_pdf
from tests.helpers import make_pdf


def make_form_pdf(path):
    """A 400 x 600 page with a text field (named through its parent), a checkbox, two radio
    buttons, a choice field, a read-only field, and fields that cannot be filled in."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=600)

    def add(entries):
        return writer._add_object(DictionaryObject({NameObject(key): value for key, value in entries.items()}))

    def rect(*values):
        return ArrayObject(NumberObject(value) for value in values)

    def appearance(*states):
        stream = DecodedStreamObject()
        stream.set_data(b"")
        stream_ref = writer._add_object(stream)
        return DictionaryObject({NameObject("/N"): DictionaryObject({NameObject(f"/{state}"): stream_ref for state in states})})

    widget = {"/Type": NameObject("/Annot"), "/Subtype": NameObject("/Widget")}
    person = add({"/T": TextStringObject("osoba"), "/FT": NameObject("/Tx"), "/DA": TextStringObject("/Helv 0 Tf 0 g")})
    name = add({
        **widget, "/Parent": person, "/T": TextStringObject("meno"), "/TU": TextStringObject("Meno a priezvisko"),
        "/Rect": rect(50, 500, 250, 520),
        "/MK": DictionaryObject({NameObject("/BC"): ArrayObject([FloatObject(0)])}),
    })
    agree = add({
        **widget, "/FT": NameObject("/Btn"), "/T": TextStringObject("suhlas"), "/Rect": rect(50, 450, 64, 464),
        "/AP": appearance("Off", "Ano"),
    })
    choice = add({"/FT": NameObject("/Btn"), "/Ff": NumberObject(1 << 15), "/T": TextStringObject("pohlavie")})
    radio_a = add({**widget, "/Parent": choice, "/Rect": rect(50, 400, 64, 414), "/AP": appearance("Off", "Muz")})
    radio_b = add({**widget, "/Parent": choice, "/Rect": rect(100, 400, 114, 414), "/AP": appearance("Off", "Zena")})
    choice.get_object()[NameObject("/Kids")] = ArrayObject([radio_a, radio_b])
    country = add({
        **widget, "/FT": NameObject("/Ch"), "/Ff": NumberObject(1 << 17), "/T": TextStringObject("krajina"),
        "/Rect": rect(50, 350, 200, 370), "/V": TextStringObject("Česko"),
        "/Opt": ArrayObject([TextStringObject("Slovensko"), ArrayObject([TextStringObject("CZ"), TextStringObject("Česko")])]),
    })
    fixed = add({
        **widget, "/FT": NameObject("/Tx"), "/Ff": NumberObject(1), "/T": TextStringObject("cislo"),
        "/Rect": rect(50, 300, 200, 320), "/V": TextStringObject("123"),
    })
    signature = add({**widget, "/FT": NameObject("/Sig"), "/T": TextStringObject("podpis"), "/Rect": rect(50, 50, 200, 90)})
    hidden = add({
        **widget, "/FT": NameObject("/Tx"), "/T": TextStringObject("skryte"), "/F": NumberObject(2),
        "/Rect": rect(50, 250, 200, 270),
    })
    page[NameObject("/Annots")] = ArrayObject([name, agree, radio_a, radio_b, country, fixed, signature, hidden])
    writer.write(path)
    return path


def test_fields_are_read_with_their_kind_value_and_place_on_the_visible_page(tmp_path):
    source = make_form_pdf(tmp_path / "form.pdf")

    fields = {field.name: field for field in read_form_fields([PageRef(source, 0), PageRef(source, 0, rotation=90)])}

    assert list(fields) == ["osoba.meno", "suhlas", "pohlavie", "krajina", "cislo"]  # no signature, no hidden field
    name = fields["osoba.meno"]
    assert (name.kind, name.label, name.value) == (FieldKind.TEXT, "Meno a priezvisko", "")
    assert [widget.row for widget in name.widgets] == [0, 1]  # shown on both occurrences of the page
    upright, turned = name.widgets
    assert [round(value, 4) for value in upright.area] == [0.125, round(80 / 600, 4), 0.5, round(20 / 600, 4)]
    # Turned clockwise: the field's bottom edge (y 500) is 500 points from the left of the visible page.
    assert [round(value, 4) for value in turned.area] == [round(500 / 600, 4), 0.125, round(20 / 600, 4), 0.5]
    assert (upright.turn, turned.turn) == (0, 90)
    assert (fields["suhlas"].kind, fields["suhlas"].value, fields["suhlas"].widgets[0].on_state) == (
        FieldKind.CHECKBOX, False, "Ano"
    )
    assert (fields["pohlavie"].kind, fields["pohlavie"].options) == (FieldKind.RADIO, ("Muz", "Zena"))
    assert (fields["krajina"].options, fields["krajina"].value) == (("Slovensko", "Česko"), "Česko")
    assert fields["cislo"].read_only


def test_filled_values_replace_their_fields_and_untouched_fields_stay(app, tmp_path):
    source = make_form_pdf(tmp_path / "form.pdf")
    pages = [PageRef(source, 0)]
    fields = read_form_fields(pages)
    values = {"osoba.meno": "Ľudmila Šťastná", "suhlas": True, "pohlavie": "Zena", "krajina": "Česko", "cislo": "999"}
    output = tmp_path / "out.pdf"

    write_filled_pdf(pages, fields, values, output)

    # Unchanged (krajina) and read-only (cislo) fields are not changed.
    assert [field.name for field in changed_fields(fields, values)] == ["osoba.meno", "suhlas", "pohlavie"]
    page = PdfReader(output).pages[0]
    assert " ".join(page.extract_text().split()) == "Ľudmila Šťastná"
    remaining = [annotation.get_object().get("/T") for annotation in page["/Annots"]]
    assert remaining == ["krajina", "cislo", "podpis", "skryte"]
    document = open_document(output)
    image = render_page_scaled(document, 0, 1.0)
    document.close()

    def dark(x, y):
        color = image.pixelColor(x, y)
        return color.alpha() > 0 and color.lightness() < 128

    assert dark(57, 143)  # the check mark in the checkbox at x 50–64, y 136–150
    assert dark(107, 193) and not dark(57, 193)  # only the chosen radio button is filled
    assert dark(50, 90) and dark(249, 90)  # the text field's border is drawn in place of the field


def test_the_tab_fills_a_form_through_the_dialog_and_explains_documents_without_fields(
    app, dialogs, tmp_path, monkeypatch
):
    source = make_form_pdf(tmp_path / "form.pdf")

    def fill_and_accept(dialog):
        assert not dialog._accept_button.isEnabled()  # nothing changed yet
        dialog._inputs["osoba.meno"].setText("Ján")
        dialog._inputs["suhlas"].setChecked(True)
        assert isinstance(dialog._inputs["krajina"], QComboBox) and dialog._inputs["krajina"].currentText() == "Česko"
        assert not dialog._inputs["cislo"].isEnabled()
        assert dialog._accept_button.isEnabled()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FormDialog, "exec", fill_and_accept)
    tab = PagesTab()
    tab.open_file(source)

    tab._fill_form()

    assert tab.has_unsaved_changes()
    edited = tab._current_pages()[0]
    page = open_pdf(edited.path).pages[edited.index]
    assert page.extract_text().strip() == "Ján"
    assert {field.name for field in read_form_fields([edited])} == {"pohlavie", "krajina", "cislo"}

    tab.open_file(make_pdf(tmp_path / "plain.pdf", [300]))
    tab._fill_form()
    assert "neobsahuje formulárové polia" in dialogs.information[-1]


def test_dialog_editors_match_field_kinds(app, tmp_path):
    source = make_form_pdf(tmp_path / "form.pdf")
    pages = [PageRef(source, 0)]
    dialog = FormDialog(pages, read_form_fields(pages), 0, digitally_signed=False)

    assert isinstance(dialog._inputs["osoba.meno"], QLineEdit)
    assert isinstance(dialog._inputs["suhlas"], QCheckBox)
    radio = dialog._inputs["pohlavie"]
    assert [radio.itemText(index) for index in range(radio.count())] == ["(nevybrané)", "Muz", "Zena"]
    radio.setCurrentIndex(2)
    assert dialog.values()["pohlavie"] == "Zena"
