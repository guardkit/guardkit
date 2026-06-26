---
id: TASK-FIX-DF44
title: Add collection_error classification to Coach test failure classifier
task_type: feature
parent_review: TASK-REV-0E44
feature_id: FEAT-CTD
status: backlog
created: 2026-03-01T00:00:00+00:00
updated: 2026-03-01T00:00:00+00:00
priority: high
tags:
  - autobuild
  - coach-validator
  - classification
  - seam-fix
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add collection_error Classification to Coach Test Failure Classifier

## Description

The Coach's `_classify_test_failure()` method has no category for pytest collection errors — cases where pytest cannot even import a test file (exit code 2). Currently, a `ModuleNotFoundError` during collection falls through to `("infrastructure", "ambiguous")` because the missing module name (e.g., `"tests"`) doesn't match `_KNOWN_SERVICE_CLIENT_LIBS`.

This is Seam Failure 2 from the TASK-REV-0E44 review. Adding a specific `"collection_error"` classification enables downstream approval logic to handle this case correctly.

## Acceptance Criteria

- [ ] New classification `("collection_error", "high")` returned when pytest output contains `"errors during collection"` or `"error collecting"`
- [ ] Collection error detection runs BEFORE the generic `ModuleNotFoundError` check
- [ ] Classification is logged at DEBUG level with the matched pattern
- [ ] Normal test execution failures (assertions, exceptions) are NOT classified as collection errors
- [ ] Mixed output (some collection errors + some test results) is correctly classified as collection error
- [ ] Unit tests cover: collection error output, normal failure output, mixed output, empty output

## Technical Context

- File: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Method: `_classify_test_failure()` (lines 2631-2719)
- Insert BEFORE the `ModuleNotFoundError` check (line ~2651)
- Existing classifications: `infrastructure` (high/ambiguous), `code` (high/n/a), `sdk_api_error` (high)
- New classification: `collection_error` (high)
- pytest exit code 2 = collection error (vs exit code 1 = test failure)

## Design Reference

- Review report: `.claude/reviews/TASK-REV-0E44-review-report.md` (Seam Failure 2, Fix 2)
- Evidence: `coach_turn_1.json` line 16 — `"Interrupted: 2 errors during collection"`

## Regression Risks

1. New `"collection_error"` class must be handled by all consumers → verify `validate()` handles it (Fix 3 adds explicit handling)
2. False positive on legitimate collection errors (syntax errors in test files) → these ARE collection errors and should be classified as such
3. Detection patterns must not match normal failure output → test with various pytest outputs

## Implementation Notes

[Space for implementation details]

## Addendum (2026-06-26) — extend to the SDK "no-marker / narration" capture

> Added from the FEAT-HARV autobuild session (see the handoff at
> `docs/handoff/autobuild-coach-test-gathering-handoff-2026-06-26.md`). Pair with
> `TASK-REV-COSE` (which diagnoses the *capture* root cause); this task owns the
> *classification + approval* side.

A second class of "independent test failed for non-deliverable reasons" was hit
in FEAT-HARV that this classifier should also cover. On the **SDK** independent
test path (`_run_tests_via_sdk`, the default `coach_test_execution=sdk`), the
harness does **not** surface the Bash tool's stdout as a `ToolResultEvent`, so the
captured `output_text` is the Coach **agent's narration** (e.g. `"I'll run the
test command and show you the full output."`), not pytest output. The heuristic
classifier then finds **no success marker and no failure marker**.

There is a load-bearing asymmetry that must be resolved deliberately:

- A **classified failure** (`infrastructure` / `collection_error` /
  `parallel_contention` / `code`-in-parallel-wave) + all gates pass →
  **conditional approval** ([coach_validator.py:2223](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L2223),
  TASK-ABFIX-005 / TASK-FIX-1D70). This is why FEAT-HARV's wave-1 002/004 passed
  despite "SDK independent tests failed".
- An **absent** signal (`signal_absent=True`) → **hard block** via Guard #6
  (INDEPENDENT-TEST ABSENT GUARD). Absent is treated as *stricter* than a
  classified failure — which is backwards.

A naïve "reclassify the no-marker narration as `signal_absent=True`" (attempted
and reverted this session, commit `437ebd8a`→`c649e069`) therefore caused a
**regression**: it moved the tolerated case into the hard-blocking absent path,
and 002/004 (green before) hit `max_turns_exceeded`.

### Additional Acceptance Criteria (this addendum)

- [ ] A no-marker SDK capture (the agent narrated but no pytest success/failure
      string was captured) is classified as a **conditional-approvable** class
      when all Player quality gates pass — NOT routed to the absent hard-block,
      and NOT left as a bare `tests_passed=False`. Treat it like
      `collection_error`: a non-deliverable verification artifact.
- [ ] The decision is reconciled against the **deterministic subprocess** result
      when available (the subprocess pytest is the reliable oracle; the SDK path
      is known-flaky). If the deterministic run passed, the SDK no-marker capture
      must not block.
- [ ] The absent-vs-classified asymmetry is resolved or explicitly documented:
      either an absent independent signal becomes conditional-approvable on
      all-gates-pass (consistent with classified failures), or Guard #6's
      stricter-than-fail behaviour is justified in a comment with the rationale.
- [ ] Genuine `code` failures (real assertion/exception output) are still
      ran-and-failed and still block — no masking of real failures.
- [ ] Unit tests cover: narration-only capture, empty/`No output` capture,
      `collected 0 items`, genuine pass, genuine failure, mixed output.

### Evidence

- FEAT-HARV TASK-HARV-003 `coach_evidence_turn_*.json`:
  `independent_tests.raw_output` = `"\nI'll run the test command and show you the
  full output.\n"`, `signal_absent=true`, while the deterministic subprocess
  pytest reported `status=passed tests_run=8601 tests_failed=0` every turn.
- The known harness limitation is documented in `coach_validator.py`
  `_run_tests_via_sdk` (the `ToolResultEvent` note) — origin TASK-HMIG-006.3.

## Test Execution Log

[Automatically populated by /task-work]
