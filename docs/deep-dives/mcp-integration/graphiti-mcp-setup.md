# Graphiti MCP Setup — Technical Deep Dive

> **Who is this for?**
>
> This guide is for developers who want to understand the internals of the Graphiti MCP server
> integration: how it's configured, how it connects to FalkorDB and vLLM, and how it relates
> to the Python client. For a task-oriented setup guide, see
> [Graphiti Claude Code Integration](../../guides/graphiti-claude-code-integration.md).

---

## Table of Contents

- [MCP Server Architecture](#mcp-server-architecture)
- [Per-Project Configuration](#per-project-configuration)
- [`.mcp.json` Schema Reference](#mcpjson-schema-reference)
- [MCP Server Config YAML Reference](#mcp-server-config-yaml-reference)
- [Environment Variables](#environment-variables)
- [How the MCP Server Connects to FalkorDB and vLLM](#how-the-mcp-server-connects-to-falkordb-and-vllm)
- [Comparison with Python Client Internals](#comparison-with-python-client-internals)
- [Available MCP Tools](#available-mcp-tools)
- [Troubleshooting](#troubleshooting)

---

## MCP Server Architecture

The Graphiti MCP server is a Python process launched by Claude Code via the `.mcp.json`
configuration. It runs as a subprocess on the developer's machine (using `stdio` transport)
and acts as a bridge between Claude Code's MCP tool calls and the FalkorDB knowledge graph.

```
Claude Code session
        │
        │  MCP protocol (stdio)
        ▼
Graphiti MCP Server (Python subprocess)
        │
        ├── vLLM / LLM endpoint  ← entity extraction
        ├── vLLM / Embeddings endpoint  ← vector embeddings
        │
        └── FalkorDB  ← graph storage
```

The MCP server is provided by the `graphiti-core` Python package. It exposes tools for
searching and adding knowledge to the graph. Claude Code calls these tools during sessions
to retrieve context and persist new knowledge.

### Transport Mode

The server uses `stdio` transport: Claude Code writes JSON-RPC requests to the server's
stdin and reads responses from stdout. This means:

- The server process is started fresh each Claude Code session
- No persistent server daemon required
- Configuration changes take effect on next Claude Code restart
- Logs go to stderr (visible in Claude Code's MCP output panel)

---

## Per-Project Configuration

Each GuardKit project gets its own MCP configuration, primarily differing in:

1. **Group IDs** — which knowledge namespace to search/write to
2. **Project ID** — used as prefix for project-specific groups

The `.mcp.json` in each project root tells Claude Code how to launch the server and which
FalkorDB/vLLM endpoints to use.

### Configuration Generation

The recommended way to set up MCP configuration is via `guardkit init --copy-graphiti`:

```bash
guardkit init --copy-graphiti
```

This inherits connection settings (FalkorDB host, embedding model, dimensions) from a
parent project, replacing only the `project_id`. It prevents the most common
misconfiguration: embedding dimension mismatch.

You then manually add the MCP server block to `.mcp.json` or create the file:

```json
{
  "mcpServers": {
    "graphiti": {
      "command": "uvx",
      "args": [
        "--from", "graphiti-core[falkordb]",
        "graphiti-service",
        "--transport", "stdio",
        "--group-id", "my-project"
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

> **Note**: If your project already has a `.mcp.json` for other MCP servers (Context7,
> Design Patterns), add the `"graphiti"` key to the existing `mcpServers` object rather
> than replacing the whole file.

---

## `.mcp.json` Schema Reference

The `.mcp.json` file configures all MCP servers for a Claude Code project. The Graphiti
server block follows this schema:

```json
{
  "mcpServers": {
    "graphiti": {
      "command": "uvx",
      "args": [
        "--from", "graphiti-core[falkordb]",
        "graphiti-service",
        "--transport", "stdio",
        "--group-id", "<project-group-id>"
      ],
      "env": {
        "FALKORDB_HOST": "<host>",
        "FALKORDB_PORT": "<port>",
        "OPENAI_API_KEY": "<not-needed-for-vllm>",
        "LLM_BASE_URL": "<vllm-llm-endpoint>",
        "LLM_MODEL": "<model-name>",
        "EMBEDDER_BASE_URL": "<vllm-embedding-endpoint>",
        "EMBEDDER_MODEL": "<embedding-model-name>"
      }
    }
  }
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `command` | Yes | Executable to launch. Use `uvx` (recommended) or absolute path to `uv`. |
| `args[--from]` | Yes | Package source. `graphiti-core[falkordb]` installs from PyPI with FalkorDB support. |
| `args[graphiti-service]` | Yes | Entry point for the MCP server. |
| `args[--transport]` | Yes | Transport mode. Always `stdio` for Claude Code. |
| `args[--group-id]` | Yes | Default group ID for this server. Should match the project's namespace. |
| `env.FALKORDB_HOST` | Yes | Hostname or IP of the FalkorDB instance. |
| `env.FALKORDB_PORT` | Yes | FalkorDB port (default: `6379`). |
| `env.OPENAI_API_KEY` | Yes | Required by graphiti-core even when not using OpenAI. Set to any non-empty string. |
| `env.LLM_BASE_URL` | No | Base URL for LLM API (vLLM or OpenAI-compatible). Omit to use OpenAI. |
| `env.LLM_MODEL` | No | LLM model name for entity extraction. |
| `env.EMBEDDER_BASE_URL` | No | Base URL for embedding API. Omit to use OpenAI. |
| `env.EMBEDDER_MODEL` | No | Embedding model name. **Must match** the model used to seed the database. |

### Group ID Naming Convention

The `--group-id` argument sets the **default** group for `add_memory` calls. For
Claude Code sessions in a GuardKit project, this should be the project-specific group
(e.g., `guardkit` or `my-project`).

When **searching**, always pass explicit `group_ids` to the MCP tools — the default
`--group-id` does not affect search scope. See `.claude/rules/graphiti-knowledge-graph.md`
in the project root for the complete group ID reference.

---

## MCP Server Config YAML Reference

An alternative to environment variables is a YAML config file. This is used in some
configurations where the MCP server is launched with a `--config` argument:

```yaml
# graphiti/mcp_server/config/config-my-project.yaml

# Graph database
graph_store:
  type: falkordb
  host: whitestocks
  port: 6379

# LLM for entity extraction
llm:
  provider: openai  # openai-compatible API
  model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
  base_url: http://promaxgb10-41b1:8000/v1
  max_tokens: 4096

# Embedding model
embedder:
  provider: openai  # openai-compatible API
  model: nomic-embed-text-v1.5
  base_url: http://promaxgb10-41b1:8001/v1
  dimensions: 1024

# Default group ID for this project
group_id: my-project
```

> **Tip**: The environment variable approach in `.mcp.json` is simpler for most projects —
> it keeps all configuration in one place without requiring a separate config file.

---

## Environment Variables

When using environment variables in `.mcp.json`, these are the available settings:

| Variable | Purpose | Example |
|----------|---------|---------|
| `FALKORDB_HOST` | FalkorDB hostname | `whitestocks` |
| `FALKORDB_PORT` | FalkorDB port | `6379` |
| `OPENAI_API_KEY` | Required by graphiti-core (set any value for local vLLM) | `not-used` |
| `LLM_BASE_URL` | OpenAI-compatible LLM base URL | `http://promaxgb10-41b1:8000/v1` |
| `LLM_MODEL` | LLM model for entity extraction | `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` |
| `EMBEDDER_BASE_URL` | OpenAI-compatible embedding base URL | `http://promaxgb10-41b1:8001/v1` |
| `EMBEDDER_MODEL` | Embedding model name | `nomic-embed-text-v1.5` |
| `CONFIG_PATH` | Path to YAML config file (alternative to env vars) | `/path/to/config.yaml` |

### Local vs Remote LLM

The MCP server uses OpenAI-compatible API endpoints. This means you can use either:

- **OpenAI directly**: Set `OPENAI_API_KEY` to a real key and omit `LLM_BASE_URL` and `EMBEDDER_BASE_URL`
- **Local vLLM**: Set `LLM_BASE_URL` and `EMBEDDER_BASE_URL` to your vLLM endpoints and set `OPENAI_API_KEY` to any non-empty string

The GuardKit project uses local vLLM at `promaxgb10-41b1` for both LLM and embeddings.

---

## How the MCP Server Connects to FalkorDB and vLLM

When Claude Code launches the MCP server, the startup sequence is:

```
1. Claude Code reads .mcp.json
2. Claude Code spawns: uvx --from graphiti-core[falkordb] graphiti-service --transport stdio
3. MCP server starts, reads env vars from .mcp.json
4. MCP server initialises graphiti-core with FalkorDB backend
5. graphiti-core connects to FalkorDB at FALKORDB_HOST:FALKORDB_PORT
6. MCP server registers tools: add_memory, search_memory_facts, search_nodes, etc.
7. MCP server signals ready to Claude Code via stdio
8. Claude Code shows mcp__graphiti__* tools as available
```

### Connection Flow for a Search Query

When Claude Code calls `mcp__graphiti__search_nodes`:

```
Claude Code → MCP tool call → MCP server
                                   │
                                   ├── Embed query text
                                   │     └── POST to EMBEDDER_BASE_URL
                                   │         (nomic-embed-text-v1.5, 1024 dims)
                                   │
                                   ├── Graph search in FalkorDB
                                   │     └── Redis protocol to FALKORDB_HOST:PORT
                                   │         Filters by group_ids parameter
                                   │
                                   └── Returns results → Claude Code
```

### Connection Flow for add_memory

When Claude Code calls `mcp__graphiti__add_memory`:

```
Claude Code → MCP tool call → MCP server
                                   │
                                   ├── Extract entities/facts via LLM
                                   │     └── POST to LLM_BASE_URL
                                   │         (Qwen2.5-14B, entity extraction)
                                   │
                                   ├── Embed episode text
                                   │     └── POST to EMBEDDER_BASE_URL
                                   │
                                   └── Write to FalkorDB
                                         └── Redis protocol to FALKORDB_HOST:PORT
                                             group_id = --group-id arg from .mcp.json
```

---

## Comparison with Python Client Internals

Both the MCP server and Python client (`guardkit.knowledge.GraphitiClient`) connect to the
same FalkorDB instance but differ in several implementation details:

| Aspect | MCP Server | Python Client |
|--------|-----------|---------------|
| **Entry point** | `graphiti-core` MCP server process | `guardkit.knowledge.GraphitiClient` |
| **Lifecycle** | Started per Claude Code session | Created per-thread, persists for session |
| **Group ID handling** | Pass-through — no auto-prefix | Auto-prefixes with `{project_id}__` |
| **FalkorDB connection** | Direct from MCP process | Direct from Python process |
| **Embedding pipeline** | Built into `graphiti-core` | Built into `guardkit.knowledge` |
| **FalkorDB workarounds** | None — uses `graphiti-core` as-is | 3 monkey-patches applied |
| **Error handling** | MCP errors surface to Claude Code | Circuit breaker + retry with backoff |
| **Offline behavior** | Tools unavailable (MCP start fails) | Graceful degradation, returns empty |

### FalkorDB Workarounds

The Python client applies three monkey-patches to `graphiti-core` to work around FalkorDB
compatibility issues:

1. **Single-group search bug**: FalkorDB fails when searching exactly one group ID.
   The workaround pads single-group queries with a sentinel group.

2. **Full-text index**: Workaround for FalkorDB full-text search query syntax differences.

3. **Edge O(n) performance**: Optimisation for relationship lookups that would otherwise
   scan all edges.

The MCP server does not apply these workarounds. If you encounter issues with MCP searches
returning empty results or errors, try the same query via the Python client CLI to compare:

```bash
guardkit graphiti search "your query" --group product_knowledge
```

### Group ID Prefix Differences

This is the most important operational difference:

```python
# Python client: auto-prefixes project groups
client.search(group_ids=["project_overview"])
# → searches group: "guardkit__project_overview"

# MCP server: pass-through (no prefix added)
mcp__graphiti__search_nodes(group_ids=["project_overview"])
# → searches group: "project_overview" (WRONG — will return nothing)

# MCP server: must pass fully qualified group ID
mcp__graphiti__search_nodes(group_ids=["guardkit__project_overview"])
# → searches group: "guardkit__project_overview" (CORRECT)
```

The `.claude/rules/graphiti-knowledge-graph.md` file contains the correct full group IDs
for this project so Claude Code uses them correctly.

---

## Available MCP Tools

Once the MCP server is running, these tools become available in Claude Code sessions:

| Tool | Purpose |
|------|---------|
| `mcp__graphiti__search_nodes` | Search for entities in the knowledge graph |
| `mcp__graphiti__search_memory_facts` | Search for relationships and facts between entities |
| `mcp__graphiti__add_memory` | Add a new episode to the knowledge graph |
| `mcp__graphiti__get_memory` | Retrieve a specific memory by ID |
| `mcp__graphiti__delete_memory` | Delete a memory from the graph |

### Usage Pattern

Always pass `group_ids` to search tools. Without explicit group IDs, searches return
no results (FalkorDB partitioning behaviour):

```python
# Search for entities (always with group_ids)
mcp__graphiti__search_nodes(
    query="authentication patterns",
    group_ids=["product_knowledge", "guardkit__project_architecture"]
)

# Search for facts/relationships
mcp__graphiti__search_memory_facts(
    query="how does the Python client handle group IDs",
    group_ids=["command_workflows", "guardkit__project_decisions"]
)

# Add knowledge (group_id comes from --group-id arg in .mcp.json)
mcp__graphiti__add_memory(
    name="architecture-decision-2026-03",
    episode_body="Decided to use dual-access pattern for Graphiti..."
)
```

See `.claude/rules/graphiti-knowledge-graph.md` in the project root
for the complete group ID reference for this project.

---

## Troubleshooting

### MCP tools not appearing in session

1. Verify `.mcp.json` is in the project root (same directory as `CLAUDE.md`)
2. Restart Claude Code after modifying `.mcp.json`
3. Check `uvx` is installed: `which uvx` (install with `pip install uv` if missing)
4. Check Claude Code's MCP output panel (View → Output → MCP Logs) for errors

### Server starts but searches return empty results

1. Always pass explicit `group_ids` to search tools
2. Verify group IDs use the correct prefix (`guardkit__` for project groups)
3. Confirm knowledge was seeded: `guardkit graphiti status`
4. Check FalkorDB is reachable: `redis-cli -h whitestocks -p 6379 ping`

### Embedding dimension errors on add_memory

The `EMBEDDER_MODEL` in `.mcp.json` must match the model that seeded the existing data.
Check `.guardkit/graphiti.yaml` for the `embedding_model` setting and ensure they match:

```bash
grep embedding_model .guardkit/graphiti.yaml
# embedding_model: nomic-embed-text-v1.5

# .mcp.json should have:
# "EMBEDDER_MODEL": "nomic-embed-text-v1.5"
```

### `uvx` not found

Install `uv` (which provides `uvx`):
```bash
pip install uv
# or
brew install uv
```

Then restart your terminal and Claude Code.

---

## See Also

- [Graphiti Claude Code Integration Guide](../../guides/graphiti-claude-code-integration.md) — Setup and operational guide
- [Graphiti Project Namespaces](../../guides/graphiti-project-namespaces.md) — Multi-project isolation
- [Context7 Setup](context7-setup.md) — Companion MCP for library documentation
- [MCP Optimization](mcp-optimization.md) — Performance tuning for MCP servers
- `.claude/rules/graphiti-knowledge-graph.md` — Group IDs and search patterns for this project
