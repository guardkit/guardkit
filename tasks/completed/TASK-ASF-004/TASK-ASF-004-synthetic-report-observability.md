---
id: TASK-ASF-004
title: Add observability logging for synthetic recovery reports (R4-lite)
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 2
implementation_mode: task-work
complexity: 2
dependencies:
  - TASK-ASF-001
  - TASK-ASF-002
priority: medium
status: completed
updated: 2026-02-15T00:00:00Z
completed: 2026-02-15T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-ASF-004/
tags: [autobuild, stall-fix, R4-lite, phase-2, observability]
---

# Task: Add observability logging for synthetic recovery reports (R4-lite)

## Description

This is the **first phase** of a two-phase fix for synthetic recovery reports (R4). This phase adds logging and warnings when synthetic reports are used, without changing the report structure itself. This provides observability into the recovery path failure mode before the higher-risk structural changes in R4-full (TASK-ASF-006).

The diagnostic data flow diagram (Diagram 4) shows synthetic reports feed two separate consumers (`_match_by_promises()` and `_match_by_text()`). Changing the report structure is a medium-risk change. R4-lite gives us observability with zero risk.

## Root Cause Addressed

- **F2**: Synthetic recovery reports structurally cannot satisfy Coach criteria (`autobuild.py:2114-2136`)
- **New finding**: No fast-fail for synthetic reports — every timeout recovery creates a report that can never pass promise matching, yet Coach still runs full validation

## Implementation

```python
# autobuild.py — in _build_synthetic_report()
def _build_synthetic_report(self, work_state, task_id, turn):
    logger.warning(
        f"[Turn {turn}] Building synthetic recovery report for {task_id}. "
        f"This report has no completion_promises and cannot satisfy "
        f"promise-based criteria matching. Files detected: "
        f"{len(work_state.files_created)} created, "
        f"{len(work_state.files_modified)} modified, "
        f"Tests: {work_state.test_count}"
    )

    report = {
        "task_id": task_id,
        "_synthetic": True,  # Flag for downstream consumers
        "files_modified": work_state.files_modified,
        ...
    }
    return report
```

```python
# autobuild.py — in _loop_phase(), before Coach invocation
if player_report.get("_synthetic"):
    logger.warning(
        f"[Turn {turn}] Passing synthetic report to Coach. "
        f"Promise matching will fail — falling through to text matching."
    )
```

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` — Add `_synthetic: True` flag and logging in `_build_synthetic_report()` (~line 2114)
2. `guardkit/orchestrator/autobuild.py` — Add warning log before Coach invocation when report is synthetic (~line 1700)

## Acceptance Criteria

- [x] Synthetic reports include `_synthetic: True` flag
- [x] Warning logged when synthetic report is built (includes file/test counts)
- [x] Warning logged when synthetic report is passed to Coach
- [x] `_synthetic` flag does not affect Coach validation behavior (flag is informational only)
- [x] Existing tests pass without modification

## Regression Risk

**None** — This adds logging and an informational flag. No behavior changes. The `_synthetic` flag is not read by any existing code path.

## Future Work

R4-full (TASK-ASF-006) will use the `_synthetic` flag to implement fast-fail logic and file-existence promise generation. That work depends on R5 (scoped test detection) being in place first.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 2, Recommendation R4)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 4, Diagram 5)
