# Graphiti LLM Offload to MacBook Pro M2 Max

When the GB10's GPU is occupied (e.g., during 50-60 hour dataset generation runs),
Graphiti's LLM can be offloaded to a MacBook Pro M2 Max over Tailscale. The embedding
model stays on GB10 (port 8001) since it uses negligible GPU (~0.5GB).

**Architecture:**

```
MacBook Pro M2 Max (Ollama)        GB10 / DGX Spark
┌──────────────────────────┐      ┌──────────────────────────┐
│ Qwen2.5-14B Q4_K_M       │      │ nomic-embed-text-v1.5    │
│ Port 8000 (LLM)          │      │ Port 8001 (embeddings)   │
│ ~10GB RAM                 │      │ ~0.5GB GPU               │
└───────────┬──────────────┘      └───────────┬──────────────┘
            │  Tailscale                       │
            └──────────┬───────────────────────┘
                       │
              ┌────────▼────────┐
              │  Synology NAS   │
              │  FalkorDB:6379  │
              │  (whitestocks)  │
              └─────────────────┘
```

---

## Prerequisites

- MacBook Pro M2 Max with 96GB RAM
- Tailscale installed and connected on all machines
- Homebrew installed on MacBook
- GB10 running embedding model on port 8001 (`scripts/vllm-embed.sh`)
- FalkorDB running on whitestocks:6379

---

## Quick Start

### 1. Install Ollama

```bash
brew install ollama
```

### 2. Pull the model

```bash
ollama pull qwen2.5:14b-instruct-q4_K_M
```

This downloads ~9GB. The Q4_K_M quantization provides good quality for entity
extraction while fitting comfortably in memory.

### 3. Start Ollama

```bash
ollama serve
```

Ollama listens on `http://localhost:11434` by default. For Graphiti, the MCP server
connects to `http://richards-macbook-pro.tailebf801.ts.net:8000/v1` — Ollama
automatically exposes the OpenAI-compatible API on this port when accessed
via the Tailscale hostname.

> **Note**: If port 8000 is already in use, set `OLLAMA_HOST=0.0.0.0:8000`
> before starting, or adjust the config URLs accordingly.

### 4. Update configuration

Two files need updating: `.mcp.json` (MCP server env vars) and
`.guardkit/graphiti.yaml` (Python client config).

**`.mcp.json`** — set LLM env vars in the graphiti server block:

```json
"env": {
  "LLM_API_URL": "http://richards-macbook-pro.tailebf801.ts.net:8000/v1",
  "LLM_MODEL": "qwen2.5:14b-instruct-q4_K_M",
  "OPENAI_API_KEY": "not-needed-vllm-local",
  "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1",
  "EMBEDDING_DIM": "1024"
}
```

**`.guardkit/graphiti.yaml`** — set LLM provider and URL:

```yaml
# --- MacBook Pro M2 Max (Ollama, Q4_K_M) ---
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
```

Comment out the GB10 lines if they're active:

```yaml
# --- GB10 (vLLM, FP8) ---
#llm_provider: vllm
#llm_base_url: http://promaxgb10-41b1:8000/v1
#llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
```

### 5. Restart Claude Code

The MCP server reads config at startup. After changing `.mcp.json`, restart
Claude Code (or the terminal session) to pick up the new settings.

### 6. Test

```
mcp__graphiti__get_status
mcp__graphiti__add_memory(
  name: "Test episode",
  episode_body: "Testing MacBook LLM offload.",
  group_id: "guardkit__project_decisions"
)
```

---

## Switching Between GB10 and MacBook

### When to use MacBook
- GB10 GPU is occupied by dataset generation or other long-running jobs
- You need Graphiti for project init, system-arch, AutoBuild context, or knowledge capture

### When to switch back to GB10
- Dataset generation is complete and GB10 GPU is free
- You need faster throughput (GB10 is ~2-3x faster)

### Toggle script

```bash
# Switch to MacBook
source scripts/graphiti-endpoint-toggle.sh macbook

# Switch to GB10
source scripts/graphiti-endpoint-toggle.sh gb10

# Check current setting
source scripts/graphiti-endpoint-toggle.sh
```

The toggle script sets `LLM_API_URL` as an environment variable. The MCP server
config (`config-guardkit.yaml`) uses `${LLM_API_URL:...}` with env var fallback,
so the env var takes precedence.

**After toggling, you must restart Claude Code** for the MCP server to pick up the change.

> **Important**: The toggle script only affects the LLM endpoint. Embeddings always
> stay on GB10 (`promaxgb10-41b1:8001`). Also update `.guardkit/graphiti.yaml` to
> match if using the Python CLI client (`guardkit graphiti ...`).

---

## Configuration Reference

### Files

| File | Controls | Used by |
|------|----------|---------|
| `.mcp.json` | MCP server env vars (LLM_API_URL, LLM_MODEL) | Claude Code MCP server |
| `.guardkit/graphiti.yaml` | llm_provider, llm_base_url, llm_model | Python CLI client |
| `graphiti/mcp_server/config/config-guardkit.yaml` | Server config with env var defaults | MCP server process |
| `scripts/graphiti-endpoint-toggle.sh` | Quick env var toggle | Shell sessions |

### Environment variable overrides

The MCP server config supports env var substitution with defaults:

```yaml
model: ${LLM_MODEL:neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic}
api_url: ${LLM_API_URL:http://promaxgb10-41b1:8000/v1}
api_url: ${EMBEDDING_API_URL:http://promaxgb10-41b1:8001/v1}
```

Setting `LLM_API_URL` and `LLM_MODEL` in the environment (or `.mcp.json` env block)
overrides the defaults without editing the YAML.

---

## Performance Notes

Measured during TASK-GMO-004 validation (2026-04-03):

| Metric | MacBook (Ollama Q4_K_M) | GB10 (vLLM FP8) |
|--------|------------------------|------------------|
| Entity extraction | 16.9s (7 entities) | ~8-10s |
| Full episode pipeline | 54.7s | ~30s |
| Throughput | ~15-25 tok/s | ~40 tok/s |
| Prefix caching | No | Yes |
| Entity quality | Comparable (7/7 correct) | Baseline |

**Acceptable threshold**: Episode processing under 180 seconds. MacBook at 54.7s is
well within limits for interactive use.

**No prefix caching**: Ollama doesn't support prefix caching, so first-token latency
(TTFT) is higher than GB10. This primarily affects the first request after model load.

---

## Troubleshooting

### macOS firewall blocking connections

If the MCP server can't reach Ollama on the MacBook, check:

```bash
# Verify Ollama is listening
curl http://localhost:11434/v1/models

# Verify Tailscale connectivity from another machine
curl http://richards-macbook-pro.tailebf801.ts.net:11434/v1/models
```

If blocked, allow Ollama through System Settings > Network > Firewall.

### Ollama port conflicts

If port 11434 (or 8000) is already in use:

```bash
# Check what's using the port
lsof -i :11434

# Start Ollama on a different port
OLLAMA_HOST=0.0.0.0:8080 ollama serve
```

Update all config files to match the new port.

### Model not loading (memory pressure)

Qwen2.5-14B Q4_K_M needs ~10GB RAM. On a 96GB MacBook this is comfortable,
but if memory-intensive apps are running:

```bash
# Check available memory
vm_stat | head -5

# Check Ollama model status
ollama ps
```

Close browsers with many tabs or memory-heavy apps if needed. Only necessary
for Q8_0 or larger quantizations (~16GB+).

### Tailscale connectivity issues

```bash
# Check Tailscale status
tailscale status

# Ping the MacBook from GB10
tailscale ping richards-macbook-pro

# Check if the MagicDNS name resolves
nslookup richards-macbook-pro.tailebf801.ts.net
```

### MCP server errors after switching endpoints

If `mcp__graphiti__add_memory` fails after switching:

1. **Check the MCP server restarted** — Claude Code must be restarted after config changes
2. **Check the LLM is reachable** — `curl <LLM_API_URL>/models` from the MCP server host
3. **Check the model name matches** — Ollama uses `qwen2.5:14b-instruct-q4_K_M`, vLLM uses `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`

### Known issue: OpenAI Responses API incompatibility

graphiti-core v0.26.3 `OpenAIClient` uses the OpenAI Responses API
(`client.responses.parse()`), which Ollama and vLLM don't support. The MCP server
factory (`graphiti/mcp_server/src/services/factories.py`) auto-detects non-OpenAI
endpoints and uses `OpenAIGenericClient` instead, which uses the standard Chat
Completions API with `json_schema` response format. This was fixed in TASK-GMO-004.

---

## Memory Budget

| Component | RAM Usage | Notes |
|-----------|-----------|-------|
| Qwen2.5-14B Q4_K_M | ~10 GB | Loaded by Ollama |
| Ollama runtime | ~0.5 GB | Server overhead |
| macOS + desktop | ~8-12 GB | Varies by open apps |
| **Total needed** | **~20 GB** | Comfortable on 96GB |

For Q8_0 quantization (~16GB model), close browsers and IDEs to free memory.
For Q4_K_M, no special memory management needed on a 96GB machine.
