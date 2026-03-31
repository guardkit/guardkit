---
id: TASK-CC3E
title: Diagnose vLLM embedding GPU memory error and fix
status: review_complete
created: 2026-02-28T00:00:00Z
updated: 2026-02-28T00:00:00Z
priority: high
tags: [graphiti, vllm, embedding, gpu, infrastructure, review]
task_type: review
complexity: 5
review_mode: architectural
review_depth: standard
review_results:
  score: 78
  findings_count: 5
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-CC3E-review-report.md
  completed_at: 2026-02-28T12:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Diagnose vLLM embedding GPU memory error and fix

## Description

Analyse the error output captured in `docs/reviews/graphiti-local-embedding/run_embedding_1.md` from running `./scripts/vllm-embed.sh` on the Dell Pro Max GB10 / DGX Spark. Diagnose the root cause and implement fixes.

## Error Summary

### Error 1: GPU Memory Exhaustion on First Start (run_embedding_1.md)

The vLLM embedding server (`nomic-ai/nomic-embed-text-v1.5`) fails to start with:

```
ValueError: Free memory on device (4.04/119.63 GiB) on startup is less than desired GPU memory utilization (0.15, 17.94 GiB).
Decrease GPU memory utilization or reduce GPU memory used by other processes.
```

**Root Cause Analysis:**
- The GPU has 119.63 GiB total VRAM but only 4.04 GiB free at startup
- The script requests `gpu_memory_utilization=0.15` which equates to ~17.94 GiB
- Other processes (likely the main vLLM LLM server on port 8000) are consuming ~115.59 GiB
- The embedding model itself is tiny (~274MB) but the 0.15 utilization factor is applied to total GPU memory

### Error 2: Model Name Mismatch — Embeddings Return 404 (docker_logs_1.md)

After a successful second start (model loaded, server running on port 8001), embedding requests fail:

```
$ curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
→ {"error":{"message":"The model `nomic-embed-text-v1.5` does not exist.","type":"NotFoundError","code":404}}
```

Also: `curl http://localhost:8001/models` → 404 (wrong path; correct path is `/v1/models`).

**Root Cause:** vLLM registers the model under its full HuggingFace path `nomic-ai/nomic-embed-text-v1.5` (as seen in `served_model_name` in the logs), but the test curl in `vllm-embed.sh` uses the basename `nomic-embed-text-v1.5` (without the `nomic-ai/` prefix). The script generates the test command using `$(basename "$MODEL")` which strips the org prefix.

**Confirmed** via `/v1/models` endpoint:
```json
{"object":"list","data":[{"id":"nomic-ai/nomic-embed-text-v1.5","object":"model",...,"max_model_len":2048}]}
```
The registered model ID is `nomic-ai/nomic-embed-text-v1.5` — the basename `nomic-embed-text-v1.5` does not match.

**Fix:** Either:
- Use the full model name in the curl test: `"model": "nomic-ai/nomic-embed-text-v1.5"`
- Or add `--served-model-name nomic-embed-text-v1.5` to the vLLM serve command to register a short alias

### Error 3: FalkorDB Connection Refused (clear_1.md, clear_2.md)

The `guardkit graphiti clear --dry-run` command fails with repeated connection errors:

```
Failed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 61] Connect call failed)
```

**Root Cause:** FalkorDB runs on the **Synology NAS**, not localhost. The Graphiti client defaults to `bolt://localhost:7687` but should be configured to connect via **Tailscale** to the NAS IP address. The `graphiti.yaml` config file is missing (`/Users/richardwoollcott/.guardkit/graphiti.yaml` not found), so the client falls back to localhost defaults.

**Fix:**
- Create/update `.guardkit/graphiti.yaml` with the Tailscale IP of the Synology NAS for the Neo4j/FalkorDB bolt connection
- Add connection timeout to the Graphiti client so it fails fast instead of retrying for minutes when the NAS is unreachable
- Document the Tailscale network dependency in setup instructions

### Additional Warnings (non-blocking):
- `NomicBertConfig` deprecated attribute names (`rotary_emb_base` → `rope_theta`)
- Nomic context extension disabled, max_model_len reduced from 8192 to 2048
- `torchvision` image extension load failure (irrelevant for embeddings)

## Acceptance Criteria

- [ ] vLLM embedding server starts successfully alongside the main LLM server
- [ ] GPU memory allocation is right-sized for the embedding model (~274MB, not 17.94 GiB)
- [ ] Script includes pre-flight check for available GPU memory
- [ ] Embedding API responds correctly (model name matches between client and server)
- [ ] Test curl in vllm-embed.sh uses correct model identifier
- [ ] FalkorDB connects via Tailscale to Synology NAS (not localhost)
- [ ] graphiti.yaml configured with Tailscale NAS address for bolt connection
- [ ] FalkorDB connection has a reasonable timeout and clear error message
- [ ] Documentation updated with correct GPU memory settings and network topology

## Proposed Fixes

### Fix 1: Reduce GPU memory utilization for embedding model
The `nomic-embed-text-v1.5` is only 137M parameters (~274MB in fp16). Setting `gpu_memory_utilization=0.15` allocates 15% of the full GPU (17.94 GiB) which is ~65x more than needed. Options:
- Set `VLLM_EMBED_GPU_UTIL=0.05` (or lower) to request ~6 GiB
- Or set `VLLM_EMBED_GPU_UTIL=0.03` to request ~3.6 GiB (still generous for a 274MB model)

### Fix 2: Add pre-flight GPU memory check to vllm-embed.sh
Before launching the container, query available GPU memory with `nvidia-smi` and warn/fail early if insufficient.

### Fix 3: Fix model name mismatch in vllm-embed.sh
The script generates the test curl using `$(basename "$MODEL")` which produces `nomic-embed-text-v1.5`, but vLLM registers the model as `nomic-ai/nomic-embed-text-v1.5` (the full HuggingFace ID). Two options:
- **Option A:** Change the test curl to use `$MODEL` (the full name) instead of `$(basename "$MODEL")`
- **Option B (preferred):** Add `--served-model-name "$(basename "$MODEL")"` to the `vllm serve` command so the short name works as an alias

### Fix 4: Configure FalkorDB connection via Tailscale to Synology NAS
FalkorDB runs on the Synology NAS, not localhost. The Graphiti client must connect via Tailscale:
- Create `.guardkit/graphiti.yaml` with `neo4j_uri: bolt://<synology-tailscale-ip>:7687`
- Update default config to document the Tailscale requirement
- Add connection timeout (e.g., 10 seconds) so it fails fast when NAS is unreachable

### Fix 5: FalkorDB connection timeout
Add a connection timeout to the Graphiti client configuration so it fails fast instead of retrying for minutes when the Synology NAS is unreachable via Tailscale.

## Files to Modify

- `scripts/vllm-embed.sh` — GPU memory utilization default, pre-flight check, model name fix
- `guardkit/knowledge/graphiti_client.py` — Connection timeout configuration
- `guardkit/knowledge/config.py` — Default timeout settings, Tailscale NAS connection defaults
- `~/.guardkit/graphiti.yaml` — FalkorDB Tailscale connection config (create if missing)

## Review Evidence

- [run_embedding_1.md](docs/reviews/graphiti-local-embedding/run_embedding_1.md) — vLLM GPU memory error (first start)
- [docker_logs_1.md](docs/reviews/graphiti-local-embedding/docker_logs_1.md) — vLLM successful start but model name 404 on embedding API
- [clear_1.md](docs/reviews/graphiti-local-embedding/clear_1.md) — FalkorDB connection refused (localhost instead of Tailscale NAS)
- [clear_2.md](docs/reviews/graphiti-local-embedding/clear_2.md) — FalkorDB connection refused (repeat)

## Infrastructure Topology

```
                    Tailscale Network
                    ─────────────────
Dell Pro Max GB10 / DGX Spark          Synology NAS
├── vLLM LLM server (port 8000)        └── FalkorDB (bolt port 7687)
├── vLLM Embedding server (port 8001)
└── Graphiti client ──── Tailscale ────────► bolt://<nas-ip>:7687
```

- **GPU:** The main LLM server on port 8000 consumes most of the GPU memory. The embedding server needs to coexist with minimal footprint.
- **FalkorDB:** Runs on the Synology NAS, NOT localhost. Must be accessed via Tailscale IP.
- The `gpu_memory_utilization` parameter in vLLM sets a fraction of *total* GPU memory, not a fixed allocation — so even 0.05 (5%) = ~6 GiB which is still 20x what the 274MB model needs.

## Test Execution Log

[Automatically populated by /task-work]
