---
id: TASK-GMO-003
title: "Update Graphiti config for MacBook LLM + GB10 embeddings split"
status: completed
updated: 2026-04-03T14:20:00Z
created: 2026-04-03T00:00:00Z
priority: high
tags: [graphiti, config, split-endpoints]
task_type: implementation
parent_review: TASK-REV-GMAC
feature_id: FEAT-GMO
implementation_mode: task-work
wave: 2
complexity: 2
depends_on:
  - TASK-GMO-002
---

# Task: Update Graphiti config for MacBook LLM + GB10 embeddings split

## Description

Update the two Graphiti config files to point the LLM endpoint at the MacBook while
keeping the embedding model on GB10. Create a toggle script for easy switching.

## Changes Required

### 1. `.mcp.json` — update `LLM_API_URL` env var

```json
"env": {
  "LLM_API_URL": "http://<macbook-tailscale-ip>:8000/v1",
  "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1"
}
```

### 2. `.guardkit/graphiti.yaml` — update `llm_base_url`

```yaml
llm_base_url: http://<macbook-tailscale-ip>:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M   # Ollama model name (or keep original if llama-server)
```

Note: `embedding_base_url` stays as `http://promaxgb10-41b1:8001/v1` — no change.

### 3. Create toggle script: `scripts/graphiti-endpoint-toggle.sh`

```bash
#!/usr/bin/env bash
# Toggle Graphiti LLM endpoint between GB10 and MacBook
# Usage: source scripts/graphiti-endpoint-toggle.sh [gb10|macbook]

case "${1:-}" in
  gb10)
    export LLM_API_URL="http://promaxgb10-41b1:8000/v1"
    echo "Graphiti LLM → GB10 (promaxgb10-41b1:8000)"
    ;;
  macbook)
    export LLM_API_URL="http://<macbook-tailscale-ip>:8000/v1"
    echo "Graphiti LLM → MacBook (<macbook-tailscale-ip>:8000)"
    ;;
  *)
    echo "Usage: source $0 [gb10|macbook]"
    echo "  gb10    — Point Graphiti LLM at GB10 (default, vLLM)"
    echo "  macbook — Point Graphiti LLM at MacBook Pro M2 Max (Ollama)"
    ;;
esac
```

### 4. Verify MCP server picks up the change

The MCP server config (`config-guardkit.yaml`) already uses `${LLM_API_URL:...}` with env var
fallback, so restarting the MCP server (or Claude Code) after setting the env var is sufficient.

## Acceptance Criteria

- [x] `.mcp.json` updated with MacBook LLM URL (richards-macbook-pro.tailebf801.ts.net:8000)
- [x] `.guardkit/graphiti.yaml` updated with MacBook LLM URL + ollama provider + Ollama model name
- [x] Toggle script created and tested (gb10 ↔ macbook) at `scripts/graphiti-endpoint-toggle.sh`
- [x] Embedding endpoint confirmed unchanged (still GB10 promaxgb10-41b1:8001)
- [ ] MCP server restarts cleanly with new endpoint (requires Claude Code restart — manual verification)
