---
id: TASK-CLQ-004
title: Create Context C templates (task-work implementation planning)
status: completed
created: 2025-12-08T14:00:00Z
updated: 2025-12-10T07:30:00Z
completed: 2025-12-10T07:30:00Z
priority: high
tags: [clarifying-questions, templates, task-work, wave-2]
complexity: 6
parent_feature: clarifying-questions
wave: 2
conductor_workspace: clarifying-questions-wave2-context-c
implementation_method: task-work
completed_location: tasks/completed/TASK-CLQ-004/
organized_files: [
  "TASK-CLQ-004.md"
]
---

# Task: Create Context C templates (task-work implementation planning)

## Description

Create the question templates and generator for Context C - implementation planning clarification used in `/task-work` Phase 1.5. This is the most comprehensive context with 6 question categories based on the 5W1H framework.

## Acceptance Criteria

- [x] Create `installer/global/commands/lib/clarification/templates/implementation_planning.py` with:
  - [x] SCOPE_QUESTIONS (5W: What) - Feature boundary questions (4 questions)
  - [x] USER_QUESTIONS (5W: Who) - User/persona questions (3 questions)
  - [x] TECHNOLOGY_QUESTIONS (5W: How) - Tech choice questions (5 questions)
  - [x] INTEGRATION_QUESTIONS (5W: Where) - Integration point questions (4 questions)
  - [x] TRADEOFF_QUESTIONS (5W: Why) - Priority trade-off questions (4 questions)
  - [x] EDGE_CASE_QUESTIONS - Edge case handling questions (5 questions)
- [x] Create `installer/global/commands/lib/clarification/generators/planning_generator.py` with:
  - [x] `generate_planning_questions()` function
  - [x] Logic to select relevant questions based on detection results (5 detection functions)
  - [x] Question prioritization (limit to 7 questions max)
- [x] Each question template has: id, category, text, options, default, rationale (25 total templates)
- [x] Create unit tests (34 tests, all passing)

## Technical Specification

### Question Templates

```python
# templates/implementation_planning.py

SCOPE_QUESTIONS = [
    Question(
        id="scope_boundary",
        category="scope",
        text='Should "{feature}" include {related_capability}?',
        options=["[Y]es", "[N]o", "[D]etails: ___"],
        default="Y",
        rationale="Common expectation for {feature}",
    ),
    Question(
        id="scope_extent",
        category="scope",
        text="What is the boundary for this task?",
        options=["[M]inimal (core only)", "[S]tandard (core + common cases)", "[C]omplete (all edge cases)"],
        default="S",
        rationale="Standard scope covers most use cases without over-engineering",
    ),
]

TECHNOLOGY_QUESTIONS = [
    Question(
        id="tech_choice",
        category="technology",
        text="Preferred approach for {component}?",
        options=["[A] {option_a}", "[B] {option_b}", "[C] Let me decide", "[O]ther: ___"],
        default="C",
        rationale="AI will recommend based on codebase patterns",
    ),
    Question(
        id="existing_pattern",
        category="technology",
        text="Use existing {pattern} or create new?",
        options=["[E]xisting (extend)", "[N]ew (create)", "[R]ecommend"],
        default="R",
        rationale="AI will analyze codebase for existing patterns",
    ),
]

# ... similar for USER_QUESTIONS, INTEGRATION_QUESTIONS, TRADEOFF_QUESTIONS, EDGE_CASE_QUESTIONS
```

### Generator Function

```python
# generators/planning_generator.py

def generate_planning_questions(
    task_context: TaskContext,
    complexity_score: int,
    codebase_context: Optional[CodebaseContext] = None
) -> List[Question]:
    """
    Generate clarifying questions for task-work Phase 1.5.

    Uses:
    - Detection results to identify what needs clarification
    - Complexity score to determine depth
    - Question templates to format questions
    """
    questions = []

    # 1. Scope Questions (What) - always check
    if scope_ambiguity := detect_scope_ambiguity(task_context):
        questions.extend(
            instantiate_questions(SCOPE_QUESTIONS, scope_ambiguity)
        )

    # 2. User Questions (Who) - if user ambiguity detected
    if user_ambiguity := detect_user_ambiguity(task_context):
        questions.extend(
            instantiate_questions(USER_QUESTIONS, user_ambiguity)
        )

    # 3. Technology Questions (How) - if choices detected
    if tech_choices := detect_technology_choices(task_context, codebase_context):
        questions.extend(
            instantiate_questions(TECHNOLOGY_QUESTIONS, tech_choices)
        )

    # 4. Integration Questions (Where) - if integration points detected
    if integration_points := detect_integration_points(task_context, codebase_context):
        questions.extend(
            instantiate_questions(INTEGRATION_QUESTIONS, integration_points)
        )

    # 5. Trade-off Questions (Why) - only for medium+ complexity
    if complexity_score >= 5:
        questions.extend(TRADEOFF_QUESTIONS)

    # 6. Edge Case Questions - only for complex tasks
    if complexity_score >= 7:
        if edge_cases := detect_unhandled_edge_cases(task_context):
            questions.extend(
                instantiate_questions(EDGE_CASE_QUESTIONS, edge_cases)
            )

    # Prioritize and limit
    return prioritize_questions(questions, max_questions=7)
```

## Files to Create

1. `installer/global/commands/lib/clarification/templates/__init__.py`
2. `installer/global/commands/lib/clarification/templates/implementation_planning.py`
3. `installer/global/commands/lib/clarification/generators/__init__.py`
4. `installer/global/commands/lib/clarification/generators/planning_generator.py`
5. `tests/unit/lib/clarification/test_planning_generator.py`

## Dependencies

- Wave 1: core.py (Question dataclass)
- Wave 1: detection.py (detection functions)

## Related Tasks

- TASK-CLQ-005 (Context A - parallel)
- TASK-CLQ-006 (Context B - parallel)

## Reference

See [Review Report Section: Question Categories](./../../../.claude/reviews/TASK-REV-B130-review-report.md#question-categories-merged-from-feature-dev--requirekit) for detailed specification.
