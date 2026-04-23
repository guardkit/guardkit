---
id: TASK-FIX-RWOP1.4
title: /feature-spec — decide Phase 5 Coach low-confidence gating wiring + FeatureSpecCommand dead-surface disposition
status: completed
task_type: review
review_mode: decision
review_depth: standard
decision_required: true
decided_at: 2026-04-22
decision_doc: .claude/reviews/TASK-FIX-RWOP1.4-decisions.md
decisions:
  part_a: WIRE (warn-mode)
  part_b: DELETE
execution_subtasks:
  - TASK-FIX-RWOP1.4a
  - TASK-FIX-RWOP1.4b
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: medium
complexity: 4
tags: [runner-without-producer, feature-spec, coach-gating, assumptions, dead-code, rwop1]
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_to: TASK-REV-RWOP1
related_tasks:
  - TASK-REV-RWOP1
  - TASK-FIX-RWOP1.4a
  - TASK-FIX-RWOP1.4b
test_results:
  status: n/a
  coverage: null
  last_run: null
---

# Task: /feature-spec — Phase 5 Coach gating decision + FeatureSpecCommand disposition

## Problem Statement

[TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
§Per-file findings (feature-spec.md) identified two separable
runner-without-producer concerns in
[installer/core/commands/feature-spec.md](../../../installer/core/commands/feature-spec.md):

**Concern 1 — Phase 5 Coach low-confidence assumption gating (line 337):**

Spec says: *"If any assumption has `confidence=low` after Phase 5,
the output summary will include a `REVIEW REQUIRED` flag. The Coach
is expected to verify all low-confidence assumptions before accepting
the specification."*

Grep of `guardkit/orchestrator/quality_gates/coach_validator.py` for
`assumptions.yaml`, `confidence`, `ASSUM-`, `REVIEW REQUIRED` returns
zero matches. The "Coach is expected to verify" sentence is
aspirational — no code enforces it. A cohort run producing
`_assumptions.yaml` files with `confidence: low` entries will have
Coach proceed without reading them, and the run will look green.

**Concern 2 — `FeatureSpecCommand` Python orchestrator is an
entirely dead surface:**

`/feature-spec` is executed by Claude interpreting
`.claude/commands/feature-spec.md` prose. The Python orchestrator at
`guardkit/commands/feature_spec.py` has 32+ unit-test references
(`tests/unit/commands/test_feature_spec.py`) + 12+ integration-test
references + 0 non-test production callers. `guardkit/cli/feature.py`
does not import it. `guardkit/cli/main.py`, `task.py`, `autobuild.py`
do not import it. The module's private producers — `detect_stack`,
`scan_codebase`, `_read_input_files`, `write_outputs`,
`seed_to_graphiti` — are all transitively orphan: they exist for the
orchestrator that itself has no caller.

`seed_to_graphiti` has an additional nuance — it is shadowed by a
live twin at `guardkit/integrations/graphiti/parsers/feature_spec.py`
which is the actually-invoked seeder. So the orchestrator's version
is not merely orphan; it is a second implementation of a live code
path. Either promote the orchestrator or delete the duplicate.

Both concerns have the same root cause: `.claude/commands/feature-spec.md`
prose is load-bearing, and the Python surface is a by-product of the
"we'll implement this for real later" pattern that never got its later.

## Scope

### In-Scope

**Part A — Phase 5 Coach low-confidence gating decision:**

Pick ONE of three paths and capture the rationale in the
implementation plan:

1. **WIRE**: add a `coach_validator` hook that (a) locates
   `features/**/_assumptions.yaml`, (b) filters rows with
   `confidence: low` AND no `human_response: confirmed`, (c) emits a
   Coach-visible warning/block (depending on how strict the gate
   should be). Implementation should match the R5 gating twin of the
   TASK-FIX-3C9D R1 linter fix — same shape, different verifier.
2. **SOFTEN PROSE**: rewrite feature-spec.md line 337 to drop the
   Coach claim. Change to: "The output summary includes a `REVIEW
   REQUIRED` flag for any low-confidence assumption; humans should
   review before approving the specification." Honest, matches reality.
3. **ESCALATE**: flag as a separate FEAT-RWOP1-GATING sub-feature if
   the wire path has significant design work (integration with
   existing Coach flows, severity levels, opt-in vs opt-out, etc.).

**Part B — FeatureSpecCommand disposition:**

Pick ONE of two paths:

1. **PROMOTE to CLI entry**: add `feature_spec.py` (or a thin
   wrapper) to
   [installer/core/commands/bin-entries.txt](../../../installer/core/commands/bin-entries.txt),
   add a `guardkit feature spec` subcommand in
   `guardkit/cli/feature.py` that invokes
   `FeatureSpecCommand.execute()`. Rewrite the spec prose to include
   an `Execute: python3 ~/.agentecflow/bin/...` imperative for users
   who want deterministic output. (Claude-runtime interpretation
   remains the default; CLI is an opt-in backstop.)
2. **DELETE**: remove `guardkit/commands/feature_spec.py`. Move
   `seed_to_graphiti` logic into the live parser at
   `guardkit/integrations/graphiti/parsers/feature_spec.py` if any of
   it is not already duplicated there. Remove the corresponding unit
   + integration test files. Update `guardkit/commands/__init__.py`
   re-exports. Remove the `.guardkit/quality-gates/FEAT-1253.yaml:22`
   smoke-import if present.

The two parts can be decided independently — one could PROMOTE
Part B while SOFTEN-ing Part A, for example.

### Out-of-Scope

- The cross-command Step 11 reference in feature-spec.md lines 501-525
  — that is the same orphan as `feature-plan.md` Step 11, fixed by
  [TASK-FIX-RWOP1.1](r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md).
- Phase 1c Graphiti ADR/domain-warning query (producer-ambiguous, low
  severity) — record the decision here but the wire work is optional
  follow-on.
- Refactoring the `_assumptions.yaml` format or the Phase 5 interview
  loop.
- Integrating `/feature-spec` with RequireKit EARS notation — separate
  feature track.

## Acceptance Criteria

- [ ] Part A decision (WIRE / SOFTEN / ESCALATE) captured with
      1-2 paragraph rationale in
      `.claude/reviews/TASK-FIX-RWOP1.4-decisions.md`.
- [ ] Part B decision (PROMOTE / DELETE) captured in the same file.
- [ ] Part A executed: either a Coach hook exists and is covered by
      at least one end-to-end test that produces a `_assumptions.yaml`
      with a `confidence: low` row and asserts Coach's behaviour; OR
      the feature-spec.md line 337 prose is updated and tests remain
      green.
- [ ] Part B executed: either a CLI entry exists and installs via
      `bin-entries.txt`; OR the Python module is deleted along with
      its tests, and no `guardkit/` / `installer/` import-surface
      references it.
- [ ] Post-execution, rerun the runner-without-producer grep for
      `feature-spec.md` per the parent review's method and record the
      new wiring rate. Target: ≥ 50 % for hard-module imperatives (up
      from 10 %).

## Implementation Notes

- Part A is the R2/R3-adjacent concern — low-confidence assumptions
  that Coach doesn't catch could cascade into BDD scenarios that are
  subtly wrong (the human never confirmed the ambiguous bit), and
  those scenarios then drive `/task-work`'s BDD oracle. If you think
  Part A should be WIRE, prioritise it over Part B.
- Part B is the clearer "dead code" case. DELETE is probably cheaper
  than PROMOTE given there's an actively-maintained twin at
  `graphiti/parsers/feature_spec.py`. But PROMOTE unlocks the
  possibility of a deterministic `/feature-spec` CLI for headless /
  CI workflows — not a trivial capability. Weigh against how often
  that would actually be used.
- **Do NOT block TASK-COH-RUN1 on this task.** Finding severity is
  medium, not cohort-critical.
- Consider running this as a `/task-review --mode=decision` since
  both parts are decisions, not implementations. That captures the
  rationale structurally and can spawn sub-tasks for execution.

## Related

- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
  §Per-file findings (feature-spec.md), §Orphans #1, #2, #4
- Canonical fix shape (R1 precedent):
  [tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Feature orchestrator guide:
  [FEAT-RWOP1-IMPLEMENTATION-GUIDE.md](../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md)
- Design-rule candidate (Graphiti): *"runner without producer
  anti-pattern"* — uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`
