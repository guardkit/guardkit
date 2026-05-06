---
id: TASK-FIX-7E3F
title: "Fix _record_honesty AttributeError + restore honesty observability (regression from b9a45694)"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T19:45:00Z
completed: 2026-05-06T19:45:00Z
previous_state: in_review
state_transition_reason: "All 14 ACs satisfied; 261/261 tests pass; code review 91/100; plan audit 0 violations"
completed_location: tasks/completed/TASK-FIX-7E3F/
organized_files:
  - TASK-FIX-7E3F-record-honesty-none-payload-regression.md
priority: critical
severity: release_blocking
task_type: bug-fix
parent_review: TASK-REV-7E3F1
tags: [autobuild, coach, honesty-verification, orchestrator-crash, regression, b9a45694, ffc3-bug-2]
complexity: 4
estimated_minutes: 45
implementation_mode: task-work
test_results:
  status: passed
  coverage: "touched code paths fully covered by 16 new tests (Layer B guard + producer threading)"
  last_run: 2026-05-06T19:30:00Z
  new_tests: 16
  existing_tests_pass: 245
  total_tests_in_targeted_suite: 261
---

# Task: Fix `_record_honesty` AttributeError + restore honesty observability

## Summary

Same-day regression introduced today (2026-05-06) by commit `b9a45694`
(TASK-AB-FIX-INVAB1). Every deterministic-Coach turn now emits
`"honesty_verification": None` in the report dict, and
`_record_honesty()` at [autobuild.py:4376](guardkit/orchestrator/autobuild.py#L4376)
crashes with `AttributeError: 'NoneType' object has no attribute 'get'`.

This is **release-blocking**. FEAT-FFC3 Wave 4 turn 2 was the first observed,
but every concurrent feature build using the deterministic Coach is affected
(deterministic Coach has been the primary path since 2025-12-30).

Ship Layer B (consumer guard) and Layer C (producer threading) **in a single
PR** today. Layer B alone restores correctness but silently undoes
TASK-AB-FIX-INVAB1's observability gains; Layer C alone leaves consumer
brittle to legitimate-None paths.

## Context

- **Parent review**: [TASK-REV-7E3F1](../backlog/TASK-REV-7E3F1-record-honesty-attributeerror-on-none-payload.md)
- **Review report**: [.claude/reviews/TASK-REV-7E3F1-review-report.md](../../.claude/reviews/TASK-REV-7E3F1-review-report.md)
  — includes C4 component diagram, three sequence diagrams (failing path,
  LLM Coach safe path, pre-regression baseline), full constructor enumeration.
- **Regression commit**: `b9a45694` (TASK-AB-FIX-INVAB1, today 2026-05-06 16:45 BST)
- **Sibling bug**: [TASK-REV-1B452](../backlog/TASK-REV-1B452-honesty-verification-false-fail-after-state-bridge-move.md)
  / [honesty-state-bridge-fix/](../backlog/honesty-state-bridge-fix/) — orthogonal
  fix area; can develop in parallel.
- **Possible duplicate review task**: `TASK-REV-FFC4-record-honesty-nonetype-crash.md`
  exists in backlog covering the same incident. Flag for human triage —
  consolidate or close before this implementation lands.

## Acceptance Criteria

### Layer B — Consumer-side guard (CRITICAL)

- [ ] **AC-1**: Modify
  [`_record_honesty`](guardkit/orchestrator/autobuild.py#L4355-L4396) to
  early-return when `honesty_data is None`. Drop the misleading `, {}`
  default from the `.get()` call (it never fires for the bug case).
  Log at debug level: `f"Turn {turn}: no honesty payload to record"`.

  **Code shape**:
  ```python
  honesty_data = turn_record.coach_result.report.get("honesty_verification")
  if honesty_data is None:
      logger.debug(
          f"Turn {turn_record.turn}: no honesty payload to record "
          f"(operator-handoff or pre-_verify_honesty short-circuit)"
      )
      return
  honesty_score = honesty_data.get("honesty_score", 1.0)
  ```

### Layer C — Producer-side threading (REQUIRED to restore TASK-AB-FIX-INVAB1 observability)

- [ ] **AC-2**: Widen `_feedback_result(...)` signature at
  [coach_validator.py:5109](guardkit/orchestrator/quality_gates/coach_validator.py#L5109)
  to accept `honesty_verification: Optional[HonestyVerification] = None`.
  Pass it to the constructor at line 5146.

- [ ] **AC-3**: Widen `_feedback_from_gates(...)` signature at
  [coach_validator.py:5159](guardkit/orchestrator/quality_gates/coach_validator.py#L5159)
  to accept `honesty_verification: Optional[HonestyVerification] = None`.
  Pass it to the constructor at line 5307.

- [ ] **AC-4**: Update six post-`_verify_honesty` callers to pass
  `honesty_verification=honesty_verification`:
  - Line 1043 (`_feedback_from_gates` — quality gates failed)
  - Line 1314 (`_feedback_result` — independent test verification failed)
  - Line 1336 (`_feedback_result` — requirements not met)
  - Line 1363 (`_feedback_result` — zero-test anomaly)
  - Line 1409 (`_feedback_result` — BDD scenarios failed)
  - Line 1437 (`_feedback_result` — seam tests missing)

- [ ] **AC-5**: Update the approve-path direct constructor at
  [coach_validator.py:1493](guardkit/orchestrator/quality_gates/coach_validator.py#L1493)
  to pass `honesty_verification=honesty_verification`.

- [ ] **AC-6**: Add a one-line comment at lines 765, 794, 817 documenting
  that `None` is correct at those sites because `_verify_honesty` has not
  yet been called. No behavioural change.

### Tests

- [ ] **AC-7**: Create `tests/unit/orchestrator/test_record_honesty.py` with
  class `TestRecordHonestyConsumerGuard` covering:
  - `test_handles_none_payload_without_crash` (key present, value None — the
    regression case)
  - `test_handles_missing_key_for_legacy_compat` (key absent — pre-regression
    shape)
  - `test_records_score_when_payload_populated` (happy path with dict)
  - `test_short_circuits_when_coach_failed` (existing line-4372 guard preserved)

- [ ] **AC-8**: In the same module, add class
  `TestCoachValidatorProducerThreading` parametrised over the seven
  decision shapes that should now thread `honesty_verification`:
  `feedback_from_gates`, `feedback_test_failure`, `feedback_missing_req`,
  `feedback_zero_test`, `feedback_bdd_failed`, `feedback_seam_missing`,
  `approve`. For each: drive `validator.validate(...)` to that branch and
  assert `result.to_dict()["honesty_verification"]` is not None and has the
  expected shape (`verified`, `honesty_score`, `discrepancy_count`).
  Also add `test_pre_verify_honesty_paths_legitimately_None` for sites
  765/794/817 — assert None is correct and consumer guard handles it.

- [ ] **AC-9** (gating regression test): Create
  `tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py`
  with `test_validate_to_dict_record_honesty_does_not_crash` that exercises
  the full producer→consumer integration path:
  1. Drive `CoachValidator.validate()` to a feedback decision (e.g.
     quality gates failed).
  2. Convert via `to_dict()` and build an `AgentInvocationResult` with
     `success=True`.
  3. Wrap in a `TurnRecord` and call `_record_honesty(turn_record)`.
  4. Assert no exception.
  5. Assert `_honesty_history` was updated with a real score (post-Layer-C).
  This is **the gate that would have caught the b9a45694 regression**.

### Quality gates

- [ ] **AC-10**: All existing tests in
  `tests/unit/test_autobuild_orchestrator.py` continue to pass.
- [ ] **AC-11**: All existing tests in
  `tests/unit/orchestrator/quality_gates/test_coach_validator*.py` continue
  to pass.
- [ ] **AC-12**: All existing tests in
  `tests/integration/orchestrator/test_coach_honesty_restoration.py`
  (added by TASK-AB-FIX-INVAB1) continue to pass.
- [ ] **AC-13**: `pytest tests/ -v --cov=guardkit/orchestrator --cov-report=term`
  passes with coverage >= 80% on lines touched.

### Manual smoke test

- [ ] **AC-14**: Re-run any task currently in-flight on the deterministic
  Coach path (e.g. a fresh `/task-work` invocation against a small task) and
  confirm `_record_honesty` does not crash and that
  `_honesty_history` updates as expected. Capture turn artefacts in
  `.guardkit/autobuild/{task_id}/coach_turn_*.json` showing
  `honesty_verification` populated as a dict, not null.

## Implementation Notes

### Why one PR (and not two)

The review's revision-2 analysis showed that shipping Layer B alone would
silently undo TASK-AB-FIX-INVAB1's observability gains: `_honesty_history`
would never grow on the deterministic-Coach primary path, and the "Player
honesty concern" warning at [autobuild.py:4384](guardkit/orchestrator/autobuild.py#L4384)
would never fire. Layer C alone leaves the consumer brittle to
legitimate-None paths (operator-handoff, pre-`_verify_honesty`
short-circuits). Both required for completeness.

### Out of scope (file separately if wanted)

1. **TypedDict / pydantic schema for the Coach report**. Would catch this
   class at static-check time. File as TASK-FUTURE.
2. **Test-rule under `tests/rules/`** asserting every
   `CoachValidationResult` field has a happy-path `to_dict()` round-trip
   test. Would have caught today's regression at PR time. File separately.
3. **Seeding of `optional-payload-discipline` rule** under
   `.claude/rules/`. Sibling of `absence-of-failure-is-not-success.md` and
   `namespace-hygiene.md`. File as a separate `/task-create` for rule
   seeding — do NOT bundle here.
4. **Consolidation of duplicate review tasks** TASK-REV-7E3F1 and
   TASK-REV-FFC4 (both filed today for this same bug). Human triage
   decision; out of scope here.

### Risk

- **Low** for Layer B: single function, local change, defensive guard.
- **Low-Medium** for Layer C: producer signature change, but
  `Optional[HonestyVerification] = None` default keeps every caller
  source-compatible.
- **Coordination with Bug 1 (TASK-REV-1B452)**: the sibling fix area is
  `_verify_files_exist` / `_verify_completion_promises_files_exist` /
  discrepancy-classification logic — disjoint from this task's fix area
  (helper signatures + caller updates). Fixes can develop in parallel and
  merge in either order. The only line of contact is the parametrised
  producer test in AC-8 — if Bug 1's implementation removes or renames the
  threaded short-circuit paths at lines 858/892, those test parameters
  need an update.

## Notes

- AutoBuild capable: yes (single task, well-bounded, complexity 4).
  Consider running on a worktree alongside the existing `honesty-state-bridge-fix`
  feature work for Bug 1 if both are progressing in parallel.
- Estimated complexity 4/10, ~30-45 min implementation + ~10 min testing.
- This task is the implementation arm of TASK-REV-7E3F1. After completion,
  run `/task-complete TASK-FIX-7E3F` and consider `/task-complete TASK-REV-7E3F1`
  to archive the review.
