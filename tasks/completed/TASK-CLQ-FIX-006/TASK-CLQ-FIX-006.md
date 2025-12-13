---
id: TASK-CLQ-FIX-006
title: "Implement --with-questions flag in should_clarify() function"
status: completed
created: 2025-12-13T17:00:00Z
updated: 2025-12-13T18:45:00Z
completed: 2025-12-13T18:45:00Z
priority: high
tags: [clarifying-questions, flag, bug-fix]
complexity: 2
parent_review: TASK-REV-0614
implementation_mode: direct
dependencies: []
---

# Task: Implement --with-questions flag in should_clarify()

## Description

The `--with-questions` flag is documented in `task-work.md` and `task-review.md` to force clarification questions even for trivial tasks, but the `should_clarify()` function in `core.py` doesn't implement this flag.

## Evidence

From `task-work.md` (lines 479-486):
```markdown
### Flag: --with-questions

**Purpose**: Force Phase 1.6 (Clarifying Questions) even for trivial tasks (complexity 1-2).

**Use cases**:
- Learning mode - understand what clarifications are available
- High-stakes tasks where even trivial scope needs confirmation
```

But `should_clarify()` only checks:
```python
if flags.get("no_questions", False):
    return ClarificationMode.SKIP
if flags.get("micro", False):
    return ClarificationMode.SKIP
if flags.get("defaults", False):
    return ClarificationMode.USE_DEFAULTS
# Then complexity-based logic...
# NO CHECK FOR with_questions!
```

## Fix Required

Add `with_questions` check to `should_clarify()`:

```python
def should_clarify(
    context_type: Literal["review", "implement_prefs", "planning"],
    complexity: int,
    flags: Dict[str, Any]
) -> ClarificationMode:
    # Universal skip conditions
    if flags.get("no_questions", False):
        return ClarificationMode.SKIP
    if flags.get("micro", False):
        return ClarificationMode.SKIP
    if flags.get("defaults", False):
        return ClarificationMode.USE_DEFAULTS

    # ADD THIS: Force full clarification if requested
    if flags.get("with_questions", False):
        return ClarificationMode.FULL

    # Context-specific thresholds (existing logic)
    thresholds = {
        "review": {"skip": 2, "quick": 4, "full": 6},
        # ...
    }
    # ... rest of complexity-based logic
```

## File to Modify

`installer/core/commands/lib/clarification/core.py`

## Acceptance Criteria

- [x] `should_clarify("planning", 1, {"with_questions": True})` returns `ClarificationMode.FULL`
- [x] `should_clarify("review", 2, {"with_questions": True})` returns `ClarificationMode.FULL`
- [x] Flag precedence: `no_questions` still overrides `with_questions`
- [x] Add unit test for `with_questions` flag

## Test Case

```python
def test_with_questions_forces_full():
    """--with-questions should force FULL mode regardless of complexity."""
    # Trivial task (complexity 1) should normally skip
    assert should_clarify("planning", 1, {}) == ClarificationMode.SKIP

    # With --with-questions, should force FULL
    assert should_clarify("planning", 1, {"with_questions": True}) == ClarificationMode.FULL

    # --no-questions takes precedence
    assert should_clarify("planning", 1, {"with_questions": True, "no_questions": True}) == ClarificationMode.SKIP
```

## Estimated Effort

30 minutes (trivial fix + test)

## Notes

This is a pre-existing gap in the clarification module design, not introduced by the TASK-CLQ-FIX-001 integration. The flag was documented but never implemented.
