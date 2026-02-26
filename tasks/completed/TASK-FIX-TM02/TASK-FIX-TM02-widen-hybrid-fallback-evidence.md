---
id: TASK-FIX-TM02
title: Widen _hybrid_fallback() upgrade condition for file-existence promises
status: completed
completed: 2026-02-25T13:30:00Z
task_type: implementation
created: 2026-02-25T12:00:00Z
priority: critical
tags: [autobuild, coach-validator, hybrid-fallback, bug-fix, P0]
complexity: 3
parent_review: TASK-REV-0828
feature_id: FEAT-TM-FIX
wave: 1
implementation_mode: task-work
dependencies: []
files_touched: [guardkit/orchestrator/quality_gates/coach_validator.py, tests/unit/test_run3_stall_fixes.py, tests/unit/test_coach_validator.py]
completed_location: tasks/completed/TASK-FIX-TM02/
---

# Task: Widen `_hybrid_fallback()` upgrade condition for file-existence promises

## Problem

`_hybrid_fallback()` in `coach_validator.py:2060-2063` only allows text-matching to override promise-based rejection when the evidence string contains `"No completion promise"`. File-existence promises produce evidence `"Promise status: incomplete"`, which does NOT match this condition.

This blocks Turn 4 (synthetic path) from upgrading criteria that were verified by text matching against actual file content (via `infer_requirements_from_files()`), because the promise evidence string doesn't match the upgrade condition.

**Current code**:
```python
elif (
    text_cr.result == "verified"
    and "No completion promise" in promise_cr.evidence
):
```

**Impact**: Turn 4 goes from 0/7 to 6/7 matched criteria when fixed.

## Solution

Widen the evidence check to also accept `"Promise status: incomplete"`:

```python
# AFTER
elif (
    text_cr.result == "verified"
    and promise_cr.result == "rejected"
    and (
        "No completion promise" in promise_cr.evidence
        or "Promise status: incomplete" in promise_cr.evidence
    )
):
```

### Why this is safe

1. `"No completion promise"` — Player wrote no promise at all → text override correct (original intent)
2. `"Promise status: incomplete"` from file-existence — Content criteria can't be verified by file path checks → text override using actual file content is more trustworthy
3. `"Promise status: incomplete"` from Player — Player may have said "incomplete" due to model limitations → text matching against actual code is more reliable signal

In ALL cases where promise says "rejected" but text matching says "verified" against actual codebase content, the text match is the better signal.

### Expected interface format

The evidence string patterns are produced by `_match_by_promises()` at these locations:
- `"No completion promise for {criterion_id}"` — coach_validator.py L1761-1767
- `"Promise status: {status}"` — coach_validator.py L1779-1781

## Acceptance Criteria

1. `_hybrid_fallback()` allows text-verified upgrade when evidence contains `"Promise status: incomplete"`
2. `_hybrid_fallback()` still allows text-verified upgrade when evidence contains `"No completion promise"` (existing behaviour preserved)
3. `_hybrid_fallback()` does NOT allow upgrade when promise was explicitly verified (no regression)
4. All existing coach_validator tests pass (376 tests)
5. New test covers file-existence promise → text upgrade path
6. New test confirms original "No completion promise" → text upgrade still works

## Architectural Invariants (MUST preserve)

- **INV-1**: `_match_by_promises()` is NOT modified — only the hybrid fallback logic changes
- **INV-2**: Hybrid fallback architecture (TASK-REV-E719) is STRENGTHENED, not weakened
- **INV-3**: Synthetic file-existence promises now correctly fall through to text matching

## Test Approach

```python
def test_hybrid_fallback_upgrades_file_existence_incomplete():
    """Verify file-existence incomplete promises allow text upgrade."""
    # promise: rejected with "Promise status: incomplete"
    # text: verified
    # expected: verified (text wins)

def test_hybrid_fallback_upgrades_no_completion_promise():
    """Verify original 'No completion promise' upgrade still works."""
    # promise: rejected with "No completion promise for AC-001"
    # text: verified
    # expected: verified (text wins)

def test_hybrid_fallback_does_not_upgrade_explicit_reject():
    """Verify explicit player rejection is NOT overridden by text."""
    # promise: rejected with "Player explicitly rejected"
    # text: verified
    # expected: rejected (promise wins — but this is a hypothetical case)
```

## Evidence

- Simulation: Turn 4 text matching finds 6/7 exact matches (from `infer_requirements_from_files` returning original AC text), but ALL blocked by evidence check
- Evidence taxonomy: `.claude/reviews/TASK-REV-0828-review-report.md` Appendix B
- Review: `.claude/reviews/TASK-REV-0828-review-report.md`
