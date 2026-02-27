---
id: TASK-FIX-7718
title: Add SDK turn budget override for local models
status: completed
completed: 2026-02-27T00:00:00Z
updated: 2026-02-27T00:00:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, quality gates passed"
completed_location: tasks/completed/TASK-FIX-7718/
task_type: implementation
priority: high
tags: [autobuild, vllm, config, agent-invoker, p0]
complexity: 2
parent_review: TASK-REV-5610
feature_id: FEAT-FF93
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  tests_total: 430
  tests_passed: 430
  tests_failed: 0
  coverage: null
  last_run: 2026-02-27T00:00:00Z
---

# Task: Add SDK Turn Budget Override for Local Models

## Description

Add a `GUARDKIT_SDK_MAX_TURNS` environment variable override for the `TASK_WORK_SDK_MAX_TURNS` constant, with automatic reduction to 50 for local backends (detected via `detect_timeout_multiplier() > 1.0`).

Currently, `TASK_WORK_SDK_MAX_TURNS = 100` (agent_invoker.py:147) is a hardcoded constant. Qwen3 on local vLLM consumes 93-101 SDK turns on complex tasks, effectively using the entire `task_timeout=9600s` on a single Player turn, leaving no time for Coach validation or retry turns.

## Root Cause

On Anthropic models, tasks complete in 15-30 SDK turns. The 100-turn limit was designed for Anthropic. For Qwen3 on local hardware (~90s per turn), 100 turns = ~9,000s = nearly the full 9,600s task timeout.

With a 50-turn budget: 50 × ~90s = ~4,500s, leaving ~5,100s for a second adversarial turn + Coach validation.

## Implementation

In `agent_invoker.py`:

```python
# At module level (near line 147):
TASK_WORK_SDK_MAX_TURNS = int(os.environ.get("GUARDKIT_SDK_MAX_TURNS", 100))

# In _invoke_task_work_implement() or wherever max_turns is applied:
effective_max_turns = TASK_WORK_SDK_MAX_TURNS
if self.timeout_multiplier and self.timeout_multiplier > 1.0:
    effective_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 50)
    logger.info(
        "SDK max turns reduced to %d for local backend (timeout_multiplier=%.1f)",
        effective_max_turns, self.timeout_multiplier,
    )
```

## Acceptance Criteria

- [x] `GUARDKIT_SDK_MAX_TURNS` env var overrides `TASK_WORK_SDK_MAX_TURNS`
- [x] Default remains 100 for Anthropic API (no regression)
- [x] Auto-reduces to 50 when `timeout_multiplier > 1.0` (local backend detected)
- [x] Env var override takes precedence when explicitly set (e.g., `GUARDKIT_SDK_MAX_TURNS=30`)
- [x] Effective max turns logged at INFO level
- [x] Existing tests pass (430/430)

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py:147` | Replace constant with env var + local backend auto-reduction |
| `guardkit/orchestrator/agent_invoker.py` (invoke methods) | Use `effective_max_turns` instead of `TASK_WORK_SDK_MAX_TURNS` |

## Risk Assessment

**Risk**: Low
- Env var provides escape hatch if 50 is too aggressive
- No architectural change — just adds configurability to an existing constant
- Anthropic behaviour unchanged (multiplier=1.0 → keeps 100)
