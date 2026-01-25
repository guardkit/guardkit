---
id: TASK-DOC-20E9
title: "Update Feature-Build Documentation for Invocation Modes"
status: completed
created: 2026-01-25T20:35:00Z
updated: 2026-01-25T20:45:00Z
completed: 2026-01-25T20:45:00Z
priority: low
task_type: implementation
implementation_mode: direct
tags: [documentation, feature-build, autobuild, invocation-modes]
complexity: 2
parent_review: TASK-REV-FDF3
related_tasks:
  - TASK-REV-FDF3
  - TASK-FIX-C4D8
  - TASK-REV-C4D7
---

# Task: Update Feature-Build Documentation for Invocation Modes

## Overview

Update feature-build documentation to clarify the two invocation modes (direct SDK vs task-work delegation) and when each is used, based on learnings from TASK-REV-FDF3 success validation.

## Background

The feature-build command uses two distinct invocation paths for executing tasks:

1. **Direct SDK Mode**: Used when `implementation_mode=direct` in task frontmatter
   - Invokes Player via `_invoke_with_role` -> `_invoke_player_direct`
   - Uses `TASK_WORK_SDK_MAX_TURNS` (50) for SDK max turns
   - Faster for simple scaffolding tasks

2. **task-work Delegation Mode**: Default path
   - Invokes Player via `_invoke_task_work_implement`
   - Runs `/task-work TASK-XXX --implement-only`
   - Uses `TASK_WORK_SDK_MAX_TURNS` (50) for SDK max turns
   - Full task-work phases (planning, implementation, testing, review)

## Acceptance Criteria

- [x] Document the two invocation modes in feature-build.md
- [x] Explain when to use `implementation_mode: direct` in task frontmatter
- [x] Document the shared `TASK_WORK_SDK_MAX_TURNS` constant
- [x] Add examples showing both modes in a feature YAML
- [x] Reference the logging from FEAT-F392 success run as examples

## Files to Update

- `installer/core/commands/feature-build.md` - Main command documentation
- `docs/guides/autobuild-guide.md` (if exists) - Guide documentation

## Documentation Content to Add

### Section: Invocation Modes

```markdown
## Invocation Modes

Feature-build supports two task invocation modes:

### Direct SDK Mode

Use for simple scaffolding or file creation tasks that don't need full planning.

**Task frontmatter**:
```yaml
implementation_mode: direct
```

**Logs**:
```
INFO: Routing to direct Player path for TASK-XXX (implementation_mode=direct)
INFO: Invoking Player via direct SDK for TASK-XXX (turn 1)
```

**Use when**:
- Creating new files/directories
- Simple configuration changes
- Tasks with clear, atomic deliverables

### task-work Delegation Mode (Default)

Use for complex implementations requiring planning and full quality gates.

**Task frontmatter**:
```yaml
implementation_mode: task-work  # or omit (default)
```

**Logs**:
```
INFO: Invoking Player via task-work delegation for TASK-XXX (turn 1)
INFO: [TASK-XXX] Max turns: 50
```

**Use when**:
- Complex feature implementation
- Tasks requiring architectural decisions
- Tasks with multiple acceptance criteria
```

## Notes

This documentation update closes the loop on TASK-REV-FDF3 recommendations, ensuring future developers understand the invocation architecture.
