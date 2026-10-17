# Document Tools

Read the feature's implementation and dialog together, and trace its action in `pdftool/gui/pages_tab.py` when pending edits or saving are involved.

| Feature | Source entry points | Tests |
|---|---|---|
| Stamps/page numbering | `pdftool/stamps.py`, `pdftool/gui/stamp_layer.py`, `pdftool/gui/stamp_dialog.py` | `tests/test_stamps.py` |
| Typed text | `pdftool/gui/text_boxes.py`, `pdftool/gui/text_box_dialog.py` | `tests/test_text_boxes.py` |
| Forms | `pdftool/forms.py`, `pdftool/gui/form_filling.py`, `pdftool/gui/form_dialog.py` | `tests/test_forms.py` |
| Signature image | `pdftool/gui/signature.py`, `pdftool/gui/signature_dialog.py` | `tests/test_signature.py` |
| Certificate signing/integrity | `pdftool/signing.py`, `pdftool/gui/digital_signature_dialog.py` | `tests/test_signing.py` |
| OCR | `pdftool/ocr.py`, `pdftool/gui/recognition.py`, `pdftool/gui/ocr_dialog.py` | `tests/test_ocr.py`, `tests/test_ocr_engine.py` |
| Permanent redaction | `pdftool/gui/redaction.py`, `pdftool/gui/redaction_dialog.py` | `tests/test_redaction.py` |
| Images/export/compression | `pdftool/gui/images.py`, `pdftool/gui/export_dialog.py`, `pdftool/gui/compress_dialog.py`, `pdftool/operations.py` | `tests/test_images.py`, `tests/test_compress.py` |
| Search | `pdftool/text_search.py`, `pdftool/gui/search_bar.py` | `tests/test_search.py` |
| Visual comparison | `pdftool/gui/compare.py`, `pdftool/gui/compare_dialog.py` | `tests/test_compare.py` |
| Blank-page detection | `pdftool/gui/blank_pages.py`, `pdftool/gui/blank_pages_dialog.py` | `tests/test_blank_pages.py` |
| Crop/metadata | `pdftool/operations.py`, `pdftool/gui/crop_dialog.py`, `pdftool/gui/properties_dialog.py` | `tests/test_crop.py`, `tests/test_properties.py` |

Overlays reuse the stamp layer and PDF overlay assembly. Preview coordinate handling must account for visible page bounds and rotation. OCR invokes Tesseract; it is distinct from text search. Redaction rasterizes affected pages and verifies the result; it is distinct from a black overlay. Certificate signing is distinct from placing a signature image.

Read `ai/specs/preview-and-dialogs.md`, `ai/specs/document-editing.md` and `ai/operations-security.md` for shared rules.
