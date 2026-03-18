---
id: TASK-REV-D205
title: Analyse Graphiti Qwen3 run-6 GPU memory failure
status: review_complete
created: 2026-03-18T14:00:00Z
updated: 2026-03-18T15:00:00Z
priority: high
tags: [graphiti, vllm, qwen3, gpu-memory, infrastructure, review]
task_type: review
review_mode: decision
review_depth: standard
complexity: 4
review_results:
  mode: decision
  depth: standard
  findings_count: 6
  recommendations_count: 5
  decision: fix_config
  report_path: .claude/reviews/TASK-REV-D205-review-report.md
  completed_at: 2026-03-18T15:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse Graphiti Qwen3 run-6 GPU memory failure

## Description

Analyse the failing output from vLLM Graphiti run-6 (`docs/reviews/graphiti-qwen3/run-6.md`). The model has been switched following diagnosis on the user's MacBook with Claude Code. The vLLM server fails to start with an out-of-memory error for KV cache blocks.

## Context

- **Model switched to**: `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`
- **Previous runs**: run-1 through run-5 exist in `docs/reviews/graphiti-qwen3/`
- **Platform**: NVIDIA DGX/GPU server (Linux, CUDA 13.1, driver 590.48.01)
- **vLLM version**: 0.13.0 (NVIDIA container release 26.01)
- **Diagnosed on**: MacBook with Claude Code, then model switch applied

## Key Findings from Log

1. **Root cause**: `gpu_memory_utilization: 0.15` (15%) is far too low for a 14B parameter model
2. **Model memory footprint**: 15.2 GiB for model weights alone
3. **Available KV cache memory**: -1.30 GiB (negative — no room for inference)
4. **Error**: `ValueError: No available memory for the cache blocks`
5. **Additional config**: `max_model_len: 32768`, `kv_cache_dtype: fp8`, chunked prefill enabled
6. **FP8 warnings**: Uncalibrated q_scale/prob_scale using default 1.0 — potential accuracy issues

## Review Focus Areas

- [ ] Why `gpu_memory_utilization` was set to 0.15 — was this inherited from a smaller model config?
- [ ] Recommended `gpu_memory_utilization` value for Qwen2.5-14B-Instruct-FP8 on this GPU
- [ ] Whether `max_model_len: 32768` is appropriate or should be reduced to conserve memory
- [ ] Impact of FP8 KV cache without calibrated scaling factors on Graphiti inference quality
- [ ] Review docker compose / startup script that sets these vLLM parameters
- [ ] Compare with previous successful run configurations (run-1 through run-5)
- [ ] Determine if the model switch itself is correct or if a smaller model would be more appropriate

## Acceptance Criteria

- [ ] Root cause of GPU memory failure fully documented
- [ ] Recommended vLLM configuration parameters identified
- [ ] Comparison with previous run configurations completed
- [ ] Action items for fix clearly specified

## Source Log

`docs/reviews/graphiti-qwen3/run-6.md`

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-D205` for structured analysis.
