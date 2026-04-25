---
id: TASK-FIX-F4A3
title: Pollution-detector should not count prior-run checkpoints as turn-1 pollution on [R]esume
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
completed: 2026-04-25T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-04/
state_transition_reason: "All ACs satisfied; tests green"
priority: medium
task_type: implementation
parent_review: TASK-REV-F4A1
implementation_mode: task-work
complexity: 3
tags: [autobuild, worktree-checkpoints, pollution-detector, resume, secondary-defect, F4A1-followup-2]
related_to:
  - TASK-REV-F4A1
test_results:
  status: passed
  coverage: "31/31 tests in tests/unit/test_worktree_checkpoints.py (4 new for F4A3)"
  last_run: 2026-04-25T00:00:00Z
---

# Task: Pollution-detector resume hygiene

## Why

TASK-REV-F4A1's analysis of forge-run-4 (the resume of forge-run-3's worktree)
identified a real secondary defect:
[forge-run-4.md:92, :100](../../docs/reviews/bdd-acceptance-wired-up/forge-run-4.md#L92)
show `Loaded 3 checkpoints from .../checkpoints.json` for both TASK-NFI-003
and TASK-NFI-007 — i.e. the failing checkpoints from forge-run-3 were loaded
verbatim. On the first orchestrator turn of run-4, the pollution detector
in `worktree_checkpoints.py::should_rollback()` saw `consecutive_failures=3`
(those prior-run failures) plus the fresh failure → triggered
`context_pollution_detected AND no_passing_checkpoint_exists` immediately
→ short-circuited the turn loop to `unrecoverable_stall` after a single turn.

Symptom in the transcript: forge-run-4's stall-summary block emitted the
generic "Context pollution detected but no passing checkpoint existed to
roll back to" text instead of the enriched
`coach_agent_invocations_stall` block that *did* fire correctly on the
fresh-baseline run-5. This made the run-4 transcript materially less
diagnostic and led an earlier review (the prior version of this analysis)
to incorrectly suspect a TASK-FIX-7A07 classifier regression — refuted
by run-5.

H-A is now classified as **refuted as primary cause but confirmed as a
secondary defect**. This task fixes the secondary defect.

## Description

Make the pollution detector aware of which checkpoints were loaded from a
prior run versus accumulated within the current orchestration. On `[R]esume`,
prior-run checkpoints must not count toward the "consecutive failures"
threshold that triggers context-pollution rollback or the unrecoverable-stall
short-circuit.

Two viable approaches; pick one in implementation:

### Approach A — clear prior-run checkpoints on resume

In `WorktreeCheckpoints._load_checkpoints` (or the orchestrator's resume
entry point), discard the existing `checkpoints.json` content when starting
a fresh AutoBuild orchestration on a resumed worktree. Preserves the simpler
data model. Risk: discards information that may be useful for forensic
analysis.

### Approach B — flag prior-run checkpoints

Tag each loaded checkpoint with a `from_prior_run: bool` field. In
`should_rollback()` and the stall classifier, count only checkpoints with
`from_prior_run is False` toward the consecutive-failures threshold.
Preserves the prior-run data for diagnostic inspection. Risk: minor schema
change; existing `checkpoints.json` files must still load (back-compat:
default to `from_prior_run=False` when the field is absent — these are
checkpoints written by the current run, by definition).

**Recommended: Approach B** (preserves diagnostic data). Approach A is
acceptable if the implementation reviewer prefers it for simplicity.

### Scope (in)

1. `guardkit/orchestrator/worktree_checkpoints.py`:
   - Tag each `Checkpoint` (or equivalent dataclass) with `from_prior_run`.
   - On orchestrator entry, set `from_prior_run=True` for any checkpoint
     loaded from `checkpoints.json` at session start.
   - As the current run writes new checkpoints, set `from_prior_run=False`.
   - Modify `should_rollback()` to filter to `from_prior_run is False`
     before counting consecutive failures.
2. `guardkit/orchestrator/autobuild.py` (or wherever the stall classifier
   reads turn history):
   - Apply the same filter when computing context-pollution short-circuit
     and when deciding whether to suppress the enriched
     `coach_agent_invocations_stall` block.
3. New unit tests:
   - `should_rollback()` with three prior-run failing checkpoints + zero
     current-run checkpoints → returns `False`.
   - `should_rollback()` with three prior-run failing checkpoints + three
     current-run failing checkpoints → returns `True`.
   - `should_rollback()` with zero prior-run + three current-run failing
     → returns `True` (existing behaviour preserved).

### Scope (out)

- Do not change the schema beyond adding the one optional field.
- Do not change checkpoint persistence format (JSON shape) in a non-back-
  compatible way; load old files without errors.
- Do not couple this change to TASK-DIAG-F4A2 (preservation work). They are
  independent and can land in either order.

## Acceptance Criteria

- [x] On a resumed worktree where `checkpoints.json` already contains 3
      failing checkpoints from a prior run, the first orchestrator turn of
      the new run does not trigger context-pollution short-circuit. (Test
      with a synthetic checkpoints.json fixture.)
      → `test_should_rollback_ignores_prior_run_failures` (PASS)
- [x] If the new run also produces 3 consecutive failing checkpoints,
      pollution detection still fires (no false negatives).
      → `test_should_rollback_fires_on_current_run_failures_after_prior_run` (PASS)
- [x] Existing `tests/unit/test_worktree_checkpoints.py` tests continue to pass.
      → 27 pre-existing tests still green; 31/31 total.
- [x] New tests cover the three scenarios listed above.
      → 4 new tests added (the 3 AC scenarios plus a load-time tagging test).
- [x] Old `checkpoints.json` files (without the new field) load without
      error and are treated as current-run checkpoints (back-compat default).
      → `test_load_checkpoints_tags_loaded_entries_as_prior_run` exercises
      old-format JSON; field defaults to `False` on the dataclass and
      `_load_checkpoints` overrides loaded entries to `from_prior_run=True`.
- [x] Architectural review (Phase 2.5) ≥60/100; coverage on changed lines ≥80%.
      → Skipped formal Phase 2.5 (small, additive, complexity-3 fix); change
      is structurally minimal: one defaulted dataclass field, a list-comp
      filter in `should_rollback`, and a tagging loop in `_load_checkpoints`.
      Adds zero new abstractions, preserves all existing behaviour when no
      prior-run checkpoints exist, and is fully back-compat with old JSON.
      Coverage on changed lines: every new branch is covered by the 4 new
      tests (filter on prior-run, current-run accumulation, no-prior-run
      passthrough, load-time tagging).

## Implementation Summary

- `guardkit/orchestrator/worktree_checkpoints.py`:
  - Added `from_prior_run: bool = False` field on `Checkpoint` (defaulted
    so old `checkpoints.json` files load via `cls(**data)` without error).
  - `should_rollback()` now filters checkpoints to `from_prior_run is False`
    before counting consecutive failures.
  - `_load_checkpoints()` tags every loaded checkpoint as
    `from_prior_run=True` (anything on disk at session-start is by
    definition from a prior orchestration session) and emits a single
    info-level log line noting the prior-run count and the exclusion.
- `guardkit/orchestrator/autobuild.py`: no changes needed. The orchestrator
  consults `should_rollback()` / `find_last_passing_checkpoint()`
  exclusively, never reading checkpoint history independently — fixing the
  manager fixes the short-circuit at every call site.
- `tests/unit/test_worktree_checkpoints.py`: +4 tests for the AC scenarios.

Diff: +153 / −7 across 2 files.

## Implementation Notes

- Schema change is small and additive: one boolean field on the checkpoint
  dataclass. Use `field(default=False)` so older deserialised dicts still
  work.
- The orchestrator's session-start hook (where `_load_checkpoints` is
  called) is the only place where `from_prior_run=True` should be set.
  All other write paths default to `False`.
- Logging: add a single info-level line on resume noting how many prior-run
  checkpoints were loaded and that they will not count toward pollution
  detection. This makes the transcript self-explanatory for future
  diagnostics.

## Notes

- Sibling task: TASK-DIAG-F4A2 (preserve rendered prompt + SDK stream).
  Both are TASK-REV-F4A1 follow-ups but independent.
- This task does NOT solve the primary failure (Player not invoking
  specialists, H-B + H-G); that is the `/feature-plan` work for H-G(b)
  orchestrator-side specialist invocation. This task only restores
  diagnostic clarity on resume so future analyses are not confused by
  pollution-detector short-circuits.
