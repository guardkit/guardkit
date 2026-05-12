---
id: TASK-FIX-CAUD-J6F1
title: "Claim-audit path normalisation: stop string-matching absolute paths against worktree-relative `git status --porcelain`"
status: completed
task_type: implementation
priority: high
created: 2026-05-12
updated: 2026-05-12T12:00:00Z
completed: 2026-05-12T12:00:00Z
completed_location: tasks/completed/2026-05/
previous_state: in_review
state_transition_reason: "All in-scope ACs delivered + tests pass; AC-005 deferred to TASK-FIX-CAUD-PREFLIGHT-C3B0"
tags: [autobuild, coach, claim-audit, path-resolution, false-positive, bug]
related_tasks: [TASK-REV-J6F1, TASK-FIX-CAUD-PREFLIGHT-C3B0]
source_review: TASK-REV-J6F1
external_repro: /Users/richardwoollcott/Projects/appmilla_github/jarvis/.claude/reviews/TASK-REV-J6F1-review-report.md
external_worktree: /Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-JARVIS-006
estimated_complexity: 4

implementation_summary:
  delivered_acs: [AC-001, AC-002, AC-003, AC-004 (verified), AC-006]
  deferred_acs: [AC-005]
  follow_up_task: TASK-FIX-CAUD-PREFLIGHT-C3B0
  files_changed:
    - guardkit/orchestrator/coach_verification.py  # AC-001, AC-002, AC-003b
    - guardkit/orchestrator/agent_invoker.py        # AC-003a
    - guardkit/orchestrator/quality_gates/coach_validator.py  # AC-002
    - tests/unit/test_coach_verification_claim_audit.py       # AC-006 unit (5 tests)
    - tests/integration/orchestrator/test_coach_claim_audit.py # AC-006 integration (1 test)
  diff_stats: "5 files, 468 insertions(+), 24 deletions(-)"
  test_results:
    coach_unit_suite: "338 passed"
    integration_suite: "7 passed (1 new J6F1 replay test)"
    agent_invoker_suite: "595 passed (1 pre-existing failure on main, unrelated)"
---

# TASK-FIX-CAUD-J6F1: Claim-audit path normalisation + diagnostic fixes

## Summary

The AutoBuild Coach's checkpoint claim-audit produces 100% false-positive
"Player claimed a file that `git add -A` would not stage" issues whenever the
Player report contains **absolute** file paths. The audit compares the
Player-reported path string against the output of `git status --porcelain`,
which is always **worktree-relative**, so any absolute claim necessarily
mismatches and is flagged as unstaged — even when the file exists, is not
git-ignored, and *is in fact* successfully staged and committed.

This bug stalled an external autobuild run for `FEAT-JARVIS-006` in the
`jarvis` repo on 2026-05-11 (run `fail-run-1`). The chat handler
implementation completed correctly on Player turn 1, but the audit
mis-flagged its absolute-path claims and the resulting `must_fix` issues
drove a 3-turn `unrecoverable_stall: context_pollution_stall_no_checkpoint`.
Full diagnosis, evidence, and 20-for-20 bucket-A classification of every
flagged path in the failed run is in the external review report (see
`external_repro` frontmatter field).

## Root Cause (verified)

For each path `p` reported in `player_turn_N.json.files_created /
files_modified / files_authored`, the Coach (currently) appears to do
roughly:

```python
staged_paths = set(line.split()[1] for line in
                   subprocess.check_output(["git", "status", "--porcelain"], cwd=worktree).splitlines())
if p not in staged_paths:
    issues.append(must_fix("Player claimed a file that 'git add -A' would not stage"))
```

`p` may be absolute (e.g.
`/Users/richardwoollcott/.../FEAT-JARVIS-006/src/jarvis/infrastructure/chat_handler.py`)
while `staged_paths` only ever contains relative entries
(`src/jarvis/infrastructure/chat_handler.py`) — so the membership test fails
deterministically on absolute claims.

The audit's failure message then misleadingly speculates "Most common cause:
an unanchored .gitignore rule" — which was provably wrong on the FEAT-JARVIS-006
repro (worktree `.gitignore` byte-identical to repo root, `git check-ignore -v
<path>` returned exit 1 / no match on every flagged path, and every flagged
file was already on disk and in the eventual checkpoint commit's `--stat`).

## Compounding interaction (also in scope)

When the Player's task delivers via `task-work` sub-delegation,
`task_work_results.json.agent_invocations_validation.status` becomes
`"violation"` with `missing_phases: ["3"]` — Phase 3 (Implementation) was
never formally invoked as a separate agent call. The Coach interprets this
gap as "validation could not run" and produces
`validation_results.quality_gates: null`,
`validation_results.independent_tests: null`. With `quality_gates == null`,
the audit-warning-to-`must_fix` promotion logic appears to fire
unconditionally. On the same run, TASK-J006-002 had the **same**
absolute-path audit defect (10 honesty discrepancies in coach_turn_1) but
its quality_gates returned all-passed, so its discrepancies stayed warnings
and the turn was approved. Only TASK-J006-003 (the same `task-work` mode but
with an SDK turn budget that may have differently shaped the agent
invocation log) ended up with quality_gates=null and was therefore the only
task whose audit warnings got promoted.

So while the path-normalisation bug is the proximate cause, the audit's
promotion-when-quality-gates-null behaviour amplifies any audit defect into
an unrecoverable stall. Both should be addressed.

## Acceptance Criteria

### AC-001: Path normalisation in claim audit (primary fix)

- [ ] Before testing path membership against `git status --porcelain` output,
      normalise every Player-reported path via `Path(p).resolve().relative_to(worktree_root)`
      (or equivalent). Both the porcelain set and the Player's set are
      converted to the same canonical form (relative to worktree root, no
      symlink, posix separator).
- [ ] After normalisation, audit a deduplicated set — so if the Player
      reports the same file under both absolute and relative forms, the
      audit treats them as one claim.
- [ ] Existing valid audit behaviour preserved: paths that genuinely don't
      stage (e.g. truly gitignored files, or claimed paths that don't exist
      on disk) must still be flagged.

### AC-002: Diagnostic-message overhaul

- [ ] When the audit decides a path is unstaged, run **both** of:
      - `git check-ignore -v <path>` (and capture matching rule + source file
        if any)
      - `os.path.exists(path)` / `Path(path).exists()`
      The issue's `description` and `details` must include the **actual**
      check-ignore output (or "no rule matched") and existence boolean.
- [ ] Remove or downgrade the speculative "Most common cause: an unanchored
      .gitignore rule silently filters the file" sentence unless
      `check-ignore -v` confirms it. (The current wording sent a downstream
      diagnostic review chasing a wrong hypothesis for a non-trivial
      amount of time.)
- [ ] Add a third checked condition: was the path written by the harness
      itself (see AC-003)?

### AC-003: Harness-owned path allowlist

- [ ] Add an explicit allowlist of paths the Coach should **never** include
      in claim-audit reasoning, including at minimum:
      - `.guardkit/autobuild/<TASK_ID>/player_turn_*.json`
      - `.guardkit/autobuild/<TASK_ID>/coach_turn_*.json`
      - `.guardkit/autobuild/<TASK_ID>/coach_feedback_for_turn_*.json`
      - `.guardkit/autobuild/<TASK_ID>/state_transitions.json`
      - `.guardkit/autobuild/<TASK_ID>/turn_state_turn_*.json`
      - `.guardkit/autobuild/<TASK_ID>/turn_context.json`
      - `.guardkit/autobuild/<TASK_ID>/task_work_results.json`
      - `.guardkit/autobuild/<TASK_ID>/phase_4_summary.json`
      - `.guardkit/autobuild/<TASK_ID>/specialist_results.json`
      - `.guardkit/autobuild/<TASK_ID>/checkpoints.json`
      The Coach can still verify these exist if it wants, but they must
      never produce a Player-claim-audit issue, because the Player has no
      control over how the harness writes them.

### AC-004: Promotion-gate review

- [ ] When `validation_results.quality_gates is None` (i.e. validation could
      not run because of a protocol violation or similar upstream
      condition), the decision must NOT silently elevate audit-honesty
      warnings into `must_fix` issues. Instead, the decision should be:
      - `decision: blocked` (or equivalent existing "blocked-pending-validation"
        state), with a clear top-level issue naming the missing validation,
        and audit warnings preserved as warnings only.
- [ ] OR, equivalently, the audit-promotion rule must be made independent
      of the quality-gates result so the same defect produces the same
      decision regardless of upstream protocol violations.

### AC-005: Pre-flight `git check-ignore` gate

- [ ] Before turn 1 of any task, walk the task's planned target file list
      (sourced from the implementation plan if one is on disk, else the
      task's `files_to_create` / similar frontmatter field) through
      `git check-ignore -v` in the worktree.
- [ ] If any planned target IS git-ignored, fail-fast with an error message
      that names the exact rule and its source file (the very thing the
      current Coach message *speculates* about but cannot prove). Block the
      run before the Player burns SDK turns.
- [ ] If no implementation plan / file list is available, skip the
      pre-flight (don't fail-open with a warning).

### AC-006: Regression test suite

- [ ] Unit test: feed the audit a path-set where the Player reports the
      same staged file under both absolute and relative form. Assert: no
      audit issue, single resolved-paths entry.
- [ ] Unit test: feed the audit a Player-reported path that genuinely is
      gitignored (use a tmp_path fixture with `.gitignore` containing a
      matching rule). Assert: audit issue is raised AND the issue body
      contains the matching `check-ignore -v` rule string.
- [ ] Unit test: feed the audit a Player-reported path that does not exist
      on disk. Assert: audit issue is raised AND the issue body says
      `path_exists: false`.
- [ ] Unit test: feed the audit a Player-reported harness-owned path (e.g.
      a `player_turn_N.json` under `.guardkit/autobuild/`). Assert: no audit
      issue raised (allowlisted).
- [ ] Unit test: validation_results.quality_gates is None + audit
      discrepancy present. Assert: decision is `blocked` (not `feedback`)
      and audit issue is warning, not must_fix.
- [ ] Integration test: replay the FEAT-JARVIS-006 fail-run-1 Player
      turn-1 report against the fixed audit logic and assert decision is
      `approve` (or at worst, audit issues are downgraded to warnings).

## Out of Scope

- The downstream `jarvis` tactical fix (re-queuing fail-run-2). Tracked in
  jarvis as `TASK-J006-006`.
- Any change to the Player's prompting / contract about path formats. (A
  player-side worktree-relative-paths directive is a valid belt-and-braces
  workaround on the consumer side, but the audit must be correct
  regardless.)
- Changing the unrecoverable-stall detector. It did the right thing on the
  failed run; it just happened to be exiting on a false-positive signal.

## Notes

External evidence — read these before starting:

- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.claude/reviews/TASK-REV-J6F1-review-report.md`
  (full review with command outputs, A/B/C bucket table for 20 flagged paths,
  cross-task comparison showing why J006-002 escaped and J006-003 didn't)
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-JARVIS-006/.guardkit/autobuild/TASK-J006-003/coach_turn_1.json`
  (raw must_fix issues)
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-JARVIS-006/.guardkit/autobuild/TASK-J006-003/player_turn_1.json`
  (mixed absolute/relative path claims)
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-JARVIS-006/.guardkit/autobuild/TASK-J006-002/player_turn_1.json`
  + `coach_turn_1.json` (the negative control — same path-format defect but
  passed because quality_gates were non-null)

The autobuild worktree at the external path above is preserved with the
failed run's full event log — useful for the integration test in AC-006.
