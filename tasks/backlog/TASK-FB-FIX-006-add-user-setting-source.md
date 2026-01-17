---
id: TASK-FB-FIX-006
title: "Add 'user' to SDK setting_sources for skill loading"
status: backlog
created: 2026-01-11T18:30:00Z
priority: critical
tags: [feature-build, sdk, skill-loading, critical-fix]
complexity: 2
parent_review: TASK-REV-FB06
implementation_mode: direct
---

# TASK-FB-FIX-006: Add 'user' to SDK setting_sources

## Problem Statement

The SDK invocation in `TaskWorkInterface._execute_via_sdk()` uses `setting_sources=["project"]`, which only loads settings from the project's `.claude/` directory. This misses user-level skills at `~/.claude/commands/` where GuardKit's `/task-work` skill is installed.

**Result**: The model can't invoke `/task-work --design-only` because the skill isn't loaded.

## Root Cause

```python
# Current (line 344)
setting_sources=["project"],  # Only loads from .claude/ in worktree
```

Skills are installed at `~/.claude/commands/` (symlinked from `~/.agentecflow/commands/`), which requires the `"user"` setting source.

## Solution

Change line 344 in `guardkit/orchestrator/quality_gates/task_work_interface.py`:

```python
# From:
setting_sources=["project"],  # Load CLAUDE.md from worktree

# To:
setting_sources=["user", "project"],  # Load skills from user AND project
```

## Acceptance Criteria

- [x] Change `setting_sources=["project"]` to `setting_sources=["user", "project"]`
- [ ] Add debug logging for loaded skills (optional)
- [ ] Run feature-build and verify SDK executes more than 1 turn
- [ ] Verify plan file is created

## Files to Modify

1. `guardkit/orchestrator/quality_gates/task_work_interface.py` (line 344)

## Risk Assessment

- **Risk Level**: Low
- **Change Size**: 1 line
- **Regression Risk**: Minimal - only adds more settings loading

## Verification

After fix, run:
```bash
cd /path/to/test/repo
guardkit autobuild task TASK-XXX --verbose
```

Expected:
- SDK should execute multiple turns (not just 1)
- Should see "Tool invoked: Skill" in logs
- Plan file should be created

## Notes

This is a simple, high-confidence fix based on official SDK documentation:

> "You must specify `settingSources: ['user', 'project']` (TypeScript) or `setting_sources=["user", "project"]` (Python) to load Skills from the filesystem."

Source: https://platform.claude.com/docs/en/agent-sdk/skills
