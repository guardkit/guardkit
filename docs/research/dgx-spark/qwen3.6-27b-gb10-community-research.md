# Qwen3.6-27B on GB10 — Community Research Summary

**Date:** 2026-04-28
**Sources:** NVIDIA DGX Spark forum threads (April 22–28, 2026), HuggingFace model cards, community benchmarks
**Purpose:** Collate real-world GB10 performance data for the Qwen3.6-27B validation decision in `gb10-model-requirements-matrix.md`

---

## 1. Headline Numbers — Single GB10

| Configuration | Quant | Footprint | tok/s (single, tg128) | Tool Eval | Source |
|---|---|---|---|---|---|
| FP8 baseline (no spec decode) | FP8 | ~27 GB | **7.8** | — | starkrun |
| FP8 + MTP (num_speculative_tokens=3) | FP8 | ~27 GB | **15.2** | 100/100 | starkrun, carlos.albarran.mx |
| NVFP4 (sakamakismile) | NVFP4 | ~26 GB | TBD (RTX PRO benchmarks only) | — | sakamakismile |
| PrismaQuant 5.5bit + DFlash | Mixed BF16/NVFP4 | ~22 GB | **31-41** | — | djordjestojanovic1992 |
| Q4_K_M via llama.cpp + Lucebox-Hub | Q4_K_M | ~16 GB | **33-45** (task-dependent) | — | joshua.dale.warner |
| FP8 + DFlash + DDTree (iotcoi, claimed) | FP8 | ~27 GB | **136 avg, 200 peak** | — | iotcoi via X (not public) |

### Why the FP8 baseline is so slow

josephbreda explained the physics: at FP8 you move 27B × 1 byte = ~27 GB per decode step. GB10 has ~270 GB/s bandwidth. That gives a theoretical ceiling of ~10 tok/s. The measured 7.8 tok/s is close to that bound. **This is a memory-bandwidth wall, not a compute wall.** Speculative decoding (MTP, DFlash) breaks through by generating multiple tokens per forward pass.

The practical implication: **FP8 without speculative decoding is too slow for code generation workloads on a single GB10.** You need either MTP/DFlash or a smaller quantisation to be productive.

---

## 2. Headline Numbers — Dual GB10 (for reference, Rich has a single)

| Configuration | tok/s (c1, tg128) | tok/s code (DFlash) | Tool Eval | Source |
|---|---|---|---|---|
| FP8 baseline (vLLM, TP=2) | 14.4 | — | 100/100 | serapis |
| FP8 + MTP (TP=2) | 7.2 (worse — MTP adds allgather overhead across nodes) | — | — | serapis |
| FP8 + DFlash (TP=2) | — | **57.5** (code), **46.5** (structured) | 14.5/15 (TC-14 partial) | arctic.gus, serapis |

MTP actually makes things *worse* on dual-node because each speculative token adds an allgather across the inter-node link.

---

## 3. Tool Calling — Confirmed Excellent

**100/100 on tool-eval-bench.** Both serapis (dual node) and carlos.albarran.mx (single node) got perfect scores: 15/15 scenarios passed, covering tool selection, parameter precision, multi-step chains, restraint/refusal, and error recovery.

The one weak spot across runs: TC-14 (Malformed Response) occasionally scored partial — the model acknowledged errors but didn't always attempt an alternative source. This is a minor edge case.

**vLLM flags confirmed working:** `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`

The `qwen3_coder` tool parser is the community standard for Qwen3.x tool calling on GB10.

---

## 4. Key Quantisation Options

### FP8 (official: Qwen/Qwen3.6-27B-FP8)
- ~27 GB footprint
- Best quality, slowest on single GB10 without spec decode
- With MTP (num_speculative_tokens=3): 15.2 tok/s — usable but not fast
- Community consensus: "this model will highly benefit from the typical Intel or cyankiwi treatment" (serapis)

### NVFP4 (sakamakismile/Qwen3.6-27B-NVFP4, AEON-7 variant)
- ~26 GB footprint (only slightly smaller than FP8 due to BF16-preserved layers)
- josephbreda's math: ~7 GB of weight movement per step → theoretical ~38 tok/s ceiling
- Vision tower preserved at BF16; SSM/GatedDeltaNet layers preserved at BF16
- `gpu-memory-utilization 0.90` max recommended; `0.85` for production stability
- New AEON-7 variant with DFlash just released (2026-04-27) — purpose-built for GB10

### PrismaQuant 5.5bit (rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm)
- Mixed precision: 300 layers at NVFP4, 30 at MXFP8, 87 at BF16
- Author (tenari) claims: "a model that's 25% bf16 and 75% nvfp4 is better than one that is fp8 through-and-through"
- Uses sensitivity-aware per-layer quantisation — keeps quality-critical layers in higher precision
- Requires vLLM 0.11+ with compressed-tensors support
- Best balance of speed and quality for the 27B dense model

### Q4_K_M GGUF (via llama.cpp)
- ~16 GB footprint — leaves massive headroom on GB10
- 33-45 tok/s depending on task type (JSON tasks fastest at 44-45 tok/s)
- Best throughput for single-GB10 llama.cpp serving
- Quality vs FP8 is the open question — community hasn't settled this for 3.6 yet

---

## 5. Speculative Decoding Landscape

Three approaches, in order of community maturity:

### MTP (Multi-Token Prediction, built into Qwen3.6)
- Native support in vLLM via `--speculative-config '{"method": "mtp", "num_speculative_tokens": 3}'`
- Single GB10: 1.9x speedup (7.8 → 15.2 tok/s)
- Dual GB10: actually slower due to allgather overhead — avoid with TP=2
- Mature and stable; recommended as baseline

### DFlash (z-lab/Qwen3.6-27B-DFlash)
- Architecture-matched draft model for speculative decode
- Single GB10 via llama.cpp: reports of 33-45 tok/s (Q4_K_M)
- Dual GB10 via vLLM: 46-57 tok/s for code/structured tasks
- z-lab drafter model is publicly available on HuggingFace
- Acceptance rate: 85-94% for code, 25-36% for filler text

### DDTree (iotcoi's work, not publicly available)
- Combined with DFlash: 136 tok/s average, 200 tok/s peak on single GB10 (claimed)
- iotcoi is "not openly sharing" the implementation
- joshua.dale.warner working on open implementation: "I will have dflash + ddtree implemented by tomorrow hopefully"
- Lucebox-Hub (Luce-Org/lucebox-hub) added consumer Blackwell support and may include DDTree

---

## 6. Deployment Recipes — Single GB10 (confirmed working)

### Recipe A: FP8 + MTP (simplest, proven)
```bash
vllm serve Qwen/Qwen3.6-27B-FP8 \
    --host 0.0.0.0 --port 8080 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.75 \
    --max-model-len 32768 \
    --max-num-batched-tokens 16384 \
    --enable-prefix-caching \
    --enable-chunked-prefill \
    --max-num-seqs 4 \
    --load-format auto \
    --attention-backend flashinfer \
    --kv-cache-dtype fp8 \
    --trust-remote-code \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder \
    --reasoning-parser qwen3 \
    --speculative-config '{"method": "mtp", "num_speculative_tokens": 3}' \
    --override-generation-config '{"temperature": 0.6, "top_p": 0.95, "top_k": 20}' \
    --default-chat-template-kwargs '{"preserve_thinking": true}'
```

Expected: ~15 tok/s, 100/100 tool calling, ~27 GB model + KV cache headroom.
Context: `max-model-len 32768` confirmed by carlos.albarran.mx. For 256K context, increase gpu-memory-utilization (but co-existence with Graphiti becomes tight).

### Recipe B: Q4_K_M via llama.cpp (fastest, smallest footprint)
```bash
llama-server \
    -hf "unsloth/Qwen3.6-27B-GGUF:Q4_K_M" \
    --host 0.0.0.0 --port 8080 \
    --alias qwen3.6-27b \
    -ngl 999 \
    --no-mmap \
    --flash-attn on \
    --jinja \
    --ctx-size 32768 \
    -np 1
```

Expected: ~33-45 tok/s, ~16 GB footprint, massive headroom for co-existence.
Caveat: quality vs FP8 not yet community-validated for 3.6.

### Recipe C: PrismaQuant 5.5bit (best quality/speed balance, newer)
```bash
vllm serve rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm \
    --trust-remote-code \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.85 \
    --speculative-config '{"method":"mtp","num_speculative_tokens":3}'
```

Expected: ~30+ tok/s with MTP, quality between Q4 and FP8.

---

## 7. Implications for the Model Requirements Matrix

### The "one model, no swap" thesis: VALIDATED on quality, NUANCED on speed

**Quality:** Tool calling is confirmed excellent (100/100). The model handles coding, structured output, and multi-step chains. Community consensus is that it's a step forward from 3.5 across the board except one near-tie STEM benchmark.

**Speed on single GB10:** The FP8 baseline (7.8 tok/s) is too slow for productive code generation. With MTP it reaches 15 tok/s — usable but not fast. The Q4_K_M or PrismaQuant paths deliver 30-45 tok/s, which is competitive with Qwen3-Coder-Next int4's 66.7 tok/s (the current AutoBuild candidate).

**Memory:** At Q4_K_M (~16 GB), the total fleet footprint is:

| Component | Footprint |
|---|---|
| Graphiti (Qwen2.5-14B FP8) | ~14 GB |
| nomic-embed | ~1 GB |
| Qwen3.6-27B Q4_K_M | ~16 GB |
| **Total** | **~31 GB** |

That's 97 GB of headroom on a 128 GB box. Enough for Gemma 4 26B specialist (~26 GB) to be loaded simultaneously with zero swaps.

### Recommended validation path for Rich

1. **Start with Recipe B** (Q4_K_M via llama.cpp): fastest to set up, smallest footprint, best co-existence with Graphiti. Test tool calling with `rag_retrieval` and `write_output` via llama-swap. Run the `architect-agent-probe` domain.

2. **If quality is insufficient**, step up to PrismaQuant 5.5bit (Recipe C) or FP8 + MTP (Recipe A).

3. **Test all three matrix roles:** Graphiti entity extraction (JSON output), AutoBuild Player (tool calling + code), Coach/Forge reasoning (structured evaluation).

4. **Monitor the DDTree situation.** If joshua.dale.warner or Lucebox-Hub deliver an open DDTree implementation, FP8 speeds jump to 50-130+ tok/s on single GB10 — at which point FP8 becomes viable without quantisation trade-offs.

---

## 8. Community References

### Forum threads (gold)
- ["Qwen3.6-27B is out!"](https://forums.developer.nvidia.com/t/qwen3-6-27b-is-out/367503) — primary benchmarks thread, 30+ posts
- ["What's the best speed we can get with Qwen 3.6 27B without quantizing?"](https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561) — josephbreda's bandwidth math
- ["Qwen3.6-27B-DFlash link"](https://forums.developer.nvidia.com/t/qwen3-6-27b-dflash-link/367803) — DFlash model location
- ["Qwen3.5 Tool Calling finally fixed (possibly)"](https://forums.developer.nvidia.com/t/qwen3-5-tool-calling-finally-fixed-possibly/366451/22) — qwen_xml parser fix for Claude Code
- ["Introducing PrismaQuant"](https://forums.developer.nvidia.com/t/introducing-prismaquant/367085) — mixed-precision quantisation approach

### Model cards
- [Qwen/Qwen3.6-27B-FP8](https://huggingface.co/Qwen/Qwen3.6-27B-FP8) — official FP8
- [rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm](https://huggingface.co/rdtand/Qwen3.6-27B-PrismaQuant-5.5bit-vllm) — mixed-precision
- [sakamakismile/Qwen3.6-27B-NVFP4](https://huggingface.co/sakamakismile/Qwen3.6-27B-NVFP4) — NVFP4
- [z-lab/Qwen3.6-27B-DFlash](https://huggingface.co/z-lab/Qwen3.6-27B-DFlash) — DFlash drafter
- [AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-DFlash](https://github.com/AEON-7/Qwen3.6-27B-AEON-Ultimate-Uncensored-DFlash) — NVFP4 + DFlash deployment guide

### Tools
- [Lucebox-Hub](https://github.com/Luce-Org/lucebox-hub) — consumer Blackwell DFlash+DDTree support
- [tool-eval-bench](https://github.com/serapis/tool-eval-bench) — the tool calling benchmark used in forum tests
- [llama-benchy](https://github.com/eugr/llama-benchy) — throughput benchmark

---

*Prepared: 2026-04-28 | Cross-references: gb10-model-requirements-matrix.md, dark-factory-economics-and-model-serving.md*
