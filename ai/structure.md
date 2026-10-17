# AI Documentation Map

Start with root `STRUCTURE.md`, then `task-routing.md` or `index.json`. Paths in the routing index are relative to the repository root.

| Location | Purpose |
|---|---|
| `knowledge/pdf-core.md` | PDF IO, page selection, passwords and output safety |
| `knowledge/editing-workspace.md` | Page workspace, pending edits, undo/redo and projects |
| `knowledge/document-tools.md` | Overlays, forms, OCR, redaction, comparison and signatures |
| `knowledge/gui-shell-settings.md` | Startup, workspaces, shared UI, settings and updates |
| `knowledge/testing-build.md` | Tests, packaging and release entry points |
| `specs/README.md` | Current reusable GUI/behavior specs and source mappings |
| `spec.md` | Cross-module invariants |
| `conventions.md` | Coding and dependency conventions |
| `workflows.md` | Implementation and verification process |
| `spec-interview.md` | Questions to resolve before larger feature designs |
| `prompt-templates.md` | Short reusable task prompts |
| `operations-security.md` | Document privacy, credentials and update safety |
| `deployment/README.md` | Desktop build and release procedure |
| `archive/README.md` | Historical proposals and their status |

Keep these docs focused on ownership, behavior and entry points rather than duplicating every source file. Active larger-feature dossiers belong in `ai/feature-<name>/`; create one only when needed. Root `STRUCTURE.md` remains the canonical repository map.
