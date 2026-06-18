---
id: TASK-AB-BDDNEUTRAL01
title: Neutral BDD verdict on absent feature file + auto-install conftest bridge
status: completed
task_type: bug
priority: medium
complexity: 4
created: 2026-06-17T11:00:00Z
updated: 2026-06-17T12:30:00Z
completed: 2026-06-17T12:30:00Z
completed_location: tasks/completed/TASK-AB-BDDNEUTRAL01/
previous_state: in_review
state_transition_reason: "completed: all ACs met, tests green"
tags: [autobuild, bdd, gate, false-red, absence-of-failure]
source: docs/retro/autobuild-retro-xref-2026-06-17.md
provenance: fleet-memory FEAT-MEM-07 Error 1 (BDD exit-4 affects every task)
---

# Task: Neutral BDD verdict on absent feature file + auto-install conftest bridge

## Description

`bdd_runner` surfaces a **synthetic failure** when no `.feature` file matches the task
(`pytest` exits 4, "not found") — `bdd_runner.py:627,706` ("surfacing as synthetic
failure"). A **missing gate input** should be **neutral / not-applicable**, not
`failed=1`. It is non-blocking on its own, but it **stacks** with any other gate result
into an `unrecoverable_stall` (the mechanism behind FEAT-MEM-07 Error 1, which had been
quietly failing the whole repo).

Two halves:
1. **Verdict:** "no matching `.feature`" → `not_applicable` (neutral), per
   `.claude/rules/absence-of-failure-is-not-success.md` (absent signal ≠ failure).
2. **Infra:** the canonical bridge
   `installer/core/templates/common/features/conftest.py.template` now ships, so a
   freshly-`init`'d project gets `features/conftest.py` — but a **pre-existing** repo
   without it still exit-4s on every task.

## Acceptance Criteria

- [x] When `bdd_runner` finds **no `.feature` file** matching the task (or pytest exits 4
      with zero collected items for the absent-feature reason), the BDD oracle result is
      **`not_applicable` / absent**, NOT `failed`. It must never contribute a failure to
      the gate tally or the pollution checkpoint.
- [x] A genuine BDD failure (a `.feature` exists and a scenario fails) still reports
      `failed` — only the **absent-input** case becomes neutral.
- [x] `guardkit init` / the autobuild bootstrap **auto-installs** `features/conftest.py`
      from the canonical template when a project has `.feature` files (or a `features/`
      dir) but no bridge.
- [x] Regression test: a task with no matching `.feature` → BDD verdict `not_applicable`,
      gate not blocked; a task whose `.feature` scenario fails → `failed`.

## Implementation Summary (2026-06-17)

**Half 1 — Neutral verdict** (`guardkit/orchestrator/quality_gates/bdd_runner.py`):
`_is_absent_feature_collection()` maps a pytest **exit 4 with a "not found" collection
signature** + zero parsed testcases → `None` (neutral ⇒ `bdd_results` key absent ⇒
Coach's `_check_bdd_results` treats the gate as not-applicable). The neutral verdict is
gated on a *positive-evidence precondition* (the not-found signature) with a
conftest-import **veto**, so genuine runner errors (conftest `ImportError`, exit 2/3,
empty-stream exit 4, timeout) STILL surface as failures — **TASK-FIX-F584 preserved**.
Verified against real pytest 9.0.2.

**Half 2 — Auto-install bridge**: new single-source helper
`guardkit/templates/conftest_bridge.py::install_features_conftest_bridge()` (guarded,
idempotent, non-raising), wired at two bootstrap chokepoints —
`WorktreeManager.create()` (covers task + shared-feature worktrees) and `guardkit init`.

**AC-1 pollution-checkpoint clause**: confirmed `worktree_checkpoints.py` has zero `bdd`
references and `_extract_tests_passed` is tri-state — an absent BDD signal cannot
contribute a failure. Removing the synthetic failure at source breaks the
`unrecoverable_stall` stacking chain (FEAT-MEM-07 Error 1).

**Tests** (all green): `test_bdd_runner.py` 59 passed (2 F584 tests repurposed to genuine
exit-4 conftest errors; `TestAbsentFeatureCollectionIsNeutral` +
`TestGenuineScenarioFailureStillFails` added); `test_conftest_bridge.py` 11 (100% cov);
`test_worktree_conftest_bridge.py` 3 (real-git). `bdd_runner.py` 86% line / 92% branch.
Downstream BDD/worktree/init suites unaffected.

> **Pre-existing, out-of-scope**: `tests/rules/test_no_dead_task_id_references.py` fails on
> `guardkit/orchestrator/feature_audit.py:60` (`TASK-XYZ-001`, a docstring example) — red
> on pristine HEAD, unrelated to this task; left untouched per zero-scope-creep.

## Implementation Notes

- `bdd_runner.py` classifies pytest exit codes; add the exit-4-with-no-collection →
  `not_applicable` mapping. Cross-check against the per-task glue contract in
  `.claude/rules/bdd-per-task-glue.md`.
- The auto-install belongs in the bootstrap/init path (where the worktree is prepared),
  guarded so it never clobbers an existing `features/conftest.py`.

## Provenance

FEAT-MEM-07 Error 1 (fleet-memory); also surfaced across prior features (masked unless
stacked with another gate). Cross-reference report
`docs/retro/autobuild-retro-xref-2026-06-17.md` §3.5.
