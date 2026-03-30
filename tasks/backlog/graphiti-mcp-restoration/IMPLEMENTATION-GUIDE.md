# Implementation Guide: Graphiti MCP Restoration

## Feature: FEAT-GMR
## Parent Review: TASK-REV-85E4

## Wave Execution Strategy

### Wave 1: Restore MCP (3 tasks, parallel via Conductor)

**Goal**: Get MCP tools available in guardkit Claude Code sessions.

| Task | Workspace | Method | Est. |
|------|-----------|--------|------|
| TASK-GMR-001: Restore .mcp.json | graphiti-mcp-restoration-wave1-1 | task-work | 15min |
| TASK-GMR-002: Reverse anti-MCP instruction | graphiti-mcp-restoration-wave1-2 | task-work | 15min |
| TASK-GMR-003: Verify MCP tools work | graphiti-mcp-restoration-wave1-3 | direct | 15min |
| TASK-GMR-011: Add .mcp.json to init | graphiti-mcp-restoration-wave1-4 | task-work | 1hr |

**Dependencies**: GMR-003 depends on GMR-001 (needs config before verification). GMR-011 is independent.
**Validation**: After Wave 1, `mcp__graphiti__search_nodes` should return results in a guardkit Claude Code session. New projects via `guardkit init` should get `.mcp.json` automatically.

### Wave 2: Command Spec Updates (3 tasks, parallel via Conductor)

**Goal**: Highest-value commands use MCP for knowledge graph context.

| Task | Workspace | Method | Est. |
|------|-----------|--------|------|
| TASK-GMR-004: /task-work MCP integration | graphiti-mcp-restoration-wave2-1 | task-work | 2-3hr |
| TASK-GMR-005: /task-review context loading | graphiti-mcp-restoration-wave2-2 | task-work | 2-3hr |
| TASK-GMR-006: /feature-plan context loading | graphiti-mcp-restoration-wave2-3 | task-work | 2-3hr |

**Dependencies**: All depend on Wave 1 completion.
**Validation**: Running `/task-work` should show "[Graphiti] Context loaded via MCP: N items".

### Wave 3: Write Paths (2 tasks, parallel via Conductor)

**Goal**: Start the learning flywheel — automatic knowledge capture from task lifecycle.

| Task | Workspace | Method | Est. |
|------|-----------|--------|------|
| TASK-GMR-007: /task-complete write path | graphiti-mcp-restoration-wave3-1 | task-work | 1-2hr |
| TASK-GMR-008: /task-review capture write path | graphiti-mcp-restoration-wave3-2 | task-work | 1-2hr |

**Dependencies**: Depend on Wave 1 (MCP available).
**Validation**: Completing a task shows "[Graphiti] Task outcome captured".

### Wave 4: Observability (2 tasks, parallel via Conductor)

**Goal**: Make Graphiti's contribution visible.

| Task | Workspace | Method | Est. |
|------|-----------|--------|------|
| TASK-GMR-009: Context influence markers | graphiti-mcp-restoration-wave4-1 | task-work | 1hr |
| TASK-GMR-010: MCP query logging | graphiti-mcp-restoration-wave4-2 | task-work | 1hr |

**Dependencies**: Depend on Wave 2 (commands using MCP).
**Validation**: Phase 2 output shows "Context Used" section.

## Dependency Graph

```
Wave 1 (parallel):
  GMR-001 (config) ──┐
  GMR-002 (instruction) ──┤
  GMR-003 (verify) ←──────┘ (depends on GMR-001)
           │
           ▼
Wave 2 (parallel, after Wave 1):
  GMR-004 (/task-work)
  GMR-005 (/task-review)
  GMR-006 (/feature-plan)
           │
           ▼
Wave 3 (parallel, after Wave 1):     Wave 4 (parallel, after Wave 2):
  GMR-007 (/task-complete)             GMR-009 (observability)
  GMR-008 (/task-review write)         GMR-010 (logging)
```

Note: Wave 3 only depends on Wave 1 (MCP available), not Wave 2. Waves 3 and 4 can run concurrently if Wave 1 and 2 are both complete.

## Key Files Modified

| Wave | Files |
|------|-------|
| 1 | `.mcp.json`, `installer/core/commands/task-work.md` (lines 1701-1703), `installer/core/commands/lib/graphiti-preamble.md` |
| 2 | `installer/core/commands/task-work.md` (Phase 1.7), `installer/core/commands/task-review.md` (Phase 1), `installer/core/commands/feature-plan.md` |
| 3 | `installer/core/commands/task-complete.md`, `installer/core/commands/task-review.md` (Phase 5) |
| 4 | `installer/core/commands/task-work.md` (Phase 2), `installer/core/commands/task-review.md` (Phase 2) |

## Infrastructure Prerequisites

All infrastructure is already running:
- FalkorDB: `whitestocks:6379` (Synology NAS via Tailscale)
- vLLM Embedding: `promaxgb10-41b1:8001` (nomic-embed-text-v1.5)
- vLLM LLM: `promaxgb10-41b1:8000` (Qwen2.5-14B)
- MCP Server: `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/`
- Reference config: `agentic-dataset-factory/.mcp.json`

## AutoBuild Note

AutoBuild's Graphiti integration (Python direct imports) is NOT modified by any of these tasks. It's already working correctly and should not be touched. These tasks only affect Claude Code command specs and their MCP integration.
