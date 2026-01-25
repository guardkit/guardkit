---
id: TASK-PLD-003
title: Update feature-build CLI Help Text
status: completed
priority: low
complexity: 4
implementation_mode: task-work
parallel_group: wave-2
conductor_workspace: preloop-docs-wave2-1
tags: [cli, documentation, preloop]
parent_review: TASK-REV-PL01
completed_date: 2026-01-13
---

# Update feature-build CLI Help Text

## Description

Update the CLI help text for `guardkit autobuild feature` and `guardkit autobuild task` commands to include notes about pre-loop behavior and defaults.

## Requirements

### Update `guardkit autobuild feature --help`

Add a note after the `--enable-pre-loop` flag description:

```
--enable-pre-loop    Enable design phase (Phases 1.6-2.8) before Player-Coach loop.
                     NOTE: Disabled by default for feature-build because tasks from
                     /feature-plan already have detailed specs. Enable for tasks
                     needing architectural design. Adds 60-90 min per task.
                     See: docs/guides/guardkit-workflow.md#pre-loop-decision-guide
```

### Update `guardkit autobuild task --help`

Add a note after the `--no-pre-loop` flag description:

```
--no-pre-loop        Skip design phase (Phases 1.6-2.8) before Player-Coach loop.
                     NOTE: Enabled by default for task-build because standalone
                     tasks often need design clarification. Disable for simple
                     bug fixes or tasks with detailed implementation notes.
                     Saves 60-90 min. See: docs/guides/guardkit-workflow.md
```

### Files to Modify

- `guardkit/cli/autobuild.py` - Update Click option help strings

## Acceptance Criteria

- [x] `guardkit autobuild feature --help` shows pre-loop note
- [x] `guardkit autobuild task --help` shows no-pre-loop note
- [x] Help text references workflow documentation
- [x] Duration estimates included
- [x] Tests pass (if any CLI tests exist)

## Implementation Notes

This task requires code changes to the CLI module. Use task-work to ensure proper testing.

Locate the Click decorators for `--enable-pre-loop` and `--no-pre-loop` options and update their `help` strings.

## Testing

```bash
# Verify help text
guardkit autobuild feature --help | grep -A3 "enable-pre-loop"
guardkit autobuild task --help | grep -A3 "no-pre-loop"
```
