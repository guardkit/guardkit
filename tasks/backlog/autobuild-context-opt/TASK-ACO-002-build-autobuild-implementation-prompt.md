---
id: TASK-ACO-002
title: Build AutoBuild implementation prompt builder
task_type: feature
parent_review: TASK-REV-A781
feature_id: FEAT-ACO
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-ACO-001
status: pending
priority: high
---

# TASK-ACO-002: Build AutoBuild Implementation Prompt Builder

## Objective

Add `_build_autobuild_implementation_prompt()` method to `agent_invoker.py` that constructs a focused prompt for Player SDK sessions, replacing the current pattern of invoking `/task-work TASK-XXX --implement-only` as an SDK skill.

## Context

Currently, `_invoke_task_work_implement()` in `agent_invoker.py` creates an SDK session with:
```python
setting_sources=["user", "project"]  # Loads ~987KB
prompt = f"/task-work {task_id} --implement-only --mode={mode}"
```

This loads all 25 user commands (758KB) just so the SDK can resolve `/task-work` as a skill.

## Deliverables

### 1. New method: `_build_autobuild_implementation_prompt()`

**File**: `guardkit/orchestrator/agent_invoker.py`

The prompt must include:
- Task requirements (from task markdown file)
- Implementation execution protocol (loaded from `autobuild_execution_protocol.md` via `load_protocol()`)
- Report format specification (PLAYER_REPORT_SCHEMA)
- Coach feedback from previous turn (if applicable)
- Job-specific Graphiti context (if available)
- Turn context (approaching_limit, escape hatch)
- Development mode (TDD/BDD/standard)
- Documentation level constraints

### 2. Update `_invoke_task_work_implement()`

Change SDK session configuration:
```python
# BEFORE:
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # ~987KB
    ...
)
prompt = f"/task-work {task_id} --implement-only --mode={mode}"

# AFTER:
options = ClaudeAgentOptions(
    setting_sources=["project"],  # ~72KB
    ...
)
prompt = self._build_autobuild_implementation_prompt(
    task_id=task_id,
    mode=mode,
    documentation_level=documentation_level,
)
```

## Acceptance Criteria

- [ ] `_build_autobuild_implementation_prompt()` method exists in `agent_invoker.py`
- [ ] `setting_sources` changed to `["project"]` in `_invoke_task_work_implement()`
- [ ] Prompt output is compatible with `TaskWorkStreamParser` (existing regex-based parser)
- [ ] Player report JSON schema (PLAYER_REPORT_SCHEMA) is included in prompt
- [ ] `task_work_results.json` is still written for Coach validation
- [ ] Git change detection enrichment still works
- [ ] Coach feedback from previous turns is included when available
- [ ] Graphiti context is included when available
- [ ] No changes to interactive `/task-work` path (zero regression)

## Key Constraints

- The prompt must produce output compatible with `TaskWorkStreamParser`
- Player report JSON schema must remain identical
- Git change detection enrichment must still work
- `task_work_results.json` must still be written for Coach validation

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Add `_build_autobuild_implementation_prompt()`, update `_invoke_task_work_implement()` |

## Testing

- Unit test: Verify prompt contains all required sections
- Unit test: Verify `setting_sources=["project"]` in SDK options
- Integration test: Verify Player output is parseable by `TaskWorkStreamParser`
