---
id: TASK-FIX-BACKENDKWARG
title: Fix build_autobuild_backend() signature regression — max_tool_result_chars kwarg crashes every SDK invocation
status: backlog
task_type: fix
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
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

- [ ] **AC-1**: `build_autobuild_backend()` accepts `max_tool_result_chars`
  (default `None`) and applies the truncation when set — verified by a test that
  a tool result longer than the cap is truncated and a `None` cap leaves it
  unbounded.
- [ ] **AC-2**: `select_harness` passes the kwarg when supported and, when NOT
  supported, **drops it with a WARNING log** (not silently) — a test forces the
  unsupported path (monkeypatched signature) and asserts the warning fires.
- [ ] **AC-3 (regression reproducer)**: a test that exercises the *real*
  selector→`build_autobuild_backend` call with `max_tool_result_chars` set
  passes (this is the call that crashed run-24). It MUST fail on the
  pre-fix tree and pass after.
- [ ] **AC-4 (truncation actually fires)**: with a matching guardkitfactory, the
  gather tool-result truncation is active (not dropped) — assert the bound is
  applied end-to-end, so COACHTURNBUDGET's Lever-2 isn't silently disabled.
- [ ] **AC-5**: an autobuild smoke run (or the harness construction path)
  completes the first Player + Coach SDK invocation without the TypeError.

## Notes

- Evidence: `docs/state/TASK-REV-HMIG/run-24-artifacts/README.md`,
  `docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-24.md:106-124`.
- This is the **acute** instance; **TASK-INFRA-XREPOCONTRACT** is the durable
  class fix (a CI contract smoke-test so the next guardkit↔guardkitfactory
  signature drift is caught in CI, not at 25s into a multi-hour run).
- Resilience note from run-24: the state-recovery path still captured 5
  git-detected file changes despite the Player crash — that part degraded
  gracefully.
