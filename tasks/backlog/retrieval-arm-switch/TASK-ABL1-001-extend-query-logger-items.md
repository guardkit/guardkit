---
id: TASK-ABL1-001
title: Extend query_logger with optional per-item results field
task_type: feature
feature_id: FEAT-ABL-001
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 8
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-ABL-001
  base_branch: main
  started_at: '2026-07-03T17:37:53.265045'
  last_updated: '2026-07-03T17:49:13.751542'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Direct-mode evidence gate blocked the turn (direct_mode_ac_unverified).
      Direct mode relaxes coverage/arch gates but still requires verifiable AC delivery,
      resolved wiring, and runnable registered producers:

      - [direct_mode_ac_unverified] Direct mode: 1/6 acceptance criteria have no disk
      evidence (unmet: [''AC-005'']). Direct mode relaxes coverage/arch but NOT AC
      delivery.'
    timestamp: '2026-07-03T17:37:53.265045'
    player_summary: 'Direct mode SDK invocation completed (git-detected: 3 modified,
      4 created)'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-07-03T17:42:17.150649'
    player_summary: Added optional `items` parameter to _build_entry and log_query,
      included it conditionally in the entry. Updated docstrings. Added unit tests
      for non-empty items, empty list, and omitted items.
    player_success: true
    coach_success: true
---

# Extend query_logger with optional per-item results field

## Context

`guardkit/knowledge/query_logger.py` writes append-only JSONL entries to
`.guardkit/memory-query-log.jsonl` (thread-safe, 1MB rotation, never raises).
Entries currently carry `timestamp/source/operation/query/group_ids/result_count/first_result_preview`
and are only produced from the `/feature-plan` chain (`feature_plan_context.py:566`).

The memory ablation (FEAT-ABL-001, scope §4) needs the same log to carry
**per-item retrieval identity**: a list of `{id, score}` objects, where `id` is a
fleet-memory natural key and `score` the retrieval relevance score. TASK-ABL1-003
will emit these from `FleetMemoryClient.search`; this task adds the schema field.

## Scope

- `guardkit/knowledge/query_logger.py` only (plus its new unit test module).
- Purely additive: existing call sites (`feature_plan_context.py:566`) must keep
  working unchanged, with byte-identical entries to today when `items` is not passed.

## Requirements

1. `log_query(...)` gains an optional keyword parameter `items: Optional[List[Dict[str, Any]]] = None`.
2. `_build_entry(...)` gains the same optional parameter. When `items is None`, the
   built entry dict **must not contain** an `"items"` key (back-compat: existing
   entries stay byte-identical). When `items` is a list (including the empty list
   `[]`), the entry contains `"items": <the list>`.
3. Each item is expected to be shaped `{"id": str, "score": float}` — document this
   shape in the docstrings, but do not validate or transform the dicts (the logger
   stays dumb/never-raises; callers own the shape).
4. Thread-safety, rotation, and the swallow-all-exceptions contract are unchanged.

## Acceptance Criteria

- [ ] `log_query(operation="search", query="q", items=[{"id": "chunk:guardkit:X", "score": 0.9}], base_dir=tmp)` writes a JSONL line whose parsed dict has `entry["items"] == [{"id": "chunk:guardkit:X", "score": 0.9}]`
- [ ] `log_query(operation="search", query="q", items=[], base_dir=tmp)` writes a line with `entry["items"] == []` (empty list is preserved, not dropped)
- [ ] `log_query(operation="search", query="q", base_dir=tmp)` (no `items` argument) writes a line where `"items" not in entry` — existing callers produce entries identical to the pre-change schema
- [ ] All pre-existing fields (`timestamp`, `source`, `operation`, `query`, `group_ids`, `result_count`, `first_result_preview`) are unaffected
- [ ] Unit tests cover the three cases above in `tests/unit/knowledge/test_query_logger.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

New module `tests/unit/knowledge/test_query_logger.py` using `tmp_path` as
`base_dir` (the logger already supports `base_dir` injection for tests). Read the
JSONL file back and assert on parsed dicts. No live services required.

## Implementation Notes

- Keep the change minimal: one optional parameter threaded from `log_query` to
  `_build_entry`, one conditional key insertion.
- Do NOT rename the log file, change rotation, or alter `extract_preview`.
