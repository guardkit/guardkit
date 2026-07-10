# design-url-integration — CLOSED 2026-07-10 (superseded)

**Disposition:** All tasks in this folder are closed to `completed/` as part of the design-tool
trio retirement — `docs/decisions/DEC-design-tool-trio-retirement.md` (DF-018 §2.4 Option A,
ACCEPTED Rich 2026-07-09).

## What happened

This 2025-11-11 folder planned a migration: deprecate the stack-specific `/figma-to-react`,
`/zeplin-to-maui` (and, per DF-018 §2.4, `/mcp-zeplin`) commands in favour of a unified
`/task-create design:` workflow. The migration never ran; `TASK-UX-2DAB`'s
`removal_planned: 2026-06-01` **lapsed unexecuted**.

On 2026-07-10 the migration's *from*-side was **retired** (the three command markdowns deleted +
tombstoned via the PB-3 path). The technology-agnostic design capability the folder aimed at had
already shipped **separately, at the orchestrator layer** —
`guardkit/orchestrator/mcp_design_extractor.py` + `guardkit/design/` — not through these
command-level tasks.

## Status of each task

Every task here is closed as **superseded / obsolete**, NOT as individually delivered:

- `TASK-UX-2DAB` (deprecate old commands) — **executed** as retirement (stronger than deprecation).
- The command-file-modification tasks (orchestrator refactors, update-claude-md, update-task-refine,
  user-guide) — targeted files that are now deleted, or a `/task-refine` command itself retired
  2026-07-09; moot.
- The new-workflow build tasks (`add-design-url-parameter`, `design-url-validation`,
  ui-specialist extensions, pattern docs) — the design capability lives in the orchestrator
  `design_url` path; these command-integration tasks are superseded, not shipped as written.

Closed for tracker hygiene (WS3-S8a declared-vs-inferred divergence). Future technology-agnostic
design work runs through the orchestrator `design_url` path, not a revived stack-specific command.

The two orchestrator design docs (`figma-react-orchestrator.md`, `zeplin-maui-orchestrator.md`)
travel with this folder as historical records.
