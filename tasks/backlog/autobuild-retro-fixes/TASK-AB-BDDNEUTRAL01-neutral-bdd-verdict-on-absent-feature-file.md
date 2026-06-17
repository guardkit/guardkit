---
id: TASK-AB-BDDNEUTRAL01
title: Neutral BDD verdict on absent feature file + auto-install conftest bridge
status: backlog
task_type: bug
priority: medium
complexity: 4
created: 2026-06-17T11:00:00Z
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

- [ ] When `bdd_runner` finds **no `.feature` file** matching the task (or pytest exits 4
      with zero collected items for the absent-feature reason), the BDD oracle result is
      **`not_applicable` / absent**, NOT `failed`. It must never contribute a failure to
      the gate tally or the pollution checkpoint.
- [ ] A genuine BDD failure (a `.feature` exists and a scenario fails) still reports
      `failed` — only the **absent-input** case becomes neutral.
- [ ] `guardkit init` / the autobuild bootstrap **auto-installs** `features/conftest.py`
      from the canonical template when a project has `.feature` files (or a `features/`
      dir) but no bridge.
- [ ] Regression test: a task with no matching `.feature` → BDD verdict `not_applicable`,
      gate not blocked; a task whose `.feature` scenario fails → `failed`.

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
