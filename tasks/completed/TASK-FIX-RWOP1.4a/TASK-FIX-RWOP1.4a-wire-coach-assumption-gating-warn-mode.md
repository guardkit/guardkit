---
id: TASK-FIX-RWOP1.4a
title: Wire Coach low-confidence assumption gating into coach_validator (warn-mode)
status: completed
task_type: feature
created: 2026-04-22T00:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
completed_location: tasks/completed/TASK-FIX-RWOP1.4a/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; human review confirmed via /task-complete"
organized_files:
  - TASK-FIX-RWOP1.4a-wire-coach-assumption-gating-warn-mode.md
priority: medium
complexity: 4
tags: [runner-without-producer, feature-spec, coach-gating, assumptions, warn-mode, rwop1]
parent_task: TASK-FIX-RWOP1.4
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
depends_on:
  - rwop1-sweep-commit  # Commit the uncommitted RWOP1 artifacts first (see Preconditions)
related_to: TASK-FIX-RWOP1.4
related_tasks:
  - TASK-FIX-RWOP1.4
  - TASK-FIX-3C9D  # R1 precedent — same shape, different verifier
test_results:
  status: passed
  suite: tests/integration/autobuild/test_assumption_confidence_gate.py
  passed: 6
  failed: 0
  last_run: 2026-04-23T00:00:00Z
  notes: "R5 precedent test (tests/integration/autobuild/test_agent_invocations_gate.py) and test_agent_invoker.py::TestWriteTaskWorkResults also re-run green (29 related tests total)."
---

# Task: Wire Coach low-confidence assumption gating (warn-mode)

## Decision Origin

Execution sub-task for Part A of [TASK-FIX-RWOP1.4](TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md). Decision rationale captured in [.claude/reviews/TASK-FIX-RWOP1.4-decisions.md](../../../.claude/reviews/TASK-FIX-RWOP1.4-decisions.md) §Part A.

Verdict: **WIRE in warn-mode** (not block).

## Problem Statement

`installer/core/commands/feature-spec.md:337` declares that the Coach "is expected to verify all low-confidence assumptions before accepting the specification." No code enforces this — grep of `guardkit/orchestrator/quality_gates/coach_validator.py` for `assumptions.yaml`, `confidence`, `ASSUM-`, `REVIEW REQUIRED` returns zero matches. A cohort run producing `features/**/_assumptions.yaml` with `confidence: low` rows (and no `human_response: confirmed` counterpart) will have Coach proceed silently and the run will look green, despite a premise that a human was meant to resolve still being ambiguous.

This is the R5-positioned twin of the R1 AC-linter failure class that [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md) resolved: a Coach-visible gate declared in prose, no producer in code, downstream pipeline artifacts silently built on the unchecked premise.

## Scope

### In-Scope

- Add a Coach-consumable validator that:
  - Locates `features/**/_assumptions.yaml` files in the workspace under validation.
  - Filters rows with `confidence: low` AND no matching `human_response: confirmed` entry.
  - Writes the filtered set into `task_work_results.json` under a new field (e.g. `unconfirmed_low_confidence_assumptions: [{file, id, text}, ...]`).
- Extend `guardkit/orchestrator/quality_gates/coach_validator.py` to read that field and surface it as a **warning** in Coach's decision output (not a failure). Coach still approves if other gates pass; the warning is attached to the approval so a human reviewing the merge can see it.
- Add one end-to-end test that:
  - Materialises a fixture workspace with a `_assumptions.yaml` containing at least one `confidence: low` row without a confirming `human_response`.
  - Runs the validator and asserts the warning field is populated with the expected row.
  - Also asserts the inverse: a `_assumptions.yaml` with all low-confidence rows confirmed produces an empty warning list.

### Out-of-Scope

- **Do NOT** convert warn-mode into block-mode. Rationale recorded in the decision doc §Part A "Why warn, not block". Escalation to block would be a separate task driven by evidence that warn-mode is being ignored.
- Severity levels, opt-in/opt-out config, integration with `/feature-plan` Step 5 human-response loops. These are the ESCALATE-path concerns — recorded but not in scope.
- Any refactor of the `_assumptions.yaml` schema itself. Consume it as-is.
- Touching `_assumptions.yaml` producers (they already emit the `REVIEW REQUIRED` summary flag per feature-spec.md prose — that path stays).

## Acceptance Criteria

- [x] New validator module (or method on an existing quality-gate module — pick what matches the TASK-FIX-3C9D shape) locates `_assumptions.yaml` files and extracts unconfirmed low-confidence rows.
  - Landed: `guardkit/orchestrator/quality_gates/assumption_confidence_checker.py` (free function `check_unconfirmed_low_confidence_assumptions`).
  - Shape matches the TASK-FIX-RWOP1.3.1 R5 precedent — producer writes a block into `task_work_results.json`, Coach reads it.
- [x] `coach_validator.py` reads the field and emits a warning (not a failure) in the Coach decision record.
  - Landed: new `_check_unconfirmed_assumptions` soft-gate method, same pattern as `_check_seam_test_recommendation` / `_check_bdd_results`. Appended to `all_issues` at the approval path (line ~973) — Coach still approves the turn; warning rides along with `severity: "warning"` and `category: "unconfirmed_low_confidence_assumptions"`.
- [x] One end-to-end test covers both the warning-emitted and warning-empty branches.
  - Landed: `tests/integration/autobuild/test_assumption_confidence_gate.py` mirrors `test_agent_invocations_gate.py`. Six tests cover: unconfirmed row flagged, all-confirmed empty, no features/ dir, Coach warning-on-approval path, Coach ok → no warning, Coach checker_error → no warning. All pass.
- [x] Post-execution rerun of the runner-without-producer grep for `feature-spec.md` per the parent review's method; the Phase 5 Coach gating claim is no longer runner-without-producer.
  - Grep of `coach_validator.py` for `_assumptions.yaml` now returns line 4018 (the warning description string inside `_check_unconfirmed_assumptions`). Producer side: `agent_invoker.py` lines 5835-5840 import and call the checker.
- [x] `installer/core/commands/feature-spec.md:337` prose is left as-is (the WIRE decision validates the existing claim; no rewrite needed).
  - No edits to `feature-spec.md`.
- [x] No existing tests regress.
  - `tests/integration/autobuild/test_agent_invocations_gate.py` (R5 precedent): 7/7 pass.
  - `tests/integration/autobuild/test_assumption_confidence_gate.py` (new): 6/6 pass.
  - `tests/unit/test_agent_invoker.py::TestWriteTaskWorkResults` (producer unit tests): 22/22 pass.
  - 50 pre-existing failures in `tests/integration/quality_gates/` and one in `test_agent_invoker.py::TestInvokeTaskWorkImplement` reproduce on `main` without this branch's changes (verified via `git stash`) — unrelated to this task.

## Implementation Notes

- **Reference shape**: [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md) — same failure class, adapted for Phase 5 assumptions rather than Phase 3 ACs. Read the producer → writer → Coach-read chain there before planning this.
- **Warn vs block mechanism**: follow whatever convention already exists in `coach_validator.py` for warning-level findings. If the file only supports pass/fail today, add a `warnings: []` list alongside the existing decision — don't overload the existing fail path.
- **Fixture workspace**: minimum viable fixture is two YAML rows — one `confidence: low` unconfirmed, one `confidence: low` with `human_response: confirmed`. The test asserts only the first is flagged.
- **Discovery glob**: `features/**/_assumptions.yaml`. Absolute vs relative path — match the Coach's existing working-directory assumption (the worktree root under `.guardkit/worktrees/TASK-XXX/`).
- **Do NOT block TASK-COH-RUN1** on this task. Medium severity, cohort-safe.

## Preconditions

- **Commit the RWOP1 sweep first.** The working tree on `main` currently carries uncommitted RWOP1.1 BDD-linking wiring, RWOP1.2 BDD-oracle+smoke-gates nudges, FEAT-RWOP1 implementation guide, the `feat-rwop1-orphan-cleanup/` subfolder, and the TASK-FIX-RWOP1.4 decision doc. Commit that sweep before starting this sub-task so the 1.4a diff is contained.
- No dependency on TASK-FIX-RWOP1.4b — 1.4a and 1.4b are independent and can run in parallel Conductor workspaces.

## Related

- Decision doc: [.claude/reviews/TASK-FIX-RWOP1.4-decisions.md](../../../.claude/reviews/TASK-FIX-RWOP1.4-decisions.md) §Part A
- Parent task: [TASK-FIX-RWOP1.4](TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md)
- Parent review: [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Per-file findings (feature-spec.md)
- R1 precedent: [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Feature guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) §Track B
