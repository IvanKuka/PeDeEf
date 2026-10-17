# Cross-Module Invariants

1. Documents are processed locally. Automatic update traffic must not contain document data or credentials.
2. User files are written only through explicit output/save actions. Preserve confirmation, cancellation and source-file protection behavior.
3. PDF writes use atomic replacement. Failure must preserve the previous target and pending edits.
4. Editing actions participate in undo/redo. Materialized edits use encrypted private working copies with session-only random passwords, retained while history needs them.
5. Passwords and signing secrets are not persisted to settings, projects, logs or documentation.
6. Cropping hides content; overlays add content. Neither is permanent redaction. Redaction replaces affected pages with raster images and validates that text/annotations are absent before output is accepted.
7. Page extraction/removal must not retain excluded pages through indirect references or unused resources.
8. Signature verification reports offline integrity/coverage, not certificate trust. Ordinary rewrites must not imply existing digital signatures remain valid.
9. Keep core logic separate from widget orchestration. Preserve Windows/macOS packaging and existing dependency license constraints.

Consult feature-level specs and actual code for detailed contracts. Change these invariants only as part of an explicitly scoped behavior change.
