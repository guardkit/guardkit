---
id: TASK-LBL-006
title: "Test suite: determinism, fail-open, identity degrade, archive branches, mapping"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: testing
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 4
implementation_mode: direct
complexity: 3
dependencies: [TASK-LBL-001, TASK-LBL-002, TASK-LBL-003, TASK-LBL-004]
tags: [observability, labels, obs-6, testing]
---

# Task: Test suite — determinism, fail-open, identity degrade, archive branches, mapping

## Description

Regression suite pinning the feature's load-bearing invariants, extending the
per-task tests shipped by LBL-001..004. Covers the BDD scenarios in
`features/outcome-label-sidecar/outcome-label-sidecar.feature` that are
unit-testable (the archive-survival scenario against the REAL
`RunArtifactArchiver` is the flagship integration test).

## Test inventory

`tests/unit/labels/` (extend) and `tests/integration/labels/`:

1. **label_id determinism** — same judged fields → same id across processes;
   timestamp excluded; any judged-field change → new id.
2. **Append-only + fail-open** — second disposition appends (first record
   byte-unchanged); unwritable dir → `success=False`, no raise; read-back
   preserves write order.
3. **Identity degrade matrix** (LBL-002): completed-shape / failed-shape /
   trailing-llm.call / corrupt-line-among-valid / empty / absent →
   expected (run_id, attempt) or (None, None).
4. **Path branches** (LBL-003): live hit; archive solo nesting; archive
   feature nesting; traversal task_id rejected; every archive case pins
   `GUARDKIT_ARCHIVE_ROOT` via monkeypatch (hermetic — the feature's only
   env var).
5. **Archive-survival integration** — write a label into a fake worktree's
   `.guardkit/autobuild/{task_id}/`, run the REAL
   `RunArtifactArchiver.archive_worktree_artifacts` (not a mock — this is a
   primary in-repo seam; mocking it is absent integration evidence per
   `.claude/rules/per-task-green-is-not-feature-green.md`), assert
   `outcome_labels.jsonl` exists in the archive nested under the task id.
6. **CLI mapping table** — parametrized over all five `--source` rows →
   documented verdict_class; unknown source errors.
7. **Coverage report** — mixed dc_class fixture across live + archive dirs →
   per-class counts, label_id dedupe, unattributed bucket, floor flags.
8. **Corrupt-record tolerance** — one corrupt line in a sidecar: append still
   works; coverage read skips it with a warning and counts the valid records.
9. **Concurrent appends** — two processes/threads appending to one sidecar:
   both records present, no torn/interleaved lines (single-write O_APPEND
   lines ≤ PIPE_BUF).

## Acceptance Criteria

- [ ] All tests above implemented and passing; suite runs green with `pytest tests/unit/labels tests/integration/labels -q`
- [ ] Archive-survival test exercises the real archiver, not a mock
- [ ] Every test pinning archive behaviour sets/unsets GUARDKIT_ARCHIVE_ROOT explicitly (no ambient-environment dependence)
- [ ] Line coverage ≥80% / branch ≥75% across `guardkit/labels/` and `guardkit/cli/label.py`

## Implementation Notes

- Reuse fixture shapes from `tests/unit/test_worktree_checkpoints_evidence.py`
  and existing archive tests if present; keep fixtures synthetic and hermetic.
