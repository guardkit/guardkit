# vLLM Run 5 Regression Fixes (FEAT-9db9)

## Summary

Fixes for AutoBuild Run 5 regression where TASK-FBP-007 failed with `timeout_budget_exhausted` after 8 turns. Root cause: budget starvation from serialized execution + infeasible acceptance criteria for vLLM backend.

## Tasks

| ID | Title | Priority | Wave | Status |
|----|-------|----------|------|--------|
| TASK-VRF-001 | Relax FBP-007 acceptance criteria | CRITICAL | 1 | backlog |
| TASK-VRF-002 | Separate FBP-007 into own wave | HIGH | 1 | completed |
| TASK-VRF-003 | Pass remaining_budget to Player | HIGH | 2 | backlog |
| TASK-VRF-004 | Backend-aware AC validation | HIGH | 3 | backlog |
| TASK-VRF-005 | Fix synthetic report corruption | MEDIUM | 4 | backlog |
| TASK-VRF-006 | Explore max_parallel=2 | LOW | 5 | backlog |
| TASK-VRF-007 | Correct task description | LOW | 1 | completed |

## Parent Review

TASK-REV-5E1F — [Review Report](../../.claude/reviews/TASK-REV-5E1F-review-report.md)
