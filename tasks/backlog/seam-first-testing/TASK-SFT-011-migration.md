---
id: TASK-SFT-011
title: Migrate existing seam tests from integration/ to seam/
task_type: refactor
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 3
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-SFT-001
- TASK-SFT-003
priority: low
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:30:50.791832'
  last_updated: '2026-02-15T21:33:12.638678'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:30:50.791832'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Migrate Existing Seam Tests to tests/seam/

## Objective

Move the existing seam-style tests from `tests/integration/` to `tests/seam/` for consistency with the new testing strategy.

## Acceptance Criteria

- [ ] `tests/integration/test_system_plan_seams.py` moved to `tests/seam/test_system_plan_seams.py`
- [ ] `tests/integration/test_planning_module_seams.py` moved to `tests/seam/test_planning_module_seams.py`
- [ ] All imports updated to reflect new location
- [ ] All tests still pass from new location: `pytest tests/seam/ -v`
- [ ] No broken imports in other test files that may have referenced the moved files
- [ ] `tests/integration/` retains its non-seam integration tests

## Implementation Notes

- Use `git mv` for the move to preserve history
- Check for any cross-references or imports between test files
- Run full test suite after migration to verify no regressions
