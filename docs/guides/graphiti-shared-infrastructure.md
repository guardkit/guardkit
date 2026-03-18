# Graphiti Shared Infrastructure

> **What is this guide?**
>
> This guide covers deploying a single Graphiti knowledge graph (FalkorDB + vLLM) shared across
> multiple GuardKit projects. Multiple projects store knowledge in isolated namespaces within the
> same FalkorDB instance. Both the Python client CLI and MCP server access the same underlying graph.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Multi-Project Setup with `--copy-graphiti`](#multi-project-setup-with---copy-graphiti)
- [MCP Server Sharing Across Projects](#mcp-server-sharing-across-projects)
- [Group ID Isolation Between MCP and Python Client Access](#group-id-isolation-between-mcp-and-python-client-access)
- [Embedding Dimension Alignment](#embedding-dimension-alignment)
- [Infrastructure Components](#infrastructure-components)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Architecture Overview

A single FalkorDB instance can serve multiple GuardKit projects simultaneously. Projects are
isolated using **group ID namespacing** — each project's knowledge is stored in groups prefixed
with `{project_id}__`. System-level knowledge (shared across all projects) uses unprefixed groups.

```
FalkorDB instance (whitestocks:6379)
├── product_knowledge          ← shared system group
├── command_workflows          ← shared system group
├── architecture_decisions     ← shared system group
├── guardkit__project_overview     ← guardkit project
├── guardkit__project_architecture ← guardkit project
├── myapp__project_overview        ← myapp project
└── myapp__project_architecture    ← myapp project
```

Both the **Python client** (CLI / AutoBuild) and the **MCP server** (Claude Code sessions)
connect to the same FalkorDB instance and read/write the same group IDs.

---

## Multi-Project Setup with `--copy-graphiti`

When setting up a new project that shares an existing FalkorDB instance, always use
`--copy-graphiti` during `guardkit init`:

```bash
# In your new project directory
guardkit init --copy-graphiti
```

This command:
1. Discovers the nearest parent project's `.guardkit/graphiti.yaml`
2. Copies all connection and embedding settings to the new project
3. Replaces only `project_id` with the new project's name
4. Ensures embedding model and dimensions match the existing graph

### Why `--copy-graphiti` Is Critical

Without `--copy-graphiti`, new projects default to Neo4j and OpenAI embeddings. If the shared
FalkorDB was seeded with `nomic-embed-text-v1.5` (1024 dimensions), the mismatch causes errors:

```
Error: dimension mismatch: expected 1024, got 1536
```

`--copy-graphiti` prevents this by inheriting the exact embedding configuration from an
existing working project.

### Explicit Source Selection

If auto-discovery doesn't find the right parent project:

```bash
guardkit init --copy-graphiti-from /path/to/parent/project
```

### What Gets Copied

| Setting | Copied? | Notes |
|---------|---------|-------|
| `project_id` | No | Set to new project name |
| `falkordb_host` | Yes | Same FalkorDB instance |
| `falkordb_port` | Yes | Same port |
| `embedding_provider` | Yes | Critical for dimension alignment |
| `embedding_base_url` | Yes | Same vLLM endpoint |
| `embedding_model` | Yes | Must match seeded data |
| `llm_provider` | Yes | Same LLM endpoint |
| `llm_base_url` | Yes | Same vLLM endpoint |
| `llm_model` | Yes | Same model for consistency |
| `group_ids` | No | Reset to defaults for new project |

---

## MCP Server Sharing Across Projects

The Graphiti MCP server connects to FalkorDB on a per-session basis (it's launched fresh for
each Claude Code session). Multiple projects can share the same FalkorDB infrastructure — they
just need per-project `.mcp.json` configurations pointing to the right group ID.

### Per-Project `.mcp.json`

Each project has its own `.mcp.json` that specifies the default `--group-id` for that project:

**Project A (guardkit):**
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

**Project B (myapp):**
```json
{
  "mcpServers": {
    "graphiti": {
      "command": "uvx",
      "args": [
        "--from", "graphiti-core[falkordb]",
        "graphiti-service",
        "--transport", "stdio",
        "--group-id", "myapp"
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

Both projects connect to the same `whitestocks:6379` FalkorDB. Isolation is enforced by
searching with project-specific group IDs (see below).

---

## Group ID Isolation Between MCP and Python Client Access

This is the most important aspect of shared infrastructure: ensuring the MCP server and
Python client use the same group ID format.

### The Core Difference

| Aspect | Python Client | MCP Server |
|--------|--------------|------------|
| Group ID handling | Auto-prefixes with `{project_id}__` | Pass-through (no auto-prefix) |
| `project_overview` → stored as | `guardkit__project_overview` | `project_overview` (raw) |
| `guardkit__project_overview` → stored as | `guardkit__project_overview` | `guardkit__project_overview` |

### Correct Usage Pattern

**Python client** — pass logical (unprefixed) group names:

```python
client = get_graphiti()
# Auto-prefixed: searches "guardkit__project_architecture"
results = await client.search("authentication", group_ids=["project_architecture"])
```

**MCP server** — pass fully qualified group names (with prefix):

```python
# Must include prefix explicitly
mcp__graphiti__search_nodes(
    query="authentication",
    group_ids=["guardkit__project_architecture"]  # full prefixed name
)
```

**System groups** — same for both (no prefix needed):

```python
# Python client
results = await client.search("task-work", group_ids=["command_workflows"])

# MCP server
mcp__graphiti__search_nodes(query="task-work", group_ids=["command_workflows"])
```

### Why This Works

Knowledge seeded via the Python client is stored as `guardkit__project_overview` in FalkorDB.
When MCP searches for `guardkit__project_overview`, it finds the same data. The group IDs
match exactly — just the *how* they're specified differs.

The `.claude/rules/graphiti-knowledge-graph.md` file in each project contains the correct
prefixed group IDs for MCP use, so Claude Code always uses the right names automatically.

---

## Embedding Dimension Alignment

**Critical**: All projects sharing a FalkorDB instance must use the same embedding model
and dimensions. Mixing models causes vector dimension mismatch errors.

### This Project's Configuration

| Setting | Value |
|---------|-------|
| Embedding model | `nomic-embed-text-v1.5` |
| Dimensions | 1024 |
| Provider | vLLM at `promaxgb10-41b1:8001` |

### Ensuring Alignment

**In `.guardkit/graphiti.yaml`** (Python client):

```yaml
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

**In `.mcp.json`** (MCP server):

```json
"EMBEDDER_BASE_URL": "http://promaxgb10-41b1:8001/v1",
"EMBEDDER_MODEL": "nomic-embed-text-v1.5"
```

Both must reference the same model. The `nomic-embed-text-v1.5` model via vLLM with
Matryoshka dimensions outputs 1024-dimensional vectors by default.

### What Happens If They Mismatch

If a new project uses OpenAI `text-embedding-3-small` (1536 dims) but the FalkorDB was
seeded with nomic-embed-text-v1.5 (1024 dims):

```
ValueError: Vector dimension mismatch: expected 1024, got 1536
```

Fix: Use `guardkit init --copy-graphiti` to inherit the correct embedding configuration.

---

## Infrastructure Components

The shared infrastructure for this GuardKit project consists of:

| Component | Location | Purpose |
|-----------|----------|---------|
| **FalkorDB** | `whitestocks:6379` (Synology NAS) | Graph database — stores all knowledge |
| **FalkorDB Browser UI** | `http://whitestocks:3000` | Visual graph inspection |
| **vLLM (LLM)** | `promaxgb10-41b1:8000` | Entity extraction (Qwen2.5-14B) |
| **vLLM (Embeddings)** | `promaxgb10-41b1:8001` | Vector embeddings (nomic-embed-text-v1.5) |

All components are accessed via Tailscale VPN.

### Starting FalkorDB on the NAS

```bash
ssh richardwoollcott@whitestocks
cd /volume1/guardkit/docker
sudo docker-compose -f docker-compose.falkordb.yml up -d
```

### Checking Infrastructure Status

```bash
# FalkorDB
redis-cli -h whitestocks -p 6379 ping
# → PONG

# Python client status
guardkit graphiti status

# vLLM (LLM)
curl -s http://promaxgb10-41b1:8000/health
# → {"status":"ok"}

# vLLM (Embeddings)
curl -s http://promaxgb10-41b1:8001/health
# → {"status":"ok"}
```

---

## Troubleshooting

### New project can't find seeded knowledge

Most likely cause: the new project was initialised without `--copy-graphiti` and has
different embedding settings than the shared FalkorDB.

```bash
# Check embedding model in new project
grep embedding_model .guardkit/graphiti.yaml

# Fix by re-initialising with correct settings
guardkit init --copy-graphiti-from /path/to/working/project
```

### MCP searches returning data from wrong project

Check that your MCP searches pass project-specific group IDs. Searching without group IDs
or with the wrong prefix will return data from other projects or nothing at all.

```bash
# Check your project_id
grep project_id .guardkit/graphiti.yaml
# project_id: guardkit  →  prefix is "guardkit__"
```

### Two projects seeing each other's knowledge

This should not happen if group IDs are correctly specified. If it does:

1. Verify `project_id` values are unique across projects
2. Check that MCP searches explicitly pass `group_ids` with the correct prefix
3. Verify the Python client's `project_id` in each project's `.guardkit/graphiti.yaml`

---

## See Also

- [Graphiti Claude Code Integration](graphiti-claude-code-integration.md) — Setup and operational guide
- [Graphiti Project Namespaces](graphiti-project-namespaces.md) — Namespace deep-dive
- [Graphiti MCP Setup Deep Dive](../deep-dives/mcp-integration/graphiti-mcp-setup.md) — Technical internals
- [FalkorDB NAS Deployment Runbook](falkordb-nas-deployment-runbook.md) — NAS-specific deployment
