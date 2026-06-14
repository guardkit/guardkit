---
id: TASK-AB-CKPTGATE01
title: Thread the deterministic Coach gate test signal into the LLM-Coach report (record real passes as pass, not unknown)
status: completed
task_type: fix
created: 2026-06-14T13:00:00Z
updated: 2026-06-14T14:30:00Z
completed: 2026-06-14T14:30:00Z
completed_location: tasks/completed/TASK-AB-CKPTGATE01/
previous_state: in_review
state_transition_reason: "Implementation complete; all quality gates passed (task-work)"
priority: medium
complexity: 5
related: [TASK-FIX-CKPTTESTRED01, TASK-HMIG-008R, TASK-AB-FIX-INVAB1]
implementation_mode: task-work
tags: [autobuild, checkpoints, coach, evidence-bundle, three-layer-reconciliation, rollback]
---

# Task: Thread the deterministic Coach gate signal into the LLM-Coach report

## Why this task exists

TASK-FIX-CKPTTESTRED01 (commit `c6b5e7d9`) closed the checkpoint false-red by
making the checkpoint test signal **tri-state** and treating an absent signal
as `UNKNOWN` (excluded from the consecutive-failure pollution tally). That
fully satisfied its acceptance criteria via the "or" branch (absent → unknown).

It deliberately left a **residual gap**, called out as a scope boundary in the
fix:

> The deterministic `tests=True` gate result is not *threaded* into the
> LLM-Coach report. So a turn whose tests genuinely passed (Coach gate
> `tests=True`) is recorded as `UNKNOWN` rather than `pass`, because the
> default LLM Coach's `coach_result.report` carries only
> `{decision, issues, criteria_verification, rationale}` and omits
> `validation_results.quality_gates`.

The contradiction (`checkpoint: fail` vs `gate: tests=True`) is resolved —
checkpoints now read `unknown`, never `fail`. But two things remain
sub-optimal:

1. **Lost rollback targets.** `find_last_passing_checkpoint` only treats
   `tests_passed is True` as a rollback target. Genuinely-passing turns
   recorded as `UNKNOWN` are not targets, so a later *real* pollution run can
   `unrecoverable_stall` with no target even though an earlier turn was clean.
2. **The 3-layer test-signal split is reconciled only negatively.**
   Remediation #3 of TASK-FIX-CKPTTESTRED01 ("the three layers must read one
   consistent test oracle") is only half-done: the layers no longer
   *contradict*, but the checkpoint layer still cannot *see* the authoritative
   `tests=True` the deterministic gate computed.

This task threads the authoritative gate signal from the Coach **evidence
bundle** into the returned `coach_result.report` so the checkpoint layer reads
the same oracle the gate logged.

## Background / where the signal lives

- `AutoBuildOrchestrator._invoke_coach_primary` (autobuild.py, ~5748) computes
  `evidence_bundle = validator.gather_evidence(...)` (~5812). The bundle
  (`guardkit/orchestrator/quality_gates/coach_evidence.py::CoachEvidenceBundle`)
  carries `quality_gates` (`QualityGateStatus.tests_passed`) and
  `independent_tests` (`IndependentTestResult.tests_passed` + `signal_absent`).
- The method then returns the LLM Coach's `result` directly (~6002). That
  `result.report` is the parsed LLM verdict — it does **not** include the
  bundle's gate result.
- `_extract_tests_passed` (autobuild.py, ~7364) already reads
  `validation_results.quality_gates.tests_passed` and
  `independent_tests.signal_absent` (tri-state, post-CKPTTESTRED01). It simply
  finds nothing in the LLM-Coach report and returns `None`.

## Remediation recipe

1. **Merge the bundle's test signal into `result.report` before returning**
   from `_invoke_coach_primary` (the normal success return at ~6002). Populate
   `result.report["validation_results"]["quality_gates"]["tests_passed"]` and
   `["independent_tests"]["signal_absent"]` from `evidence_bundle`, **only if
   not already present** (do not clobber a report that already carries them).
   - Do this via a small helper (e.g. `_merge_evidence_test_signal_into_report`)
     so the legacy path and any future substrate can share it.
   - The synthetic-feedback path (`_emit_synthetic_coach_feedback`) should
     remain absent → `UNKNOWN` (the Coach genuinely produced no verdict there).
2. **Preserve the absence-of-failure invariant.** When the bundle's
   `independent_tests.signal_absent` is `True`, the merged report must still
   resolve to `UNKNOWN` via `_extract_tests_passed` (do not let a stale
   `quality_gates.tests_passed=True` override an absent independent signal —
   `_extract_tests_passed` already checks `signal_absent` first; keep that
   ordering).
3. **Do not weaken any Coach invariant.** Coach stays read-only; this is an
   orchestrator-side enrichment of the returned report object, not a Coach
   write. No change to verdict emission (`coach_output_parser`).
4. **Confirm the checkpoint now records real passes as `pass`.** A turn whose
   deterministic gate is `tests=True` (and independent signal present/passed)
   must produce `Checkpoint.tests_passed is True` and be a valid
   `find_last_passing_checkpoint` target.

## Acceptance Criteria

- [x] In the primary (LLM-Coach) path, a turn whose deterministic gate is
      `tests=True` (independent signal present and passing) is recorded with
      `Checkpoint.tests_passed is True` (not `None`/`unknown`).
- [x] `find_last_passing_checkpoint` returns that turn as a rollback target.
- [x] An absent independent-test signal (`signal_absent=True`) still resolves
      to `UNKNOWN` (regression guard for TASK-FIX-CKPTTESTRED01 — absent is not
      a pass and not a fail).
- [x] A genuine ran-and-failed gate (`tests=False`) is still recorded as
      `False` and still contributes to the consecutive-failure pollution tally.
- [x] Coach read-only invariant preserved (no `Write`/`Edit`; no change to
      `coach_output_parser` verdict emission).
- [x] Regression test: an LLM-Coach turn with a populated evidence bundle
      (`quality_gates.tests_passed=True`) yields a checkpoint recorded as
      `pass`, reproducing the FEAT-9DDE run-5 turns now being correctly
      classified as passing rather than unknown.
- [x] No regression of the run-5 false-red fix (absent-signal turns still do
      not stall).

## Implementation Summary (2026-06-14)

**Change** (orchestrator-side enrichment only; Coach untouched):

- New helper `AutoBuildOrchestrator._merge_evidence_test_signal_into_report`
  (`guardkit/orchestrator/autobuild.py`) copies the evidence bundle's
  `quality_gates.tests_passed` and `independent_tests.signal_absent`
  (+ `tests_passed`) into `report["validation_results"]`, using `setdefault`
  so a report that already carries the signal is never clobbered.
- Wired into `_invoke_coach_primary` at the **normal success return only**
  (the `return result` after the COACHSF01 soft-fail check). All
  synthetic-feedback returns (`_emit_synthetic_coach_feedback`,
  `_evidence_repo_gate`, `_direct_mode_evidence_gate`, exception paths) are
  intentionally **not** enriched — the Coach produced no verdict there, so they
  stay absent → `UNKNOWN` per remediation #1.
- `_extract_tests_passed` was **not** changed: it already reads
  `independent_tests.signal_absent` before `quality_gates.tests_passed`, so the
  absence-of-failure ordering is preserved by construction.

**Tests**: `tests/unit/test_checkpoint_gate_signal_threading.py` (13 tests, all
passing) covering all 7 ACs: pass-threading + rollback-target restoration,
absent-signal → UNKNOWN regression guard, ran-and-failed still stalls,
non-clobber, None-guards, and verdict-field read-only.

**Verification**:
- New suite: 13 passed.
- Named regression suites (`test_checkpoint_pollution_absent_test_signal.py`,
  `test_checkpoint_extraction_and_ordering.py`, `test_null_quality_gates.py`):
  35 passed, 3 skipped.
- Coach-primary path (`test_llm_coach_primary.py`,
  `test_direct_mode_false_green_regression.py`): 39 passed.
- Pre-existing, unrelated: 4 BDD `test_coach_validator.py` failures fail
  identically on unmodified `autobuild.py` (different module; out of scope).

## Notes / risk

- Touches `_invoke_coach_primary` (both the normal and COACHSF01 soft-fail
  returns), the new merge helper, and possibly `AgentInvocationResult`/report
  shaping. Medium blast radius — gate behind the same signature/None-guards
  the existing code already uses for partial rollouts.
- Verify against `tests/unit/test_checkpoint_pollution_absent_test_signal.py`,
  `tests/unit/test_checkpoint_extraction_and_ordering.py`,
  `tests/unit/test_null_quality_gates.py`, and the coach-primary path tests.

## Evidence
- Parent fix + scope boundary: commit `c6b5e7d9`
  (`tasks/completed/TASK-FIX-CKPTTESTRED01/TASK-FIX-CKPTTESTRED01.md`,
  "Scope boundary" in the Implementation Summary).
- Signal source: `guardkit/orchestrator/quality_gates/coach_evidence.py`
  (`CoachEvidenceBundle.quality_gates` / `.independent_tests`).
- Consumer: `guardkit/orchestrator/autobuild.py::_extract_tests_passed`.
