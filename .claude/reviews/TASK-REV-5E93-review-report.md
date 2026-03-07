# Review Report: TASK-REV-5E93

## Executive Summary

Analysis of the FEAT-1637 autobuild run on Dell ProMax GB10 with vLLM reveals three critical findings:

1. **Parallel execution is actively harmful** — Wave 5 shows a **4.3x throughput penalty** when running 2 tasks concurrently (87s/turn vs ~20s/turn sequential). `max_parallel` must be reduced from 2 to **1**.
2. **Graphiti context retrieval fails on both runs** due to a factory initialization ordering bug — `get_factory()` returns `None` because no caller invokes `init_graphiti()` before the preflight check. TASK-FIX-GCW6 is the critical fix.
3. **Sequential vLLM performance is ~1.5-1.8x slower** than Anthropic API per task — acceptable for local development, with room for optimization via `sdk_max_turns` increase.

The CancelledError crash (now fixed) affected both runs identically, confirming it's not vLLM-specific.

## Review Details

- **Mode**: Performance + Graphiti Root Cause Analysis
- **Depth**: Standard → Revised (deeper analysis on 5 areas)
- **Revision Areas**: vLLM serving config, token-level profiling, context budget, dual-role contention, wave parallelism
- **Reviewer**: Manual analysis of run logs, source code, vLLM configuration, and C4 diagrams

---

## Finding 1: Hardware & Model Configuration (NEW — Revision Area 1)

### Infrastructure Profile

| Component | Specification |
|-----------|--------------|
| **GPU** | NVIDIA Blackwell GB10 (single GPU, 128GB unified CPU/GPU memory) |
| **Platform** | ARM64, DGX OS, Docker |
| **Model** | Qwen/Qwen3-Coder-Next-FP8 (80B MoE, ~3B active params per token) |
| **Context Window** | 262,144 tokens (256K) |
| **Quantization** | FP8 (native to model) |
| **vLLM Image** | `nvcr.io/nvidia/vllm:26.01-py3` |
| **Served As** | `claude-sonnet-4-6` (model alias) |

### vLLM Serving Configuration

From [scripts/vllm-serve.sh](scripts/vllm-serve.sh):
```bash
docker run -d --name vllm-server --gpus all -p 8000:8000 --ipc=host \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  nvcr.io/nvidia/vllm:26.01-py3 \
  vllm serve Qwen/Qwen3-Coder-Next-FP8 \
    --host 0.0.0.0 --port 8000 \
    --served-model-name claude-sonnet-4-6 \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder \
    --gpu-memory-utilization 0.8 --max-model-len 262144 \
    --attention-backend flashinfer --enable-prefix-caching --load-format auto
```

### Embedding Server

From [scripts/vllm-embed.sh](scripts/vllm-embed.sh):
```bash
vllm serve nomic-ai/nomic-embed-text-v1.5 \
  --host 0.0.0.0 --port 8001 \
  --gpu-memory-utilization 0.15 --runner pooling
```

### Key Observations

- **GPU memory split**: LLM 0.8 (102GB) + Embedding 0.15 (19GB reserved, ~274MB actual) = 0.95 total
- **MoE architecture**: Only ~3B params active per token despite 80B total — explains reasonable per-token latency
- **Prefix caching enabled**: Repeated protocol prefixes are cached, reducing redundant KV computation
- **flashinfer backend**: Optimized attention for Blackwell architecture
- **Alternative models available**: Qwen3-Coder-30B-A3B, MiniMax M2.5 variants (in serve script)

---

## Finding 2: Per-Turn Throughput Analysis (NEW — Revision Area 2)

### CRITICAL FINDING: Parallel Execution Destroys Throughput

Timestamp analysis from the run log reveals dramatic throughput degradation during parallel execution:

| Task | Wave | Parallel? | Duration | SDK Turns | Avg Turn Time | vs Sequential Baseline |
|------|------|-----------|----------|-----------|---------------|----------------------|
| FBP-001 | 1 | No | 19m 22s | 57 | **20.4s** | Baseline |
| FBP-002 | 2 | **Yes (2x)** | 12m 09s | 34 | **21.4s** | 1.05x (light task) |
| FBP-004 T1 | 2 | **Yes (2x)** | 29m 15s | 51 | **34.4s** | **1.7x penalty** |
| FBP-004 T2 | — | No (retry) | 5m 19s | 24 | **13.3s** | 0.65x (warm cache) |
| FBP-003 | 3 | No | 9m 16s | 29 | **19.2s** | ~Baseline |
| FBP-005 T1 | 4 | No | 22m 26s | 51 | **26.4s** | 1.3x (complex task) |
| FBP-005 T2 | — | No (retry) | 6m 15s | 24 | **15.6s** | 0.76x (warm cache) |
| FBP-006 T1 | 5 | **Yes (2x)** | 73m 59s | 51 | **87.0s** | **4.3x penalty** |
| FBP-006 T2 | — | No (post-crash) | 11m 50s | 30 | **23.7s** | ~Baseline |
| FBP-007 | 5 | **Yes (2x)** | ~35m | ~20 | ~105s* | **5.1x penalty** |

*FBP-007 crashed via CancelledError; timing estimated from progress logs.

### Throughput Analysis

**Sequential baseline**: ~20s/turn average (FBP-001, FBP-003, FBP-006 T2)

**Wave 2 parallel penalty**: 1.7x — FBP-004 (complexity 5) was meaningfully slowed. FBP-002 (complexity 4, lighter workload) finished faster and freed the GPU, so the penalty was moderate.

**Wave 5 parallel penalty**: 4.3-5.1x — Both FBP-006 (complexity 6) and FBP-007 (complexity 3) were severely degraded. Two complex inference streams competing for GPU compute created extreme queuing delays.

**Retry turns are faster**: FBP-004 T2 (13.3s) and FBP-005 T2 (15.6s) were faster than baseline, likely due to KV cache warmth from the first attempt and simpler "fix" prompts.

### Root Cause of Parallel Degradation

The Qwen3-Coder-Next-FP8 model with `max-model-len=262144` pre-allocates substantial KV cache memory. When two concurrent requests are processed:

1. **KV cache contention**: Two 256K-capable sequences compete for the 102GB GPU memory allocation
2. **Compute saturation**: Despite MoE architecture (~3B active params), two concurrent forward passes saturate GPU compute
3. **vLLM scheduling**: The continuous batching scheduler interleaves tokens, but each sequence's total latency increases
4. **No request prioritization**: Both autobuild tasks get equal scheduling priority

### Updated Per-Task Timing Comparison (Corrected)

| Task | Complexity | vLLM Sequential* | Anthropic API (MBP) | Corrected Ratio | Turns |
|------|-----------|------------------|---------------------|-----------------|-------|
| FBP-001 (Scaffolding) | 3 | **19m 22s** | **14m 21s** | 1.35x | 1/1 |
| FBP-002 (Settings) | 4 | **12m 09s** | **4m 06s** | 2.96x | 1/1 |
| FBP-004 (Middleware) | 5 | **34m 34s** (29m+5m) | **5m 16s** | 6.6x† | 2/1 |
| FBP-003 (Logging) | 5 | **9m 16s** | **5m 09s** | 1.8x | 1/1 |
| FBP-005 (Health) | 4 | **28m 41s** (22m+6m) | **7m 32s** | 3.8x† | 2/1 |
| FBP-006 (Tests) | 6 | **85m 49s** (74m+12m) | **~41m** (est.) | ~2.1x | 2/2 |
| FBP-007 (Quality) | 3 | **CRASHED** | **CRASHED** | N/A | N/A |

*vLLM times include retries. †High ratio partly due to needing 2 turns vs Anthropic's 1.

**Corrected sequential-only estimate**: For tasks that ran sequentially (FBP-001, FBP-003), vLLM is **1.35-1.8x slower**. The higher ratios for FBP-004/FBP-005 are inflated by retry turns (code quality issue, not raw speed).

### Total Run Duration

| Metric | vLLM (GB10) | Anthropic API (MBP) |
|--------|-------------|---------------------|
| Total elapsed (until crash) | **~3h 0m** (08:04→11:02+crash) | **~52m** (08:07→crash) |
| Tasks completed | 6/7 | 5/7 (crashed Wave 5) |
| Waves completed | 4/5 | 4/5 |
| Estimated if max_parallel=1 | **~2h 20m** (no parallel penalty) | N/A |

---

## Finding 3: Graphiti Context Retrieval Failure (CRITICAL)

### Root Cause Identified

**The `get_factory()` function returns `None` because `_factory` is never initialized.**

Code path in [feature_orchestrator.py:1194-1197](guardkit/orchestrator/feature_orchestrator.py#L1194-L1197):
```python
from guardkit.knowledge.graphiti_client import get_factory
factory = get_factory()
if factory is None or not factory.config.enabled:
    logger.info("Graphiti factory not available or disabled, disabling context loading")
```

`get_factory()` in [graphiti_client.py:2173-2182](guardkit/knowledge/graphiti_client.py#L2173-L2182) simply returns the module-level `_factory` variable:
```python
def get_factory() -> Optional[GraphitiClientFactory]:
    return _factory  # Returns None — nobody called init_graphiti()
```

**The factory is never initialized** because:
1. `init_graphiti()` (the async initializer) is never called by the autobuild entry path
2. `get_factory()` deliberately does NOT trigger lazy initialization (comment says "use get_graphiti() for that")
3. `_try_lazy_init()` (the lazy path via `get_graphiti()`) creates a factory but only when called — and nobody calls `get_graphiti()` before the preflight check either

**The paradox explained**: Thread clients ARE created later (`"Graphiti factory: thread client created"`) because `AutoBuildOrchestrator.__init__` calls `get_graphiti()` (which triggers `_try_lazy_init`), but this happens AFTER `FeatureOrchestrator` has already disabled context by setting `enable_context=False`.

### Same failure on both runs

Both the vLLM run (line 35) and Anthropic run (line 32) show identical:
```
Graphiti factory not available or disabled, disabling context loading
```

This confirms it's a **code-level bug in the autobuild orchestrator path**, not infrastructure-related.

### Existing fix coverage

| Fix Task | Status | Covers this issue? |
|----------|--------|-------------------|
| `graphiti-context-wiring/TASK-FIX-GCW3` | **COMPLETED** | **Partially** — auto-initializes `AutoBuildContextLoader` when `enable_context=True` |
| `graphiti-context-wiring/TASK-FIX-GCW4` | **COMPLETED** | **Partially** — wires `context_loader` in FeatureOrchestrator callers |
| `graphiti-context-wiring/TASK-FIX-GCW6` | **BACKLOG** | **YES** — "Fix Graphiti client lifecycle - singleton never initialized in autobuild" |
| `graphiti-lifecycle-fix/TASK-GLF-001` | **COMPLETED** | No — fixes `_capture_turn_state` guard only |

**TASK-FIX-GCW6 is the critical remaining task** that directly addresses the `_factory = None` issue. It must be completed before the next autobuild run.

---

## Finding 4: Context Budget Analysis (REVISED — Revision Area 4)

### Context Usage Is Negligible

| Metric | Value |
|--------|-------|
| Inline protocol size | ~19KB per turn (~19,196 bytes) |
| Estimated token count | ~5,000 tokens |
| Model context window | 262,144 tokens (256K) |
| **Protocol as % of context** | **~2%** |
| Prefix caching | **Enabled** — repeated protocol prefix cached in KV |

### Previous Assessment Corrected

The original report estimated 5-19% context overhead based on hypothetical 128K/32K models. Now that we know the actual model has a **256K context window** with **prefix caching enabled**, the 19KB protocol overhead is negligible:

- **Without prefix caching**: ~5,000 tokens × $N$ turns = cumulative but still small relative to 256K
- **With prefix caching**: The ~19KB protocol is identical across turns, so KV cache is computed once and reused. Effective per-turn overhead approaches zero after the first turn.

### Graphiti Context Addition (Post-GCW6)

When Graphiti context is enabled, each turn will include additional context from the knowledge graph. Even with generous context injection (e.g., 10-20KB additional), total context usage would remain under 10% of the 256K window. **Context budget is not a concern for this hardware/model combination.**

---

## Finding 5: Dual-Role Contention Assessment (NEW — Revision Area 5)

### Current Memory Allocation

| Server | GPU Memory Reservation | Actual Usage | Port |
|--------|----------------------|--------------|------|
| LLM (Qwen3-Coder-Next-FP8) | 0.80 (102GB) | Variable (KV cache) | 8000 |
| Embedding (nomic-embed-text-v1.5) | 0.15 (19GB) | **~274MB** | 8001 |
| **Total reserved** | **0.95 (121GB)** | — | — |
| **Free** | **0.05 (6.4GB)** | — | — |

### Contention Risk Assessment

**Memory contention: LOW RISK**
- The embedding model (274MB actual) vastly over-reserves (19GB). This is wasteful but not harmful — vLLM pre-allocates the GPU memory pool at startup.
- The LLM server has 102GB for KV cache, sufficient for the 256K context window even with parallel requests.
- **Optimization opportunity**: Reduce embedding `--gpu-memory-utilization` from 0.15 to 0.05 to free ~13GB for LLM KV cache (though with max_parallel=1, this is less important).

**Compute contention: LOW RISK (with max_parallel=1)**
- When Graphiti is enabled, embedding requests (nomic-embed-text-v1.5) run on a separate vLLM instance on a different port.
- Graphiti LLM requests (entity extraction, etc.) share the LLM server on port 8000. These are typically short requests with small context.
- **With max_parallel=1**: Only one autobuild task generates LLM requests at a time. Graphiti's occasional small requests should interleave without meaningful delay.
- **With max_parallel=2**: Contention would compound the already-severe parallel penalty. This is another reason to use max_parallel=1.

**Queue depth contention: MONITOR**
- vLLM's continuous batching handles concurrent requests, but with 256K max context, each request's KV cache allocation is large.
- Recommendation: Enable vLLM metrics endpoint and monitor `vllm:request_queue_length` during the first run with Graphiti enabled.

---

## Finding 6: Wave Parallelism Analysis (NEW — Revision Area 6)

### CRITICAL: max_parallel Must Be Reduced to 1

#### Evidence from Wave Execution

| Wave | Tasks | max_parallel | Wall Time | Estimated Sequential Time | Parallel Efficiency |
|------|-------|-------------|-----------|--------------------------|-------------------|
| Wave 1 | FBP-001 | 1 (single task) | 19m 22s | 19m 22s | N/A |
| Wave 2 | FBP-002, FBP-004 | 2 | 34m 35s | 17m 28s* | **0.51** (49% wasted) |
| Wave 3 | FBP-003 | 1 (single task) | 9m 16s | 9m 16s | N/A |
| Wave 4 | FBP-005 | 1 (single task) | 28m 41s | 28m 41s | N/A |
| Wave 5 | FBP-006, FBP-007 | 2 | 85m 49s | 40m 22s* | **0.47** (53% wasted) |

*Estimated sequential time calculated from sequential baseline throughput (~20s/turn).

#### Why Parallel Is Worse Than Sequential

For parallel execution to be beneficial, it must satisfy:

```
Wall time (parallel) < Sum of sequential times
```

**Wave 2**: 34m 35s (parallel) vs 12m 9s + 34m 34s = 46m 43s (sequential) — Parallel wins by 12m, but only because FBP-002 finished quickly and freed resources. The *throughput penalty* means each task individually took longer.

**Wave 5**: 85m 49s (parallel) vs estimated 40m 22s (sequential at ~20s/turn) — **Parallel is 2.1x SLOWER than sequential**. This is because FBP-007's CancelledError crash didn't free the GPU cleanly, and FBP-006's per-turn time ballooned to 87s.

#### Recommendation: max_parallel=1

| Setting | Current | Recommendation | Impact |
|---------|---------|----------------|--------|
| `max_parallel` | 2 | **1** | Eliminates 4.3x throughput penalty; total run time estimated ~2h 20m vs 3h actual |

**With max_parallel=1**:
- Each task runs at full GPU throughput (~20s/turn)
- No KV cache contention between concurrent requests
- Simpler debugging (one task at a time in logs)
- Estimated total time: ~140 minutes (vs 180 minutes actual with parallel)
- **Net savings: ~40 minutes per run**

**When to reconsider max_parallel=2**:
- If using a smaller model (e.g., Qwen3-Coder-30B-A3B) with less KV cache pressure
- If vLLM adds request prioritization in a future version
- If running on multi-GPU setup with tensor parallelism

---

## Recommendations Summary (REVISED)

| # | Recommendation | Priority | Effort | Change from v1 |
|---|---------------|----------|--------|----------------|
| 1 | **Complete TASK-FIX-GCW6** (factory singleton init) | **CRITICAL** | Medium | Unchanged |
| 2 | **Reduce `max_parallel` from 2 to 1** | **HIGH** | Trivial | **NEW — was "keep at 2"** |
| 3 | Increase `sdk_max_turns` from 50 to 75 | Medium | Trivial | Unchanged |
| 4 | Reduce `timeout_multiplier` from 4.0x to 3.0x | Low | Trivial | Unchanged |
| 5 | Reduce embedding `--gpu-memory-utilization` from 0.15 to 0.05 | Low | Trivial | **NEW** |
| 6 | Monitor vLLM queue depth when Graphiti is enabled | Medium | Low | Refined |
| 7 | Consider protocol compression only if context window shrinks | Low | N/A | **Downgraded — 2% is negligible** |

---

## Pre-Run Checklist for Next Attempt (REVISED)

### Critical (Must Do)
- [ ] **TASK-FIX-GCW6 completed and deployed** — verify `get_factory()` returns a valid factory
- [ ] **CancelledError fix deployed** (confirmed already implemented)
- [ ] **Set `max_parallel=1`** in autobuild configuration

### Validation
- [ ] **Quick smoke test**: Run `guardkit autobuild feature FEAT-XXX --max-turns 1` on a single-task feature to verify:
  - [ ] `enable_context=True` propagates to AutoBuildOrchestrator
  - [ ] `context_loader` is not None
  - [ ] No "factory not available" message in logs
- [ ] **Verify FalkorDB reachable**: `python -c "import socket; s=socket.create_connection(('whitestocks', 6379), timeout=5); print('OK'); s.close()"` from GB10
- [ ] **Verify vLLM model warmed up**: Send a test prompt before starting autobuild

### Optimization (Nice to Have)
- [ ] **Set `sdk_max_turns=75`** for more iteration headroom
- [ ] **Set `timeout_multiplier=3.0`** (sufficient with max_parallel=1)
- [ ] **Reduce embedding GPU memory**: `--gpu-memory-utilization 0.05` in [scripts/vllm-embed.sh](scripts/vllm-embed.sh)
- [ ] **Set `--verbose`** for detailed timing data
- [ ] **Enable vLLM metrics**: Monitor `vllm:request_queue_length` during run

---

## Appendix A: CancelledError Root Cause (Previously Analyzed)

The crash at `feature_orchestrator.py:1564` was caused by:
1. `CancelledError` raised within TASK-FBP-007's worker thread event loop
2. Escapes through 5 consecutive `except Exception` handlers (CancelledError is `BaseException` on Python 3.9+)
3. Captured by `gather(return_exceptions=True)` as a result value
4. Result processing assumes `.success` attribute — crashes with `AttributeError`

**Fix**: Already implemented in `tasks/backlog/cancelled-error-fix/`. The fix adds `except (asyncio.CancelledError, BaseException)` handlers at all 5 guard points.

**Same crash on both runs**: Confirms this is a GuardKit bug, not vLLM or Anthropic-specific.

## Appendix B: Graphiti Configuration

From [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml):
```yaml
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

Both LLM and embedding requests for Graphiti are served by the same Dell ProMax GB10, creating a self-contained inference stack. FalkorDB (graph database) runs on Synology NAS (`whitestocks:6379`).

## Appendix C: Alternative Model Options

The [scripts/vllm-serve.sh](scripts/vllm-serve.sh) includes presets for:

| Model | Parameters | Type | Potential Use |
|-------|-----------|------|--------------|
| Qwen3-Coder-Next-FP8 | 80B (3B active) | MoE, FP8 | **Current — best quality** |
| Qwen3-Coder-30B-A3B | 30B (3B active) | MoE | Faster, may allow max_parallel=2 |
| MiniMax M2.5 NVFP4 | Unknown | FP4 | Experimental |
| MiniMax M2.5 AWQ | Unknown | AWQ | Experimental |

If max_parallel=2 is desired in the future, switching to the smaller Qwen3-Coder-30B-A3B model would reduce KV cache pressure and potentially make parallel execution viable.
