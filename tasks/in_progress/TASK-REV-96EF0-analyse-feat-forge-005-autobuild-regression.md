---
id: TASK-REV-96EF0
title: Analyse FEAT-FORGE-005 autobuild regression post pytest-bdd fix
status: backlog
created: 2026-04-26T00:00:00Z
updated: 2026-04-26T00:00:00Z
priority: critical
task_type: review
decision_required: true
tags: [autobuild, regression, pytest-bdd, forge, player-invocation-stall, authentication-failed]
complexity: 6
---

# Task: Analyse FEAT-FORGE-005 autobuild regression post pytest-bdd fix

## Description

A `guardkit autobuild feature FEAT-FORGE-005` run on the GB10 host failed in
Wave 1 with both TASK-GCI-001 and TASK-GCI-002 hitting `PLAYER_INVOCATION_STALL`
after 3 consecutive `authentication_failed` SDK errors. This is a regression:
FEAT-FORGE-003 and FEAT-FORGE-004 ran cleanly on the same host, and the prior
FEAT-FORGE-005 attempt only hit a rate-limit (not auth). The regression appears
to coincide with the recently-merged pytest-bdd silent-bypass fixes
(TASK-FIX-BDDM-1, TASK-FIX-BDDM-2 + Wave 3 cross-repo remediation).

Critically, **JARVIS on the macbook is currently building OK with autobuild of
FEAT-J003** — so the regression is not universal, which suggests the forge repo
is missing a piece of remediation that Jarvis received.

This review must determine the root cause, distinguish between
"pytest-bdd-fix regression" vs "transient SDK auth flake" vs "missing forge
remediation", and recommend a concrete fix.

## Acceptance Criteria

- [ ] Root cause for the `authentication_failed` SDK errors identified
      (env-bootstrap failure side-effect? SDK auth state? pytest-bdd preflight
      side-effect? something else?)
- [ ] Determined whether the GuardKit Wave 1 changes (TASK-FIX-BDDM-1,
      TASK-FIX-BDDM-2) introduced a new failure mode that surfaces as
      `authentication_failed` in the SDK layer (e.g. preflight short-circuiting
      env setup such that the player runs from a broken venv)
- [ ] Confirmed whether Forge needs the equivalent of jarvis commits
      `46b9ce4` (add `pytest-bdd>=8.1,<9` to dev group) and/or `f60c6be`
      (wire pytest-bdd collection for `features/*.feature`) — user note says
      forge was skipped for the toml update because the dep was "already there",
      but the jarvis changes also included other wiring that may need porting
- [ ] Bootstrap-failure relevance assessed: log shows
      `nats-core<0.3,>=0.2.0` (forge dep) cannot be resolved by pip →
      `Environment bootstrap partial: 0/1 succeeded`. Determine whether this
      contributes to the SDK auth failure (e.g. SDK invoked from a venv that
      doesn't have claude-agent-sdk) or is unrelated background noise
- [ ] Comparison documented: what differs between the working Jarvis FEAT-J003
      run and the failing Forge FEAT-FORGE-005 run (env, deps, fixtures,
      claude-agent-sdk version, host, auth state)
- [ ] Recommendation produced: one of
      (a) fix to apply to forge repo (port specific jarvis commits / re-publish
          nats-core 0.2.0 / re-auth claude on GB10 / etc.),
      (b) fix to apply to GuardKit core (revert/adjust BDDM Wave 1),
      (c) both, with a clear ordering
- [ ] Decision checkpoint reached with [A]ccept / [I]mplement / [R]evise /
      [C]ancel options

## Context — Inputs to Review

### Failure log (primary input)

- [docs/reviews/bdd-acceptance-wired-up/autobuild-FOREGE-FEAT-005-fails-1.md](../../docs/reviews/bdd-acceptance-wired-up/autobuild-FOREGE-FEAT-005-fails-1.md)
  - 787 lines
  - Wave 1 (TASK-GCI-001, TASK-GCI-002) — both stalled at turn 3
  - Decision: `PLAYER_INVOCATION_STALL`
  - Underlying SDK error: `Agent player received API error: authentication_failed`
  - Bootstrap log shows `ERROR: Could not find a version that satisfies the requirement nats-core<0.3,>=0.2.0` and `Environment bootstrap partial: 0/1 succeeded`

### Comparison — historical successful forge runs

- [forge/docs/history/autobuild-FEAT-FORGE-003-history.md](/home/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-003-history.md)
- [forge/docs/history/autobuild-FEAT-FORGE-004-history.md](/home/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-004-history.md)
- [forge/docs/history/autobuild-FEAT-FORGE-005-history-hit-rate-limit.md](/home/richardwoollcott/Projects/appmilla_github/forge/docs/history/autobuild-FEAT-FORGE-005-history-hit-rate-limit.md)
  — earlier 005 attempt, only hit rate limit (so the SDK auth path was healthy then)

### Recently-merged GuardKit pytest-bdd fix

- [tasks/backlog/bdd-runner-silent-bypass-fix/IMPLEMENTATION-GUIDE.md](bdd-runner-silent-bypass-fix/IMPLEMENTATION-GUIDE.md)
- Relevant guardkit commits (most recent first):
  - `70a7a609 Review and fixes for pytest-bdd`
  - `3f3531b8 chore(task): complete TASK-OPS-BDDM-11 (proactive pytest-bdd add for study-tutor)`
  - `49a53f98 chore(task): complete TASK-OPS-BDDM-7 (proactive pytest-bdd add for nats-infrastructure)`
  - `1301a01d chore(task): complete TASK-OPS-BDDM-6 (advisory pytest-bdd add for nats-core)`
  - `6af9eb36 chore(task): complete TASK-OPS-BDDM-5 (advisory pytest-bdd add for ADF)`
  - `68bee41f fix(bdd-runner): synthesise blocker when tagged scenarios exist + pytest-bdd absent (TASK-FIX-BDDM-1)`
  - `56a8448a fix(autobuild): env-level preflight catches pytest-bdd ↔ tagged feature gap (TASK-FIX-BDDM-2)`
  - `d2e3fce2 docs(bdd): document pytest-bdd runtime prerequisite (TASK-DOC-BDDM-4)`

### Working comparator — Jarvis

Jarvis received TWO commits as part of the BDDM Wave 3 remediation:
- `46b9ce4 chore(deps): add pytest-bdd>=8.1,<9 to dev group (TASK-OPS-BDDM-9)`
- `f60c6be fix(bdd): wire pytest-bdd collection for features/*.feature (TASK-OPS-J002-BDD)`

User hypothesis: forge was **only** updated for the dep (or skipped because the
dep was already present) and is missing the **collection wiring** equivalent of
`f60c6be`. Verify by inspecting the jarvis vs forge diffs and confirming
whether forge has analogous wiring (e.g. a `tests/conftest.py` `scenarios()`
call, or `[tool.pytest.ini_options] bdd_features_base_dir`).

### Forge environment hint

Forge's `pyproject.toml` requires `nats-core<0.3,>=0.2.0` but pip cannot find
0.2.0 (only 0.0.0 is published). This makes the bootstrap install fail and
**the autobuild venv may be unusable** — which could starve the player SDK
of its expected dependencies (including claude-agent-sdk) and surface as
`authentication_failed`. Cross-check against `nats-core` PyPI/Artifactory
publication state and whether a 0.2.0 was supposed to land but didn't.

## Suggested Investigation Plan

1. **Read the failure log end-to-end.** Confirm the auth error is per-turn (not
   one transient flake replayed) and whether it precedes/follows the bootstrap
   failure narratively.
2. **Diff jarvis vs forge** — compare `pyproject.toml`, `conftest.py`,
   `pytest.ini` / `[tool.pytest.ini_options]`, and any `features/` directory
   structure. Identify what jarvis received that forge did not.
3. **Verify the GB10 SDK auth state** — check `claude auth status`, the
   `claude-agent-sdk` install, and whether the bootstrap-created venv inherits
   the right credentials. The failure-log "Suggested checks" section flags
   this explicitly.
4. **Re-read the BDDM Wave 1 patches** (`bdd_runner.py`, `feature_validator.py`,
   `feature_orchestrator.py:733`) and look for any code path that could short-
   circuit env bootstrap or alter player invocation when pytest-bdd is missing
   or when feature files have tagged scenarios. The orchestrator runs preflight
   *before* the player; if preflight failure causes the orchestrator to
   continue with a partially-set-up env, that could surface as auth failure.
5. **Check `nats-core` publication status** — is 0.2.0 expected to be on
   PyPI/internal index? If the dep pin is wrong, fix it; if it was supposed to
   be published, file an OPS task. Either way, decide whether bootstrap failure
   should be a hard stop (i.e. abort before attempting player invocation).
6. **Test a minimal repro** in the forge worktree:
   `python -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"`
   from the bootstrap venv, to confirm whether the SDK is even importable.
7. **Decision options at the checkpoint:** apply forge-side fix only / apply
   GuardKit-side guard (e.g. abort run on bootstrap failure) / both.

## Notes

- This is a **review task** — use `/task-review TASK-REV-96EF0` (not
  `/task-work`). The review should produce findings + a recommended action set,
  not a code change. Implementation tasks (if needed) should be filed via the
  [I]mplement option at the review checkpoint, with `parent_review:
  TASK-REV-96EF0`.
- Tag `regression` because it's a confirmed regression vs FEAT-FORGE-003/004
  on the same host.
- The user's working hypothesis is that **the forge repo needs an equivalent
  of jarvis commit `f60c6be`** — confirm or refute that explicitly in the
  findings.
- Do NOT delete the failed worktree at
  `/home/richardwoollcott/Projects/appmilla_github/forge/.guardkit/worktrees/FEAT-FORGE-005`
  during the review — it contains the per-turn coach decisions and turn-state
  JSON needed to triangulate.

## References

- Failure: `docs/reviews/bdd-acceptance-wired-up/autobuild-FOREGE-FEAT-005-fails-1.md`
- Implementation guide for the recent fix: `tasks/backlog/bdd-runner-silent-bypass-fix/IMPLEMENTATION-GUIDE.md`
- Forge history: `forge/docs/history/autobuild-FEAT-FORGE-{003,004,005-hit-rate-limit}-history.md`
- Jarvis fix commits: `46b9ce4`, `f60c6be` (in `~/Projects/appmilla_github/jarvis`)
- GuardKit BDDM commits: `68bee41f`, `56a8448a`, `d2e3fce2`, `70a7a609`
- Sibling pattern: `.claude/rules/namespace-hygiene.md` (anti-pattern catalogue
  for the broader meta-class "local design decisions touching externally-defined
  contracts must be audited")
- Worktree to inspect: `forge/.guardkit/worktrees/FEAT-FORGE-005/.guardkit/autobuild/TASK-GCI-00{1,2}/`
