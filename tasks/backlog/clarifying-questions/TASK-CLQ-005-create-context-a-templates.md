---
id: TASK-CLQ-005
title: Create Context A templates (task-review scope clarification)
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: medium
tags: [clarifying-questions, templates, task-review, wave-2]
complexity: 4
parent_feature: clarifying-questions
wave: 2
conductor_workspace: clarifying-questions-wave2-context-a
implementation_method: direct
---

# Task: Create Context A templates (task-review scope clarification)

## Description

Create the question templates and generator for Context A - review scope clarification used in `/task-review` Phase 1 and `/feature-plan` Step 2. This context helps guide what the review should focus on and what trade-offs to prioritize.

## Acceptance Criteria

- [ ] Create `installer/global/commands/lib/clarification/templates/review_scope.py` with:
  - [ ] REVIEW_FOCUS_QUESTIONS - What aspects to analyze
  - [ ] ANALYSIS_DEPTH_QUESTIONS - How deep to go
  - [ ] TRADEOFF_PRIORITY_QUESTIONS - What to optimize for
  - [ ] SPECIFIC_CONCERNS_QUESTIONS - User-specified focus areas
- [ ] Create `installer/global/commands/lib/clarification/generators/review_generator.py` with:
  - [ ] `generate_review_questions()` function
  - [ ] Logic to select questions based on review mode
- [ ] Each question has: id, category, text, options, default, rationale
- [ ] Limit to 4-5 questions (reviews are lighter weight)

## Technical Specification

### Question Templates

```python
# templates/review_scope.py

REVIEW_FOCUS_QUESTIONS = [
    Question(
        id="review_aspects",
        category="focus",
        text="What aspects should this analysis focus on?",
        options=[
            "[A]ll aspects",
            "[T]echnical only",
            "[R]chitecture",
            "[P]erformance",
            "[S]ecurity"
        ],
        default="A",
        rationale="All aspects provides comprehensive analysis",
    ),
]

TRADEOFF_PRIORITY_QUESTIONS = [
    Question(
        id="tradeoff_priority",
        category="priority",
        text="What trade-offs are you optimizing for?",
        options=[
            "[S]peed of delivery",
            "[Q]uality/reliability",
            "[C]ost",
            "[M]aintainability",
            "[B]alanced"
        ],
        default="B",
        rationale="Balanced approach considers all factors",
    ),
]

SPECIFIC_CONCERNS_QUESTIONS = [
    Question(
        id="specific_concerns",
        category="concerns",
        text="Are there specific concerns you want addressed?",
        options=["[Enter text or skip]"],
        default="",
        rationale="Free-form input for user-specific concerns",
    ),
]

EXTENSIBILITY_QUESTIONS = [
    Question(
        id="future_extensibility",
        category="scope",
        text="Should the review consider future extensibility?",
        options=[
            "[Y]es (long-term thinking)",
            "[N]o (current needs only)",
            "[D]efault"
        ],
        default="D",
        rationale="Default based on task complexity",
    ),
]
```

### Generator Function

```python
# generators/review_generator.py

def generate_review_questions(
    task_context: TaskContext,
    review_mode: str,  # "architectural", "code-quality", "decision", etc.
    complexity: int
) -> List[Question]:
    """
    Generate clarifying questions for task-review Phase 1.

    Lighter weight than planning questions - max 4-5 questions.
    """
    questions = []

    # Always ask about focus (unless mode is specific)
    if review_mode in ["architectural", "decision"]:
        questions.extend(REVIEW_FOCUS_QUESTIONS)

    # Ask about trade-offs for decision mode
    if review_mode == "decision":
        questions.extend(TRADEOFF_PRIORITY_QUESTIONS)

    # Ask about specific concerns for comprehensive reviews
    if complexity >= 6:
        questions.extend(SPECIFIC_CONCERNS_QUESTIONS)

    # Ask about extensibility for architectural reviews
    if review_mode == "architectural":
        questions.extend(EXTENSIBILITY_QUESTIONS)

    return questions[:5]  # Limit to 5 max
```

## Files to Create

1. `installer/global/commands/lib/clarification/templates/review_scope.py`
2. `installer/global/commands/lib/clarification/generators/review_generator.py`

## Why Direct Implementation

- Simpler than Context C (4 categories vs 6)
- Clear spec from review report
- Follows same pattern as Context C
- Lower complexity (4/10)

## Dependencies

- Wave 1: core.py (Question dataclass)

## Related Tasks

- TASK-CLQ-004 (Context C - parallel)
- TASK-CLQ-006 (Context B - parallel)

## Reference

See [Review Report Section: Context A: Review Scope Clarification](./../../../.claude/reviews/TASK-REV-B130-review-report.md#context-a-review-scope-clarification-task-review-feature-plan).
