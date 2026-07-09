---
id: TASK-FIX-RESUMEVENV01
title: Resume-path venv resolution — probe bootstrap location or fail loudly
status: completed
task_type: bugfix
priority: high
created: 2026-07-05
closed: 2026-07-09
closed_by: WS3-S1 (L17)
tags: [autobuild, resume, venv, verifier-infrastructure]
---

> **CLOSED 2026-07-09 (WS3-S1, L17) — closed-as-decided (duplicate).** This FIX
> file duplicates the shipped AB half TASK-AB-RESUMEVENV01, implemented on
> guardkit main in `111b02ac` (resume path superseded by `fc33a23e` — resume
> now re-bootstraps). The "or fail loudly" it demanded — hard-abort rather than
> the shipped WARNING + `sys.executable` fallback — was deliberately declined
> at the time and left as the open Q1 question. **Q1 is now DECIDED (Rich
> 2026-07-09, WS3 §7): SPLIT** — the hard-abort is granted, scoped to inside
> autobuild runs (`InterpreterResolutionError`,
> `guardkit/orchestrator/coach_verification.py`, threaded through the Coach
> verdict paths); interactive CLI keeps warn-and-fallback. Implemented in
> WS3-S1. No further work — closed, not silently deleted.

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
