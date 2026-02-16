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
status: design_approved
task_type: feature
title: Update QualityGateProfile with seam test requirements
wave: 3
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