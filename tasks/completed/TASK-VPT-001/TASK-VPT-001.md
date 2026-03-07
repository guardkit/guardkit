---
id: TASK-VPT-001
title: Tune autobuild defaults for local backends (max_parallel=1, sdk_max_turns=75, timeout_multiplier=3.0)
status: completed
completed: 2026-03-07
task_type: fix
priority: high
tags: [autobuild, vllm, performance, config]
complexity: 1
parent_review: TASK-REV-5E93
feature_id: FEAT-VPT1
wave: 1
implementation_mode: direct
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-07
---

# Task: Tune Autobuild Defaults for Local Backends

## Description

Update three default configuration values for local backend (vLLM) autobuild runs based on profiling data from FEAT-1637 run on Dell ProMax GB10.

## Root Cause

Profiling in TASK-REV-5E93 revealed:
1. **max_parallel=2 causes 4.3x throughput penalty** — Wave 5 showed 87s/turn vs ~20s/turn sequential due to KV cache contention on single GPU
2. **sdk_max_turns=50 is too restrictive** — Tasks needing 2 turns hit the ceiling; 75 provides sufficient headroom
3. **timeout_multiplier=4.0 is excessive** — Longest task was ~74min; 3.0x gives 144min timeout, still ample headroom

## Changes

### 1. max_parallel: 2 → 1 (HIGH priority)

File: `guardkit/cli/autobuild.py`, line ~715

```python
# Before:
if detected_multiplier > 1.0:
    max_parallel = 2

# After:
if detected_multiplier > 1.0:
    max_parallel = 1
```

Users can still override via `--max-parallel 2` CLI flag or `GUARDKIT_MAX_PARALLEL_TASKS=2` env var.

### 2. sdk_max_turns: 50 → 75 (Medium priority)

File: `guardkit/orchestrator/agent_invoker.py`, line ~764

```python
# Before:
self._effective_sdk_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 50)

# After:
self._effective_sdk_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 75)
```

Users can still override via `GUARDKIT_SDK_MAX_TURNS=50` env var.

### 3. timeout_multiplier: 4.0 → 3.0 (Low priority)

File: `guardkit/orchestrator/agent_invoker.py`, line ~155

```python
# Before:
if "localhost" in base_url or "127.0.0.1" in base_url:
    return 4.0

# After:
if "localhost" in base_url or "127.0.0.1" in base_url:
    return 3.0
```

Users can still override via `GUARDKIT_TIMEOUT_MULTIPLIER=4.0` env var.

## Acceptance Criteria

- [ ] `max_parallel` defaults to 1 for local backends (timeout_multiplier > 1.0)
- [ ] `sdk_max_turns` auto-reduces to 75 (not 50) for local backends
- [ ] `timeout_multiplier` auto-detects to 3.0 (not 4.0) for localhost
- [ ] All three remain overridable via env vars or CLI flags
- [ ] Existing tests updated to reflect new defaults
- [ ] No changes to Anthropic API behavior (all changes gated on local backend detection)

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/cli/autobuild.py` | Line ~715: `max_parallel = 2` → `max_parallel = 1` |
| `guardkit/orchestrator/agent_invoker.py` | Line ~764: `min(..., 50)` → `min(..., 75)` |
| `guardkit/orchestrator/agent_invoker.py` | Line ~155: `return 4.0` → `return 3.0` |
| `tests/unit/test_max_parallel.py` | Update expected default from 2 to 1 |
| `tests/unit/test_agent_invoker_sdk_turn_budget.py` | Update expected default from 50 to 75 |
| `tests/unit/test_timeout_scaling.py` | Update expected default from 4.0 to 3.0 |

## Risk Assessment

**Risk**: Very Low
- All changes are numeric value updates to existing logic
- All values remain overridable via env vars and CLI flags
- Changes only affect local backend behavior (Anthropic API unchanged)
- Profiling data provides clear evidence for each change
