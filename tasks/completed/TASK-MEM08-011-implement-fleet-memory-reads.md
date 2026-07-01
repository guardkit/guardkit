---
id: TASK-MEM08-011
title: Implement real fleet-memory reads (FleetMemoryClient.search + interface) — unblock GROI / 007
task_type: feature
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 6
implementation_mode: task-work
complexity: 6
status: completed
resolved_by: commit 422d8b1e (autobuild/FEAT-MEM-08), 2026-06-29
dependencies:
  - TASK-MEM08-002
  - TASK-MEM08-006
---

# TASK-MEM08-011 — Implement real fleet-memory reads

> Filed 2026-06-29 from the **TASK-MEM08-007** read-proof gate, which found the GROI read path
> is a stub. Evidence: `docs/design/specs/memory-cutover/TASK-MEM08-007-read-path-evidence.md`.
> This is the genuine "wire it in" work TASK-MEM08-006 was meant to deliver.

## Problem

`FleetMemoryClient.search()` (`guardkit/knowledge/fleet_memory_client.py`) is a stub: it
hardcodes `context_block = ""` and returns `[]` unconditionally — it never queries the live
store. And `FleetMemoryClient` lacks the interface its consumers call (`build_context`,
`guardkit memory status/search`): no `enabled` property, no `initialize()` / `health_check()` /
`close()`. Runtime: `AttributeError: 'FleetMemoryClient' object has no attribute 'enabled'`.
The fleet-memory read path is therefore non-functional and TASK-MEM08-007 FAILS.

## Acceptance Criteria

- [x] **AC-1** — `FleetMemoryClient.search()` actually queries the live fleet-memory store and
      returns real graphiti-shaped hits (`[{fact, uuid, score}, ...]`). Approach: call
      fleet-memory's search directly (import its store / `memory_search` logic) or via a real
      MCP client. **No hardcoded `""` / unconditional `[]`.**
- [x] **AC-2** — `FleetMemoryClient` implements the consumer interface that `build_context`
      (`feature_plan_context.py:384`) and the CLI (`_cmd_status`, `_cmd_search`) call:
      `enabled` property, `initialize()`, `health_check()`, `close()`.
- [x] **AC-3** — `_check_mcp_available()` (or a read-specific check) reflects the **read**
      dependency (the `memory_search` tool / store reachability), not `import nats_core`.
- [x] **AC-4** — `_load_fleet_config_from_env` defaults match the live deployment
      (`embed` / `1024`) **or** hard-error on missing required config — no silent
      `nomic-embed`/`768`/`localhost:5433`. *(This subsumes the adapter-defaults follow-up.)*
- [x] **AC-5** — A real `guardkit memory search "<q>"` against the live corpus returns
      `result_count > 0`, and `build_context()` returns a non-empty injected context block.
- [x] **AC-6** — Re-run TASK-MEM08-007: AC-007-1..3 pass with `graphiti-query-log.jsonl`
      evidence (fleet-memory source, `result_count > 0`, context injected).

## Notes

- **Not stub-prone-autobuild-safe.** The 006 unit tests passed against *mocked* clients, which
  is exactly how the stub + interface gap shipped (per-task-green-is-not-feature-green). Verify
  with a **real run against the live store**, not mocks.
- The fleet-memory MCP-tool surface (`mcp__fleet_memory__memory_search` via `.mcp.json`) is a
  separate read path for agents and is out of scope here — this task fixes the **Python adapter**
  used by the automated GROI readers + the `guardkit memory` CLI.
- Corpus reality: 679 rows, all `payload_type=chunk` (harvested docs). The GROI `group_ids` map
  to `build_outcome`/`document`/`warning` payload types that don't exist yet; once search is
  real, confirm whether GROI queries should also read the `chunk` corpus or wait on the 005
  dual-write soak to populate the mapped payload types.

## Resolution (2026-06-29, commit 422d8b1e on autobuild/FEAT-MEM-08)

Implemented: `FleetMemoryClient.search` now reuses `fleet_memory.retrieval.search` +
`assemble_context` (single source of truth); added `enabled`/`initialize`/`health_check`/
`close`; `_check_read_backend_available` imports `fleet_memory.retrieval` (not nats_core);
env defaults corrected to `embed`/`1024`; fleet-memory added to the `memory` extra +
`[tool.uv.sources]` (requires Python >=3.12). Verified live against the NAS 679-row corpus
(result_count>0, 0.901-scored hit, context block injected); 47 unit tests pass.
TASK-MEM08-007 re-run PASSES. Evidence:
`docs/design/specs/memory-cutover/TASK-MEM08-007-read-path-evidence.md`.
