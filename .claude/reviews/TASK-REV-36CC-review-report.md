# Review Report: TASK-REV-36CC

## Executive Summary

Analysis of the vLLM embedding pipeline verification output (`verify_1.md`) against the acceptance criteria defined in TASK-VEF-003. Of 5 acceptance criteria, **2 pass**, **1 fails**, and **2 were not tested**. The critical GPU memory fix works correctly, but the model name resolution fix is incomplete — only the short name works, not both names as specified. FalkorDB and full pipeline tests were not captured.

## Review Details

- **Mode**: Verification Analysis
- **Depth**: Standard
- **Task Complexity**: 2/10
- **Parent Review**: TASK-CC3E
- **Feature**: FEAT-VEF (vLLM Embedding Fixes)

## Verification Step Assessment

### Step 1: vLLM Embedding Server Starts — PASS

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Server starts successfully | **PASS** | `verify_1.md:15` — "Container started: vllm-embedding" |
| Pre-flight check shows available memory | **WARN** | GPU util displayed (`verify_1.md:9` — "GPU util: 0.03") but pre-flight `bc` calculation produced `(standard_in) 1: syntax error` twice (lines 12-13) |
| GPU util at 0.03 (not 0.15) | **PASS** | `verify_1.md:9` — "GPU util: 0.03" |

**Analysis**: The CRITICAL fix from TASK-CC3E Finding 1 (change GPU util from 0.15 to 0.03) is working correctly. The container starts alongside the LLM server without GPU memory errors.

**Issue**: The two `(standard_in) 1: syntax error` messages on lines 12-13 come from the `bc` command in the pre-flight GPU memory check (`vllm-embed.sh:83`). The line:
```bash
REQUESTED_MIB=$(echo "$TOTAL_MEM_MIB * $GPU_UTIL" | bc | cut -d. -f1)
```
likely fails because `nvidia-smi` output contains unexpected formatting (trailing whitespace, MiB suffix, or locale-specific decimal separator). The pre-flight check silently fails but does not block server startup (by design — the `if [ ... ] 2>/dev/null` on line 84 suppresses the comparison error).

### Step 2: Model Name Resolution — PARTIAL FAIL

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `curl /v1/models` returns model ID | **PASS** | `verify_1.md:30` — `"nomic-embed-text-v1.5"` (short name only) |
| Short name works | **PASS** | `verify_1.md:33-34` — 200 OK with 768-dimensional embedding vector |
| Full name works | **FAIL** | `verify_1.md:98-99` — `{"error":{"message":"The model nomic-ai/nomic-embed-text-v1.5 does not exist.","type":"NotFoundError","param":null,"code":404}}` |

**Root Cause**: The `--served-model-name` flag in vLLM **replaces** the default model name rather than adding an alias. The current script (`vllm-embed.sh:37`):
```bash
EXTRA_ARGS="--runner pooling --trust-remote-code --served-model-name $(basename "$MODEL")"
```
registers only `nomic-embed-text-v1.5`. The full HuggingFace path `nomic-ai/nomic-embed-text-v1.5` is no longer available.

**TASK-CC3E Context**: Finding 2 recommended Option B — "Add `--served-model-name` to allow both full and short names." However, the implementation only serves the short name, not both. To serve both names, the flag must be passed twice or as a comma-separated list:
```bash
--served-model-name nomic-embed-text-v1.5 --served-model-name nomic-ai/nomic-embed-text-v1.5
```

**Impact Assessment**: This is a **functional issue** but its severity depends on how Graphiti's embedding client references the model:
- If `graphiti.yaml` uses the short name `nomic-embed-text-v1.5` → pipeline works fine
- If `graphiti.yaml` uses the full name `nomic-ai/nomic-embed-text-v1.5` → pipeline will fail with 404
- The TASK-CC3E review (Finding 5) flagged that `embedding_model` in `graphiti.yaml` was set to `text-embedding-3-small` (an OpenAI name). If this was updated to the short name, the pipeline should work despite this issue.

### Step 3: FalkorDB Connection — NOT TESTED

| Criterion | Status | Evidence |
|-----------|--------|----------|
| FalkorDB reachable via Tailscale | **NOT TESTED** | No output captured in verify_1.md |
| `guardkit graphiti status` connects | **NOT TESTED** | No output captured in verify_1.md |

**Note**: The verification output ends after the model name tests. Steps 3 and 4 from TASK-VEF-003 were not executed or their output was not captured.

### Step 4: Full Pipeline — NOT TESTED

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `guardkit graphiti capture` works end-to-end | **NOT TESTED** | No output captured in verify_1.md |

## Acceptance Criteria Summary

| # | TASK-VEF-003 Acceptance Criterion | Status | Notes |
|---|-----------------------------------|--------|-------|
| 1 | vLLM embedding server starts alongside LLM server (no GPU memory error) | **PASS** | Container starts with GPU util 0.03 |
| 2 | Embedding API responds to both short and full model names | **FAIL** | Short name works; full name returns 404 |
| 3 | FalkorDB connects via Tailscale to Synology NAS | **NOT TESTED** | Not captured in verify_1.md |
| 4 | Graphiti capture works end-to-end (embedding + storage) | **NOT TESTED** | Not captured in verify_1.md |
| 5 | Pre-flight GPU check displays correct memory information | **PARTIAL** | GPU util displays correctly; `bc` calculation errors (non-blocking) |

## Findings

### Finding 1: `--served-model-name` replaces rather than aliases (HIGH)

**File**: `scripts/vllm-embed.sh:37`
**Evidence**: `verify_1.md:30` shows only `"nomic-embed-text-v1.5"` registered; `verify_1.md:99` shows full name returns 404.

The `--served-model-name` flag in vLLM replaces the default model registration. To serve both the short and full names, the flag must be specified twice.

**Fix**: Update the `EXTRA_ARGS` line in `vllm-embed.sh`:
```bash
# Current (only short name):
EXTRA_ARGS="--runner pooling --trust-remote-code --served-model-name $(basename "$MODEL")"

# Fixed (both names):
EXTRA_ARGS="--runner pooling --trust-remote-code --served-model-name $(basename "$MODEL") --served-model-name $MODEL"
```

### Finding 2: Pre-flight `bc` calculation fails silently (LOW)

**File**: `scripts/vllm-embed.sh:83`
**Evidence**: `verify_1.md:12-13` — two `(standard_in) 1: syntax error` messages.

The `bc` command fails, likely due to `nvidia-smi` output formatting. The pre-flight check degrades gracefully (script continues), but the warning about insufficient memory will never display.

**Fix**: Sanitize `nvidia-smi` output before passing to `bc`:
```bash
FREE_MEM_MIB=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')
TOTAL_MEM_MIB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
```

### Finding 3: Incomplete verification capture (MEDIUM — Process)

**Evidence**: `verify_1.md` ends after model name tests. Steps 3-4 (FalkorDB, full pipeline) not captured.

The verification session was either interrupted or the remaining steps were run separately without output capture. A complete verification requires all 4 steps.

## Recommendations

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 1 | Fix `--served-model-name` to register both short and full names | HIGH | 1 line change |
| 2 | Re-run verification for steps 3-4 (FalkorDB + full pipeline) | HIGH | 15 min manual |
| 3 | Fix `bc` input sanitization in pre-flight check | LOW | 2 line change |
| 4 | Verify `embedding_model` in `graphiti.yaml` matches served name | MEDIUM | Config check |

## Recommended Next Steps

1. **Fix** `vllm-embed.sh` line 37 to serve both model names
2. **Restart** embedding server with the fix
3. **Re-run** complete verification (all 4 steps) and capture output to `verify_2.md`
4. **Check** `graphiti.yaml` `embedding_model` value matches the served name

## Appendix

### Embedding Vector Validation

The successful embedding response (`verify_1.md:34`) returns:
- Model: `nomic-embed-text-v1.5`
- Embedding dimension: 768 floats (correct for nomic-embed-text-v1.5)
- Prompt tokens: 4 (correct for "Hello world" with BOS token)
- Response time: sub-second (healthy)

This confirms the embedding model is loaded correctly and producing valid output.
