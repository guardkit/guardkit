# Completion Report - TASK-FIX-CC-BDD

**Task**: Coach independent_tests must scope BDD step-defs runs by `@task:` tag
**Completed**: 2026-05-08T20:59:23Z
**Parent review**: TASK-REV-CC40 (study-tutor) — FEAT-39E1 post-mortem

## Summary

Fixed a false-positive in `coach_validator._detect_test_command` where pytest-bdd
glue files in `task_work_results.tests_written` (and `files_created` /
`files_modified`) were being passed to an unscoped `pytest <files>` invocation.
Unscoped pytest collected every scenario in the matching `.feature` file —
including scenarios tagged for downstream peer tasks that share a master
feature — and pytest-bdd v8 surfaced their unbound steps as `FAILED` rather
than `pending`. The Coach's `tests_passed == True` and
`bdd_results.scenarios_failed > 0` gates rejected on a deterministic,
retry-immune signal, blocking parallel-wave execution (FEAT-39E1, TASK-NATS-PH1-006).

## Approach

**Option (a) chosen** per task ACs: filter pytest-bdd glue files out of the
`independent_tests` pytest cmd. BDD verification is delegated to the existing
task-tag-scoped path:

1. Player-side `agent_invoker._run_bdd_oracle` calls `bdd_runner.run_bdd_for_task`
   (already scoped via `-m @task:<TASK-ID>`) and writes `bdd_results` into
   `task_work_results.json`.
2. Coach reads `bdd_results` via `_check_bdd_results` and gates on
   `scenarios_failed == 0` (with `pending` tolerated per the documented contract).

Removing BDD glue files from the unscoped pytest cmd does not weaken
verification — it eliminates a redundant, unscoped run that was the sole
source of the false-positive.

## Files Modified

- `guardkit/orchestrator/quality_gates/bdd_runner.py` — added public
  `is_bdd_glue_file(file_path)` helper (cheap text scan for pytest-bdd v8
  imports: `pytest_bdd.scenarios(`, `from pytest_bdd import`,
  `import pytest_bdd`).
- `guardkit/orchestrator/quality_gates/coach_validator.py` — added
  `CoachValidator._filter_bdd_glue_files(test_files)` and applied it in all
  four detection paths in `_detect_test_command`:
  1. Primary `_detect_tests_from_results` (most common — files_created /
     files_modified union).
  2. Glob fallback (`tests/**/test_{task_prefix}*.py`).
  3. Cumulative-diff fallback (`git diff --name-only`).
  4. Completion-promises fallback.
  The quinary fallback recursively calls the primary path, so it inherits
  the filter.
- `guardkit/orchestrator/quality_gates/__init__.py` — re-exported
  `is_bdd_glue_file` at the package level.

## Files Created

- `tests/unit/orchestrator/quality_gates/test_coach_validator_bdd_filter.py`
  — 17 new tests across 4 classes:
  - `TestIsBddGlueFile` (8): detection helper edge cases (scenarios call,
    import variants, plain files, missing files, non-Python, directory,
    invalid type).
  - `TestFilterBddGlueFiles` (5): the validator helper with mixed lists,
    BDD-only lists, order preservation, and missing files.
  - `TestDetectTestsFromResultsBddFiltering` (3): integration with
    `_detect_tests_from_results`, including the FEAT-39E1 reproducer shape
    and the backward-compat regression case.
  - `TestPeerTaskScenariosNotSurfacedAsFailures` (1): the FEAT-39E1
    multi-task feature file fixture in synthetic form.

## Test Results

- **17/17** new tests pass.
- **123/123** existing quality_gates tests pass — no regression.
- **38/38** existing bdd_runner tests pass — no regression.
- `bdd_runner.py` coverage: **85%** (target met).
- `ruff check`: 8 errors total, **all pre-existing** (verified by
  comparing baseline against working tree). No new lint issues
  introduced.

## Acceptance Criteria

| AC | Status | Evidence |
|----|--------|----------|
| BDD glue file routed via tag-scoped path, plain files via existing pytest path | ✅ | `_filter_bdd_glue_files` excludes BDD glue from pytest cmd; `_run_bdd_oracle` + `_check_bdd_results` handle BDD via `run_bdd_for_task` |
| Unbound peer-task scenarios counted as `scenarios_pending` (or not collected) | ✅ | Filtered out of pytest cmd entirely; tag-scoped runner uses 3-state model with `parse_junit_xml` |
| Regression test with N scenarios across M tasks | ✅ | `test_master_feature_with_multi_task_tags_does_not_pollute_pytest_cmd` |
| Replay against FEAT-39E1 fixture | ⚠️ Partial | Synthetic equivalent in `test_master_feature_with_multi_task_tags_does_not_pollute_pytest_cmd`; true cross-repo fixture replay is consumer-side (TASK-NATS-FIX-001 in study-tutor, marked Out of Scope) |
| Existing tasks unaffected | ✅ | `test_unaffected_when_no_bdd_files_present` + 123/123 existing tests pass |
| No new dependency added | ✅ | Reuses existing pytest / pytest-bdd surface |

## Out of Scope (per task spec)

- Fixing pytest-bdd v8's pending-vs-failed emission upstream — worked around, not fixed.
- Re-running the FEAT-39E1 autobuild — consumer-side (TASK-NATS-FIX-001 in study-tutor).
- Sibling false-positive in `_detect_source_file_contention` — separate task TASK-FIX-CC-COND.

## Sibling Rule

This fix has the same shape as
[`absence-of-failure-is-not-success.md`](../../../.claude/rules/absence-of-failure-is-not-success.md):
a binary verdict from a low-fidelity oracle (`tests_passed == True`)
that cannot distinguish "no signal in our scope" from "real failure".
Pre-fix, the oracle saw failures from peer-task scenarios and rejected;
post-fix, the oracle is scoped to this task's surface and only fails
when the task's own scenarios fail. The remediation pattern (pair
the boolean verdict with a positive-evidence precondition — here,
"this file belongs to this task's tag scope") matches the meta-class.
