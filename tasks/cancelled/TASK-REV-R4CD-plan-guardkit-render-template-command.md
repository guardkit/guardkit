---
id: TASK-REV-R4CD
title: "Plan: first-class guardkit render command for template pattern layer"
task_type: review
status: cancelled
priority: high
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
cancelled_at: 2026-04-18T00:00:00Z
tags: [planning, cli, templates, render, pattern-layer, superseded]
complexity: 7
source_review: TASK-REV-A925
source_recommendation: R4
superseded_by: docs/research/pattern-layer-rendering/SCOPE-system-arch-pattern-layer-rendering.md
cancellation_reason: >-
  Scope handed off to `/system-arch` before subtask generation. During the
  `/feature-plan` flow, analysis from Claude Desktop surfaced three shifts
  that invalidated the in-flight decomposition:
  (1) A shared rendering LIBRARY (Option D) should precede any CLI surface
      decision — committing to `guardkit render` as a CLI shape before the
      library primitive existed was premature.
  (2) `guardkit render` (Option A) and Player-context injection (Option C /
      FEAT-1A5E) are complementary consumers of the same primitive, not
      alternatives.
  (3) A manifest `pattern_layer` schema extension is the real architectural
      move — it retroactively invalidates the Context A Q4 answer
      (integrated-flag `init --render`, which re-litigates the settled
      TASK-INST-010 / TASK-REV-A5F8 config-layer split).
  The architecture is unsettled and warrants an Architect-owned design pass
  rather than subtask generation. Scope doc produced for `/system-arch`.
clarification:
  context_a:
    timestamp: 2026-04-18T00:00:00Z
    decisions:
      focus: all
      tradeoff: maintainability
      layout_contract: hybrid
      init_relationship: integrated_flag
      concerns: [feat_1a5e_interaction, lcl_003_backcompat, placeholder_contract, scope_boundary]
    invalidated_by_cancellation: true
test_results:
  status: cancelled
  coverage: null
  last_run: null
---

> **Cancelled 2026-04-18.** See `docs/research/pattern-layer-rendering/SCOPE-system-arch-pattern-layer-rendering.md`
> for the superseding scope document handed off to `/system-arch`.
> Rationale is in the `cancellation_reason` field above.
> The `/feature-plan` flow will resume once the Architect's output is in
> hand, as one or more feature-plan sessions — likely one per deliverable
> (library, manifest schema + migration, `guardkit render` CLI).

# Task: Plan — first-class `guardkit render <template>` command for template pattern layer

## Description

Execute a design-focused decision review for R4 of
[TASK-REV-A925](../../.claude/reviews/TASK-REV-A925-review-report.md) — promoting
the prototype `_render_template` / `_resolve_target` / layout-map logic from
[tests/integration/test_template_render_import.py](../../tests/integration/test_template_render_import.py)
into a first-class `guardkit render <template>` CLI command.

This is the "capability-gap" recommendation from TASK-REV-A925. It is explicitly
hinted at in LCL-003's module docstring:

> If the installer ever grows a first-class `.template` renderer
> (`guardkit render` or an importable `render_template(...)` API), swap the
> local `_render_template` helper for it — see `_RENDER_IMPL` sentinel.

## Background

All 10 builtin templates ship a `templates/` pattern layer that is **never
rendered by `guardkit init`**. This is deliberate (TASK-INST-010, 2026-03-02,
re-affirmed by TASK-REV-A5F8). Consumers that expect a runnable project
(e.g. the Forge) discover the partition only when downstream workflows fail.

The user has selected the **integrated-flag** relationship model: `guardkit init
<template> --render` runs both layers in one command, while `render` remains
standalone. Layout contract will be **hybrid** (manifest.json declarative +
convention fallback + optional plugin escape hatch). Trade-off priority is
**maintainability**.

## Review Scope (Context A)

- Focus: **all dimensions** (technical + architecture + design contracts)
- Trade-off priority: **maintainability** (long-lived CLI; manifest-driven
  contract must be stable)
- Layout contract: **hybrid** (manifest.json + convention + plugin fallback)
- Init relationship: **integrated flag** (`init --render`) + standalone `render`
- Concerns to address:
  - FEAT-1A5E interaction (render and AutoBuild Player must share layout
    contract — no divergence)
  - Backwards compatibility with LCL-003's `_render_template` shim
    (migration path via `_RENDER_IMPL` sentinel)
  - Placeholder substitution contract (strict `{{Key}}` vs Jinja for `.j2`
    templates)
  - Scope boundary (render stays out of init's config-layer responsibility;
    no overlap with FEAT-1A5E's Player-consumer wiring)

## Acceptance Criteria

- [ ] Review produces a decision report in `.claude/reviews/TASK-REV-R4CD-review-report.md`
- [ ] Report covers all 5 design questions from R4 (layout source, output dir,
      placeholder contract, init relationship, FEAT-1A5E interaction)
- [ ] Report defines the manifest.json `rendering` schema (hybrid model)
- [ ] Report defines the migration path for LCL-003's `_render_template` shim
- [ ] Report identifies complementary (non-competing) boundaries with FEAT-1A5E
- [ ] Decision checkpoint presents [A]ccept / [R]evise / [I]mplement / [C]ancel
- [ ] If [I]mplement: produces `tasks/backlog/render-command/` with subtasks

## Related Tasks

- Source review: [TASK-REV-A925](../../.claude/reviews/TASK-REV-A925-review-report.md) (R4)
- Prior reviews: [TASK-REV-A5F8](../../.claude/reviews/TASK-REV-A5F8-review-report.md) (config-layer split reaffirmation)
- Complementary feature: [FEAT-1A5E](./template-pattern-layer/README.md) (Player-consumer wire-in)
- Prototype implementation: [test_template_render_import.py](../../tests/integration/test_template_render_import.py) (LCL-003)
- Architectural precedent: [TASK-INST-010](../design_approved/TASK-INST-010-reconcile-init-paths.md) (skip code scaffolds decision)

## Review Approach

Execute via `/task-review TASK-REV-R4CD --mode=decision --depth=standard` with
architectural + technical + integration focus.
