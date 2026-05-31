# DGX Spark / GB10 Research

Research, decisions, and deployment docs for the GuardKit inference fleet on the Dell DGX Spark GB10 (Blackwell SM121, 128 GB unified memory).

> **For history**: this directory's primary record is [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md) §1–§11 (chronological, from 2026-05-14 through 2026-05-31). **For current operational state**: the sections immediately below are the source of truth. Update them when the live config changes; don't expect to reconstruct today's reality from the findings doc alone.

---

## Current architecture (steady state 2026-05-31)

**All-llama.cpp via llama-swap on `:9000`**, plus vLLM-in-Docker for a handful of multi-modal models that need it (`granite-docling`, `granite-vision-4-1-4b`). One memory manager — llama-swap — owns the unified-memory pool; vLLM containers run as llama-swap children via per-model launch scripts in `/opt/llama-swap/scripts/`.

### Always-on preload (~80 GB resident, ~40 GB headroom)

| Model | Role | Footprint | Engine |
|---|---|---:|---|
| `qwen-graphiti` (Qwen2.5-14B-Instruct Q8_0) | Graphiti entity extraction; default `jarvis-router` LLM | ~28 GB (incl. ctx 65K × `-np 4` KV) | llama.cpp |
| `nomic-embed` (nomic-embed-text-v1.5 F16) | Embeddings (768 dim) for Graphiti + ChromaDB | ~2 GB | llama.cpp |
| `qwen36-workhorse` (Qwen3.6-35B-A3B-Instruct UD-Q4_K_XL) | AutoBuild Player + Coach (default); Forge; Jarvis-reasoner; Dataset Factory; `claude-sonnet-*` aliases | ~28–30 GB (incl. ctx 131K KV) | llama.cpp |
| `architect-agent` (Gemma 4 26B-A4B Q4_K_M + thinking template) | `/system-arch`, `/system-design`, `/arch-refine`, `/system-plan` | ~22 GB (incl. ctx 65K KV) | llama.cpp |

The keep-alive timer (`llama-swap-keepalive.timer`, 5-min cadence) probes these four; if any child crashes, the next probe revives it. See [`llama-swap-keepalive-start-stop.md`](./llama-swap-keepalive-start-stop.md).

### On-demand models (loaded by request, auto-unload on idle)

| Model | Aliases | Footprint when loaded | ttl | Engine | Purpose |
|---|---|---:|---:|---|---|
| `gemma4-tutor` (Gemma 4 26B-A4B Q4_K_M + Socratic template) | `study-tutor`, `gcse-tutor`, `gemma4-specialist` | ~17 GB | 1800s | llama.cpp | GCSE study tutor (Socratic) |
| `qwen3-coder-30b` (Qwen3-Coder-30B-A3B UD-Q4_K_XL) | `autobuild-coder` | ~22–25 GB | 600s | llama.cpp | Opt-in code-tuned alternative to workhorse for autobuild |
| `granite-docling` (IBM Granite Docling 258M) | `granite-docling-258M`, `docling` | ~11 GB | 1800s | vLLM-in-Docker (cu130-nightly) | Page→markdown extraction for the LPA POC (legacy, being phased out) |
| `granite-vision-4-1-4b` (IBM Granite Vision 4.1-4b bf16) | `granite-vision-4.1-4b`, `granite-vision` | ~26 GB | 1800s | vLLM-in-Docker (v0.22.0-aarch64-cu129) | LPA POC's planned replacement for docling-258M |

### Matrix sets (which models can co-reside)

| Set | Members | Resident | When solver picks it |
|---|---|---:|---|
| `all` (default) | qg + ne + qw + aa + dl | ~80 GB always-on + ~11 GB if docling loaded | Any request for a member of this set. Docling loads in-place. |
| `tutor` | gt + qw | ~45 GB | `study-tutor` request → evicts qg + ne + aa + dl |
| `lpa` | gv + qw + ne | ~56 GB | `granite-vision-4-1-4b` request → evicts qg + aa + dl |
| `coder_30b` | qc | ~22 GB | `autobuild-coder` request → evicts everything else in `all` |

**Mutually-exclusive workloads**: `tutor`, `lpa`, and `coder_30b` each evict at least part of the `all` family. While any of them is loaded, the always-on workloads are partially unavailable (e.g. **Graphiti is unavailable during `lpa` and `coder_30b` runs**). The keep-alive timer's 5-min probe cycle will evict them mid-session — see "When to pause keep-alive" in [`llama-swap-keepalive-start-stop.md`](./llama-swap-keepalive-start-stop.md).

### Per-workload routing recipes

| Workload | Model / alias | Set triggered | Notes |
|---|---|---|---|
| Graphiti capture (`/feature-spec`, `/system-arch` write, `/task-complete`, autobuild outcomes) | `qwen-graphiti` + `nomic-embed` (implicit) | `all` | Always available unless a mutually-exclusive set is loaded |
| `/system-arch`, `/system-design`, `/arch-refine`, `/system-plan` | `software-architect` | `all` (aa loaded by request within set) | Thinking-mode output |
| Jarvis routing / reasoning | `jarvis-router` / `jarvis-reasoner` | `all` | Routes to workhorse |
| AutoBuild default (Player + Coach) | `claude-sonnet-4-5-20250929` / `autobuild-player` / `coach` | `all` (qw) | Workhorse — also wins AgentBench vs coder-next (see findings §9.9) |
| AutoBuild with code-tuned alternative | `--model autobuild-coder` | `coder_30b` (exclusive) | Evicts the family for the build duration |
| Study tutor session | `study-tutor` | `tutor` | Evicts graphiti + architect; pause keep-alive for long sessions |
| LPA page→markdown extraction | `granite-vision-4-1-4b` | `lpa` | Evicts graphiti + architect + docling; pause keep-alive for long sessions; first load ~110 s cold |
| LPA legacy docling (being phased out) | `granite-docling` | `all` (loads in-place) | Co-resident with family — no eviction |

### Operational essentials

- **Live config**: `/opt/llama-swap/config/config.yaml` (NOT in repo; backups exist alongside at `.bak-YYYY-MM-DD-*`)
- **Launch scripts** (vLLM containers): `/opt/llama-swap/scripts/vllm-{docling,granite-vision,coder-next}.sh`
- **Logs**: `/opt/llama-swap/logs/llama-swap.log`
- **Systemd**: `llama-swap.service` (user unit) + `llama-swap-keepalive.timer` (system unit, 5-min)
- **Pause/resume keep-alive**: see [`llama-swap-keepalive-start-stop.md`](./llama-swap-keepalive-start-stop.md)
- **Memory safety hatch**: `curl http://localhost:9000/unload` drops every loaded model; the always-on family revives on the next keep-alive probe (or on the next request to one of them)
- **Memory ceiling**: 121 GB usable (of 128 GB unified). Safe ceiling ~115 GB. The §9.4 freeze at 114 GB / 7 GB free / 11 GB swap is the documented incident — stay below that.

---

## Document index

### Current (active operational state)

| Document | Purpose |
|---|---|
| `README.md` (this file) | **Current operational state.** Architecture table, matrix sets, per-workload recipes, pointers to operational docs. Update when the live config changes. |
| [`llama-swap-keepalive-start-stop.md`](./llama-swap-keepalive-start-stop.md) | Keep-alive timer control: pause / resume / inspect; per-workload "when to pause" recipes. |
| [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md) | Chronological findings log §1–§11: AutoBuild + llama-swap setup; the `-np` ctx-split trap; memory-ceiling freeze postmortem (§9.4); workhorse-as-Graphiti failed experiments (§9.5–§9.7); Gemma-4-as-Graphiti failed experiment (§9.8); coder-next drop + tutor↔architect rotation (§9.9); granite-vision-4-1-4b registration + fix (§9.10–§9.11). |
| [`gemma4-as-graphiti-experiment-runbook.md`](./gemma4-as-graphiti-experiment-runbook.md) | The runbook executed for §9.8 (Gemma 4 as Graphiti backend; failed). Preserved as a worked example of the experiment pattern. |
| [`gb10-memory-budget-and-macbook-offload.md`](./gb10-memory-budget-and-macbook-offload.md) | Memory-budget analysis: where the 121 GB goes, what could offload to the MacBook Pro M2 Max. |
| [`RUNBOOK-v3-production-deployment.md`](./RUNBOOK-v3-production-deployment.md) | Original production deployment runbook (2026-04-28). Six gaps found and fixed via TASK-RUN-D6F4. Architectural sections are still current; model lineup table is historical (superseded by this README). |
| [`llama-swap-systemd-supervision.md`](./llama-swap-systemd-supervision.md) | User-space systemd unit with `-watch-config` for auto-reload. |
| [`POST-VALIDATION-model-strategy-revision.md`](./POST-VALIDATION-model-strategy-revision.md) | The dense-27B → MoE-35B-A3B strategy pivot. Physics + decision. |
| [`gb10-model-requirements-matrix.md`](./gb10-model-requirements-matrix.md) | Fleet-wide model consolidation analysis: 16 roles → 6 models → 4 deployed. Role mapping still valid; speed expectations superseded. |
| [`qwen3.6-27b-gb10-community-research.md`](./qwen3.6-27b-gb10-community-research.md) | NVIDIA DGX Spark forum research on Qwen3.6-27B. |

### Historical (superseded but preserved)

| Document | Status |
|---|---|
| [`llama-swap-setup.md`](./llama-swap-setup.md) | **Superseded by RUNBOOK-v3.** Describes the old vLLM proxy architecture. Kept for the llama.cpp SM121 build flags and the dynamic VRAM launcher pattern. |
| [`llama-swap-config.yaml`](./llama-swap-config.yaml) | **Superseded.** Old config with vLLM proxy entries. Live config is at `/opt/llama-swap/config/config.yaml`. |
| [`dark-factory-economics-and-model-serving.md`](./dark-factory-economics-and-model-serving.md) | Original research doc: April 2026 cost crisis (£30 Gemini spend in 3 days), forum research, DECISION-DF-001. Conclusions about model choices are superseded. |
| [`dark-factory-dataset-factory-conversation-starter.md`](./dark-factory-dataset-factory-conversation-starter.md) | Original conversation starter. Historical. |
| [`TASK-graphiti-yaml-endpoint-migration.md`](./TASK-graphiti-yaml-endpoint-migration.md) | Task spec for the 2026-04-29 vLLM→llama-swap endpoint migration. Historical. |

### Validation records

| Document | What it proved |
|---|---|
| [`RESULTS-v3-production-deployment.md`](./RESULTS-v3-production-deployment.md) | Production deployment results: 65 GB VRAM, 41.32 tok/s workhorse, all four models coexisting. |
| [`VALIDATION-D6F4-gap-fix-results.md`](./VALIDATION-D6F4-gap-fix-results.md) | All six D6F4 gaps verified PASS. |
| [`VALIDATION-OPS-7CB1-9F2A-results.md`](./VALIDATION-OPS-7CB1-9F2A-results.md) | Keep-alive timer revives crashed children in 30s; concurrency tuning eliminated 429 throttling. |
| [`RESULTS-v2-all-llamacpp-validation.md`](./RESULTS-v2-all-llamacpp-validation.md) | All-llama.cpp works: Graphiti JSON via llama.cpp (no xgrammar needed); embeddings at 768 dims; MoE workhorse at 45 tok/s. **The key evidence that eliminated vLLM.** |
| [`RESULTS-qwen3.6-27b-validation.md`](./RESULTS-qwen3.6-27b-validation.md) | Dense Qwen3.6-27B quality excellent, 8.35 tok/s bandwidth wall. **The key evidence that pivoted to MoE.** |
| [`RUNBOOK-v2-all-llamacpp-architecture.md`](./RUNBOOK-v2-all-llamacpp-architecture.md) | Validation runbook for RESULTS-v2. |
| [`RUNBOOK-qwen3.6-27b-validation.md`](./RUNBOOK-qwen3.6-27b-validation.md) | Validation runbook for RESULTS-v1. |

### Background reading

| Document | Notes |
|---|---|
| `DGX Spark, Nemotron3, and NVFP4 - Thomas P. Braun.pdf` | NVFP4 optimisation background |

---

## Key decisions

1. **DECISION-DF-001** (2026-04-20): No cloud API on dark factory critical path. Triggered by £30 Gemini spend in 3 days.
2. **Dense 27B → MoE 35B-A3B** (2026-04-28): Bandwidth physics caps dense models at ~8–10 tok/s on GB10; MoE with 3B active params achieves 40+ tok/s.
3. **vLLM → all-llama.cpp** (2026-04-29): vLLM pre-allocates ~50 GB for a 14 GB model; llama.cpp takes only what it needs. vLLM kept for the few models llama.cpp can't serve (granite-docling vision encoder, granite-vision-4-1-4b).
4. **Four always-on preload** (2026-05-30, §9.9): qg + ne + qw + aa at ~80 GB, leaves ~40 GB headroom for on-demand workloads.
5. **Drop qwen-coder-next** (2026-05-30, §9.9): Forum AgentBench shows workhorse-class beats coder-next on agent tasks (59.3% vs 46.0%); coder-next's ~92 GB resident footprint blocked Graphiti during every autobuild run. Launch script + HF cache preserved for zero-download restoration if needed.
6. **`tutor` and `lpa` matrix sets are mutually exclusive with the family** (2026-05-30, §9.9, §9.11): Long sessions of either require pausing the keep-alive timer.
7. **Gemma 4 26B-A4B is not viable as Graphiti backend** (2026-05-30, §9.8): Thinking-mode markers leak into `json_object` calls; hallucinated dedup indices. Added to the eliminated list in `docs/reference/graphiti-llm-selection.md`.

---

## External references

- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719) — primary community resource for benchmarks and setup tips
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard) — community-submitted benchmarks
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) — model lifecycle manager (the unified front door on :9000)
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) — inference engine for everything except the vLLM-served vision models
- [llama.cpp Anthropic Messages API PR #17570](https://github.com/ggml-org/llama.cpp/pull/17570) — the change that made llama.cpp a drop-in for the Claude Agent SDK
- [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) — the vLLM Docker images the granite-docling / granite-vision scripts depend on
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama) — reference implementation for LiteLLM + llama-swap + vLLM + llama.cpp on GB10
- [AEON-7 DFlash deployment](https://github.com/AEON-7/Qwen3.6-NVFP4-DFlash) — reference for future DFlash integration
- [LiteLLM](https://docs.litellm.ai/) — unified API proxy (potential Phase 4 target)
- [sparkrun](https://sparkrun.dev) — inference orchestration CLI (monitoring for future adoption)

---

## Rollback

If the all-llama.cpp + on-demand-vLLM architecture needs to be reverted to the pre-2026-04-29 pure-vLLM stack:

```bash
sudo systemctl stop llama-swap
cp ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml.pre-llamacpp.bak \
   ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml
cp ~/Projects/appmilla_github/guardkit/scripts/archive-vllm/*.sh \
   ~/Projects/appmilla_github/guardkit/scripts/
./scripts/vllm-graphiti.sh && ./scripts/vllm-embed.sh
```
