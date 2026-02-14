---
id: TASK-GWR-002
title: Wire Coach context into CoachValidator.validate()
status: backlog
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
---

# Task: Wire Coach Context Into CoachValidator.validate()

## Description

The TASK-REV-GROI review identified that `_invoke_coach_safely()` in `autobuild.py` retrieves `context_prompt` via `thread_loader.get_coach_context()` (line 2967) but then calls `validator.validate()` WITHOUT passing it (lines 3010-3018). The context is assembled, logged, and discarded.

This task wires the already-retrieved context into the validator so it's traceable and available for validation decisions.

## The Disconnection

```python
# autobuild.py line 2967 — context IS retrieved:
context_prompt = context_result.prompt_text

# autobuild.py lines 3010-3018 — context NOT passed:
validation_result = validator.validate(
    task_id=task_id,
    turn=turn,
    task={
        "acceptance_criteria": acceptance_criteria or [],
        "task_type": task_type,
    },
    skip_arch_review=skip_arch_review,
    # NOTE: context_prompt is available but not passed!
)
```

## Implementation

### Step 1: Add `context` parameter to `CoachValidator.validate()`

File: `guardkit/orchestrator/quality_gates/coach_validator.py`

Add an optional `context: Optional[str] = None` parameter to `validate()`. When provided:
- Include in `CoachValidationResult` via a new optional `context_used: Optional[str]` field
- Log at DEBUG level: `[Graphiti] Coach context provided: {len(context)} chars`
- Append a brief note to `rationale` when context was available (e.g., "Architecture context: {N} chars provided")

This is the **minimal** wire-up. The context doesn't change approve/feedback decision logic yet — traceability first.

### Step 2: Pass `context_prompt` from `_invoke_coach_safely()` to `validator.validate()`

File: `guardkit/orchestrator/autobuild.py`

At lines 3010-3018, add `context=context_prompt if context_prompt else None`:

```python
validation_result = validator.validate(
    task_id=task_id,
    turn=turn,
    task={
        "acceptance_criteria": acceptance_criteria or [],
        "task_type": task_type,
    },
    skip_arch_review=skip_arch_review,
    context=context_prompt if context_prompt else None,  # NEW
)
```

### Step 3: Add observability logging

In `_invoke_coach_safely()`, after the `validator.validate()` call, log:
```python
if context_prompt:
    logger.info(
        f"[Graphiti] Coach context provided: {len(context_prompt)} chars"
    )
```

## Acceptance Criteria

- [ ] AC-F1-01: `CoachValidator.validate()` accepts optional `context: Optional[str] = None` parameter
- [ ] AC-F1-02: When context is provided, it appears in `CoachValidationResult` (new `context_used` field or in `rationale`)
- [ ] AC-F1-03: `_invoke_coach_safely` passes `context_prompt` to `validator.validate()`
- [ ] AC-F1-04: `validate(context=None)` works identically to current behavior (backward compatibility)
- [ ] AC-F1-05: Graceful degradation when context retrieval fails (empty string or None)
- [ ] AC-F1-06: Structured log `[Graphiti] Coach context provided: N chars` emitted when context is used

## Tests Required

- `tests/unit/test_coach_validator.py`: Test `validate(context="some architecture context")` includes context in result
- `tests/unit/test_coach_validator.py`: Test `validate(context=None)` produces identical output to current behavior
- `tests/unit/test_coach_validator.py`: Test `validate(context="")` treated as no context (backward compat)
- Verify `_invoke_coach_safely` passes context_prompt by checking mock validator call args

## Implementation Notes

- `CoachValidationResult` is likely a dataclass — add optional `context_used: Optional[str] = None` field
- Do NOT change the approve/feedback decision logic based on context yet — that's a future enhancement
- The goal is traceability: can we see in logs/results that context was available?
- This enables the before/after measurement protocol
