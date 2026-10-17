# Document Editing and Output

Owners: `pdftool/gui/pages_tab.py`, `pdftool/operations.py`, `pdftool/history.py`, `pdftool/working_document.py`.

- Page actions preserve page order/selection and make coherent undoable changes.
- Tool edits can be combined without asking for a destination after each action. Materialized edits use validated encrypted working copies; source documents are tracked separately for final protection decisions.
- Undo/redo restores the corresponding document state. Working copies remain usable for retained history and are cleaned up on document lifecycle transitions.
- Save writes the current document after explicit replacement confirmation; Save As chooses another destination. Cancellation preserves work.
- A failed write preserves the existing destination and pending edits. Atomic output helpers remain the shared write boundary.
- Metadata, password handling, omitted-page cleanup and permanent-redaction checks must survive composed edits.

Verify `tests/test_pending_edits.py`, `tests/test_history.py`, `tests/test_operations.py`, and relevant password/redaction/GUI tests for changes crossing those boundaries.
