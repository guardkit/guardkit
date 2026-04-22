---
id: TASK-FIX-F584
title: "R2 BDD oracle silently approves pytest usage errors (Outcome D defect)"
status: completed
task_type: bugfix
severity: P0
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T14:00:00Z
completed: 2026-04-22T14:30:00Z
priority: high
complexity: 4
tags: [r2, bdd-oracle, bugfix, p0, blocks-cohort, task-bdd-e8954]
parent_defect_evidence: .claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md
blocks: [TASK-COH-RUN1]
defect_against: TASK-BDD-E8954
depends_on: []
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-F584/
organized_files:
  - TASK-FIX-F584.md
state_transition_reason: "Completed via /task-complete. Spot-checks confirmed all 12 ACs actually implemented (not just checkbox-ticked): returncode-handling branch at bdd_runner.py:519 synthesises FailureDetail for returncodes 2/3/4, rglob at :155, 8 new tests present and named per ACs, post-fix jarvis probe section at .claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md:197, and test run green (36/36 passing in 2.01s). Implementation plan preserved at docs/state/TASK-FIX-F584/implementation_plan.md. Resolves block on TASK-COH-RUN1 (R2 silent-false-approval fixed)."
test_summary:
  added: 7
  passing: 36
  coverage_module: "86%"
  module: "guardkit/orchestrator/quality_gates/bdd_runner.py"
follow_up_tasks:
  - "parse_junit_xml empty-parse signalling (noted in-file, out of scope here)"
---

# Task: Fix R2 silent-false-approval on pytest usage errors

## Problem Statement

`guardkit.orchestrator.quality_gates.bdd_runner.run_bdd_for_task()` can return `BDDResult(scenarios_passed=0, scenarios_failed=0, scenarios_pending=0, failures=[], pending=[])` when the underlying `pytest` subprocess errors with returncode ≠ 5. Coach's approval rule is `bdd_results.scenarios_failed == 0`, so such a result is silently **approved** even though nothing actually ran.

Discovered during TASK-BDD-JBKF backfill verification. Reproduces on any `@task:`-tagged jarvis-style feature whose environment lacks pytest-bdd step-def glue — pytest exits with returncode **4** (USAGE_ERROR: "not found"), the runner's silent-skip path (`bdd_runner.py:430-441`) only guards `returncode == 5` (NO_TESTS_COLLECTED), and the `parse_junit_xml("")` path produces all-zero counters.

This is a strictly worse failure mode than either of the defects originally enumerated:
- Not a pending-collapse-into-failed (Outcome B): no false block.
- Not a silent-skip-via-path-3 (Outcome C): no `None` for the caller to null-check.
- Instead: **silent false green**, approving an implementation with zero verification.

Full evidence (probes, raw pytest output, exit codes): `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md`.

## Reproduction

```bash
# In a checkout of any project that has an @task:<ID>-tagged .feature file
# but no pytest-bdd step-def glue:
python3 -c "
from pathlib import Path
from guardkit.orchestrator.quality_gates.bdd_runner import run_bdd_for_task
r = run_bdd_for_task(
    task_id='TASK-J001-001',
    worktree_path=Path('/path/to/project'),
    python_executable='/path/to/venv/bin/python',  # venv with pytest-bdd installed
    features_subdir='features/<nested-dir-if-any>',
)
print(r.to_dict() if r else None)
# Actual:   {'scenarios_passed': 0, 'scenarios_failed': 0, 'scenarios_pending': 0, ...}
# Expected: None (silent-skip) or scenarios_failed > 0 (explicit runner-error)
"
```

## Root Cause

`bdd_runner.py:430-441`:

```python
if (
    passed == 0
    and not failures
    and not pending
    and invocation.returncode == _PYTEST_EXIT_NO_TESTS  # == 5
):
    return None
```

Guard is too narrow. pytest exits 4 (usage error), 3 (internal error), or 2 (interrupted) all produce the same `(0, 0, 0, [], [])` parse from empty/incomplete JUnit XML, but only returncode 5 is caught.

## Acceptance Criteria

### Primary fix (runner-error surfacing)

- [x] `run_bdd_for_task()` MUST NOT return `BDDResult(0, 0, 0, [], [])` for any pytest invocation with `returncode != 0`. Either return `None` (expand silent-skip) OR return a `BDDResult` with a synthetic `FailureDetail(reason="pytest_runner_error: exit=N")` such that `scenarios_failed > 0` and Coach's approval rule catches it.
- [x] Preferred choice: **surface as failure**, not silent-skip, so Coach feedback explicitly names the runner error rather than treating the task as BDD-not-applicable. Rationale: a tagged feature file is explicit opt-in to R2 verification — silent skip of that opt-in is too quiet.
- [x] Unit test exercising this path. Suggested setup: monkeypatch `_invoke_pytest_bdd` to return `_PytestInvocation(returncode=4, stdout="ERROR: not found: ...", stderr="", junit_xml="")` and assert the result surfaces as a failure (or `None`, per fix decision).
- [x] Cover the same path for returncode 2 (interrupted) and 3 (internal error) explicitly.
- [x] **End-to-end Coach-rejection test**: assert that the post-fix `BDDResult` (with `scenarios_failed > 0` on runner error) actually causes Coach's approval validator to reject. If wiring Coach into the test is awkward, a tracer-style assertion directly on `result.scenarios_failed > 0` is acceptable PROVIDED it carries an explanatory comment citing the Graphiti-captured approval rule (`bdd_results.scenarios_failed == 0 ⇒ approve`), so the linkage to Coach behaviour is preserved in the test.

### Bundled: nested-feature discovery (rglob)

- [x] Extend `find_feature_files_with_tag` from non-recursive `features_dir.glob("*.feature")` to recursive discovery (`rglob` or equivalent). Nested layouts like `features/<feature-slug>/<feature-slug>.feature` (jarvis's `/feature-spec` scaffold convention) MUST be found under the default `features_subdir="features"`.
- [x] Unit test with nested layout.
- [x] **Filter-out test**: confirm `.feature` files under `.venv/`, `node_modules/`, `.git/`, and other dotdirs are NOT discovered by the recursive walk. Mitigates blast-radius concern from scope review — ensures the recursive switch does not pull in vendored/third-party feature files.

### Post-fix verification (in-task)

- [x] Re-run the TASK-BDD-JBKF probe (`.claude/reviews/jbkf_probe.py`) against jarvis with the fix applied and confirm Outcome D no longer occurs; update `TASK-BDD-JBKF-r2-backfill-evidence.md` with a "Post-fix re-run" section. Budget **~15–30 min** for throwaway jarvis venv setup/teardown in addition to script execution.

## Secondary Defect (Bundled — see rglob ACs above)

`find_feature_files_with_tag` uses a **non-recursive** glob (`features_dir.glob("*.feature")`). Jarvis's `/feature-spec` scaffold produces nested layouts like `features/<feature-slug>/<feature-slug>.feature`. Any cohort task following that convention silent-skips via path (1) without this fix.

Scope decision (2026-04-22): bundled into this task — one-line fix + test, shared test infrastructure, both defects block TASK-COH-RUN1, and the filter-out test covers the blast-radius concern of switching glob → rglob.

## Implementation Notes

- The cleanest fix is in `_invoke_pytest_bdd` or `run_bdd_for_task` — inspect the returncode and raw output after `parse_junit_xml` returns all-zero. If runner errored and nothing was collected, emit a synthetic `FailureDetail` naming the exit code and the first ~200 chars of stderr/stdout.
- Consider also emitting a logger.warning at INFO level so Coach's human-readable feedback surfaces the runner error, not just the `scenarios_failed` counter.
- Keep the `returncode == 5` silent-skip path intact — "no tests collected, feature tag present but no matching scenario" is a legitimate skip (tag in a comment, etc.); conflating that with usage errors would over-fire.
- `parse_junit_xml("")` returning `(0, 0, 0)` rather than signalling empty-parse is an upstream contributor to this class of bug — the runner has to reconstruct "nothing ran" from the empty parse plus the returncode, rather than getting a clear signal from the parser. Worth a defensive follow-up task (e.g., return `Optional[tuple]` or raise) but out of scope here.

## Priority Rationale (P0 / blocks cohort)

- Directly produces **false green** for any cohort task that lacks pytest-bdd glue in its env.
- Affects the exact failure mode that caused TASK-BDD-JBKF to be authored in the first place: "R2's runner has never been exercised against real cohort code. Until it has, we don't know whether the wiring actually works end-to-end."
- Answer from this defect: **it does not work end-to-end**; it silently approves unrun scenarios.
- Forge and study-tutor cohort runs must not proceed until this is fixed, or they risk a wave of silently-approved tasks whose BDD oracle signal is meaningless.

## Related

- Evidence: `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md`
- Parent verification task: `tasks/in_progress/TASK-BDD-JBKF-backfill-r2-on-jarvis-feature-file.md`
- Original R2 delivery: `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md`
- Blocks: TASK-COH-RUN1 (forge/study-tutor cohort — must not start until this fix ships)
