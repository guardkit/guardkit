---
id: TASK-FIX-ASPF-001
title: Commit DMCP fixes (DMCP-001 through 004)
status: completed
completed: 2026-02-25T00:00:00Z
task_type: implementation
created: 2026-02-24T23:00:00Z
priority: critical
tags: [autobuild, direct-mode, criteria-pipeline, git]
complexity: 1
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-FIX-ASPF-001/
commit: 5c1aea32
---

# Task: Commit DMCP fixes (DMCP-001 through 004)

## Description

The four DMCP bug fixes (TASK-FIX-DMCP-001 through 004) are applied to the source files but remain unstaged in git. These fixes are confirmed correct, active at runtime (editable install), and introduce no regressions (6676 unit tests pass).

Commit these fixes to preserve them in version control.

## Files to Stage

- `guardkit/orchestrator/agent_invoker.py` — DMCP-001 (requirements_addressed copy), DMCP-003 (_synthetic propagation), DMCP-004 (TaskLoader parsing)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — DMCP-002 (text matching field name fix)
- `tests/unit/test_agent_invoker.py` — Unit tests for DMCP fixes

## Acceptance Criteria

1. All three files staged and committed with descriptive message
2. All unit tests still pass after commit
3. Commit message references TASK-FIX-DMCP-001 through 004

## Implementation

```bash
git add guardkit/orchestrator/agent_invoker.py \
        guardkit/orchestrator/quality_gates/coach_validator.py \
        tests/unit/test_agent_invoker.py

git commit -m "fix: commit DMCP-001 through 004 direct mode criteria pipeline fixes

- DMCP-001: Copy requirements_addressed to task_work_results.json
- DMCP-002: Fix Coach text matching to check requirements_addressed first
- DMCP-003: Propagate _synthetic flag in player report
- DMCP-004: Use TaskLoader for acceptance criteria loading

All fixes verified: 6676 unit tests pass, no regressions.

Refs: TASK-FIX-DMCP-001, TASK-FIX-DMCP-002, TASK-FIX-DMCP-003, TASK-FIX-DMCP-004
Parent review: TASK-REV-CECA"
```
