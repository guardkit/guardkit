---
id: TASK-SFT-005
title: "Seam tests S8 \u2014 Quality gate to state transition wiring"
task_type: testing
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-SFT-001
priority: high
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:22:24.042331'
  last_updated: '2026-02-15T21:27:32.405755'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:22:24.042331'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Seam Tests S8: Quality Gates → State Transitions

## Objective

Write seam tests verifying that quality gate decisions actually block or allow task state transitions — catching cases where tasks move to IN_REVIEW with 0% criteria checked.

## Seam Definition

**Layer A**: Quality gate evaluation (`QualityGateProfile`, `CoachValidator` decisions)
**Layer B**: Task state management (state file writes, frontmatter updates)

## Acceptance Criteria

- [ ] `tests/seam/test_quality_gate_state.py` created
- [ ] Test: Task with failing tests cannot transition from IN_PROGRESS to IN_REVIEW
- [ ] Test: Task with zero tests and `zero_test_blocking=True` is blocked
- [ ] Test: DOCUMENTATION task type with zero tests is NOT blocked (exempt)
- [ ] Test: Coverage below threshold prevents completion for FEATURE type
- [ ] Test: Architectural review score below 60 triggers checkpoint for FEATURE type
- [ ] Tests create real task files on disk and verify state transitions
- [ ] All tests pass with `pytest tests/seam/test_quality_gate_state.py -v`

## Implementation Notes

- Use `tmp_task_dir` fixture from conftest
- Create actual task markdown files with frontmatter
- Verify state changes by re-reading the task file after attempted transition
- Reference `guardkit/models/task_types.py` for `QualityGateProfile` definitions
