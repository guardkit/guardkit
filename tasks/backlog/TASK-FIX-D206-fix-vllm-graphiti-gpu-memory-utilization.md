---
id: TASK-FIX-D206
title: Fix vLLM Graphiti gpu_memory_utilization from 0.15 to 0.40
status: in_review
created: 2026-03-18T15:05:00Z
updated: 2026-03-18T15:05:00Z
priority: high
tags: [graphiti, vllm, gpu-memory, infrastructure, config-fix]
task_type: implementation
parent_review: TASK-REV-D205
complexity: 1
depends_on: []
---

# Task: Fix vLLM Graphiti gpu_memory_utilization from 0.15 to 0.40

## Description

The vLLM Graphiti server (port 8000) fails to start because `gpu_memory_utilization` is set to 0.15 (15%), which is insufficient for the Qwen2.5-14B-Instruct-FP8-dynamic model (15.2 GiB weights). This results in -1.30 GiB available for KV cache and a `ValueError: No available memory for the cache blocks`.

## Changes Required

In `scripts/vllm-graphiti.sh`:

1. **Line 63** — Change global default from `0.15` to `0.40`:
   ```bash
   GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.40}"
   ```

2. **Line 76** — Change qwen2.5-14b preset default from `0.15` to `0.40`:
   ```bash
   GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.40}"
   ```

3. **Line 54** — Update memory budget comment to reflect actual vLLM allocation:
   ```bash
   #   qwen2.5-14b  weights ~16GB, vLLM alloc ~51GB (@0.40)
   #   qwen2.5-32b  weights ~34GB, vLLM alloc ~38GB (@0.30)
   #   qwen3-30b    weights ~29GB, vLLM alloc ~38GB (@0.30)
   ```

## Acceptance Criteria

- [ ] `gpu_memory_utilization` default changed to 0.40 for qwen2.5-14b preset
- [ ] Global default changed to 0.40
- [ ] Memory budget comment updated
- [ ] Script still respects `VLLM_GRAPHITI_GPU_UTIL` env var override

## Context

- Parent review: TASK-REV-D205
- Review report: `.claude/reviews/TASK-REV-D205-review-report.md`
- Run-6 log: `docs/reviews/graphiti-qwen3/run-6.md`
- Successful run-2 used 0.30 with the larger Qwen3-30B model

## Implementation Notes

This is a 3-line config change in a shell script. No code logic changes needed.
