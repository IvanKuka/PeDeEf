"""Undo/redo history made of whole-state snapshots.

The states kept here are small immutable values (the list of page references,
never rendered images), so restoring one is just showing it again. This keeps
every kind of edit undoable the same way and needs no per-operation inverse.
This module has no GUI dependencies.
"""

from __future__ import annotations

from typing import Generic, TypeVar

State = TypeVar("State")


class History(Generic[State]):
    """A linear history: recording after an undo discards the undone (redo) branch."""

    def __init__(self, initial: State, max_steps: int = 200) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self._max_steps = max_steps
        self._states: list[State] = [initial]
        # Label of the edit that led to the state at the same position; the initial state has none.
        self._labels: list[str] = [""]
        self._position = 0

    @property
    def current(self) -> State:
        return self._states[self._position]

    @property
    def can_undo(self) -> bool:
        return self._position > 0

    @property
    def can_redo(self) -> bool:
        return self._position < len(self._states) - 1

    @property
    def undo_label(self) -> str:
        """Label of the edit `undo` would take back; empty when there is nothing to undo."""
        return self._labels[self._position]

    @property
    def redo_label(self) -> str:
        """Label of the edit `redo` would reapply; empty when there is nothing to redo."""
        return self._labels[self._position + 1] if self.can_redo else ""

    def record(self, state: State, label: str) -> None:
        """Add `state` as the result of an edit; a state equal to the current one is not an edit."""
        if state == self.current:
            return
        del self._states[self._position + 1 :]
        del self._labels[self._position + 1 :]
        self._states.append(state)
        self._labels.append(label)
        self._position += 1
        # Bound memory on very long sessions by forgetting the oldest edits.
        excess = len(self._states) - 1 - self._max_steps
        if excess > 0:
            del self._states[:excess]
            del self._labels[:excess]
            self._labels[0] = ""
            self._position -= excess

    def replace_current(self, state: State) -> None:
        """Swap the current state for an equal one that carries more detail; this is not an edit."""
        if state != self.current:
            raise ValueError("replace_current needs a state equal to the current one")
        self._states[self._position] = state

    def undo(self) -> State:
        if not self.can_undo:
            raise IndexError("Nothing to undo")
        self._position -= 1
        return self.current

    def redo(self) -> State:
        if not self.can_redo:
            raise IndexError("Nothing to redo")
        self._position += 1
        return self.current
