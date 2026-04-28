# Conversation Starter: Dark Factory Economics — Dataset Factory Model Correction

**Date:** 2026-04-25
**Predecessor sessions:** 2026-04-20 (cost crisis + llama-swap discovery), 2026-04-24 (forum review + Qwen3.6-27B), 2026-04-25 (dataset factory co-existence)
**Purpose:** Correct §3.11 of the dark factory research doc to reflect the actual agentic-dataset-factory model setup, then update the llama-swap config and ADR accordingly.

---

## 1. What happened across these sessions

### The triggering event (2026-04-20)

Rich saw £29.91 Gemini API spend on the GuardKit Google Cloud project in just 3 days (Fri–Sun) of normal Graphiti ingestion work. Extrapolated: £300–400/month for Graphiti alone, £1,200–1,900/month at full fleet. The dark factory economic thesis breaks at that price point — marginal cost per build must approach zero for unconstrained experimentation.

**Immediate action taken:** All 13 repos' `.guardkit/graphiti.yaml` reverted to `llm_provider: vllm` (local Qwen2.5-14B-Instruct-FP8 on GB10 port 8000). Provider switching documented in `.guardkit/llm-provider-switching.md`.

### The llama-swap discovery (2026-04-20)

Research into the NVIDIA DGX Spark forums found:
- **eugr** (author of `spark-vllm-docker`) recommends llama.cpp over vLLM for concurrent multi-model serving on GB10's unified memory — vLLM's percentage-based `--gpu-memory-utilization` is wrong for shared memory
- **llama.cpp PR #17570** (Jan 2026) added native Anthropic `/v1/messages` support — removes the previous blocker for Claude Agent SDK / AutoBuild compatibility
- **mostlygeek/llama-swap** provides exactly the model lifecycle management needed: groups (always-on vs swappable), request queuing during swap, TTL-based unloading, web UI monitoring

### Forum review (2026-04-24)

Two NVIDIA forum posts reviewed at Rich's request:
- ["Managing Local LLM Orchestration"](https://forums.developer.nvidia.com/t/managing-local-llm-orchestration/363264) — griffith.mark's three-stage model (manual → ops-driven → intelligent routing), maps to Jarvis's intent router as Stage 3
- ["Running a Full LLM Stack on DGX Spark GB10"](https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580) — martinB78's authoritative benchmarks and dynamic VRAM launcher

Key findings from martinB78's benchmarks:
- **Qwen3-Coder-Next int4-AutoRound: 66.7 tok/s** (vs 32.9 tok/s FP8, at ~35 GB vs ~60 GB)
- **GPT-OSS 120B MXFP4: 56.4 tok/s** (fastest 120B on Spark)
- Dynamic VRAM launcher script needed for L-tier model swaps (CUDA stale memory issue)
- LiteLLM as Phase 4 routing layer on top of llama-swap for cloud fallbacks + usage logging

Same day: Qwen3.6-27B released. Dense 27B, Apache 2.0, natively multimodal. "One model, no swap" thesis — if it handles coding + reasoning + entity extraction, the entire swap infrastructure becomes optional.

### Dataset factory co-existence (2026-04-25)

Rich raised that the agentic-dataset-factory can't co-exist with Graphiti on the GB10 — this is a significant daily workflow bottleneck. Analysis showed `vllm-agentic-factory.sh`'s default preset (Qwen3.5-35B-A3B FP8 at `GPU_UTIL=0.70`) claims ~85 GB, which can't co-exist with Graphiti's ~49 GB. Total: ~134 GB on a 121.7 GB pool.

llama-swap fixes this because llama.cpp takes only what models actually need (weights + KV cache), not a percentage of total VRAM.

**However:** Rich then flagged that `vllm-agentic-factory.sh` is **out of date**. The actual current model for the dataset factory is **Gemma 4 26B A4B MoE** (via `train_gemma4_moe.py`), which uses ~48 GB during training. Rich clarified this model is for fine-tuning the architect-agent and GCSE study tutor, not directly for the dataset generation pipeline itself.

## 2. What needs doing in this session

### 2.1 Understand the actual dataset factory setup

Read these files from the `agentic-dataset-factory` repo to understand the current state:

```
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/tasks/backlog/gemma4-moe-deploy/IMPLEMENTATION-GUIDE.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/docs/research/train_gemma4_moe.py
```

Also look for more up-to-date docs in the repo:
```
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/docs/
```

Key questions to answer:
- What model does the Player-Coach loop in the agentic-dataset-factory actually use NOW for generating training data? (Not the fine-tuning target — the LLM that runs the generation pipeline)
- What's the actual memory footprint during a dataset generation run?
- What tool calling mechanism does the Player use? (vLLM `--tool-call-parser`? OpenAI-format? Anthropic-format?)
- Can GPT-OSS 120B (or Qwen3.6-27B) substitute in for the generation model?

### 2.2 Correct §3.11 in the research doc

The current §3.11 in `docs/research/dgx-spark/dark-factory-economics-and-model-serving.md` references `vllm-agentic-factory.sh` and assumes Qwen3.5-35B-A3B is the generation model. This needs correcting based on whatever the actual current setup is.

### 2.3 Verify the four replacement files

The previous session produced four replacement files but the Filesystem:edit_file tool failed to persist changes directly to Rich's Mac. The files exist in Claude's outputs and Rich downloaded them, but they need verification:

| File | Target path | Status |
|---|---|---|
| `dark-factory-economics-and-model-serving.md` | `guardkit/docs/research/dgx-spark/` | Has §3.7–3.11, migration phases 2b/2c/4/5, updated refs — but §3.11 needs correction |
| `llama-swap-setup.md` | `guardkit/docs/research/dgx-spark/` | Has §12 (dynamic VRAM launcher), §13 (LiteLLM), int4-AutoRound download |
| `README.md` | `guardkit/docs/research/dgx-spark/` | Updated summaries and external refs |
| `vllm-agentic-factory.sh` | `guardkit/scripts/` | Header annotated with llama-swap alternative — may need further correction |

### 2.4 Update llama-swap config.yaml alias

The current `config.yaml` has a `dataset-factory` alias on `gpt-oss-120b`. This may need changing depending on what model the factory actually needs.

## 3. Documents created across these sessions

### ADR (created 2026-04-20, ready to seed)
- `guardkit/docs/decisions/DECISION-DF-001-local-first-inference-on-dark-factory-critical-path.md`
- Seed script: `guardkit/.guardkit/seeding/DECISION-DF-001-seed.sh`
- **Run from repo root:** `cd /Users/richardwoollcott/Projects/appmilla_github/guardkit && ./.guardkit/seeding/DECISION-DF-001-seed.sh`
- Seed script has the `SCRIPT_DIR`/`REPO_ROOT` fix for location-independence

### llama-swap config (created 2026-04-20)
- `guardkit/scripts/llama-swap-config.yaml` — standalone config for GB10, drop to `/opt/llama-swap/config/config.yaml`

### Research docs (created 2026-04-20, updated 2026-04-24/25)
- `guardkit/docs/research/dgx-spark/dark-factory-economics-and-model-serving.md` — primary research doc
- `guardkit/docs/research/dgx-spark/llama-swap-setup.md` — companion implementation guide
- `guardkit/docs/research/dgx-spark/README.md` — index

## 4. Architectural decisions made (do not reopen)

1. **"No cloud API on the dark factory critical path."** Cloud APIs for interactive sessions only (5-10/month, £20-50/month). All autonomous work runs local on GB10.
2. **llama-swap as unified inference front door on :9000.** Existing vLLM Graphiti (:8000) and embedder (:8001) proxied via `proxy:` overrides. New swap members via llama.cpp.
3. **Groups: "forever" (Graphiti + embeddings, persistent) and "builders" (Coder-Next + GPT-OSS 120B, exclusive swap).**
4. **Graphiti LLM stays on Qwen2.5-14B-Instruct-FP8.** Proven JSON enforcement via xgrammar. MoE models (Qwen3.5-35B-A3B, Qwen3.6-35B-A3B) have confirmed JSON contamination bugs.
5. **Embeddings stay on nomic-embed-text-v1.5 (768-dim).** FalkorDB index locked to this dimensionality.
6. **LiteLLM as Phase 4 addition** (routing, cloud fallback, usage logging) — not Phase 1.

## 5. Open decisions

- **Qwen3-Coder-Next FP8 vs int4-AutoRound** — 66.7 vs 32.9 tok/s, needs A/B test
- **Qwen3.6-27B as multi-purpose workhorse** — too new (released 2026-04-24), waiting for community validation
- **What model does the dataset factory generation pipeline actually use?** — this is the open question for this session
- **Preload target** — currently `qwen-coder-next`, may change based on actual usage patterns
- **TTL values** — 1800s (30 min) is an estimate, revisit with real data

## 6. Key file locations

```
# GuardKit repo
/Users/richardwoollcott/Projects/appmilla_github/guardkit/
├── .guardkit/
│   ├── llm-provider-switching.md          # Provider toggle doc
│   ├── graphiti.yaml                       # Points at local vLLM (:8000)
│   └── seeding/
│       ├── FEAT-1253-seed.sh              # Existing seed pattern
│       └── DECISION-DF-001-seed.sh        # New ADR seed
├── docs/
│   ├── decisions/
│   │   └── DECISION-DF-001-local-first-inference-on-dark-factory-critical-path.md
│   └── research/dgx-spark/
│       ├── README.md
│       ├── dark-factory-economics-and-model-serving.md
│       └── llama-swap-setup.md
└── scripts/
    ├── vllm-serve.sh                      # AutoBuild vLLM preset manager
    ├── vllm-graphiti.sh                   # Graphiti vLLM launcher
    ├── vllm-embed.sh                      # Embedder launcher
    ├── vllm-agentic-factory.sh            # Dataset factory launcher (OUT OF DATE)
    └── llama-swap-config.yaml             # llama-swap fleet config

# Agentic Dataset Factory repo
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/
├── tasks/backlog/gemma4-moe-deploy/
│   └── IMPLEMENTATION-GUIDE.md            # READ THIS
├── docs/research/
│   └── train_gemma4_moe.py               # READ THIS — fine-tuning script (Gemma 4 26B MoE)
└── docs/                                  # CHECK FOR MORE UP-TO-DATE DOCS

# GB10 model serving (current state)
promaxgb10-41b1:8000  — vLLM Qwen2.5-14B-Instruct-FP8 (Graphiti, running)
promaxgb10-41b1:8001  — vLLM nomic-embed-text-v1.5 (embeddings, running)
promaxgb10-41b1:8002  — vLLM Qwen3-Coder-Next (AutoBuild, on-demand via vllm-serve.sh)
```

## 7. Community references (gold)

- [NVIDIA DGX Spark forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard)
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama) — authoritative reference implementation
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) — model lifecycle manager
- [sparkrun](https://sparkrun.dev) — monitoring for future adoption
- [llama.cpp Anthropic API PR #17570](https://github.com/ggml-org/llama.cpp/pull/17570)
