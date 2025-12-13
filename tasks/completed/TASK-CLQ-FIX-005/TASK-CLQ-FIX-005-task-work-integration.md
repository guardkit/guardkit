---
id: TASK-CLQ-FIX-005
title: "Integrate clarification module into task-work Phase 1.6"
status: completed
created: 2025-12-13T16:45:00Z
updated: 2025-12-13T22:45:00Z
completed: 2025-12-13T22:45:00Z
priority: critical
tags: [clarifying-questions, task-work, orchestrator, integration, bug-fix]
complexity: 5
parent_review: TASK-REV-0614
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-CLQ-FIX-005/
---

# Task: Integrate clarification module into task-work Phase 1.6

## Description

The `/task-work` command documents **Phase 1.6: Clarifying Questions** in `task-work.md`, and the module exists (`planning_generator.py`), but clarification is never actually invoked.

This is the same pattern as the task-review issue - the clarification code exists but isn't wired into the execution path.

## Evidence

From `task-work.md` documentation (lines 1441-1475):
```
Phase 1.5: Loading context...
Phase 1.6: Clarifying Questions (complexity: 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CLARIFYING QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Implementation Scope
    How comprehensive should this implementation be?
    ...
```

But this flow never executes because:
1. No Python orchestrator for task-work (it's markdown-based)
2. `phase_execution.py` doesn't import or call clarification functions
3. Claude follows markdown instructions but doesn't call the Python module

## Implementation Options

### Option A: Add to phase_execution.py (Recommended)

If `phase_execution.py` handles task-work phases, add clarification:

```python
from clarification import (
    should_clarify,
    ClarificationMode,
)
from clarification.generators.planning_generator import generate_planning_questions
from clarification.display import display_full_questions, display_quick_questions

def execute_phase_1_6(task_context, flags):
    """Phase 1.6: Clarifying Questions."""
    complexity = task_context.get('complexity', 5)

    mode = should_clarify("planning", complexity, flags)

    if mode == ClarificationMode.SKIP:
        print("Skipping clarification (trivial task)")
        return None

    questions = generate_planning_questions(
        task_context=TaskContext(
            task_id=task_context['task_id'],
            title=task_context['title'],
            description=task_context['description'],
            complexity_score=complexity
        ),
        mode=mode
    )

    if mode == ClarificationMode.FULL:
        return display_full_questions(questions, ...)
    else:
        return display_quick_questions(questions, timeout=15)
```

### Option B: Create task_work_orchestrator.py

Create a dedicated orchestrator similar to `task_review_orchestrator.py`:

```python
# installer/core/commands/lib/task_work_orchestrator.py

def execute_task_work(task_id: str, mode: str, flags: dict):
    """Main orchestrator for /task-work command."""

    # Phase 1.5: Load context
    task_context = load_task_context(task_id)

    # Phase 1.6: Clarifying Questions
    clarification = execute_clarification_phase(task_context, flags)

    # Phase 2: Implementation Planning (with clarification)
    plan = create_implementation_plan(task_context, clarification)

    # Phase 2.5: Architectural Review
    # ... continue with existing phases
```

### Option C: Enforce via Claude Instructions

Update `task-work.md` to explicitly require calling the Python module:

```markdown
#### Phase 1.6: Clarifying Questions

**EXECUTE** the following Python code to generate and display questions:

```python
from lib.clarification.generators.planning_generator import generate_planning_questions
questions = generate_planning_questions(task_context)
# Display questions and collect responses
```
```

## Recommended Approach

**Option A** if `phase_execution.py` is the actual execution path.
**Option B** if we want consistent orchestrator patterns across commands.

## Files to Modify

1. `installer/core/commands/lib/phase_execution.py` - Add Phase 1.6 call
2. OR create `installer/core/commands/lib/task_work_orchestrator.py`
3. `installer/core/commands/task-work.md` - Ensure documentation matches implementation

## Acceptance Criteria

- [x] `/task-work TASK-XXX` triggers clarification for complexity >= 3
- [x] `/task-work TASK-XXX --no-questions` skips clarification
- [x] `/task-work TASK-XXX --with-questions` forces clarification
- [x] `/task-work TASK-XXX --answers="1:Y 2:N"` uses inline answers
- [x] Clarification persists to task frontmatter
- [x] Clarification context passed to Phase 2 planning

## Test Cases

```bash
# Should ask questions (complexity 5)
/task-create "Add user authentication" complexity:5
/task-work TASK-XXX
# Expected: Phase 1.6 clarification questions displayed

# Should skip (trivial task)
/task-create "Fix typo" complexity:1
/task-work TASK-XXX
# Expected: Skip Phase 1.6, proceed to Phase 2

# Should skip with flag
/task-work TASK-XXX --no-questions
# Expected: No questions, direct to Phase 2

# Inline answers
/task-work TASK-XXX --answers="1:C 2:I"
# Expected: Use provided answers, no prompting
```

## Related

- TASK-CLQ-FIX-001: Task-review orchestrator integration (same pattern)
- `planning_generator.py`: Complete, has 7 question categories
- `task-work.md`: Documents Phase 1.6 that doesn't execute

## Estimated Effort

2-3 hours
