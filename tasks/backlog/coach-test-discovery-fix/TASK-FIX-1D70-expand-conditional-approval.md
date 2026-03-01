---
id: TASK-FIX-1D70
title: Expand conditional approval for collection errors with all gates passed
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: backlog
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T00:00:00+00:00
priority: high
tags:
  - autobuild
  - coach-validator
  - approval-logic
  - seam-fix
complexity: 3
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-FIX-DF44
---

# Task: Expand Conditional Approval for Collection Errors with All Gates Passed

## Description

The Coach's `conditional_approval` logic only covers one scenario: high-confidence infrastructure failures when Docker is unavailable and the task declares `requires_infrastructure`. It has no path for test collection errors where all quality gates passed — meaning the Player's tests ran successfully but the Coach's independent re-verification failed at collection time (not execution time).

This is Seam Failure 3 from the TASK-REV-0E44 review. This task adds a second approval path so that collection errors with all gates passed result in conditional approval (with warning) instead of feedback.

## Acceptance Criteria

- [ ] `conditional_approval` is True when `failure_class == "collection_error"` AND `gates_status.all_gates_passed == True`
- [ ] Existing infrastructure approval path is unchanged (no regression)
- [ ] Conditional approval for collection errors is logged at WARNING level with details
- [ ] Approval rationale includes "Conditionally approved — test collection errors in independent verification"
- [ ] When `failure_class == "collection_error"` but gates NOT all passed → feedback (not approved)
- [ ] `_build_approval_rationale()` handles `collection_error` conditional approval
- [ ] Unit tests cover: collection error + all gates → approval, collection error + failed gate → feedback, existing infra path unchanged

## Technical Context

- File: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `validate()` (lines 689-695 — conditional_approval check)
- Method: `_build_approval_rationale()` (lines 2830-2884)
- Depends on TASK-FIX-DF44 which adds the `"collection_error"` classification
- Current conditional_approval requires ALL of: infrastructure + high + requires_infra + !docker + all_gates
- New path requires: collection_error + all_gates (simpler — collection errors are always the Coach's test scope issue)

## Design Reference

- Review report: `.claude/reviews/TASK-REV-0E44-review-report.md` (Seam Failure 3, Fix 3)
- Evidence: Run log line 1473 — `confidence=ambiguous, requires_infra=[]` blocking approval despite all gates passing

## Expected Interface Format

The `conditional_approval` boolean is consumed by:
1. Line 697: `if conditional_approval:` → logs warning and continues to requirements check
2. Line 815: `if conditional_approval:` → modifies approval rationale
3. Line 830: Passed to `_build_approval_rationale(conditional_approval=True)`

All three consumers use it as a boolean flag — no changes needed to consumers.

## Regression Risks

1. Approving tasks where collection errors mask real failures → mitigated by requiring ALL gates to pass (Player's own tests must have passed)
2. Must not change behaviour for non-collection-error failures → add as OR branch to existing check
3. Test thoroughly with: collection_error + all gates, collection_error + failed gate, infrastructure path, code failure

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
