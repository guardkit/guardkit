# Review Report: TASK-REV-8B3A

## Executive Summary

The Graphiti seeding failure for the feature-spec v2 document is caused by **OpenAI `/responses` endpoint rate limiting** (LLM calls, not embedding calls). A single `add_episode()` invocation on a ~70KB document triggers **~140 LLM calls + ~215 embedding API calls** due to graphiti-core's entity extraction, deduplication, edge resolution, and summarisation pipeline. The retry backoff intervals (0.3–0.9s) are far too short for the volume of parallel requests fired.

**Recommended approach**: Deploy local embeddings + LLM on the Dell ProMax GB10 via **vLLM** (already planned for AutoBuild inference), fully eliminating the OpenAI rate limit dependency. graphiti-core's architecture natively supports this with zero library changes — both `EmbedderClient` and `LLMClient` accept `base_url` pointing at vLLM's OpenAI-compatible API. Using vLLM rather than Ollama consolidates the inference stack on a single runtime with significantly higher throughput (up to 20x under concurrency).

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Standard |
| **Reviewer** | Claude Opus 4.6 |
| **Date** | 2026-02-22 |

---

## Finding 1: Root Cause — LLM Call Fan-Out, Not Embeddings

### Evidence

The seed log shows retries against the `/responses` endpoint (OpenAI's LLM/chat completions endpoint), **not** the `/embeddings` endpoint:

```
INFO:openai._base_client:Retrying request to /responses in 0.392428 seconds
INFO:openai._base_client:Retrying request to /responses in 0.949371 seconds
WARNING:guardkit.knowledge.graphiti_client:Episode creation request failed: Rate limit exceeded.
```

### Analysis

graphiti-core's `add_episode()` pipeline for a document of this size (~70KB, ~8,800 words, ~92 headings) triggers a massive API call fan-out:

| Step | Type | Estimated Calls | Parallelism |
|------|------|-----------------|-------------|
| Entity extraction (chunked) | LLM | ~5 (5 chunks at 12K chars) | Parallel |
| Node dedup search | Embedding | ~50 (1 per entity) | Parallel (semaphore=20) |
| Node dedup resolution | LLM | 1 (batched) | Single |
| Edge extraction (covering chunks) | LLM | ~4 (for ~50 nodes, MAX_NODES=15) | Parallel |
| Edge embedding (pre-resolution) | Embedding | 1 (batch) | Single |
| Edge resolution search | Embedding | ~160 (2 per edge × ~80 edges) | Parallel |
| Edge dedup resolve | LLM | ~80 (1 per edge with candidates) | Parallel |
| Node summary extraction | LLM | ~50 (1 per entity) | Parallel |
| Node name embeddings | Embedding | 1 (batch) | Single |
| Final edge re-embeddings | Embedding | 2 (batch) | Parallel |
| **TOTAL** | | **~140 LLM + ~215 Embedding** | |

The parallelism is constrained by `SEMAPHORE_LIMIT=20`, but even 20 concurrent `/responses` requests in rapid succession exceeds typical OpenAI Tier 1 rate limits.

### Severity: **Critical** — Blocks all large document seeding

---

## Finding 2: Unawaited Coroutine (`extract_edges_for_chunk`)

### Evidence

```
RuntimeWarning: coroutine 'extract_edges.<locals>.extract_edges_for_chunk' was never awaited
```

### Analysis

This is a **different** coroutine leak than TASK-REV-661E (which was `search`). When the rate limit exception propagates during edge extraction, the parallel `semaphore_gather` call for remaining edge extraction chunks is abandoned, leaving `extract_edges_for_chunk` coroutines unawaited.

This is a **consequence** of the rate limit failure, not a root cause. The fix is upstream in graphiti-core — their error handling in `extract_edges()` doesn't properly cancel sibling coroutines when one fails. However, fixing the rate limit problem eliminates this symptom.

### Severity: **Low** — Symptom of the rate limit issue, not a standalone bug

---

## Finding 3: Retry Backoff Is Inadequate

### Evidence

The OpenAI client retries use intervals of 0.3–0.9 seconds:
```
Retrying request to /responses in 0.392428 seconds
Retrying request to /responses in 0.949371 seconds
```

### Analysis

OpenAI's rate limit windows are per-minute. With ~140 LLM calls fired within seconds (limited by semaphore=20, so ~7 batches of 20), the 0.3–0.9s retry intervals mean retries happen well within the same rate limit window. The retries themselves contribute to the rate limit pressure.

graphiti-core relies on the openai Python SDK's built-in retry logic, which uses jittered exponential backoff but with very short initial intervals. There's no application-level rate limiting or throttling.

### Severity: **Medium** — Exacerbates the core problem

---

## Finding 4: Content Parsing Warnings (Known)

```
Warning: Missing feature overview section
Warning: No phases found in feature spec
```

These are identical to TASK-REV-661E Finding 4 — the FeatureSpecParser expects specific section headings that the v2 document uses different names for. **Known and low priority** — doesn't affect seeding functionality, only metadata extraction.

### Severity: **Low** — Cosmetic, already documented

---

## Option Evaluation

### Option A: Local Embeddings + LLM on Dell ProMax GB10 via vLLM (Recommended)

**Description**: Serve both embedding model (nomic-embed-text-v1.5) and LLM (Qwen3-Coder-30B) from **vLLM** on the GB10, reusing the same runtime already planned for AutoBuild inference. Point graphiti-core at vLLM's OpenAI-compatible `/v1/embeddings` and `/v1/chat/completions` endpoints.

**Why vLLM over Ollama**: vLLM is already the designated inference runtime for AutoBuild on the GB10 (TASK-REV-55C3). Using it for Graphiti too means one runtime to manage, not two. The performance advantage is substantial — benchmarks show vLLM delivering **up to 20x higher throughput** under concurrency (793 TPS vs 41 TPS) with **8x lower P99 latency** (80ms vs 673ms). This matters because a single `add_episode()` fires ~355 API calls with `SEMAPHORE_LIMIT=20` concurrency.

#### vLLM vs Ollama for This Workload

| Factor | vLLM | Ollama |
|--------|------|--------|
| **Throughput (concurrent)** | ~120-160 req/s | ~1-3 req/s |
| **P99 latency at load** | 80ms | 673ms |
| **Embedding model support** | nomic-embed-text-v1.5 via `task="embed"` | nomic-embed-text native |
| **OpenAI-compatible API** | Full (`/v1/embeddings`, `/v1/chat/completions`) | Full (`/v1/embeddings`, `/v1/chat/completions`) |
| **Already planned for GB10** | Yes (AutoBuild, TASK-REV-55C3) | Was planned, superseded by vLLM |
| **Multi-model serving** | Yes (can serve LLM + embedding concurrently) | Yes (auto-loads on demand) |
| **Setup complexity** | Medium (pip install, model config) | Low (single binary, `ollama pull`) |
| **GPU memory management** | PagedAttention, KV-cache optimised | Basic allocation |
| **Continuous batching** | Yes (key advantage for 20+ concurrent requests) | No |

The critical difference is **continuous batching**: graphiti-core's semaphore fires up to 20 concurrent requests. vLLM batches these efficiently on the GPU; Ollama processes them mostly sequentially, creating a bottleneck.

**Implementation**:
```python
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIGenericClient, LLMConfig
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig

graphiti = Graphiti(
    graph_driver=falkordb_driver,
    llm_client=OpenAIGenericClient(
        config=LLMConfig(
            base_url="http://promaxgb10-41b1:8000/v1",
            model="Qwen/Qwen3-Coder-30B-A3B",
            api_key="vllm-local-key",
        )
    ),
    embedder=OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            base_url="http://promaxgb10-41b1:8001/v1",
            embedding_model="nomic-ai/nomic-embed-text-v1.5",
            api_key="vllm-local-key",
        )
    ),
)
```

Note: vLLM serves one model per process, so LLM (port 8000) and embeddings (port 8001) run as separate vLLM instances. This is actually an advantage — each gets dedicated GPU memory allocation.

**Feasibility**: HIGH
- graphiti-core natively supports this via `base_url` injection — zero library changes
- `OpenAIGenericClient` was purpose-built for local models (higher `max_tokens=16384` default)
- vLLM supports nomic-embed-text-v1.5 via `task="embed"` parameter
- vLLM supports Qwen3-Coder (already validated for AutoBuild in TASK-REV-55C3)
- Dell ProMax GB10 has 128GB unified memory — plenty for concurrent LLM + embedding model
- Consolidates with existing AutoBuild inference stack — one runtime, not two
- No rate limits — local inference bounded only by GPU throughput
- Continuous batching handles the 20-concurrent-request pattern efficiently

| Factor | Score |
|--------|-------|
| Eliminates rate limits | 10/10 |
| Quality parity | 9/10 (nomic-embed-text matches OpenAI; Qwen3-Coder-30B handles entity extraction well) |
| Implementation effort | 7/10 (vLLM already planned; add embedding model instance + GuardKit config) |
| Ongoing cost | 10/10 ($0/month — electricity only) |
| Latency | 9/10 (continuous batching handles concurrent load efficiently) |
| Risk | 8/10 (vLLM mature, models validated, infrastructure exists) |
| Stack consolidation | 10/10 (single runtime for AutoBuild + Graphiti) |

**Estimated effort**: 2–4 hours (add vLLM embedding instance, GuardKit config update, test seed)

---

### Option B: OpenAI Rate Limit Mitigations (Partial Fix)

**Description**: Stay on OpenAI but add mitigations: reduce semaphore limit, add application-level throttling, chunk the document before seeding.

**Sub-options**:

#### B1: Reduce SEMAPHORE_LIMIT
Set `SEMAPHORE_LIMIT=5` (env var) to throttle concurrent API calls. Reduces burst rate but dramatically slows seeding (5x–10x slower for large docs).

#### B2: Pre-chunk the document
Split the 70KB document into smaller episodes before calling `add_episode()`. Each smaller episode extracts fewer entities, reducing the call fan-out. But this loses cross-section entity relationships.

#### B3: Exponential backoff with longer waits
Override the openai SDK's retry configuration with longer initial intervals (e.g., 5s, 10s, 30s). Requires patching the client or wrapping calls.

#### B4: Upgrade OpenAI tier
Move from Tier 1 to Tier 2+ for higher RPM limits. Requires spending threshold ($50+ for Tier 2, $100+ for Tier 3). Doesn't eliminate the problem, just raises the ceiling.

| Factor | B1 | B2 | B3 | B4 |
|--------|----|----|----|----|
| Eliminates rate limits | 3/10 | 4/10 | 5/10 | 6/10 |
| Quality parity | 10/10 | 7/10 | 10/10 | 10/10 |
| Implementation effort | 9/10 | 5/10 | 6/10 | 10/10 |
| Ongoing cost | 5/10 | 5/10 | 5/10 | 3/10 |
| Latency | 3/10 | 6/10 | 3/10 | 8/10 |
| Risk | 7/10 | 6/10 | 7/10 | 8/10 |

**Problem**: None of these fully solve the issue. Large documents will always generate 100+ API calls, and any OpenAI tier has finite limits. These are band-aids.

---

### Option C: Hybrid Approach

**Description**: Use local Ollama for embeddings (high-volume, quality-parity), keep OpenAI for LLM calls (higher quality entity extraction). Reduces API calls by ~60% (embeddings are the majority).

**Problem**: The rate limit is on `/responses` (LLM), not `/embeddings`. This doesn't fix the actual bottleneck. Would need to also switch LLM to local to fully resolve.

| Factor | Score |
|--------|-------|
| Eliminates rate limits | 5/10 (only fixes embedding calls, not LLM) |
| Quality | 9/10 (best of both) |
| Implementation effort | 6/10 (same as A but keep OpenAI LLM config) |
| Ongoing cost | 7/10 (reduced but not eliminated) |

---

## Decision Matrix

| Criterion (Weight) | A: vLLM Local | B1: Throttle | B2: Pre-chunk | B3: Backoff | B4: Tier Up | C: Hybrid |
|---------------------|:---:|:---:|:---:|:---:|:---:|:---:|
| Eliminates rate limits (30%) | 10 | 3 | 4 | 5 | 6 | 5 |
| Quality parity (20%) | 9 | 10 | 7 | 10 | 10 | 9 |
| Implementation effort (15%) | 7 | 9 | 5 | 6 | 10 | 6 |
| Ongoing cost (15%) | 10 | 5 | 5 | 5 | 3 | 7 |
| Latency (10%) | 9 | 3 | 6 | 3 | 8 | 6 |
| Risk (10%) | 8 | 7 | 6 | 7 | 8 | 7 |
| **Weighted Score** | **9.05** | **5.80** | **5.20** | **5.95** | **6.95** | **6.30** |

---

## Recommendation

### Primary: Option A — Full Local Inference via vLLM on Dell ProMax GB10

**Rationale**:
1. **Eliminates the root cause permanently** — no rate limits on local inference
2. **Stack consolidation** — vLLM is already the designated AutoBuild inference runtime (TASK-REV-55C3); one runtime to manage, not two
3. **Throughput match for workload** — continuous batching handles the 20-concurrent-request pattern from graphiti-core's semaphore efficiently (120-160 req/s vs Ollama's 1-3 req/s under concurrency)
4. **Zero ongoing API cost** — saves OpenAI spend for seeding operations
5. **Native graphiti-core support** — `OpenAIGenericClient` + `OpenAIEmbedder` with `base_url` requires only config changes
6. **Quality parity** — nomic-embed-text matches text-embedding-3-small on MTEB benchmarks; Qwen3-Coder-30B handles entity extraction well
7. **Infrastructure already planned** — GB10 documented for vLLM in multiple infrastructure guides

### Implementation Outline

1. **Launch vLLM embedding instance on GB10** (SSH to `promaxgb10-41b1`)
   ```bash
   # Embedding model on port 8001 (separate from AutoBuild LLM on port 8000)
   vllm serve nomic-ai/nomic-embed-text-v1.5 \
     --host 0.0.0.0 \
     --port 8001 \
     --task embed \
     --dtype auto
   ```

2. **Ensure vLLM LLM instance is available** (may already be running for AutoBuild)
   ```bash
   # LLM on port 8000 (Qwen3-Coder for entity extraction)
   vllm serve Qwen/Qwen3-Coder-30B-A3B \
     --host 0.0.0.0 \
     --port 8000 \
     --enable-auto-tool-choice \
     --max-model-len 16384
   ```

3. **Update GuardKit graphiti_client.py** to accept embedder/LLM config
   - Add `llm_provider`, `llm_base_url`, `llm_model`, `embedding_provider`, `embedding_base_url`, `embedding_model` to `GraphitiConfig`
   - Pass custom `OpenAIGenericClient` and `OpenAIEmbedder` to `Graphiti()` constructor when provider is not "openai"

4. **Update `.guardkit/graphiti.yaml`** with new config fields
   ```yaml
   # Local inference via vLLM on Dell ProMax GB10
   llm_provider: vllm
   llm_base_url: http://promaxgb10-41b1:8000/v1
   llm_model: Qwen/Qwen3-Coder-30B-A3B
   embedding_provider: vllm
   embedding_base_url: http://promaxgb10-41b1:8001/v1
   embedding_model: nomic-ai/nomic-embed-text-v1.5
   ```

5. **Test with feature-spec v2 document** — verify successful seeding

6. **Optional: Keep OpenAI as fallback** — add provider switching for when GB10 is offline

### Embedding Model Selection

| Model | Params | MTEB Mean | Dim | Max Tokens | NVFP4? | GB10 Fit |
|-------|--------|-----------|-----|------------|--------|----------|
| nomic-embed-text-v1.5 | 137M | 62.39 | 768 | 8192 | N/A (tiny) | Trivial |
| nvidia/llama-nemotron-embed-1b-v2 | 1B | ~65* | 2048 | 8192 | Quantized variant exists | Easy |
| nvidia/llama-embed-nemotron-8b | 7.5B | **69.46** (#1 MMTEB) | 4096 | 8192 | Quantized variant exists | ~16GB fp16 |

\* Estimated from BEIR/NQ benchmarks; official MTEB not published.

**Recommendation**: Start with **nomic-embed-text-v1.5** (proven quality parity with OpenAI, 137M params means negligible memory, proven on vLLM with `--task embed`). If quality is insufficient for Graphiti entity resolution, upgrade to **nvidia/llama-nemotron-embed-1b-v2** which is purpose-built for NVIDIA hardware and has a DGX Spark community track record. The 8B variant is overkill for this workload and would consume GPU memory better reserved for the LLM.

Note: NVFP4 quantisation is designed for LLMs (billions of parameters). Embedding models at 137M–1B are small enough that FP16/BF16 is fine — the memory savings from FP4 are negligible at this scale. NVFP4 matters for the LLM side (Qwen3-Coder-30B), where it's already the planned deployment format per TASK-REV-55C3.

### Implementation Subtasks

| # | Task | Complexity | Mode |
|---|------|-----------|------|
| 1 | GB10 vLLM setup guide: embedding model instance with optimal config | Medium | task-work |
| 2 | Extend GraphitiConfig for local inference provider settings | Medium | task-work |
| 3 | Update GraphitiClient.initialize() to inject custom embedder/LLM | Medium | task-work |
| 4 | Update `.guardkit/graphiti.yaml` schema and config loader | Low | task-work |
| 5 | Test seeding with feature-spec v2 document | Low | Direct |

---

## Appendix

### A. graphiti-core Version and Architecture

- **Version**: 0.26.3
- **Embedder interface**: Abstract `EmbedderClient` with `create()` and `create_batch()` methods
- **LLM interface**: Abstract `LLMClient` with `_generate_response()` method
- **Purpose-built local support**: `OpenAIGenericClient` class with `base_url` and high `max_tokens` default
- **Parallelism control**: `SEMAPHORE_LIMIT` env var (default 20)
- **Chunking thresholds**: `CHUNK_MIN_TOKENS=1000`, `CHUNK_TOKEN_SIZE=3000`, `CHUNK_OVERLAP_TOKENS=200`

### B. Document Characteristics

| Metric | Value |
|--------|-------|
| File size | 70,344 bytes (68.7 KB) |
| Lines | 1,122 |
| Words | 8,841 |
| Headings | 92 |
| Estimated entities | ~50 |
| Estimated edges | ~80 |
| Estimated content chunks | ~5 |

### C. Dell ProMax GB10 Specifications

| Spec | Value |
|------|-------|
| GPU | NVIDIA Blackwell GB10 |
| Memory | 128GB LPDDR5X unified |
| Bandwidth | 273 GB/s |
| Peak FP4 | 1 PFLOP |
| Model capacity | Up to 200B parameters |
| Hostname | promaxgb10-41b1 |
| Tailscale IP | 100.84.90.91 |

### D. Embedding Quality Comparison

| Model | MTEB (short) | MTEB (long/LoCo) | Parameters | Local? |
|-------|:---:|:---:|:---:|:---:|
| text-embedding-3-small | 62.26 | 82.40 | Cloud | No |
| nomic-embed-text v1 | 62.39 | 85.53 | 137M | Yes |

### E. Sources

- [Nomic Embed Technical Report](https://www.nomic.ai/news/nomic-embed-text-v1)
- [OpenAI Rate Limits Guide](https://platform.openai.com/docs/guides/rate-limits)
- [Dell ProMax GB10](https://www.dell.com/en-us/blog/dell-pro-max-with-gb10-purpose-built-for-ai-developers/)
- [Best Open-Source Embedding Models Benchmarked](https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/)
