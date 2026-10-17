# PDF Core, Merge and Batch

`pdftool/operations.py` owns `PageRef`, PDF opening, page assembly, crop/metadata handling, password cache and atomic writes. `page_ranges.py` parses user selections; `pdf_resources.py` removes unused page resources. Core operations do not own GUI prompts.

Start with `write_pdf`, `write_pages`, `split_pages`, `apply_overlay` or `write_optimized` for their respective workflows. Preserve `_finish` and excluded-page cleanup; copying a page must not retain omitted content through shared references. Use `write_file_atomically` rather than writing directly to the destination.

`gui/merge_tab.py` orchestrates merging and images. `batch.py` owns batch rules/results and non-overwriting names; `gui/batch_tab.py` owns background UI and cancellation. Batch processing does not reuse another workspace's cached password.

Tests: `tests/test_operations.py`, `tests/test_page_ranges.py`, `tests/test_crop.py`, `tests/test_properties.py`, `tests/test_passwords.py`, `tests/test_compress.py`, `tests/test_batch.py`. For input/output behavior also read `ai/specs/document-editing.md` and `ai/operations-security.md`.
