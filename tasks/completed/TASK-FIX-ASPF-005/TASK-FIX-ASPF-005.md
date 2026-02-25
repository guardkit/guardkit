---
id: TASK-FIX-ASPF-005
title: Increase SDK turn limit and vLLM context for fresh builds
status: completed
task_type: implementation
created: 2026-02-24T23:00:00Z
updated: 2026-02-25T00:00:00Z
completed: 2026-02-25T00:00:00Z
completed_location: tasks/completed/TASK-FIX-ASPF-005/
priority: high
tags: [autobuild, vllm, sdk, turn-limit, context-window]
complexity: 2
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 2
implementation_mode: direct
dependencies: [TASK-FIX-ASPF-001]
organized_files: [
  "TASK-FIX-ASPF-005.md"
]
---

# Task: Increase SDK turn limit and vLLM context for fresh builds

## Description

Run 2 Turn 1 failed because the vLLM Player exhausted its SDK turns (50) scaffolding 31 files with `--fresh` and never reached the report-writing step. The SDK returned normally (no timeout) but no `player_turn_1.json` was written, triggering the synthetic fallback.

Two parameter changes fix this at the source — giving the Player enough room to complete ALL operations including report writing:

1. **Increase `TASK_WORK_SDK_MAX_TURNS`** from 50 to 100 — allows the Player to scaffold files AND write the structured report
2. **Increase `VLLM_MAX_LEN`** from 131072 (128K) to 262144 (256K) — Qwen3-Coder-Next supports 256K natively, and the GB10's 128GB VRAM can handle it

If the Player writes the report, the DMCP fixes handle the rest of the pipeline correctly — no synthetic fallback needed.

## Changes

### 1. agent_invoker.py — Increase SDK turn limit

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: Line 116

```python
TASK_WORK_SDK_MAX_TURNS = 100
```

### 2. vllm-serve.sh — Increase default context to 256K

**File**: `scripts/vllm-serve.sh`

- Default and `next` preset: `MAX_LEN="${VLLM_MAX_LEN:-262144}"`
- `next-nvfp4` preset: `MAX_LEN="${VLLM_MAX_LEN:-262144}"`
- `30b` preset unchanged at 32768

## Acceptance Criteria

1. [x] `TASK_WORK_SDK_MAX_TURNS` increased to 100
2. [x] vLLM serve script defaults to 262144 for next and next-nvfp4 presets
3. [x] Comment updated to explain the rationale
4. [x] Existing tests still pass (146 passed)

## Completion Notes

All changes were already applied in prior commits. Verified:
- `TASK_WORK_SDK_MAX_TURNS = 100` at agent_invoker.py:116
- `VLLM_MAX_LEN=262144` defaults in vllm-serve.sh for next and next-nvfp4 presets
- 30B preset correctly remains at 32768
- All 146 unit tests pass
