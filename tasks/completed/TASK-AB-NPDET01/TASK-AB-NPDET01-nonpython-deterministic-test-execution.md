---
id: TASK-AB-NPDET01
title: Extend AC-004 deterministic Phase-4 test execution to non-Python stacks (.NET/JS-TS/Go)
task_type: feature
status: completed
created: 2026-06-18T13:30:00Z
updated: 2026-06-18T15:00:00Z
completed: 2026-06-18T15:00:00Z
completed_location: tasks/completed/TASK-AB-NPDET01/
priority: medium
complexity: 5
parent_task: TASK-AB-PERTASKFG01
feature_id: FEAT-AB-PERTASKFG
tags:
  - autobuild
  - deterministic-test-execution
  - stack-agnostic
  - absence-of-failure
  - phase-4
falsifier: >
  After this task, a SINGLE-task non-Python autobuild wave whose worktree has a
  .NET (*.csproj/*.sln), Node (package.json), or Go (go.mod) marker and no
  Python task-specific tests runs Phase-4 tests via a deterministic subprocess
  (`dotnet test` / `npm test` / `go test ./...`) — NOT the LLM test-orchestrator
  specialist — so a tool-call-shy model cannot hang the test phase. A missing
  toolchain (exit 127 / "command not found"), a zero-test run (`go test ./...`
  with no test files at exit 0; `dotnet test` "No test is available"; npm
  "no test specified"/"missing script") maps to signal_absent (UNKNOWN, never a
  pass). A genuine compile/test failure stays ran-and-failed. A PARALLEL
  (wave_size>1) non-Python wave still defers to the LLM specialist (whole-suite
  commands would attribute sibling tasks' failures to this task). If any of
  these is false, the task is not done.
---

# Task: Non-Python deterministic Phase-4 test execution

## Provenance

Follow-up to **TASK-AB-PERTASKFG01 AC-004** (the per-task verification
false-green fix, 2026-06-18). AC-004 made Phase-4 test EXECUTION deterministic
(a venv-pinned `pytest` subprocess — no LLM in the loop, so it cannot hang) for
**Python only**. Non-Python stacks still fall back to the LLM `test-orchestrator`
specialist, which retains the tool-call-shy-model hang risk (gpt-oss emitting no
tool call → 150s watchdog → `tests_run=0` false-green) that motivated PERTASKFG01.
Flagged as the open "(Optional) non-Python deterministic test execution"
follow-up in `docs/retro/session-handoff-2026-06-18-pertaskfg01-false-green-closed.md`
§122 item 2.

## Design (Option B — declarative stack registry)

Adjudicated by a 3-architect + adversarial-judge design panel (2026-06-18).
**Letter-vs-spirit ruling on `.claude/rules/stack-plugin-architecture.md`:** the
rule's "execution → ABC + contract-gated loader plugin" row is grounded in the
`guardkitfactory/bdd/` reference impl, where each stack plugin exists to parse a
*different report FORMAT* (JUnit XML / .trx / cucumber-json). This Phase-4 oracle
has **no such surface**: `CoachValidator.run_independent_tests` already runs any
command via `subprocess.run(test_cmd, shell=True)` and the authoritative verdict
is uniform `returncode == 0` (`_parse_pytest_counts` is best-effort metadata
only, never the verdict). The plugin clause's precondition (heterogeneous result
parsing) is absent, so the rule's controlling clause is **"a new stack = a DATA
row, not a code plugin"** + **"isolate the stack assumption in a named module."**
A full plugin would wrap zero per-stack behaviour in ABC+loader ceremony and
would live in `guardkitfactory` (which the CI main suite runs *without* —
`ci-tests-yml-no-guardkitfactory`), forcing the safety-critical absent-classifier
tests off the merge gate. Option B is the proportional, rule-spirit choice.

## Completion note (2026-06-18)

All 5 ACs landed + verified. Implemented via a design panel (3 architects +
adversarial judge → Option B) and an adversarial verification panel (3 skeptics
+ adjudicator) that found **2 real high-severity holes, both fixed before
commit**:

1. **False-green (node exit-0 zero-test):** `npm test` with `jest/vitest
   --passWithNoTests` (or a bare `echo; exit 0` placeholder) exits 0 having run
   ZERO tests. Fixed with a positive **ran-marker precondition** for node
   (`success_requires_ran_marker` + `_NODE_RAN_MARKER`): an exit-0 run matching
   no mainstream-runner pass-marker is ABSENT, never a pass.
2. **False-red (`': not found'`):** the bare substring matched genuinely-passing
   output (an HTTP `404: Not Found`, a test title `id: not found`). Dropped from
   all three profiles; toolchain-missing is caught reliably by `returncode 127`.

Test counts: `test_stack_test_execution.py` (43), `test_coach_nonpython_det_execution.py`
(25), `test_specialist_wave_size_threading.py` (3). Affected regression suites
green (`test_coach_validator.py`, `test_coach_subprocess_tests.py`,
`test_specialist_invocations.py`, `test_coach_signal_absent_classifier.py`,
autobuild Phase-4 path). Full `tests/unit` collects clean (8487). dead-task-id
lint green.

## Acceptance Criteria

- [x] **AC-001** — New module
  `guardkit/orchestrator/quality_gates/stack_test_execution.py` (pure stdlib, no
  `guardkitfactory`/`langchain` imports — runs on main CI). Frozen
  `StackTestProfile` rows for `dotnet` / `node` / `go` (**python deliberately
  excluded** — the pytest path is untouched). `detect_stack_profile(worktree)`
  returns a profile only when **exactly one** stack's depth-0 marker globs match
  (zero or >1 → `None`, so a polyglot/vendored-`package.json` repo defers safely).
  `classify_absent_for_stack(profile, returncode, combined_output)` is
  absence-of-failure-safe: missing toolchain (rc 127/126, or "command not
  found"/"is not recognized"/"no .NET SDKs were found" — the bare `": not
  found"` substring was deliberately NOT used; it false-red'd passing output)
  → absent; zero-test markers → absent; the **go exit-0 mixed-module rule** —
  `go test ./...` prints `[no test files]` for testless packages even when other
  packages pass, so `[no test files]` counts as absent **only when no go
  pass-line (`^ok\s`) is present**; and the **node exit-0 ran-marker
  precondition** — node has no reliable zero-test phrase (`--passWithNoTests`
  exits 0; a bare `echo` placeholder prints nothing), so an exit-0 node run
  matching no mainstream-runner pass-marker (`_NODE_RAN_MARKER`) is absent. A
  genuine compile/test failure matches no absent pattern and stays
  ran-and-failed.
- [x] **AC-002** — `CoachValidator._detect_test_command` (task_id path): after the
  entire Python-first cascade (results → glob → git-diff → promises → prior-turns)
  returns `None`, consult `detect_stack_profile` — but **only when
  `not self.is_parallel`** (single-task wave). On a hit, set
  `self._active_stack_profile` and return the whole-suite command; in a parallel
  wave (or no hit) return `None` (defer to the LLM specialist). The Python
  task-specific path is byte-for-byte unchanged (it filters to task-specific
  `.py` files and is already parallel-safe).
- [x] **AC-003** — `CoachValidator.run_independent_tests` subprocess branch:
  when `self._active_stack_profile` is set, compute `signal_absent` via
  `classify_absent_for_stack` on **both** the success and failure branches (the
  exit-0 zero-test guard), and force `tests_passed=False` whenever
  `signal_absent` is True (honour the `IndependentTestResult` invariant). The
  existing pytest-only absent classifier (the TASK-AB-PERTASKFG01 fix:
  runner-absent / exit-5 / conftest-collection-failure) is **left byte-for-byte**
  and stays the path when no stack profile is active.
- [x] **AC-004** — `wave_size` threaded end-to-end so the parallel-wave guard is
  real: `autobuild.py` `invoke_test_orchestrator(...)` call →
  `invoke_test_orchestrator(wave_size=...)` → `_run_deterministic_phase_4(wave_size=...)`
  → `CoachValidator(wave_size=...)`. (Currently the deterministic runner
  constructs `CoachValidator` without `wave_size`, so it always believes
  `wave_size=1` — the guard would be a no-op without this.) Default `1` preserves
  back-compat for SDK-fallback/direct callers.
- [x] **AC-005** — Tests (all under `tests/unit/`, no `guardkitfactory`):
  registry+classifier table per stack incl. the go exit-0 mixed (`ok`+`[no test
  files]` → ran-and-passed) and empty (`[no test files]` only → absent) cases;
  `run_independent_tests` with an active dotnet/node/go profile (missing
  toolchain → absent, ran-and-failed → not absent, exit-0 zero-test → absent);
  `_detect_test_command` detection + the `wave_size>1` parallel guard returning
  `None`; `wave_size` threading reaches `CoachValidator` (construction spy); and a
  **regression pin** that all existing pytest absent cases stay green unchanged
  (TASK-AB-PERTASKFG01 not regressed).

## Default policy

Default-**on** for non-Python, governed by the **same existing valve** as
Python: `GUARDKIT_PHASE4_TEST_EXECUTION` (default `subprocess`; `=sdk` reverts
the whole deterministic path for all stacks). No new env var. Safe to default-on
because the classifier is absence-of-failure-safe.

## Scope residual (explicit — NOT silently "closed")

- **Non-Python PARALLEL (wave_size>1) waves still fall back to the LLM
  test-orchestrator specialist** and retain the pre-existing tool-call-shy-model
  hang risk. The deterministic runner only takes over for SINGLE-task non-Python
  waves. Per-stack task-specific test filtering (to lift the parallel guard for
  non-Python, the way the Python path filters to task-specific `.py` files) is a
  separate, larger task.
- The deterministic non-Python path is a pass/fail oracle (coverage_pct left at
  default `0.0`), parity with the Python deterministic path; it does NOT collect
  coverage the way the LLM specialist's `--collect "XPlat Code Coverage"` /
  `npm test --coverage` did.
- **Environment-failure narrowness (accepted trade-off):** a non-Python suite
  that cannot run for an env reason OUTSIDE the recognised toolchain-absent set
  (offline NuGet `NU1101`, missing `node_modules` `Cannot find module`, a go
  module-proxy DNS failure) is classified ran-and-failed, not absent. This is
  feedback-direction-only (never a false APPROVAL) and is at exact parity with
  the Python deterministic path (a missing-app-dep pytest failure is likewise
  ran-and-failed — the TASK-AB-PERTASKFG01 "missing app dep is a real failure"
  precedent). The env bootstrap (AC-003) installs deps before the loop, so the
  normal flow has them. Widening the absent set to cover arbitrary env failures
  is out of scope.
- **node bare-placeholder residual:** the node exit-0 zero-test guard is a
  positive ran-marker precondition covering the mainstream runners
  (jest/mocha/vitest/jasmine/ava/tap/node:test). A *custom* runner whose passing
  output matches none of those markers is bounced as absent (fail-toward-
  feedback, recoverable), not approved — the safe direction.

## Key references

- Parent: `tasks/completed/TASK-AB-PERTASKFG01/`
- Rules: `.claude/rules/stack-plugin-architecture.md` (letter-vs-spirit),
  `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/per-task-green-is-not-feature-green.md`
- Code: `guardkit/orchestrator/specialist_invocations.py:992` (`_run_deterministic_phase_4`),
  `guardkit/orchestrator/quality_gates/coach_validator.py:4105`
  (`run_independent_tests`), `:5884` (`_detect_test_command`), `:4322-4359`
  (pytest-only absent classifier — leave untouched)
