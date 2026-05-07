# Implementation Guide — autobuild-feat-pebr-failure-recovery-rev2

**Parent review**: [TASK-REV-PEBR-002](../../../../forge/tasks/backlog/forge-autobuild-runner-pipeline-emitter-bridge/TASK-REV-PEBR-002-analyse-autobuild-failed-run-2.md)
**Review report**: [docs/reviews/FEAT-PEBR-failed-run-2-analysis.md](../../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md)
**See also**: [README.md](./README.md) for the failure narrative.

## Wave Plan

There is **no wave dependency** between the four guardkit tasks —
they touch four different files and four different code paths:

- `TASK-GK-CV-001` → `guardkit/orchestrator/quality_gates/coach_validator.py`
- `TASK-GK-PA-002` → `guardkit/orchestrator/agent_invoker.py`
- `TASK-GK-COACH-001` → `guardkit/orchestrator/autobuild.py`
- `TASK-GK-BS-001`   → `guardkit/orchestrator/environment_bootstrap.py` + feature_loader

All four can land in **parallel** as separate PRs. The forge-side
TASK-FRR-PEB-FM-002 is also independent (forge repo, task-file edit
only).

| Wave | Tasks                                                                  | Conductor parallel? | Notes |
|------|------------------------------------------------------------------------|---------------------|-------|
| 1    | TASK-GK-CV-001, TASK-GK-PA-002, TASK-GK-COACH-001                     | ✅ yes (3-up)       | Original rev-2 set; independent files |
| 2    | TASK-GK-BS-001                                                         | n/a (single)        | Discovered in run-3; independent surface |

(The forge task lives in a different repo and is not part of any
guardkit wave.)

The Wave-1 / Wave-2 split is **organisational only** — there is no
build-time dependency. Wave-1 fixes the per-task adversarial loop
(rev-2 surface); Wave-2 fixes the bootstrap so smoke gates can
actually execute (run-3 surface). They can land in either order.

## Recommended Landing Order

For maximum safety, land in this order **even though they're
parallelisable**:

1. **TASK-GK-CV-001 (Bug B) first**, because it is the smallest,
   highest-leverage change (one line: delete the
   `^AC-\d+:\s*` strip in `_strip_criterion_prefix`). Closes
   `criteria_met=0` regressions for every task in every feature.
2. **TASK-GK-PA-002 (Bug A) second**, because it is the largest
   logical change (introduces a new helper that consults
   `## Files to Create` / `## Files to Modify` from the task body
   when no `docs/state/` plan exists). Closes the FRR-PEB family of
   prose-trap stalls.
3. **TASK-GK-COACH-001 (Bug C) third**, because it is a
   defence-in-depth fix for a class of stall that becomes much
   rarer once Bug B is fixed. Smaller surface (~10 lines) but lower
   urgency.

Operator can flip the order without consequence — the three PRs do
not conflict.

## Cross-Repo Coordination

The forge-side fix (`TASK-FRR-PEB-FM-002`) can land **any time
before run-3**, independent of the guardkit fixes. The guardkit
fixes do **not** require the forge fix to land first; they can be
unit-tested standalone in the guardkit repo with synthetic fixtures.

Final validation is a forge-side autobuild run-3 (see README.md
"Validation Plan"). That run requires all four tasks to have landed.

## Test Strategy

Each task spec lists its own ACs and test fixtures. Common patterns:

- **Repro fixture**: each guardkit task includes a unit-test fixture
  that reproduces the FEAT-PEBR run-2 signature for that bug. Tests
  must fail on `main` and pass on the fix branch.
- **Regression suite**: each task must keep
  `tests/unit/test_coach_validator.py`,
  `tests/unit/test_agent_invoker.py`, and
  `tests/integration/quality_gates/` green. These are large
  test suites; budget ~5 minutes for a full run.
- **No new external dependencies**: all three fixes are pure-Python
  changes; no new imports, no new files outside `tests/`.

## Worktree Hygiene

The forge worktree at
`forge/.guardkit/worktrees/FEAT-PEBR/` is the verification artefact
for run-3. **Do not delete it.** All three guardkit fixes can be
developed and tested entirely within the guardkit checkout; the
forge worktree is only consumed at the final validation step.

## Out of Scope (rev 2)

These items were considered and explicitly **not** added to the
recommended set:

- **Renaming `_scan_ac_for_missing_paths`** to match its body-wide
  scope. Cosmetic; can fold into TASK-GK-PA-002 or a follow-up
  cleanup task.
- **Operator-feedback truncation reordering** (rev-1 review item
  #4). Carried over but P2 priority; not on the unblock critical
  path.
- **Auto-stub plan enrichment** from the task body's `## Files to
  Create` / `## Files to Modify` sections (rev-2 review item #6).
  Defence-in-depth that becomes valuable once TASK-GK-PA-002 lands.
  Open a separate task once the rev-2 unblock has been verified.

These can be triaged after run-3 validation passes.
