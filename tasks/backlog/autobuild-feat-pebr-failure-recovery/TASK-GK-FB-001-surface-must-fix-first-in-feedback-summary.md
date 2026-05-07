---
id: TASK-GK-FB-001
title: Surface must_fix issues first in operator-visible feedback summary
status: backlog
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 00:00:00+00:00
priority: medium
priority_band: P2
task_type: refactor
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: task-work
wave: 2
complexity: 3
estimated_minutes: 60
dependencies:
  - TASK-GK-CR-001
tags:
  - autobuild
  - operator-experience
  - feedback-display
  - P2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Surface must_fix issues first in operator-visible feedback summary

## Description

The operator-visible turn summary at
[guardkit/orchestrator/autobuild.py:3127-3129](../../../guardkit/orchestrator/autobuild.py#L3127-L3129)
truncates the Coach's full feedback text to 80 characters:

```python
summary = (
    f"Feedback: {feedback_text[:80]}..."
    if len(feedback_text) > 80
    else f"Feedback: {feedback_text}"
)
```

Combined with the issue-list ordering at
[coach_validator.py:1058-1069](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1058-L1069)
— which **prepends** the `agent_invocations_advisory`
(severity=warning, non-blocking) ahead of all other issues — the
truncated summary always shows the non-blocking advisory and hides
any `must_fix` issue.

In the FEAT-PEBR run the live log showed:
*"Feedback: - Advisory (non-blocking): task-work produced a report
with 2 of 3 expected agen..."*

while the actual reason for `decision=feedback` was a
`must_fix`-severity plan-audit violation that never appeared in the
operator log. The Player still got the full feedback (per
`coach_feedback_for_turn_2.json:8`), but the operator could not see
what was actually broken.

## Acceptance Criteria

- [ ] AC-1: When the Coach feedback contains both a `warning`-severity
  advisory AND a `must_fix`-severity issue, the truncated operator
  summary shows the must_fix issue's description (not the advisory).
- [ ] AC-2: When the feedback contains only `warning`-severity issues
  (no must_fix), the summary shows the first warning's description
  (current behaviour preserved).
- [ ] AC-3: When the feedback contains multiple must_fix issues, the
  summary shows the highest-severity one; ties broken by the order
  they appear in the issues list.
- [ ] AC-4: Two implementation options — pick one based on smallest
  diff:
  - (a) Reverse the prepend at `coach_validator.py:1058-1069` so
    must_fix items appear first in the issues list, OR
  - (b) Change the summary builder at `autobuild.py:3127-3129` to
    extract the highest-severity issue's `description` from the
    Coach report directly rather than slicing the joined string.
- [ ] AC-5: Existing tests asserting the joined feedback text format
  (delivered to the Player) continue to pass — this change is for the
  operator log only.
- [ ] AC-6: A new test fixture replays the FEAT-PEBR turn-1 Coach
  output and asserts the operator summary contains
  `"Plan audit detected high-severity"` (not the advisory).
- [ ] AC-7: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test for AC-1, AC-2, AC-3 (severity-ordered selection).
- Unit test for AC-5 (Player-delivered feedback unchanged).
- Regression fixture for AC-6 using the captured FEAT-PEBR
  coach_turn_1.json.

## Implementation notes

### Files to Modify

- One of:
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (option a)
  - `guardkit/orchestrator/autobuild.py:3127-3129` (option b)
- `tests/orchestrator/test_autobuild.py` (or wherever the summary
  builder is tested)

### Recommended approach

Option (b) is preferred — it does not change what the Player sees,
only the operator-facing log. The summary builder reads
`coach_result.report.issues` directly:

```python
def _build_feedback_summary(self, coach_report: Dict[str, Any]) -> str:
    issues = coach_report.get("issues", [])
    severity_order = {"must_fix": 0, "should_fix": 1, "warning": 2}
    if issues:
        primary = min(
            issues,
            key=lambda i: severity_order.get(i.get("severity", "warning"), 99),
        )
        desc = primary.get("description", "")
        if len(desc) > 80:
            return f"Feedback: {desc[:80]}..."
        return f"Feedback: {desc}"
    # Fall back to current behaviour if no structured issues
    feedback_text = coach_report.get("feedback", "")
    return (
        f"Feedback: {feedback_text[:80]}..."
        if len(feedback_text) > 80
        else f"Feedback: {feedback_text}"
    )
```

### Dependency

This task lists TASK-GK-CR-001 as a dependency because the latter
touches `coach_validator.py` and we want to land that first to avoid
merge conflicts. If option (b) is picked (autobuild.py only), the
dependency is technically optional but kept for ordering hygiene.

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/orchestrator/test_autobuild.py -x -v -k feedback_summary
PYTHONPATH=. python -m pytest tests/quality_gates/test_coach_validator.py -x -v
ruff check guardkit/orchestrator/autobuild.py guardkit/orchestrator/quality_gates/coach_validator.py
```

## Out of scope

- Changing what the Player receives (delivered feedback is unchanged).
- The advisory-prepend itself (it's still useful in the full feedback;
  this task is about the truncated summary only).
