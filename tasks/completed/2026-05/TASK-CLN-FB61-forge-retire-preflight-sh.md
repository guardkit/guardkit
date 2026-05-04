---
id: TASK-CLN-FB61
title: "forge cleanup: retire .guardkit/preflight.sh after AB60 + AB61"
task_type: cleanup
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T13:30:00Z
completed: 2026-05-04T13:30:00Z
previous_state: in_review
completed_location: tasks/completed/2026-05/
state_transition_reason: "All four ACs satisfied. AC1+AC2+AC4 landed on forge branch cleanup/TASK-CLN-FB61-retire-preflight (commit ad5e9ee). AC3 verified 2026-05-04 via guardkit autobuild feature FEAT-FORGE-003 --task TASK-SAD-001 --fresh — Coach approved task, AB61 INFO line fired and created bridging symlink autonomously, no preflight invocation. See Verification Run block below for log evidence. AB60's conditional retry path was not triggered (forge/.venv exists, no-venv sentinel not emitted) — independently covered by TASK-FIX-AB60's own AC suite."
priority: medium
tags: [cleanup, forge, cross-repo, AB61-followup, AB60-followup, preflight]
complexity: 2
estimated_minutes: 30
estimated_effort: "30min (delete script + audit runbook references + verify autobuild on forge)"
parent_task: TASK-FIX-AB61
implementation_mode: cross-repo
target_repo: appmilla_github/forge
related_tasks:
  - TASK-FIX-AB61  # uv-sources symlink coordination — obsoletes the second half of preflight.sh
  - TASK-FIX-AB60  # uv venv arrangement — obsoletes the first half of preflight.sh
  - TASK-FIX-F09A1 # the original forge preflight.sh
context_files:
  - ../../forge/.guardkit/preflight.sh
  - ../../guardkit/tasks/completed/2026-05/TASK-FIX-AB61-uv-sources-worktree-symlink-coordination.md
test_results:
  status: passed
  coverage: n/a  # cleanup task — no new code/tests; verified via end-to-end autobuild run
  last_run: 2026-05-04T13:21:35Z  # FEAT-FORGE-003 / TASK-SAD-001 Coach approval timestamp
---

# Task: forge — retire `.guardkit/preflight.sh`

## Description

`forge:.guardkit/preflight.sh` was introduced in TASK-FIX-F09A1 to do
two pieces of work that guardkit could not yet do autonomously:

1. **Create a worktree-local `.venv`** so `uv pip install -e .` could
   honour `[tool.uv.sources]` overrides. Obsoleted by **TASK-FIX-AB60**
   (guardkit now detects the no-venv stderr sentinel and runs
   `uv venv` automatically).

2. **Pre-create sibling-source symlinks** (e.g. for `nats-core`) so uv
   could resolve path-typed sources from the worktree. Obsoleted by
   **TASK-FIX-AB61** (guardkit now parses `[tool.uv.sources]` and
   pre-creates the bridging symlinks autonomously).

After AB61's helper-level cross-repo verification confirmed correct
emission against forge's actual `pyproject.toml`, the script is fully
vestigial. Keeping it carries two risks: (a) operators forget it
exists and waste time debugging "why didn't my preflight run?", (b)
its presence implies guardkit can't handle forge's bootstrap shape,
which is no longer true.

## Acceptance Criteria

- [x] **Delete `.guardkit/preflight.sh`** from the forge repo. Single
      `git rm`. Commit message references TASK-CLN-FB61 and AB60+AB61.
      → Done on forge branch `cleanup/TASK-CLN-FB61-retire-preflight`,
        commit `ad5e9ee`.

- [x] **Audit forge runbook + docs** for any references to the
      preflight script. Likely sites:
      - `forge/README.md` — no references found
      - `forge/docs/*.md` (any bootstrap / quickstart guide) — only
        `docs/runbooks/RUNBOOK-FEAT-FORGE-009-nats-core-symlink-fix.md`
        substantively references the preflight script; updated to mark
        the runbook **Retired (2026-05-04)** with a pointer to AB60+AB61.
        Other matches in `docs/research/`, `docs/product/`,
        `docs/history/` are either historical context (left as-is) or
        refer to a different "preflight" concept (template `preflight.py`,
        readiness-gate command idea — unrelated to the script).
      - `forge/.guardkit/config.yaml` — file is empty, nothing to remove.

- [x] **Verify autobuild still works** on forge: pick any current
      feature in `forge:.guardkit/features/`, run
      `guardkit autobuild feature <FEAT-XXX> --verbose --fresh` from a
      fresh checkout. Confirm:
      1. ✅ No preflight prompt or invocation in the log.
      2. ✅ AB61's `creating uv-sources symlink` INFO line fires (post-
         operator-nit log-level bump on `feature_orchestrator.py:1282`).
      3. ⏸️ AB60's venv-arrangement retry fires if uv reports no venv.
         **Not triggered this run** — `forge/.venv` exists, so uv resolved
         the venv autonomously and never emitted the no-venv stderr
         sentinel that AB60 watches for. The retry path is a safety net
         for the no-venv case, independently verified by TASK-FIX-AB60's
         own AC suite. This run exercises the happy path where AB60 is
         not needed; bootstrap reached success regardless.
      4. ✅ Bootstrap reaches success and the feature's tasks execute.
      → **Verified 2026-05-04** — see "Verification Run" block below.

- [x] **Close `TASK-FIX-F09A1`** in forge once this task lands —
      F09A1's deliverable is now retired by upstream guardkit fixes.
      → Closure note appended to
        `forge/tasks/completed/TASK-FIX-F09A1/TASK-FIX-F09A1-add-preflight-and-cli-deps.md`
        in commit `ad5e9ee` referencing this task and AB60+AB61.

## Verification Status

| AC | Status | Where |
|----|--------|-------|
| 1. Delete script | ✅ Done | forge `cleanup/TASK-CLN-FB61-retire-preflight` @ `ad5e9ee` |
| 2. Audit docs | ✅ Done | same commit (runbook retired, F09A1 note appended) |
| 3. Autobuild verification | ✅ Verified | see "Verification Run" below |
| 4. Close F09A1 | ✅ Done | same commit (closure note in F09A1 task file) |

## Verification Run (AC#3 evidence)

**Date:** 2026-05-04
**Command:** `guardkit autobuild feature FEAT-FORGE-003 --task TASK-SAD-001 --fresh --max-turns 1 --verbose`
**Forge branch:** `cleanup/TASK-CLN-FB61-retire-preflight` @ `ad5e9ee`
**Pre-run cleanup:** removed pre-existing manual `.guardkit/worktrees/nats-core` symlink (the obsolete runbook setup) so AB61's autonomous creation could be observed end-to-end. Also removed stale `FEAT-FORGE-002` worktree dir.
**Result:** `decision=approved, turns=1` — Coach approved TASK-SAD-001 turn 1 in ~5 minutes.
**Log:** `/tmp/CLN-FB61/autobuild.log` (185 lines, kept for reference).

Marker-by-marker observations:

1. **No preflight invocation** ✅
   `grep -i preflight /tmp/CLN-FB61/autobuild.log` → zero matches. The deleted script is not referenced anywhere in the autobuild path.

2. **AB61 `creating uv-sources symlink` INFO line** ✅
   ```
   INFO:guardkit.orchestrator.feature_orchestrator:creating uv-sources symlink:
     /Users/.../forge/.guardkit/worktrees/nats-core
     -> /Users/.../appmilla_github/nats-core
   ```
   Fires at line 37 of the log, between worktree creation (`Copied 11 task file(s) to worktree`) and bootstrap (`Bootstrapping environment: python`). Post-run `ls -la .guardkit/worktrees/` confirms AB61 created the bridging symlink autonomously.

   **Note on detection sensitivity:** `_resolve_uv_sources_symlinks()` uses `.resolve()` on the worktree path before comparing against the source path. If the worktree's `.guardkit/worktrees/<name>` slot is *already* a symlink resolving to the same target the source pyproject would resolve to, AB61's `worktree_resolved == source_resolved` short-circuit treats it as in-tree and skips. This is *correct* behavior (AB61 doesn't redundantly re-create existing-and-correct symlinks), but it means the INFO line will not fire on a worktree where the manual runbook symlink is still present. We confirmed this on the first verification attempt and removed the manual symlink before the second attempt.

3. **AB60 venv-arrangement retry** ⏸️ Not triggered (precondition not met)
   AB60's retry path at `environment_bootstrap.py:1619-1625` requires three conjunctive conditions: (a) command is `uv pip install …`, (b) `self._uv_venv_python is None`, (c) uv stderr contains the "No virtual environment found" sentinel (`_is_uv_no_venv_error`). On this run, `forge/.venv` already existed, so uv discovered it and the no-venv sentinel was never emitted — AB60's retry was correctly skipped. The bootstrap call succeeded on the first attempt: `INFO:guardkit.orchestrator.environment_bootstrap:Install succeeded for python (pyproject.toml)`. AB60's retry behavior under the no-venv condition is independently verified by TASK-FIX-AB60's own AC suite; this verification covers the happy path where AB60 is unneeded.

4. **Bootstrap reaches success and tasks execute** ✅
   - Line 41: `Install succeeded for python (pyproject.toml)`
   - Line 122: `Coach approved TASK-SAD-001 turn 1`
   - Line 159: `Orchestration complete: TASK-SAD-001, decision=approved, turns=1`
   - The Player ran TASK-SAD-001 (Pydantic models for the dispatch package), Coach independently re-ran the tests via subprocess fallback (`Independent tests passed in 0.8s`), and the worktree was preserved at `forge/.guardkit/worktrees/FEAT-FORGE-003/`.

**Conclusion:** preflight.sh is fully retired. Bootstrap reaches success with no manual setup; AB60 + AB61 cover the two responsibilities preflight.sh used to handle. Cross-repo cleanup objectives met.

## Forge-Side Branch

```
forge: cleanup/TASK-CLN-FB61-retire-preflight
  └── ad5e9ee chore(cleanup): retire .guardkit/preflight.sh after AB60+AB61 (TASK-CLN-FB61)
```

Not pushed to origin. Merge after AC#3 verification passes.

## Out of Scope

- Re-running guardkit's own AB61 verification — already passed at
  helper level.
- Touching forge's pyproject.toml itself — preflight.sh deletion does
  not require it.
- Auditing any OTHER consuming repo's preflight scripts (specialist-
  agent's stop-gap symlink was filesystem-only, not a script;
  jarvis has no preflight).

## Why a Separate Task

The cleanup is in forge, not guardkit, so it lives in forge's own
worktree branch and CI. AB61 itself only added the upstream code that
makes this cleanup possible — the deletion-side work belongs here.
