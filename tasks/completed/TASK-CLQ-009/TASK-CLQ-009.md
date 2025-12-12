---
id: TASK-CLQ-009
title: Integrate clarification into feature-plan.md
status: completed
created: 2025-12-08T14:00:00Z
updated: 2025-12-12T00:00:00Z
completed: 2025-12-12T00:00:00Z
completed_location: tasks/completed/TASK-CLQ-009/
priority: medium
tags: [clarifying-questions, integration, feature-plan, wave-3]
complexity: 3
parent_feature: clarifying-questions
wave: 3
conductor_workspace: clarifying-questions-wave3-feature-plan
implementation_method: direct
organized_files: ["TASK-CLQ-009.md"]
---

# Task: Integrate clarification into feature-plan.md

## Description

Update the `/feature-plan` command documentation to show how clarification flows through its orchestrated workflow. Since feature-plan uses task-review under the hood, clarification is mostly inherited - this task documents that flow and adds any feature-plan-specific configuration.

## Implementation Status

**Complete** - All clarification documentation has been added to feature-plan.md.

### Completed
- ✅ Command-line flags documented in feature-plan.md (lines 13-18)
- ✅ Clarification logic implemented in task-review.md (which feature-plan calls)
- ✅ CLAUDE.md has "Three Clarification Contexts" table referencing feature-plan
- ✅ Added "Clarification Integration" section to feature-plan.md with:
  - Phase flow diagram showing Context A and Context B integration points
  - Context A (review scope) documentation
  - Context B (implementation prefs) documentation
  - Full clarification flow example with both REVIEW SCOPE and IMPLEMENTATION PREFERENCES output
  - Skip clarification example with --no-questions
  - Force clarification example with --with-questions
  - Inline answers example for CI/CD automation
  - Clarification Propagation section with pseudo-code
  - Clarification Decision Persistence documentation
  - Benefits summary

## Acceptance Criteria

- [x] Add command-line flag documentation
  - [x] `--no-questions` - Propagated to task-review
  - [x] `--with-questions` - Force clarification
  - [x] `--defaults` - Use defaults throughout
  - [x] `--answers="..."` - Inline answers for automation
- [x] Document clarification flow in feature-plan.md
  - [x] Add phase flow diagram showing Context A and Context B integration points
  - [x] Show how Context A (review scope) applies during review phase
  - [x] Show how Context B (implementation prefs) applies at [I]mplement
- [x] Add examples showing clarification in feature-plan workflow
  - [x] Full clarification flow example with "REVIEW SCOPE CLARIFICATION" output
  - [x] Full clarification flow example with "IMPLEMENTATION PREFERENCES" output
  - [x] Skip clarification example with --no-questions
- [x] Document how clarification decisions flow to subtask generation
  - [x] Add "Clarification Propagation" section with pseudo-code

## Technical Specification

### Clarification Flow in Feature-Plan

```markdown
## Clarification Integration

`/feature-plan` orchestrates `/task-review` under the hood, so clarification questions flow automatically:

### Phase Flow

```
/feature-plan "add authentication"
        │
        ▼
┌─────────────────────────────┐
│ 1. Create Review Task       │
│    (auto-generated)         │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 2. Execute Task Review      │◀── Context A: Review Scope
│    with --mode=decision     │    (What to analyze?)
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 3. Decision Checkpoint      │
│    [A]ccept/[R]evise/       │
│    [I]mplement/[C]ancel     │
└─────────────────────────────┘
        │
        ▼ (if [I]mplement)
┌─────────────────────────────┐
│ 4. Implementation Prefs     │◀── Context B: Implementation
│    (approach, parallel,     │    (How to implement?)
│    testing depth)           │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 5. Generate Feature         │
│    Structure with subtasks  │
│    (uses clarification)     │
└─────────────────────────────┘
```

### Command-Line Flags

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip all clarification (propagates to task-review) |
| `--with-questions` | Force clarification even for simple features |
| `--defaults` | Use defaults without prompting |
| `--answers="..."` | Inline answers for automation |

### Example: Full Clarification Flow

```bash
/feature-plan "add user authentication"

Creating review task: TASK-REV-a3f8
Executing review...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SCOPE CLARIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Review Focus
    What aspects should this review focus on?

    [A]ll aspects
    [S]pecific area (DEFAULT)
    [R]isks only

    Your choice [A/S/R]: A

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Review executes with clarified scope...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete. Found 3 approaches:
1. JWT with refresh tokens (Recommended)
2. Session-based auth
3. OAuth 2.0 integration

Options:
  [A]ccept - Approve findings only
  [R]evise - Request deeper analysis
  [I]mplement - Create feature structure
  [C]ancel - Discard review

Your choice: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Which approach should subtasks follow?
    [1] JWT with refresh tokens (Recommended)
    [2] Session-based auth
    [3] OAuth 2.0 integration
    [R]ecommend for me

    Your choice: 1

Q2. Parallelization preference?
    [M]aximize parallel
    [S]equential
    [D]etect (DEFAULT)

    Your choice: M

Q3. Testing depth?
    [F]ull TDD
    [S]tandard (DEFAULT)
    [M]inimal
    [D]efault based on complexity

    Your choice: S

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generating feature structure...

✅ Created: tasks/backlog/user-authentication/
├── README.md
├── IMPLEMENTATION-GUIDE.md (3 parallel waves)
├── TASK-AUTH-001-setup-jwt-middleware.md
├── TASK-AUTH-002-create-user-model.md
├── TASK-AUTH-003-implement-login-endpoint.md
├── TASK-AUTH-004-implement-refresh-tokens.md
└── TASK-AUTH-005-add-auth-tests.md

Subtasks configured with:
  - Approach: JWT with refresh tokens
  - Execution: Parallel (Conductor workspaces assigned)
  - Testing: Standard mode
```

### Example: Skip Clarification

```bash
/feature-plan "add dark mode" --no-questions

Creating review task: TASK-REV-b4c5
Executing review... (skipping clarification)

[Review executes with defaults...]

Decision: [I]mplement (skipping preferences)

Generating feature structure with defaults...

✅ Created: tasks/backlog/dark-mode/
```

### Clarification Propagation

When `/feature-plan` calls `/task-review`:

```python
# Pseudo-code for feature-plan orchestration
def execute_feature_plan(description: str, flags: dict):
    # Create review task
    task_id = create_review_task(description)

    # Execute task-review with propagated flags
    review_flags = {
        'no_questions': flags.get('no_questions'),
        'with_questions': flags.get('with_questions'),
        'defaults': flags.get('defaults'),
        'answers': flags.get('answers'),
    }

    # Task-review handles Context A and Context B clarification
    result = execute_task_review(
        task_id,
        mode='decision',
        depth='standard',
        flags=review_flags
    )

    # Generate feature structure using clarification context
    if result.decision == 'implement':
        generate_feature_structure(
            result.findings,
            result.clarification  # Contains both Context A & B decisions
        )
```
```

## Files to Modify

1. `installer/core/commands/feature-plan.md` - Add clarification documentation

## Why Direct Implementation

- Primarily documentation updates
- Clarification logic is inherited from task-review
- No new algorithms or complex integration
- Lower complexity (4/10)

## Dependencies

- Wave 1: core.py (ClarificationContext dataclass)
- Wave 3: TASK-CLQ-008 (task-review integration must exist)

## Related Tasks

- TASK-CLQ-007 (task-work integration - parallel)
- TASK-CLQ-008 (task-review integration - parallel, dependency)

## Reference

See [Review Report Section: Feature-Plan Integration](./../../../.claude/reviews/TASK-REV-B130-review-report.md#feature-plan-integration).
