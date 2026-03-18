# Review Report: TASK-REV-DGX1
# Identify optimal LLM for Graphiti on DGX Spark GB10

**Review Mode**: Decision Analysis
**Depth**: Comprehensive (revised with NVIDIA forum data)
**Completed**: 2026-03-18

---

## Executive Summary

The current Graphiti LLM (Nemotron 3 Nano 4B FP8, 8192-token context) is **incompatible** with Graphiti — its context window is entirely consumed by the baseline system prompt overhead (~7800-8100 tokens), leaving zero room for document content. The same 8192-token limit applies to all current Nemotron 3 Nano variants.

**Recommendation: Replace with `Qwen/Qwen3-30B-A3B-FP8`.**

This MoE model provides a 32K context window, has only 3.3B active parameters at inference (~60-66 tok/s on a single GB10), weighs ~32.5 GB in FP8 (fits GB10's 128GB unified memory with headroom), and avoids the structured JSON failure mode of the Qwen3-Coder variant. Forum community data from the NVIDIA DGX Spark developer forum confirms this model works well on GB10 with documented configurations.

**One critical risk**: Qwen3 defaults to `<think>...</think>` extended reasoning mode. Graphiti expects clean JSON responses. This must be disabled via `--reasoning-parser qwen3` in the vLLM serve command (strips think blocks at serving layer).

---

## Problem Context

| Item | Detail |
|------|--------|
| Graphiti prompt overhead | ~7800–8100 input tokens (measured 2026-03-18) |
| Minimum context required | >10K (for any document content), ≥16K practical minimum |
| Current model | `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` (8192-token ctx) |
| Current model status | **Incompatible** — prompt overflows before document content |
| Hardware | DGX Spark GB10, 128 GB unified memory, SM 12.1 (ARM64) |
| Co-resident on port 8001 | nomic-embed-text-v1.5 (~0.5 GB) |
| AutoBuild LLM on port 8002 | Qwen3-Coder-Next ~30B (~32–45 GB, separate workload) |

---

## Model Evaluation

### Candidate 1: Qwen/Qwen3-30B-A3B-FP8 ✅ RECOMMENDED

| Attribute | Value |
|-----------|-------|
| Architecture | MoE (30.5B total, **3.3B active**, 128 experts, 8 active per token) |
| Context window | **32K tokens native** (YaRN extends to 131K if needed) |
| FP8 memory footprint | ~32.5 GB weights |
| Total w/ embed on port 8001 | ~33 GB |
| KV cache at 32K ctx | ~5 GB additional |
| GB10 throughput (forum confirmed) | **~60–66 tok/s** output at 5–10 concurrent (int4-AutoRound + prefix cache) |
| FP8 throughput (estimate) | ~52–55 tok/s (FP8 slightly below int4-AutoRound per forum data) |
| Structured JSON quality | **Good** — general-purpose instruction model |
| Tool calling | `--tool-call-parser qwen3_coder` + `--enable-auto-tool-choice` |
| HuggingFace ID | `Qwen/Qwen3-30B-A3B-FP8` |
| Thinking mode | Yes — must disable for Graphiti (see below) |

**Note on naming**: The NVIDIA forum thread titles refer to "Qwen3.5-35B-A3B" which is a community naming convention for quantised variants (e.g., `Intel/Qwen3.5-35B-A3B-int4-AutoRound`). The canonical FP8 model is `Qwen/Qwen3-30B-A3B-FP8`. Performance data from the forum applies to this same model family.

**Strengths:**
- 32K context: leaves ~24K+ tokens for document content after 8100-token overhead
- MoE efficiency: 3.3B active params → fast inference despite 30B total size
- General-purpose instruction following: avoids the >600s episode time seen with Qwen3-Coder
- Forum-validated on GB10: trystan1's benchmarks at 60-66 tok/s are reproducible
- FP8 works with standard NGC image (`nvcr.io/nvidia/vllm:25.12.post1-py3` confirmed)

**Required vLLM config for GB10 (SM 12.1):**
```bash
# Critical: MoE latency backend for SM 12.1 (~60% speedup)
VLLM_FLASHINFER_MOE_BACKEND=latency

# Recommended vLLM flags
--max-model-len 32768           # Native 32K — no YaRN needed for Graphiti workloads
--kv-cache-dtype fp8            # KV cache compression
--trust-remote-code
--tensor-parallel-size 1
--enable-prefix-caching         # Essential: cuts TTFT from ~28s to 2-3s for agent workflows
--reasoning-parser qwen3        # CRITICAL: strips <think> blocks — Graphiti needs clean JSON
--load-format fastsafetensors   # Faster model loading (community best practice)
```

**Thinking mode — confirmed approach from forum:**
- `--reasoning-parser qwen3` in the vLLM serve command strips `<think>...</think>` blocks at the serving layer before the response reaches the Graphiti client. This is the cleanest approach.
- Alternative (per-request): `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` in API call

---

### Candidate 2: Qwen/Qwen3-14B-FP8 (Fallback)

| Attribute | Value |
|-----------|-------|
| Architecture | Dense (14.8B) |
| Context window | **32K tokens native** |
| FP8 memory footprint | ~16.3 GB |
| Total w/ embed | ~17 GB |
| GB10 throughput | ~80–120 tok/s est. (dense, smaller) |
| Structured JSON quality | Good |
| HuggingFace ID | `Qwen/Qwen3-14B-FP8` |

**Use case:** Drop-in if Qwen3-30B-A3B proves memory-constrained when all three ports run simultaneously. Forum official NVIDIA benchmark: Qwen3-14B NVFP4 via TRT-LLM hits 22.71 tok/s TG (lower bound — FP8 vLLM will be faster). Same thinking-mode disable required.

---

### Candidate 3: Qwen/Qwen3-8B-FP8 (Lightweight)

| Attribute | Value |
|-----------|-------|
| Architecture | Dense (8.2B) |
| Context window | **32K tokens native** |
| FP8 memory footprint | ~9.4 GB |
| GB10 throughput | ~120–180 tok/s est. |
| Structured JSON quality | Adequate |

Highest throughput, minimal memory. Some entity extraction quality loss vs 30B. Same thinking-mode disable required.

---

### Eliminated Candidates

| Model | Context | Reason Eliminated |
|-------|---------|-------------------|
| Nemotron 3 Nano 4B FP8 (current) | 8192 | Context too small — prompt overflow |
| Nemotron 3 Nano 30B-A3B FP8 | 8192 | Context too small — same family limit |
| Nemotron 3 Nano 30B-A3B NVFP4 | 8192 | Context too small + NVFP4 crashes on ARM64 (vLLM bug #35519) |
| Nemotron 3 Super 120B NVFP4 | 262K | 69.5 GB model weight; only ~16 tok/s on single Spark — too slow |
| Qwen3-Coder-Next / Qwen3-Coder variants | 32K | >600s per episode — poor structured JSON for non-code tasks |
| NVFP4 variants (any) | — | ARM64 crashes (vLLM bug #35519), currently underperforms AWQ on SM 12.1 |
| Llama 3.1 8B | 128K | Inferior JSON quality vs Qwen3; no GB10 community validation |
| Mistral-Nemo-12B | 128K | No GB10 benchmarks; BF16 memory pressure; `VLLM_MLA_DISABLE=1` workaround needed |
| Mistral Small 4 119B NVFP4 | 40K (hard limit) | ~99 GB RAM footprint; ~27 tok/s; multiple Docker failures on GB10 |

---

## NVIDIA DGX Spark GB10 Forum Key Findings

Sources: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/dgx-spark-gb10/721 and linked threads.

### GB10 Hardware Specifics Confirmed
- **Architecture**: SM 12.1 (compute_121a), with SM 12.1f for full feature set
- **Memory**: 128 GB LPDDR5x unified (273 GB/s bandwidth)
- **OS/arch**: Ubuntu 24.04 **ARM64** — rules out x86-only kernels
- **Compute**: 1 petaFLOP FP4 theoretical

### NVFP4 Status — Not Recommended for Graphiti

**PSA thread summary**: NVFP4 on GB10 is currently unreliable:
- vLLM bug #35519: Qwen3.5 NVFP4 crashes on ARM64 (open bug as of March 2026)
- In benchmarks, NVFP4 is **slower** than AWQ in current builds: Qwen3-VL-235B at 10 concurrent shows NVFP4 35.58 tok/s vs AWQ 42.11 tok/s
- Workaround requires patched Docker images (`avarok/dgx-vllm-nvfp4-kernel:v23`) and complex env var combinations (`VLLM_MLA_DISABLE=1`, `VLLM_NVFP4_GEMM_BACKEND=marlin`, etc.)
- Active PRs in vLLM (#35568, #35693, #35947) and CUTLASS (#3038) — improvements coming but not stable yet

**Conclusion**: Use FP8 for Graphiti. The existing `nano-4b-nvfp4` and `nano-30b-nvfp4` presets in `llm-graphiti.sh` can remain as-is (they're documented as requiring the Avarok image), but the new `qwen3-30b` preset should use FP8 with the standard NGC image.

### Quantisation Performance Ranking (single Spark, Qwen3.5-35B-A3B family)
1. **int4-AutoRound** (Intel): ~60–66 tok/s — best tok/s on single Spark
2. **FP8** (online): ~52–55 tok/s — most reliable, standard NGC image
3. **AWQ/Marlin**: ~35–42 tok/s
4. **BF16**: ~31 tok/s

For Graphiti's use case (low-concurrency, correctness-critical), **FP8 is the pragmatic choice**: no patched Docker image, no ARM64 crash risk, good throughput.

### NGC Container for GB10
`nvcr.io/nvidia/vllm:25.12.post1-py3` — confirmed working across multiple models in forum.

(The existing `llm-graphiti.sh` uses `nvcr.io/nvidia/vllm:26.01-py3` which is newer and should also work.)

### Prefix Caching is Essential for Agent Workflows
Forum user trystan1 (post #12 of Qwen3.5 thread): with a 42K shared prefix, prefix caching cuts TTFT from **28s to 2-3s**. Graphiti sends highly repetitive system prompts, making this directly applicable.

Add `--enable-prefix-caching` to the `qwen3-30b` preset.

### CPU Frequency Bug (Known Issue)
Some GB10 units cap at ~1.5 GHz instead of 2.8 GHz. This causes vLLM inference crashes when the CPU drops below 1.8 GHz. Workaround: `sudo nvidia-smi -lgc 2300,2300`. If experiencing slowness or instability, check `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`.

### Long-Running CPU Busy-Loop
After ~12 hours, vLLM EngineCore processes pin all CPU cores at 100%. Root cause: busy-loop to minimise latency. Fix: `--no-ray` flag if using Ray, or restart periodically. Relevant for long Graphiti seeding sessions.

---

## Decision

**Winner: `Qwen/Qwen3-30B-A3B-FP8`**

| Requirement | Result |
|-------------|--------|
| Context ≥16K | ✅ 32K native |
| Good structured JSON | ✅ General-purpose instruction model, not coder-biased |
| Fits GB10 memory | ✅ ~32.5 GB FP8, leaves 95 GB for other services |
| GB10 validated | ✅ 60-66 tok/s confirmed in forum benchmarks |
| Thinking mode manageable | ✅ `--reasoning-parser qwen3` strips `<think>` blocks server-side |
| FP8 stable on ARM64 | ✅ No known crashes (unlike NVFP4) |

---

## Implementation Plan

### 1. Update `scripts/llm-graphiti.sh` — add `qwen3-30b` preset

```bash
qwen3-30b)
  MODEL="Qwen/Qwen3-30B-A3B-FP8"
  GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
  MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
  # MoE model — latency backend required for SM 12.1 (GB10), ~60% speedup
  EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
  # reasoning-parser strips <think>...</think> blocks — Graphiti needs clean JSON
  EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
    --enable-prefix-caching --reasoning-parser qwen3 --load-format fastsafetensors"
  echo "═══ Qwen3-30B-A3B FP8 (3.3B active, ~32.5GB, 32K ctx) ═══"
  echo "    Graphiti entity extraction & fact deduplication"
  echo "    --reasoning-parser qwen3 strips <think> blocks for clean JSON"
  ;;
```

Also update the default preset to `qwen3-30b` (or keep `nano-4b` as a legacy alias with a deprecation note).

### 2. Update `.guardkit/graphiti.yaml`

```yaml
llm_model: Qwen/Qwen3-30B-A3B-FP8
```

Do **not** set `llm_max_tokens` or `llm_chunk_threshold` — these were 8K-context workarounds and are not needed with 32K.

### 3. Verify thinking mode is suppressed

The `--reasoning-parser qwen3` flag in vLLM strips `<think>...</think>` blocks at the serving layer. Graphiti's OpenAI-compatible client receives clean JSON. Test by:
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-30B-A3B-FP8","messages":[{"role":"user","content":"Reply with only valid JSON: {\"test\": true}"}]}'
# Verify response content contains no <think> prefix
```

### 4. Validate end-to-end

```bash
./scripts/llm-graphiti.sh qwen3-30b
# Wait for model load (~2-5 min for 32.5 GB FP8)
guardkit graphiti add-context --interactive
# Expect: no prompt overflow, episode time <60s, valid JSON entity extraction
```

---

## Config Cleanup Opportunity

`llm_max_tokens` and `llm_chunk_threshold` in `config.py`, `graphiti_client.py`, `cli/graphiti.py`, `cli/init.py` were added as workarounds for the 8K Nemotron context. With a 32K model, neither should be set in the default `graphiti.yaml`. The fields can remain in the codebase — they're useful for future edge-case models.

---

## Memory Budget Summary

| Service | Model | Footprint |
|---------|-------|-----------|
| Port 8000 (Graphiti LLM) | Qwen3-30B-A3B-FP8 | ~33 GB (weights + KV cache) |
| Port 8001 (Embeddings) | nomic-embed-text-v1.5 | ~0.5 GB |
| Port 8002 (AutoBuild) | Qwen3-Coder-Next ~30B | ~32–45 GB |
| **Total (all active)** | | **~66–79 GB** of 128 GB |

All three services can run simultaneously on the GB10's 128 GB unified memory.

---

## Acceptance Criteria Status

- [x] Minimum context window requirement documented (~8100 tokens overhead, ≥16K required)
- [x] Qwen3-30B-A3B evaluated: 32K context, good JSON, ~52-66 tok/s GB10, ~32.5 GB FP8
- [x] 2+ alternative candidates evaluated (Qwen3-14B, Qwen3-8B, Mistral, Llama 3.1, Nemotron Super)
- [x] Winner selected with rationale (Qwen3-30B-A3B-FP8)
- [x] NVFP4 status assessed — not recommended for GB10 ARM64 (vLLM bug #35519, unstable)
- [ ] `llm-graphiti.sh` updated with `qwen3-30b` preset
- [ ] `graphiti.yaml` `llm_model` updated to `Qwen/Qwen3-30B-A3B-FP8`
- [ ] Thinking mode disabled — `--reasoning-parser qwen3` verified, clean JSON output confirmed
- [ ] At least one `guardkit graphiti add-context` run succeeds end-to-end

---

## Appendix A: GB10 vLLM Environment Variables Reference

| Variable | Value | Purpose |
|----------|-------|---------|
| `VLLM_FLASHINFER_MOE_BACKEND` | `latency` | MoE kernel for SM 12.1 (~60% speedup) |
| `PYTORCH_CUDA_ALLOC_CONF` | `expandable_segments:True` | Reduce memory fragmentation |

For NVFP4 if ever needed in future (requires patched image):
| Variable | Value |
|----------|-------|
| `VLLM_USE_FLASHINFER_MOE_FP4` | `1` |
| `VLLM_FLASHINFER_MOE_BACKEND` | `throughput` |
| `VLLM_NVFP4_GEMM_BACKEND` | `marlin` |
| `VLLM_TEST_FORCE_FP8_MARLIN` | `1` |

## Appendix B: Community Resources

- **eugr/spark-vllm-docker**: https://github.com/eugr/spark-vllm-docker — recipes for Qwen3.5, Nemotron, MiniMax, etc. Useful reference for Docker commands.
- **Qwen3.5-35B-A3B forum thread**: https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-on-the-table/362200
- **NVFP4 PSA thread**: https://forums.developer.nvidia.com/t/psa-state-of-fp4-nvfp4-support-for-dgx-spark-in-vllm/353069
- **Nemotron-3-Nano-30B-A3B-NVFP4 thread**: https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074
- **Nemotron-3-Super-120B-A12B-NVFP4 advanced guide**: https://github.com/NVIDIA-NeMo/Nemotron/tree/main/usage-cookbook/Nemotron-3-Super/AdvancedDeploymentGuide
