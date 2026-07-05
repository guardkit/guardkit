---
id: TASK-FIX-RESUMEVENV01
title: Resume-path venv resolution — probe bootstrap location or fail loudly
status: backlog
task_type: bugfix
priority: high
created: 2026-07-05
tags: [autobuild, resume, venv, verifier-infrastructure]
---

# Resume-path venv resolution

`guardkit autobuild feature <F> --resume` skips bootstrap, and
`_resolve_venv_python`'s filesystem recovery probes `<worktree>/.guardkit/venv`
— but bootstrap creates `<worktree>/.venv`. On mismatch it silently falls back
to `sys.executable`, so Phase-4 pytest runs in the orchestrator's own env and
collects 0 tests. Cost: FEAT-ABL-005 run 4 burned 8 turns with the Coach blind
(`docs/retro/abl005-autobuild-infra-chain-2026-07-04.md`, defect #4).

Fix: probe `<worktree>/.venv` too (or persist `venv_python` in feature
execution state); if no venv resolves, fail the run loudly instead of falling
back to `sys.executable`.

Acceptance: a `--resume` on a bootstrap-created worktree resolves the worktree
interpreter; a worktree with no venv aborts with a clear error; regression test
covers both.
