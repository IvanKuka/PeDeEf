from pdftool.gui.pages_tab import PagesTab
from pdftool.gui.stamp_layer import write_stamp_layer
from pdftool.stamps import StampSpec
from pdftool.text_search import find_pages, next_match, normalize
from tests.helpers import make_pdf


def test_search_ignores_case_and_diacritics_and_wraps_around():
    texts = [normalize(text) for text in ("Úvod", "Zmluva o dielo – ŽILINA", "Príloha:\nžilinská\npobočka")]

    assert find_pages(texts, "zilin") == [1, 2]
    assert find_pages(texts, "Žilinská pobočka") == [2]  # a line break in the PDF counts as a space
    assert find_pages(texts, "   ") == []
    assert next_match([1, 2], current=2, step=1) == 1  # past the last match: back to the first
    assert next_match([1, 2], current=-1, step=-1) == 2


def make_text_pdf(path, texts):
    write_stamp_layer([(595, 842)] * len(texts), texts, StampSpec("x"), path)
    return path


def test_search_follows_pages_after_moving_rotating_and_deleting(app, tmp_path):
    tab = PagesTab()
    tab.open_file(make_text_pdf(tmp_path / "doc.pdf", ["Úvod", "Zmluva – Žilina", "Príloha", "Žilina, dodatok"]))
    tab._open_search()
    tab._search_bar._edit.setText("zilina")

    tab._move_rows([3], 0)  # "Žilina, dodatok" is now the first page
    tab._list.item(2).setSelected(True)
    tab._rotate_selected(90)
    tab._search(1)
    assert [item.text() for item in tab._list.selectedItems()] == ["1"]
    tab._search(1)
    assert [item.text() for item in tab._list.selectedItems()] == ["3"]
    assert tab._search_bar._status.text() == "Strana 3  ·  2 z 2"

    tab._select_all_matches()
    assert sorted(item.text() for item in tab._list.selectedItems()) == ["1", "3"]

    tab._delete_selected()
    tab._search(1)
    assert tab._search_bar._status.text() == "Nenájdené"


def test_search_in_a_scan_without_text_explains_why(app, tmp_path):
    tab = PagesTab()
    tab.open_file(make_pdf(tmp_path / "scan.pdf", [300, 300]))
    tab._open_search()
    tab._search_bar._edit.setText("zmluva")

    tab._search(1)

    assert "neobsahuje text" in tab._search_bar._status.text()
