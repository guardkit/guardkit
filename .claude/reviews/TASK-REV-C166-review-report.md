# Review Report: TASK-REV-C166

## Executive Summary

The agentic-dataset-factory project has a working Graphiti + Claude Code integration using the **Graphiti MCP server** via `.mcp.json`. GuardKit currently uses a **Python client library** for Graphiti access. The two approaches serve different purposes: MCP gives Claude Code direct, interactive access to the knowledge graph during conversations; the Python client gives GuardKit CLI commands programmatic access for seeding, querying, and workflow automation.

**Recommendation**: GuardKit should support **both approaches** — keep the Python client for CLI/programmatic use, and add MCP server configuration via `guardkit init` for Claude Code session integration. The infrastructure is already shared; only configuration files need to be templated.

**Complexity**: Low-Medium. No new code required for basic enablement — only configuration templating and documentation.

## Review Details

- **Mode**: Architectural / Decision Analysis
- **Depth**: Standard
- **Task**: TASK-REV-C166
- **Reviewer**: Manual source analysis across guardkit and agentic-dataset-factory repos

---

## Finding 1: How Graphiti Works in agentic-dataset-factory Claude Code Sessions

### MCP Server Configuration

The integration is entirely configuration-driven via four files:

**1. `.mcp.json`** (Claude Code MCP server launch config):
```json
{
  "mcpServers": {
    "graphiti": {
      "type": "stdio",
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "--directory", "/path/to/graphiti/mcp_server",
        "run", "main.py",
        "--transport", "stdio",
        "--config", "/path/to/graphiti/mcp_server/config/config-guardkit.yaml"
      ],
      "env": {
        "CONFIG_PATH": "/path/to/graphiti/mcp_server/config/config-guardkit.yaml",
        "OPENAI_API_KEY": "not-needed-vllm-local",
        "LLM_API_URL": "http://promaxgb10-41b1:8000/v1",
        "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1",
        "EMBEDDING_DIM": "1024"
      }
    }
  }
}
```

**2. `.claude/CLAUDE.md`** — instructs Claude Code that Graphiti is available and to always pass `group_ids` when searching.

**3. `.claude/rules/graphiti-knowledge-graph.md`** — detailed usage rules (auto-loaded by Claude Code):
- Which MCP tools to use (`mcp__graphiti__search_nodes`, `mcp__graphiti__search_memory_facts`)
- Critical rule: always pass all three group_ids or searches return empty
- Group ID contents reference

**4. `.guardkit/graphiti.yaml`** — project-level config (shared with Python client).

### How Knowledge is Captured and Retrieved

- **Capture**: Knowledge is seeded into the graph via `guardkit graphiti add-context` (Python client CLI) or directly through MCP `add_episode` calls during Claude Code sessions.
- **Retrieval**: Claude Code uses `mcp__graphiti__search_nodes` and `mcp__graphiti__search_memory_facts` tools. The rules file instructs it to always include all group_ids.
- **No hooks trigger automatic capture** — it's manual or command-driven.

### MCP Server Config (Shared)

The MCP server uses `config-guardkit.yaml` at `/path/to/graphiti/mcp_server/config/`:
- LLM: Qwen2.5-14B via vLLM (port 8000), max_tokens: 4096
- Embeddings: nomic-embed-text-v1.5 via vLLM (port 8001), dimensions: 1024
- Database: FalkorDB at whitestocks:6379
- Group ID: "guardkit" (hardcoded in server config)

---

## Finding 2: MCP vs Python Client — Comparison

| Aspect | MCP Server (agentic-dataset-factory) | Python Client (GuardKit) |
|--------|--------------------------------------|--------------------------|
| **Access method** | Claude Code calls MCP tools directly | CLI commands invoke Python API |
| **Interactive use** | Claude can search/add during conversation | Only via `/guardkit graphiti ...` commands |
| **Configuration** | `.mcp.json` + server YAML | `.guardkit/graphiti.yaml` |
| **Group ID handling** | Passed per-call, must be explicit | Auto-prefixed with project_id |
| **Project isolation** | Single `group_id` in server config | `project_id__` prefix on all groups |
| **Seeding** | Manual via MCP add_episode | `guardkit graphiti seed` / `add-context` |
| **Error handling** | MCP server handles retries | Circuit breaker, retry with backoff |
| **FalkorDB workarounds** | None (uses graphiti-core as-is) | 3 monkey-patches (single-group bug, fulltext, edge O(n)) |
| **Offline graceful degradation** | MCP server fails to start; Claude loses tools | Python client returns empty; commands continue |

### Key Insight: Complementary, Not Competing

The two approaches serve different use cases:

- **MCP**: Gives Claude Code **real-time, interactive** access to the knowledge graph. Claude can search for context mid-conversation, add episodes from discussion, and retrieve facts to inform responses.
- **Python client**: Gives GuardKit CLI commands **programmatic** access for bulk seeding, structured queries, workflow automation, and quality gate integration.

A project benefits from having **both**:
- MCP for Claude Code sessions (interactive knowledge retrieval)
- Python client for CLI workflows (seeding, batch operations, phase integrations)

---

## Finding 3: Project Isolation with Shared FalkorDB

### Current Isolation Mechanisms

**Python Client (GuardKit)**:
- `GraphitiClient.get_group_id()` auto-prefixes every group ID with `{project_id}__`
- Example: `guardkit__product_knowledge`, `agentic-dataset-factory__product_knowledge`
- System groups (shared across projects) have no prefix
- Isolation is **automatic and enforced** at the client level

**MCP Server (agentic-dataset-factory)**:
- Server config has `group_id: "guardkit"` — this is a **static, single group ID**
- No automatic project-level prefixing
- All data written via MCP goes into the `guardkit` group, not project-namespaced groups

### Isolation Gap

There is a **mismatch** between how the Python client and MCP server handle project isolation:

| Operation | Python Client | MCP Server |
|-----------|---------------|------------|
| Write to `product_knowledge` | `guardkit__product_knowledge` | `guardkit` (server-level group) |
| Search `product_knowledge` | Searches `guardkit__product_knowledge` | Searches `guardkit` (or explicit group_ids) |

This means:
1. Knowledge seeded via Python client is **not visible** to MCP searches (different group IDs)
2. Knowledge added via MCP goes into the server-level group, not project-prefixed groups
3. If two projects share the same MCP server config, their MCP-written data would collide

### Mitigation Options

**Option A**: Configure MCP server `group_id` to match the Python client's prefixed format (e.g., `guardkit__product_knowledge`). Requires per-project MCP server configs.

**Option B**: Create a per-project MCP server config file that includes the project_id prefix. `guardkit init` generates this automatically.

**Option C**: Modify the Graphiti MCP server to support project_id prefixing natively (upstream contribution).

**Recommendation**: **Option B** — generate per-project MCP server configs during `guardkit init`. This aligns with the existing `--copy-graphiti` pattern and keeps isolation consistent.

---

## Finding 4: Configuration Requirements for Claude Code + Graphiti

To enable Graphiti in any GuardKit-enabled repo's Claude Code sessions, the following files are needed:

### Required Files

| File | Purpose | Can Template? |
|------|---------|---------------|
| `.mcp.json` | Launch MCP server for Claude Code | Yes — paths and project_id vary |
| `.claude/rules/graphiti-knowledge-graph.md` | Usage rules for Claude Code | Yes — group_ids vary per project |
| `.guardkit/graphiti.yaml` | Project config (already exists) | Already templated via `guardkit init` |

### Already Exists (No Change Needed)

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Brief mention + pointer to rules file |
| `.guardkit/graphiti.yaml` | Full Python client config |

### External Dependencies

| Dependency | Location | Notes |
|------------|----------|-------|
| Graphiti MCP server code | `~/Projects/appmilla_github/graphiti/mcp_server/` | Shared installation, not per-project |
| `uv` | `/opt/homebrew/bin/uv` | Package manager for running MCP server |
| Per-project MCP server config | `graphiti/mcp_server/config/config-{project_id}.yaml` | Currently only `config-guardkit.yaml` exists |

---

## Finding 5: LLM/Embedding Compatibility

### Current State

Both projects use identical LLM and embedding configurations:

| Setting | GuardKit | agentic-dataset-factory |
|---------|----------|------------------------|
| LLM model | Qwen2.5-14B-Instruct-FP8 | Same |
| LLM endpoint | promaxgb10-41b1:8000 | Same |
| Embedding model | nomic-embed-text-v1.5 | Same |
| Embedding endpoint | promaxgb10-41b1:8001 | Same |
| Embedding dimensions | 768 (Python client) / 1024 (MCP config) | Same |
| max_tokens | 4096 | 4096 |

### Dimension Discrepancy

There is a **potential dimension mismatch**:
- MCP server config specifies `EMBEDDING_DIM: "1024"` and `dimensions: 1024`
- The nomic-embed-text-v1.5 model supports multiple dimensions (768 default, up to 1024 with Matryoshka)
- GuardKit's Python client doesn't explicitly set dimensions — relies on model default

**Risk**: If the MCP server creates embeddings at 1024 dimensions and the Python client creates at 768 dimensions, vector search across both will produce incorrect results.

**Mitigation**: Add explicit `embedding_dimensions` to `.guardkit/graphiti.yaml` and ensure both MCP server config and Python client use the same value. The `--copy-graphiti` flag already handles this for Python client configs.

---

## Finding 6: Installer Integration Assessment

### What `guardkit init` Should Do

Currently `guardkit init`:
1. Creates `.guardkit/graphiti.yaml` with project-specific settings
2. Supports `--copy-graphiti` to inherit settings from parent project
3. Seeds project knowledge (Phase 1 seeding)

To add Claude Code MCP integration, `guardkit init` should additionally:

1. **Generate `.mcp.json`** (or merge into existing):
   - Detect Graphiti MCP server installation path
   - Use project_id from `.guardkit/graphiti.yaml`
   - Point to per-project server config (or generate one)

2. **Generate `.claude/rules/graphiti-knowledge-graph.md`**:
   - Template with project-specific group_ids
   - Include search instructions and tool references

3. **Generate per-project MCP server config** (or use shared):
   - Copy from template, replacing project_id and group_ids
   - Store at known location (e.g., `graphiti/mcp_server/config/config-{project_id}.yaml`)

### Blockers and Prerequisites

| Blocker | Severity | Notes |
|---------|----------|-------|
| Graphiti MCP server must be installed locally | Medium | Not a pip dependency — separate repo clone |
| `uv` must be installed | Low | Standard Python tooling |
| MCP server path varies per machine | Medium | Need discovery or config |
| Per-project MCP server config needed | Low | Template generation |
| Embedding dimension alignment | Medium | Must be explicit in both configs |
| FalkorDB must be reachable | Low | Already a prerequisite |

---

## Recommendations

### Recommendation 1: Add MCP Configuration to `guardkit init` (Priority: High)

**What**: Extend `guardkit init` to optionally generate `.mcp.json` and `.claude/rules/graphiti-knowledge-graph.md`.

**How**:
- New flag: `guardkit init --with-mcp` (or auto-detect if Graphiti MCP server is installed)
- Generate `.mcp.json` with correct paths
- Generate Claude Code rules file from template
- Merge into existing `.mcp.json` if present (don't overwrite other MCP servers)

**Effort**: 2-3 days (templating + path discovery + merge logic)

### Recommendation 2: Resolve Group ID Isolation Gap (Priority: High)

**What**: Ensure MCP server and Python client use consistent group ID namespacing.

**How**:
- Generate per-project MCP server configs with `group_id: "{project_id}"`
- Update `.claude/rules/graphiti-knowledge-graph.md` template to reference project-prefixed group IDs
- Document that MCP searches should use the same group_ids as `graphiti.yaml`

**Effort**: 1 day (config generation + documentation)

### Recommendation 3: Fix Embedding Dimension Alignment (Priority: Medium)

**What**: Make embedding dimensions explicit and consistent across MCP and Python client.

**How**:
- Add `embedding_dimensions: 1024` to `.guardkit/graphiti.yaml` schema
- Ensure `--copy-graphiti` copies this field
- Validate dimension consistency during `guardkit init`

**Effort**: 0.5 days

### Recommendation 4: Document the Dual-Access Architecture (Priority: Medium)

**What**: Create a guide explaining MCP vs Python client, when each is used, and how isolation works.

**How**:
- Add `docs/guides/graphiti-claude-code-integration.md`
- Cover: setup, configuration, isolation, troubleshooting
- Reference from CLAUDE.md and graphiti-knowledge.md

**Effort**: 0.5 days

### Recommendation 5: Template the Rules File (Priority: Low)

**What**: Create a `.claude/rules/graphiti-knowledge-graph.md` template in the installer.

**How**:
- Add template to `installer/core/templates/`
- Support `{{project_id}}`, `{{group_ids}}` placeholders
- Generate during `guardkit init --with-mcp`

**Effort**: 0.5 days

---

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| 1. MCP config in `guardkit init` | High | Medium (2-3d) | Low | **Do first** |
| 2. Group ID isolation fix | High | Low (1d) | Low | **Do first** |
| 3. Embedding dimension alignment | Medium | Low (0.5d) | Medium | Do second |
| 4. Documentation | Medium | Low (0.5d) | None | Do second |
| 5. Rules file template | Low | Low (0.5d) | None | Do with #1 |

**Total estimated effort**: 4-5 days for complete implementation.

---

## Appendix A: File Inventory

### agentic-dataset-factory (Reference)

| File | Purpose |
|------|---------|
| `.mcp.json` | MCP server launch config for Claude Code |
| `.guardkit/graphiti.yaml` | Project Graphiti config (Python client + shared settings) |
| `.claude/CLAUDE.md` | Project instructions mentioning Graphiti |
| `.claude/rules/graphiti-knowledge-graph.md` | Detailed search/usage rules for Claude Code |
| `docs/reviews/graphiti-setup/graphiti-mcp-claude-code-setup.md` | Setup guide |

### GuardKit (Current)

| File | Purpose |
|------|---------|
| `.guardkit/graphiti.yaml` | Project Graphiti config (Python client) |
| `.claude/rules/graphiti-knowledge.md` | Python client usage rules |
| `guardkit/knowledge/graphiti_client.py` | Python client (2,423 lines) |
| `guardkit/knowledge/config.py` | Config loading |
| `guardkit/knowledge/falkordb_workaround.py` | FalkorDB patches |
| `installer/core/commands/lib/graphiti-preamble.md` | Command availability check guide |

### GuardKit (Needed for MCP Integration)

| File | Purpose | Source |
|------|---------|--------|
| `.mcp.json` | MCP server launch config | Generated by `guardkit init --with-mcp` |
| `.claude/rules/graphiti-knowledge-graph.md` | MCP search rules for Claude Code | Template in installer |
| Per-project MCP server config | Server-side config | Generated by `guardkit init --with-mcp` |

## Appendix B: Infrastructure Topology

```
┌─────────────────────────────────────────────────────────┐
│ Developer Machine (macOS)                                │
│                                                          │
│  ┌──────────────┐    ┌──────────────────┐               │
│  │ Claude Code   │    │ GuardKit CLI     │               │
│  │ (VS Code ext) │    │ (guardkit ...)   │               │
│  │               │    │                  │               │
│  │ Uses: MCP     │    │ Uses: Python     │               │
│  │ tools         │    │ client           │               │
│  └──────┬───────┘    └────────┬─────────┘               │
│         │                     │                          │
│  ┌──────▼───────┐            │                          │
│  │ Graphiti MCP  │            │                          │
│  │ Server (stdio)│            │                          │
│  │ via uv        │            │                          │
│  └──────┬───────┘            │                          │
│         │                     │                          │
│         └──────────┬──────────┘                          │
│                    │ (both use same LLM/embedding)       │
└────────────────────┼────────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │ promaxgb10-41b1         │
        │ :8000 vLLM (Qwen2.5)   │
        │ :8001 vLLM (nomic-embed)│
        └─────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │ whitestocks (NAS)       │
        │ :6379 FalkorDB          │
        │ :3000 FalkorDB UI       │
        └─────────────────────────┘
```
