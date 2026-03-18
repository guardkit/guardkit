# Review Report: TASK-REV-1150

## Executive Summary

The `vllm-graphiti.sh` script fails to launch Qwen3-30B-A3B-FP8 due to a single root cause: the `--load-format fastsafetensors` flag requires an optional Python package not included in the NGC vLLM 26.01 container. The fix is to remove this flag from all three Qwen3 presets, letting vLLM use its default `auto` load format.

## Review Details

- **Mode**: Technical Decision Analysis
- **Depth**: Standard
- **Hardware**: Dell ProxMax GB10 (DGX Spark), 128GB unified, SM 12.1
- **Container**: `nvcr.io/nvidia/vllm:26.01-py3` (vLLM 0.13.0)

## Findings

### Finding 1: Missing `fastsafetensors` package (CRITICAL)

**Evidence**: `ModuleNotFoundError: No module named 'fastsafetensors'` (run-1.md:71)

The NGC vLLM 26.01 container does not bundle `fastsafetensors`. The flag `--load-format fastsafetensors` is set on all three Qwen3 presets (lines 69, 80, 91 of `vllm-graphiti.sh`), causing immediate failure after the 826-second model download completes.

The error message confirms: `ImportError: Please install vllm[fastsafetensors] for fastsafetensors support` (run-1.md:136).

### Finding 2: DeepGEMM warning is benign (INFO)

**Evidence**: `WARNING: DeepGEMM backend requested but not available` (run-1.md:55)

This is expected on SM 12.1 (GB10 ARM64). vLLM correctly falls back to Triton for FP8 MoE. No action needed.

### Finding 3: Flag origin — research docs, not tested config

The `--load-format fastsafetensors` was likely adopted from the Braun PDF research for faster weight loading. The working `vllm-serve.sh` script uses `--load-format auto` (line 301), confirming the default path works fine.

## Decision Matrix

| Option | Effort | Risk | Performance | Recommendation |
|--------|--------|------|-------------|----------------|
| **A: Remove flag** | Trivial (3 lines) | Very low | Standard (proven) | **Recommended** |
| B: Install in container | Medium (Dockerfile) | Medium | Potentially faster load | Not recommended |
| C: Newer NGC image | Unknown | Unknown | Unknown | Defer |

## Recommendations

1. **Remove `--load-format fastsafetensors`** from all three Qwen3 presets in `scripts/vllm-graphiti.sh` (lines 69, 80, 91). This is a 3-line change.
2. **Re-run** the script and verify Qwen3-30B-A3B-FP8 loads and serves on port 8000.
3. **Test Graphiti integration** — confirm entity extraction returns clean JSON (the `--reasoning-parser qwen3` flag strips `<think>` blocks).
4. **Document** the DeepGEMM/Triton fallback as expected behavior for SM 12.1 in the script comments (already partially documented).

## Implementation Scope

The fix touches only `scripts/vllm-graphiti.sh`:
- Line 69: Remove `--load-format fastsafetensors` from `qwen3-30b` preset
- Line 80: Remove `--load-format fastsafetensors` from `qwen3-14b` preset
- Line 91: Remove `--load-format fastsafetensors` from `qwen3-8b` preset

No other files affected. No tests to update (shell script).
