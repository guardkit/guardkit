# GB10 memory budget — where it actually goes, and what to offload to the MacBook

**Date:** 2026-05-28
**Question:** do the agents (forge / jarvis / study-tutor / architect) eat a lot
of GB10 memory, and would running them on the MacBook Pro (M2 Max, 96 GB) free
memory for inference?
**Short answer:** the *agent apps* cost almost nothing — moving them frees ~0.
The memory is the *LLM models* behind them. Offloading the right **models**
(tutor + architect) to the MacBook frees ~40 GB on the GB10.

---

## 1. Measured breakdown (2026-05-28, GB10 `promaxgb10-41b1`)

### App containers — negligible (`docker stats`)

| Container | Memory |
|---|---|
| forge-prod | 25 MiB |
| graphiti-mcp | 23 MiB |
| open-webui | 48 MiB |
| ships-computer-nats | 38 MiB |
| specialist-agent-architect-agent-1 | 5 MiB |
| specialist-agent-product-owner-agent-1 | 5 MiB |
| study-tutor-gcse-tutor-1 | 10 MiB |
| **Total app layer** | **~0.15 GB** |

These are thin orchestration shells (Python apps, NATS, the OpenWebUI front
end). They *call* the LLM endpoints; they hold no model weights.

### LLM models — this is the memory (`nvidia-smi` per-process GPU memory)

| Model (llama-swap) | Serves | GPU memory |
|---|---|---|
| nomic-embed | Graphiti embeddings | ~1.0 GB |
| qwen-graphiti (Qwen2.5-14B) | Graphiti extraction, jarvis-router | ~28 GB* |
| qwen36-workhorse (Qwen3.6-35B-A3B) | jarvis-reasoner, forge, autobuild, dataset-factory | **25.6 GB** |
| architect-agent (Gemma 4 thinking) | software-architect / ddd-architect (ADR checks) | **20.2 GB** |
| gemma4-tutor (Gemma 4 26B-A4B) | study-tutor / gcse-tutor | **19.6 GB** |
| granite-docling (vLLM, on-demand) | LPA extraction | ~11 GB |
| qwen-coder-next (vLLM/FP8, on-demand, exclusive) | autobuild Player | ~95 GB |

\* qwen-graphiti was not resident in this snapshot; ~28 GB from findings §4.1.

**The 1000× ratio is the whole point:** the apps are ~0.15 GB; the models are
~20–95 GB each. Memory pressure on the GB10 is *entirely* the models.

---

## 2. So: moving the *apps* to the MacBook frees nothing

forge, jarvis (supervisor), the study-tutor app, the specialist-agent
containers, OpenWebUI — moving any/all of these to the MacBook frees ~0.15 GB
total. They'd still call the LLM endpoints; if the models stay on the GB10,
the GB10 memory is unchanged and you've just added a network hop.

**To free GB10 memory you must move MODELS, not apps.**

---

## 3. What to offload to the MacBook (M2 Max, 96 GB)

The M2 Max 96 GB comfortably runs 20–35B models via Ollama or MLX. Best
candidates are the workloads that are **independent of the GB10's
build/ingestion critical path**:

| Move to MacBook | Footprint freed | Why it's a good candidate |
|---|---|---|
| **gemma4-tutor** | **~20 GB** | Daughter's study tutor — independent of builds; also removes the tutor-vs-coder contention noted in §9.2. M2 Max runs Gemma 4 26B easily. |
| **architect-agent** | **~20 GB** | ADR / architecture checks are occasional and interactive; latency over the network is fine. |
| **Both** | **~40 GB** | Drops GB10 steady-state from ~93 GB to ~53 GB → ample room for coder-next (95 GB) + docling + autobuild + graphiti. |

**Keep on the GB10** (latency-sensitive, high-volume, or build-critical):

- **qwen-graphiti** + **nomic-embed** — continuous ingestion; co-located with FalkorDB writes.
- **qwen36-workhorse** — busiest model (jarvis-reasoner, forge, autobuild legacy).
- **qwen-coder-next** / **qwen3-coder-30b** — autobuild Players; want GB10 throughput.
- **granite-docling** — LPA extraction; tiny (~11 GB) and already co-resident.

---

## 4. How to wire the offload

Two options (see DECISION-DF-001 §6.4 "peer federation"):

1. **Simplest — MacBook serves the models directly.** Run Ollama (or MLX
   via `mlx_lm.server`) on the MacBook serving Gemma 4 tutor (+ architect)
   on an OpenAI-compatible endpoint over Tailscale. Point the consuming apps
   at the MacBook:
   - study-tutor app → `http://<macbook-tailscale>:11434/v1` (Ollama), model `gemma4-tutor`.
   - architect callers (`software-architect` alias) → same host.
   Then **remove `gemma4-tutor` and `architect-agent` from the GB10
   `config.yaml`** (and from `hooks.on_startup.preload` and the matrix sets).
2. **Unified — llama-swap peer federation.** Run llama-swap on the MacBook
   too and federate, so a single `:9000` model list spans both nodes and
   requests route by model name. More moving parts; do (1) first.

**Caveats:**
- Cross-machine calls go over Tailscale — fine for conversational tutoring
  and occasional ADR checks; not ideal for high-volume batch.
- M2 Max throughput for a 26B-A4B (MoE, ~4B active) is roughly 20–40 tok/s
  via MLX — adequate for these roles.
- Gemma 4 weights must be present on the MacBook (Ollama pull / MLX convert).
- Reachy Scholar's spoken tutoring already uses **Gemini Live**, not
  gemma4-tutor (findings §6), so moving gemma4-tutor only affects the
  text/OpenWebUI study-tutor path, not Reachy.

---

## 5. Bottom line

- Apps ≈ 0 GB; models ≈ everything.
- Offloading **gemma4-tutor + architect-agent** to the MacBook frees **~40 GB**
  on the GB10 and removes the tutor↔build memory contention.
- Keep graphiti, embeddings, workhorse, the coders, and docling on the GB10.
