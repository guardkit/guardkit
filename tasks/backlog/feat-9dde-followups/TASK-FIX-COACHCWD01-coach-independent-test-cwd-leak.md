---
id: TASK-FIX-COACHCWD01
title: Pin the Coach independent-test run cwd to the worktree (stop coverage.xml/json leaking into the host repo)
status: backlog
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T12:40:00Z
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

- [ ] The Coach independent-test subprocess runs with `cwd` set to the task's
      worktree root (or the relevant evidence repo root), so `coverage.xml` /
      `coverage.json` and any other relative-path artifacts land inside the
      worktree, never the host repo.
- [ ] Confirm the test discovery/paths still resolve when cwd is the worktree
      (the run-3 invocation used worktree-relative `tests/...` paths, so this
      should be a pure cwd fix).
- [ ] Regression test asserting the independent-test subprocess is invoked with
      the worktree cwd (mock the executor, assert `cwd`).
- [ ] No stray `coverage.*` in the host repo root after an autobuild run.

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md`
  §"Harness-health scorecard" (minor leak (a)).
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (CoachValidator
  independent-test lines, ~445-447).
</content>
