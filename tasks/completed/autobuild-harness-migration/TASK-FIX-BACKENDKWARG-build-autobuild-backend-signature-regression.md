---
id: TASK-FIX-BACKENDKWARG
title: Fix build_autobuild_backend() signature regression — max_tool_result_chars kwarg crashes every SDK invocation
status: completed
task_type: fix
created: 2026-06-10T00:00:00Z
updated: 2026-06-11T00:00:00Z
completed: 2026-06-11T00:00:00Z
completed_location: tasks/completed/autobuild-harness-migration/
previous_state: in_review
state_transition_reason: "All ACs satisfied; Shape 2 + AC-2..AC-5 tests green; AC-1 already satisfied in guardkitfactory"
priority: high
complexity: 3
parent_task: TASK-PERF-COACHTURNBUDGET
related: [TASK-PERF-COACHTURNBUDGET, TASK-PERF-COACHSYNTH, TASK-INFRA-XREPOCONTRACT]
implementation_mode: task-work
intensity: strict
tags: [autobuild, harness, cross-repo, regression]
---

# Task: Fix build_autobuild_backend() signature regression

## Why this task exists

Run-24 **failed in 25 seconds, 0/3 tasks** — a code regression, not a substrate
issue. `guardkit/orchestrator/harness/selector.py:301` now passes a
`max_tool_result_chars` kwarg to `build_autobuild_backend()` (the
guardkitfactory backend constructor), but **that function's signature was not
updated to accept it**:

```
TypeError: build_autobuild_backend() got an unexpected keyword argument
  'max_tool_result_chars'
  File ".../harness/selector.py", line 301
    backend=build_autobuild_backend(Path(cwd), max_tool_result_chars=max_tool_result_chars)
```

It fires on **every** SDK invocation → Player turn 1 crashes immediately, the
Coach gather crashes identically (run-24 log:106-124,157-159) → the whole run
dies at 25s. Introduced by `f4b6422a` (TASK-PERF-COACHTURNBUDGET Lever 2 — the
gather tool-result truncation): the **guardkit side** of the interface was
updated, the **guardkitfactory side** wasn't. Classic cross-repo coupling miss.

## The fix (do BOTH — Shape 1 is the real fix, Shape 2 is the guard)

1. **Shape 1 (real fix): update `build_autobuild_backend()` in guardkitfactory**
   to accept `max_tool_result_chars: int | None = None` and actually apply the
   truncation (truncate each gather tool result to that many chars before it
   re-enters context — the COACHTURNBUDGET Lever-2 behaviour). Default `None`
   keeps existing callers unchanged. Ensure the installed/pinned guardkitfactory
   matches the guardkit selector.
2. **Shape 2 (defensive guard, NON-silent): selector compatibility check.**
   `select_harness` introspects `build_autobuild_backend`'s signature
   (`inspect.signature(...).parameters`) and only passes the kwarg if accepted —
   **but logs a loud WARNING when it drops it.** The truncation silently
   not-happening is the absence-of-failure / silent-degradation trap the project
   has a whole rule family about — Shape 2 alone would let the COACHTURNBUDGET
   bound silently no-op against an old guardkitfactory. The WARNING makes the
   version-skew observable.

## Acceptance criteria

- [x] **AC-1**: `build_autobuild_backend()` accepts `max_tool_result_chars`
  (default `None`) and applies the truncation when set — verified by a test that
  a tool result longer than the cap is truncated and a `None` cap leaves it
  unbounded.
  → **Already satisfied** in guardkitfactory `main` (commit `62b2525`,
  TASK-PERF-COACHSYNTH). Tests: `guardkitfactory/tests/harness/test_gather_bound.py`
  `::TestBuildBackendWiring` (`test_default_is_unwrapped` None→unwrapped,
  `test_limit_wraps_default` 4096→`TruncatingBackend`) + `::TestTruncatingBackend`
  (read/execute/grep over/under-limit). Re-verified green on 2026-06-10 in the
  factory's own 3.11 venv: **8 passed**.
- [x] **AC-2**: `select_harness` passes the kwarg when supported and, when NOT
  supported, **drops it with a WARNING log** (not silently) — a test forces the
  unsupported path (monkeypatched signature) and asserts the warning fires.
  → Shape 2 in `selector.py` (`_factory_accepts_kwarg` +
  `_build_backend_with_optional_cap`). Test:
  `test_selector.py::TestSelectHarnessBackendKwargCompat::test_stale_factory_drops_cap_with_warning`
  (injects an old-signature factory; asserts no crash + WARNING fires) plus the
  unit-level `TestBuildBackendWithOptionalCap::test_stale_factory_drops_cap_and_warns`.
- [x] **AC-3 (regression reproducer)**: a test that exercises the *real*
  selector→`build_autobuild_backend` call with `max_tool_result_chars` set
  passes (this is the call that crashed run-24). It MUST fail on the
  pre-fix tree and pass after.
  → `TestSelectHarnessBackendKwargCompat::test_run24_reproducer_no_typeerror`:
  injects the stale-signature factory (asserts it *genuinely* rejects the kwarg
  with `TypeError`, the exact pre-Shape-2 call shape), then asserts
  `select_harness(..., max_tool_result_chars=4096)` constructs without raising.
  Pre-Shape-2 the unconditional call raised the run-24 `TypeError`; post-fix it
  passes.
- [x] **AC-4 (truncation actually fires)**: with a matching guardkitfactory, the
  gather tool-result truncation is active (not dropped) — assert the bound is
  applied end-to-end, so COACHTURNBUDGET's Lever-2 isn't silently disabled.
  → `TestSelectHarnessBackendKwargCompat::test_current_factory_receives_cap_and_no_warning`
  asserts the current-signature factory *receives* `max_tool_result_chars=4096`
  (kwarg forwarded, not dropped) with no warning. The real `TruncatingBackend`
  wrap is covered by the importorskip test `test_langgraph_forwards_tool_result_cap`
  (runs in the 3.11 CI) and by guardkitfactory's AC-1 suite above.
- [x] **AC-5**: an autobuild smoke run (or the harness construction path)
  completes the first Player + Coach SDK invocation without the TypeError.
  → Harness-construction path verified: `select_harness` (langgraph) constructs
  without `TypeError` against **both** the stale and current factory signatures
  (AC-2/AC-3/AC-4 tests). A full autobuild smoke run is deferred to the 3.11 path
  (guardkitfactory pins `requires-python>=3.11`; guardkit's unit venv is 3.10).

## Resolution (2026-06-10)

**Finding that refines the task framing.** The task hypothesised "the guardkit
side was updated, the guardkitfactory side wasn't." Verification showed **both
sides of the COACHSYNTH interface are already in sync on `main`**: guardkit
selector `a15d0564` forwards the kwarg and guardkitfactory `62b2525` accepts it
(both 2026-06-10). The run-24 crash was a **version-skew at install time** — the
Mac that ran run-24 had a *stale installed* guardkitfactory predating `62b2525`,
so the up-to-date selector passed a kwarg the installed factory couldn't accept.

So Shape 1 ("real fix" in guardkitfactory) was **already landed**; the genuinely
missing, load-bearing piece was **Shape 2** — the selector's defensive
signature introspection that turns a future version-skew from a 25s hard crash
into a loud, observable WARNING + graceful degradation. That is what this task
delivered (in `selector.py`), plus the AC-2..AC-5 test coverage.

**Scope boundary.** The durable class fix — a CI smoke-test that exercises the
*real installed* guardkitfactory signatures so skew is a red CI build, not a
runtime crash — is the **separate** TASK-INFRA-XREPOCONTRACT (its
`test_xrepo_contract_seam.py` + `seam-tests.yml` are in flight independently).
This task is the acute, unit-level guard only.

## Notes

- Evidence: `docs/state/TASK-REV-HMIG/run-24-artifacts/README.md`,
  `docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-24.md:106-124`.
- This is the **acute** instance; **TASK-INFRA-XREPOCONTRACT** is the durable
  class fix (a CI contract smoke-test so the next guardkit↔guardkitfactory
  signature drift is caught in CI, not at 25s into a multi-hour run).
- Resilience note from run-24: the state-recovery path still captured 5
  git-detected file changes despite the Player crash — that part degraded
  gracefully.
