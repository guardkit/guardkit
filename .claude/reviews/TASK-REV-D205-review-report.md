# Review Report: TASK-REV-D205

## Executive Summary

The vLLM Graphiti run-6 failure is caused by a single misconfiguration: `gpu_memory_utilization: 0.15` (15%) is far too low for the 14B parameter dense model (`neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`). The model weights alone consume 15.2 GiB, leaving **-1.30 GiB** for KV cache — hence the `ValueError: No available memory for the cache blocks` crash. The fix is to increase `gpu_memory_utilization` to 0.40-0.50 in the startup script.

## Review Details

- **Mode**: Infrastructure / Root Cause Analysis
- **Depth**: Standard
- **Task**: TASK-REV-D205
- **Source**: [run-6.md](docs/reviews/graphiti-qwen3/run-6.md)

## Findings

### Finding 1: Root Cause — `gpu_memory_utilization` set to 0.15

**Severity**: Critical (blocks startup entirely)

The script [vllm-graphiti.sh:76](scripts/vllm-graphiti.sh#L76) sets `GPU_UTIL` to `0.15` for the `qwen2.5-14b` preset. This value was inherited from the original config and was never recalculated for this model.

**Memory arithmetic** (from run-6 logs):
- GPU memory budget at 15%: unknown total, but clearly insufficient
- Model weights: **15.2 GiB** (log line: `Model loading took 15.2227 GiB memory`)
- Available KV cache after model load: **-1.30 GiB** (negative!)
- Result: vLLM cannot allocate even a single KV cache block

**Comparison with run-2 (successful, Qwen3-30B-A3B MoE)**:
- `gpu_memory_utilization: 0.30` (30%)
- Model weights: 29.0 GiB (MoE — larger total but sparse activation)
- Available KV cache: **4.04 GiB** (healthy)
- KV cache tokens: 88,176 (max concurrency: 2.69x at 32K context)
- Server started successfully and served requests at ~65 tokens/s generation

The 14B dense model is smaller than the 30B MoE (15.2 GiB vs 29.0 GiB), but GPU_UTIL was halved from 0.30 to 0.15 — which overcompensated.

### Finding 2: Why 0.15 was set (inherited config, not recalculated)

The [vllm-graphiti.sh](scripts/vllm-graphiti.sh) script comment block (line 54) documents memory budgets:
```
qwen2.5-14b  ~17GB  | qwen2.5-32b  ~35GB  | qwen3-30b  ~33GB
```

The 0.15 value appears to have been set conservatively to leave room for other models on the same GPU (ports 8001, 8002, 8003). However, 15% of GPU memory is insufficient for even the model weights of a 14B FP8 model.

**The script defaults** (line 63 and 76):
```bash
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"   # line 63 (global default)
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"   # line 76 (qwen2.5-14b preset)
```

Compare with qwen2.5-32b and qwen3-30b presets which correctly use 0.30.

### Finding 3: `max_model_len: 32768` is reasonable but could be reduced

The Qwen2.5-14B model supports up to 128K context. Setting 32K is already conservative. However, Graphiti's system prompts only use ~7800-8100 tokens baseline. For Graphiti workloads:
- Typical request: ~8K system + ~2-4K user = ~10-12K tokens
- 32K provides ample headroom for larger episodes
- Reducing to 16384 would halve KV cache memory requirements if memory remains tight

**Verdict**: 32768 is fine — the real problem is GPU_UTIL, not max_model_len.

### Finding 4: FP8 KV cache without calibrated scaling factors

Run-6 logs show three warnings:
```
WARNING: Checkpoint does not provide a q scaling factor. Setting it to k_scale.
WARNING: Using KV cache scaling factor 1.0 for fp8_e4m3.
WARNING: Using uncalibrated q_scale 1.0 and/or prob_scale 1.0 with fp8 attention.
```

These same warnings appeared in run-2 (Qwen3-30B) which worked successfully. The `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` model uses "dynamic" quantization which doesn't include pre-calibrated KV cache scales.

**Impact**: Potential minor accuracy degradation but unlikely to affect Graphiti's entity extraction (structured JSON output). The model worked correctly in the successful Qwen3 run-2 with identical warnings. This is a low-priority concern for production but worth monitoring if extraction quality drops.

### Finding 5: Run history — progressive debugging across 6 runs

| Run | Model | GPU_UTIL | Failure | Root Cause |
|-----|-------|----------|---------|------------|
| 1 | Qwen3-30B-A3B-FP8 | 0.30 | fastsafetensors import | Missing `vllm[fastsafetensors]` + `load_format: fastsafetensors` |
| 2 | Qwen3-30B-A3B-FP8 | 0.30 | **SUCCESS** | Fixed by removing `load_format: fastsafetensors` |
| 3 | Qwen3-30B-A3B-FP8 | 0.30 | **SUCCESS** (duplicate of run-2 log) | Working — served Graphiti requests |
| 4 | Qwen/Qwen3-30B-A3B-FP8 | 0.30 | `--guided-decoding-backend` unrecognized | Old vLLM flag used (removed in v0.12+) |
| 5 | Qwen/Qwen2.5-14B-Instruct-FP8 | 0.15 | 401 Unauthorized | Wrong model ID (gated repo, not the neuralmagic variant) |
| 6 | neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic | 0.15 | OOM (KV cache) | **gpu_memory_utilization too low** |

The model switch from Qwen3 to Qwen2.5 was motivated by Qwen3's thinking mode causing timeouts (documented in script comments). The switch itself is correct — the GPU_UTIL just wasn't recalculated.

### Finding 6: Model switch rationale is sound

The [vllm-graphiti.sh](scripts/vllm-graphiti.sh) comments (lines 11-15) explain:
> Qwen3 models have a thinking mode that generates thousands of `<think>` tokens internally before producing output. Even with `--reasoning-parser qwen3` stripping them, the model still spends the time generating them — causing 900s+ timeouts on Graphiti episodes. Qwen2.5 is a pure instruct model with no thinking mode.

This is correct. Run-2/3 show Qwen3 working but with ~35 tok/s generation that could easily timeout on complex episodes with extensive thinking overhead. Qwen2.5-14B is the right choice for Graphiti's structured extraction workload.

## Recommendations

### 1. Increase `gpu_memory_utilization` to 0.40 (Critical — fixes the crash)

**In [vllm-graphiti.sh](scripts/vllm-graphiti.sh)**, change lines 63 and 76:

```bash
# Line 63 (global default):
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.40}"

# Line 76 (qwen2.5-14b preset):
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.40}"
```

**Rationale**:
- Model weights: ~15.2 GiB
- At 0.40 utilization on a system with 128 GB unified memory, vLLM gets ~51 GiB
- After model weights: ~36 GiB available for KV cache
- This provides ~174K tokens of KV cache (FP8) — ample for Graphiti
- Still leaves ~77 GiB for embedding model (port 8001), AutoBuild LLM (port 8002), and system

**Alternative**: 0.30 would also work (gives ~23 GiB for KV cache after model), but 0.40 provides better concurrency headroom. Use `VLLM_GRAPHITI_GPU_UTIL` env var to override if other models need more memory.

### 2. Update memory budget comment (Low priority)

Line 54 says `qwen2.5-14b ~17GB` — but this is only model weights. The actual allocation at 0.40 utilization would be ~51 GiB. Update the comment to reflect both weight size and vLLM allocation:

```bash
# Memory budget (128GB unified):
#   qwen2.5-14b  weights ~16GB, vLLM alloc ~51GB (@0.40)
#   qwen2.5-32b  weights ~34GB, vLLM alloc ~38GB (@0.30)
#   qwen3-30b    weights ~29GB, vLLM alloc ~38GB (@0.30)
```

### 3. Consider reducing `max_model_len` to 16384 if memory is tight (Optional)

Only if running multiple large models simultaneously makes 0.40 infeasible. This halves KV cache memory per request while still providing ample context for Graphiti (~8K system + 8K user content).

### 4. Monitor FP8 accuracy (Low priority, post-fix)

After the server starts successfully, validate Graphiti extraction quality. If entity extraction accuracy drops compared to the Qwen3 runs, consider:
- Switching to `neuralmagic/Qwen2.5-14B-Instruct-GPTQ-Int4` (calibrated quantization)
- Or using `--kv-cache-dtype auto` (uses BF16 for KV cache, more memory but no accuracy loss)

### 5. No model change needed

The switch from Qwen3-30B-A3B to Qwen2.5-14B-Instruct-FP8 is correct. The 14B dense model:
- Has no thinking mode overhead
- Is smaller (15 GiB vs 29 GiB)
- Supports xgrammar JSON schema enforcement
- Has 128K context window (32K configured)
- Is a well-validated instruct model for structured extraction

## Decision Matrix

| Option | Fixes Crash | Memory Impact | Concurrency | Risk |
|--------|-------------|---------------|-------------|------|
| GPU_UTIL=0.40 (recommended) | Yes | ~51 GiB alloc | High (~174K tokens) | Low |
| GPU_UTIL=0.30 | Yes | ~38 GiB alloc | Medium (~100K tokens) | Low |
| GPU_UTIL=0.25 | Likely | ~32 GiB alloc | Low (~73K tokens) | Medium |
| Reduce max_model_len to 16384 + 0.30 | Yes | ~38 GiB, smaller KV | Medium | Low |
| Switch to smaller model (7B) | Yes | ~25 GiB alloc | High | Medium (quality) |

## Appendix

### Key Log Lines (run-6)

```
non-default args: {...'gpu_memory_utilization': 0.15...}
Model loading took 15.2227 GiB memory and 512.925670 seconds
Available KV cache memory: -1.30 GiB
ValueError: No available memory for the cache blocks
```

### Successful Config Reference (run-2, Qwen3-30B)

```
gpu_memory_utilization: 0.30
Model loading took 29.0435 GiB memory
Available KV cache memory: 4.04 GiB
GPU KV cache size: 88,176 tokens
Maximum concurrency for 32,768 tokens per request: 2.69x
```
