---
id: TASK-FIX-ARCH
title: "Fix: Architectural review score not written to task_work_results.json"
status: completed
created: 2026-01-23T16:00:00Z
updated: 2026-01-23T18:15:00Z
completed: 2026-01-23T18:15:00Z
priority: high
tags: [bug-fix, feature-build, quality-gates, autobuild, coach-validator]
task_type: bug_fix
complexity: 4
parent_review: TASK-REV-FBVAL
depends_on: []
previous_state: in_review
state_transition_reason: "Task completed - all quality gates passed, implementation verified"
completed_location: tasks/completed/TASK-FIX-ARCH/
---

# Fix: Architectural review score not written to task_work_results.json

## Problem Statement

During feature-build execution, the Coach validator reads `code_review.score` from `task_work_results.json` but this field is never populated. The Coach defaults to 0, causing all tasks with `arch_review_required=True` to fail.

**Evidence from logs:**
```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete:
  tests=True (required=True), coverage=True (required=True),
  arch=False (required=True), audit=True (required=True), ALL_PASSED=False
```

3 of 4 gates pass. Only arch review fails because score defaults to 0.

**Root cause hypothesis:**
1. Phase 2.5 (Architectural Review) may not be running during `--implement-only`
2. The review runs but score isn't written to the results JSON
3. The field name may be different than expected (`code_review.score`)

## Acceptance Criteria

- [x] Identify where architectural review is triggered during task-work
- [x] Trace the data flow from review execution to task_work_results.json
- [x] Verify the score field name matches what coach_validator expects
- [x] Fix the data flow so score is properly written
- [x] Add test coverage for the score writing path
- [x] Verify fix with a test run showing `arch=True` in quality gate evaluation

## Investigation Points

1. **agent_invoker.py** - How is task-work invoked? Does it include Phase 2.5?
2. **task-work command** - Does `--implement-only` skip Phase 2.5?
3. **architectural-reviewer agent** - Where does it write its score?
4. **task_work_results.json writer** - What fields are captured?
5. **coach_validator.py:576** - What field name does it expect?

## Technical Context

**Coach expectation (coach_validator.py:576):**
```python
code_review = task_work_results.get("code_review", {})
arch_score = code_review.get("score", 0)  # Default to 0 if not present
```

**Expected structure:**
```json
{
  "code_review": {
    "score": 72,
    "threshold": 60,
    "passed": true
  }
}
```

## Files to Investigate

- `src/guardkit/orchestrator/agent_invoker.py`
- `src/guardkit/orchestrator/quality_gates/coach_validator.py`
- `installer/core/commands/task-work.md` (Phase 2.5 section)
- Any code that writes to `task_work_results.json`

## Success Metrics

- `code_review.score` field populated in task_work_results.json after task-work
- Coach validator shows `arch=True` or `arch=False` based on actual score vs threshold
- No more "Architectural review score below threshold" when threshold is met

## Implementation Summary

### Root Cause
`TaskWorkStreamParser` class was missing regex patterns to extract architectural review scores from task-work output stream. The parser had patterns for tests, coverage, and file changes, but not for architectural review scores.

### Solution
Added parsing support to `TaskWorkStreamParser` in `guardkit/orchestrator/agent_invoker.py`:

1. **Pattern Constants** (lines 174-176):
   - `ARCH_SCORE_PATTERN`: Matches "Architectural Score: 82/100" or "Architectural score: 82"
   - `ARCH_SUBSCORES_PATTERN`: Matches "SOLID: 85, DRY: 80, YAGNI: 82"

2. **State Variables** (lines 187-190):
   - `_arch_score`, `_solid_score`, `_dry_score`, `_yagni_score`

3. **Parsing Logic** (lines 288-305):
   - Extracts scores with try/except error handling
   - Logs debug info for successful extraction
   - Logs warnings for invalid formats

4. **Result Building** (lines 343-351):
   - Builds `architectural_review` dict with score and optional subscores

5. **Data Flow Mapping** (lines 2388-2426 in `_write_task_work_results`):
   - Maps `architectural_review` → `code_review` for Coach compatibility

### Test Coverage
Added 8 new tests to `TestTaskWorkStreamParser`:
- Score parsing with/without /100 suffix
- Subscores parsing with/without commas
- Combined score + subscores
- Case insensitive matching
- No score found (returns empty)
- Reset clears state

### Verification
- 286 tests pass (73 coach_validator + 8 new + 205 agent_invoker)
- Phase 5 Code Review: APPROVED
- Phase 5.5 Plan Audit: APPROVED (zero scope creep)

## Notes

This is a data flow bug, not a design issue. The infrastructure works - we just need to connect the architectural review output to the Coach's input.
