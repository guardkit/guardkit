---
id: TASK-OBS-80FE
title: Archive run artifacts before worktree prune, with a stated durable home
task_type: feature
priority: high
feature_id: FEAT-OBSC
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: []
status: in_review
decision_of_record: D-OBS-1 (OBS-2) + D-OBS-4 (NAS home) + L12 rider (baseline.json)
created: 2026-07-09
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-OBSC
  base_branch: main
  started_at: '2026-07-10T08:21:57.344036'
  last_updated: '2026-07-10T08:36:14.477897'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-10T08:21:57.344036'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# TASK-OBS-80FE: Archive run artifacts before worktree prune, with a stated durable home

## Description

Run artifacts are destructible today: everything under
`<worktree>/.guardkit/autobuild/<task_id>/` — `player_turn_N.json`,
`coach_turn_N.json`, `turn_state_turn_N.json`, `state_transitions.json`
(`state_bridge.py:352`), `task_work_results.json` (`agent_invoker.py:10300`),
`design_results.json` (`agent_invoker.py:8963`), `specialist_results.json`
(read at `agent_invoker.py:9358`; written by `specialist_invocations.py:1229`),
`sdk_debug/turn_N/...` (`sdk_debug.py:57-81`), `_rollback_archive/`
(`worktree_checkpoints.py:894-964`) — is gitignored and destroyed by
`git worktree remove --force`. The lpa-platform-poc per-turn corpus was permanently
lost exactly this way (3 of 4 QAV gold negatives had to be reconstructed). All
`.guardkit` artifacts are one copy on one machine with no git recovery.

**Correction to the kickoff's cited seam** (disk-verified 2026-07-09): the decision
docs said "extend `_archive_phase`, feature_orchestrator.py:4456", but `_archive_phase`
actually sits at `feature_orchestrator.py:4901`, archives only task-markdown folders,
and is **production-dead** — called only from `tests/integration/test_feature_archival.py`.
The real destruction seams are:

- the `--fresh` clean-state path: `feature_orchestrator.py:1106` / `:1198` →
  `cleanup(force=True)` (`:2181`);
- `WorktreeManager.cleanup` (`worktrees/manager.py:509-551`) — `git worktree remove`
  + `git branch -D`, reachable from any caller;
- `feature_complete.py`'s `_archival_phase` (`:516-534`), an explicit TASK-FC-003
  placeholder that only prints intent. (The handoff text also prints a
  `guardkit worktree cleanup` command that is not a registered CLI group —
  `cli/main.py:107-134`.)

Per `.claude/rules/structural-defence-beats-prompt-instruction.md`: the archive hook
belongs **inside `WorktreeManager.cleanup`** (every removal path funnels through it),
not in per-caller advice.

## Changes

1. **Archive hook in `WorktreeManager.cleanup`** (and any direct removal path that
   bypasses it, if one exists): before `git worktree remove`, copy
   `<worktree>/.guardkit/autobuild/` (all task dirs **and** the feature-level dir
   containing `baseline.json` — the L12 wave-0 probe output,
   `guardkit/orchestrator/baseline.py`, `_BASELINE_FILENAME = "baseline.json"`,
   `.guardkit/autobuild/<feature>/baseline.json`) into the durable home. Archive
   failure must not block cleanup (log WARNING and continue) but must be loud —
   never a silent skip.
2. **Incremental archive at task finalize** (belt to the cleanup hook's braces):
   after each task's loop phase completes, archive that task's artifact dir. A crash
   between finalize and cleanup then loses at most the in-flight task.
3. **Sweep the main-repo `events.jsonl`** into the same archive location at run
   finalize, so one archive tree holds a complete run — BOTH forms: the feature-level
   `<cwd>/.guardkit/autobuild/<FEAT>/events.jsonl` (written by the CLI emitter,
   TASK-INST-013) and the task-mode `<cwd>/.guardkit/autobuild/<task_id>/events.jsonl`
   that TASK-OBS-4899 AC-3 newly creates for `guardkit autobuild task` runs.
4. **Stated durable home (D-OBS-4)**: default archive root
   `~/.guardkit/archive/<repo-name>/<feature-or-task-id>/...` — outside every repo
   working tree (survives prune, `git clean`, and repo deletion), overridable via
   `GUARDKIT_ARCHIVE_ROOT`. In-loop writes are strictly node-local (self-contained
   agents rule). The NAS half is **out-of-loop**: document the rsync runbook step to
   the D-OBS-4 home (`whitestocks:~/factory-corpora/`, NAS user home
   `/var/services/homes/RichardWoollcott/` — regular users cannot mkdir at the
   `/volume1` root) in `docs/guides/autobuild-instrumentation-guide.md`, alongside a
   note that `.guardkit/archive/` (repo-local) is itself gitignored local disk and is
   NOT the durable home.
5. **Task-mode parity**: `guardkit autobuild task` worktrees get the same
   archive-before-cleanup treatment.

## Acceptance Criteria

- [ ] AC-1: After a feature run followed by worktree cleanup (including the `--fresh`
      re-run path), every `<worktree>/.guardkit/autobuild/<task_id>/` dir and the
      feature-level `baseline.json` exist under the archive root; a test asserts
      specific expected files (player/coach turn JSONs, task_work_results.json,
      sdk_debug dir when present) are in the archive — positive evidence, not
      absence of errors.
- [ ] AC-2: The archive root is outside the repo working tree and worktrees; a test
      pins `git check-ignore` / path containment (archived data can never enter git).
- [ ] AC-3: `baseline.json` (L12 wave-0 probe output) is archived at feature level —
      pinned by its own assertion (the rider is not implied by AC-1's task dirs).
- [ ] AC-4: Archive failure (e.g. unwritable root) logs a WARNING naming the lost
      paths and does not block cleanup; pinned by a test. An absent archive is a
      surfaced signal, never silent.
- [ ] AC-5: The NAS runbook step (rsync target, destination constraint, cadence
      suggestion) is documented in the instrumentation guide with a pointer to
      D-OBS-4; the doc states explicitly that the local archive root is one copy on
      one machine until the rsync runs.
- [ ] AC-6: `feature_complete.py:_archival_phase` placeholder either delegates to the
      new archival (preferred) or its docstring is updated to point at it — no second
      divergent archival path (single source of truth).

## Test Strategy

Integration test: fabricate a worktree with the full artifact set, run cleanup,
assert archive contents file-by-file. Unit tests for root resolution/override and
the failure path. Do NOT touch `_record_baseline`/evidence machinery
(`.claude/rules/evidence-boundary-narrower-than-write-surface.md` governs that
surface; this task only copies files at destruction time).
