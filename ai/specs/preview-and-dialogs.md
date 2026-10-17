# Preview and Tool Dialogs

Owners: `pdftool/gui/page_grid.py`, `pdftool/gui/page_preview.py`, `pdftool/gui/zoomed_page.py`, `pdftool/gui/stamp_layer.py` and adjacent feature dialogs.

- Reuse shared page rendering and zoom/pan surfaces rather than duplicating a viewer for each tool.
- Preview placement and final output must agree for crop bounds, rotation and page dimensions. Follow the existing feature's coordinate conversion rather than assuming raw PDF coordinates equal widget coordinates.
- Tool dialogs validate input before applying work. Cancel must leave document state unchanged.
- Reuse shared widgets, icons, Slovak labels and error dialogs. Preserve keyboard access and clear selection/enabled states.
- Long-running tools retain their existing progress and cancellation mechanisms.
- Distinguish visual previews from output guarantees: a black rectangle is not secure redaction, and a signature image is not a cryptographic signature.

Verify the affected feature's tests listed in `ai/knowledge/document-tools.md`, plus GUI tests when shared selection/rendering changes.
