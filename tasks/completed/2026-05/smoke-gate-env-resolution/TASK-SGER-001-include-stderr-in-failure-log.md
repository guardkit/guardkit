---
id: TASK-SGER-001
title: Include captured stderr/stdout in smoke-gate failure log and final-summary banner
task_type: implementation
parent_review: TASK-REV-61F1
parent_repo: specialist-agent
feature_id: FEAT-SGER
wave: 1
implementation_mode: direct
status: completed
priority: high
complexity: 2
dependencies: []
tags: [smoke-gates, autobuild, observability, diagnostics, recurring-bug-class]
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T12:35:00Z
completed: 2026-05-06T12:35:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied; 16/16 smoke-gate tests pass"
completed_location: tasks/completed/2026-05/smoke-gate-env-resolution/
---

# Include captured stderr/stdout in smoke-gate failure log

## Context

The autobuild's smoke-gate runner (`guardkit/orchestrator/smoke_gates.py:run_smoke_gate`)
captures stdout and stderr via `subprocess.run(..., capture_output=True)` and stores
both on the returned `SmokeGateResult` (lines 187, 252–254). But the failure-path
log at lines 240–247 emits only:

```
WARNING:guardkit.orchestrator.smoke_gates:Smoke gate failed after wave N (exit=X, expected=Y)
```

— the captured stderr is **discarded**. Operators see a single line with no
diagnostic and have to re-run the gate by hand to learn what actually failed.

This is a recurring class of opacity. It bit FEAT-61F1 (specialist-agent, wave 2,
2026-05-05), it bit FEAT-D40B (specialist-agent, wave 5, 2026-05-04 —
`autobuild-D40B-history.md:1142-1147`), and it will bite every future smoke-gate
failure until the log is fixed.

The data is already captured at the subprocess call site. This is a 5-line
log-statement change.

## Description

Update three call sites to surface captured output:

### Site 1 — Exit-mismatch failure path

`guardkit/orchestrator/smoke_gates.py` lines 240–247.

Extend the WARNING to include `proc.stderr` and `proc.stdout`. Suggested form:

```python
else:
    passed = False
    logger.warning(
        "Smoke gate failed after wave %d (exit=%d, expected=%d)\n"
        "stderr:\n%s\n"
        "stdout:\n%s",
        wave_number, proc.returncode, config.expected_exit,
        (proc.stderr or "(empty)").rstrip(),
        (proc.stdout or "(empty)").rstrip(),
    )
```

### Site 2 — Timeout path

`guardkit/orchestrator/smoke_gates.py` lines 192–205. The `subprocess.TimeoutExpired`
exception carries partial output as `exc.stdout` / `exc.stderr`, which are already
decoded into the returned `SmokeGateResult` but not logged. Add an equivalent
WARNING that surfaces what the gate produced before timing out — useful when a
gate hangs partway through a multi-statement script.

### Site 3 — Final-summary banner

`guardkit/orchestrator/feature_orchestrator.py` lines 2049–2059. The red banner
displayed via `console.print(...)` is the operator's first signal in interactive
runs. Append a stderr tail (last ~20 lines is sufficient — full output goes to the
log) so the banner is itself self-diagnosing.

Suggested form for the `reason` block:

```python
reason = (
    f"timed out after {smoke_result.timeout}s"
    if smoke_result.timed_out
    else f"exit={smoke_result.exit_code}, expected={feature.smoke_gates.expected_exit}"
)
stderr_tail = "\n".join((smoke_result.stderr or "").rstrip().splitlines()[-20:])
console.print(
    f"[red]✗ Smoke gate failed after wave {wave_number}[/red] ({reason}). "
    f"Subsequent waves not started; worktree preserved at {worktree.path}."
)
if stderr_tail:
    console.print(f"[red]stderr (last 20 lines):[/red]\n{stderr_tail}")
```

## Acceptance Criteria

- [ ] `smoke_gates.py:240-247` failure-path WARNING includes captured stderr and stdout.
- [ ] `smoke_gates.py:192-205` timeout path emits an equivalent WARNING with partial output.
- [ ] `feature_orchestrator.py:2049-2059` red banner includes a stderr tail (≤20 lines).
- [ ] No change to `SmokeGateResult` schema — the data is already there.
- [ ] No change to passing-path behaviour — only failure paths are updated.
- [ ] Tests in `tests/unit/orchestrator/test_smoke_gates_*.py` extended to assert
      that the failure-path WARNING text contains the captured stderr (use
      `caplog` or equivalent).
- [ ] At least one test asserts the timeout path also surfaces partial output.
- [ ] Existing `test_smoke_gates_exit5.py` and `test_smoke_gates_venv.py` tests
      continue to pass.

## Out of Scope

- Changing what gets captured. `capture_output=True` is already correct.
- Truncation policy for very long output. A 20-line tail in the banner is enough;
  the log gets the full text.
- Redaction of secrets from captured output. Not currently a concern for smoke gates
  (gates are import-and-assert scripts, not credential-handling code), but if it
  becomes one, file separately.

## Implementation Notes

- This is a low-risk single-file change at each site — `direct` mode is appropriate.
- The change is independent of TASK-SGER-002 and can land first; SGER-002 is the
  structural fix for the underlying environmental gap, but SGER-001 makes every
  future smoke-gate failure self-diagnosing regardless of root cause.
- Keep the WARNING format machine-parseable if the autobuild has any log-scraping
  consumers downstream — preserve the leading "Smoke gate failed after wave %d
  (exit=%d, expected=%d)" prefix.

## Test Execution Log

### 2026-05-06 — implementation + verification (interactive `/task-work`, minimal intensity)

**Files changed:**

- `guardkit/orchestrator/smoke_gates.py` — both failure paths (exit-mismatch and
  timeout) now emit captured stderr/stdout in the WARNING, with `(empty)`
  placeholders when a stream produced nothing. Machine-parseable prefix
  preserved (`"Smoke gate failed after wave %d (exit=%d, expected=%d)"` /
  `"Smoke gate timed out after %ds: %s"`).
- `guardkit/orchestrator/feature_orchestrator.py` — red banner appends a
  stderr tail (≤20 lines) on the exit-mismatch path. Unwired-gate banner
  unchanged (already actionable). Full output stays in the log per the
  task's truncation policy.
- `tests/unit/orchestrator/test_smoke_gates_failure_log.py` — new file,
  five `caplog`-based tests covering: exit-mismatch with stderr+stdout,
  empty-stream placeholder, timeout with bytes-typed partial output,
  timeout with no partial output, and a passing-path negative assertion
  (passing log must NOT echo captured streams).

**Verification:**

```
$ python -m pytest tests/unit/orchestrator/test_smoke_gates_failure_log.py \
                   tests/unit/orchestrator/test_smoke_gates_exit5.py \
                   tests/unit/orchestrator/test_smoke_gates_venv.py -v
============================== 16 passed in 2.26s ==============================
```

All five new tests pass. Both pre-existing test files
(`test_smoke_gates_exit5.py` 6 tests, `test_smoke_gates_venv.py` 5 tests)
continue to pass — no regression in exit-5 soft-warn / hard-fail
distinctions or venv PATH-prepend semantics.

`from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator`
imports cleanly post-change, confirming the banner edit didn't break the
module.

**Acceptance criteria status:** all eight items satisfied (failure-path log,
timeout-path log, banner stderr tail, no `SmokeGateResult` schema change,
no passing-path change, failure-path stderr assertion in tests, timeout
partial-output assertion in tests, existing tests still green).

**Out-of-scope items deferred per task description:** truncation policy
revisions (20-line banner tail is sufficient), secret redaction (smoke
gates are import-and-assert scripts, not credential code).
