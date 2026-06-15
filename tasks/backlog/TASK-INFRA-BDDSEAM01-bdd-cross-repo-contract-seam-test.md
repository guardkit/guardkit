---
id: TASK-INFRA-BDDSEAM01
title: Add a cross-repo BDD-contract seam test (guardkit ↔ guardkitfactory) to the merge-gating seam-tests.yml
status: backlog
task_type: infrastructure
created: 2026-06-15T00:00:00Z
updated: 2026-06-15T00:00:00Z
priority: medium
complexity: 3
related: [TASK-FIX-BDDFW01, TASK-INFRA-XREPOCONTRACT, TASK-HMIG-BDDWIRE, TASK-BDDW-001, TASK-HMIG-007]
implementation_mode: task-work
tags: [ci, seam-test, cross-repo-contract, bdd, guardkitfactory, recurrence-prevention]
---

# Task: Add a cross-repo BDD-contract seam test against the real installed guardkitfactory

> **Provenance.** Recurrence-prevention follow-up flagged by TASK-FIX-BDDFW01
> (commit `0e4b7912`, 2026-06-15). BDDFW01 fixed a Coach BDD-factory bridge that
> had been *silently dead* for days because production
> (`coach_validator.py`) targeted a stale `guardkitfactory` contract and the
> only test exercising the real contract was dead-on-arrival at collection. A
> per-component diagnosis missed a 4th mismatch (`plugin.run` arity); it was
> only caught by hand-verifying against the real installed package.

## Why this task exists

There is **no executable guard** that asserts the orchestrator's actual calls
into `guardkitfactory.bdd` agree with the real installed `guardkitfactory`
signatures. A future `BDDRunResult` field rename, a `discover`/`run` arity
change, or a `StackProfile` field change in `guardkitfactory` would silently
re-break the Coach BDD bridge: the production `except Exception` at
`coach_validator.py` swallows the resulting `TypeError`/`AttributeError` and
degrades to the legacy fallback, so the autobuild loop never visibly fails
(`.claude/rules/absence-of-failure-is-not-success.md`,
`evidence-boundary-narrower-than-write-surface.md`).

This is the **direct analogue** of the harness `cancel()` seam test
(`tests/orchestrator/harness/test_xrepo_contract_seam.py`,
TASK-INFRA-XREPOCONTRACT), which asserts the orchestrator's required
constructor/method signatures against the *real installed* guardkitfactory via
`inspect`, run in the merge-gating `.github/workflows/seam-tests.yml`.

## Scope

Add a fast, `@pytest.mark.seam` cross-repo contract test (e.g.
`tests/orchestrator/test_bdd_xrepo_contract_seam.py`) that, against the **real
installed** `guardkitfactory` (not a fake):

1. Asserts `guardkitfactory.bdd.discover` has signature
   `discover(stack, worktree)` (2 positional params) via `inspect.signature`.
2. Asserts `BDDPlugin.run` has params `(self, scenarios, task_id, worktree, *, timeout_seconds=...)`.
3. Asserts `BDDRunResult` exposes exactly the fields the mapper reads
   (`scenarios_attempted/passed/failed/skipped/errored`, `duration_seconds`,
   `raw_report_path`, `discoveries`, `errors`) via `dataclasses.fields`.
4. Asserts `StackProfile` exposes the fields `_detect_stack_profile`
   constructs (`language`, `test_framework`, `package_manager`,
   `project_root`, `extras`).
5. Uses `importorskip("guardkitfactory")` so it is a clean no-op when the
   `[autobuild]` extra is absent — matching the existing seam-test idiom.

Wire it into the merge-gating `seam-tests.yml` job (it likely already collects
`-m seam`; confirm the new module is in scope).

## Acceptance Criteria

- [ ] A `@pytest.mark.seam` test module asserts `discover`/`run` arity and the
      `BDDRunResult`/`StackProfile` field sets against the **real installed**
      `guardkitfactory` via `inspect`/`dataclasses` (NOT a local fake).
- [ ] The test FAILS (red) if any of the four contracts above drifts — verified
      by a local mutation experiment (e.g. temporarily rename a `BDDRunResult`
      field and confirm the seam test goes red).
- [ ] `importorskip("guardkitfactory")` makes it a clean skip without the
      `[autobuild]` extra.
- [ ] The module is collected by `.github/workflows/seam-tests.yml` (the
      merge-gating job), confirmed by inspecting its `-m seam` selection.
- [ ] `python -m pytest -m seam -o addopts= -q` stays green on current main.

## Notes

- Keep it `inspect`/`dataclasses`-only (no subprocess, no LLM) so it runs in
  milliseconds, like `test_xrepo_contract_seam.py`.
- This guards the *contract surface* BDDFW01 corrected; it does NOT need to
  exercise a live BDD run (that is TASK-HMIG-BDDWIRE's remit).
- Consider co-locating with or extending the existing harness seam test so the
  whole guardkit ↔ guardkitfactory seam is covered by one CI job.
