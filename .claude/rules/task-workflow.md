---
paths: tasks/**/*
---

# Task Workflow Patterns

Patterns for working with GuardKit task files.

## Task File Structure

### Frontmatter Format

```yaml
---
id: TASK-STE-007
title: Add rules structure to GuardKit .claude/
status: in_progress
created: 2025-12-13T13:00:00Z
updated: 2025-12-13T15:00:00Z
priority: high
tags: [rules-structure, guardkit, python-library]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 2
conductor_workspace: self-template-wave2-guardkit-rules
complexity: 5
depends_on:
  - TASK-STE-001
---
```

### Required Fields

- `id`: Task identifier (TASK-{prefix}-{hash} format)
- `title`: Human-readable task title
- `status`: Current state (backlog, in_progress, in_review, completed, blocked)
- `created`: ISO 8601 timestamp
- `priority`: low, medium, high

### Optional Fields

- `updated`: Last modification timestamp
- `tags`: Array of searchable tags
- `parent_task`: Parent task ID for subtasks
- `implementation_mode`: task-work, direct, manual
- `wave`: Parallel execution wave number
- `conductor_workspace`: Workspace name for parallel development
- `complexity`: 1-10 complexity score
- `depends_on`: Array of dependency task IDs

## Task ID Format

```
TASK-{prefix}-{hash}

Examples:
- TASK-A3F2          (simple hash)
- TASK-E01-A3F2      (with epic prefix)
- TASK-STE-007       (feature prefix)
- TASK-FIX-B2C4      (bug fix prefix)
- TASK-E01-A3F2.1    (subtask)
```

## Directory Organization

```
tasks/
├── backlog/           # New tasks, not started
├── in_progress/       # Active development
├── in_review/         # Passed quality gates
├── blocked/           # Failed tests or gates
├── completed/         # Finished and archived
└── design_approved/   # Design approved (design-first workflow)
```

## Status Transitions

```
BACKLOG
   ├── (task-work) ──────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                            ↓              ↓
   │                        BLOCKED        BLOCKED
   │
   └── (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (--implement-only) ─→ IN_PROGRESS
```

## Task Content Sections

### Standard Sections

```markdown
# Task: {title}

## Description
Brief description of what needs to be done.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Implementation Notes
Technical notes and context for implementation.

## Notes
Additional context, references, decisions made.
```

## Feature Folder Structure

For multi-task features, use a feature folder:

```
tasks/backlog/feature-name/
├── README.md                    # Feature overview
├── IMPLEMENTATION-GUIDE.md      # Wave breakdown, parallel execution
├── TASK-FN-001-subtask-one.md   # Individual subtask
├── TASK-FN-002-subtask-two.md   # Individual subtask
└── TASK-FN-003-subtask-three.md # Individual subtask
```

### Feature README Format

```markdown
# Feature: {Feature Name}

## Overview
Brief description of the feature.

## Subtasks
| Task ID | Title | Mode | Wave |
|---------|-------|------|------|
| TASK-FN-001 | Subtask one | task-work | 1 |
| TASK-FN-002 | Subtask two | direct | 1 |
| TASK-FN-003 | Subtask three | task-work | 2 |

## Dependencies
- External dependencies
- Internal dependencies

## Acceptance Criteria
- [ ] Overall feature criteria
```

## Moving Tasks Between States

When moving tasks, update the frontmatter:

```yaml
status: in_progress
updated: 2025-12-13T15:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
```
