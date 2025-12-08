---
id: TASK-CLQ-008
title: Integrate clarification into task-review.md
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: high
tags: [clarifying-questions, integration, task-review, wave-3]
complexity: 6
parent_feature: clarifying-questions
wave: 3
conductor_workspace: clarifying-questions-wave3-task-review
implementation_method: task-work
---

# Task: Integrate clarification into task-review.md

## Description

Integrate the clarification module into the `/task-review` command at two points:
1. **Phase 1**: Review scope clarification (Context A) - before analysis begins
2. **[I]mplement handler**: Implementation preferences (Context B) - when user chooses to implement

## Acceptance Criteria

- [ ] Add Context A clarification to Phase 1 (Review Scope)
  - [ ] REVIEW_FOCUS_QUESTIONS - What aspects to focus on
  - [ ] DEPTH_PREFERENCE_QUESTIONS - How deep to analyze
  - [ ] OUTPUT_FORMAT_QUESTIONS - What deliverables needed
  - [ ] CONSTRAINT_QUESTIONS - Time/resource limits
- [ ] Add Context B clarification to [I]mplement decision handler
  - [ ] APPROACH_PREFERENCE_QUESTIONS - Which option to follow
  - [ ] CONSTRAINT_QUESTIONS - Implementation limits
  - [ ] PARALLELIZATION_QUESTIONS - Parallel vs sequential
  - [ ] TESTING_DEPTH_QUESTIONS - TDD/standard/minimal
- [ ] Document command-line flags (--no-questions, --with-questions, --defaults)
- [ ] Add complexity gating for review clarification
- [ ] Update decision checkpoint to trigger Context B

## Technical Specification

### Context A: Review Scope Clarification

```markdown
## Phase 1: Load Context (with Clarification)

**Enhanced Workflow**:

1. Load task file and parse frontmatter
2. **NEW**: Detect if clarification needed
   - Decision mode tasks: Always ask (unless --no-questions)
   - Quick reviews: Skip clarification
   - Standard/Comprehensive: Ask scope questions
3. **NEW**: Present review scope questions
4. Record clarification decisions
5. Continue with analysis using clarified scope

### Review Scope Questions

| Category | Question | Options |
|----------|----------|---------|
| Focus | What should review focus on? | [A]ll aspects, [S]pecific area, [R]isks only |
| Depth | How thorough should analysis be? | [Q]uick scan, [S]tandard, [D]eep dive |
| Output | What deliverables needed? | [R]eport only, [T]asks generated, [B]oth |
| Constraints | Any review constraints? | [T]ime limit, [S]cope limit, [N]one |

### Example Flow

```
/task-review TASK-b2c4 --mode=decision

Phase 1: Loading context...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SCOPE CLARIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Review Focus
    What aspects should this review focus on?

    [A]ll aspects - Comprehensive analysis
    [S]pecific area - Focus on particular concern (DEFAULT)
    [R]isks only - Risk assessment focus

    Your choice [A/S/R]: S
    Specify area: Authentication flow

Q2. Review Depth
    How thorough should the analysis be?

    [Q]uick - Initial assessment (15-30 min)
    [S]tandard - Regular review (1-2 hours) (DEFAULT)
    [D]eep - Comprehensive audit (4-6 hours)

    Your choice [Q/S/D]: S

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 2 decisions - proceeding with review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Analyzing with focus: Authentication flow...
```
```

### Context B: Implementation Preferences

```markdown
## Decision Checkpoint Enhancement

When user selects [I]mplement at the decision checkpoint:

1. **NEW**: Present implementation preference questions
2. Collect preferences for:
   - Which recommended approach to follow
   - Implementation constraints
   - Parallelization preference
   - Testing depth
3. Pass preferences to subtask creation
4. Generate subtasks with preferences applied

### Implementation Preference Questions

| Category | Question | Options |
|----------|----------|---------|
| Approach | Which approach to follow? | [1-3] Options from review, [R]ecommended |
| Constraints | Any implementation constraints? | [T]ime, [R]esource, [N]one, [C]ustom |
| Parallelization | How to execute tasks? | [M]aximize parallel, [S]equential, [D]etect |
| Testing | Testing depth for subtasks? | [F]ull TDD, [S]tandard, [M]inimal, [D]efault |

### Example Flow

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Options:
  [A]ccept - Approve findings
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation tasks
  [C]ancel - Discard review

Your choice: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The review identified 3 recommended approaches:

Q1. Which approach should subtasks follow?

    [1] JWT with refresh tokens (Recommended)
    [2] Session-based auth
    [3] OAuth 2.0 integration
    [R]ecommend for me

    Your choice [1/2/3/R]: 1

Q2. Parallelization preference?

    [M]aximize parallel - Use Conductor workspaces
    [S]equential - Simpler execution
    [D]etect automatically (DEFAULT)

    Your choice [M/S/D]: M

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Creating 5 subtasks with preferences:
  - Approach: JWT with refresh tokens
  - Execution: Parallel (3 Conductor workspaces)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```

### Integration Points

```python
# In task-review command implementation

from lib.clarification import (
    generate_review_questions,
    generate_implement_questions,
    display_questions_full,
)
from lib.clarification.core import ClarificationContext

def execute_task_review(task_id: str, mode: str, depth: str, flags: dict):
    # Phase 1: Context Loading with Clarification
    task = load_task(task_id)

    review_clarification = None
    if not flags.get('no_questions') and mode == 'decision':
        questions = generate_review_questions(task, mode, depth)
        if flags.get('defaults'):
            review_clarification = apply_defaults(questions)
        else:
            review_clarification = display_questions_full(questions)

    # Phase 2-4: Execute Review (with clarified scope)
    findings = execute_review(task, mode, depth, review_clarification)

    # Phase 5: Decision Checkpoint
    decision = present_decision_checkpoint(findings)

    if decision == 'implement':
        # Context B: Implementation Preferences
        impl_clarification = None
        if not flags.get('no_questions'):
            impl_questions = generate_implement_questions(
                findings,
                num_subtasks=len(findings.recommendations),
                complexity=task.complexity
            )
            impl_clarification = display_questions_full(impl_questions)

        # Create subtasks with preferences
        create_implementation_subtasks(findings, impl_clarification)
```

## Files to Modify

1. `installer/global/commands/task-review.md` - Add clarification specifications
2. `installer/global/commands/lib/task_review_executor.py` (if exists) - Add integration

## Why /task-work Method

- Two integration points (Phase 1 + [I]mplement handler)
- Complex flow control between clarification contexts
- Quality gates needed for correct decision routing
- Higher complexity (6/10)

## Dependencies

- Wave 1: core.py, detection.py, display.py
- Wave 2: review_scope.py templates, implementation_prefs.py templates
- Wave 2: review_generator.py, implement_generator.py

## Related Tasks

- TASK-CLQ-007 (task-work integration - parallel)
- TASK-CLQ-009 (feature-plan integration - parallel)

## Reference

See [Review Report Section: Context A & B](./../../../.claude/reviews/TASK-REV-B130-review-report.md#context-a-review-scope-task-review-feature-plan).
