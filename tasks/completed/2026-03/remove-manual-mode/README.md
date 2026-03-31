# Feature: Remove Manual Implementation Mode

## Overview

Remove the `manual` implementation mode from GuardKit's task system. The `/task-work` command with complexity gating (0-10 scale) and `--micro`/`--intensity` flags already provides sufficient workflow adaptation for all task types.

## Problem Statement

The `manual` implementation mode:
1. Cannot be executed by AutoBuild (causes 25 retry failures)
2. Has unclear criteria for when to use it
3. Is redundant with complexity-based workflow adaptation
4. Creates a false distinction between "AI tasks" and "human tasks"

## Solution

Remove `manual` mode entirely:
- Keep only `task-work` (default) and `direct` modes
- Rely on complexity analysis (0-10) to adapt workflow intensity
- Use `--micro` or `--intensity=minimal` for trivial tasks

## Subtasks

| Task ID | Title | Mode | Wave | Status |
|---------|-------|------|------|--------|
| TASK-RMM-001 | Remove manual mode from implementation_mode_analyzer | task-work | 1 | ✅ COMPLETED |
| TASK-RMM-002 | Clean up manual references in agent_invoker | task-work | 1 | ✅ COMPLETED |
| TASK-RMM-003 | Convert existing manual tasks to task-work | direct | 2 | ✅ COMPLETED |
| TASK-RMM-004 | Update documentation | direct | 2 | ⏳ Backlog |

## Acceptance Criteria

- [x] `implementation_mode_analyzer.py` no longer assigns or recognizes `manual` mode
- [x] `agent_invoker.py` has no `manual` mode handling code (normalizes to task-work)
- [x] All existing tasks with `implementation_mode: manual` converted to `task-work`
- [ ] CLAUDE.md and command specs updated to reflect two-mode system
- [ ] Tests updated to remove manual mode test cases

## References

- TASK-GR-REV-001: AutoBuild failure analysis (identified the gap)
- TASK-GR-REV-002: Design review (this decision)
