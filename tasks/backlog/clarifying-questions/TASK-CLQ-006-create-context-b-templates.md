---
id: TASK-CLQ-006
title: Create Context B templates (feature-plan implementation preferences)
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: medium
tags: [clarifying-questions, templates, feature-plan, wave-2]
complexity: 4
parent_feature: clarifying-questions
wave: 2
conductor_workspace: clarifying-questions-wave2-context-b
implementation_method: direct
---

# Task: Create Context B templates (feature-plan implementation preferences)

## Description

Create the question templates and generator for Context B - implementation preferences clarification used when user chooses [I]mplement at the decision checkpoint in `/task-review` or `/feature-plan`. This helps guide how subtasks should be created and executed.

## Acceptance Criteria

- [ ] Create `installer/core/commands/lib/clarification/templates/implementation_prefs.py` with:
  - [ ] APPROACH_PREFERENCE_QUESTIONS - Which recommended approach to follow
  - [ ] CONSTRAINT_QUESTIONS - Time/resource constraints
  - [ ] PARALLELIZATION_QUESTIONS - Parallel vs sequential preference
  - [ ] TESTING_DEPTH_QUESTIONS - TDD/standard/minimal
- [ ] Create `installer/core/commands/lib/clarification/generators/implement_generator.py` with:
  - [ ] `generate_implement_questions()` function
  - [ ] Logic to present approach options from review findings
- [ ] Each question has: id, category, text, options, default, rationale
- [ ] Limit to 4 questions (implementation prefs are action-oriented)

## Technical Specification

### Question Templates

```python
# templates/implementation_prefs.py

APPROACH_PREFERENCE_QUESTIONS = [
    Question(
        id="approach_choice",
        category="approach",
        text="Which recommended approach should subtasks follow?",
        options=[
            "[1] Option 1 (Recommended)",
            "[2] Option 2",
            "[3] Option 3",
            "[R]ecommend for me"
        ],
        default="R",
        rationale="AI will use the recommended approach from analysis",
    ),
]

CONSTRAINT_QUESTIONS = [
    Question(
        id="constraints",
        category="constraints",
        text="Any implementation constraints?",
        options=[
            "[T]ime constraint (specify)",
            "[R]esource limit",
            "[N]one",
            "[C]ustom: ___"
        ],
        default="N",
        rationale="No constraints allows full implementation",
    ),
]

PARALLELIZATION_QUESTIONS = [
    Question(
        id="parallelization",
        category="execution",
        text="Parallelization preference?",
        options=[
            "[M]aximize parallel (Conductor)",
            "[S]equential (simpler)",
            "[D]etect automatically"
        ],
        default="D",
        rationale="Auto-detect based on file conflicts",
    ),
]

TESTING_DEPTH_QUESTIONS = [
    Question(
        id="testing_depth",
        category="quality",
        text="Testing depth for subtasks?",
        options=[
            "[F]ull TDD",
            "[S]tandard",
            "[M]inimal",
            "[D]efault based on complexity"
        ],
        default="D",
        rationale="Default scales with task complexity",
    ),
]
```

### Generator Function

```python
# generators/implement_generator.py

def generate_implement_questions(
    review_findings: ReviewFindings,
    num_subtasks: int,
    complexity: int
) -> List[Question]:
    """
    Generate clarifying questions for [I]mplement option.

    Triggered after user chooses [I]mplement at decision checkpoint.
    """
    questions = []

    # Ask about approach if multiple options were presented
    if len(review_findings.options) > 1:
        # Customize options based on actual review findings
        approach_q = customize_approach_question(
            APPROACH_PREFERENCE_QUESTIONS[0],
            review_findings.options
        )
        questions.append(approach_q)

    # Ask about constraints for larger implementations
    if num_subtasks >= 3:
        questions.extend(CONSTRAINT_QUESTIONS)

    # Ask about parallelization for multi-task implementations
    if num_subtasks >= 3:
        questions.extend(PARALLELIZATION_QUESTIONS)

    # Ask about testing depth for complex tasks
    if complexity >= 5:
        questions.extend(TESTING_DEPTH_QUESTIONS)

    return questions[:4]  # Limit to 4 max


def customize_approach_question(
    template: Question,
    options: List[ReviewOption]
) -> Question:
    """Customize approach question with actual review options."""
    custom_options = []
    for i, opt in enumerate(options[:3], 1):
        rec = " (Recommended)" if opt.is_recommended else ""
        custom_options.append(f"[{i}] {opt.name}{rec}")
    custom_options.append("[R]ecommend for me")

    return Question(
        id=template.id,
        category=template.category,
        text=template.text,
        options=custom_options,
        default=template.default,
        rationale=template.rationale,
    )
```

## Files to Create

1. `installer/core/commands/lib/clarification/templates/implementation_prefs.py`
2. `installer/core/commands/lib/clarification/generators/implement_generator.py`

## Why Direct Implementation

- Simpler context (4 categories)
- Clear spec from review report
- Follows same pattern as Context A and C
- Lower complexity (4/10)

## Dependencies

- Wave 1: core.py (Question dataclass)

## Related Tasks

- TASK-CLQ-004 (Context C - parallel)
- TASK-CLQ-005 (Context A - parallel)

## Reference

See [Review Report Section: Context B: Implementation Preferences](./../../../.claude/reviews/TASK-REV-B130-review-report.md#context-b-implementation-preferences-feature-plan-iimplement).
