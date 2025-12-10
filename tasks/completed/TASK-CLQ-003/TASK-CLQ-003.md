---
id: TASK-CLQ-003
title: Create display formatting utilities
status: completed
created: 2025-12-08T14:00:00Z
updated: 2025-12-10T00:00:00Z
completed: 2025-12-10T00:00:00Z
priority: medium
tags: [clarifying-questions, display, ui, wave-1]
complexity: 4
parent_feature: clarifying-questions
wave: 1
conductor_workspace: clarifying-questions-wave1-display
implementation_method: direct
completed_location: tasks/completed/TASK-CLQ-003/
organized_files: ["TASK-CLQ-003.md"]
---

# Task: Create display formatting utilities

## Description

Create the display module that handles UI formatting for clarification questions. This includes full question display (blocking), quick question display (with timeout), and skip message display. The formatting should be consistent with GuardKit's existing checkpoint patterns.

## Acceptance Criteria

- [x] Create `installer/core/commands/lib/clarification/display.py` with:
  - [x] `display_full_questions()` - Comprehensive question display
  - [x] `display_quick_questions()` - Brief display with timeout
  - [x] `display_skip_message()` - Message when skipping clarification
  - [x] `format_question_box()` - Helper for consistent box formatting
  - [x] `format_response_prompt()` - Format the input prompt
- [x] Match existing GuardKit checkpoint visual style
- [x] Support category grouping (SCOPE, TECHNOLOGY, TRADE-OFFS, etc.)
- [x] Include default value display with rationale
- [x] Support timeout display for quick mode

## Technical Specification

### display_full_questions()

```python
def display_full_questions(
    questions: List[Question],
    task_id: str,
    task_title: str,
    complexity: int
) -> str:
    """
    Generate full question display for blocking clarification.

    Output format:
    ═══════════════════════════════════════════════════════════════════════════
    🤔 PHASE 1.5 - CLARIFICATION QUESTIONS
    ═══════════════════════════════════════════════════════════════════════════

    TASK: TASK-XXX - {Title}
    COMPLEXITY: {score}/10 ({level})

    Before planning implementation, I need clarification on {n} items:

    ┌─────────────────────────────────────────────────────────────────────────┐
    │ SCOPE (What)                                                            │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ 1. Should "user authentication" include password reset functionality?  │
    │    [Y]es / [N]o / [D]etails                                            │
    │    Default: Yes (common expectation)                                    │
    └─────────────────────────────────────────────────────────────────────────┘

    Enter responses (e.g., "1:Y 2:N 3:J 4:R 5:S")
    Or press [Enter] to use all defaults
    Or type "skip" to proceed without clarification

    Your responses: _
    ═══════════════════════════════════════════════════════════════════════════
    """
```

### display_quick_questions()

```python
def display_quick_questions(
    questions: List[Question],
    timeout_seconds: int = 15
) -> str:
    """
    Generate quick question display with timeout.

    Output format:
    ═══════════════════════════════════════════════════════════════════════════
    🤔 QUICK CLARIFICATION (2 questions, 15s timeout)
    ═══════════════════════════════════════════════════════════════════════════

    1. Include error handling for network failures? [Y/n] Default: Y
    2. Use existing logging pattern? [Y/n] Default: Y

    [Enter] for defaults, or type answers (e.g., "Y N"): _

    Auto-proceeding with defaults in 15s...
    ═══════════════════════════════════════════════════════════════════════════
    """
```

### display_skip_message()

```python
def display_skip_message(
    reason: str,  # "trivial", "flag", "defaults"
    complexity: Optional[int] = None
) -> str:
    """
    Generate skip message when clarification is bypassed.

    Output format:
    ═══════════════════════════════════════════════════════════════════════════
    ✅ PHASE 1.5 - SKIPPED (Trivial task, complexity: 2/10)
    ═══════════════════════════════════════════════════════════════════════════
    Task description is clear. Proceeding to implementation planning...
    ═══════════════════════════════════════════════════════════════════════════
    """
```

## Files to Create

1. `installer/core/commands/lib/clarification/display.py`

## Why Direct Implementation

- Straightforward UI formatting
- Clear patterns from existing checkpoints (Phase 2.8)
- No complex logic or algorithms
- Well-defined spec from review report

## Dependencies

- TASK-CLQ-001 (imports Question dataclass) - but can develop in parallel with agreed interface

## Related Tasks

- TASK-CLQ-001 (core.py - parallel)
- TASK-CLQ-002 (detection.py - parallel)

## Reference

See [Review Report Section: UI/UX Specification](./../../../.claude/reviews/TASK-REV-B130-review-report.md#uiux-specification) for detailed mockups.
