---
id: TASK-CLQ-007
title: Integrate clarification into task-work.md
status: completed
created: 2025-12-08T14:00:00Z
updated: 2025-12-10T00:00:00Z
completed: 2025-12-10T00:00:00Z
completed_location: tasks/completed/TASK-CLQ-007/
priority: high
tags: [clarifying-questions, integration, task-work, wave-3]
complexity: 6
parent_feature: clarifying-questions
wave: 3
conductor_workspace: lagos
implementation_method: task-work
organized_files: [
  "TASK-CLQ-007.md",
  "completion-report.md"
]
---

# Task: Integrate clarification into task-work.md

## Description

Integrate the clarification module into the `/task-work` command by adding Phase 1.5 (Clarifying Questions) between context loading and implementation planning. This is the primary integration point for Context C (Implementation Planning) questions.

## Acceptance Criteria

- [ ] Add Phase 1.5 specification to task-work.md after Phase 1
- [ ] Document complexity gating thresholds (skip 1-2, quick 3-4, full 5+)
- [ ] Add command-line flag documentation:
  - [ ] `--no-questions` - Skip clarification entirely
  - [ ] `--with-questions` - Force clarification even for simple tasks
  - [ ] `--defaults` - Use defaults without prompting
  - [ ] `--answers="1:Y 2:N 3:JWT"` - Inline answers for automation
- [ ] Update Phase 2 to accept clarification context
- [ ] Add examples showing clarification flow
- [ ] Document timeout behavior (15s for quick mode)

## Technical Specification

### Phase 1.5 Specification

```markdown
## Phase 1.5: Clarifying Questions (Complexity-Gated)

**Purpose**: Ask targeted clarifying questions before making assumptions in implementation planning.

**Trigger**: After Phase 1 (Context Loading), before Phase 2 (Implementation Planning)

**Complexity Gating**:
| Complexity | Behavior |
|------------|----------|
| 1-2 (Trivial) | Skip - proceed directly to Phase 2 |
| 3-4 (Simple) | Quick mode - 15s timeout, then use defaults |
| 5+ (Complex) | Full mode - blocking, wait for user response |

### Workflow

1. **Detect Ambiguity**
   - Analyze task description for scope ambiguity
   - Check for technology choices not specified
   - Identify trade-offs not addressed

2. **Generate Questions**
   - Select relevant questions from templates
   - Customize based on task context
   - Limit to 3-5 questions maximum

3. **Present to User**
   - Display questions with options
   - Show defaults and rationale
   - Accept answers or timeout (quick mode)

4. **Record Decisions**
   - Store in ClarificationContext
   - Pass to Phase 2 for planning
   - Persist to task frontmatter

### Command-Line Flags

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip Phase 1.5 entirely |
| `--with-questions` | Force Phase 1.5 even for complexity 1-2 |
| `--defaults` | Use all defaults without prompting |
| `--answers="..."` | Provide answers inline (CI/CD automation) |

### Example Flow

```
/task-work TASK-a3f8

Phase 1: Loading context...
Phase 1.5: Clarifying Questions (complexity: 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CLARIFYING QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Implementation Scope
    How comprehensive should this implementation be?

    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases

    Your choice [M/S/C]: S

Q2. Testing Approach
    What testing strategy?

    [U]nit tests only
    [I]ntegration tests included (DEFAULT)
    [F]ull coverage (unit + integration + e2e)

    Your choice [U/I/F]: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 2 decisions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Planning implementation with clarifications...
```
```

### Integration Points

```python
# In task-work command implementation

from lib.clarification import (
    ClarificationContext,
    generate_planning_questions,
    display_questions_full,
    display_questions_quick,
)
from lib.clarification.detection import detect_ambiguity_level

def execute_task_work(task_id: str, flags: dict):
    # Phase 1: Context Loading
    task = load_task(task_id)
    context = load_project_context()

    # Phase 1.5: Clarifying Questions
    clarification = None
    if not flags.get('no_questions'):
        ambiguity = detect_ambiguity_level(task, context)
        complexity = task.complexity

        if flags.get('with_questions') or complexity >= 3:
            questions = generate_planning_questions(task, context, ambiguity)

            if flags.get('answers'):
                clarification = parse_inline_answers(flags['answers'], questions)
            elif flags.get('defaults'):
                clarification = apply_defaults(questions)
            elif complexity >= 5:
                clarification = display_questions_full(questions)
            else:
                clarification = display_questions_quick(questions, timeout=15)

    # Phase 2: Implementation Planning (with clarification context)
    plan = create_implementation_plan(task, context, clarification)

    # ... continue with phases 3-5.5
```

## Files to Modify

1. `installer/global/commands/task-work.md` - Add Phase 1.5 specification
2. `installer/global/commands/lib/task_work_executor.py` (if exists) - Add integration code

## Why /task-work Method

- Core integration point with highest complexity
- Needs quality gates for correct flag handling
- Multiple decision points in implementation
- Architectural review important for Phase 1.5 placement

## Dependencies

- Wave 1: core.py, detection.py, display.py
- Wave 2: implementation_planning.py templates, planning_generator.py

## Related Tasks

- TASK-CLQ-008 (task-review integration - parallel)
- TASK-CLQ-009 (feature-plan integration - parallel)

## Reference

See [Review Report Section: Context C: Implementation Planning](./../../../.claude/reviews/TASK-REV-B130-review-report.md#context-c-implementation-planning-task-work-phase-15).
