---
id: TASK-AB-RESUMEVENV01
title: Resume-path venv resolution — probe <worktree>/.venv, thread venv_python through hash-match skip, never silently fall back to sys.executable
status: completed
created: 2026-07-04T10:05:00Z
closed: 2026-07-09
closed_by: WS3-S1 (L17)
priority: high
tags: [autobuild, bootstrap, resume, venv, coach, false-red]
complexity: 5
source: docs/retro/abl005-autobuild-infra-chain-2026-07-04.md
---

> **CLOSED 2026-07-09 (WS3-S1, L17) — closed-as-decided.** The probe-order /
> resume-threading body of this task is IMPLEMENTED on guardkit main in
> `111b02ac` (the resume path further superseded by `fc33a23e` — resume now
> re-bootstraps). The one semantic this file (and its FIX duplicate,
> TASK-FIX-RESUMEVENV01) left open — warn-and-fallback vs hard-abort on an
> unresolved interpreter — is now **decided by Rich (2026-07-09, WS3 §7): Q1 =
> SPLIT.** Inside autobuild runs an interpreter-resolution failure is a
> HARD-ABORT (`InterpreterResolutionError`,
> `guardkit/orchestrator/coach_verification.py`, threaded through the Coach
> verdict paths); interactive CLI keeps the WARNING + `sys.executable`
> fallback. Split implemented in WS3-S1. One of the four FIX/AB duplicate
> files closed together (WS3 §3 disposition) — closed, not silently deleted.

# Task: Resume-path venv resolution must match the bootstrap layout, or fail loudly

> Implementation in progress 2026-07-04 (same session that filed this task); this file is
> the tracking record. Filed at the explicit request of the ABL-005 retro ("File as a
> guardkit task: resume-path venv resolution").

## Description

FEAT-ABL-005 run 4 (2026-07-04) burned all 8 turns on `absent test signal (deterministic
Phase 4): tests_run=0` because of a resume-path venv-resolution defect:

- `guardkit autobuild feature --resume` skips environment bootstrap ("Environment already
  bootstrapped (hash match)"), so `BootstrapResult.venv_python` is never threaded into the
  Coach/Phase-4 execution path.
- The filesystem recovery probe in `_resolve_venv_python`
  (`guardkit/orchestrator/coach_verification.py:35-63`) checks ONLY the legacy
  `<worktree>/.guardkit/venv/bin/python` location — but current bootstrap creates
  `<worktree>/.venv` (the FFC6 worktree-local venv; see also
  `.claude/rules/uv-sources-must-survive-every-install-path.md`).
- Result: `None` → callers silently fall back to `sys.executable` (the ORCHESTRATOR'S own
  guardkit venv, with no target-project deps installed) → pytest collects 0 tests → every
  turn records an absent test signal. From the outside this is indistinguishable from a
  hard task: "the Coach *appeared* to be rejecting the Player on quality for 8 straight
  turns, when it was actually blind."

Run-4 reproduction evidence (retro): the log records
`resolved_interpreter=<guardkit>/.venv/bin/python3` (the orchestrator's own); hand-running
that interpreter against the worktree tests reproduces the 0-collection ImportError
byte-identical to the specialist record. The operator worked around it with
`ln -s ../.venv .guardkit/venv` inside the worktree.

## Acceptance Criteria

- [ ] AC-001: `_resolve_venv_python`'s filesystem recovery probes BOTH layouts, current
      first: `<worktree>/.venv/bin/python` then `<worktree>/.guardkit/venv/bin/python`
      (keep the legacy probe — old worktrees exist).
- [ ] AC-002: The resume/hash-match bootstrap-skip path still yields a usable
      `venv_python` (either re-resolved from disk at skip time or persisted in the feature
      execution state from the original bootstrap) so the explicit param is threaded on
      resume exactly as on fresh runs.
- [ ] AC-003: No silent `sys.executable` fallback for a Python project worktree: when no
      worktree venv interpreter resolves and the caller would fall back, log at WARNING
      naming (a) the probed locations and (b) the interpreter actually used, and record
      the resolved interpreter in the Phase-4/independent-test evidence so the ABL-005
      forensic dig ("which interpreter did the verifier actually run?") is one grep, not
      a reproduction session.
- [ ] AC-004: Regression tests: fresh-run explicit path unchanged; resume-shaped call
      (explicit=None) with `.venv` on disk resolves it; legacy `.guardkit/venv` still
      resolves; neither present → None + WARNING; the resolved interpreter appears in the
      evidence/record payload.

## Implementation Notes

- `guardkit/orchestrator/coach_verification.py:35-63` — `_resolve_venv_python` (both the
  probe list and the docstring's resolution-order contract).
- Find every caller/duplicate resolver: `rg -n "_resolve_venv_python" guardkit/orchestrator/`
  (coach_verification.py + quality_gates/coach_validator.py at minimum) and the Phase-4
  deterministic runner's interpreter resolution in
  `guardkit/orchestrator/specialist_invocations.py` (the run-4 log's
  `resolved_interpreter=` line comes from this path — locate and align it).
- Bootstrap venv creation location + the hash-match skip: `rg -n "already bootstrapped|hash match|\.venv" guardkit/orchestrator/environment_bootstrap.py guardkit/orchestrator/feature_orchestrator.py`.
- Windows layout (`Scripts/python.exe`) — follow whatever the existing probe/bootstrap
  code already does; do not invent new platform handling.

## Regression constraints

- `.claude/rules/namespace-hygiene.md` — the whole point of venv pinning is that
  `sys.executable`/PATH pytest can mask missing deps; the fix must keep the interpreter
  worktree-venv-pinned and verify imports standalone.
- `.claude/rules/absence-of-failure-is-not-success.md` +
  `absence-must-survive-every-reconciliation-layer.md` — this fix REMOVES a cause of
  absent signals; it must not change how an absent signal, when it still occurs, is
  represented (None stays None; guard #6 / `_reconcile_absent_independent_test_signal`
  stays armed; the tri-state checkpoint chain untouched).
- `.claude/rules/uv-sources-must-survive-every-install-path.md` — do not add any new
  install path; this task is resolution-only.
- Sibling task `TASK-AB-ZEROTESTLOUD01` handles the diagnosis/messaging half (persistent
  absent Phase-4 signal surfaced as verifier infrastructure); keep the split — this task
  fixes resolution, that one fixes attribution.
