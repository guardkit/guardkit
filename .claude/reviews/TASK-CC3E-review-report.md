# Review Report: TASK-CC3E

## Executive Summary

Three distinct infrastructure issues prevent the vLLM embedding + FalkorDB knowledge pipeline from working on the Dell Pro Max GB10 / DGX Spark. The task diagnosis is **accurate and well-evidenced**. All three root causes are correctly identified, and the proposed fixes are sound. Two fixes are trivial (< 5 min each), one is a config change, and the pre-flight GPU check is a small enhancement.

**Architecture Score: 78/100** — The existing codebase already handles timeouts and graceful degradation well. The issues are configuration/scripting gaps, not architectural defects.

## Review Details

- **Mode**: Architectural + Infrastructure Review
- **Depth**: Standard
- **Task Complexity**: 5/10
- **Files Analyzed**: 4 source files, 2 evidence logs, 1 YAML config

## Findings

### Finding 1: GPU Memory Over-Allocation (CRITICAL)

**File**: `scripts/vllm-embed.sh:19,27,94`
**Evidence**: `run_embedding_1.md` — `ValueError: Free memory on device (4.04/119.63 GiB) ... desired (0.15, 17.94 GiB)`

The default `VLLM_EMBED_GPU_UTIL=0.15` requests 15% of 119.63 GiB = **17.94 GiB** for a model that only needs **~0.26 GiB** (model load: 0.2551 GiB per `docker_logs_1.md:68`). The main LLM server on port 8000 leaves only ~4 GiB free.

**Impact**: Embedding server cannot start at all when the LLM server is running.

**Recommendation**: Set `VLLM_EMBED_GPU_UTIL=0.03` (= ~3.6 GiB, 14x headroom over the 0.26 GiB actual model size). This leaves room for KV cache and CUDA graph captures while staying well within the ~4 GiB available.

**Risk**: vLLM's `gpu_memory_utilization` sets a floor, not a ceiling. Even 0.03 may fail if free memory drops below 3.6 GiB. A value of 0.02 (~2.4 GiB) would be safer but may limit batch throughput.

### Finding 2: Model Name Mismatch (HIGH)

**File**: `scripts/vllm-embed.sh:107`
**Evidence**: `docker_logs_1.md:125` — `POST /v1/embeddings HTTP/1.1" 404 Not Found`

The test curl command uses `$(basename "$MODEL")` which produces `nomic-embed-text-v1.5`, but vLLM registers the model as `nomic-ai/nomic-embed-text-v1.5` (the full HuggingFace path). Confirmed by the `served_model_name` in the engine config log.

**Impact**: Test command fails with 404. Users will think the server is broken even when it's running correctly.

**Two fix approaches**:
- **Option A**: Fix test curl to use `$MODEL` (full name) — simplest, no server-side change
- **Option B** (preferred): Add `--served-model-name "$(basename "$MODEL")"` to vllm serve — allows both full and short names, matches OpenAI convention

**Recommendation**: Option B. It makes the API more user-friendly and matches how most vLLM deployments work. The `--served-model-name` flag creates an alias; the full path still works.

### Finding 3: FalkorDB Connection Misconfiguration (MEDIUM — Already Fixed)

**File**: `guardkit/knowledge/config.py:80,92` (defaults), `.guardkit/graphiti.yaml:31-32`
**Evidence**: Task description references `clear_1.md`, `clear_2.md` — `Connect call failed ('127.0.0.1', 7687)`

The task describes FalkorDB connecting to localhost:7687 instead of the Synology NAS via Tailscale.

**Current state**: The `.guardkit/graphiti.yaml` **already has the correct configuration**:
```yaml
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
```

The error likely occurred when `graphiti.yaml` was missing or before it was configured. This issue appears to be **already resolved** in the current config.

**Remaining concern**: The default values in `config.py` still default to `neo4j` store with `bolt://localhost:7687`. If the YAML file is missing, the system falls back to these defaults and will fail. This is by design (graceful degradation), but the error message could be more specific about FalkorDB connectivity.

### Finding 4: No Pre-Flight GPU Check (LOW — Enhancement)

**File**: `scripts/vllm-embed.sh` (missing functionality)

The script launches the Docker container without checking available GPU memory first. The failure happens inside the container after startup, requiring `docker logs` to diagnose.

**Impact**: Poor developer experience. The user waits for container startup only to find the error buried in logs.

**Recommendation**: Add a pre-flight check using `nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits` before launching Docker. Compare free memory against the requested utilization and warn/fail early.

### Finding 5: Embedding Model Name in graphiti.yaml (MEDIUM)

**File**: `.guardkit/graphiti.yaml:50`

The config specifies `embedding_model: text-embedding-3-small` which is an OpenAI model name, but the embedding provider is set to `vllm`. When the vLLM embedding server registers the model as `nomic-ai/nomic-embed-text-v1.5`, the client may use the wrong model name in API calls.

**Impact**: Depends on how graphiti-core passes the model name. If it uses the configured `embedding_model` in API calls to the vLLM endpoint, requests will fail with a model-not-found error (same class of issue as Finding 2).

**Recommendation**: Update `embedding_model` in `graphiti.yaml` to match the vLLM served model name. If Fix 2 Option B is applied (with `--served-model-name`), use the short name. Otherwise use the full HuggingFace path.

## Recommendations Summary

| # | Fix | Priority | Effort | Risk |
|---|-----|----------|--------|------|
| 1 | Change `VLLM_EMBED_GPU_UTIL` default from 0.15 to 0.03 | CRITICAL | 1 line | Low |
| 2 | Add `--served-model-name` to vllm serve command | HIGH | 2 lines | Low |
| 3 | Fix test curl to use `$MODEL` instead of `$(basename "$MODEL")` | HIGH | 1 line | None |
| 4 | Update `embedding_model` in graphiti.yaml to match vLLM model | MEDIUM | 1 line | Low |
| 5 | Add pre-flight GPU memory check to vllm-embed.sh | LOW | ~15 lines | None |
| 6 | Verify FalkorDB config is working (already configured) | LOW | Manual test | None |

## Architecture Assessment

| Principle | Score | Notes |
|-----------|-------|-------|
| Configuration (SRP) | 8/10 | Clean separation: YAML config, env overrides, Python defaults |
| Resilience (DRY) | 9/10 | Graceful degradation, circuit breaker, timeout handling all present |
| Error Handling | 7/10 | Client-side excellent; script-side lacking (no pre-flight checks) |
| Documentation | 8/10 | Good inline docs in YAML, good docstrings in Python |
| Testability | 7/10 | Python code well-tested; bash script untestable |
| Overall | **78/100** | Solid infrastructure code with minor scripting gaps |

## Appendix

### GPU Memory Budget

```
Total GPU VRAM:     119.63 GiB
LLM Server (8000):  ~115.59 GiB (estimated from 119.63 - 4.04 free)
Available:           ~4.04 GiB

Embedding model:     0.26 GiB (actual load from docker_logs_1.md)
CUDA graphs:         0.01 GiB (from docker_logs_1.md)
KV cache overhead:   ~0.5-1.0 GiB (estimate for 2048 max_seq_len)

gpu_memory_utilization=0.03 → 3.59 GiB requested
  Headroom: 3.59 - 0.27 = 3.32 GiB for KV cache + overhead ✓

gpu_memory_utilization=0.02 → 2.39 GiB requested
  Headroom: 2.39 - 0.27 = 2.12 GiB (tighter but sufficient) ✓
```

### Verified Timestamps

- First start (failed): 02-28 16:12:03 — GPU memory error at 16:12:13
- Second start (success): 02-28 16:40:45 — Model loaded at 16:41:06, server ready at 16:41:15
- Model load: 0.2551 GiB, 11.14 seconds
- torch.compile: 7.05 seconds
- Total init (engine core): 8.35 seconds
