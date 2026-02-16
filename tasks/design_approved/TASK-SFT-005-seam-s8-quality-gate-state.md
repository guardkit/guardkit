---
complexity: 4
dependencies:
- TASK-SFT-001
feature_id: FEAT-AC1A
id: TASK-SFT-005
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: high
status: design_approved
task_type: testing
title: Seam tests S8 — Quality gate to state transition wiring
wave: 2
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