# Operations and Security

- PDF document processing is local. The update subsystem contacts GitHub; document processing must not become network-dependent.
- PDF passwords are session-only. Clear cached credentials when their working copies are discarded or the document closes; never place secrets in QSettings or project files.
- Use `operations.write_file_atomically` for final file replacement. Exercise write errors without losing the target or pending edits.
- Private edit copies are encrypted in `PagesTab._apply_document_edit`; `WorkingDocument` owns temporary paths and cleanup. Preserve the distinction between original source protection and a random working-copy password.
- Batch processing must not borrow a password entered in another workspace and must preserve its non-overwriting output naming.
- Redaction is security-sensitive: inspect `pdftool/gui/redaction.py` and `tests/test_redaction.py`; crop rectangles, stamps and black overlays cannot substitute for it.
- Inspect `pdftool/signing.py` for P12/PFX handling. Offline signature integrity does not prove a trusted identity; certificate/key material must not be logged or persisted.
- Update downloads are checked against release `SHA256SUMS.txt`. A checksum detects mismatches but is not an independent signature of the publisher. Preserve existing download verification and update-confirmation behavior.
- Keep bundled OCR license notices and verified language-data checksums aligned with build changes. Never include user PDFs, local credentials or runtime caches in artifacts.
