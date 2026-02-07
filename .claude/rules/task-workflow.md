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
parent_review: TASK-REV-a3f8  # Review that recommended this task
feature_id: FEAT-a3f8          # Feature grouping identifier
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
- `parent_review`: Review task ID that generated this task (format: TASK-REV-{hash})
- `feature_id`: Feature ID for multi-task features (format: FEAT-{hash})
- `implementation_mode`: task-work, direct
- `wave`: Parallel execution wave number
- `conductor_workspace`: Workspace name for parallel development
- `complexity`: 1-10 complexity score
- `depends_on`: Array of dependency task IDs

## Provenance Fields

| Field | Format | Set By | Purpose |
|-------|--------|--------|---------|
| `parent_review` | `TASK-REV-{hash}` | `/task-review` [I]mplement | Links to review that recommended this task |
| `feature_id` | `FEAT-{hash}` | `/feature-plan` | Groups related tasks under a feature |

Provenance enables traceability: feature idea → review → implementation → completion.

## Task ID Format

```
TASK-{prefix}-{hash}

Examples:
- TASK-A3F2          (simple hash)
- TASK-E01-A3F2      (with epic prefix)
- TASK-STE-007       (feature prefix)
- TASK-FIX-B2C4      (bug fix prefix)
- TASK-E01-A3F2.1    (subtask)
- TASK-REV-A3F2      (review task)
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

Multi-task features use `tasks/backlog/feature-name/` containing `README.md`, `IMPLEMENTATION-GUIDE.md`, and individual `TASK-FN-NNN-*.md` subtask files.

## Moving Tasks Between States

When moving tasks, update the frontmatter:

```yaml
status: in_progress
updated: 2025-12-13T15:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
```

## Task Work Intensity Levels

| Level | Use Case | Duration | Coverage |
|-------|----------|----------|----------|
| `minimal` / `--micro` | Typos, cosmetic | 3-5 min | No coverage |
| `light` | Simple features | 10-15 min | 70% |
| `standard` (default) | Most tasks | 15-30 min | 80% + arch review |
| `strict` | Security, APIs | 30-60+ min | 85% + security scan |

**See**: `installer/core/commands/task-work.md` for full phase execution details per level.
