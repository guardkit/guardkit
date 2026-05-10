---
id: TASK-FIX-RBSS
title: rollback_on_pollution should reset the Player SDK session and preserve per-turn coach JSONs across the reset
status: completed
task_type: implementation
implementation_mode: task-work
parent_review: TASK-REV-F30A
external_origin: study-tutor/tasks/backlog/TASK-REV-F30A-analyse-feat-39e1-autobuild-run-3-failure.md
priority: medium
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T19:45:00Z
completed: 2026-05-10T19:45:00Z
completed_location: tasks/completed/TASK-FIX-RBSS/
previous_state: in_review
state_transition_reason: "All ACs satisfied; tests pass; ready to commit"
complexity: 6
tags: [autobuild, rollback, perspective-reset, sdk-session, audit-trail, observability]
related_tasks:
  - TASK-FIX-7A07
  - TASK-RFX-B20B
dependencies: []
inputs:
  source_files:
    - guardkit/orchestrator/autobuild.py
    - guardkit/orchestrator/worktree_checkpoints.py
  reference: |
    autobuild.py:2160-2197 (perspective reset clears session)
    autobuild.py:2319-2342 (rollback does NOT clear session)
    worktree_checkpoints.py:437-477 (git reset --hard implementation)
test_results:
  status: passing
  coverage: scope-targeted
  last_run: 2026-05-10T19:30:00Z
  details: |
    104/104 rollback-adjacent tests pass (test_worktree_checkpoints.py,
    test_autobuild_stall_detection.py, test_autobuild_perspective_reset.py,
    test_checkpoint_extraction_and_ordering.py). New tests added for AC-2
    (test_rollback_clears_player_session) and AC-4
    (test_rollback_preserves_audit_trail, plus
    test_rollback_with_no_audit_files_is_noop and
    test_archive_does_not_recurse_into_prior_archives for the AC-5
    self-defense). AC-6 verified — every pre-existing rollback /
    checkpoint test still passes against the modified code.
---

# Task: rollback_on_pollution should reset the Player SDK session and preserve per-turn coach JSONs across the reset

## Description

Two related defects in the `rollback_on_pollution` flow that turned an FEAT-39E1 run-3 turn-3 honesty drop into a max_turns_exceeded failure ([TASK-REV-F30A review report](study-tutor/.claude/reviews/TASK-REV-F30A-review-report.md)):

**Defect 1 — Player SDK session is not reset on rollback.** `autobuild.py:2319-2342` (the rollback branch) restores the worktree filesystem with `git reset --hard <commit>` but does not call `set_player_resume_session(None)`. The next turn's Player resumes the prior turn's SDK session, which has cumulative-authoring memory of all the files the rollback just deleted. The Player then re-emits those file claims into a wiped worktree, the audit's `total_claims` denominator stays low while the `critical_failures` numerator stays high (or grows), and the honesty curve diverges instead of recovering.

By contrast, the *perspective reset* code path at lines 2160-2165 explicitly *does* clear the session — that's the correct precedent. Rollback should match.

**Defect 2 — Rollback wipes the per-turn audit JSONs.** `git reset --hard` in `worktree_checkpoints.py:465` discards the run's checkpoint commits and any tracked content unique to them — including `coach_turn_2.json … coach_turn_5.json` that were committed in those run-checkpoints. After the rollback, the only Coach decision file on disk is `coach_turn_1.json` from the rollback target commit (often a `from_prior_run` checkpoint). This destroys the forensic audit trail of the very turns that triggered the rollback decision, making post-mortems harder.

## Acceptance Criteria

- [x] **AC-1**: When `rollback_on_pollution` fires (`autobuild.py:2320-2342`), call `self._agent_invoker.set_player_resume_session(None)` immediately after `self._checkpoint_manager.rollback_to(target_turn)` and before the `continue` statement. Mirror the perspective-reset code at lines 2161-2165.
- [x] **AC-2**: New unit test `test_rollback_clears_player_session` exercises the rollback branch and asserts that `_agent_invoker.set_player_resume_session` was called with `None` after rollback.
- [x] **AC-3**: Before `git reset --hard`, the rollback should snapshot per-turn audit artefacts to a sibling directory `.guardkit/autobuild/<TASK-ID>/_rollback_archive/turn_<N>_<timestamp>/`. At minimum: every `coach_turn_*.json`, `player_turn_*.json`, `turn_state_turn_*.json` matching turns `> target_turn`. Use `shutil.copytree` or equivalent. Logs `[rollback] Archived N audit files to _rollback_archive/...`.
- [x] **AC-4**: New unit test `test_rollback_preserves_audit_trail` creates a fake run with checkpoints turn 1-3, fires rollback to turn 1, and asserts that `coach_turn_2.json` and `coach_turn_3.json` exist under `_rollback_archive/`.
- [x] **AC-5**: `_rollback_archive/` is added to the project's `.gitignore` template (so the archived files don't pollute future commits) AND is excluded from the worktree-checkpoint tracked-set so subsequent rollbacks don't recursively archive prior archives.
- [x] **AC-6**: Existing `should_rollback` / `find_last_passing_checkpoint` tests continue to pass; no semantic change to those.
- [x] **AC-7**: A short note in `worktree_checkpoints.py:rollback_to` docstring explains that the *caller* (`autobuild.py`) is responsible for SDK-session reset; this method is filesystem-only by design.

## Implementation Notes

- AC-1 is the load-bearing change. AC-3 is the audit-trail hygiene. AC-1 alone would have prevented the run-3 PH1-004 divergence even if the .gitignore rule had stayed broken (the Player would have produced one bad turn, then a fresh-session re-attempt).
- Be careful about ordering: the SDK-session reset must happen *before* `continue` so that the next iteration's `_execute_turn` sees `_last_session_id == None`. Test AC-2 should pin the call ordering.
- The current code at `autobuild.py:2187-2197` re-saves the session ID at the *end* of every turn. After AC-1's reset-on-rollback, the next turn will run with no session_id, save the new fresh session at line 2195, and the session for turn N+2 onwards is the new one. Behaviour matches perspective reset.
- Reproducer fixture: a worktree with an unanchored gitignore rule that drops Player writes, plus an `AgentInvoker` mock that records every `set_player_resume_session` call. Run 3 turns, trigger rollback. Without AC-1 the test should fail; with AC-1 it passes.

## Implementation Summary

**Approach**: Two-layer fix matching the two-defect framing of the task.

**Layer 1 — SDK-session reset (AC-1, AC-7)**: Mirrored the
perspective-reset precedent at `autobuild.py:2161-2165` into the
rollback branch at `autobuild.py:2360-2366`. Immediately after
`self._checkpoint_manager.rollback_to(target_turn)` returns, the
orchestrator now calls
`self._agent_invoker.set_player_resume_session(None)` (guarded against
no-invoker test fixtures). The `rollback_to` docstring on
`WorktreeCheckpointManager` was updated to spell out that the method is
**filesystem-only by design** and that the caller is responsible for
the SDK-session reset, so a future maintainer can't undo Layer 1 by
"helpfully" pulling the reset into the checkpoint manager and then
forgetting to add an invoker reference.

**Layer 2 — Audit-trail preservation (AC-3, AC-4, AC-5)**: Added
`WorktreeCheckpointManager._archive_post_target_audit_files(target_turn)`
which globs the autobuild dir's top level for `coach_turn_<N>.json`,
`player_turn_<N>.json`, and `turn_state_turn_<N>.json` (turns
`> target_turn`) and `shutil.copy2`'s each into
`.guardkit/autobuild/<task>/_rollback_archive/turn_<target>_<UTC-iso>/`
**before** `git reset --hard` runs. The iterator deliberately does not
descend into `_rollback_archive/` itself — the no-recurse property is
pinned by `test_archive_does_not_recurse_into_prior_archives`. Three
self-defenses for the snapshot survival problem: (a) project
`.gitignore` gets a `_rollback_archive/` entry; (b) on first archive,
the manager writes a per-directory `.gitignore` containing
`*\n!.gitignore\n` so the snapshots self-exclude regardless of the
consumer project's root `.gitignore`; (c) archive failure is caught and
logged at warning level so a copy fault never blocks the load-bearing
SDK-session reset that must follow.

**Test surface**: 4 new tests + 100 pre-existing rollback-adjacent
tests still passing.

- `test_rollback_clears_player_session` (AC-2): Pinned the call
  ordering with a parent-`Mock` witness that observes `rollback_to` and
  `set_player_resume_session` across two separate mocks. Asserts
  `set_player_resume_session(None)` is called *after* `rollback_to`
  and after the per-turn live-session write, so the rollback's None
  wins for the next turn's invocation.
- `test_rollback_preserves_audit_trail` (AC-4): Real `tmp_path` worktree
  with seeded `coach_turn_{1,2,3}.json` etc. Drives rollback to turn 1
  and asserts the post-target JSONs land in
  `_rollback_archive/turn_1_<ts>/`, including verification that the
  defensive in-directory `.gitignore` was written with
  `*` + `!.gitignore`.
- `test_rollback_with_no_audit_files_is_noop`: Edge case — early-failure
  worktrees with no per-turn JSONs must still let rollback succeed.
- `test_archive_does_not_recurse_into_prior_archives`: Pre-seeds an
  existing `_rollback_archive/turn_1_19990101T000000Z/coach_turn_2.json`
  and asserts a second archival pass picks up only the top-level
  `coach_turn_3.json`, never the prior snapshot's contents.

## Notes

**Lessons / non-obvious decisions worth recording**:

1. **The audit-trail archival is best-effort by design**. AC-1's
   SDK-session reset is the load-bearing recovery primitive; AC-3 is
   forensic hygiene. So the archive call is wrapped in
   `try/except Exception` inside `rollback_to` — a `shutil.copy2`
   `OSError` (full disk, ACL miss) must never block the
   `git reset --hard` that the SDK-reset's caller depends on. This is
   the same pattern as `_save_checkpoints` (best-effort persistence).

2. **The defensive in-directory `.gitignore` is the load-bearing
   AC-5 mechanism, not the project-level entry**. The original F30A
   reproducer was in a consumer repo whose `.gitignore` did not list
   `.guardkit/autobuild/`. Adding `_rollback_archive/` to the GuardKit
   repo's own `.gitignore` defends the GuardKit-host case but doesn't
   help downstream consumers. The
   `_rollback_archive/.gitignore` (`*\n!.gitignore\n`) self-defends
   regardless of consumer-side configuration. Removing the project-level
   entry would still leave the consumer-safe path working; removing the
   in-directory write would silently break consumer repos.

3. **Path-pattern check ordering matters**. The audit globs match
   `coach_turn_<N>.json`, `player_turn_<N>.json`,
   `turn_state_turn_<N>.json`. Note `turn_state_turn_<N>.json` would
   also match a more permissive `turn_*\.json`, so the patterns are
   anchored with `^…$`. `unrelated.json` and `checkpoints.json` must
   not be archived — pinned by
   `test_rollback_preserves_audit_trail`'s assertion that
   `checkpoints.json` is NOT under the snapshot dir.

4. **Pre-existing in-flight work in the host repo**: at the time this
   task ran, branch `main` already had uncommitted TASK-FIX-HEAB
   changes in `autobuild.py` (adding `honesty_early_abort_window`
   attribute and `honesty_collapse` exit decision). My AC-1 hunk lives
   in a different region (the rollback branch around
   `autobuild.py:2360`), so the two changes don't overlap. The
   commit for this task isolates only my AC-1 hunk via stash-and-apply
   so the HEAB work stays in the working tree for its own
   `/task-complete` later.

**Related rules**:

- `.claude/rules/absence-of-failure-is-not-success.md` — sibling
  meta-frame. The Layer-1 SDK-session reset is the inverse: a
  *caller-visible* invariant that must hold across boundary, where
  forgetting to call it makes the boundary look like it succeeded
  (rollback returned True, worktree files reverted) when in fact the
  next turn will resume the polluted memory and re-emit the same
  claims.
