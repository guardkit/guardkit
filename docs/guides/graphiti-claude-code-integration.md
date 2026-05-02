# Graphiti Claude Code Integration Guide

> **What is this guide?**
>
> GuardKit accesses the Graphiti knowledge graph via two complementary methods depending on context:
> **MCP server** (when running inside a Claude Code session) and **Python client** (for CLI workflows
> and AutoBuild). This guide covers both, explains when each is used, and how they stay in sync.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Infrastructure Topology](#infrastructure-topology)
- [Setup](#setup)
- [Configuration Files](#configuration-files)
- [Project Isolation and Group ID Namespacing](#project-isolation-and-group-id-namespacing)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Architecture Overview

### Two Access Methods, One Knowledge Graph

Graphiti is a temporal knowledge graph backed by FalkorDB. GuardKit accesses it in two ways:

| Method | When Used | Tools / API |
|--------|-----------|-------------|
| **MCP server** | Inside a Claude Code session | `mcp__graphiti__search_nodes`, `mcp__graphiti__search_memory_facts`, `mcp__graphiti__add_memory` |
| **Python client** | CLI commands, AutoBuild, seeding scripts | `guardkit.knowledge.get_graphiti()`, `guardkit graphiti *` CLI |

Both methods connect to **the same FalkorDB instance** and read/write the **same group IDs**. There is
no separate MCP-only or Python-only dataset — they are fully interchangeable views of the same graph.

### When Each Method Is Active

```
Claude Code session open
        │
        ├── MCP tools available? (mcp__graphiti__*)
        │       YES → Use MCP access
        │             (see .claude/rules/graphiti-knowledge-graph.md)
        │
        └── MCP tools NOT available
                    └── Use Python client access
                          (guardkit graphiti search / get_graphiti())
                          (see .claude/rules/graphiti-knowledge.md)
```

**The `graphiti-knowledge-graph.md` rule file** loads in sessions where MCP tools are available
and contains the correct group IDs and search patterns for MCP use.

**The `graphiti-knowledge.md` rule file** covers Python client access for CLI workflows.

Both rule files cross-reference each other so you always land in the right place.

---

## Infrastructure Topology

```
┌──────────────────────────────────────────────────────────────┐
│                      Developer Machine                        │
│                                                              │
│  ┌─────────────────┐        ┌──────────────────────────────┐ │
│  │  Claude Code    │        │  guardkit CLI / AutoBuild    │ │
│  │  Session        │        │  (Python client)             │ │
│  │                 │        │                              │ │
│  │  mcp__graphiti__│        │  guardkit.knowledge          │ │
│  │  search_nodes   │        │  get_graphiti()              │ │
│  │  add_memory     │        │  GraphitiClient              │ │
│  └────────┬────────┘        └──────────────┬───────────────┘ │
│           │  MCP protocol                  │  Direct Redis    │
│           │  (stdio / HTTP)                │  protocol        │
└───────────┼────────────────────────────────┼─────────────────┘
            │                                │
            │         Tailscale VPN          │
            ▼                                ▼
┌───────────────────────────────────────────────────────────────┐
│                     GB10 Workstation (promaxgb10-41b1)         │
│                                                               │
│  ┌──────────────────────┐   ┌─────────────────────────────┐  │
│  │  Graphiti MCP Server │   │  vLLM (port 8000)           │  │
│  │  (Python process,    │   │  Qwen2.5-14B                │  │
│  │   launched by        │   │  (entity extraction)        │  │
│  │   .mcp.json)         │   └─────────────────────────────┘  │
│  └──────────┬───────────┘   ┌─────────────────────────────┐  │
│             │               │  vLLM (port 8001)           │  │
│             │               │  nomic-embed-text-v1.5      │  │
│             │               │  (embeddings, 1024 dims)    │  │
│             │               └─────────────────────────────┘  │
└─────────────┼─────────────────────────────────────────────────┘
              │ Redis protocol
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Synology NAS (whitestocks)                     │
│                                                                  │
│   FalkorDB (port 6379)   ·   Browser UI (port 3000)             │
│   Knowledge graph storage                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Key infrastructure components:**

| Component | Location | Purpose |
|-----------|----------|---------|
| FalkorDB | `whitestocks:6379` | Graph storage (Synology NAS via Tailscale) |
| Graphiti MCP server | GB10 workstation | Claude Code MCP access |
| vLLM LLM | `promaxgb10-41b1:8000` | Entity extraction (Qwen2.5-14B) |
| vLLM Embeddings | `promaxgb10-41b1:8001` | Vector embeddings (nomic-embed-text-v1.5, 1024 dims) |
| FalkorDB Browser | `http://whitestocks:3000` | Graph inspection UI |

---

## Setup

### Prerequisites

- Tailscale connected (for access to `whitestocks` and `promaxgb10-41b1`)
- GuardKit installed (`pip install guardkit-py`)
- FalkorDB running on NAS (see below)

### Start FalkorDB on NAS

```bash
ssh richardwoollcott@whitestocks
cd /volume1/guardkit/docker
sudo docker-compose -f docker-compose.falkordb.yml up -d
```

### Initialize a New Project with MCP

```bash
# Standard init (inherits Graphiti settings from parent project)
guardkit init --copy-graphiti

# Or specify source explicitly
guardkit init --copy-graphiti-from /path/to/parent/project
```

Using `--copy-graphiti` ensures your project inherits the correct FalkorDB host, embedding model,
and dimension settings. Without it, the project defaults to OpenAI embeddings, which causes
**dimension mismatches** if the shared FalkorDB was seeded with nomic-embed-text-v1.5 (1024 dims
vs OpenAI's 1536 dims).

### Seed System Knowledge

After init, seed GuardKit system knowledge (one-time per FalkorDB instance):

```bash
guardkit graphiti seed-system
```

Seed project-specific knowledge:

```bash
guardkit graphiti capture --interactive
```

### Configure MCP Server (`.mcp.json`)

To enable MCP access in Claude Code sessions, add the Graphiti MCP server to `.mcp.json`:

```json
{
  "mcpServers": {
    "graphiti": {
      "command": "uvx",
      "args": [
        "--from", "graphiti-core[falkordb]",
        "graphiti-service",
        "--transport", "stdio",
        "--group-id", "guardkit"
      ],
      "env": {
        "FALKORDB_HOST": "whitestocks",
        "FALKORDB_PORT": "6379",
        "OPENAI_API_KEY": "not-used",
        "LLM_BASE_URL": "http://promaxgb10-41b1:8000/v1",
        "LLM_MODEL": "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic",
        "EMBEDDER_BASE_URL": "http://promaxgb10-41b1:8001/v1",
        "EMBEDDER_MODEL": "nomic-embed-text-v1.5"
      }
    }
  }
}
```

> **Note**: The `.mcp.json` in this repository currently has an empty `mcpServers` object because
> the MCP server is configured per-developer. Each developer adds their own server configuration
> to suit their infrastructure.

After updating `.mcp.json`, restart Claude Code. If the MCP server starts correctly, you will see
`mcp__graphiti__*` tools available in your session.

---

## Configuration Files

### `.guardkit/graphiti.yaml` — Python Client Configuration

This file configures the Python client used by CLI commands and AutoBuild:

```yaml
# Project ID — prefix for all project-specific group IDs
project_id: guardkit

# Enable/disable Graphiti
enabled: true

# Graph database backend
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0

# Parallelism for seeding (1-10, default: 3)
max_concurrent_episodes: 3

# LLM for entity extraction (vLLM in this project)
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
llm_max_tokens: 4096

# Embedding model (must match what FalkorDB was seeded with)
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5

# System-scoped group IDs for seed-system command
group_ids:
  - product_knowledge
  - command_workflows
  - architecture_decisions
```

**Critical**: `embedding_model` must match the model used when FalkorDB was first seeded.
Changing the model after seeding causes dimension mismatches. Use `--copy-graphiti` when
initializing new projects to inherit the correct settings automatically.

### `.mcp.json` — MCP Server Configuration

Configures the Graphiti MCP server launched by Claude Code. The MCP server connects to the
same FalkorDB instance using the same embedding model. The key constraint: the `EMBEDDER_MODEL`
in `.mcp.json` **must match** `embedding_model` in `.guardkit/graphiti.yaml`.

---

## Project Isolation and Group ID Namespacing

### The Problem

Multiple projects can share a single FalkorDB instance. Without isolation, a query for
"authentication patterns" in Project B might return Project A's JWT decision instead.

### The Solution: `project_id` Prefixing

The Python client (`GraphitiClient`) automatically prefixes all project-specific group IDs
with `{project_id}__`. This happens transparently via `GraphitiClient.get_group_id()`.

**Example for `project_id: guardkit`:**

| Logical Group | Stored As |
|---------------|-----------|
| `project_overview` | `guardkit__project_overview` |
| `project_architecture` | `guardkit__project_architecture` |
| `feature_specs` | `guardkit__feature_specs` |
| `task_outcomes` | `guardkit__task_outcomes` |
| `turn_states` | `guardkit__turn_states` |

**System groups are never prefixed** — they're intentionally shared:

| Group | Stored As | Shared? |
|-------|-----------|---------|
| `product_knowledge` | `product_knowledge` | Yes — all projects |
| `command_workflows` | `command_workflows` | Yes — all projects |
| `architecture_decisions` | `architecture_decisions` | Yes — all projects |

### MCP Access and Namespacing

When using MCP tools, pass group IDs **as stored** (with the prefix already applied):

```python
# Correct — pass the actual stored group IDs
group_ids = [
    "product_knowledge",          # system (no prefix)
    "command_workflows",          # system (no prefix)
    "guardkit__project_overview", # project-specific (prefixed)
    "guardkit__project_decisions",
]
```

The MCP server does not auto-prefix — you must pass the full group IDs. The `.claude/rules/graphiti-knowledge-graph.md`
file contains the complete group ID reference for this project.

### Python Client Access and Namespacing

The Python client auto-prefixes via `get_group_id()`. Pass the logical (unprefixed) name:

```python
client = get_graphiti()

# Client auto-prefixes project groups
results = await client.search(
    query="authentication patterns",
    group_ids=["project_architecture"],  # stored as guardkit__project_architecture
    num_results=5
)
```

For system groups, pass them as-is (no prefix needed either way):

```python
results = await client.search(
    query="task-work command workflow",
    group_ids=["command_workflows"],  # system group, no prefix
    num_results=5
)
```

---

## Troubleshooting

### MCP server won't start

**Symptom**: `mcp__graphiti__*` tools not available in Claude Code session.

1. Check `.mcp.json` has the correct server configuration (see [Setup](#setup))
2. Restart Claude Code after modifying `.mcp.json`
3. Verify Tailscale is connected and `whitestocks` and `promaxgb10-41b1` are reachable:
   ```bash
   ping whitestocks
   ping promaxgb10-41b1
   ```
4. Check FalkorDB is running:
   ```bash
   redis-cli -h whitestocks -p 6379 ping
   # Expected: PONG
   ```
5. Check MCP server logs in Claude Code (View → Output → MCP)

### MCP write `group_id` coercion (HTTP transport)

**Symptom**: Episodes written via `mcp__graphiti__add_memory` land in
`product_knowledge` (or another server-default group) instead of the
`group_id` the caller passed. Subsequent searches scoped to the
requested group return no results.

**Cause**: The HTTP MCP transport at `http://promaxgb10-41b1:8004/mcp`
silently overrides the client-supplied `group_id` parameter with a
server-side default. Search calls are unaffected — only writes leak
into the wrong namespace.

**Detection**: The MCP response message reveals the actual group used:

```
"Episode 'X' queued for processing in group 'product_knowledge'"
                                            ^^^^^^^^^^^^^^^^^
                                            actual, may differ from
                                            what was requested
```

If this string differs from the requested `group_id`, the write was
overridden.

**Workaround**:

- `/task-complete` auto-detects the override (via
  `installer/core/commands/lib/graphiti_response_parser.py`) and falls
  back to the Python CLI for task-outcome writes:
  ```bash
  guardkit graphiti capture-outcome --from-task-file <path> --timeout 300
  ```
  The CLI bypasses the MCP server and writes directly via
  `GraphitiClient`, which honours `group_id`.
- For ad-hoc writes outside `/task-complete`, prefer the CLI for any
  episode that must land in a specific group. Inline
  `mcp__graphiti__add_memory` calls are still subject to the override.
- For inline architectural-decision writes (Write 2 in `/task-complete`),
  there is no equivalent CLI surface — the user is warned and decides
  whether to file a follow-up.

**Status**: This is an upstream `graphiti-mcp` HTTP-server issue. The
server runs on `promaxgb10-41b1` (not in this repo's `infra/`). A
separate infra task should configure the server to honour client-
supplied `group_id` or patch the upstream server to forward the
parameter from the JSON body to the underlying `add_episode` call.
See: TASK-FIX-B1F7.

### Group ID mismatch — no results returned

**Symptom**: Searches return empty results even though knowledge was seeded.

1. Always pass explicit `group_ids` — searching without them returns nothing:
   ```python
   # Wrong — no group_ids
   mcp__graphiti__search_nodes(query="...")

   # Correct — explicit group_ids
   mcp__graphiti__search_nodes(query="...", group_ids=["product_knowledge", "guardkit__project_overview"])
   ```
2. Verify the correct prefix for project groups. Check `project_id` in `.guardkit/graphiti.yaml`:
   ```bash
   grep project_id .guardkit/graphiti.yaml
   # project_id: guardkit → prefix is "guardkit__"
   ```
3. Use the Python client to verify knowledge exists:
   ```bash
   guardkit graphiti search "your query" --group product_knowledge
   ```
4. Re-seed if knowledge is missing:
   ```bash
   guardkit graphiti seed-system   # system groups
   guardkit graphiti capture --interactive  # project groups
   ```

### Embedding dimension mismatch

**Symptom**: Errors like `dimension mismatch: expected 1024, got 1536` when seeding or querying.

**Cause**: The FalkorDB instance was seeded with one embedding model but the current config
uses a different model. This is most common when a new project uses the OpenAI default
(`text-embedding-3-small`, 1536 dims) but the shared FalkorDB was seeded with
`nomic-embed-text-v1.5` (1024 dims).

**Fix**: Always use `--copy-graphiti` when initialising new projects on a shared FalkorDB:
```bash
guardkit init --copy-graphiti
```

If already initialised with wrong settings, copy the embedding config from an existing project:
```bash
guardkit init --copy-graphiti-from /path/to/working/project
```

Or manually update `.guardkit/graphiti.yaml` to match:
```yaml
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

And ensure `.mcp.json` matches:
```json
"EMBEDDER_MODEL": "nomic-embed-text-v1.5"
```

### Python client connection failure

**Symptom**: `guardkit graphiti status` shows `Connection: Failed`.

1. Check FalkorDB is reachable:
   ```bash
   redis-cli -h whitestocks -p 6379 ping
   ```
2. Start FalkorDB on the NAS if needed:
   ```bash
   ssh richardwoollcott@whitestocks
   cd /volume1/guardkit/docker
   sudo docker-compose -f docker-compose.falkordb.yml up -d
   ```
3. Check `enabled: true` in `.guardkit/graphiti.yaml`
4. Verify Tailscale connection

GuardKit degrades gracefully when Graphiti is unavailable — all commands continue to work,
skipping knowledge capture and context loading.

---

## See Also

- `.claude/rules/graphiti-knowledge-graph.md` — MCP access: group IDs, search tools, add_memory patterns
- `.claude/rules/graphiti-knowledge.md` — Python client access: CLI commands, threading model, seeding
- `docs/guides/graphiti-integration-guide.md` — Full Graphiti integration overview
- `docs/guides/graphiti-project-namespaces.md` — Multi-project isolation deep-dive
- `docs/guides/graphiti-shared-infrastructure.md` — Shared FalkorDB setup
- `.guardkit/graphiti.yaml` — Python client configuration
- `.mcp.json` — MCP server configuration
