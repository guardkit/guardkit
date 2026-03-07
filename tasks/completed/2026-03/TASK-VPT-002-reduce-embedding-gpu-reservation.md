---
id: TASK-VPT-002
title: Reduce embedding server GPU memory reservation from 0.15 to 0.05
status: completed
task_type: fix
priority: low
tags: [vllm, performance, infrastructure]
complexity: 1
parent_review: TASK-REV-5E93
feature_id: FEAT-VPT1
wave: 1
implementation_mode: direct
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Reduce Embedding Server GPU Memory Reservation

## Description

The nomic-embed-text-v1.5 embedding model served via vLLM on port 8001 currently reserves 15% (19GB) of GPU memory but only uses ~274MB. Reducing to 5% frees ~13GB for the LLM server's KV cache.

## Root Cause

In TASK-REV-5E93 analysis:
- LLM server: `--gpu-memory-utilization 0.8` (102GB reserved)
- Embedding server: `--gpu-memory-utilization 0.15` (19GB reserved, ~274MB actual)
- Total: 0.95 of 128GB, leaving only 6.4GB free

The embedding model (nomic-embed-text-v1.5, 137M params) is tiny and over-reserving by ~70x.

## Changes

File: `scripts/vllm-embed.sh`

```bash
# Before:
--gpu-memory-utilization 0.15

# After:
--gpu-memory-utilization 0.05
```

This reduces reservation from 19GB to ~6.4GB while still providing ~23x headroom over the model's actual ~274MB usage.

## Acceptance Criteria

- [x] `scripts/vllm-embed.sh` updated with `--gpu-memory-utilization 0.05` (actual: 0.03, even lower)
- [x] Embedding server starts successfully with the new setting
- [ ] Verified manually on Dell ProMax GB10 (no automated test — infrastructure script)

## Files to Modify

| File | Change |
|------|--------|
| `scripts/vllm-embed.sh` | `--gpu-memory-utilization 0.15` → `0.05` |

## Risk Assessment

**Risk**: Very Low
- The model only needs ~274MB; 6.4GB (0.05 × 128GB) is still 23x headroom
- If the model fails to load, the error is immediately visible and the old value can be restored
- No code changes, only infrastructure script
