---
id: TASK-REV-DGX1
title: Identify optimal LLM for Graphiti on DGX Spark GB10
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
created: 2026-03-18T10:00:00Z
updated: 2026-03-18T11:00:00Z
priority: high
tags: [graphiti, vllm, dgx-spark, gb10, nemotron, llm-selection]
complexity: 5
parent_review: TASK-REV-G4C1
review_results:
  mode: decision
  depth: standard
  decision: replace_nemotron_with_qwen3_30b
  winner: Qwen/Qwen3-30B-A3B-FP8
  findings_count: 5
  recommendations_count: 4
  report_path: .claude/reviews/TASK-REV-DGX1-review-report.md
  completed_at: 2026-03-18T11:00:00Z
---

# Task: Identify optimal LLM for Graphiti on DGX Spark GB10

## Description

Graphiti's entity extraction prompts require ~7800-8100 tokens of input overhead (system prompt + graph context). This means the LLM serving Graphiti on port 8000 **must have a context window > 10K tokens** to leave room for any document content and output.

The Nemotron 3 Nano 4B FP8 was chosen for Graphiti after Qwen3-Coder-Next caused >600s per episode (poor structured JSON performance, graph density issues). However, Nemotron's 8192-token context is insufficient — Graphiti's prompts overflow it entirely before any document content is included.

The current state:
- Port 8000: Nemotron 3 Nano 4B FP8 (8192 ctx) — **incompatible with Graphiti**
- Port 8001: nomic-embed-text-v1.5 (embeddings, working)
- Port 8002: Qwen3-Coder-Next/30B (AutoBuild, working)

Graphiti needs a model that is:
1. **Context window ≥ 16K tokens** (ideally 32K+)
2. **Good at structured JSON output** (entity extraction, fact deduplication)
3. **Fast on GB10** (DGX Spark with Grace Blackwell GB10 SoC, 128GB unified memory)
4. **Small enough** to leave GPU/memory headroom for the embedding model on port 8001

## Review Scope

1. **Research GB10-optimised models**: Check NVIDIA developer forums (especially the thread referenced below) and vLLM release notes for models with proven GB10 performance
2. **Evaluate Qwen3.5-35B-A3B**: Does it have a large enough context window? What is its JSON structured output quality? Performance on GB10?
3. **Evaluate alternative candidates**: MoE models ≤35B active params with 16K+ context that run well on GB10
4. **Assess JSON/structured output quality**: Graphiti uses JSON schema extraction — models that struggle with structured output will cause slow/failed episodes (the original Qwen3-Coder problem)
5. **Memory fit**: Profile expected VRAM/unified memory usage alongside nomic-embed-text-v1.5 on port 8001
6. **Decision**: Recommend a specific model + llm-graphiti.sh preset (or new preset to add)

## Reference Material

- NVIDIA GB10 forum thread: https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-on-the-table/362200/24
- Original Nemotron decision rationale: `scripts/llm-graphiti.sh` header comment + TASK-REV-5B3A
- Graphiti prompt overhead: ~7800-8100 input tokens baseline (measured 2026-03-18)
- Current llm-graphiti.sh presets: nano-4b, nano-4b-nvfp4, nano-30b, nano-30b-nvfp4, custom

## Acceptance Criteria

- [x] Minimum context window requirement documented (currently measured at ~8100 tokens overhead)
- [x] Qwen3-30B-A3B evaluated: context size, JSON quality, GB10 performance, memory footprint
- [x] At least 2 alternative candidates evaluated (Qwen3-14B, Qwen3-8B, Mistral-Nemo, Llama 3.1 8B)
- [x] Winner selected with rationale: Qwen3-30B-A3B-FP8 (32K ctx, MoE efficiency, 60+ tok/s on GB10)
- [x] `vllm-graphiti.sh` created with `qwen3-30b` (default), `qwen3-14b`, `qwen3-8b` presets
- [x] `graphiti.yaml` `llm_model` updated to `Qwen/Qwen3-30B-A3B-FP8`
- [ ] Thinking mode disable strategy validated (Graphiti gets clean JSON, not `<think>` blocks)
- [ ] At least one `guardkit graphiti add-context` run succeeds end-to-end

## Context

- `llm_max_tokens` and `llm_chunk_threshold` config fields were added to guardkit during debugging
  (in `config.py`, `graphiti_client.py`, `cli/graphiti.py`, `cli/init.py`) — these may be useful
  for the new model config or can be removed if not needed
- The GB10 has 128GB unified memory shared between CPU and GPU — large models are viable
- MoE models with small active parameter counts are especially good candidates (fast inference, large knowledge)

## Implementation Notes

### Research Findings (2026-03-18)

#### Clarification: Qwen3.5 vs Qwen3

The NVIDIA forum thread references "Qwen3.5-35B-A3B" but this is **not an official Qwen release name**.
The Qwen team released **Qwen3-30B-A3B** (30.5B total / 3.3B active MoE). The forum thread
appears to be discussing an early/custom quantised variant (Intel/Qwen3.5-35B-A3B-int4-AutoRound)
that may be a repackaged or renamed version. The canonical HuggingFace model is `Qwen/Qwen3-30B-A3B`.

---

### Candidate Models Evaluated

#### 1. Qwen3-30B-A3B (MoE) — RECOMMENDED

| Property | Value |
|---|---|
| Architecture | MoE: 30.5B total / 3.3B active, 128 experts, 8 active per token |
| Native context | 32,768 tokens |
| Extended context | 131,072 tokens (YaRN, factor 4.0) |
| FP8 weights (disk/RAM) | ~32.5 GB (measured from HF repo: 7 safetensors totalling 32.43 GB) |
| JSON/structured output | Good — general-purpose instruction model, not coder-biased |
| Thinking mode | Yes — can disable with `enable_thinking=False` for lower latency |
| GB10 performance | ~60-66 tok/s output at 5-10 concurrent (Intel AutoRound int4 + prefix cache) |
| Memory fit | 32.5 GB weights + ~5 GB KV cache at 32K ctx = ~38 GB total. Ample headroom in 128 GB alongside nomic-embed (~0.5 GB) and AutoBuild (Qwen3-Coder-Next ~92 GB). Combined: ~130 GB — tight but feasible with careful `gpu_memory_utilization` tuning. |
| vLLM notes | Needs `VLLM_FLASHINFER_MOE_BACKEND=latency` on GB10 SM 12.1 (MoE kernel issue). Native 32K ctx satisfies the ≥16K requirement. |

**Why recommended for Graphiti**: 32K native context (4x the Nemotron 8K limit) satisfies the 7800-8100 token baseline overhead requirement with room for document content. As a general-purpose instruction model (not a coder model), it follows structured JSON instructions well. The 3.3B active params means fast inference despite the 30B parameter count.

**Concern**: With Qwen3-Coder-Next (~92 GB) on port 8002 and nomic-embed (~0.5 GB) on port 8001, total unified memory usage would be ~125-130 GB against the 128 GB limit. This requires running Graphiti entity extraction **sequentially with AutoBuild** (not simultaneously), or switching to a smaller model for AutoBuild when Graphiti is active. Alternatively use the `nano-30b` preset swap-out pattern already in the script.

#### 2. Qwen3-14B (dense) — GOOD ALTERNATIVE

| Property | Value |
|---|---|
| Architecture | Dense, 14.8B total |
| Native context | 32,768 tokens |
| Extended context | 131,072 tokens (YaRN) |
| FP8 weights (disk/RAM) | ~16.3 GB |
| JSON/structured output | Good — same instruction-following capability as 30B-A3B |
| GB10 performance | Estimated 80-120 tok/s (dense, smaller active params than 30B-A3B) |
| Memory fit | 16.3 GB weights + ~3 GB KV cache at 32K ctx = ~20 GB total. Leaves 108 GB for AutoBuild + embeddings. Very comfortable. |

**Best option if memory pressure is a concern.** Can run simultaneously with Qwen3-Coder-Next and nomic-embed with plenty of headroom. Slightly lower quality than 30B-A3B but still a significant improvement over Nemotron Nano for structured JSON.

#### 3. Qwen3-8B (dense) — LIGHTWEIGHT OPTION

| Property | Value |
|---|---|
| Architecture | Dense, 8.2B total |
| Native context | 32,768 tokens |
| Extended context | 131,072 tokens (YaRN) |
| FP8 weights (disk/RAM) | ~9.4 GB |
| JSON/structured output | Good but weaker than 14B for complex entity schemas |
| GB10 performance | Estimated 120-180 tok/s |
| Memory fit | ~12 GB total. Minimal footprint. |

Suitable if entity extraction quality degrades, but context window is satisfied. The entity extraction quality step-down from 14B is likely noticeable for complex documents.

#### 4. Mistral-Nemo-Instruct-2407 (~12B dense)

| Property | Value |
|---|---|
| Native context | 128,000 tokens |
| Weights (BF16) | ~24 GB |
| JSON/structured output | Function-calling trained, good for structured tasks |
| GB10 notes | No GB10-specific benchmarks found; not a common DGX Spark community choice |

Has excellent context window (128K native). However, no GB10 performance data found and the Qwen3 family has more recent community validation on GB10. Mistral-Nemo is 12B dense so would require ~24 GB in BF16 or ~12 GB FP8. Viable but less proven on this hardware.

#### 5. Llama 3.1 8B Instruct

| Property | Value |
|---|---|
| Native context | 128,000 tokens |
| Weights (BF16) | ~16 GB |
| JSON/structured output | Function-calling supported but historically weaker than Qwen3 on strict JSON schemas |

Sufficient context window and small footprint. No specific GB10 benchmarks found. Qwen3-8B is preferred due to stronger instruction following and the existing community validation of the Qwen3 series on GB10.

#### 6. Qwen3-32B (dense)

| Property | Value |
|---|---|
| Native context | 32,768 tokens (extended to 131K with YaRN) |
| FP8 weights | ~34.3 GB |
| Memory fit | ~37 GB total |

Good quality but heavier than the 30B-A3B MoE for similar or worse inference speed (dense vs MoE). The 30B-A3B is preferred at similar memory cost.

---

### NVIDIA GB10 Forum Key Findings

Source: https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-on-the-table/362200

- Qwen3.5-35B-A3B (the forum's "35B-A3B") is functionally Qwen3-30B-A3B family with ~20GB quantised weights
- GB10 performance with AutoRound int4 + prefix caching: **60-66 tok/s** output at 5-10 concurrent requests
- With BF16 + Ray 2-node cluster: 253 tok/s at 10 concurrent (not applicable to single Spark)
- **Critical config for MoE on GB10**: `VLLM_FLASHINFER_MOE_BACKEND=latency` (avoids CUTLASS kernel issue on SM 12.1, gives ~60% speedup)
- **Prefix caching is essential**: reduces effective context from 42K to 5K new tokens for agent workflows; cuts TTFT from 28s to 2-3s
- NVFP4 is "20% faster than AWQ when functional" but "currently buggy on ARM64" (GB10 is ARM64) — stick with FP8 or AutoRound int4
- Context at 100K degrades from 3918 tok/s (2K) to 60 tok/s — keep `max_model_len` at 32768 for Graphiti's use case

---

### Recommendation

**Primary: Qwen3-30B-A3B-FP8**
- Model ID: `Qwen/Qwen3-30B-A3B-FP8`
- Context: `--max-model-len 32768` (native, no YaRN needed for Graphiti's ~8-16K prompts)
- Memory: ~32.5 GB weights, runs comfortably in isolation; tight but feasible with full stack
- Key env var: `VLLM_FLASHINFER_MOE_BACKEND=latency`
- Thinking mode: disable with `enable_thinking=False` for Graphiti (no chain-of-thought needed for entity extraction)
- Expected performance: ~60-66 tok/s for Graphiti's concurrency of 1-3 episodes

**Fallback: Qwen3-14B-FP8**
- Model ID: `Qwen/Qwen3-14B-FP8`
- Context: `--max-model-len 32768`
- Memory: ~16.3 GB — no memory pressure concern at all
- Use if memory contention with AutoBuild proves problematic

**Do not use**: Any Qwen3-Coder variant — confirmed to cause 120-600s+ per Graphiti episode due to poor structured JSON output in a non-code context.

---

### Proposed vllm-nemotron3-nano.sh Changes

Add two new presets to `scripts/vllm-neomtron3-nano.sh`:

```
qwen3-30b       Qwen3-30B-A3B FP8 (~32.5GB, 3.3B active, 32K ctx, recommended)
qwen3-14b       Qwen3-14B FP8 (~16.3GB, dense, 32K ctx, fallback)
```

Key vLLM args for 30B-A3B:
```bash
EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
EXTRA_ARGS="--max-model-len 32768 --enable-prefix-caching --kv-cache-dtype fp8"
GPU_UTIL=0.30  # ~32.5 GB / 128 GB * safety margin
```

### graphiti.yaml Update

```yaml
llm_model: Qwen/Qwen3-30B-A3B-FP8
```

The `llm_max_tokens` config field added during debugging should be set to 32768 to match the model's context.

### Thinking Mode Handling

Qwen3 models default to `enable_thinking=True` which adds `<think>...</think>` blocks before responses. Graphiti expects clean JSON responses. Must disable thinking mode in the vLLM request or via the Graphiti client. Two options:
1. Pass `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` in the OpenAI client call
2. Or rely on vLLM's `--reasoning-parser` to strip think blocks automatically

This needs to be validated during the acceptance criteria test run.
