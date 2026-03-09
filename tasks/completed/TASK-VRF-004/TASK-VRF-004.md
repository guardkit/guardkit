---
id: TASK-VRF-004
title: Add backend-aware AC validation to feature-plan command
status: completed
priority: high
complexity: 6
tags: [feature-plan, acceptance-criteria, validation, vllm]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 3
implementation_mode: task-work
dependencies: []
created: 2026-03-09
updated: 2026-03-09
completed: 2026-03-09
previous_state: in_review
state_transition_reason: "All quality gates passed - task completed"
completed_location: tasks/completed/TASK-VRF-004/
---

# Task: Backend-Aware AC Validation in Feature-Plan

## Description

Add pre-flight acceptance criteria validation to the `/feature-plan` command that detects and flags infeasible criteria based on the target backend (vLLM vs cloud). Currently, AC generation is entirely LLM-driven with no feasibility checking.

## Context

From TASK-REV-5E1F review: The feature planning system generated "mypy strict + zero Any types" criteria for TASK-FBP-007 without checking whether they're achievable on a vLLM backend. This is a systemic issue — feature-plan generates AC without checking backend limitations.

## Changes Required

1. **Create AC validation module** (e.g., `guardkit/validation/ac_validator.py`):
   - Detect backend type from `timeout_multiplier` (>1.0 = local/vLLM)
   - Define known-infeasible patterns per backend:
     - vLLM: `mypy --strict`, `zero Any types`, strict typing criteria
   - Score each AC on 1-10 feasibility scale
   - Warn if any criterion scores < 3

2. **Integrate into feature-plan workflow**:
   - After LLM generates task breakdown with AC
   - Before writing task files
   - Display warnings for infeasible criteria
   - Suggest relaxed alternatives

3. **Create backend-specific AC templates**:
   - `vLLM`: Relaxed typing (disallow-untyped-defs, not strict)
   - `cloud`: Full strictness allowed
   - `unknown`: Conservative defaults

## Acceptance Criteria

- [x] AC validation module detects vLLM backend from timeout_multiplier
- [x] Known-infeasible patterns flagged with warnings
- [x] Relaxed alternatives suggested for flagged criteria
- [x] Integration with feature-plan workflow
- [x] Existing feature-plan behavior unchanged for cloud backends

## Implementation Summary

### Files Created
- `guardkit/validation/__init__.py` - Package with public API exports
- `guardkit/validation/ac_validator.py` - AC validation module (83 statements)
- `tests/unit/test_ac_validator.py` - Test suite (54 tests, 10 classes)

### Quality Gates
- Tests: 54/54 passed (100%)
- Line Coverage: 100%
- Branch Coverage: 100%
- Code Review: Approved with fixes applied
