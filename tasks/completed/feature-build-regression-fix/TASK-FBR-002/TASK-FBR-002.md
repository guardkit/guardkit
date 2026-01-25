---
id: TASK-FBR-002
title: Propagate max_turns parameter to SDK invocation layer
status: completed
task_type: bug-fix
implementation_mode: task-work
priority: high
complexity: 3
wave: 1
parallel_group: feature-build-regression-fix-wave1-2
created: 2026-01-25T15:35:00Z
completed: 2026-01-25T16:15:00Z
parent_review: TASK-REV-FB
feature_id: FEAT-FBR
tags:
  - parameter-propagation
  - sdk-integration
  - autobuild
  - configuration
dependencies: []
---

# TASK-FBR-002: Propagate max_turns Parameter to SDK Invocation

## Problem Statement

The CLI `--max-turns` parameter is correctly received by `FeatureOrchestrator` and `AutoBuildOrchestrator`, but is ignored when invoking the Claude Agent SDK. Instead, a hardcoded value of 50 is used.

**Evidence from logs**:
```
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-FHE (max_turns=10, ...)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FHE-001] Max turns: 50
```

## Root Cause

1. `AgentInvoker` is instantiated without passing `max_turns_per_agent`
2. `_invoke_via_task_work_delegation` uses hardcoded `max_turns=50`

## Implementation

### Step 1: Pass max_turns_per_agent to AgentInvoker

Update all `AgentInvoker` instantiation sites in `autobuild.py`:

**Location 1** (line 712-717):
```python
self._agent_invoker = AgentInvoker(
    worktree_path=worktree.path,
    max_turns_per_agent=self.max_turns,  # ADD THIS
    development_mode=self.development_mode,
    sdk_timeout_seconds=self.sdk_timeout,
    use_task_work_delegation=True,
)
```

**Location 2** (line 731-736):
```python
self._agent_invoker = AgentInvoker(
    worktree_path=worktree.path,
    max_turns_per_agent=self.max_turns,  # ADD THIS
    development_mode=self.development_mode,
    sdk_timeout_seconds=self.sdk_timeout,
    use_task_work_delegation=True,
)
```

**Location 3** (line 2125-2130):
```python
self._agent_invoker = AgentInvoker(
    worktree_path=worktree.path,
    max_turns_per_agent=self.max_turns,  # ADD THIS
    development_mode=self.development_mode,
    sdk_timeout_seconds=self.sdk_timeout,
    use_task_work_delegation=True,
)
```

### Step 2: Use max_turns_per_agent in SDK Invocation

Update `_invoke_via_task_work_delegation` at `agent_invoker.py:2260`:

```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=self.max_turns_per_agent,  # USE INSTANCE VARIABLE
    setting_sources=["user", "project"],
)
```

### Step 3: Update task_work_interface.py (if needed)

Check if `task_work_interface.py:357` also has hardcoded max_turns and update similarly.

## Acceptance Criteria

- [x] `AgentInvoker` receives `max_turns_per_agent` from `AutoBuildOrchestrator`
- [x] SDK invocation uses configured `max_turns_per_agent` value
- [x] Log shows correct max_turns matching CLI parameter
- [x] `--max-turns 10` results in `Max turns: 10` in logs
- [x] Unit tests verify parameter propagation

## Implementation Notes (TASK-FBR-002)

### Changes Made

1. **autobuild.py** - Updated 3 AgentInvoker instantiation sites:
   - Line 712-717: Pass `max_turns_per_agent=self.max_turns`
   - Line 731-736: Pass `max_turns_per_agent=self.max_turns`
   - Line 2127-2132: Pass `max_turns_per_agent=self.max_turns`

2. **agent_invoker.py** - Updated SDK invocation:
   - Line 2260: Changed from `max_turns=50` to `max_turns=self.max_turns_per_agent`

3. **task_work_interface.py** - No change needed:
   - This file is used for design phases (`--design-only`), not implementation
   - Design phases have different turn requirements than implementation
   - The hardcoded 50 is appropriate for design phase duration

### Tests Updated

1. **test_autobuild_orchestrator.py**:
   - `test_setup_phase_initializes_agent_invoker_with_delegation` now verifies `max_turns_per_agent` is passed

2. **test_agent_invoker.py**:
   - `test_invoke_task_work_implement_success` now expects `max_turns=30` (default) instead of hardcoded 50

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Pass `max_turns_per_agent` in 3 AgentInvoker instantiations |
| `guardkit/orchestrator/agent_invoker.py` | Use `self.max_turns_per_agent` instead of hardcoded 50 |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Same change if applicable |

## Test Plan

1. Run `/feature-build TASK-XXX --max-turns 10`
2. Verify log shows `[TASK-XXX] Max turns: 10`
3. Run unit test for `AgentInvoker` configuration
4. Verify existing tests still pass

## Related

- **Parent Review**: TASK-REV-FB
- **Related Location**: `agent_invoker.py:2260`
