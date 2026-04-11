---
id: TASK-DOC-C3D7
title: Document the two-layer template model (config layer + pattern layer)
status: backlog
created: 2026-04-11T15:15:00Z
updated: 2026-04-11T15:15:00Z
priority: medium
tags: [documentation, templates, guardkit-init, autobuild, software-factory]
parent_review: TASK-REV-A5F8
feature_id: FEAT-1A5E
implementation_mode: direct
complexity: 3
depends_on: [TASK-PAT-1A5E]
blocked_reason: "Must not ship until TASK-PAT-1A5E reaches design-approved state — docs that describe unwired pattern layer would ship a half-truth"
---

# Task: Document the two-layer template model

## Background

Surfaced by [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md) (see [review report](../../../.claude/reviews/TASK-REV-A5F8-review-report.md), Section 1 "Recommended F4B8 plan" — TASK-DRF-F4B8a).

GuardKit builtin templates have two distinct layers and it is not documented anywhere a template author, task reviewer, or new contributor would naturally look:

1. **Config layer** — `.claude/`, `agents/`, `manifest.json`, `settings.json`, `CLAUDE.md`, `README.md`. Consumed by `guardkit init` at project-setup time.
2. **Pattern layer** — `templates/*.template` files. Produced by `/template-create`. Consumed by the AutoBuild Player at feature-build time (once [TASK-PAT-1A5E](TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md) wires the consumer).

TASK-REV-D0C1's smoke test and TASK-REV-A5F8's scope-discovery both show that new template authors and reviewers expect `guardkit init <template>` to scaffold a working project from the pattern layer files, and are confused when it doesn't. The fix is documentation — but only after the pattern-layer consumer (TASK-PAT-1A5E) is at least design-approved, so docs describe real wiring rather than future intent.

## Description

Add clear documentation of the two-layer template model and the roles of `guardkit init` vs the AutoBuild Player.

## Acceptance Criteria

- [ ] New section "Template layers: config vs pattern" added to `installer/core/templates/README.md` (create file if absent)
- [ ] New guide at `docs/guides/template-layers-guide.md` (or updates to an existing template philosophy doc if one exists) covering:
  - What `guardkit init` copies and does NOT copy
  - What the pattern layer is for
  - Which commands produce the pattern layer (`/template-create`) and consume it (AutoBuild Player via TASK-PAT-1A5E)
  - Guidance for template authors on where to put new files
- [ ] `templates/README.md` stub added to all 10 builtin templates (one paragraph explanation + pointer to TASK-PAT-1A5E's wiring and the new `template-layers-guide.md`):
  - `installer/core/templates/default/templates/`
  - `installer/core/templates/dotnet-railway-fastendpoints/templates/`
  - `installer/core/templates/fastapi-python/templates/`
  - `installer/core/templates/fastmcp-python/templates/`
  - `installer/core/templates/langchain-deepagents/templates/`
  - `installer/core/templates/mcp-typescript/templates/`
  - `installer/core/templates/nats-asyncio-service/templates/`
  - `installer/core/templates/nextjs-fullstack/templates/`
  - `installer/core/templates/python-library/templates/`
  - `installer/core/templates/react-fastapi-monorepo/templates/`
  - `installer/core/templates/react-typescript/templates/`
- [ ] `/template-create` post-generation output updated to include a one-line explanation of what the generated `templates/` subdirectory is for
- [ ] Root `CLAUDE.md` updated if its Installation or Templates section implies `init` scaffolds source code (quick audit only; no exhaustive rewrite)
- [ ] No references in the new docs to the original "reference material" framing (rejected in TASK-REV-A5F8 revision)

## Must NOT

- [ ] Must not describe the pattern layer as "consumed by AutoBuild Player" unless TASK-PAT-1A5E has reached at least design-approved state with a concrete consumer path. If the wiring is not yet real, hold this task in backlog.
- [ ] Must not introduce new rename-style changes to the `templates/` directory name — that is TASK-REN-B9F2's scope.

## References

- Parent review: [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md)
- Review report: [.claude/reviews/TASK-REV-A5F8-review-report.md](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
- Superseded by this task: [TASK-DRF-F4B8](../TASK-DRF-F4B8-clarify-template-scaffolding-vs-config-layer.md)
- Dependency: [TASK-PAT-1A5E](TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md)
