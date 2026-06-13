---
id: TASK-FIX-COACHCWD01
title: Pin the Coach independent-test run cwd to the worktree (stop coverage.xml/json leaking into the host repo)
status: completed
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T16:10:00Z
completed: 2026-06-13T16:10:00Z
completed_location: tasks/completed/TASK-FIX-COACHCWD01/
priority: low
complexity: 2
related: [TASK-FIX-WTESCAPE01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, coach, independent-tests, cwd, artifact-leak, wtescape]
---

# Task: Pin the Coach independent-test run cwd to the worktree

## Why this task exists

During FEAT-9DDE run 3 (2026-06-13) the Coach's independent test execution wrote
`coverage.xml` and `coverage.json` into the **host repo root**
(`/home/richardwoollcott/Projects/appmilla_github/guardkit/`), not the worktree.
The run's log line confirms the interpreter was correctly pinned to the worktree
venv, but the subprocess cwd resolved to the host repo, so pytest's
`--cov-report` artifacts landed outside the worktree:

```
CoachValidator: Running independent tests via subprocess:
  pytest tests/test_task_status_json_integration.py tests/unit/commands/test_task_status_json.py -v --tb=short
# -> coverage.xml / coverage.json written to the HOST cwd
```

This is benign (a coverage artifact, not source pollution, and outside the
`WTESCAPE01` source-watch set), but it is a real cross-boundary write the
evidence loop should not make — it clutters the host repo and, in principle,
could overwrite a host-side coverage report. The `evidence-boundary-narrower-
than-write-surface` family says every arm of the evidence loop should be scoped
to the declared evidence roots; here the independent-test runner's cwd is wider
than the worktree.

## Acceptance Criteria

- [x] The Coach independent-test subprocess runs with `cwd` set to the task's
      worktree root (or the relevant evidence repo root), so `coverage.xml` /
      `coverage.json` and any other relative-path artifacts land inside the
      worktree, never the host repo.
- [x] Confirm the test discovery/paths still resolve when cwd is the worktree
      (the run-3 invocation used worktree-relative `tests/...` paths, so this
      should be a pure cwd fix).
- [x] Regression test asserting the independent-test subprocess is invoked with
      the worktree cwd (mock the executor, assert `cwd`).
- [x] No stray `coverage.*` in the host repo root after an autobuild run.

## Outcome (2026-06-13)

**Finding:** Every coverage-producing subprocess in `coach_validator.py` already
pins `cwd` to the worktree — the standard pytest path
([`coach_validator.py:4032-4039`](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L4032)
`cwd=str(self.worktree_path)`), the shell path (4041-4048), the parallel-isolation
path (tmpdir snapshot, 3791-3807), and the SDK path
(`cwd=self.worktree_path` into `select_harness`, ~3447). This pin landed in
TASK-BOOT-43DE (2026-02-17). The interpreter is pinned independently via
`_resolve_venv_python` (explicit `venv_python` wins regardless of `worktree_path`),
which is why the run-3 log shows a worktree venv interpreter — but cwd was never
the unpinned half in the current code.

**Gap closed:** there was **no regression test** locking the cwd pin in place, so a
future refactor dropping the `cwd=` kwarg would silently re-open the host-leak.
Added `TestSubprocessCwdPinnedToWorktree` (3 tests) in
[`tests/unit/test_coach_subprocess_tests.py`](../../../tests/unit/test_coach_subprocess_tests.py)
asserting `cwd == str(worktree)` for the pytest path, the shell path, and that
worktree-relative test paths survive the pin (AC-2). Removed the stray gitignored
`coverage.json` / `.coverage` from the host root (AC-4).

No production-code change was required — the pin the task's AC-1 specifies is
already present and is now guarded against regression.

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md`
  §"Harness-health scorecard" (minor leak (a)).
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (CoachValidator
  independent-test lines, ~445-447).
</content>
