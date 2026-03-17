---
id: TASK-FIX-GC02
title: Update command specs to use graphiti-check wrapper
status: completed
created: 2026-03-17T12:00:00Z
updated: 2026-03-17T13:00:00Z
completed: 2026-03-17T13:05:00Z
completed_location: tasks/completed/TASK-FIX-GC02/
priority: high
tags: [graphiti, commands, specs, fix]
parent_review: TASK-REV-4219
feature_id: FEAT-GC42
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, documentation-only changes verified"
---

# Task: Update command specs to use graphiti-check wrapper

## Description

Update command specifications and rules that reference `python -m installer.core.commands.lib.graphiti_check` to use the `graphiti-check` wrapper instead (or the explicit guardkit venv Python path).

This ensures the module invocation path also resolves to the correct Python environment.

## Files Modified

- `installer/core/commands/task-work.md` — lines 1712-1713, 1741-1743
- `.claude/rules/graphiti-knowledge.md` — line 13

## Current (Broken)

```bash
python -m installer.core.commands.lib.graphiti_check --status --quiet
```

## Target

```bash
graphiti-check --status --quiet
```

Or if the wrapper is not guaranteed to be on PATH:
```bash
~/.agentecflow/bin/graphiti-check --status --quiet
```

## Acceptance Criteria

- [x] `task-work.md` uses wrapper or explicit venv Python for graphiti check
- [x] `graphiti-knowledge.md` uses wrapper or explicit venv Python
- [x] No remaining references to bare `python -m installer.core.commands.lib.graphiti_check`

## Test Execution Log

### Micro-Task Execution (2026-03-17)

**Changes Made:**

1. `installer/core/commands/task-work.md`:
   - Line 1713: `python -m installer.core.commands.lib.graphiti_check --status --quiet` → `graphiti-check --status --quiet`
   - Line 1743: `python -m installer.core.commands.lib.graphiti_check \` → `graphiti-check \`
   - Removed unnecessary `cd {project_root}` directives (wrapper handles environment)
   - Updated descriptive text from "Run the graphiti check script from the project root directory" to "Run the graphiti check wrapper"

2. `.claude/rules/graphiti-knowledge.md`:
   - Line 13: Updated to `graphiti-check --status` with note about wrapper location

**Verification:**
- Zero remaining references to bare `python -m installer.core.commands.lib.graphiti_check` in either target file
- Note: `graphiti_check.py` module's own docstring still references `python -m` for direct module usage — this is intentional (developer documentation)
