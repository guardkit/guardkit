---
id: TASK-ABL1-003
title: "Enforce retrieval arm inside FleetMemoryClient.search and emit per-item retrieval log"
task_type: feature
feature_id: FEAT-ABL-001
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-ABL1-001
- TASK-ABL1-002
status: backlog
---

# Enforce retrieval arm inside FleetMemoryClient.search and emit per-item retrieval log

## Context

`FleetMemoryClient.search` (`guardkit/knowledge/fleet_memory_client.py:227-322`) is the
single choke point every AutoBuild context read flows through
(`orchestrator/autobuild.py:1351` factory → `autobuild_context_loader.py:333` →
`job_context_retriever` → `search`). It currently:

- returns `[]` when `self.config.enabled` is false (lines 257-258) — this is the gate
  shape the arm gate must mirror exactly;
- calls `fm_search(request, self._store)` then `assemble_context(results, token_budget)`
  (lines 304-305) — **between those two calls is the only place per-item identity
  still exists**: each `results` item has `.score` and `.value["natural_key"]`;
- collapses everything into ONE synthetic hit `{"fact": context_block, "uuid": str(uuid4()), "score": coverage_score}` (lines 312-318) before any caller sees it.

TASK-ABL1-002 added `retrieval_arm`/`fixture_id` to `FleetMemoryConfig`.
TASK-ABL1-001 added the optional `items` field to `query_logger.log_query`.
This task wires both into `search()`.

## Scope

- `guardkit/knowledge/fleet_memory_client.py`: `search()` only.
- `tests/unit/knowledge/test_fleet_memory_client.py`: extend.
- Do NOT modify `AutoBuildContextLoader`, `JobContextRetriever`, the orchestrator, or the fleet-memory sibling repo. Do NOT change the graphiti-shaped return contract `[{"fact", "uuid", "score"}]` — GROI readers depend on it.

## Requirements

1. **Arm gate**: immediately after the existing `if not self.config.enabled: return []`
   gate, add: `if self.config.retrieval_arm == "off": return []` (a `logger.debug` line
   is fine; no store access, no log entry, no other side effects). The gate must sit
   INSIDE `search()` so the context loader, turn-continuation, and template-pattern
   paths execute identically on every arm.
2. **Per-item retrieval log**: after `results = await fm_search(request, self._store)`
   succeeds and BEFORE the `assembly.context_block` early-return can fire, call
   `guardkit.knowledge.query_logger.log_query` with:
   - `operation="search"`, `query=query`, `group_ids=group_ids or []`,
   - `result_count=len(results)`,
   - `items=[{"id": item.value.get("natural_key", ""), "score": float(item.score or 0.0)} for item in results]`,
   - `first_result_preview` from the first item's content when available (reuse the existing preview convention, 50 chars),
   - `source="fleet_memory_client"`.
   The entry is written on EVERY search that reaches `fm_search` — including when
   `results` is empty (`items=[]`) — on both the unset arm and the fixture arm.
   The run-time guardrail depends on distinguishing "retrieval attempted, nothing
   found" (entry with empty items) from "no retrieval" (no entry).
3. **No log on failure paths**: the existing `except` block (log + `return []`) must
   NOT write a retrieval-log entry when `fm_search` itself raised; a log write only
   happens after a successful `fm_search` return. (`log_query` never raises by
   contract, so no extra try/except is needed around it.)
4. The synthetic single-hit return shape (lines 312-318) stays byte-identical.

## Acceptance Criteria

- [ ] With `retrieval_arm="off"` and `enabled=True`, `await client.search("q")` returns `[]`, never touches `initialize()`/the store, and writes zero retrieval-log entries (off arm: zero retrieval calls in the log)
- [ ] With `retrieval_arm=None` (unset) and a mocked store/`fm_search` returning 2 items, `search()` returns the same single synthetic hit as before the change, and exactly one JSONL entry is appended with `items == [{"id": "<natural_key_1>", "score": <score_1>}, {"id": "<natural_key_2>", "score": <score_2>}]`
- [ ] With `retrieval_arm="fixture:v1"` and a mocked `fm_search` returning items, the entry's item ids equal the mocked natural keys (never freshly-generated uuids) and scores equal the mocked per-item scores
- [ ] With a mocked `fm_search` returning `[]`, one entry is appended with `result_count == 0` and `items == []`, and `search()` returns `[]`
- [ ] With a mocked `fm_search` that raises, `search()` returns `[]` and no entry is appended
- [ ] With `enabled=False`, `search()` returns `[]` with no entry (existing gate keeps precedence, arm irrelevant)
- [ ] The logged entries never contain the DSN or credentials (assert the serialized line does not contain the configured DSN string)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

Extend `tests/unit/knowledge/test_fleet_memory_client.py`. Mock
`fleet_memory.retrieval` (`fm_search`, `assemble_context`, `SearchRequest`) the same
way existing search tests do; use `log_query`'s `base_dir` injection (or monkeypatch
`query_logger._get_log_path`) plus `tmp_path` to capture entries. Mocked result items
need `.score` and `.value` (dict with `natural_key`) attributes — a simple
`SimpleNamespace`/`MagicMock` suffices. No live Postgres, no network.

## Implementation Notes

- Gate order inside `search()`: `enabled` gate (existing) → `retrieval_arm == "off"`
  gate (new) → `_read_available` gate (existing) → lazy `initialize()` (existing).
- The fixture arm needs NO special handling inside `search()` beyond logging — the
  DSN swap already happened at config time (TASK-ABL1-002), so `initialize()`
  naturally opens the fixture store.
- Import `log_query` lazily inside `search()` (matching the file's local-import
  style) or at module top — either is acceptable; be consistent with the file.
