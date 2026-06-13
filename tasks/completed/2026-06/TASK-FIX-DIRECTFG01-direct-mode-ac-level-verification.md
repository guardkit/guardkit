---
id: TASK-FIX-DIRECTFG01
title: Close the direct-mode false-green — run AC-level / wiring verification even when Coach gates are required=False
status: completed
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T15:10:00Z
completed: 2026-06-13T15:10:00Z
previous_state: in_review
completed_location: tasks/completed/2026-06/
state_transition_reason: "Quality gates passed (compile + 22/22 tests, code review 88/100 APPROVE); completed via /task-complete"
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

- [x] In `direct` implementation_mode, the Coach still runs AC-level verification
      against disk (the task's acceptance criteria are checked for evidence, not
      assumed met) before `decision=approve`. Relaxed `required=False` gates may
      stay relaxed for *test/coverage thresholds*, but **AC delivery must not be
      assumed**.
- [x] Wiring evidence (the FEAT-C332 `WiringWiringAnalyzer` UNWIRED_PATH /
      MOCKED_SEAM probes) is consulted on the direct-mode path too — a registered
      bin entry / composition-root edge that does not resolve is surfaced as
      feedback, never silently approved.
- [x] A registered CLI bin-entry whose target raises on `python <path>` (import
      error / traceback / non-zero exit with empty stdout) is treated as an
      ABSENT producer signal → feedback, not approve.
- [x] Regression test: a synthetic direct-mode task whose deliverable is a
      broken wrapper (imports a missing module) and whose own test is green must
      NOT receive `decision=approve`.
- [x] No change to `task-work` (full) mode behaviour, which already verified
      correctly in run 3 (TSJ-001 real green).

## Implementation Result (2026-06-13, /task-work)

A deterministic `_direct_mode_evidence_gate` was added to
`guardkit/orchestrator/autobuild.py`, mirroring the existing `_evidence_repo_gate`
precedent: it runs in BOTH Coach paths (`_invoke_coach_legacy` and
`_invoke_coach_primary`) AFTER `_evidence_repo_gate` and BEFORE the LLM Coach, so
neither path (incl. a `GUARDKIT_COACH_LEGACY=1` revert) can bypass it. It is a
structural no-op unless `task_work_results.quality_gates.quality_gates_relaxed is
True` — the flag written ONLY by `_write_direct_mode_results` — so full task-work
mode is untouched (AC5).

- **AC1**: `validator.validate_requirements(...)` is run in direct mode; an unmet
  criterion (no disk/promise evidence) blocks the turn (`direct_mode_ac_unverified`).
- **AC2**: `_run_wiring_analysis(..., task_type="feature", ...)` is consulted; an
  `UNWIRED_PATH` finding on an authored, registered bin-entry blocks
  (`direct_mode_wiring_gap`). Fail-open otherwise (no invented false-reds).
- **AC3**: `_check_direct_mode_bin_entries` executes each `bin-entries.txt ∩
  authored` `.py` target as a subprocess (`cwd=worktree`, clean
  `PYTHONPATH=worktree` only, `stdin=DEVNULL`, 10 s timeout, never imported). A
  Python traceback / non-zero-exit-with-empty-stdout / timeout → ABSENT producer
  → block (`direct_mode_bin_entry_broken`). Non-Python entry → non-blocking
  `should_fix` advisory. Exit-0 (even empty stdout) → PRESENT.
- **Block mechanism**: `_emit_synthetic_coach_feedback` (decision `feedback`),
  rationale naming the categories + specifics for the Player's next turn.

**Verification**: 22 targeted tests in
`tests/orchestrator/test_direct_mode_false_green_regression.py` (AC4 asserts the
LLM Coach `invoke_coach` is NOT called when the gate blocks — proving the block is
pre-LLM). 81 pass across all touched Coach suites. A dead-code bug in AC2 (the
wiring discriminator filtered on `kind` instead of the factory's `pattern` key)
was caught during independent verification and fixed; the regression test was
empirically falsified (reverting `pattern`→`kind` makes it fail).

**Quality gates**: compilation ✅ · tests 100% (22/22 new, 81 across touched
suites) ✅ · new code branch-covered by the 22 tests ✅. Phases run via agents:
planning → architectural review (74/100) → implementation → testing → code review
(88/100, APPROVE). Change surface: `guardkit/orchestrator/autobuild.py` (+421) and
the new test file only.

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Finding 2".
- Run log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log` (lines ~444 onward, Wave 2).
- Coach verdict: `.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-002/coach_turn_1.json`.
- Sibling rules: `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/evidence-boundary-narrower-than-write-surface.md`,
  `.claude/rules/namespace-hygiene.md`.
</content>
