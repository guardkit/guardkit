# Task: Update graphiti.yaml Endpoints — vLLM → llama-swap

**Date:** 2026-04-29
**Context:** The GB10 inference stack has been migrated from vLLM to all-llama.cpp via llama-swap on `:9000` (see `guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md`). The `guardkit` repo's config was updated during deployment. All other repos still point at the dead vLLM endpoints (`:8000` for LLM, `:8001` for embeddings).

---

## What Needs to Change

In every `.guardkit/graphiti.yaml` file:

| Field | Old (vLLM, dead) | New (llama-swap, live) |
|---|---|---|
| `llm_base_url` | `http://promaxgb10-41b1:8000/v1` | `http://promaxgb10-41b1:9000/v1` |
| `embedding_base_url` | `http://promaxgb10-41b1:8001/v1` | `http://promaxgb10-41b1:9000/v1` |

Additionally, add this field if missing (prevents 429 throttling — see TASK-OPS-9F2A):
```yaml
chunk_extraction_concurrency: 4
```

And remove the deprecated fields at the bottom if present:
```yaml
# REMOVE these:
host: localhost
port: 8000
```

The `llm_model` value `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` is fine — it's registered as a llama-swap alias for `qwen-graphiti`.

---

## Affected Repos (13 repos, 15 files)

### ✅ Already updated
| Repo | Status |
|---|---|
| `guardkit` | ✅ Updated to :9000 during v3 deployment |

### ❌ Needs update — Active repos (create tasks for these)

| # | Repo | File | Priority |
|---|---|---|---|
| 1 | `agentic-dataset-factory` | `.guardkit/graphiti.yaml` | **High** — active pipeline work |
| 2 | `jarvis` | `.guardkit/graphiti.yaml` | **High** — fleet intent router |
| 3 | `forge` | `.guardkit/graphiti.yaml` | **High** — pipeline orchestrator |
| 4 | `study-tutor` | `.guardkit/graphiti.yaml` | **High** — Lilymay's tutor |
| 5 | `specialist-agent` | `.guardkit/graphiti.yaml` | **High** — agent fleet member |
| 6 | `lpa-platform` | `.guardkit/graphiti.yaml` | **Medium** — FinProxy client project |
| 7 | `nats-core` | `.guardkit/graphiti.yaml` | **Medium** — fleet messaging |
| 8 | `nats-infrastructure` | `.guardkit/graphiti.yaml` | **Medium** — fleet infra |
| 9 | `require-kit` | `.guardkit/graphiti.yaml` | **Medium** — PM tooling |
| 10 | `youtube-transcript-mcp` | `.guardkit/graphiti.yaml` | **Low** — content pipeline |

### ❌ Needs update — Reference/exemplar repos (lower priority)

| # | Repo | File | Priority |
|---|---|---|---|
| 11 | `deepagents-player-coach-exemplar` | `.guardkit/graphiti.yaml` | **Low** — template source |
| 12 | `deepagents-player-coach-exemplar-original` | `.guardkit/graphiti.yaml` | **Low** — archive |
| 13 | `dotnet-functional-fastendpoints-exemplar` | `.guardkit/graphiti.yaml` | **Low** — .NET reference |
| 14 | `vllm-profiling` | `.guardkit/graphiti.yaml` | **Low** — historical |

### Worktree copies (updated automatically when parent is fixed)

| Repo | Worktree file |
|---|---|
| `study-tutor` | `.guardkit/worktrees/FEAT-1773/.guardkit/graphiti.yaml` |
| `vllm-profiling` | `.guardkit/worktrees/FEAT-1637/.guardkit/graphiti.yaml` |

### Different schema — no action needed

| Repo | File | Notes |
|---|---|---|
| `require-kit` | `installer/global/config/graphiti.yaml` | This is the RequireKit installer template — uses Neo4j/Bolt config, not LLM endpoints. Not affected. |

---

## Task Template (copy per repo)

```
Title: Update graphiti.yaml — vLLM → llama-swap endpoint migration

The GB10 inference stack has migrated from vLLM (ports 8000/8001) to 
all-llama.cpp via llama-swap (single port 9000). Update the Graphiti 
config to point at the live endpoint.

Changes in .guardkit/graphiti.yaml:
1. llm_base_url: change :8000 → :9000
2. embedding_base_url: change :8001 → :9000  
3. Add chunk_extraction_concurrency: 4 (if missing)
4. Remove deprecated host/port fields at bottom (if present)
5. Update comments: "vLLM" → "llama-swap" where applicable

Reference: guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md
```

---

## Batch Fix Script (optional — run from MacBook)

If you'd prefer to fix all 13 repos in one shot rather than creating individual tasks:

```bash
cd ~/Projects/appmilla_github

for REPO in \
    agentic-dataset-factory \
    jarvis \
    forge \
    study-tutor \
    specialist-agent \
    lpa-platform \
    nats-core \
    nats-infrastructure \
    require-kit \
    youtube-transcript-mcp \
    deepagents-player-coach-exemplar \
    deepagents-player-coach-exemplar-original \
    dotnet-functional-fastendpoints-exemplar \
    vllm-profiling; do
    
    FILE="$REPO/.guardkit/graphiti.yaml"
    
    if [ -f "$FILE" ]; then
        echo "Updating: $FILE"
        
        # Fix LLM endpoint
        sed -i '' 's|llm_base_url: http://promaxgb10-41b1:8000/v1|llm_base_url: http://promaxgb10-41b1:9000/v1|' "$FILE"
        
        # Fix embedding endpoint
        sed -i '' 's|embedding_base_url: http://promaxgb10-41b1:8001/v1|embedding_base_url: http://promaxgb10-41b1:9000/v1|' "$FILE"
        
        # Remove deprecated host/port fields
        sed -i '' '/^host: localhost$/d' "$FILE"
        sed -i '' '/^port: 8000$/d' "$FILE"
        
        # Add chunk_extraction_concurrency if missing
        if ! grep -q 'chunk_extraction_concurrency' "$FILE"; then
            sed -i '' '/^max_concurrent_episodes:/a\
chunk_extraction_concurrency: 4' "$FILE"
        fi
        
        echo "  Done."
    else
        echo "SKIP: $FILE not found"
    fi
done

echo ""
echo "=== Verify changes ==="
grep -r "8000\|8001" */\.guardkit/graphiti.yaml 2>/dev/null && echo "WARNING: Some files still reference old ports" || echo "All files updated to :9000"
```

---

*Prepared: 2026-04-29*
*Reference: guardkit/.guardkit/graphiti.yaml (already correct — use as template)*
