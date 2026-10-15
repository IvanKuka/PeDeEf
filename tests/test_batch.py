from pathlib import Path

from PySide6.QtCore import QCoreApplication

from pdftool.batch import Status, plan_outputs, rotate_operation, run_batch
from pdftool.gui import batch_tab
from pdftool.gui.batch_tab import BatchTab
from tests.helpers import make_pdf, page_rotations


def test_outputs_never_overwrite_sources_existing_files_or_each_other(tmp_path):
    first = tmp_path / "a" / "zmluva.pdf"
    second = tmp_path / "b" / "zmluva.pdf"
    out = tmp_path / "out"
    out.mkdir()
    (out / "ZMLUVA.pdf").write_text("an older result")  # names differing only in case collide on Windows and macOS

    outputs = plan_outputs([first, second], out)
    assert [path.name for path in outputs] == ["zmluva (2).pdf", "zmluva (3).pdf"]

    # Writing into a source folder: the source itself is never the output.
    first.parent.mkdir()
    make_pdf(first, [101])
    assert plan_outputs([first], first.parent) == [first.parent / "zmluva (2).pdf"]


def test_batch_rotates_skips_and_reports_each_file(tmp_path):
    short = make_pdf(tmp_path / "short.pdf", [101])
    long = make_pdf(tmp_path / "long.pdf", [101, 102, 103])
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    out = tmp_path / "out"
    out.mkdir()

    results = run_batch([short, long, broken], out, rotate_operation("2-3", 90))

    assert [result.status for result in results] == [Status.SKIPPED, Status.DONE, Status.FAILED]
    assert "Strana 2 neexistuje" in results[0].message
    assert page_rotations(results[1].output) == [0, 90, 90]
    assert sorted(path.name for path in out.iterdir()) == ["long.pdf"]  # nothing for skipped or failed files
    assert page_rotations(long) == [0, 0, 0]  # the source is untouched


def test_cancelled_batch_keeps_finished_files_and_marks_the_rest(tmp_path):
    sources = [make_pdf(tmp_path / f"{name}.pdf", [101]) for name in "abc"]
    out = tmp_path / "out"
    out.mkdir()
    reported = []

    results = run_batch(
        sources, out, rotate_operation("", 90), is_cancelled=lambda: len(reported) >= 1, on_result=reported.append
    )

    assert [result.status for result in results] == [Status.DONE, Status.CANCELLED, Status.CANCELLED]
    assert sorted(path.name for path in out.iterdir()) == ["a.pdf"]


def test_batch_tab_runs_in_the_background_and_lists_each_result(app, tmp_path, monkeypatch):
    summaries = []
    monkeypatch.setattr(batch_tab.QMessageBox, "information", lambda parent, title, text: summaries.append(text))
    folder = tmp_path / "scans"
    (folder / "sub").mkdir(parents=True)
    make_pdf(folder / "one.pdf", [101, 102])
    make_pdf(folder / "sub" / "two.pdf", [101])
    out = tmp_path / "out"
    out.mkdir()
    tab = BatchTab()

    tab.add_paths([folder])  # subfolders only when asked for
    assert tab._list.count() == 1
    tab._recursive_check.setChecked(True)
    tab.add_paths([folder])
    assert tab._list.count() == 2  # one.pdf is not added twice

    tab._pages_edit.setText("2")
    tab._output_edit.setText(str(out))
    tab._start()
    tab._thread.wait()
    QCoreApplication.processEvents()  # deliver the queued results and the finished signal

    assert [tab._list.item(row).text().split(":")[0] for row in range(2)] == [
        "✓  one.pdf  —  Uložené ako one.pdf",
        "⚠  two.pdf  —  Preskočené",
    ]
    assert not tab.is_running()
    assert Path(out / "one.pdf").exists()
    assert "preskočené: 1" in summaries[0]  # skipped files are pointed out at the end
