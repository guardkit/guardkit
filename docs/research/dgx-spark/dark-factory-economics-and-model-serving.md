# Dark Factory Economics and Model Serving on GB10

**Status:** Preferred direction — challenge only with new evidence
**Date:** 2026-04-20
**Author:** Rich (with research assistance)
**Scope:** Model serving strategy for the GuardKit dark factory (Jarvis + Forge + architect-agent + Graphiti + embeddings + AutoBuild) running on the Dell Pro Max GB10.

---

## 1. The triggering event

On Monday 20 April 2026, Gemini API usage for Graphiti entity extraction on the GuardKit Google Cloud project showed **£29.91 / £80 monthly cap consumed in 3 days** (Fri/Sat/Sun — normal weekend tinkering). The same pattern on the GuardKit Anthropic organisation showed $28.93 spend across the same window.

Extrapolated, that is a £300–£400/month burn rate for *Graphiti entity extraction alone* — before Jarvis, Forge, architect-agent, or any of the other five planned fleet members come online. At the full fleet's likely load, cloud API spend would be £30–£50/day, or £900–£1,500/month.

**The dark factory economic thesis breaks at that price point.** The whole point of overnight autonomous builds is that the marginal cost per build approaches zero, enabling experimentation without a per-run price tag. If each Forge run costs £5–£10 in API fees, self-throttling kicks in and defeats the purpose. The GB10 investment is only justified if it genuinely carries the continuous workload.

## 2. What the weekend taught us

Three days of heavy Gemini usage was driven by ordinary Graphiti ingestion:

- Seeding FinProxy docs (~14 documents, ~310 KB) into Graphiti
- Reseeding after embedding or schema changes
- Iterating on Graphiti config with repeat `guardkit graphiti seed --force` runs

Each Graphiti episode fires at least **two** LLM calls (entity extraction + relationship extraction), plus a third when reranking is on. A single document seed can hit 500K–1M output tokens across all episodes. At `gemini-2.5-flash` pricing ($0.30/$2.50 per M tokens), that is £1–£3 per document. Fourteen documents × three reseed iterations × two or three calls per episode reaches £10/day very quickly.

**This is the canary in the coal mine.** Graphiti updates are indexing, not real work. If indexing alone hits £10/day, an orchestration-heavy multi-agent fleet running 24/7 would dwarf that.

## 3. Forum research — what the GB10 community has already solved

The DGX Spark / GB10 community has converged on a set of patterns that directly address this exact problem. Key findings from the NVIDIA Developer Forums and Spark Arena:

### 3.1 Real-world cost parallel

The "Best Local LLM for Ralph Loop" thread (March 2026) opens with: *"I recently found some success with a ralph loop... my loop is burning ~$50 in API credits from Claude a day."* Same pattern, same conclusion: local or bust for continuous autonomous work. The thread's recommendations converged on Qwen3-Coder-Next FP8 and Qwen3.5-35B-A3B served via llama.cpp or vLLM.

### 3.2 The authoritative voice on concurrent serving

**eugr** (author of the `spark-vllm-docker` repo that underpins GuardKit's current vLLM setup) wrote in "Best LLM engine for several parallel models?" (January 2026):

> "I'd say llama.cpp, as it is the most memory efficient and not overly eager to occupy as much memory as possible like other choices. vLLM will have better concurrency and throughput, but the only way to limit its memory use is through `--gpu-memory-utilization` flag which takes a percentage of total VRAM available which is not a constant on Spark. I actually run a small vision model and an embedding model on one of my Sparks all the time using llama.cpp, and use vLLM for larger models."

The constraint is specifically about the GB10's **unified memory**: vLLM's percentage-based memory allocation doesn't play well with a shared pool, whereas llama.cpp requests only what each model actually needs.

### 3.3 Proven concurrent-model setups on a single GB10

The "Code assist and RAG (instruct) in single node" thread (February 2026) documents **g.marconi's** working setup: after abandoning vLLM, he runs the following concurrently on one GB10 via Ollama:

| Model | Role |
|---|---|
| `gpt-oss:120b-64k` | Inference and planner |
| `qwen3-coder:30b-64k` | Code builder |
| `nomic-embed-text` (on Grace CPU) | Embeddings |
| `qwen2.5-coder:1.5b` | Autocomplete |

Notably, `nomic-embed` runs on the Grace ARM CPU, freeing GPU memory entirely. This is the pattern the GuardKit dark factory should adopt.

### 3.4 Memory arithmetic on GB10 (128 GB unified)

Real-world footprints from Spark Arena and forum benchmarks:

| Model | Quant | Footprint | Solo throughput |
|---|---|---|---|
| Qwen2.5-14B-Instruct | FP8 | ~14 GB | ~40 tok/s |
| nomic-embed-text-v1.5 | Q8 | ~1 GB | n/a (embedding) |
| Qwen3-Coder-Next | FP8 | ~60 GB | 36 tok/s (vLLM) |
| Qwen3-Coder-Next | NVFP4 | ~45 GB | 35–67 tok/s (Avarok image) |
| GPT-OSS 20B | MXFP4 | ~14 GB | ~70 tok/s (SGLang) |
| GPT-OSS 120B | MXFP4 | ~63 GB | 50–58 tok/s (solo) |
| Qwen3.5-35B-A3B | Q4_K_XL | ~20 GB | 48–55 tok/s (llama.cpp) |
| Qwen3.5-122B-A10B | int4 | ~63 GB | 25 tok/s solo, 40–50 concurrent |
| NVIDIA-Nemotron-3-Nano-30B | NVFP4 | ~16 GB | ~56 tok/s |

**Key constraint:** GB10 has 273 GB/s memory bandwidth. When two models are actively generating simultaneously, they share that bus. Expect 60–70% of solo throughput for each under concurrent load. Capacity is the obvious constraint; bandwidth is the silent one.

### 3.5 The Graphiti entity extraction constraint

Graphiti's own documentation says *"avoid smaller local models as they may not accurately extract data or output the correct JSON structures."* Several otherwise-attractive models fail this test on the GB10:

- **Qwen3.5-35B-A3B** — HuggingFace issue #18 confirms reasoning tokens leak into `message.content` when `response_format: json_schema` is used. Breaks JSON parsing. Same failure mode that caused the original 900-second Qwen3 timeouts with Graphiti.
- **GPT-OSS 20B/120B** — known JSON strict-mode failures in Groq community threads. Risky without a fallback path.
- **Qwen3-Coder-Next** — coder model, not intended for entity extraction structure.
- **Qwen2.5-14B-Instruct FP8** (current GuardKit setup) — pure instruct, no thinking mode, `xgrammar` enforcement works. **This remains the right answer for Graphiti.**

### 3.6 llama.cpp now speaks Anthropic Messages API natively

A critical development since the February 2026 MiniMax backup planning: llama.cpp PR #17570 (merged January 2026, build b4847+) added native `/v1/messages` support. The previous constraint — "llama.cpp only does OpenAI format, so it won't work with AutoBuild's Anthropic protocol" — **is no longer true**.

Features now supported:
- Full `/v1/messages` and `/v1/messages/count_tokens` endpoints
- Streaming with proper Anthropic SSE event types
- Tool use via `tool_use` and `tool_result` content blocks
- Vision support (base64 and URL)
- Extended thinking parameter

This unlocks llama.cpp as a direct drop-in for the Claude Agent SDK used by AutoBuild.

**Known bug to track:** Issue #20090 (March 2026) — thinking content blocks are silently dropped during Anthropic→OpenAI conversion. Does not affect non-thinking models like Qwen3-Coder-Next or Qwen2.5-14B-Instruct. Affects Qwen3.5-family and GPT-OSS-family if thinking is enabled. Workaround: disable thinking via `--reasoning off` or `--chat-template-kwargs '{"enable_thinking":false}'`.

## 4. The llama-swap discovery

`mostlygeek/llama-swap` is a Go binary that sits in front of any OpenAI-or-Anthropic-compatible inference server (llama.cpp, vLLM, TabbyAPI, SGLang). One YAML config lists all models; llama-swap becomes the single `/v1` endpoint the rest of the system talks to.

### 4.1 Why this fits the GuardKit dark factory shape

The Forge is sequential by design — one project is built out, other work queues behind it. llama-swap was built for exactly this pattern:

- **Request queuing during swap.** When a request arrives and the wrong model is running, llama-swap uses a `sync.WaitGroup` (`waitStarting`) to block concurrent requests while the model transitions from stopped to ready. Even if 100 requests arrive during a swap, only one shell command executes; the rest queue until the model is ready.
- **`concurrencyLimit` for backpressure.** Per-model cap on parallel requests; exceeding returns HTTP 429 rather than queueing forever. Setting `concurrencyLimit: 1` gives hard serialisation for Forge runs that need it.
- **Groups for "always-on vs swapped" split.** The `forever` group pattern (`persistent: true`, `swap: false`) prevents other groups from evicting its members. This is the killer feature for Graphiti + embeddings.

### 4.2 What llama-swap does well

- Serves all four protocols the GuardKit stack needs: OpenAI chat completions, OpenAI embeddings, Anthropic Messages API (with `count_tokens`), and rerank endpoints
- Mixes inference engines freely — the existing vLLM Graphiti container stays as-is (wrapped), new models come in via llama.cpp; no migration of working components required
- Supports hooks (`on_startup`) for model preloading so the first Forge request doesn't pay the cold-start tax
- Web UI at `/ui` shows real-time loaded models, request logs, token metrics — useful for debugging Forge hangs
- HTTP API endpoints for orchestration: `/models/unload`, `/running`, `/log`. Jarvis can query and control fleet state via HTTP, which fits the NATS-based agent orchestration model
- API key enforcement for differentiated agent permissions
- Peer federation — if a second machine is added later (second GB10, Mac Studio), llama-swap instances can federate, syncing model lists automatically

### 4.3 What llama-swap does not do

- **No intelligent swap scheduling.** Requests are served in arrival order; llama-swap will not reorder a queue to minimise model swaps. Forge job ordering is the Forge's responsibility.
- **Swap cost is real.** Loading GPT-OSS 120B cold is ~2–4 minutes (63 GB off NVMe + compile graph warmup). Chronic swapping kills throughput. Design the Forge loop to batch Player turns before switching to Coach.
- **vLLM inside llama-swap is container-only.** vLLM leaves GPU memory held until the parent Python process fully exits; bare-metal process management is awkward. The recommended pattern is Docker + `cmdStop: docker stop <name>`. Existing vLLM Graphiti setup works as-is by pointing llama-swap at its port via `proxy:`.
- **No built-in job queue persistence.** If llama-swap crashes or GB10 reboots, in-flight queued requests are lost. The Forge (via `buildplan.md` / `command-history.md` + NATS JetStream) must remain the durable job queue. llama-swap is an inference lifecycle manager, not a job scheduler.
- **Single-node only by default.** Peers exist, but it's not a cluster orchestrator.
- **Concurrent-models story is simpler than the swap story.** Groups with `swap: false` work but they're just refusing to unload each other. Memory budget is still managed manually via per-model flags.

### 4.4 Sweet spot for the GuardKit fleet

The five planned concurrent roles are:
1. **Graphiti LLM** (Qwen2.5-14B FP8) — always-on, entity extraction
2. **Embeddings** (nomic-embed-text-v1.5) — always-on, 768-dim vectors for FalkorDB
3. **Jarvis intent router + Architect reasoning** (GPT-OSS 120B MXFP4) — swap-in for orchestration and `/system-arch` sessions
4. **AutoBuild Player** (Qwen3-Coder-Next FP8) — swap-in for code generation during Forge runs
5. **Fine-tuned specialist models** (Gemma 4 31B variants) — future swap targets for specialist-agent roles

Memory footprint in the steady state:
- Always-on forever group: ~15 GB (Graphiti 14B + embedder 1 GB)
- Available for swappable builders group: ~110 GB
- Swapping between Coder-Next (~60 GB) and GPT-OSS 120B (~63 GB) fits comfortably with KV cache headroom

## 5. Decision

**Adopt llama-swap as the unified inference front door on GB10.**

Architectural shape:

```
GB10 (single node)
├── llama-swap :9000        — unified /v1 front door (OpenAI + Anthropic)
│    ├── group "forever" (never evicted)
│    │    ├── nomic-embed     — delegated to existing vLLM on :8001
│    │    └── qwen-graphiti   — delegated to existing vLLM on :8000
│    └── group "builders" (swap, exclusive)
│         ├── qwen-coder-next  — llama.cpp, loaded on Forge Player turns
│         └── gpt-oss-120b     — llama.cpp, loaded for Jarvis / Coach / architect
│
├── vLLM :8000              — Qwen2.5-14B-Instruct-FP8 (Graphiti)
├── vLLM :8001              — nomic-embed-text-v1.5 (embeddings)
└── llama.cpp servers        — managed by llama-swap on-demand
```

All agents, tools, and pipelines point at `http://promaxgb10-41b1:9000` as their single LLM endpoint. llama-swap routes internally based on the `model` field of each request.

## 6. Migration plan

### Phase 1 — Standup without disruption

1. Install llama-swap on GB10, bind to port 9000
2. Configure it to proxy the **existing** vLLM Graphiti (:8000) and embedder (:8001) via `proxy:` overrides with `ttl: 0` (never unload — lifecycle delegated to existing scripts)
3. Verify all current Graphiti ingestion continues to work via the new front door
4. **No changes to `vllm-serve.sh`, `vllm-graphiti.sh`, or the LLM provider switching doc** — they continue to manage the underlying services

### Phase 2 — Add llama.cpp swap members

1. Build llama.cpp on GB10 with SM121 optimisations (see companion setup doc)
2. Add `qwen-coder-next` and `gpt-oss-120b` as llama-swap members
3. Smoke-test `/v1/messages` endpoint with tool calls
4. A/B test AutoBuild on one real task: existing vLLM on :8002 vs. llama.cpp via llama-swap on :9000. Compare Player-Coach turn counts, tool call success, and time-to-complete

### Phase 3 — Migrate AutoBuild and Jarvis endpoints

1. Point AutoBuild at `ANTHROPIC_BASE_URL=http://promaxgb10-41b1:9000`
2. Point Jarvis intent routing at the same front door with OpenAI-style requests
3. Retain vLLM-based Coder-Next on :8002 as a fallback path for one sprint before decommissioning
4. Monitor the llama-swap web UI (`/ui`) to track swap frequency and identify Forge loop ordering that causes excess swap churn

## 7. Cost impact projection

### Before (continuing with Gemini for Graphiti)
- Graphiti alone: £300–£400/month (validated by weekend data)
- Plus Jarvis (6 agents × similar usage): potentially £900–£1,500/month
- **Total at full fleet: £1,200–£1,900/month**

### After (local-first on GB10)
- Graphiti: £0 (local Qwen2.5-14B)
- Jarvis, Forge, architect-agent: £0 (GPT-OSS 120B swap)
- AutoBuild: £0 (Qwen3-Coder-Next swap)
- Gemini 3.1 Pro fallback for 5–10 interactive `/system-arch` sessions/month where frontier reasoning justifies the spend: ~£20–£50/month
- **Total at full fleet: £20–£50/month**

The GB10 investment amortises within the first month of full-fleet operation against the avoided cloud spend alone.

## 8. Key learnings (to preserve)

1. **"No cloud API on the dark factory critical path"** is now an architectural principle. Cloud APIs belong on the *interactive* path (Claude Desktop planning, rare frontier-reasoning architect sessions where a human is driving) — not in any unattended loop.
2. **Graphiti updates are the canary.** Indexing bills reveal orchestration bills in miniature. If indexing hits £10/day, agent orchestration will hit £50+/day.
3. **Unified memory changes the serving calculus.** vLLM's percentage-based allocation is wrong for GB10. llama.cpp's request-what-you-need model is right. This is why the community migrated away from vLLM for multi-model setups.
4. **The Anthropic Messages API is no longer a moat.** llama.cpp, Ollama, LM Studio, and vLLM ≥0.17 all speak it natively. Claude Agent SDK portability to local models is effectively solved.
5. **Swap is fine if sequential work is fine.** The Forge is sequential by design. Chasing concurrent multi-model serving would be a solution looking for a problem.
6. **Memory bandwidth, not capacity, is the silent constraint.** 273 GB/s shared across all active models. Two big models generating simultaneously means both drop to 60–70% of solo throughput. Plan the fleet accordingly.
7. **Nagging doubts prove correct.** The £29 cost spike felt like a disproportionate reaction to 3 days of tinkering — but extrapolation showed it was catastrophic at scale. Always chase the cost signal.

## 9. Related documents

- `.guardkit/llm-provider-switching.md` — repo-level Graphiti provider toggle (GB10 vLLM / MacBook Ollama / Gemini fallback)
- `scripts/vllm-serve.sh` — existing vLLM preset manager; continues to manage underlying services
- `scripts/vllm-graphiti.sh` — existing Graphiti vLLM launcher with xgrammar JSON enforcement; unchanged
- `docs/research/dgx-spark/llama-swap-setup.md` — companion setup guide (installation, config.yaml for the fleet, smoke tests, troubleshooting)
- `docs/research/dgx-spark/DGX Spark, Nemotron3, and NVFP4: Getting to 65+ tps | by Thomas P. Braun | Avarok.pdf` — NVFP4 background
- NVIDIA Developer Forums — "Best LLM engine for several parallel models?", "Code assist and RAG in single node", "Best Local LLM for Ralph Loop", "Implementation Guide: DGX Spark with Qwen3.5-35B-A3B via llama.cpp for Claude Code"
- Spark Arena leaderboard — <https://spark-arena.com/leaderboard>
- llama-swap — <https://github.com/mostlygeek/llama-swap>
- llama.cpp Anthropic API PR — <https://github.com/ggml-org/llama.cpp/pull/17570>
