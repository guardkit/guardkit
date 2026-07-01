---
complexity: 4
dependencies:
- TASK-MEM08-007
feature_id: FEAT-MEM-08
id: TASK-MEM08-009
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: completed
task_type: feature
title: Flip .mcp.json + task-complete tool renames + graphiti.yaml config + docs/rules
wave: 7
---

# TASK-MEM08-009 — Flip integration-point config + docs (rollback-guarded)

> Source: brief W4 — repoint `.mcp.json`, rename the `/task-complete` tool calls, update
> `.guardkit/graphiti.yaml`, and refresh docs/rules. Depends on TASK-MEM08-007 (do **not** flip the live
> MCP config until reads are proven). These are deterministic file edits; the *live verification* that the
> new MCP server responds is the operator task TASK-MEM08-010.

## Deliverables (config + markdown + docs — no Python logic)

1. `.mcp.json` — repoint the memory MCP server from the graphiti HTTP endpoint
   (`http://promaxgb10-41b1:8004/mcp`) to `python -m fleet_memory.mcp` (stdio) with `FLEET_MEMORY_*` env.
   Rename the server key `graphiti` → `fleet_memory`.
2. `installer/core/commands/task-complete.md` — rename the Tier-0 tool calls:
   `mcp__graphiti__add_memory` → `mcp__fleet_memory__memory_write_payload`,
   `mcp__graphiti__search_*` → `mcp__fleet_memory__memory_search` (payload-shaped args, not free text).
3. `.guardkit/graphiti.yaml` → fleet-memory config block; **leave `enabled: false` during the soak**
   (rollback). Document the `backend` flag values.
4. Docs/rules: update `.claude/rules/graphiti-knowledge-graph.md` / `graphiti-knowledge.md` and
   `CLAUDE.md`'s Graphiti section to describe the fleet-memory backend, the `guardkit memory` group, and
   the deprecation of `guardkit graphiti`. Note the rollback procedure.

## Acceptance Criteria

- [ ] `.mcp.json` points the memory server at `python -m fleet_memory.mcp` with the `FLEET_MEMORY_*` env;
      the JSON is valid.
- [ ] `task-complete.md` Tier-0 references `mcp__fleet_memory__memory_write_payload` /
      `mcp__fleet_memory__memory_search`; no `mcp__graphiti__add_memory` remains in the Tier-0 block.
- [ ] `.guardkit/graphiti.yaml` carries the fleet-memory config and `enabled: false` (soak/rollback) with
      the `backend` flag documented.
- [ ] Docs/rules describe the fleet-memory backend, `guardkit memory`, and the `guardkit graphiti`
      deprecation; the rollback path (`backend=graphiti`, re-enable graphiti.yaml) is written down.
- [ ] No stale `promaxgb10-41b1:8004/mcp` reference remains in `.mcp.json`.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
python -c "import json; json.load(open('.mcp.json'))"
grep -q "fleet_memory" .mcp.json && ! grep -q "8004/mcp" .mcp.json && echo "mcp.json flipped"
! grep -q "mcp__graphiti__add_memory" <(sed -n '/Tier 0/,/Tier 1/p' installer/core/commands/task-complete.md) && echo "tier-0 renamed"
```

## Implementation Notes

This is config + docs only — all Python behaviour is already flag-controlled from W2/W3. Flipping
`.mcp.json` changes which MCP server a *Claude Code session* talks to; confirming it actually responds is
the operator's job (TASK-MEM08-010). Keeping `graphiti.yaml enabled: false` means the autobuild/CLI path
stays on the dual/flag-controlled code until the operator signs off.