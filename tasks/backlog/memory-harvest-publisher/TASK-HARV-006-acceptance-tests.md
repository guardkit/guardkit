---
id: TASK-HARV-006
title: Acceptance tests for the harvest contract
task_type: testing
status: backlog
created: 2026-06-25T00:00:00Z
updated: 2026-06-25T00:00:00Z
complexity: 3
parent_review: TASK-REV-HARV
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
wave: 4
implementation_mode: direct
depends_on:
  - TASK-HARV-005
---

# TASK-HARV-006: Acceptance tests for the harvest contract

## Objective

One acceptance test module that asserts the brief's four explicit contract tests
end-to-end against the **assembled CLI** — closing the per-task-green-≠-feature-green
gap (each prior task's unit tests pass in isolation; this proves the composed harvest
behaves correctly). Runs with **no live broker**.

## Context

The brief specifies a four-point test contract. Per-task unit tests cover their slices;
this task asserts the four together against `guardkit memory harvest` so a regression in
the wiring (walker → publisher → CLI) is caught at the feature boundary.

## Acceptance Criteria

- [ ] Subject resolution: for every `episode_type` the walker emits (`adr`,
      `review_report`, `feature_outcome`, `document`), the published subject is
      `memory.episode.guardkit.{episode_type}` (assert via `nats_core` subject
      resolution or by capturing the subject a fake client publishes to).
- [ ] `episode_id` stability: two independent harvest runs over the same docs root
      produce identical `episode_id`s for the same documents (idempotency precondition).
- [ ] Oversized rejection: a > 900 KB body is rejected with an **actionable** error —
      assert the walker's skip report (or the publisher catch) names the path and the
      byte size.
- [ ] Dry-run isolation: `guardkit memory harvest --dry-run` lists counts-per-type and
      constructs **no** `NATSClient` / performs no `connect()` (assert via patch/spy).
- [ ] The entire module runs green with NATS fully mocked/faked — **no** GB10 access,
      **no** `GUARDKIT_NATS_PASSWORD` required, green in CI.

## Implementation Notes

- Reuse the fake `NATSClient` from TASK-HARV-004's tests (or promote it to a shared
  fixture) so the acceptance suite never touches a real broker.
- Build a small temp docs tree (a handful of `.md` across the four episode_types, plus
  one synthetic > 900 KB file) as the fixture rather than harvesting the real `docs/`.

## Coach Validation

```bash
pytest tests/ -v -k harvest_acceptance
```
- Testing task: no architectural review, no lint gate.
