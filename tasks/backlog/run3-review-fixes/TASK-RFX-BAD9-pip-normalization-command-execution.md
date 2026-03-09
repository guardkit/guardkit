---
id: TASK-RFX-BAD9
title: Normalize pip to sys.executable -m pip in command execution
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: high
complexity: 2
wave: 1
implementation_mode: direct
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, command-execution, environment]
dependencies: []
---

# Task: Normalize pip to sys.executable -m pip in Command Execution

## Description

In `_execute_command_criteria()` (autobuild.py ~2878-2886), normalize bare `pip` commands to `sys.executable -m pip` before subprocess execution. This directly eliminates the VID-001 class of runtime criteria failures where `/opt/homebrew/bin/pip` is broken but `python3 -m pip` works.

Also consider injecting virtualenv PATH if `.venv/bin/` exists in the worktree.

## Root Cause

Runtime criteria uses bare `pip` which resolves to `/opt/homebrew/bin/pip` (broken Homebrew shim). The environment bootstrap uses `sys.executable -m pip` which works. This PATH inconsistency causes false runtime criteria failures.

## Acceptance Criteria

- [ ] `_execute_command_criteria()` normalizes `pip install ...` to `{sys.executable} -m pip install ...`
- [ ] `_execute_command_criteria()` normalizes `pip` to `{sys.executable} -m pip` for all pip subcommands
- [ ] Normalization is logged at INFO level when applied
- [ ] If `.venv/bin/` exists in the worktree, PATH is prepended in subprocess env
- [ ] Unit tests cover pip normalization with various command patterns
- [ ] Unit tests cover virtualenv PATH injection

## Implementation Notes

```python
import re, sys

# In _execute_command_criteria(), before subprocess.run():
cmd = criterion.extracted_command
if re.match(r'^pip\s', cmd):
    cmd = f"{sys.executable} -m pip {cmd[4:]}"
    logger.info("Normalized 'pip' to '%s -m pip'", sys.executable)
```
