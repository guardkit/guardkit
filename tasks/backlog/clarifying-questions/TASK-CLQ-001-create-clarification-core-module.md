---
id: TASK-CLQ-001
title: Create clarification module core infrastructure
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: high
tags: [clarifying-questions, core, infrastructure, wave-1]
complexity: 6
parent_feature: clarifying-questions
wave: 1
conductor_workspace: clarifying-questions-wave1-core
implementation_method: task-work
---

# Task: Create clarification module core infrastructure

## Description

Create the core infrastructure for the unified clarification module. This includes shared dataclasses, response processing functions, and prompt formatting utilities that will be used by all three clarification contexts (review scope, implementation prefs, implementation planning).

## Acceptance Criteria

- [ ] Create `installer/global/commands/lib/clarification/__init__.py` with module exports
- [ ] Create `installer/global/commands/lib/clarification/core.py` with:
  - [ ] `ClarificationContext` dataclass (explicit_decisions, assumed_defaults, metadata)
  - [ ] `Decision` dataclass (category, question, answer, is_default, confidence, rationale)
  - [ ] `Question` dataclass (id, category, text, options, default, rationale)
  - [ ] `ClarificationMode` enum (SKIP, QUICK, FULL, USE_DEFAULTS)
  - [ ] `should_clarify()` function with context-specific thresholds
  - [ ] `process_responses()` function to parse user input
  - [ ] `format_for_prompt()` function to format context for agent prompts
  - [ ] `persist_to_frontmatter()` stub for Wave 4
- [ ] Include type hints for all functions and dataclasses
- [ ] Add docstrings explaining usage
- [ ] Create basic unit tests in `tests/unit/lib/clarification/test_core.py`

## Technical Specification

### ClarificationContext Dataclass

```python
@dataclass
class ClarificationContext:
    """Context passed to planning/review agents."""
    explicit_decisions: List[Decision]
    assumed_defaults: List[Decision]
    not_applicable: List[str]
    total_questions: int
    answered_count: int
    skipped_count: int
    complexity_triggered: bool
    user_override: Optional[str]  # "skip", "defaults", etc.
```

### Decision Dataclass

```python
@dataclass
class Decision:
    """Single clarification decision."""
    category: str          # "scope", "technology", "trade-off", etc.
    question: str          # Full question text
    answer: str            # User's answer or default
    is_default: bool       # True if user used default
    confidence: float      # 0-1, lower if assumed
    rationale: str         # Why this default was chosen
```

### should_clarify() Function

```python
def should_clarify(
    context_type: Literal["review", "implement_prefs", "planning"],
    complexity: int,
    flags: Dict[str, Any]
) -> ClarificationMode:
    """Determine clarification mode based on context and complexity."""
    # Universal skip conditions
    if flags.get("no_questions"):
        return ClarificationMode.SKIP
    if flags.get("micro"):
        return ClarificationMode.SKIP
    if flags.get("defaults"):
        return ClarificationMode.USE_DEFAULTS

    # Context-specific thresholds
    thresholds = {
        "review": {"skip": 2, "quick": 4, "full": 6},
        "implement_prefs": {"skip": 3, "quick": 5, "full": 7},
        "planning": {"skip": 2, "quick": 4, "full": 5},
    }
    # ... implementation
```

## Files to Create

1. `installer/global/commands/lib/clarification/__init__.py`
2. `installer/global/commands/lib/clarification/core.py`
3. `tests/unit/lib/clarification/test_core.py`

## Dependencies

- None (Wave 1 has no dependencies)

## Related Tasks

- TASK-CLQ-002 (detection.py - parallel)
- TASK-CLQ-003 (display.py - parallel)

## Reference

See [Review Report Section: Response Processing](./../../../.claude/reviews/TASK-REV-B130-review-report.md#response-processing) for detailed specification.
