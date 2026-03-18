---
id: TASK-REV-1150
title: Diagnose vllm-graphiti.sh Qwen3-30B launch failure
status: review_complete
created: 2026-03-18T12:00:00Z
updated: 2026-03-18T13:00:00Z
priority: high
tags: [vllm, graphiti, dgx-spark, qwen3, debugging]
task_type: review
complexity: 4
review_results:
  mode: decision
  depth: standard
  findings_count: 3
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-1150-review-report.md
  completed_at: 2026-03-18T13:00:00Z
---

# Task: Diagnose vllm-graphiti.sh Qwen3-30B Launch Failure

## Description

The `vllm-graphiti.sh` script fails when launching Qwen3-30B-A3B-FP8 as the Graphiti LLM
on the Dell ProxMax GB10 (DGX Spark). This model was selected to replace Nemotron3-Nano
whose 8K context window is too small for Graphiti's system prompts (~7800-8100 token
baseline overhead).

## Root Cause (Preliminary)

**Primary error**: `ModuleNotFoundError: No module named 'fastsafetensors'`

The script passes `--load-format fastsafetensors` but the `fastsafetensors` package is
not installed in the NGC vLLM 26.01 container (`nvcr.io/nvidia/vllm:26.01-py3`).
The error message confirms: `ImportError: Please install vllm[fastsafetensors] for fastsafetensors support`.

**Secondary observation**: `DeepGEMM backend requested but not available` — falls back to
Triton for FP8 MoE, which is expected on SM 12.1 (GB10 ARM64).

## Error Output

See: `docs/reviews/graphiti-qwen3/run-1.md`

Key lines:
- Line 55: `WARNING: DeepGEMM backend requested but not available`
- Line 71: `ModuleNotFoundError: No module named 'fastsafetensors'`
- Line 136: `ImportError: Please install vllm[fastsafetensors] for fastsafetensors support`
- Line 273: `RuntimeError: Engine core initialization failed`

## Acceptance Criteria

- [ ] Identify fix for fastsafetensors missing module error
- [ ] Determine whether to remove `--load-format fastsafetensors` or install the package
- [ ] Verify Qwen3-30B-A3B-FP8 loads successfully on GB10
- [ ] Confirm Graphiti can use the model for entity extraction (clean JSON output)
- [ ] Document any additional tuning for MoE on SM 12.1

## Recommended Fix Options

### Option A: Remove `--load-format fastsafetensors` (simplest)
Remove the flag from all presets — vLLM defaults to `auto` which uses standard
safetensors loading. This worked fine for Nemotron3-Nano in run_2.

### Option B: Install fastsafetensors in container
Use a custom Dockerfile or `docker exec pip install fastsafetensors` before launch.
More complex but may provide faster weight loading for large MoE models.

### Option C: Use newer NGC image
Check if `nvcr.io/nvidia/vllm:26.02-py3` or later includes fastsafetensors.

## Context

- **Hardware**: Dell ProxMax GB10 (DGX Spark), 128GB unified memory, SM 12.1
- **Script**: `scripts/vllm-graphiti.sh`
- **Model**: `Qwen/Qwen3-30B-A3B-FP8` (MoE, 3.3B active params, ~32.5GB)
- **Purpose**: Replace Nemotron3-Nano (8K ctx too small) as Graphiti LLM
- **Research**: `docs/research/dgx-spark/DGX Spark, Nemotron3, and NVFP4` PDF
- **Previous success**: Nemotron3-Nano runs fine on same infra (run_2.md)

## Implementation Notes

The `--load-format fastsafetensors` was likely added from the Braun PDF research
for faster weight loading. The NGC 26.01 image doesn't bundle this optional dependency.
