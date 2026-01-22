---
id: TASK-FBSDK-019
title: Persist Phase 2.5B results for implement-only mode
status: completed
created: 2025-01-21T16:30:00Z
updated: 2026-01-22T12:15:00Z
completed: 2026-01-22T12:20:00Z
priority: high
tags: [autobuild, quality-gates, bug-fix, phase-2-5b]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 1
conductor_workspace: arch-score-fix-wave1-2
complexity: 4
depends_on: []
previous_state: in_review
state_transition_reason: "Human approved completion after quality gates passed"
completed_location: tasks/completed/TASK-FBSDK-019/
organized_files:
  - TASK-FBSDK-019.md
  - test-results.md
quality_gates:
  compilation: passed
  tests_passing: true (21/21)
  line_coverage: 100%
  branch_coverage: 100%
  architectural_review: 82/100 (approved)
  plan_audit: approved (low severity)
acceptance_criteria_met: true
implementation_summary:
  files_modified: 2
  lines_added: 137
  tests_added: 21
  pattern_used: Cache-Aside
  duration: ~3 minutes (auto-execution)
---

# Task: Persist Phase 2.5B results for implement-only mode

## Description

When AutoBuild uses `task-work --implement-only`, Phase 2.5B (Architectural Review) is skipped because it's part of the design phases (2-2.8). The architectural review score generated during pre-loop needs to be persisted and accessible during the implementation loop.

## Problem

**Current behavior**:
1. Pre-loop runs `task-work --design-only` → Phase 2.5B generates score → Score not persisted
2. Loop runs `task-work --implement-only` → Phases 3-5.5 only → No Phase 2.5B
3. Coach reads `task_work_results.json` → No score available → Defaults to 0

**Expected behavior**:
- Phase 2.5B results should be stored in a persistent location
- When `--implement-only` runs, it should read and include the pre-loop scores

## Acceptance Criteria

- [ ] Phase 2.5B results stored in `.guardkit/autobuild/{task_id}/design_results.json`
- [ ] `--implement-only` reads design results if available
- [ ] Architectural review score from design phase included in `task_work_results.json`
- [ ] Works correctly when pre-loop is disabled (graceful handling)
- [ ] Unit tests verify persistence and retrieval

## Implementation Notes

### Design Results File

Create new artifact at `.guardkit/autobuild/{task_id}/design_results.json`:

```json
{
  "task_id": "TASK-XXX",
  "design_phase_completed": true,
  "timestamp": "2025-01-21T16:00:00Z",
  "architectural_review": {
    "score": 75,
    "solid_score": 8,
    "dry_score": 9,
    "yagni_score": 8
  },
  "complexity_score": 5,
  "plan_approved": true
}
```

### Files to Modify

1. `guardkit/orchestrator/agent_invoker.py`
   - Add `_write_design_results()` method
   - Modify `_write_task_work_results()` to read design results

2. `guardkit/orchestrator/paths.py`
   - Add `DESIGN_RESULTS = ".guardkit/autobuild/{task_id}/design_results.json"`
   - Add `design_results_path()` method

3. `guardkit/tasks/state_bridge.py`
   - Store design results when transitioning to `design_approved`

### Edge Cases

1. **Pre-loop disabled**: No design results file exists
   - Handle gracefully: Skip reading, proceed with implement-only defaults

2. **Pre-loop failed**: Design results incomplete
   - Check `design_phase_completed: true` before using values

3. **Resume scenario**: Design results already exist
   - Don't overwrite, use existing values

## Related Files

- `guardkit/orchestrator/autobuild.py` (orchestration flow)
- `guardkit/tasks/state_bridge.py:150-156` (creates stub implementation plan)
- `tests/unit/test_state_bridge.py`

## Notes

This task is parallel with TASK-FBSDK-018 but addresses the persistence layer while 018 addresses the writing format. Together they ensure the Coach receives valid architectural review scores.
