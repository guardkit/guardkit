---
id: TASK-HARV-006
title: Acceptance tests for the harvest contract
task_type: testing
status: in_progress
created: 2026-06-25 00:00:00+00:00
updated: 2026-06-25 00:00:00+00:00
complexity: 3
parent_review: TASK-REV-HARV
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
wave: 4
implementation_mode: direct
depends_on:
- TASK-HARV-005
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-HARV
  base_branch: main
  started_at: '2026-06-26T12:22:18.237966'
  last_updated: '2026-06-26T12:28:38.762806'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Independent test verification FAILED for a TESTING task: the Coach's\
      \ own run of the task's tests reported failures classified as a CODE defect\
      \ (confidence=n/a), not an environment/substrate gap and not parallel-wave contention.\
      \ A TESTING task's deliverable is passing tests \u2014 fix the failing test\
      \ code. Independent-test output (tail): 0     0%   2-97\ninstaller/core/lib/utils/path_resolver.py\
      \                                          28     28      6      0     0%  \
      \ 2-81\n---------------------------------------------------------------------------------------------------------------------------\n\
      TOTAL                                                                      \
      \     12178  12162   4186      0     1%\nCoverage JSON written to file coverage.json\n\
      ============================== 15 passed in 4.44s =============================="
    timestamp: '2026-06-26T12:22:18.237966'
    player_summary: 'Created comprehensive acceptance test suite for the harvest contract
      that validates all four explicit contract points end-to-end against the assembled
      CLI. The test suite includes 15 tests organized into 5 groups covering: (1)
      Subject resolution for all 4 episode_types, (2) episode_id stability/idempotency,
      (3) Oversized rejection handling, (4) Dry-run isolation, and (5) No live broker/password
      requirements. All tests use mocked NATSClient to ensure no GB10 access is required.
      Tests create tempo'
    player_success: true
    coach_success: true
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
