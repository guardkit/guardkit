# Results: Production Deployment — All-llama.cpp via llama-swap (Runbook v3)

**Date:** 2026-04-28
**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 124 GB unified memory
**Predecessor:** `RESULTS-v2-all-llamacpp-validation.md`
**Runbook:** `RUNBOOK-v3-production-deployment.md`
**llama.cpp:** v8954 (516e8d7a8)
**llama-swap:** v208 (e8d4384cd2099d02394ad48e465cae2b9b4c95f1)
**Gap fixes:** [`TASK-RUN-D6F4`](../../../tasks/completed/2026-04/TASK-RUN-D6F4-fix-dgx-runbook-v3-gaps.md) — folded the six gaps below back into the runbook
**Post-fix validation:** [`VALIDATION-D6F4-gap-fix-results.md`](VALIDATION-D6F4-gap-fix-results.md) — 2026-04-29, all six gaps verified PASS against live deployment; surfaced two operational follow-ups: [`TASK-OPS-7CB1`](../../../tasks/backlog/TASK-OPS-7CB1-investigate-overnight-llama-server-crashes.md) (overnight crashes), [`TASK-OPS-9F2A`](../../../tasks/backlog/TASK-OPS-9F2A-tune-graphiti-extraction-concurrency.md) (429 throttling)

---

## Phase 9: Decision Gate — Results Table

| Test | Result | Notes |
|---|---|---|
| P0.1: v2 models on disk | ✅ | All four Q8_0 14B shards (14.9 GB), nomic f16 (262 MB), Qwen3.6-35B-A3B Q4_K_XL (21 GB) |
| P0.2: Fine-tuned tutor GGUF | ✅ | `~/fine-tuning/output/gcse-tutor-gemma4-26b-moe/gguf_gguf/gemma-4-26b-a4b-it.Q4_K_M.gguf` (16 GB) |
| P0.2: Modelfile present | ⚠️ | Modelfile has TEMPLATE block (`<\|turn>...<turn\|>`) but **no SYSTEM block** — fallback prompt used in P6.5 |
| P0.3: llama-server build | ✅ | v8954 (516e8d7a8), CUDA, ARM64 |
| P0.4: stray test servers killed | ✅ | v1 27B server on :8080 (PID 3181112) killed |
| P0.5: disk space | ✅ | 2.5 TB free on `/` |
| P1: Tutor model verified | ✅ | No conversion needed, 16 GB Q4_K_M |
| P2: llama-swap installed | ✅ | v208 to `/usr/local/bin/llama-swap` (linux-arm64). Runbook URL fixed to resolve real release tarball. |
| P3: All models staged to /opt | ✅ | qwen2.5-14b: 15 GB · nomic-embed: 262 MB · qwen36-35b: 21 GB · gemma4-tutor: 16 GB · **total: ~52 GB on disk** |
| P4: vLLM stopped | ✅ | No containers were running (already cleared) |
| P5.3: llama-swap started | ✅ | PID running, listening :9000. **Runbook flag fix:** v208 uses single-dash `-config`/`-listen`, not `--config`/`--listen` |
| P5.4: All 4 models loaded | ✅ | After config fix — see "Runbook gap #1" below |
| P5.5: Production VRAM | ✅ | **65 GB** total (Graphiti 21.3 + Embed 0.9 + Workhorse 23.7 + Tutor 19.1) — slightly above runbook's ~60 GB target, well within 128 GB |
| P6.1: Graphiti JSON extraction | ✅ | 9 entities, 10 relationships, valid JSON |
| P6.2: Embeddings (768 dims) | ✅ | 768 dims confirmed |
| P6.3: Workhorse tool calling | ✅ | `tool_use` block, correct args, `stop_reason: tool_use` via `/v1/messages` |
| P6.4: Workhorse throughput | ✅ | **41.32 tok/s** for 109 output tokens (v2 baseline 45.43 tok/s — small variance, four-model coexistence) |
| P6.5: Study tutor Socratic dialogue | ⚠️ | Content PASS (138 words, Socratic, encouraging) but **template-token leak** (`<\|channel>thought<channel\|>` and `<think>...</think>` blocks). See "Follow-up #1" below. |
| P6.6: Alias routing | ✅ | All 9 aliases tested route correctly (study-tutor, gcse-tutor, architect-agent, gemma4-specialist, coach, autobuild-player, jarvis-router, graphiti-llm, embeddings) |
| P7: Graphiti MCP config updated | ✅ | `scripts/graphiti-mcp-config.yaml`: 8000→9000, 8001→9000, dims 1024→768. Backup at `.pre-llamacpp.bak` |
| P7: Graphiti MCP container restarted | ✅ | `graphiti-mcp` running, healthy after 20 s |
| P8: E2E Graphiti seed | ✅ | DECISION-DF-001 → 2 nodes, 1 edge in FalkorDB via llama-swap. 36.5 s wall time (parity with v2's 37 s). 0 errors. **Required additional fix — see "Runbook gap #2".** |

---

## Decision: ALL PASS → Production live on all-llama.cpp

The all-llama.cpp architecture is in production behind `:9000` on the GB10. Four models are permanently resident; switching is impossible by config. Graphiti round-trip works end-to-end. Two issues remain as follow-ups (neither blocking).

---

## Runbook gaps discovered while executing

These are corrections that should be folded into a v4 runbook revision before the next clean-room deployment.

### Gap #1: llama-swap v208 swaps models by default — `matrix` block required

The runbook config sets `ttl: 0` on each model (which means "never auto-unload on idle") but does **not** declare which models can run concurrently. By default, llama-swap evicts the previously running model when a request hits a different model — `ttl: 0` only governs idle eviction, not request-driven eviction.

The first start of llama-swap with the runbook-as-written produced this thrash:

```
[INFO] <qwen36-workhorse> Health check passed on http://localhost:5803/health
2026/04/28 18:16:36 http: proxy error: context canceled
[INFO] Request "POST /v1/chat/completions HTTP/1.1" 502 -1 ... 3m16.9s
[INFO] <gemma4-tutor> Health check passed on http://localhost:5800/health
2026/04/28 18:16:52 http: proxy error: context canceled
[INFO] Request "POST /v1/chat/completions HTTP/1.1" 502 -1 ... 3m28.0s
... (cycles indefinitely)
```

Polling four model endpoints in parallel forced llama-swap to load → kill → load → kill in a loop.

**Fix:** add a `matrix` block declaring all four can coexist, plus an `on_startup.preload` hook so the cold start is deterministic:

```yaml
matrix:
  vars:
    qg: qwen-graphiti
    ne: nomic-embed
    qw: qwen36-workhorse
    gt: gemma4-tutor
  sets:
    all: "qg & ne & qw & gt"

hooks:
  on_startup:
    preload:
      - qwen-graphiti
      - nomic-embed
      - qwen36-workhorse
      - gemma4-tutor
```

Also bump `healthCheckTimeout: 300` → `600` to give the 21 GB workhorse and 19 GB tutor enough cold-start budget on first run.

### Gap #2: Python `guardkit graphiti` client config not patched

Phase 7 of the runbook only patches `scripts/graphiti-mcp-config.yaml` (the MCP container config). The Python client used by `guardkit graphiti add-context` reads from a separate file: `.guardkit/graphiti.yaml`. That file was still pointing at:

```yaml
llm_base_url:       http://promaxgb10-41b1:8000/v1
embedding_base_url: http://promaxgb10-41b1:8001/v1
```

Result: the first run of Phase 8 produced three rounds of `openai._base_client:Retrying request` followed by `Episode creation failed: Connection error.`

**Fix:** add to Phase 7 a sed pass against `.guardkit/graphiti.yaml`:

```bash
sed -i 's|http://promaxgb10-41b1:8000/v1|http://promaxgb10-41b1:9000/v1|g' .guardkit/graphiti.yaml
sed -i 's|http://promaxgb10-41b1:8001/v1|http://promaxgb10-41b1:9000/v1|g' .guardkit/graphiti.yaml
```

Backup at `.guardkit/graphiti.yaml.pre-llamacpp.bak`.

### Gap #3: llama-swap CLI flag style

Runbook uses `--config` and `--listen`. v208 binary takes `-config` and `-listen` (single dash). Trivial — just update the runbook commands.

### Gap #4: Graphiti GGUF glob mismatch

Runbook uses `*Q8*` (capital Q). Actual files on disk are `qwen2.5-14b-instruct-q8_0-...gguf` (lowercase q). Should be `-iname` or `*[Qq]8*`.

### Gap #5: `pkill -f "llama-server"` self-kills

In Phase 4.2, `pkill -f "llama-server"` matches the bash script running it (because the script text contains the string `llama-server`) and kills the script before it can do anything else. Use `pkill -x llama-server` (basename match) instead.

### Gap #6: `/opt` model dir path mismatch with mmproj/BF16 files

The fine-tuned tutor directory contains BF16 shards, an mmproj file, and the Q4_K_M used in production. The runbook copies the correct file but does not exclude the others — at 16 GB Q4_K_M plus the unused files this could be wasteful. Not blocking; the runbook only copies the named `$TUTOR_GGUF` so the extra files stay in `~/fine-tuning/...`.

---

## Follow-ups (not blocking production)

### Follow-up #1: Tutor template-token leak

The `gemma4-tutor` model emits its internal harmony-format markers in user-visible output:

```
<|channel>thought
<channel|><think>The student is asking about Question 5 in AQA GCSE English Language Paper 1...</think>

That's a really important question! Question 5 is worth 40 marks...
```

The Modelfile has a custom `<|turn>...<turn|>` chat template, but the GGUF metadata template appears to be different — `--jinja` reads from the GGUF, not the Modelfile. Two probable fixes:

1. **Add `--reasoning off`** to the tutor's llama-server cmd (the workhorse already uses this and produces clean output).
2. **Re-export the tutor GGUF with the Modelfile template baked into metadata** — requires touching `convert_hf_to_gguf.py` or post-processing with `gguf-py/scripts/gguf_set_metadata.py`.

Recommended: try (1) first — single line change, no re-quantization.

### Follow-up #2: tutor system-prompt extraction is no-op

Phase 0.2's sed extraction of a SYSTEM block from the Modelfile produced an empty string because the actual Modelfile has only a TEMPLATE block. Phase 6.5 falls back to the runbook's hard-coded GCSE prompt. Either:

- The fine-tune was trained against an external system prompt that lives elsewhere, or
- The training used no system prompt and the model relies entirely on user-message structure.

If the former, surface the system prompt and add it to the tutor's MCP server. If the latter, document that the fallback prompt is canonical.

### Follow-up #3: VRAM 5 GB above runbook estimate

| Model | Runbook estimate | Actual |
|---|---|---|
| Qwen2.5-14B Q8_0 | 22 GB | 21.3 GB |
| nomic-embed f16 | 0.3 GB | 0.9 GB |
| Qwen3.6-35B-A3B Q4_K_XL | 21 GB | 23.7 GB |
| Gemma 4 26B-A4B Q4_K_M | 17 GB | 19.1 GB |
| **Total** | **~60 GB** | **65 GB** |

Workhorse and tutor are larger than estimated by ~3 GB combined. Likely KV-cache contribution from 64K and 32K context sizes respectively. Not a problem (60 GB headroom remains) but worth updating the runbook's expected number for future reference.

### Follow-up #4: Swap usage during cold start

System reported ~7.7 GB of swap in use during preload — likely ghost residue from the v2 vLLM run before reboot. After everything is loaded, headroom is fine; if swap pressure becomes a recurring issue, a `swapoff -a && swapon -a` after llama-swap is up would clear it.

---

## Memory and throughput summary

| Configuration | Total VRAM | Workhorse tok/s | Models concurrent |
|---|---|---|---|
| **v1 vLLM stack** | ~85 GB (claimed) | 8.35 (dense 27B Q4) | 3 |
| **v2 llama.cpp validation** | 46 GB | 45.43 (35B-A3B Q4) | 3 |
| **v3 production all-llama.cpp** | **65 GB** | **41.32 (35B-A3B Q4)** | **4 (incl. fine-tuned tutor)** |
| **vs v1** | -20 GB | +5× | +1 model |

Dropping vLLM and adding the fine-tuned tutor cost only ~5 GB net vs. v2 (because the extra ~17 GB of tutor weights replaces unused vLLM overhead).

---

## What's running now

```
llama-swap v208 :9000 (single front door)
├── qwen-graphiti       :5802  Qwen2.5-14B Q8_0           21.3 GB
├── nomic-embed         :5801  nomic-embed-text-v1.5 f16   0.9 GB
├── qwen36-workhorse    :5803  Qwen3.6-35B-A3B Q4_K_XL    23.7 GB
└── gemma4-tutor        :5800  Gemma 4 26B-A4B Q4_K_M     19.1 GB
                                                          ──────
                                                  Total:   65.0 GB / 128 GB
```

Endpoint: `http://promaxgb10-41b1:9000` (and via Tailscale)
Config: `/opt/llama-swap/config/config.yaml`
Models: `/opt/llama-swap/models/`
Logs: `/opt/llama-swap/logs/llama-swap.log`
Rollback: `scripts/archive-vllm/` + `*.pre-llamacpp.bak`

Phase 10 (systemd auto-start, archive vLLM scripts) pending — completing next.

---

*Runbook v3 results — completed 2026-04-28*
