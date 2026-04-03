# Feature: Register python-library and nats-asyncio-service as Builtin Templates

## Problem Statement

Two templates created via `/template-create` as part of the Dark Factory initiative need to be promoted from user-local (`~/.agentecflow/templates/`) to builtin (`installer/core/templates/`). The nats-asyncio-service template is near-ready with minor metadata fixes. The python-library template has critical issues: its manifest, settings, and CLAUDE.md were incorrectly generated as JavaScript instead of Python.

## Solution Approach

1. Fix metadata for both templates (nats-asyncio-service: minor; python-library: major rework)
2. Copy both templates to `installer/core/templates/`
3. Update all registration points (init.py, CLAUDE.md, install.sh)
4. Enhance agents with `/agent-enhance --hybrid`
5. Verify `guardkit init` works end-to-end for both

## Parent Review

- **Review Task**: TASK-REV-DF07
- **Review Report**: `.claude/reviews/TASK-REV-DF07-review-report.md`
- **Architecture Score**: 45/100 (pre-fix)

## Subtasks

| ID | Title | Wave | Mode | Depends On |
|----|-------|------|------|------------|
| TASK-RBT-001 | Fix nats-asyncio-service metadata | 1 | task-work | - |
| TASK-RBT-002 | Fix python-library template | 1 | task-work | - |
| TASK-RBT-003 | Register both templates as builtins | 2 | task-work | 001, 002 |
| TASK-RBT-004 | Run agent-enhance on both templates | 3 | direct | 003 |
| TASK-RBT-005 | Verify guardkit init end-to-end | 3 | direct | 003 |
