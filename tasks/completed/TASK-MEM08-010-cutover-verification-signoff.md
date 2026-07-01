---
id: TASK-MEM08-010
title: "Cutover verification + soak sign-off → green-light FEAT-MEM-09 [operator]"
task_type: operator_handoff
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 8
implementation_mode: task-work
complexity: 3
dependencies:
  - TASK-MEM08-008
  - TASK-MEM08-009
---

# TASK-MEM08-010 — Cutover verification + soak sign-off

> `task_type: operator_handoff` — AutoBuild will **not** attempt this. The final gate: verify the flipped
> live config actually works end-to-end and sign off the soak so FEAT-MEM-09 (decommission) can begin.
> `observed_at_runtime` against the live fleet-memory MCP server + store. The operator verifies the
> criteria, then marks the task complete via `/task-complete`.

## What to do

1. From a live Claude Code session, confirm the `.mcp.json` fleet-memory MCP server
   (`python -m fleet_memory.mcp`) starts and responds (`memory_search` / `memory_write_payload` reachable).
2. Confirm `guardkit memory search "<q>"` returns live results and `guardkit memory status` reports a
   healthy store.
3. Confirm the dual-write soak audit (TASK-MEM08-005) is clean over the agreed window and the GROI read
   proof (TASK-MEM08-007) is signed off.
4. Record the sign-off and explicitly green-light FEAT-MEM-09 (freeze FalkorDB → pull `qwen-graphiti`).

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator must verify the
runtime acceptance criteria below manually, then mark the task complete via `/task-complete`.

- **AC-010-1**: The `.mcp.json` fleet-memory MCP server starts from a live session and its tools respond.
- **AC-010-2**: `guardkit memory search` returns live results and `guardkit memory status` is healthy
  against the live Postgres store.
- **AC-010-3**: The W2 soak audit (TASK-MEM08-005) and W3 read proof (TASK-MEM08-007) are both signed off,
  and a cutover sign-off note green-lighting **FEAT-MEM-09** is recorded under
  `docs/design/specs/memory-cutover/`.

## Notes

Rollback remains available throughout: `backend=graphiti` + re-enable `.guardkit/graphiti.yaml` +
the `guardkit graphiti` warn+delegate alias. Only after this sign-off does FEAT-MEM-09 remove the
Graphiti substrate. See [[graphiti-cutover-qwen25-removal]].
