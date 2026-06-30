---
complexity: 7
consumer_context:
- consumes: get_memory_client
  driver: in-process import
  format_note: factory returns fleet_memory|graphiti|dual client from config.backend;
    dual mode writes both
  framework: guardkit.knowledge.fleet_memory_client factory + add_episode
  task: TASK-MEM08-002
- consumes: BuildOutcomePayload
  driver: MCP memory_write_payload OR nats_core.publish_episode
  format_note: build_outcome payload now carries task_id/lessons/approach; ADR ->
    adr payload (decision,status)
  framework: fleet_memory.payloads.models (pydantic typed payload)
  task: TASK-MEM08-003
dependencies:
- TASK-MEM08-002
- TASK-MEM08-003
feature_id: FEAT-MEM-08
id: TASK-MEM08-004
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: design_approved
task_type: feature
title: Repoint writes to dual-write Graphiti + fleet-memory behind a flag
wave: 3
---

# TASK-MEM08-004 — Dual-write repoint (task-complete / outcome_manager / adr_service)

> Source: brief W2 — "Repoint `/task-complete` (Tier-0 + Tier-1), `outcome_manager`, `adr_service` to
> fleet-memory, **dual-writing to both** behind a flag." The **code + unit tests** only — the live soak
> audit is the sibling operator task TASK-MEM08-005.

## Goal

Route guardkit's runtime knowledge writes through the W2 factory so that, under `backend=dual`, every
Graphiti write is **also** published to fleet-memory as the mapped typed payload — with Graphiti still
authoritative (rollback-safe). Default backend stays `graphiti` until the operator flips the flag.

## Scope (write call-sites)

- `guardkit/knowledge/outcome_manager.py` (`capture_task_outcome`) → also publish `build_outcome`
  (task_id → identifier; status/duration_seconds; lessons/approach from the outcome fields).
- `guardkit/knowledge/adr_service.py` (`create_adr`) → also publish `adr` (decision, status, supersedes).
- `/task-complete` Tier-1 path (`guardkit/cli/graphiti.py` `capture-outcome`) → routes through the factory.
- Obtain the client via the W2 factory (`get_memory_client()`), **not** by importing graphiti directly.

> Note: `/task-complete` **Tier-0** MCP tool-call renames (`mcp__graphiti__add_memory` →
> `mcp__fleet_memory__memory_write_payload`) live in the markdown and are done in W4 (TASK-MEM08-009),
> after reads are proven. This task is the Python write path only.

## Acceptance Criteria

- [ ] Under `backend=dual`, a captured task outcome is written to **both** Graphiti (unchanged) and
      fleet-memory (`build_outcome` payload with task_id/lessons/approach populated).
- [ ] Under `backend=dual`, an ADR is written to both Graphiti and fleet-memory (`adr` payload).
- [ ] Under `backend=graphiti` (default), behaviour is byte-for-byte unchanged (Graphiti only) — proven by test.
- [ ] A fleet-memory write failure under `dual` **does not** fail the task completion (graceful degradation —
      Graphiti remains authoritative; the failure is logged, not raised).
- [ ] Group_ids resolve through `fleet_memory_mapping`; a `retire` group is not published to fleet-memory.
- [ ] Unit tests mock both backends; cover dual write, graphiti-only default, fleet-write-failure isolation,
      and outcome→build_outcome field mapping. No live infra in tests.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
pytest tests/unit/knowledge/test_outcome_manager.py tests/unit/knowledge/test_adr_service.py -v
pytest tests/unit/cli/test_graphiti_capture_outcome.py -v
```

## Implementation Notes

Keep Graphiti authoritative throughout W2 — `dual` means "additionally publish to fleet-memory", never
"switch". The published payloads feed the TASK-MEM08-005 soak audit (`published == stored`). This is the
seed of the runtime corpus the W3 reads will later retrieve from.