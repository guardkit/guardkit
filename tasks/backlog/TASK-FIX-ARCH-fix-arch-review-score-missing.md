---
id: TASK-FIX-ARCH
title: "Fix: Architectural review score not written to task_work_results.json"
status: backlog
created: 2026-01-23T16:00:00Z
updated: 2026-01-23T16:00:00Z
priority: high
tags: [bug-fix, feature-build, quality-gates, autobuild, coach-validator]
task_type: bug_fix
complexity: 4
parent_review: TASK-REV-FBVAL
depends_on: []
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

- [ ] Identify where architectural review is triggered during task-work
- [ ] Trace the data flow from review execution to task_work_results.json
- [ ] Verify the score field name matches what coach_validator expects
- [ ] Fix the data flow so score is properly written
- [ ] Add test coverage for the score writing path
- [ ] Verify fix with a test run showing `arch=True` in quality gate evaluation

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

## Notes

This is a data flow bug, not a design issue. The infrastructure works - we just need to connect the architectural review output to the Coach's input.
