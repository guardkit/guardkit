---
complexity: 6
consumer_context:
- consumes: get_memory_client
  driver: in-process import
  format_note: search(query, group_ids) -> list[{fact,uuid,score}] adapted from memory_search
    context_block; token_budget generous
  framework: guardkit.knowledge.fleet_memory_client factory + search
  task: TASK-MEM08-002
dependencies:
- TASK-MEM08-005
feature_id: FEAT-MEM-08
id: TASK-MEM08-006
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: completed
task_type: feature
title: Wire memory_search into coach-context + feature-plan-context readers
wave: 5
---

# TASK-MEM08-006 — Wire the GROI reads through fleet-memory

> Source: brief W3 — "Wire `memory_search` into the coach-context / feature-plan-context readers." The
> **code + unit tests** only; the "prove a real run reads from fleet-memory" acceptance gate is the
> sibling operator task TASK-MEM08-007. (Depends on TASK-MEM08-005 to encode the brief's
> "dual-write soak **before** cutting reads over" sequencing.)

## Goal

Route guardkit's live read paths through the W2 factory so that, under `backend=fleet_memory` (or `dual`),
`coach_context_builder` and `feature_plan_context` obtain their context block from
`memory_search(project="guardkit", …)` instead of Graphiti `search()` — with the read flag defaulting off.

## Scope (read call-sites — all verified to consume flat `fact` text + score only)

- `guardkit/planning/coach_context_builder.py` (→ AutoBuild coach prompt).
- `guardkit/knowledge/feature_plan_context.py` (→ /feature-plan context).
- Obtain the client via `get_memory_client()`; the adapter returns the graphiti-shaped `list[dict]`.
- **Evidence hook:** ensure `query_logger.log_query(...)` fires on the fleet-memory read path with a
  distinguishable `source` (e.g. `"fleet_memory_client"`) so a real run's reads are visible in
  `.guardkit/graphiti-query-log.jsonl` — this is the evidence TASK-MEM08-007 inspects.

## Acceptance Criteria

- [ ] Under `backend=fleet_memory`/`dual`, `coach_context_builder` and `feature_plan_context` build their
      context from `memory_search` results (flat context block), with a **generous token budget** so the
      relevant heading lands (brief: passages can bury the answer).
- [ ] Under `backend=graphiti` (default), both readers behave exactly as today — proven by test.
- [ ] `group_ids` are translated to `payload_types`/`domain_tags` via `fleet_memory_mapping`; an unmapped
      group degrades gracefully (empty context, no raise).
- [ ] The fleet-memory read path emits a `query_logger` entry tagged with a fleet-memory `source`.
- [ ] A fleet-memory read failure degrades gracefully (empty/partial context, never crashes the pipeline).
- [ ] Unit tests mock `memory_search`; cover: context-block→reader injection, graphiti-default unchanged,
      unmapped-group degradation, query-logger emission, read-failure isolation. No live infra in tests.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
pytest tests/unit/planning/test_coach_context_builder.py tests/unit/knowledge/test_feature_plan_context.py -v
pytest tests/unit/knowledge/test_query_logger.py -v
```

## Seam Tests

```python
"""Seam test: verify the fleet-memory read path emits a query-log evidence entry."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("groi_read_evidence")
def test_fleet_memory_read_logs_evidence():
    """A real pipeline read must be observable in the query log (basis for TASK-MEM08-007).

    Contract: a fleet-memory search emits query_logger entry with source identifying fleet-memory.
    Producer: TASK-MEM08-002 adapter + query_logger
    """
    # With memory_search mocked and backend=fleet_memory, invoking the reader must append
    # a query-log entry whose "source" marks the fleet-memory backend.
    logged = []  # capture query_logger.log_query calls
    assert any("fleet" in (e.get("source") or "") for e in logged), "fleet-memory read must be logged"
```

## Implementation Notes

Do not reshape the readers' downstream consumers — they already take flat text. The only change is the
*source* of the context block + the evidence-logging tag. Keep the token budget generous and configurable.