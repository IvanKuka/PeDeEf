# Change Workflow

1. Read repository routing and the relevant knowledge/spec documents.
2. Inspect the owning source and tests. Establish current behavior, input validation, cancellation and failure paths.
3. Resolve unclear requirements before implementation. For larger features use `ai/spec-interview.md`.
4. Make the smallest cohesive change. Reuse existing ownership boundaries and helpers.
5. Run the affected tests; broaden coverage when changes touch shared document writing, history, credentials or UI orchestration.
6. Review the diff for accidental changes, sensitive data and stale documentation. Update current knowledge/specs and user documentation as appropriate.
7. Report the result, actual checks and any unresolved limitations. Do not publish releases or push tags merely to verify a local change.

For documentation-only changes, verify referenced paths, Markdown links, JSON routing and identical agent instructions. A full application build is unnecessary unless runtime or packaging changes.

Use `ai/feature-<name>/` for a substantial feature's findings, decisions, design and verification plan. After completion, incorporate durable behavior into current docs before moving the dossier to `ai/archive/`.
