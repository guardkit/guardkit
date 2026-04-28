# GB10 Model Requirements Matrix — Fleet Consolidation Analysis

**Date:** 2026-04-28
**Purpose:** Map every model role across the Ship's Computer fleet, identify consolidation opportunities, and define the target serving architecture on the Dell DGX Spark GB10 (128GB unified memory).
**Predecessor:** `dark-factory-economics-and-model-serving.md`, `dark-factory-dataset-factory-conversation-starter.md`, `llama-swap-config.yaml`

---

## 1. Complete Role Inventory

Every model consumer across the fleet, with requirements:

| # | Role | Consumer | Key Requirements | Tool Calling? | JSON Strict? | Reasoning Depth | Concurrency |
|---|------|----------|-----------------|--------------|-------------|----------------|-------------|
| R1 | Graphiti LLM | Graphiti (all repos) | Entity + relationship extraction, strict JSON output | No | **Yes — critical** | Medium | Low (sequential episodes) |
| R2 | Embeddings | Graphiti / ChromaDB | 768-dim vectors (locked by FalkorDB index) | No | No | N/A | Medium (batch) |
| R3 | AutoBuild Player | GuardKit Factory | Code generation, filesystem ops | **Yes** (Anthropic Messages) | No | Medium-High | 1 (sequential by design) |
| R4 | AutoBuild Coach | GuardKit Factory | Validate code, run test commands (read-only) | No | Yes (JSON feedback) | High | 1 |
| R5 | Dataset Factory Player | agentic-dataset-factory | Generate training examples from RAG chunks | **Yes** (`rag_retrieval`, `write_output`) | No | High | 1 |
| R6 | Dataset Factory Coach | agentic-dataset-factory | Evaluate training data quality against GOAL.md criteria | No | Yes (JSON scoring) | High | 1 |
| R7 | Jarvis Intent Router | jarvis | Classify intent, match against registered agent signals | No | Yes (classification) | Low | High (every request) |
| R8 | Jarvis General Purpose | jarvis | ReAct agent — research, drafting, chores, broad tool access | **Yes** (multiple tools) | No | Medium-High | Low |
| R9 | Forge Orchestrator | forge | Pipeline checkpoint management, confidence-gated quality gates | No | Yes (gate decisions) | High | 1 |
| R10 | Architect Agent (inference) | architect-agent | Product docs → C4/ADRs → `/system-arch` input | **Yes** (MCP tools) | No | High | 1 |
| R11 | Study Tutor (inference) | study-tutor | GCSE tutoring — Socratic dialogue, multi-subject | No | No | Medium | 1 (per student) |
| R12 | Product Owner Agent | product-owner-agent | Raw info → structured product docs | **Yes** | No | High | 1 |
| R13 | Ideation Agent | ideation-agent | Weighted evaluation of ideas | No | Yes (scoring) | Medium | 1 |
| R14 | Architect Agent (fine-tune) | train_gemma4_moe.py | Training run — produces architect LoRA adapter | N/A (training) | N/A | N/A | Exclusive (offline) |
| R15 | Study Tutor (fine-tune) | train_gemma4_moe.py | Training run — produces tutor LoRA adapter | N/A (training) | N/A | N/A | Exclusive (offline) |
| R16 | Docling VLM | ingestion pipeline | Scanned PDF → text via Granite Docling 258M | No | No | N/A | Batch (offline) |

---

## 2. Model Consolidation Clusters

Roles that can share the same model, grouped by compatible requirements:

### Cluster A: "The Forever Pair" — always-on infrastructure (vLLM)

| Role | Model | Footprint | Port | Group |
|------|-------|-----------|------|-------|
| R1 — Graphiti LLM | Qwen2.5-14B-Instruct-FP8 | ~14 GB | :8000 | forever |
| R2 — Embeddings | nomic-embed-text-v1.5 | ~1 GB | :8001 | forever |
| **Total always-on** | | **~15 GB** | | |

**Why separate models:** Graphiti needs xgrammar JSON enforcement on an instruct model. MoE models (Qwen3.5, Qwen3.6-MoE variants) have confirmed JSON contamination bugs. Embeddings are a fundamentally different model type. These stay as-is.

**Bonus opportunity (R7):** Jarvis intent routing is a lightweight classification task. Qwen2.5-14B is already loaded for Graphiti — route classification requests to it via the same :8000 endpoint (or `qwen-graphiti` alias through llama-swap). No additional memory cost. Just needs a classification prompt, not a separate model.

### Cluster B: "The Coder" — code generation (llama.cpp, swap)

| Role | Why this cluster |
|------|-----------------|
| R3 — AutoBuild Player | Primary consumer. Needs tool calling + code quality |
| R5 — Dataset Factory Player | Also needs tool calling. Never concurrent with AutoBuild |

**Model options:**

| Candidate | Footprint | tok/s (martinB78) | Notes |
|-----------|-----------|-------------------|-------|
| Qwen3-Coder-Next FP8 | ~60 GB | 32.9 | Current. Proven with AutoBuild |
| Qwen3-Coder-Next int4-AutoRound | ~35 GB | **66.7** | 2× faster, needs A/B test |
| Qwen3.6-27B FP8 (dense) | ~27 GB | TBD | Wildcard — see §4 |

**Decision needed:** int4-AutoRound A/B test. If quality is within 10-15% of FP8, strictly prefer it: double the throughput at ~40% less memory.

### Cluster C: "The Reasoner" — evaluation, orchestration, coaching (llama.cpp, swap)

| Role | Why this cluster |
|------|-----------------|
| R4 — AutoBuild Coach | Validates code. Needs strong reasoning, JSON feedback |
| R6 — Dataset Factory Coach | Evaluates training data quality. Same pattern |
| R8 — Jarvis General Purpose | Complex reasoning tasks (simple ones → Cluster A) |
| R9 — Forge Orchestrator | Confidence-gated quality gates. Needs judgement |
| R12 — Product Owner Agent | Structured doc generation. Reasoning-heavy |
| R13 — Ideation Agent | Weighted evaluation. Scoring + reasoning |

**Model:** GPT-OSS 120B MXFP4 (~63 GB, 56.4 tok/s)

Six roles, one model, never concurrent. The Forge is sequential — it orchestrates which agent runs when. The Coach only runs after the Player finishes. Jarvis GP only handles one complex task at a time. All these roles share the same "strong reasoner with good JSON" profile.

### Cluster D: "The Fine-Tuned Specialist" — domain-specific inference (llama.cpp, swap)

| Role | LoRA Adapter | Domain |
|------|-------------|--------|
| R10 — Architect Agent (inference) | architect-lora | Architecture books, C4, ADRs |
| R11 — Study Tutor (inference) | gcse-tutor-lora | GCSE AQA curriculum, Socratic method |
| R12 — Product Owner Agent (future) | po-lora | PM methodology, product docs |

**Base model:** Gemma 4 26B A4B MoE (~26 GB base, adapters are a few MB each)

Same base, different LoRA adapters. LoRA adapter swap is near-instant (milliseconds) vs full model swap (~2-4 min). llama.cpp supports `--lora` hot-swap. This means architect → tutor → PO switching costs nearly nothing in the same llama-server process.

**Training (R14, R15):** Uses the same Gemma 4 26B A4B MoE base via `train_gemma4_moe.py` (Unsloth QLoRA). ~48 GB during training. **Exclusive — nothing else runs on GB10 during fine-tuning.**

### Cluster E: "Offline/Batch" — not in the serving graph

| Role | Model | When |
|------|-------|------|
| R14 — Fine-tuning (architect) | Gemma 4 26B A4B MoE | Offline, exclusive, overnight |
| R15 — Fine-tuning (tutor) | Gemma 4 26B A4B MoE | Offline, exclusive, overnight |
| R16 — Docling VLM | Granite Docling 258M | Batch ingestion, pre-pipeline |

These never compete with the serving fleet. Fine-tuning takes the whole box. Docling is a one-time pre-run step per domain.

---

## 3. Target Serving Architecture — Memory Budget

### Scenario 1: Current plan (swap between Coder and Reasoner)

```
Forever group (always loaded):
  Qwen2.5-14B (Graphiti)       ~14 GB
  nomic-embed (embeddings)      ~1 GB
                               --------
  Subtotal:                     ~15 GB

Builders group (one at a time):
  Option A: Coder-Next FP8      ~60 GB  → Total: ~75 GB  (53 GB headroom)
  Option B: Coder-Next int4     ~35 GB  → Total: ~50 GB  (78 GB headroom)
  Option C: GPT-OSS 120B        ~63 GB  → Total: ~78 GB  (50 GB headroom)
  Option D: Gemma 4 26B + LoRA  ~26 GB  → Total: ~41 GB  (87 GB headroom)
```

### Scenario 2: Qwen3.6-27B as multi-purpose workhorse (if validated)

```
Forever group (always loaded):
  Qwen2.5-14B (Graphiti)        ~14 GB
  nomic-embed (embeddings)       ~1 GB
  Qwen3.6-27B FP8 (everything)  ~27 GB
                                --------
  Total:                         ~42 GB  (86 GB headroom!)

No swap needed. Zero cold-load latency. Every role served instantly.
```

### Scenario 3: Full concurrent mode (Qwen3.6-27B + Gemma 4 specialist)

```
Forever group:
  Qwen2.5-14B (Graphiti)        ~14 GB
  nomic-embed (embeddings)       ~1 GB
  Qwen3.6-27B (coder/reasoner)  ~27 GB
  Gemma 4 26B + LoRA (specialist) ~26 GB
                                  --------
  Total:                          ~68 GB  (60 GB headroom for KV caches)
```

This is the dream state: Graphiti + embeddings + general-purpose LLM + fine-tuned specialist all loaded simultaneously. No swaps ever. The Forge loop runs without a single model transition.

---

## 4. The Qwen3.6-27B Wildcard — Validation Matrix

If Qwen3.6-27B passes all three tests below, it collapses Clusters B + C + the bonus R7 into a single always-on model:

| Test | Pass Criteria | How to Validate |
|------|-------------|-----------------|
| Graphiti entity extraction | JSON output matches Qwen2.5-14B quality; no contamination | Run `guardkit graphiti seed --force` on 3 repos, diff entity/relationship counts |
| AutoBuild Player (coding) | Player-Coach turn count within 15% of Coder-Next on same task | A/B test on one real FEAT task via llama-swap |
| Coach/Forge reasoning | Structured JSON feedback quality, confidence gate accuracy | Run Coach validation on known-good and known-bad code samples |

**If it fails any test:** Keep the swap architecture (Coder-Next + GPT-OSS 120B). The swap cost is real (~2-4 min) but tolerable for sequential Forge work.

**If it passes all three:** Promote to forever group. The entire builders group becomes unnecessary. This is the highest-leverage validation task on the roadmap.

**Note on Graphiti:** Even if Qwen3.6-27B passes extraction quality, you may want to keep Qwen2.5-14B for Graphiti specifically because it's proven + xgrammar-enforced + only 14 GB. The cost of keeping it loaded is trivial. Use Qwen3.6-27B for everything else.

---

## 5. Summary: Distinct Models Required

| # | Model | Purpose | Footprint | Serving | Swappable? |
|---|-------|---------|-----------|---------|-----------|
| 1 | **Qwen2.5-14B-Instruct-FP8** | Graphiti LLM + intent routing | ~14 GB | vLLM :8000 | No (forever) |
| 2 | **nomic-embed-text-v1.5** | Embeddings (768-dim) | ~1 GB | vLLM :8001 | No (forever) |
| 3 | **Qwen3-Coder-Next** (FP8 or int4) | AutoBuild Player + Dataset Factory Player | ~35-60 GB | llama.cpp via llama-swap | Yes (builders) |
| 4 | **GPT-OSS 120B MXFP4** | Coach + Forge + Jarvis GP + PO + Ideation | ~63 GB | llama.cpp via llama-swap | Yes (builders) |
| 5 | **Gemma 4 26B A4B MoE** | Architect + Study Tutor + PO (fine-tuned) | ~26 GB | llama.cpp via llama-swap | Yes (builders) |
| 6 | **Granite Docling 258M** | PDF VLM ingestion | ~0.5 GB | vLLM (batch, offline) | N/A |
| — | **Qwen3.6-27B** (if validated) | Could replace #3 + #4 above | ~27 GB | llama.cpp or vLLM | Promoted to forever |

**Minimum distinct model weights to download/store: 6** (5 serving + 1 batch).
**Maximum simultaneously loaded (Scenario 3): 4** models, ~68 GB.
**Swap groups at most: 3** members in builders (Coder, Reasoner, Specialist).

---

## 6. llama-swap Config Update Required

The current `llama-swap-config.yaml` has two builders members (`qwen-coder-next`, `gpt-oss-120b`). To support Cluster D, add Gemma 4:

```yaml
  "gemma4-specialist":
    name: "Fine-tuned specialist (Gemma 4 26B A4B MoE)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/gemma4-26b-a4b/gemma4-26b-a4b.gguf
      --lora /opt/llama-swap/models/gemma4-26b-a4b/architect-lora.gguf
      --alias gemma4-specialist
      --ctx-size 32768
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
    checkEndpoint: /health
    ttl: 1800
    concurrencyLimit: 1
    aliases:
      - "architect-agent"
      - "study-tutor"
      - "product-owner"
```

LoRA adapter swap happens via the `--lora` flag at startup. For hot-swap between architect/tutor/PO, llama-swap would need to restart the process with a different `--lora` path — or use llama.cpp's runtime LoRA swap API if available.

---

## 7. Open Questions

1. **Dataset Factory generation model — confirmed?** The conversation starter says `vllm-agentic-factory.sh` is out of date and Gemma 4 26B is the fine-tuning target, but the actual generation pipeline model (what runs the Player-Coach loop) remains unconfirmed. GPT-OSS 120B via llama-swap is the proposed path per §3.11 of the economics doc. Needs validation.

2. **Qwen3.6-27B timeline.** Community benchmarks have had ~4 days since release. When is there enough data to run the validation matrix in §4?

3. **LoRA hot-swap in llama.cpp.** Does llama-server support runtime LoRA switch without process restart? If yes, Cluster D becomes much more elegant. If no, llama-swap restarts the process per-adapter (still fast, ~30s for 26B model).

4. **Jarvis intent routing on Graphiti's Qwen2.5-14B.** Is there a latency concern from sharing the vLLM instance? Graphiti episodes are bursty during seeding but idle most of the time. Intent classification prompts are tiny (~100 tokens). Should be fine but worth a quick load test.

5. **Coder-Next int4 A/B test priority.** This is the single highest-ROI test: if int4 quality is good enough, it frees ~25 GB of headroom and doubles throughput. Worth doing before the Qwen3.6-27B evaluation.

---

*Prepared: 2026-04-28 | GB10 model fleet planning*
*Cross-references: dark-factory-economics-and-model-serving.md, llama-swap-config.yaml, dark-factory-dataset-factory-conversation-starter.md*
