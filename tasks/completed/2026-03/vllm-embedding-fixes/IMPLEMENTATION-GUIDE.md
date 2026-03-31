# Implementation Guide: vLLM Embedding Infrastructure Fixes

## Wave 1: Script & Config Fixes (Parallel)

### TASK-VEF-001: Fix vllm-embed.sh
**Method**: `/task-work TASK-VEF-001`
**Complexity**: 3 (simple, single file)
**File**: `scripts/vllm-embed.sh`

Changes:
1. Line 27: `GPU_UTIL` default 0.15 -> 0.03
2. Line 37/42: Add `--served-model-name $(basename "$MODEL")` to EXTRA_ARGS
3. Before `docker run`: Add nvidia-smi pre-flight memory check (~15 lines)

### TASK-VEF-002: Fix graphiti.yaml
**Method**: Direct edit
**Complexity**: 1 (single line change)
**File**: `.guardkit/graphiti.yaml`

Change:
- Line 50: `embedding_model: text-embedding-3-small` -> `embedding_model: nomic-embed-text-v1.5`

**Cross-task dependency**: The model name `nomic-embed-text-v1.5` must match the `--served-model-name` set in TASK-VEF-001. If VEF-001 changes the naming approach, update this accordingly.

## Wave 2: Verification (Sequential)

### TASK-VEF-003: End-to-End Verification
**Method**: Manual on Dell Pro Max GB10
**Complexity**: 2
**Depends on**: TASK-VEF-001, TASK-VEF-002

Run on GB10 hardware:
1. Start embedding server with LLM running -> no GPU memory error
2. Test embedding API with both short and full model names -> 200 OK
3. Test FalkorDB connection via Tailscale -> connected
4. Test graphiti capture -> embeddings stored successfully

## Wave 3: Post-Verification Fixes (from TASK-REV-36CC)

### TASK-VEF-004: Fix served-model-name and pre-flight bc calculation
**Method**: `/task-work TASK-VEF-004`
**Complexity**: 2 (two small changes in same file)
**File**: `scripts/vllm-embed.sh`
**Depends on**: TASK-VEF-001

Changes:
1. Line 37: Add second `--served-model-name $MODEL` to register both short and full names
2. Lines 81-82: Add `| tr -d ' '` to sanitize nvidia-smi output for `bc`

**Context**: Verification (TASK-VEF-003) showed that `--served-model-name` replaces rather than aliases the default model name. Full HuggingFace path returns 404.

## Wave 4: Re-verification (Sequential)

### TASK-VEF-005: Re-run Complete Verification
**Method**: Manual on Dell Pro Max GB10
**Complexity**: 2
**Depends on**: TASK-VEF-004

Re-run all 4 verification steps after VEF-004 fix:
1. Both short and full model names return 200
2. No `(standard_in)` errors during startup
3. FalkorDB connects via Tailscale
4. Graphiti capture works end-to-end
5. Capture output to `docs/reviews/graphiti-local-embedding/verify_2.md`

## Risk Notes

- `gpu_memory_utilization=0.03` assumes ~4 GiB free. If the LLM server consumes more, drop to 0.02.
- The `--served-model-name` flag behavior may vary between vLLM versions. Tested against v0.13.0.
- Multiple `--served-model-name` flags should work per vLLM docs but verify with the 26.01 container.
