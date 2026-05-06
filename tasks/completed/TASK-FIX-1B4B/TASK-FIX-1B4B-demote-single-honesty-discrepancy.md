---
id: TASK-FIX-1B4B
title: "Layer 2: Demote single path-only honesty discrepancies from must_fix to should_fix"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
completed: 2026-05-06T00:00:00Z
completed_location: tasks/completed/TASK-FIX-1B4B/
previous_state: in_review
state_transition_reason: "Task completed via /task-complete"
priority: high
task_type: implementation
tags: [autobuild, coach, honesty-verification, short-circuit, layer-2, robustness]
parent_review: TASK-REV-1B452
feature_id: FEAT-1B452
implementation_mode: task-work
wave: 2
conductor_workspace: honesty-fix-wave2-1
complexity: 3
depends_on:
  - TASK-FIX-1B4A
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-06T00:00:00Z
  new_tests: 5
  full_suite_passed: 267
  related_suites_passed: 51
---

# Task: Layer 2 — Don't short-circuit gate evaluation on a single path-only honesty discrepancy

## Description

Make the deterministic Coach's honesty gate **proportional**: a single `file_existence` discrepancy (the residual case after Layers 1 + 3' filter the load-bearing one) should be a `should_fix` issue that surfaces in feedback, not a `must_fix` short-circuit that drops 16 ACs.

This is Layer 2 of three from the [v2 review](../../../.claude/reviews/TASK-REV-1B452-review-report.md). Robustness improvement — not load-bearing — but closes a residual class of false-fail where neither Layer 1 nor Layer 3' catches an edge case.

## Context

**Current behaviour** ([`coach_validator.py:850-872`](../../../guardkit/orchestrator/quality_gates/coach_validator.py)):

```python
honesty_issues = self._honesty_issues_from(honesty_verification)
if honesty_issues:
    # ANY honesty issue → must_fix → short-circuit → 16 ACs dropped
    return CoachValidationResult(decision="feedback", ...)
```

`_honesty_issues_from` (line 5078-5107) marks **every** `severity=="critical"` discrepancy as `must_fix`. There is no proportionality — one discrepancy is treated identically to ten.

**Desired behaviour**: a single `file_existence` discrepancy is a `should_fix` issue that proceeds to gate evaluation. The discrepancy still surfaces in feedback so the Player can correct on the next turn. Multiple discrepancies, `promise_file_existence` discrepancies (FEAT-6CC5 sophisticated lie), and content-claim discrepancies (`test_result`, `test_count`) retain `must_fix` and short-circuit.

## Acceptance Criteria

- [ ] **AC-B1**: A Player report with **one** `file_existence` discrepancy (e.g. residual case where Layer 1 resolution failed and Layer 3' didn't filter) results in a `should_fix` issue and **does not short-circuit**. `CoachValidator.validate` proceeds through `run_independent_tests` and AC verification. The honesty issue is included in the result's `issues` list as `should_fix` so the Player sees it in feedback.
- [ ] **AC-B2**: A Player report with **two or more** `file_existence` discrepancies retains `must_fix` short-circuit (current behaviour; pattern not accident).
- [ ] **AC-B3**: A Player report with **any** `promise_file_existence` discrepancy (FEAT-6CC5 sophisticated-lie case) retains `must_fix` short-circuit (current behaviour preserved).
- [ ] **AC-B4**: A Player report with `test_result` or `test_count` discrepancy retains `must_fix` short-circuit (content claims remain blocking).
- [ ] **AC-B5**: The `CoachValidationResult.issues` schema's `severity` enum permits `should_fix`. Downstream consumers (autobuild loop classifier at `autobuild.py`, stall sub-typer) treat `should_fix` honesty issues as advisory — they do NOT increment failure counters or trigger early-stall classification.
- [ ] **AC-B6**: New tests in `tests/unit/test_coach_validator.py`:
  - `test_single_file_existence_discrepancy_demoted_should_fix` — one discrepancy, AC verification runs.
  - `test_multiple_file_existence_discrepancies_short_circuit` — two discrepancies, short-circuit fires.
  - `test_promise_file_existence_short_circuit_preserved` — FEAT-6CC5 case still rejects.
  - `test_test_result_discrepancy_short_circuit_preserved` — content claim still blocks.
  - `test_should_fix_honesty_issue_appears_in_feedback` — the demoted issue is visible in `result.issues`.
- [ ] **AC-B7**: Existing tests in `tests/unit/test_coach_validator.py` (full suite) pass with no regression.
- [ ] **AC-B8**: Stall classifiers in `autobuild.py` (search for `category == "honesty"` consumers) handle `should_fix` honesty issues without crashing or false-classifying. If a consumer was implicitly relying on `severity=="must_fix"` for category=="honesty", update it to be explicit.

## Implementation Notes

**Files to modify**:

1. `guardkit/orchestrator/quality_gates/coach_validator.py` (~30 lines):
   - Refactor `_honesty_issues_from(honesty: HonestyVerification) -> List[Dict]`:
     ```python
     def _honesty_issues_from(self, honesty: HonestyVerification) -> List[Dict[str, Any]]:
         issues: List[Dict[str, Any]] = []
         critical = [d for d in honesty.discrepancies if d.severity == "critical"]
         file_existence_only = all(d.claim_type == "file_existence" for d in critical)
         single_discrepancy = len(critical) == 1
         demote = file_existence_only and single_discrepancy
         for d in critical:
             severity = "should_fix" if demote else "must_fix"
             issues.append({"severity": severity, "category": "honesty", ...})
         return issues
     ```
   - Update the short-circuit guard at line 852:
     ```python
     # Only short-circuit when at least one issue is must_fix.
     must_fix_issues = [i for i in honesty_issues if i["severity"] == "must_fix"]
     if must_fix_issues:
         # ... existing return-early ...
     # Otherwise fall through; should_fix issues will be appended to the
     # result's issues list later, alongside whatever the gates produce.
     ```
   - Thread `should_fix` honesty issues into the final `CoachValidationResult.issues` (so they show up in Player feedback even though they didn't short-circuit). Add to the result-construction site at the end of `validate()`.

2. `tests/unit/test_coach_validator.py` (~150 lines added):
   - 5 new tests per AC-B6.

3. (potential) `guardkit/orchestrator/autobuild.py` — if any stall classifier filter on `severity=="must_fix" AND category=="honesty"`, ensure it still works correctly with the new `should_fix` variant. **Spike step 1 of implementation**: grep for these consumers and confirm AC-B8 holds.

## Notes

- **Depends on TASK-FIX-1B4A** because the regression test fixtures need to align with Layer 1's resolution semantics. If a discrepancy survives Layer 1 (genuine missing file or state_bridge unavailable), Layer 2 demotes it. Tests must exercise both paths consistently.
- This task is NOT load-bearing for next autobuild attempt — Layers 1 + 3' close the FFC3 reproducer alone. Layer 2 is the third line of defence for residual cases not covered by 1 + 3'.
- Risk assessment in v2 review report §AC-8 "Layer 2 risk: weakening adversarial property" with three mitigations.
