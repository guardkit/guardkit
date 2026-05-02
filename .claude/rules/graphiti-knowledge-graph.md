# Graphiti Knowledge Graph — MCP Usage Guide

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

## Known transport limitation: HTTP MCP coerces write `group_id` (TASK-FIX-B1F7)

The HTTP MCP transport at `http://promaxgb10-41b1:8004/mcp` accepts a
`group_id` parameter on `mcp__graphiti__add_memory` calls but silently
overrides it with the server-side default (typically `product_knowledge`).
**Search calls (`search_nodes`, `search_memory_facts`) honour `group_ids`
correctly** — only writes are affected.

**Detection.** The MCP response message reveals the actual group used:

```
Episode 'X' queued for processing in group 'product_knowledge'
                                            ^^^^^^^^^^^^^^^^^
                                            actual group, may differ
                                            from what was requested
```

`/task-complete` parses this string via
`installer/core/commands/lib/graphiti_response_parser.py` and falls back
to the Python CLI (`guardkit graphiti capture-outcome`) for task-outcome
writes when override is detected. CLI writes use the Python
`GraphitiClient` directly and respect `group_id`.

**Workaround for ad-hoc writes** (outside `/task-complete`):

- Prefer the CLI for any write that must land in a specific group:
  `guardkit graphiti capture-outcome --from-task-file <path> --timeout 300`.
- For inline `mcp__graphiti__add_memory` calls, inspect the response
  message after each write — if the actual group differs from the
  requested group, the write landed in the wrong namespace and future
  scoped searches will not find it.

**Status.** This is an upstream `graphiti-mcp` HTTP-server issue (not in
this repo's `infra/`; the server runs on `promaxgb10-41b1`). A separate
infra task should configure the server to honour client-supplied
`group_id` or patch the upstream server to forward the parameter.

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
- LLM backend: vLLM at `promaxgb10-41b1:8000` (Qwen2.5-14B for extraction)
- Embedding: vLLM at `promaxgb10-41b1:8001` (nomic-embed-text-v1.5, 1024 dims)
- **No hyphens in group_ids** — use underscores only (hyphens break RediSearch)
