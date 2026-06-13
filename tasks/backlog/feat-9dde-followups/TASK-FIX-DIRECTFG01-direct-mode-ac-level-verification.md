---
id: TASK-FIX-DIRECTFG01
title: Close the direct-mode false-green — run AC-level / wiring verification even when Coach gates are required=False
status: backlog
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T12:40:00Z
priority: high
complexity: 5
related: [TASK-AB-FIX-INVAB1, TASK-AB-XREPOEV01, FEAT-C332, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, coach, direct-mode, false-green, qa-verifier, absence-of-failure]
---

# Task: Close the `direct` implementation_mode false-green

## Why this task exists

FEAT-9DDE run 3 (2026-06-13, qwen3-coder-30b Player) built both tasks to
`APPROVED`, but on-disk verification found **Wave 2 / TASK-TSJ-002 was a
false-green**:

- TSJ-002 ran in `implementation_mode: direct`. Its turn-1 Coach validation
  logged `Quality gate evaluation complete: tests=True … audit=True
  ALL_PASSED=True`, but **every gate ran `required=False`** (the direct-mode
  relaxation), so the Coach approved without verifying the task's acceptance
  criteria against disk.
- The delivered bin-entry wrapper (`installer/core/commands/task-status-json.py`)
  was **non-functional** — an off-by-one `sys.path.insert` raised
  `ModuleNotFoundError`, so the registered `task-status-json` command emitted a
  traceback and **no JSON**. It also re-introduced the documented
  `namespace-hygiene` `sys.path.insert(0, …)` hazard.
- AC3b ("remove the orphaned `export:json` mention") was simply not done.

The Player's own added "integration test" was green over the broken wiring — a
textbook SPEC_GAP. The root cause is **mechanism, not model**: direct mode trusts
the Player on "simple" tasks and the local coder Player makes plausible-but-
spec-violating choices that the relaxed gates wave through.

This is a member of the `absence-of-failure-is-not-success` /
`evidence-boundary-narrower-than-write-surface` family: a binary APPROVE with no
positive AC-level / wiring evidence behind it.

(The specific TSJ-002 deliverable was hand-corrected on the `autobuild/FEAT-9DDE`
branch — see commit `fix(TASK-TSJ-002): point bin-entry at real producer …`.
This task is the *systemic* fix so the class can't recur.)

## Acceptance Criteria

- [ ] In `direct` implementation_mode, the Coach still runs AC-level verification
      against disk (the task's acceptance criteria are checked for evidence, not
      assumed met) before `decision=approve`. Relaxed `required=False` gates may
      stay relaxed for *test/coverage thresholds*, but **AC delivery must not be
      assumed**.
- [ ] Wiring evidence (the FEAT-C332 `WiringWiringAnalyzer` UNWIRED_PATH /
      MOCKED_SEAM probes) is consulted on the direct-mode path too — a registered
      bin entry / composition-root edge that does not resolve is surfaced as
      feedback, never silently approved.
- [ ] A registered CLI bin-entry whose target raises on `python <path>` (import
      error / traceback / non-zero exit with empty stdout) is treated as an
      ABSENT producer signal → feedback, not approve.
- [ ] Regression test: a synthetic direct-mode task whose deliverable is a
      broken wrapper (imports a missing module) and whose own test is green must
      NOT receive `decision=approve`.
- [ ] No change to `task-work` (full) mode behaviour, which already verified
      correctly in run 3 (TSJ-001 real green).

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Finding 2".
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (lines ~444 onward, Wave 2).
- Coach verdict: `.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-002/coach_turn_1.json`.
- Sibling rules: `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/evidence-boundary-narrower-than-write-surface.md`,
  `.claude/rules/namespace-hygiene.md`.
</content>
