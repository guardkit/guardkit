---
id: TASK-ACO-003
title: Build AutoBuild design prompt builder
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

# TASK-ACO-003: Build AutoBuild Design Prompt Builder

## Objective

Add `_build_autobuild_design_prompt()` method to `task_work_interface.py` that constructs a focused prompt for the AutoBuild design phase SDK session, replacing the current pattern of invoking `/task-work TASK-XXX --design-only` as an SDK skill.

## Context

Currently, `_execute_via_sdk()` in `task_work_interface.py` creates an SDK session with:
```python
setting_sources=["user", "project"]  # Loads ~987KB
prompt = self._build_design_prompt(task_id, options)  # "/task-work TASK-XXX --design-only"
```

## Deliverables

### 1. New method: `_build_autobuild_design_prompt()`

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

The prompt must include:
- Task requirements (from task markdown)
- Design phase execution protocol (loaded from `autobuild_design_protocol.md` via `load_protocol()`)
- Output format for implementation plan
- Complexity evaluation criteria
- Architectural review criteria (SOLID/DRY/YAGNI) — lightweight inline check, no subagent

### 2. Encode Phase Skipping in Design Prompt

The autobuild design prompt must encode these decisions directly:

| Phase | Interactive | AutoBuild | Rationale |
|-------|-----------|-----------|-----------|
| 1.6 Clarification | Yes | **Skip** | No human present |
| 2 Planning | Yes | Yes | Essential |
| 2.1 Library Context | Yes | **Skip** | Adds 30-60s, marginal value |
| 2.5A Pattern MCP | Yes | **Skip** | Pattern suggestions add latency |
| 2.5B Arch Review | Yes | **Lightweight** | Inline check, no subagent |
| 2.7 Complexity | Yes | Yes | Needed for orchestration decisions |
| 2.8 Checkpoint | Yes | **Auto-approve** | Already implemented |

### 3. Update `_execute_via_sdk()`

```python
# BEFORE:
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],
    ...
)
prompt = self._build_design_prompt(task_id, options)

# AFTER:
options = ClaudeAgentOptions(
    setting_sources=["project"],
    ...
)
prompt = self._build_autobuild_design_prompt(task_id, options)
```

## Acceptance Criteria

- [ ] `_build_autobuild_design_prompt()` method exists in `task_work_interface.py`
- [ ] `setting_sources` changed to `["project"]` in `_execute_via_sdk()`
- [ ] Output is parseable by existing `_parse_design_result()`
- [ ] `DesignPhaseResult` dataclass schema unchanged
- [ ] Phase skipping encoded in prompt (1.6, 2.1, 2.5A skipped; 2.5B lightweight; 2.8 auto-approve)
- [ ] Implementation plan compatible with downstream Player consumption
- [ ] No changes to interactive `/task-work` path (zero regression)

## Key Constraints

- Output must be parseable by existing `_parse_design_result()`
- `DesignPhaseResult` dataclass schema unchanged
- Implementation plan must be compatible with downstream Player consumption

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Add `_build_autobuild_design_prompt()`, update `_execute_via_sdk()` |

## Testing

- Unit test: Verify prompt encodes phase skipping correctly
- Unit test: Verify `setting_sources=["project"]` in SDK options
- Integration test: Verify design output is parseable by `_parse_design_result()`
