---
id: TASK-POF-004
title: Inline implement phase execution protocol in Player SDK prompt
status: completed
completed: 2026-02-15T18:30:00Z
completed_location: tasks/completed/TASK-POF-004/
task_type: implementation
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T18:30:00Z
priority: high
complexity: 5
tags: [autobuild, preamble, performance, main-fix]
parent_review: TASK-REV-A781
feature_id: preamble-overhead-fix
implementation_mode: task-work
wave: 2
parallel_group: wave-2
dependencies: [TASK-POF-001]
test_results:
  status: passed
  tests_passed: 344
  tests_failed: 0
  last_run: 2026-02-15T18:00:00Z
---

# Task: Inline Implement Phase Execution Protocol

## Description

The Player turn currently invokes `/task-work TASK-XXX --implement-only --mode={mode}` via SDK, which requires `setting_sources=["user", "project"]` to find the `/task-work` skill. This loads ~1MB of commands into every Player session.

**Fix**: Same approach as TASK-POF-003 but for the implementation path. Inline a slim Phases 3-5 execution protocol directly in the Player prompt and switch to `setting_sources=["project"]`.

## Root Cause (from TASK-REV-A781)

```python
# Current: agent_invoker.py:2504-2515
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Loads ALL user commands (~839KB) per Player turn
    # ... because the prompt is "/task-work TASK-XXX --implement-only"
)
```

This happens on **every Player turn**, not just the first. A 5-turn autobuild run loads 1MB x 5 = 5MB of context across Player sessions alone.

## Acceptance Criteria

- [x] `AgentInvoker._invoke_task_work_implement()` sends inline protocol, NOT `/task-work ...` skill invocation
- [x] SDK options use `setting_sources=["project"]` (NOT `["user", "project"]`)
- [x] Inline protocol covers Phases 3 (Implementation), 4 (Testing), 4.5 (Fix Loop), 5 (Code Review)
- [x] Inline protocol is ≤20KB
- [x] Player still writes `task_work_results.json` that Coach can validate
- [x] Player still creates `player_turn_N.json` report
- [x] Existing quality gates (compilation, test pass, coverage) still enforced
- [x] Integration test: run Player on a test task, verify implementation output

## Files to Modify

1. `guardkit/orchestrator/agent_invoker.py`
   - `_invoke_task_work_implement()` - Replace skill invocation with inline protocol
   - Change `setting_sources` from `["user", "project"]` to `["project"]`
   - Add new method `_build_inline_implement_protocol()` for the slim prompt
2. Possibly share protocol template extraction with TASK-POF-003

## Implementation Notes

### What the inline protocol needs

The implement phase prompt should instruct Claude to:
1. **Phase 3**: Read the implementation plan, implement code changes
2. **Phase 4**: Run tests, check compilation, measure coverage
3. **Phase 4.5**: If tests fail, auto-fix (up to 3 attempts)
4. **Phase 5**: Run code review (lint, basic quality checks)
5. **Output**: Write `task_work_results.json` with quality gate results

### What it does NOT need

- Phases 1-2.8 (already done in pre-loop)
- Phase 5.5 (Plan Audit - not relevant for implement-only)
- The full task-work command spec
- All user commands, agent definitions, etc.

### Key constraint

Must produce `task_work_results.json` compatible with Coach validation. The Coach reads this file to verify Player claims. Check `coach_validator.py` and `coach_verification.py` for expected format.

### Estimated savings per Player turn

- Context: 1,078KB -> 78KB (93% reduction)
- Per-turn savings: ~200-300s
- For 5-turn run: ~1,000-1,500s total savings across all turns

### Interaction with TASK-POF-003

Both tasks follow the same pattern (inline protocol, switch setting_sources). Consider extracting a shared utility for building inline prompts with the right SDK options. But don't over-abstract - these are two different protocols with different phase requirements.
