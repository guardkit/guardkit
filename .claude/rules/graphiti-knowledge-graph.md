# Graphiti Knowledge Graph — MCP Usage Guide

> ## ⚠️ Cutover in progress: Graphiti → fleet-memory (FEAT-MEM-08, 2026-06-29)
>
> GuardKit knowledge capture is being cut over from **Graphiti/FalkorDB** to the
> **fleet-memory** pure-embeddings backend. The Graphiti path documented below is
> **legacy** — retained for the dual-write soak and as the rollback target.
>
> - **Backend flag** — `.guardkit/graphiti.yaml` → `backend: fleet_memory`. The soak
>   keeps `enabled: false`; the flag-controlled code path stays dual until the
>   operator signs off (TASK-MEM08-010).
> - **MCP tools** — `mcp__graphiti__add_memory` → `mcp__fleet_memory__memory_write_payload`;
>   `mcp__graphiti__search_*` → `mcp__fleet_memory__memory_search` (payload-shaped args,
>   not free text). `.mcp.json` server key is `fleet_memory` (stdio: `python -m fleet_memory.mcp`).
> - **CLI** — `guardkit graphiti *` is **deprecated**; use `guardkit memory *`.
> - **Rollback** — set `backend: graphiti` + `enabled: true` in `.guardkit/graphiti.yaml`
>   and restore the `graphiti` HTTP server in `.mcp.json`.

## Overview

This project has a Graphiti MCP server connected to a FalkorDB knowledge graph.
The graph contains seeded project knowledge about GuardKit architecture, workflows,
and design decisions. **You must query it with the correct group_ids to retrieve results.**

> **Access Method**: Use this file when `mcp__graphiti__search_nodes` or
> `mcp__graphiti__search_memory_facts` tools are available in your session (MCP access).
> When those tools are not available, see `.claude/rules/graphiti-knowledge.md`
> for Python client access via `graphiti-check --status`.

---

## Critical: Always Pass group_ids

Knowledge is partitioned by `group_id`. Searching without explicit `group_ids` returns
nothing or returns stale results from other sessions. **Always pass all relevant group_ids.**

---

## HTTP MCP transport: `group_id` is honoured (TASK-INF-5053)

> **Status, 2026-05-02 (TASK-INF-5053):** an earlier task (TASK-FIX-B1F7)
> reported that the HTTP MCP server at `http://promaxgb10-41b1:8004/mcp`
> silently overrode client-supplied `group_id` to `product_knowledge`.
> Verification against the running server invalidated that diagnosis —
> the server source at `/app/mcp/src/graphiti_mcp_server.py:374-375`
> uses the standard "client wins, fall back to default" pattern
> (`effective_group_id = group_id or config.graphiti.group_id`), and
> live probes confirm the response message reports the same group the
> caller sent. See `docs/state/TASK-INF-5053/audit.md` for the full
> audit trail (image SHA, source line numbers, probe response, server
> log correlation).
>
> The symptom that motivated TASK-FIX-B1F7 ("episode never appears under
> requested group on subsequent search") is real, but its root cause is
> background **LLM-extraction failure**, not group_id coercion: episodes
> are correctly routed to the requested group, then dropped by the queue
> worker because graphiti-core 0.28.1's `OpenAIClient` calls the new
> OpenAI Responses API at `api.openai.com/v1/responses` instead of the
> configured local LLM endpoint. Tracked separately as
> **TASK-INF-5054** (graphiti-mcp LLM endpoint misrouting).

**Defence-in-depth still in place.** `/task-complete` continues to
parse the MCP response message via
`installer/core/commands/lib/graphiti_response_parser.py` and fall back
to the Python CLI (`guardkit graphiti capture-outcome`) for task-outcome
writes if a divergence is ever detected. The fallback is harmless when
no divergence fires (which is the current state) and would defend
against a future regression. Do not remove it without filing a task.

**For ad-hoc inline writes,** trust the response message: it accurately
reflects the queued group. There is no need to compare requested vs
actual group_id manually. If a write does not appear in subsequent
searches scoped to the same group, the issue is almost certainly
extraction failure (TASK-INF-5054), not routing — check the server
logs on `promaxgb10-41b1` (`docker logs graphiti-mcp --tail 50`) for
`Failed to process episode ... for group <X>` lines.

---

## Group ID Reference

Knowledge is stored in two scopes:

### System Groups (no prefix — shared across all GuardKit projects)

These contain GuardKit product and system knowledge seeded by `guardkit graphiti seed-system`.

| Group ID | Contents |
|----------|----------|
| `product_knowledge` | GuardKit product context, quality gates, target users, installation |
| `command_workflows` | Slash commands, Player-Coach workflow, feature-build pipeline |
| `architecture_decisions` | ADRs (global), system decisions, design rationale |

### Project Groups (prefixed with `guardkit__` — this project only)

These contain GuardKit-project-specific context seeded by `guardkit graphiti capture`.

| Group ID | Contents |
|----------|----------|
| `guardkit__project_overview` | Project purpose, goals, problem statement |
| `guardkit__project_architecture` | Component structure, services, data flow |
| `guardkit__project_decisions` | Project-level technical decisions and ADRs |
| `guardkit__feature_specs` | Feature specifications and requirements |
| `guardkit__task_outcomes` | Task completion outcomes and lessons learned |
| `guardkit__turn_states` | Feature-build turn state history |

> **Convention: no hyphens in group IDs.** Always use underscores in project IDs
> and group IDs (e.g. `specialist_agent`, not `specialist-agent`). Hyphens break
> FalkorDB's RediSearch fulltext queries — see `guardkit/docs/fixes/migrate-hyphens.py`
> for details. This applies to all repos, not just GuardKit.

> **Why the prefix?** The `guardkit__` prefix ensures isolation when multiple projects
> share the same FalkorDB instance. Each project's knowledge stays in its own namespace.
> System groups are intentionally shared — they contain GuardKit product knowledge
> that all projects benefit from.
>
> **No hyphens.** Use underscores only — hyphens break RediSearch fulltext queries.

---

## Standard Search Pattern

Use both search tools together and pass all relevant group_ids:

```python
# Search all GuardKit knowledge
# NOTE: Never use hyphens in group_ids — they break FalkorDB RediSearch queries.
group_ids = [
    # System groups (GuardKit product knowledge)
    "product_knowledge",
    "command_workflows",
    "architecture_decisions",
    # Project groups (this project's specific context)
    "guardkit__project_overview",
    "guardkit__project_architecture",
    "guardkit__project_decisions",
]
```

### Search Tools

- `mcp__graphiti__search_nodes` — finds entities (concepts, components, roles, commands)
- `mcp__graphiti__search_memory_facts` — finds relationships and facts between entities

Run both together for comprehensive results. Narrow `group_ids` only when you know which
group contains the information.

---

## Adding Knowledge via MCP

When using `mcp__graphiti__add_memory`, choose the group_id based on content type:

**System knowledge** (GuardKit product/system level — shared across all projects):
- `group_id: "product_knowledge"` — GuardKit capabilities, features, user guides
- `group_id: "command_workflows"` — command usage patterns, workflow examples
- `group_id: "architecture_decisions"` — global ADRs, cross-project design decisions

**Project-specific knowledge** (GuardKit project — isolated to this project):
- `group_id: "guardkit__project_architecture"` — component/service structure
- `group_id: "guardkit__project_decisions"` — technical decisions specific to this project
- `group_id: "guardkit__feature_specs"` — in-progress feature context

> **Isolation rule**: Always use `guardkit__` prefixed group IDs for project-specific data.
> This prevents knowledge from leaking into other projects that share the same FalkorDB.
> Do NOT use bare group names (like `project_architecture` without prefix) for project-specific
> knowledge — those would be misclassified as system groups and shared across all projects.

---

## Configuration Reference

- Server config: see `.mcp.json` for MCP server launch configuration
- Project config: see `.guardkit/graphiti.yaml` for group_ids and infrastructure
- Graph database: FalkorDB at `whitestocks:6379` (Synology NAS via Tailscale)
- LLM backend: llama-swap at `promaxgb10-41b1:9000` (alias `qwen-graphiti` = Qwen2.5-14B-Instruct Q8_0 for extraction, served by llama.cpp)
- Embedding: llama-swap at `promaxgb10-41b1:9000` (alias `nomic-embed` = nomic-embed-text-v1.5 F16, **768 dims**)
  - > **Updated 2026-06-21:** the standalone vLLM servers on `:8000`/`:8001` were retired in the 2026-04-29 all-llama.cpp consolidation (RESULTS-v2) — both the LLM and the embedder are now served by the single llama-swap front door on `:9000`. The model identities are unchanged (Qwen2.5-14B; nomic-embed-text-v1.5); only the substrate (vLLM→llama.cpp) and port changed. The embedding dimension is **768**, not 1024 — `.guardkit/graphiti.yaml` already encodes this; a config claiming 1024 silently corrupts Graphiti writes.
- **No hyphens in group_ids** — use underscores only (hyphens break RediSearch)
