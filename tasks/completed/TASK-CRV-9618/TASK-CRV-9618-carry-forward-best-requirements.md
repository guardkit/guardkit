---
id: TASK-CRV-9618
title: Carry forward best requirements_addressed across turns
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: medium
tags: [synthetic-report, requirements, state-tracking, reliability]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 2
implementation_mode: task-work
complexity: 3
dependencies: []
---

# Task: Carry forward best requirements_addressed across turns

## Description

The `requirements_addressed` inference in the synthetic report degrades over turns. In FEAT-2AAA, turn 1 inferred 2 requirements but subsequent turns inferred 0 — the best result was not carried forward. When the Player makes incremental changes, the content analysis finds fewer keyword matches than on the initial full implementation.

Add a "high water mark" mechanism that merges the current turn's `requirements_addressed` with the best previous results, with a staleness check to prevent false positives from earlier turns.

**Key concern**: If the Player significantly restructures files between turns, an inferred requirement from turn 1 might be a false positive by turn 6. The carry-forward must validate that the source file still exists and still contains the matching content before including a previous turn's requirement.

## Acceptance Criteria

- [ ] Autobuild turn loop tracks best `requirements_addressed` set across all turns for a task
- [ ] Each turn's synthetic report `requirements_addressed` is merged (union) with best previous
- [ ] **Staleness check**: Before carrying forward a previous requirement, verify that the file that produced the keyword match still exists and still contains the matching content in the worktree
- [ ] Stale requirements logged and dropped from carry-forward set
- [ ] Merged set passed to Coach validator instead of current-turn-only set
- [ ] High water mark reset when task changes (new task in wave)
- [ ] Log message when carry-forward adds criteria (e.g., "Carried forward 2 requirements from turn 1")
- [ ] Existing autobuild tests continue to pass
- [ ] New test verifying carry-forward behavior across turns
- [ ] New test verifying staleness check drops requirements when source file is deleted or modified

## Implementation Notes

In `autobuild.py` turn loop:

```python
# Track high water mark with staleness validation
best_requirements: Set[str] = set()

for turn in range(max_turns):
    # ... state recovery, synthetic report ...
    current_reqs = set(synthetic_report.get("requirements_addressed", []))

    # Staleness check: re-validate previous requirements against current worktree
    still_valid = set()
    for req in best_requirements:
        if _requirement_still_valid(req, worktree_path):
            still_valid.add(req)
        else:
            logger.debug("Dropping stale requirement: %s", req[:80])
    best_requirements = still_valid

    # Merge with best previous
    merged = best_requirements | current_reqs
    if merged - current_reqs:
        logger.info(
            "Carried forward %d requirements from previous turns",
            len(merged - current_reqs),
        )
    best_requirements = merged

    synthetic_report["requirements_addressed"] = list(merged)
    # ... Coach validation ...

def _requirement_still_valid(req_text: str, worktree_path: Path) -> bool:
    """Check if a previously-inferred requirement is still supported by worktree files.

    Re-runs keyword extraction against current file contents to avoid
    false positives from files that were deleted or significantly restructured.
    """
    # Reuse infer_requirements_from_files logic on current worktree state
    # ... implementation checks file existence and keyword match ...
```

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (turn loop — add high water mark tracking)
- `tests/unit/test_autobuild.py` (carry-forward test)
