import pytest

from pdftool.history import History


def test_undo_and_redo_walk_through_recorded_states():
    history = History("a")
    history.record("b", "B")
    history.record("c", "C")

    assert history.undo() == "b"
    assert history.undo() == "a"
    assert not history.can_undo
    assert history.redo() == "b"
    assert history.redo() == "c"
    assert not history.can_redo


def test_labels_name_the_edit_that_would_be_undone_or_redone():
    history = History("a")
    assert history.undo_label == history.redo_label == ""

    history.record("b", "B")
    history.record("c", "C")
    assert history.undo_label == "C"
    assert history.redo_label == ""

    history.undo()
    assert history.undo_label == "B"
    assert history.redo_label == "C"


def test_recording_after_undo_discards_the_redo_branch():
    history = History("a")
    history.record("b", "B")
    history.undo()

    history.record("x", "X")

    assert not history.can_redo
    assert history.undo() == "a"


def test_recording_an_unchanged_state_adds_no_step():
    history = History("a")

    history.record("a", "nothing")

    assert not history.can_undo


def test_nothing_to_undo_or_redo_raises():
    history = History("a")

    with pytest.raises(IndexError):
        history.undo()
    with pytest.raises(IndexError):
        history.redo()


def test_oldest_steps_are_forgotten_beyond_the_limit():
    history = History(0, max_steps=3)
    for number in range(1, 6):
        history.record(number, str(number))

    states = [history.current]
    while history.can_undo:
        states.append(history.undo())

    assert states == [5, 4, 3, 2]
    assert history.undo_label == ""  # the oldest kept state has no edit to take back


def test_replace_current_keeps_the_step_count_and_rejects_a_different_state():
    history = History("a")
    history.record("b", "B")

    history.replace_current("b")

    assert history.undo() == "a"
    with pytest.raises(ValueError):
        history.replace_current("zzz")
