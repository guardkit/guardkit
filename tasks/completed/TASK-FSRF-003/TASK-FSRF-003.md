---
id: TASK-FSRF-003
title: "Update CLAUDE.md with /feature-spec command entry"
status: completed
task_type: feature
parent_review: TASK-REV-FCA5
feature_id: FEAT-FSRF
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T13:00:00Z
completed: 2026-02-22T13:00:00Z
completed_location: tasks/completed/TASK-FSRF-003/
priority: medium
tags: [documentation, claude-md, feature-spec]
complexity: 1
wave: 1
implementation_mode: direct
dependencies: []
tests_required: false
---

# Task: Update CLAUDE.md with /feature-spec command entry

## Description

The root `CLAUDE.md` lists all available commands in the "Essential Commands" section but does not include `/feature-spec`. Add it to the appropriate section so new users discover it.

## Fix

Add `/feature-spec` to the BDD Workflow section or create a new "Specification" subsection under Essential Commands:

```markdown
### BDD / Specification Workflow
```bash
/feature-spec "description" [--from file.md] [--output dir/] [--auto] [--stack name] [--context file.md]
```
```

## Acceptance Criteria

- [x] `/feature-spec` appears in CLAUDE.md Essential Commands
- [x] Command syntax and flags briefly described
- [x] Links to `docs/commands/feature-spec.md` for details

## Files to Change

- `CLAUDE.md`
