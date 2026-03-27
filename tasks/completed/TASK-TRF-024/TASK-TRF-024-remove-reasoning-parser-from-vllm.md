---
id: TASK-TRF-024
title: Remove --reasoning-parser qwen3 from vLLM launch script
status: completed
created: 2026-03-27T16:00:00Z
updated: 2026-03-27T17:10:00Z
completed: 2026-03-27T17:10:00Z
completed_location: tasks/completed/TASK-TRF-024/
previous_state: in_review
state_transition_reason: "task-complete — all acceptance criteria met"
priority: critical
tags: [vllm, config, think-blocks, eighth-run]
complexity: 1
parent_review: TASK-REV-TRF8
feature_id: FEAT-TRF8
depends_on: []
wave: 1
implementation_mode: direct
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Remove --reasoning-parser qwen3 from vLLM Launch Script

## Problem

vLLM's `--reasoning-parser qwen3` flag intercepts `<think>` blocks from Qwen3.5's output, strips them from the `content` field, and redirects them to `reasoning_content` in `additional_kwargs`. This creates two failures:

1. **Training examples lose think blocks**: The Player generates training examples with `<think>` blocks in the assistant content, but vLLM strips them. The `write_output` validator then rejects all reasoning-type examples for "missing `<think>...</think>` block".

2. **JSON extraction corruption**: The think-block stripping may corrupt the JSON structure, contributing to extraction failures.

The `_extract_coach_content` function already has a `reasoning_content` fallback (added for TASK-REV-TRF5), but the Player doesn't need this — think blocks should flow through naturally.

## Root Cause

File: `guardkit/scripts/vllm-agentic-factory.sh` line 65

```bash
EXTRA_ARGS="--trust-remote-code \
  --reasoning-parser qwen3 \           # <-- THIS LINE
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --enable-prefix-caching"
```

## Fix

Remove `--reasoning-parser qwen3` from the qwen35 case in the launch script. Keep all other flags:

```bash
EXTRA_ARGS="--trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --enable-prefix-caching"
```

Also update the banner text on line 71 to remove the "Reasoning: qwen3" reference.

## Files to Modify

- `guardkit/scripts/vllm-agentic-factory.sh` (lines 64-68, 71)

## Acceptance Criteria

- [x] `--reasoning-parser qwen3` removed from qwen35 case
- [x] Banner text updated (remove "Reasoning: qwen3")
- [x] `--enable-auto-tool-choice` and `--tool-call-parser qwen3_coder` preserved
- [ ] vLLM container restarts successfully with updated script (manual verification on DGX Spark)
- [ ] Player response `content` field contains `<think>` blocks (verified in next run)

## Risk

**Low**. Removing the reasoning parser means `<think>` blocks appear in the raw `content` field. The normalisation pipeline (TRF-020/021) already handles malformed think tags. The JSON extraction pipeline handles content with think block prefixes.

## Test Plan

1. Restart vLLM with updated script
2. Run a single-target test
3. Verify Player `content` contains `<think>` blocks
4. Verify JSON extraction handles `<think>...</think>\n\n{json}` format
