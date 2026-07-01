---
complexity: 5
consumer_context:
- consumes: get_memory_client
  driver: in-process import
  format_note: CLI search uses adapter.search; capture-outcome uses adapter.add_episode/build_outcome
  framework: guardkit.knowledge.fleet_memory_client factory (search + add_episode)
  task: TASK-MEM08-002
dependencies:
- TASK-MEM08-006
feature_id: FEAT-MEM-08
id: TASK-MEM08-008
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: completed
task_type: feature
title: Add guardkit memory search/status/capture-outcome; deprecate guardkit graphiti
wave: 7
---

# TASK-MEM08-008 — `guardkit memory` CLI + deprecate `guardkit graphiti`

> Source: brief W4 — "Fold reads/writes into the existing `guardkit memory` CLI group (search,
> capture-outcome, status); keep `guardkit graphiti` as a deprecated warn+delegate alias during soak."
> The `guardkit memory` group already exists (`guardkit/cli/memory.py`, with `harvest`).

## Goal

Give the operator a fleet-memory-backed CLI for the reads/writes, and turn `guardkit graphiti` into a
thin warn+delegate alias so existing muscle-memory / scripts keep working during the soak.

## Deliverables

- `guardkit memory search "<query>"` — over `memory_search` (project=guardkit; flags for
  `--payload-types`, `--domain-tags`, `--token-budget`); prints the context block + coverage.
- `guardkit memory status` — store reachability + counts by payload_type (replaces graph topology, which
  fleet-memory does not have — drop `graph_stats`).
- `guardkit memory capture-outcome` — mirrors `guardkit graphiti capture-outcome` (`--from-task-file`,
  explicit flags) but writes the `build_outcome` payload via the adapter.
- `guardkit graphiti` group → **deprecated**: each subcommand prints a deprecation warning and **delegates**
  to its `guardkit memory` equivalent (warn+delegate; do not remove during soak — rollback path).

## Acceptance Criteria

- [ ] `guardkit memory search "<q>"` returns fleet-memory results (context block + coverage_score), honouring
      `--token-budget` / `--payload-types` / `--domain-tags`; graceful message when the store is unreachable.
- [ ] `guardkit memory status` reports store reachability and per-payload_type counts (no graph_stats).
- [ ] `guardkit memory capture-outcome --from-task-file <md>` writes a `build_outcome` payload via the adapter.
- [ ] `guardkit graphiti <subcmd>` emits a deprecation warning and delegates to the `guardkit memory`
      equivalent (output equivalent; exit code preserved).
- [ ] Unit tests mock the adapter/store; cover each new command + the deprecation delegation. No live infra.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
pytest tests/unit/cli/test_memory_cli.py -v
guardkit memory --help | grep -E "search|status|capture-outcome"
guardkit graphiti search --help 2>&1 | grep -i deprecat
```

## Implementation Notes

Reuse the W2 factory (`get_memory_client()`) — do not re-implement the fleet-memory calls in the CLI.
Keep `guardkit memory harvest` untouched. The deprecation alias is rollback insurance; it is removed only
in FEAT-MEM-09, not here.