# Implementation Guide: vLLM AutoBuild Run 2 Fixes (FEAT-FF93)

**Parent Review**: TASK-REV-5610
**Feature**: vLLM/Qwen3 AutoBuild Run 2 Fixes for GB10
**Total Tasks**: 5 (2 P0, 2 P1, 1 P2)

## Problem Statement

AutoBuild run 2 with vLLM/Qwen3 on Dell GB10 completed 5/8 tasks (up from 2/8 in run 1) but failed at Wave 3 with three root causes:
1. `extract_acceptance_criteria()` can't find task files in `design_approved/` → 0/6 Coach verification
2. 93-101 SDK turns per Player turn exhaust the 9,600s task timeout
3. Transient vLLM streaming error under 3-task parallel GPU load

## Execution Strategy

### Wave 1: P0 Critical Fixes (Parallel)

Both tasks are independent and can run in parallel.

| Task | Description | Mode | Complexity | File |
|------|-------------|------|------------|------|
| TASK-FIX-6141 | Fix AC search path divergence | task-work | 2 | `agent_invoker.py:4108-4129` |
| TASK-FIX-7718 | SDK turn budget for local models | task-work | 2 | `agent_invoker.py:147` |

**No file conflicts**: 6141 modifies lines 4108-4129, 7718 modifies line 147 and invoke methods. Both in `agent_invoker.py` but different sections.

**Expected outcome**: These two fixes alone should enable Wave 3 success in run 3 (predicted 7-8/8 tasks).

### Wave 2: P1 Robustness Improvements (Parallel)

| Task | Description | Mode | Complexity | File |
|------|-------------|------|------------|------|
| TASK-FIX-CDF8 | Fix cancelled error display | direct | 2 | `autobuild.py` |
| TASK-FIX-46F2 | vLLM streaming retry | task-work | 4 | `agent_invoker.py` |

**No file conflicts**: CDF8 modifies `autobuild.py`, 46F2 modifies `agent_invoker.py`.

### Wave 3: P2 Deferred (Sequential, Conditional)

| Task | Description | Mode | Complexity | File |
|------|-------------|------|------------|------|
| TASK-FIX-DF01 | Wave parallelism config | task-work | 4 | `feature_orchestrator.py` |

**Dependencies**: Depends on TASK-FIX-6141 and TASK-FIX-7718 (Wave 1).
**Conditional**: Re-evaluate after run 3 results with Wave 1 fixes applied. May not be needed.

## Architecture Constraints

**DO NOT MODIFY** the following components (validated as working correctly):
- `timeout_multiplier` auto-detection (4.0x for localhost)
- Cooperative cancellation (TASK-ASF-007) — per-task `threading.Event`
- State recovery (TASK-ASF-006) — synthetic report generation
- Semantic matching auto-resolution (`_resolve_matching_strategy()`)
- Text-matching fixes (TASK-FIX-TM01-04) — 50% Jaccard + fuzzy prefix
- Per-task timeout via `asyncio.wait_for()`
- State bridge `_find_task_file()` — correct glob pattern

## Testing Strategy

All fixes modify autobuild internals:
- **Unit tests**: Each fix should include targeted unit tests for the changed code
- **Integration verification**: After Wave 1 fixes, re-run the DB feature autobuild on GB10 with vLLM
- **Regression check**: Run existing test suite to confirm no Anthropic regression

## Quick Reference

| Task ID | Priority | Effort | Key File | Key Method |
|---------|----------|--------|----------|------------|
| TASK-FIX-6141 | P0 | Small | agent_invoker.py:4108 | `extract_acceptance_criteria()` |
| TASK-FIX-7718 | P0 | Small | agent_invoker.py:147 | `TASK_WORK_SDK_MAX_TURNS` |
| TASK-FIX-CDF8 | P1 | Small | autobuild.py | Summary rendering |
| TASK-FIX-46F2 | P1 | Medium | agent_invoker.py | SDK stream invocation |
| TASK-FIX-DF01 | P2 | Medium | feature_orchestrator.py | `_execute_wave_parallel()` |
