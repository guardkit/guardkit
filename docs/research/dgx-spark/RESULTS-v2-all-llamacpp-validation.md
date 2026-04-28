# Results: All-llama.cpp Architecture Validation (Runbook v2)

**Date:** 2026-04-28
**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 124 GB unified memory
**Predecessor:** `RESULTS-qwen3.6-27b-validation.md` (v1: dense 27B baseline at 8.35 tok/s)
**Runbook:** `RUNBOOK-v2-all-llamacpp-architecture.md`
**llama.cpp:** v8954 (516e8d7a8), CUDA-enabled, ARM64

---

## Phase 7: Decision Gate — Results Table

| Test | Result | Notes |
|---|---|---|
| P1: All models downloaded | ✅ | Q8_0 14B (4 shards, 14.9 GB), nomic f16 (262 MB), Qwen3.6-35B-A3B Q4_K_XL (21 GB) |
| P2.3: Graphiti JSON extraction (single) | ✅ | 11 entities, 8 relationships, valid JSON, no markdown fences |
| P2.4: Graphiti JSON stability (5/5) | ✅ | 5/5 valid JSON, deterministic at 7 entities (temp=0) |
| P2.5: Graphiti throughput + memory | ✅ | **10.08 tok/s**, **21.8 GB VRAM** (vs vLLM ~50 GB claim → ~28 GB reclaimed) |
| P3.3: Embedding dimensions (768) | ✅ | 768 dims confirmed; project CLAUDE.md mentions "1024 dims" — stale comment, actual deployment is 768 |
| P3.4: Batch embeddings | ✅ | 3/3 returned at 768 dims |
| P4.3: MoE tool calling | ✅ | `tool_use` block, correct args, `stop_reason: tool_use` via `/v1/messages` (Anthropic API compat) |
| P4.4: MoE throughput (>20 tok/s required) | ✅ | **45.43 tok/s** — 5.4× the v1 dense 27B baseline |
| P4.5: MoE Coach reasoning | ✅ | `hard-stop` with confidence 1.0, correct rationale |
| P5.2: Combined VRAM (3 models) | ✅ | **46 GB** for all three v2 models running simultaneously |
| P5.3: Concurrent requests | ✅ | All 3 endpoints returned valid responses, ~12.9 s wall time |
| P6.2: Graphiti seed end-to-end | ✅ | 1 ADR seeded via llama.cpp, 2 nodes / 1 edge, no JSON / xgrammar errors |

---

## Decision: ALL PASS → Go all-in on llama.cpp (with caveats)

Every gate passes, including the make-or-break P6.2 round-trip through Graphiti against FalkorDB on the NAS. The all-llama.cpp architecture is viable for this project.

**Caveats before flipping the production switch:**

1. **Graphiti throughput at Q8_0 is ~2× slower than vLLM FP8.** One ADR took ~37 s end-to-end (graphiti-core add_episode reported 37.17 s). At ~10 tok/s on Q8_0 this is expected. If full re-seeds matter (typically rare), accept the slower rate or re-quantise to Q5_K_M for a speed bump at modest quality cost.
2. **Embedding dimension reality check.** Project CLAUDE.md says "nomic-embed-text-v1.5, 1024 dims" — the actual model produces 768 dims (confirmed with both vLLM in prior runs and llama.cpp in P3.3). The CLAUDE.md note appears stale and should be corrected in a follow-up. FalkorDB index is 768.
3. **llama-swap not yet installed.** Phase 8 production deploy was not executed in this session — only the validation phases. Install llama-swap before deploying the production config.
4. **The v1 27B server is still running on :8080.** It uses 19.7 GB and should be killed before Phase 8 to free memory.

---

## Memory Footprint Comparison

| Configuration | Total VRAM |
|---|---|
| **v1 vLLM stack** (Graphiti FP8 + nomic + Qwen3.6-27B Q4) | ~85 GB (claimed) |
| **v2 llama.cpp stack** (Qwen2.5-14B Q8 + nomic + Qwen3.6-35B-A3B Q4) | **46 GB** |
| **Reclaimed** | **~39 GB** |
| **Headroom** for KV cache + future models | ~80 GB |

The MoE upgrade from 27B-dense to 35B-A3B-MoE *and* the Q4→Q8 quality bump on Graphiti both fit, with ~40 GB to spare vs. the v1 vLLM baseline.

---

## Throughput Comparison

| Model | Quant | tok/s | Notes |
|---|---|---|---|
| Qwen2.5-14B (Graphiti) | Q8_0 | 10.08 | Dense 14B at full quality. KV cache 32K, np=2. |
| Qwen3.6-35B-A3B (Workhorse) | Q4_K_XL | **45.43** | MoE — only ~3B active params per token. KV cache 64K, np=1. |
| _v1: Qwen3.6-27B-dense_ | _Q4_K_M_ | _8.35_ | _For comparison only — superseded by 35B-MoE._ |

The MoE result is the headline: switching from a dense 27B to a 35B-MoE actually delivers **5.4× the throughput** despite the parameter count being higher. Bandwidth-bound dense inference on GB10 was the v1 bottleneck; MoE sidesteps it.

---

## API Compatibility Notes

- **Anthropic Messages API (`/v1/messages` + `x-api-key`)** works on llama.cpp v8954 — tested with `tools` array and confirmed `tool_use` blocks plus `stop_reason: tool_use`. This means agent code that talks to Anthropic-style endpoints (Player, Coach) can target llama.cpp directly without an adapter.
- **OpenAI Chat Completions API (`/v1/chat/completions`)** with `response_format: {"type": "json_object"}` is sufficient for Graphiti's JSON-only entity extraction. No xgrammar grammar files needed in the v2 happy path.
- **OpenAI Embeddings API (`/v1/embeddings`)** with batch input works correctly (P3.4).

---

## Recommended Next Steps

1. **Install llama-swap** (Phase 0.3 was skipped):
   ```bash
   sudo curl -L -o /usr/local/bin/llama-swap \
       https://github.com/mostlygeek/llama-swap/releases/latest/download/llama-swap-linux-arm64
   sudo chmod +x /usr/local/bin/llama-swap
   ```
2. **Stop the v1 27B server on :8080** — it's no longer needed.
3. **Copy GGUFs to `/opt/llama-swap/models/`** and adopt the runbook's Phase 8 config (port :9000).
4. **Update agent endpoint configs** to point at `:9000` (already the convention).
5. **Update `.guardkit/graphiti.yaml`** to point at the production llama-swap port (likely just `llm_base_url: http://promaxgb10-41b1:9000/v1` with `llm_model: qwen-graphiti`). Embedding endpoint similar.
6. **Update CLAUDE.md** to correct the "nomic-embed-text-v1.5, 1024 dims" line — actual is 768.
7. **Optional: re-quantise Graphiti model to Q5_K_M** if the ~10 tok/s rate becomes a friction point during seeding.

---

## Files Generated by This Validation

- `/tmp/graphiti-llamacpp-test.log` — Qwen2.5-14B server log
- `/tmp/embed-llamacpp-test.log` — nomic-embed server log
- `/tmp/moe-workhorse-test.log` — Qwen3.6-35B-A3B server log
- `/tmp/p2.3-result.json` — P2.3 entity extraction output
- `/tmp/moe-speed-test.json` — P4.4 throughput sample
- `/tmp/graphiti-llamacpp-seed.log` — P6.2 end-to-end seed log

These are temp files and will not survive a reboot.

---

*Generated 2026-04-28 by working through `RUNBOOK-v2-all-llamacpp-architecture.md`.*
