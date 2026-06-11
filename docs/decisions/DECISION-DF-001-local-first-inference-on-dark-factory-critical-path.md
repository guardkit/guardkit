# DECISION-DF-001 — Local-first inference on the dark factory critical path

**Status:** Accepted
**Date:** 2026-04-20
**Author:** Rich (pair-programmed with Claude Opus 4.7 in Claude Desktop)
**Scope:** All unattended, autonomous, or continuous workloads in the GuardKit dark factory running on the GB10. Specifically: Jarvis, the Forge, architect-agent, AutoBuild Player-Coach loops, Graphiti entity extraction, embeddings.
**Companions:** DECISION-DF-002 (ledger-based tool selection, `ai-transition/docs/`) · DECISION-DF-003 (hybrid pipeline boundary) — both apply this decision's boundary to the commercial ledger and the pipeline stages respectively; neither amends it.

---

## Summary

**Cloud LLM APIs are excluded from the dark factory critical path. All continuous, autonomous, or scheduled workloads run on local inference served from the GB10. Cloud APIs are retained only for the interactive path where a human is driving and frontier-reasoning quality justifies the per-session cost.**

The single unified inference front door is `llama-swap` on port 9000, orchestrating a mix of always-on services (Graphiti LLM, embeddings) and swappable builders (AutoBuild Coder, Jarvis/Architect/Coach reasoner). The underlying inference engines are a mix of the existing vLLM containers (for Graphiti and embeddings, unchanged) and llama.cpp (for the swap members, leveraging its native Anthropic Messages API support).

This supersedes the implicit assumption — never formally stated but operationally in effect during March–April 2026 — that cloud Gemini 2.5 Flash / 3.1 Pro could serve as a general-purpose LLM for agent workloads. Weekend usage data proved this assumption catastrophically wrong at scale.

## 1. Context

### 1.1 The triggering event

On Friday 17 to Sunday 19 April 2026, over a weekend of normal Graphiti ingestion work (seeding FinProxy docs, iterating on config, reseeding after embedding changes), the GuardKit Google Cloud project accumulated **£29.91 of Gemini 2.5 Pro API spend in 3 days**. The parallel GuardKit Anthropic organisation showed a similar pattern with $28.93 over the same window.

The ingestion was not unusual in volume. It was typical of weekend tinkering against the knowledge graph while iterating on Graphiti configuration. The spend was driven by Graphiti's natural call pattern: each episode triggers entity extraction and relationship extraction (minimum two LLM calls per episode), plus reranking when enabled. At `gemini-2.5-flash` pricing, a single document seed traverses 500K–1M output tokens across all episodes, which is £1–£3 per document. Fourteen FinProxy docs × three reseed iterations × two or three LLM calls per episode reaches £10/day without any real agent work happening.

### 1.2 The extrapolation that changed the decision

Monday morning extrapolation made the scale clear:

| Scope | Monthly cloud spend at observed rate |
|---|---|
| Graphiti entity extraction only (current state) | £300–£400/month |
| Plus Jarvis intent routing (6 agents planned) | £900–£1,500/month |
| Plus Forge + architect-agent + AutoBuild at typical Forge cadence | £1,200–£1,900/month |

The GB10 (£3,500–£4,000 one-time) amortises against the avoided cloud spend in under a month at full fleet. More importantly: at £900–£1,900/month of cloud API burn, the dark factory *self-throttles* — Rich would consciously or unconsciously run fewer builds to keep the bill down, which defeats the entire thesis.

**The thesis of the dark factory is that marginal cost per build approaches zero, enabling unconstrained experimentation. Cloud APIs on the critical path break that thesis.**

### 1.3 Community confirmation

The DGX Spark / GB10 forum community has independently arrived at the same conclusion through similar cost experiences. Representative: the "Best Local LLM for Ralph Loop" thread (March 2026) opens with *"my loop is burning ~$50 in API credits from Claude a day"* — same pattern, same migration to local-first.

The forum has also converged on the engineering solutions:
- **eugr** (author of `spark-vllm-docker`, which the GuardKit stack already depends on) explicitly recommends llama.cpp for concurrent multi-model serving on GB10's unified memory: *"the only way to limit [vLLM's] memory use is through `--gpu-memory-utilization` flag which takes a percentage of total VRAM available which is not a constant on Spark."*
- **g.marconi** documents a working single-GB10 setup running GPT-OSS 120B + Qwen3-Coder-30B + nomic-embed + qwen2.5-coder:1.5b concurrently, with the embedder offloaded to the Grace ARM CPU to free GPU memory.
- **llama.cpp PR #17570** (merged January 2026) added native `/v1/messages` support, removing the previous architectural blocker that forced AutoBuild onto vLLM for Anthropic protocol compatibility.

### 1.4 Why this decision was not made earlier

Two factors kept the implicit "cloud is fine for agent workloads" position alive through March and April 2026:

- **Free tier comfort.** Gemini 2.5 Flash's free tier absorbed early experiments without visible cost. The jump to paid tier (forced by 429 rate limits during FinProxy seeding on 2026-04-17) happened without an accompanying cost-projection exercise.
- **GB10 was initially earmarked for fine-tuning.** The Gemma 4 31B fine-tuning job in early April consumed the GPU, which created the legitimate short-term case for moving Graphiti to Gemini. That short-term case quietly became a default before the GB10 was free again.

Both of these are examples of **architecturally significant decisions being made implicitly through operational convenience**. The absence of this ADR until now is itself the lesson.

## 2. Decision

### 2.1 The principle

**No cloud LLM API calls on any unattended, autonomous, scheduled, or continuous workload.** Specifically excluded from cloud:

- Graphiti entity extraction and relationship extraction
- Graphiti reranking
- Embeddings (always local, always has been)
- Jarvis intent routing and multi-agent orchestration
- Forge loop execution (`/feature-build`, `/feature-plan`, scheduled overnight runs)
- Architect-agent automated sessions (`/system-arch` reviews, drift detection scans)
- AutoBuild Player and Coach cycles
- Specialist-agent execution (ideation, UX designer, fine-tuned specialists)
- Any dark factory loop that runs without a human present at the keyboard

Cloud LLM APIs are **retained** for:

- Interactive `/system-arch` sessions where a human drives the reasoning and frontier-model quality genuinely matters (estimated 5–10 sessions/month, ~£20–£50/month total)
- Claude Desktop research and planning sessions (pair-programming with Claude Opus, this current conversation is an example)
- Gemini 3.1 Pro as an *explicit, human-invoked* escalation path when a local model fails a task and the operator chooses to pay the cost for a one-shot better answer
- Short-term fallback when the GB10 is fully committed to fine-tuning jobs, with per-repo toggle via `.guardkit/graphiti.yaml` as documented in `.guardkit/llm-provider-switching.md`

### 2.2 The implementation

The decision is implemented by introducing **`llama-swap` as a unified inference front door on GB10 port 9000**, serving both OpenAI and Anthropic protocols.

Architectural shape:

```
GB10 (single node)
├── llama-swap :9000        — unified /v1 front door
│    ├── group "forever" (persistent, never evicted)
│    │    ├── qwen-graphiti   — proxied to existing vLLM on :8000
│    │    └── nomic-embed     — proxied to existing vLLM on :8001
│    └── group "builders" (swap, exclusive)
│         ├── qwen-coder-next  — llama.cpp, for Forge Player turns
│         └── gpt-oss-120b     — llama.cpp, for Jarvis / Coach / architect
│
├── vLLM :8000              — Qwen2.5-14B-Instruct-FP8 (Graphiti, unchanged)
├── vLLM :8001              — nomic-embed-text-v1.5 (embeddings, unchanged)
└── llama.cpp servers        — lifecycle managed by llama-swap on demand
```

All agents, tools, and pipelines point at `http://promaxgb10-41b1:9000` as their single LLM endpoint. llama-swap routes internally based on the `model` field of each request.

### 2.3 What stays unchanged

The existing infrastructure continues to work untouched. This decision is additive, not disruptive:

- `scripts/vllm-serve.sh` — continues to manage AutoBuild vLLM on :8002 as a fallback
- `scripts/vllm-graphiti.sh` — continues to manage Graphiti vLLM on :8000
- `scripts/vllm-embed.sh` — continues to manage the embedder on :8001
- `.guardkit/llm-provider-switching.md` — continues to document the Gemini / MacBook Ollama fallback paths for operator-initiated emergencies
- `.guardkit/graphiti.yaml` across all 13 affected repos — already reverted to `llm_provider: vllm` on 2026-04-20 as the immediate cost-stop action; this ADR ratifies that revert

If llama-swap misbehaves or is unavailable, agents can point directly at the individual vLLM/llama.cpp endpoints. Rollback is operational, not architectural.

## 3. Consequences

### 3.1 Cost impact

- Graphiti entity extraction: £300–£400/month → £0
- Full-fleet agent workload at projected scale: £1,200–£1,900/month → ~£20–£50/month (interactive path only)
- GB10 amortises within the first month of full-fleet operation

### 3.2 Performance impact

- Graphiti entity extraction: Qwen2.5-14B FP8 on GB10 is ~9s per call vs Gemini 2.5 Flash's ~2–3s. Slower, but acceptable for non-interactive ingestion.
- AutoBuild throughput: Qwen3-Coder-Next FP8 on llama.cpp is comparable to the existing vLLM setup; no expected regression beyond the warm-up cost of swapping.
- Jarvis intent routing: GPT-OSS 120B MXFP4 at ~50–58 tok/s is faster for routing decisions than round-tripping to Gemini for the same task.
- First-of-day latency: cold-loading a swapped model adds ~2–4 min. Mitigated via llama-swap's `preload` hook on startup.

### 3.3 Operational impact

- New operational surface: llama-swap process lifecycle, config file management, memory pressure monitoring on the unified memory pool.
- Swap-churn risk: if the Forge loop alternates Player (Coder-Next) and Coach (GPT-OSS 120B) on every turn, model swap cost dominates. Mitigation: design the Forge loop to batch several Player turns before switching to Coach, and track swap frequency via llama-swap's web UI at `/ui`.
- Single point of failure: llama-swap on :9000 becomes the routing bottleneck. Mitigation: direct-port fallback is always available (agents can revert to :8000/:8001/:8002 via env vars).

### 3.4 Strategic impact

- **The dark factory thesis is preserved.** Marginal cost per build is genuinely near zero, enabling the experimentation volume the architecture was designed for.
- **GB10 investment is retrospectively justified.** The hardware pays for itself in the first month of full-fleet operation vs the equivalent cloud spend.
- **DDD Southwest talk narrative strengthens.** The "Year of the Software Factory" argument gains a concrete economic dimension: traditional PM tooling is a category error *and* cloud-API-first agent architectures are an economic error when you're running continuous autonomous loops.
- **Future cloud API price changes become a non-issue.** The dark factory is insulated from Anthropic/Google pricing shifts, rate limit policy changes, or API deprecations.

## 4. Alternatives considered and rejected

### 4.1 Cloud-first with careful budgeting
*Keep Gemini 2.5 Flash for Graphiti, add per-repo budget caps, accept the cost.*

Rejected. Per-repo budget caps create operator friction (interrupts mid-build) and fail to solve the fundamental problem: at full fleet, cost scales linearly with agent activity, and agent activity is the product. The dark factory becomes self-throttling.

### 4.2 Local embeddings only, cloud LLMs everywhere else
*Continue with embeddings local, move Graphiti LLM + Jarvis + Forge to Gemini 3.1 Pro for better reasoning quality.*

Rejected. Gemini 3.1 Pro is ~10× more expensive than 2.5 Flash; the cost problem becomes worse, not better. Reasoning quality is real but matters mainly on interactive architect sessions, not on indexing and build loops where volume dominates.

### 4.3 Hybrid with automatic cost-aware routing
*Build a router that picks local or cloud per request based on task complexity and current budget.*

Rejected. Massively premature optimisation. Adds a new agent (a cost-aware router) to solve a problem that is better solved at the policy level. If the policy is "local only," no router is needed.

### 4.4 Continue with vLLM for all models, no llama-swap
*Use the existing `vllm-serve.sh` swap pattern for all models, no new orchestration layer.*

Rejected on two grounds. First, vLLM's `--gpu-memory-utilization` percentage-based allocation is architecturally wrong for GB10's unified memory (eugr's documented finding). Second, `vllm-serve.sh` handles one model at a time by design; the dark factory needs Graphiti, embeddings, AND a builder running simultaneously. The current script cannot express that, so a new orchestration layer is required regardless.

### 4.5 Build a custom orchestration layer
*Write GuardKit's own model lifecycle manager instead of adopting llama-swap.*

Rejected. llama-swap already implements exactly the semantics needed (groups, TTL, swap policy, Anthropic+OpenAI front door, request queuing during swap). Building an equivalent would consume weeks of engineering for no differentiation.

## 5. Principle made explicit

From this decision, a principle for the GuardKit architecture as a whole:

> **Cost structure is an architectural property. A per-request API cost, however small in isolation, becomes a critical-path constraint in autonomous loops that run continuously. Architectures that assume "cheap enough" without doing the extrapolation are making an implicit decision that future-us will have to reverse. Do the extrapolation explicitly, at architecture time, for any component that runs without a human present.**

This applies beyond LLM APIs. Any paid external dependency — embedding APIs, managed knowledge graphs, hosted vector databases, cloud observability platforms — should be evaluated under the same lens before being placed on a dark factory critical path.

## 6. Immediate actions

### 6.1 Today

- ✅ **Revert all 13 repos' `.guardkit/graphiti.yaml` to `llm_provider: vllm`** (completed 2026-04-20 as the cost-stop action before this ADR was written).
- **Capture this decision in Graphiti** via `guardkit-py graphiti add-context` so all future agents retrieve it during context loading.

### 6.2 This week

- **Stand up llama-swap on GB10:9000** following `docs/research/dgx-spark/llama-swap-setup.md`. Start with Phase 1 (proxying existing vLLM services only) to validate the front door without disrupting anything. No agent migrations yet.
- **Pre-download the GGUF models** (Qwen3-Coder-Next FP8, GPT-OSS 120B MXFP4 Blackwell-tuned) to `/opt/llama-swap/models`.
- **A/B test AutoBuild** on one real task: existing vLLM on :8002 vs llama.cpp via llama-swap on :9000. Compare Player-Coach turn counts, tool call success rate, time-to-complete.

### 6.3 Next sprint

- **Migrate AutoBuild to `ANTHROPIC_BASE_URL=http://promaxgb10-41b1:9000`** after A/B results confirm parity. Retain vLLM :8002 for one more sprint as a fallback.
- **Wire Jarvis intent routing to the same front door** via OpenAI-format requests to `gpt-oss-120b`.
- **Monitor swap frequency** via llama-swap's `/ui` dashboard; tune Forge loop ordering if swap churn exceeds ~3/hour during active builds.

### 6.4 Open for revisit

- **Preload target.** Current config preloads `qwen-coder-next` on startup (AutoBuild-first assumption). If Jarvis becomes the most-invoked agent in practice, switch preload to `gpt-oss-120b`.
- **Concurrency limits.** `concurrencyLimit: 4` on Coder-Next and `2` on GPT-OSS 120B are estimates. Revisit after two weeks of real fleet traffic with actual parallelism data.
- **TTL values.** `globalTTL: 1800` (30 min idle → unload) optimises for memory reuse across varied workloads. If the day splits cleanly between "AutoBuild morning" and "architect afternoon," raising TTL to 3600 may reduce cold-load cost at the price of higher idle memory usage.
- **Fine-tuned specialist models.** Once Gemma 4 31B variants land (GCSE tutor validated first on Bedrock, then other specialist-agent roles), register them as additional builders-group members.
- **Peer federation.** If a second machine joins the fleet (second GB10, Mac Studio), enable llama-swap peers so agents see a unified model list across nodes.

## 7. References

- `docs/research/dgx-spark/dark-factory-economics-and-model-serving.md` — primary research doc covering the cost analysis, forum findings, and model selection rationale
- `docs/research/dgx-spark/llama-swap-setup.md` — companion implementation guide with the full fleet `config.yaml`, smoke tests, operational monitoring, and troubleshooting
- `scripts/llama-swap-config.yaml` — standalone config file, ready to drop onto GB10 at `/opt/llama-swap/config/config.yaml`
- `.guardkit/llm-provider-switching.md` — per-repo Graphiti provider toggle doc (written 2026-04-20 as part of the immediate cost-stop response)
- `scripts/vllm-graphiti.sh` — existing Graphiti vLLM launcher with xgrammar JSON enforcement; unchanged by this ADR
- `scripts/vllm-serve.sh` — existing AutoBuild vLLM preset manager; continues as a fallback path
- NVIDIA Developer Forums — "Best LLM engine for several parallel models?" (eugr's llama.cpp recommendation), "Code assist and RAG in single node" (g.marconi's concurrent setup), "Best Local LLM for Ralph Loop" (cost-parallel story), "Implementation Guide: DGX Spark with Qwen3.5-35B-A3B via llama.cpp for Claude Code" (claytantor's SM121 reference)
- llama.cpp PR #17570 — Anthropic Messages API support
- `https://github.com/mostlygeek/llama-swap` — llama-swap repository
- `https://spark-arena.com/leaderboard` — community benchmarks for GB10

---

*Decision accepted: 2026-04-20*
*Scope: All unattended, autonomous, or continuous workloads in the GuardKit dark factory.*
*"Cost structure is an architectural property. Do the extrapolation before the bill arrives."*
