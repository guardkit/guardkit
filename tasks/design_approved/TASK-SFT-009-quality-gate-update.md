---
complexity: 4
dependencies:
- TASK-SFT-003
- TASK-SFT-004
- TASK-SFT-005
feature_id: FEAT-AC1A
id: TASK-SFT-009
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: high
status: in_review
task_type: feature
title: Update QualityGateProfile with seam test requirements
wave: 3
autobuild_state:
  current_turn: 3
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:30:50.793903'
  last_updated: '2026-02-15T21:43:35.354069'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 Existing tests pass (no\
      \ regression)"
    timestamp: '2026-02-15T21:30:50.793903'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- No task-specific tests created and no task-specific tests found via
      independent verification. Project-wide test suite may pass but this task contributes
      zero test coverage.'
    timestamp: '2026-02-15T21:36:02.545190'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:39:31.107645'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Update Quality Gates for Seam Test Requirements

## Objective

Add seam test awareness to the quality gate pipeline so that features crossing technology boundaries require seam tests before completion.

## Acceptance Criteria

- [ ] `QualityGateProfile` in `guardkit/models/task_types.py` gets `seam_tests_recommended: bool` field
- [ ] FEATURE and REFACTOR profiles set `seam_tests_recommended=True`
- [ ] SCAFFOLDING, DOCUMENTATION, TESTING profiles set `seam_tests_recommended=False`
- [ ] Coach validation prompt (in `coach_validator.py`) includes seam test check when `seam_tests_recommended=True`
- [ ] Feature plan template (in `feature-plan.md`) includes seam test checklist item
- [ ] Architecture docs updated: `docs/architecture/quality-gate-pipeline.md` reflects new gate
- [ ] Cross-cutting concerns updated: `docs/architecture/crosscutting-concerns.md` adds XC-seam-testing
- [ ] Existing tests pass (no regression)

## Implementation Notes

- This is a soft gate (recommended, not blocking) in the first iteration
- The Coach can note "no seam tests for cross-boundary feature" but should not block
- Future iteration can make it a hard gate after the team has experience with seam testing
- Add the field with `seam_tests_recommended: bool = False` default to avoid breaking existing profiles
