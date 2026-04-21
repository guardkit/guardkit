---
id: TASK-SMK-F703A
title: Feature-level smoke gates between autobuild waves (not between tasks)
status: backlog
task_type: implementation
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
priority: medium
complexity: 5
tags: [feature-build, autobuild, smoke-test, regression-gate, between-waves]
parent_review: TASK-REV-4D012
implementation_mode: task-work
depends_on:
  - TASK-BDD-E8954
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Feature-level smoke gates between autobuild waves

## Context

Follow-on from **TASK-REV-4D012** (AutoBuild Coach integration review). Report: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`, §6 R3.

The review's F4 finding: specialist-agent's FEAT-POR-EXT reported **13/13 tasks Coach-approved** and then failed on the first real `--phase roadmap` smoke test (129 `ProductRoadmap.model_validate` errors). Six patch tasks (PEX-014..020) were filed over ~36 hours, each fixing a bug that composition testing would have caught before approval. The per-task Player-Coach loop is structurally composition-blind.

## Problem Statement

AutoBuild has no gate between individual task approvals and feature-level verification. Composition failures are invisible to the Coach and only surface after `/feature-build` completes — at which point the patch loop is already expensive.

## Scope

### In-Scope

1. Extend `.guardkit/features/FEAT-*.yaml` schema with an optional `smoke_gates` section:

```yaml
smoke_gates:
  after_wave: 1             # or "all" or a list of wave numbers
  command: "python -m specialist_agent extract --phase A --smoke-fixture docs/smoke/fixture.md"
  expected_exit: 0
  timeout: 120
```

2. `/feature-build` (feature mode) runs the `command` inside the shared worktree after the specified wave completes. Exit code ≠ `expected_exit` → wave blocked, subsequent waves not started, worktree preserved, reported in final summary.
3. Schema validation: if `smoke_gates` key is present but malformed, surface a clear error before `/feature-build` starts.
4. Where the feature has a whole-feature `.feature` file (no task-scope tags), `smoke_gates.command` MAY be `pytest features/FEAT-X.feature` — this is how feature-level BDD composition is validated, completing R2's scoping boundary.

### Placement — CRITICAL

**Smoke gates run between WAVES, not between TASKS.**

- Between-task = re-invents the per-task Player-Coach loop with extra steps. Noisy. Wrong scope.
- Between-wave = composition starts to matter (one wave's outputs feed the next). Right scope.

If the implementer is tempted to make this per-task, that is a signal the scope has slipped and the design should stop.

### Wave definition — use the feature-plan dependency graph; do NOT invent

A "wave" is **not** a timer, a task count, or any new concept introduced by this task. A wave is defined by `/feature-plan`'s task dependency graph and already encoded in `.guardkit/features/FEAT-*.yaml`:

> **Wave N** = the set of tasks with no unsatisfied dependencies at the point in time when waves 1..N-1 have completed.

There is exactly one correct answer here and it already lives in the feature plan. Concretely:

- Read `tasks[].depends_on` and `tasks[].wave` from `FEAT-*.yaml` as they are.
- Compute wave boundaries by topological levels of the dependency graph — tasks in the same topological level form a wave.
- `smoke_gates.after_wave: 1` means "after the tasks forming topological level 1 have all been Coach-approved".

The existing AutoBuild feature-mode orchestrator already uses this wave concept for parallel scheduling. The smoke gate MUST use the same boundary definition. **Do not introduce a second wave concept scoped to smoke gates** — if the existing orchestrator is right about what wave 1 is, the smoke gate must agree; if the orchestrator is wrong, that's a separate bug, not something to paper over here.

### Out-of-Scope

- **Cross-phase Coach input** (loading prior task outputs into Coach prompt) — that's R4, deferred.
- Integration-test gates attached to individual tasks — that's R5, deferred.
- Auto-detecting smoke commands — the user writes the `smoke_gates.command` explicitly in `FEAT-*.yaml`.

## Acceptance Criteria

- [ ] `.guardkit/features/FEAT-*.yaml` loader accepts optional `smoke_gates` key. Schema documented in `docs/schemas/feature-yaml.md` (new or extended).
- [ ] Wave-boundary computation reuses the existing AutoBuild feature-mode wave definition (topological level of `tasks[].depends_on` / `tasks[].wave`). `tests/unit/orchestrator/test_smoke_wave_boundary.py::test_smoke_uses_existing_wave_definition` passes — asserts the smoke gate does not compute waves from any source other than the feature-plan dependency graph.
- [ ] `tests/unit/orchestrator/test_smoke_wave_boundary.py::test_after_wave_1_fires_when_topological_level_1_approved` passes — smoke gate configured with `after_wave: 1` fires after all topological-level-1 tasks are Coach-approved, regardless of wall-clock time.
- [ ] `tests/unit/models/test_feature_yaml_schema.py::test_smoke_gates_optional` passes — feature YAML without `smoke_gates` loads unchanged.
- [ ] `tests/unit/models/test_feature_yaml_schema.py::test_smoke_gates_malformed_raises` passes — malformed `smoke_gates` raises `SchemaValidationError` before `/feature-build` starts.
- [ ] `guardkit/orchestrator/autobuild.py` (feature mode) executes `smoke_gates.command` via subprocess after the specified wave completes, with timeout enforced.
- [ ] `tests/integration/autobuild/test_smoke_gate_blocks_wave.py::test_failing_smoke_stops_feature_build` passes — feature with failing smoke command causes `/feature-build` to stop after wave 1, worktree preserved, smoke failure in final summary.
- [ ] `tests/integration/autobuild/test_smoke_gate_noop.py::test_no_smoke_gates_key_runs_unchanged` passes — feature without `smoke_gates` runs identically to today.
- [ ] `tests/integration/autobuild/test_smoke_gate_bdd_integration.py::test_whole_feature_bdd_runs_as_smoke_gate` passes — `.feature` file at feature-level can be run via `smoke_gates.command: "pytest features/FEAT-X.feature"` with expected outcome.
- [ ] Implementation explicitly rejects per-task smoke invocation: `tests/unit/orchestrator/test_autobuild_smoke_placement.py::test_smoke_not_invoked_per_task` passes.
- [ ] User-facing doc: `docs/guides/feature-smoke-gates.md` explains when to use smoke_gates, how to write the command, and the between-waves-only placement rule.

## Implementation Notes

- Subprocess cwd must be the feature-mode shared worktree (`.guardkit/worktrees/FEAT-X/`), not the main repo.
- Timeout default 120s; cap 600s. Bounded to keep `/feature-build` deterministic.
- Failure mode: wave N+1 tasks are **not** started; currently-approved worktree contents are preserved for human triage.
- Depends on TASK-BDD-E8954 only for sequencing — the R2 scoping decision (task-level only) is what makes R3's feature-level territory coherent.

## Non-Goals / Guardrails

- **Do not default `smoke_gates` to anything.** Features without the key behave exactly as today. Zero regression risk.
- **Do not support a `smoke_gates.per_task` variant.** Per-task smoke is the per-task Coach with extra steps.
- **Do not introduce a new subsystem for "integration runners".** This is a subprocess call with a timeout. Keep it boring.
- **Do not invent a new wave concept.** Waves come from the feature-plan dependency graph already encoded in `FEAT-*.yaml`. If you find yourself writing wave-detection logic that doesn't read the existing `tasks[].depends_on` / `tasks[].wave`, stop — the concept already has exactly one correct definition and the smoke gate must match it.

## Related

- Review report: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` §6 R3
- Graphiti pattern: `"Review-gate hole: AutoBuild 13/13 green + e2e broken"` (specialist-agent/command_history.md:7405)
- Prior review with orthogonal remediation: `specialist-agent/tasks/backlog/TASK-REV-POEX-review-feat-por-ext-consolidation-path.md`
- Sibling task: `TASK-BDD-E8954` (task-level BDD — this task is the feature-level complement)
- Cohort: last of the three; jarvis tested first after all three land
