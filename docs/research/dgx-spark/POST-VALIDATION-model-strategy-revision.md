# Post-Validation Analysis: Model Strategy for GB10

**Date:** 2026-04-28
**Predecessor:** `RESULTS-qwen3.6-27b-validation.md` (Claude Code run), `qwen3.6-27b-gb10-community-research.md`
**Purpose:** Revise the model strategy based on the validation results and deeper forum research.

---

## 1. What the validation proved

Qwen3.6-27B Q4_K_M passed every quality test (tool calling, JSON extraction, reasoning) but hit **8.35 tok/s single-stream** — the GB10 memory-bandwidth floor for dense models at this scale. Claude Code independently confirmed the same ~8.8 tok/s ceiling on vLLM Qwen2.5-14B-FP8 single-stream on the same hardware.

**The 33-45 tok/s community numbers were from batched or speculative-decode setups, not single-stream.** The runbook's speed expectation was wrong. This is not a Qwen3.6-27B problem — it's a physics problem: 27B × 1 byte = 27 GB per decode step ÷ 270 GB/s bandwidth = ~10 tok/s theoretical ceiling.

## 2. The physics: why MoE wins on GB10

The memory-bandwidth constraint changes everything for model selection on GB10:

| Architecture | Params | Active params/step | Bytes moved/step | Theoretical ceiling | Observed |
|---|---|---|---|---|---|
| Dense 27B (FP8) | 27B | 27B | ~27 GB | ~10 tok/s | 7.8-8.8 tok/s |
| Dense 27B (Q4) | 27B | 27B | ~16 GB | ~17 tok/s | 8.35 tok/s* |
| **MoE 35B-A3B (FP8)** | 35B | **3B** | **~20 GB†** | **~14 tok/s** | **31-50 tok/s‡** |

\* Q4 should theoretically be faster but llama.cpp's CUDA kernel path on GB10 doesn't fully exploit the reduced weight movement yet.
† MoE has shared expert + routing overhead beyond the 3B active expert params.
‡ MoE kernel optimisations (FlashInfer, batched expert dispatch) add efficiency beyond the naive calculation. Community reports 31-50 tok/s baseline.

**With DFlash speculative decoding on MoE 35B-A3B:** AEON-7 reports 117 tok/s single-stream (greedy/agentic at T=0) on a single GB10.

The conclusion is clear: **for a single GB10, MoE architecture is the right answer for throughput-sensitive roles.** Dense 27B is quality-competitive but bandwidth-limited to ~8-15 tok/s regardless of quantisation.

## 3. Revised model strategy

### Keep what works

| Role | Model | Why |
|---|---|---|
| Graphiti LLM | **Qwen2.5-14B-Instruct-FP8** (unchanged) | Proven JSON extraction via xgrammar. MoE models have known JSON contamination risks. ~14 GB via vLLM on :8000 |
| Embeddings | **nomic-embed-text-v1.5** (unchanged) | 768-dim locked by FalkorDB index. ~1 GB via vLLM on :8001 |

### Change the workhorse model

Replace the "Coder-Next vs GPT-OSS 120B swap" architecture with **Qwen3.6-35B-A3B-FP8** as the primary workhorse:

| Attribute | Previous plan | Revised plan |
|---|---|---|
| Player model | Qwen3-Coder-Next FP8 (~60 GB, 32.9 tok/s) | **Qwen3.6-35B-A3B-FP8 (~20 GB active, 31-50 tok/s)** |
| Coach/Forge model | GPT-OSS 120B MXFP4 (~63 GB, 56 tok/s) | **Same model** (reasoning quality is excellent) |
| Swap required? | Yes — Coder ↔ GPT-OSS | **No swap needed** — one model serves both roles |
| With DFlash? | N/A | **117 tok/s single-stream** (agentic/greedy at T=0) |

### Why Qwen3.6-35B-A3B over the dense 27B

1. **5-15× faster single-stream decode** on GB10 (MoE moves ~3B active params vs 27B)
2. **Tool calling confirmed working** — community using `--tool-call-parser qwen3_coder` with `preserve_thinking` enabled
3. **Native tool calling is fixed in Qwen3.6** — the old `fix-qwen3.5-chat-template` mod should NOT be applied; native template with `--default-chat-template-kwargs '{"preserve_thinking": true}'` is the correct path
4. **DFlash drafter available**: `z-lab/Qwen3.6-35B-A3B-DFlash` (public on HuggingFace)
5. **AEON-7 production-ready deployment**: pre-built Docker image, NVFP4 quantisation, documented for GB10
6. **Quality competitive with or better than 27B** — benchmarks show 3.6 MoE is a step up from 3.5 across the board
7. **Smaller effective footprint** — FP8 weights ~20 GB (the rest is MoE expert parameters that only load on demand)

### Why NOT Qwen3.6-27B for the workhorse

The dense 27B remains valuable for roles where throughput doesn't matter (batch processing, overnight dataset generation), but for interactive AutoBuild Player-Coach loops where latency directly impacts build time, MoE is the right architecture on GB10's bandwidth-constrained unified memory.

## 4. Revised memory budget

### Scenario A: MoE workhorse without DFlash

```
Forever group (always loaded):
  Qwen2.5-14B (Graphiti)           ~14 GB (vLLM pre-allocates ~50 GB with KV cache)
  nomic-embed (embeddings)          ~1 GB

Builders group:
  Qwen3.6-35B-A3B-FP8              ~20 GB model + KV cache
  
Total: ~85 GB  (39 GB headroom)
```

### Scenario B: MoE workhorse with DFlash (target state)

```
Forever group:
  Qwen2.5-14B (Graphiti)           ~50 GB (vLLM with KV cache pre-alloc)
  nomic-embed (embeddings)          ~1 GB

Builders group:
  Qwen3.6-35B-A3B-FP8 + DFlash    ~25 GB (target model + small drafter)
  
Total: ~76 GB  (48 GB headroom)
```

### Scenario C: Full fleet (Scenario B + fine-tuned specialist)

```
Everything above + Gemma 4 26B specialist: ~102 GB  (22 GB headroom)
```

Tight but feasible. The specialist only loads when needed (Architect/Tutor sessions), and can evict the MoE workhorse via llama-swap.

## 5. Revised llama-swap configuration

The builders group simplifies dramatically:

```yaml
  "qwen36-35b":
    name: "AutoBuild Player + Coach + Forge (Qwen3.6-35B-A3B-FP8)"
    # Option A: vLLM with DFlash (best performance)
    # Use AEON-7 container: ghcr.io/aeon-7/vllm-spark-omni-q36:v1.2
    # Option B: llama.cpp (simpler, co-existence friendly)
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen36-35b/Qwen3.6-35B-A3B-FP8.gguf
      --alias qwen36-35b
      --ctx-size 65536
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --reasoning off
      --temp 0.6
      --top-p 0.95
    checkEndpoint: /health
    ttl: 1800
    concurrencyLimit: 2
    aliases:
      - "autobuild-player"
      - "coach"
      - "jarvis-reasoner"
      - "forge-orchestrator"
      - "dataset-factory"
      - "claude-sonnet-4-6"
```

Note: the vLLM + DFlash path (AEON-7 container) is significantly faster (117 tok/s vs ~30-50 tok/s) but requires a Docker-based deployment rather than llama.cpp. Worth the complexity for the Player role.

## 6. Next steps — Runbook v2

A revised runbook should test **Qwen3.6-35B-A3B-FP8** instead of the dense 27B:

1. **Phase 1**: Download `Qwen/Qwen3.6-35B-A3B-FP8` and serve via vLLM with the spark-vllm-docker recipe
2. **Phase 2**: Re-run tool calling tests (P2.1-P2.3 from original runbook) with `--tool-call-parser qwen3_coder --default-chat-template-kwargs '{"preserve_thinking": true}'`
3. **Phase 3**: Re-run JSON extraction tests (expecting MoE to be riskier here — this validates whether the JSON contamination bug persists in 3.6)
4. **Phase 4**: Re-run Coach/Forge reasoning tests
5. **Phase 5**: Measure single-stream tok/s — expect 31-50 tok/s baseline, clearing the 20 tok/s gate easily
6. **Phase 6 (bonus)**: If vLLM + DFlash works, measure with `z-lab/Qwen3.6-35B-A3B-DFlash` drafter — expect 50-117 tok/s

### What about Qwen3.6-27B?

Keep it as a validated fallback for roles where co-existence headroom matters more than speed:
- Dataset factory overnight runs (latency doesn't matter, headroom does)
- Batch evaluation/scoring
- Any role where the Forge loop can tolerate 8 tok/s

## 7. Key forum findings to preserve

1. **Native tool calling is fixed in Qwen3.6** — do NOT apply `fix-qwen3.5-chat-template` mod. Use `--default-chat-template-kwargs '{"preserve_thinking": true}'` instead. This was confirmed by multiple community members.

2. **AEON-7 is the reference implementation** for DFlash on GB10. Their pre-built Docker images (`ghcr.io/aeon-7/vllm-spark-omni-q36:v1.2`) include all GB10-specific patches (SM121 CUTLASS NVFP4, Mamba cache alignment, M-RoPE fallback).

3. **`gpu-memory-utilization` max on GB10 is 0.85-0.88** — above that, unified memory thrashes. AEON-7 recommends 0.85 for production.

4. **vLLM pre-allocates KV cache aggressively** — Qwen2.5-14B with `max_model_len=32768` uses ~50 GB, not the ~14 GB model-weights-only estimate. This is the real co-existence budget.

5. **DFlash acceptance rate varies by task**: code prompts 78-94%, structured 85%, filler/creative 16-25%. Agentic/greedy workloads (T=0) get the best speedup. This is ideal for AutoBuild.

---

## References

- AEON-7 Qwen3.6 NVFP4 + DFlash repo: https://github.com/AEON-7/Qwen3.6-NVFP4-DFlash
- AEON-7 vllm-dflash (27B): https://github.com/AEON-7/vllm-dflash
- Tool calling fix thread: https://forums.developer.nvidia.com/t/qwen3-5-tool-calling-finally-fixed-possibly/366451
- Qwen3.6-35B-A3B landing thread: https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822
- DFlash drafter: https://huggingface.co/z-lab/Qwen3.6-35B-A3B-DFlash
- spark-vllm-docker: https://github.com/eugr/spark-vllm-docker

---

*Prepared: 2026-04-28 | Supersedes speed expectations in gb10-model-requirements-matrix.md §4*
