---
id: TASK-FIX-COACHPYENV
title: Coach independent tests run under the wrong interpreter (3.14 framework pytest, not the bootstrap venv)
status: completed
task_type: bug
created: 2026-06-07T13:00:00Z
updated: 2026-06-07T14:45:00Z
completed: 2026-06-07T14:45:00Z
completed_location: tasks/completed/autobuild-harness-migration/
previous_state: in_review
state_transition_reason: "task-complete — interpreter pin implemented, 23 tests pass, zero regressions"
priority: high
complexity: 4
effort_hours: 3
deadline: 2026-06-15
parent_review: TASK-REV-AOF-RUN9
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
related_tasks:
  - TASK-FIX-COACHBUDG01      # once Coach can emit verdicts, a spurious test-fail = spurious reject
  - TASK-FIX-COACHBUDG01-LG   # guardkitfactory — the reasoning fix this interacts with
surfaced_in: ../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md
tags:
  - autobuild
  - coach
  - quality-gates
  - substrate-robustness
  - interpreter-parity
falsifier: "After landing, the Coach's independent test execution (`coach_validator`, `coach_test_execution=sdk`) runs pytest under the worktree bootstrap venv interpreter (`.guardkit/worktrees/<FEAT>/.venv/bin/python`), NOT the host Python 3.14 framework pytest. Re-running the run-9 IA03 turn-1 Coach validation no longer logs `which pytest=/…/Python.framework/Versions/3.14/bin/pytest`, the Pydantic-V1-on-3.14 incompatibility warning does not appear in the Coach test phase, and a Player turn that is genuinely correct yields passing independent tests (no spurious reject)."
---

# Task: Fix Coach independent-test interpreter mismatch (Finding N from TASK-REV-AOF-RUN9)

## Why this task exists

In run-9, the Coach validator reported its independent tests as **failed** on both
turns (`SDK independent tests failed in 216.7s` / `188.0s`). The run-9 readiness
review (`TASK-REV-AOF-RUN9`, Finding N) traced a likely cause:

- Bootstrap set the Coach pytest interpreter correctly:
  `Coach pytest interpreter set from bootstrap venv: …/.venv/bin/python` (run-9 L66-67).
- **But** the Coach test-execution env reported a different interpreter:
  `Test execution environment: sys.executable=/usr/local/bin/python3,
  which pytest=/…/Python.framework/Versions/3.14/bin/pytest` (run-9 L255/L461) —
  the host Python 3.14 framework pytest, which emits *"Core Pydantic V1
  functionality isn't compatible with Python 3.14 or greater"* (L116).

If the Coach validates against the wrong interpreter, its independent tests can
**fail spuriously** (env/dependency incompatibility, not Player-code defects).
That matters acutely **once `TASK-FIX-COACHBUDG01(-LG)` lands**: a Coach that can
finally emit a verdict will turn a spurious test failure into a **spurious turn-1
reject** → forces a turn 2 → blows the feature `task_timeout`. This defeats the
"pass the next run" goal *independently of the reasoning fix*.

Confidence at review time: **medium** — inferred from env log lines; the Coach's
actual pytest stdout was not in the run-9 log. **Step 1 is to confirm.**

## What to do

1. **Confirm** (cheap): inspect `coach_validator`'s independent-test execution path
   (`coach_test_execution=sdk`). Determine which interpreter actually runs pytest
   and whether the bootstrap venv interpreter (set at feature setup) is threaded
   through to the SDK test invocation. Pull a real Coach pytest stdout to settle
   whether the run-9 failures were genuine or interpreter-induced.
2. **Fix** (if confirmed): ensure the Coach runs independent tests under the
   worktree bootstrap venv interpreter, not `sys.executable` / host `which pytest`.
3. **Guard:** add a regression assertion that the resolved test interpreter equals
   the configured bootstrap venv interpreter; log a loud warning on mismatch.

## Acceptance criteria

- [x] **AC-1:** Root cause confirmed and documented in
  `docs/state/TASK-FIX-COACHPYENV/findings.md`. Structural confirmation (code
  reading) — stronger than the single captured stdout run-9 did not preserve:
  `CoachValidator` never received `venv_python`, so the SDK path resolved
  `pytest` via host PATH (3.14 framework) and the subprocess path used
  `sys.executable`. Interpreter-induced, not Player-code defect.
- [x] **AC-2:** Coach independent tests run under the bootstrap venv interpreter.
  SDK command rewritten to `<venv> -m pytest …`; subprocess argv pinned to the
  venv interpreter; diagnostic now logs `resolved_interpreter`. Unit-locked by
  `TestCoachValidatorInterpreter`.
- [~] **AC-3:** Structurally satisfied + unit-locked (a known-correct turn now
  runs under the bootstrap interpreter, removing the spurious-reject mechanism).
  Final live confirmation on the `/v1/responses` substrate is the next FEAT-AOF
  run — this AC is itself the run-level falsifier.
- [x] **AC-4:** Mismatch guard added (loud WARNING when configured bootstrap venv
  ≠ resolved interpreter) + regression tests in
  `tests/orchestrator/test_coach_interpreter_selection.py`.

## Completion note (2026-06-07)

**Files changed:**
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `venv_python` param
  + `_resolve_venv_python` reuse; `_pytest_interpreter` / `_pin_pytest_command`
  / `_pytest_env` helpers; both subprocess paths and the SDK path pinned;
  `_patched_path` PATH prepend (defence-in-depth); mismatch guard; diagnostic.
- `guardkit/orchestrator/autobuild.py` — thread `venv_python=self._venv_python`
  into both `CoachValidator(...)` sites (primary @ ~5566, legacy @ ~5422).
- `tests/orchestrator/test_coach_interpreter_selection.py` — +7 regression tests.

**Tests:** `tests/orchestrator/test_coach_interpreter_selection.py` 23 passed.
Broader coach_validator suites: 284 passed, 13 failed — the 13 are **pre-existing
and environmental** (local `.venv` is Python 3.10; the SDK path uses
`asyncio.timeout`, a 3.11+ API). Identical pass/fail counts on baseline `main`
(stash-verified) → zero regressions from this change.

**Reuse / DRY:** uses the existing `_resolve_venv_python` (TASK-FIX-7A05) and
`build_venv_env` helpers rather than re-implementing interpreter resolution —
this is the inverse-shape sibling of the CoachVerifier 7A05 fix.

## Out of scope

- The Python 3.14 / Pydantic V1 portfolio dependency debt itself (anomaly J).
- The reasoning-extraction fix (guardkitfactory, COACHBUDG01-LG).

## References

- Review (Finding N): `../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`
- Run-9 log L66-67, L116, L254-257, L461, L276, L473
- `coach_validator` (guardkit orchestrator quality gates)
