---
id: TASK-FIX-AB01
title: Add context parameter to AgentInvoker.invoke_player()
status: completed
created: 2026-02-05T17:00:00Z
updated: 2026-02-05T18:05:00Z
completed: 2026-02-05T18:05:00Z
priority: critical
tags: [autobuild, bugfix, blocking]
parent_review: TASK-REV-5796
task_type: bugfix
complexity: 2
implementation_mode: direct
---

# Task: Add context parameter to AgentInvoker.invoke_player()

## Problem Statement

TASK-GR6-006 (Job-Specific Context Retrieval) was partially integrated. The call site at `guardkit/orchestrator/autobuild.py:2030` passes `context=context_prompt`, but `AgentInvoker.invoke_player()` at `guardkit/orchestrator/agent_invoker.py:592` does not accept a `context` parameter.

This causes `TypeError: AgentInvoker.invoke_player() got an unexpected keyword argument 'context'` on every Player invocation, blocking ALL AutoBuild task execution.

## Acceptance Criteria

- [x] `invoke_player()` method signature updated to accept `context: str = ""` parameter
- [x] Context value propagated to Player prompt/requirements within the method body
- [x] Existing tests still pass (no regression)
- [x] Manual verification: `invoke_player()` no longer raises TypeError when called with `context=`

## Implementation Notes

### Files to modify

1. `guardkit/orchestrator/agent_invoker.py` - Add `context: str = ""` to `invoke_player()` signature at line 592
2. Within the method body, propagate `context` to the Player's prompt construction (prepend to requirements or pass as separate system context)

### Key consideration

The `context` parameter contains Graphiti-retrieved role constraints, quality gates, and turn states. It should be included in the Player's prompt but kept separate from the core `requirements` to maintain clean prompt structure.
