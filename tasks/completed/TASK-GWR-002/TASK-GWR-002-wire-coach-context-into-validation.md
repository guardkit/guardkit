---
id: TASK-GWR-002
title: Wire Coach context into CoachValidator.validate()
status: completed
completed: 2026-02-15T10:20:00Z
updated: 2026-02-15T10:20:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed, implementation verified"
created: 2026-02-14T10:30:00Z
priority: high
tags: [graphiti, coach, context-injection, autobuild]
parent_review: TASK-REV-GROI
feature_id: FEAT-GWR
implementation_mode: task-work
wave: 2
complexity: 4
task_type: feature
depends_on:
  - TASK-GWR-001
completed_location: tasks/completed/TASK-GWR-002/
---

# Task: Wire Coach Context Into CoachValidator.validate()

## Description

The TASK-REV-GROI review identified that `_invoke_coach_safely()` in `autobuild.py` retrieves `context_prompt` via `thread_loader.get_coach_context()` (line 2967) but then calls `validator.validate()` WITHOUT passing it (lines 3010-3018). The context is assembled, logged, and discarded.

This task wires the already-retrieved context into the validator so it's traceable and available for validation decisions.

## Acceptance Criteria

- [x] AC-F1-01: `CoachValidator.validate()` accepts optional `context: Optional[str] = None` parameter
- [x] AC-F1-02: When context is provided, it appears in `CoachValidationResult` (new `context_used` field or in `rationale`)
- [x] AC-F1-03: `_invoke_coach_safely` passes `context_prompt` to `validator.validate()`
- [x] AC-F1-04: `validate(context=None)` works identically to current behavior (backward compatibility)
- [x] AC-F1-05: Graceful degradation when context retrieval fails (empty string or None)
- [x] AC-F1-06: Structured log `[Graphiti] Coach context provided: N chars` emitted when context is used

## Files Modified

- `guardkit/orchestrator/quality_gates/coach_validator.py` - Added context_used field and context parameter
- `guardkit/orchestrator/autobuild.py` - Wired context_prompt to validator.validate()
- `tests/unit/test_coach_validator.py` - 4 new tests for context wiring

## Tests

- test_validate_with_context_includes_context_used_in_result - PASS
- test_validate_with_context_none_is_backward_compatible - PASS
- test_validate_with_empty_context_treated_as_no_context - PASS
- test_to_dict_includes_context_used_field - PASS
