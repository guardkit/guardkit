---
id: TASK-FIX-HEAB-FOLLOWUP
title: Complete TASK-FIX-HEAB autobuild-loop integration — _check_honesty_early_abort helper + early-exit wiring
status: completed
task_type: implementation
implementation_mode: task-work
parent_task: TASK-FIX-HEAB
priority: medium
created: 2026-05-10T19:35:00Z
updated: 2026-05-10T20:35:00Z
completed: 2026-05-10T20:35:00Z
completed_location: tasks/completed/TASK-FIX-HEAB-FOLLOWUP/
organized_files:
  - TASK-FIX-HEAB-FOLLOWUP.md
previous_state: in_review
state_transition_reason: "All ACs satisfied; AC-4 tests pass 3/3; regression sweep stable"
complexity: 3
tags: [autobuild, honesty-verification, early-abort, partial-implementation, half-merged]
related_tasks:
  - TASK-FIX-HEAB
  - TASK-FIX-RBSS
  - TASK-FIX-IGNR
inputs:
  source_files:
    - guardkit/orchestrator/autobuild.py
    - guardkit/orchestrator/feature_orchestrator.py
    - guardkit/cli/autobuild.py
  test_file: tests/unit/orchestrator/test_honesty_early_abort.py
  origin_commit: 18e0ea16  # complete(TASK-FIX-HEAB) — only the perimeter actually landed
  origin_external_review: ../study-tutor/.claude/reviews/TASK-REV-F30A-review-report.md
test_results:
  status: pass
  target_file: tests/unit/orchestrator/test_honesty_early_abort.py
  target_count: 3
  target_passed: 3
  regression_sweep: "607 passed / 14 pre-existing failures (env-bootstrap + prompt-builder) — same set as baseline"
  coverage: null
  last_run: 2026-05-10T20:30:00Z
---

# Task: Complete TASK-FIX-HEAB autobuild-loop integration

## Description

The TASK-FIX-HEAB commit `18e0ea16` ("complete(TASK-FIX-HEAB): honesty rolling-average early-abort for autobuild loop") landed the perimeter — CLI flags (`cli/autobuild.py:243-263, 284-285, 375-392, 490-491`), `FeatureOrchestrator` ctor params + forwarding (`feature_orchestrator.py:534-535, 629-630, 2953-2954`), and the test file (`tests/unit/orchestrator/test_honesty_early_abort.py`) — but **did not land the AutoBuildOrchestrator-level integration** the commit message claimed:

> "New AutoBuildOrchestrator ctor params honesty_early_abort_threshold (default 0.3) and honesty_early_abort_window (default 3); propagated through FeatureOrchestrator..."
> "New _check_honesty_early_abort helper. Computes the rolling avg over _honesty_history[-window:]..."

Neither change was actually applied to `autobuild.py`. The 8-line autobuild.py diff in the commit is RBSS-flavoured session-clearing code, not HEAB code.

**Symptom**: every per-task `AutoBuildOrchestrator(...)` call from `FeatureOrchestrator` raises `TypeError: AutoBuildOrchestrator.__init__() got an unexpected keyword argument 'honesty_early_abort_threshold'`. No autobuild can complete a wave on this guardkit version. Discovered during study-tutor FEAT-39E1 run-4 attempt (2026-05-10), trace at `~/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-39E1-run-4.md`.

**Stub patch already in tree**: as a temporary unblock, `AutoBuildOrchestrator.__init__` now accepts and stores both kwargs but does not use them (see comment at the assignment site). This restores pre-HEAB behaviour (no early abort) so autobuilds can run. The stub is an explicit pointer to this followup task.

This task closes the gap by landing the `_check_honesty_early_abort` helper and wiring it into the adversarial loop so HEAB actually fires on sustained low honesty.

## Acceptance Criteria

- [ ] **AC-1**: New private method `_check_honesty_early_abort(self, turn: int) -> Optional[str]` on `AutoBuildOrchestrator`. Returns `None` if no abort indicated; returns an operator-facing message (per the original TASK-FIX-HEAB spec) when:
  1. `len(self._honesty_history) >= self.honesty_early_abort_window`, AND
  2. `mean(self._honesty_history[-self.honesty_early_abort_window:]) < self.honesty_early_abort_threshold`.
- [ ] **AC-2**: Diagnostic message contains: rolling average value, threshold, most-flagged `player_claim` across the window (top 1 from `coach_result.report["issues"][*]["details"]["player_claim"]` filtered to honesty/claim_audit categories), and a best-effort `git check-ignore -v <path>` recommendation when the path matches a `.gitignore` rule (skip the rec line if no match).
- [ ] **AC-3**: Loop integration: in `_loop_phase` (around `autobuild.py:2242` after `_record_honesty`), call `_check_honesty_early_abort`. When it returns non-None, log the message via the orchestrator's logger AND return `(turn_history, "honesty_collapse")` from the loop function — short-circuiting to the existing `honesty_collapse` Decision tabulation that the original commit added to the literal types.
- [ ] **AC-4**: The 3 existing tests in `tests/unit/orchestrator/test_honesty_early_abort.py` pass:
  - `test_honesty_early_abort_triggers_at_threshold`: sequence `[0.6, 0.4, 0.2, 0.1]` aborts at turn 3 with threshold 0.5
  - `test_honesty_early_abort_does_not_trigger_when_above_threshold`: sequence `[0.9, 0.85, 0.95]` never trips with default 0.3
  - `test_honesty_early_abort_window_partial_data`: fewer than `window` samples → no abort
- [ ] **AC-5**: Existing autobuild unit-test sweep stays green (the commit message claimed "193-test regression sweep across honesty, quality_gates, and autobuild unit suites stays green" — re-validate).
- [ ] **AC-6**: Remove or update the stub comment block in `AutoBuildOrchestrator.__init__` (currently labelled "TASK-FIX-HEAB stub"); replace with a real docstring describing the kwargs.

## Implementation Notes

The infrastructure for HEAB *almost* exists in autobuild.py already:

```python
# autobuild.py:1042  (already present)
self._honesty_history: List[float] = []  # Track honesty scores across turns

# autobuild.py:2242 (already present, after each turn)
self._record_honesty(turn_record)

# autobuild.py:4383+ (already implements the 3-turn average + log line)
def _record_honesty(self, turn_record):
    ...
    if len(self._honesty_history) >= 3:
        avg_honesty = sum(self._honesty_history[-3:]) / 3
        ...
```

So the `_check_honesty_early_abort` helper can reuse `self._honesty_history`. The thresholds come from the new ctor params (now stored). The rolling-average logic at line 4415-4418 already exists for logging — refactor it into the helper or copy the formula.

**Most-flagged player_claim extraction** (AC-2): turn_history's `coach_result.report["issues"]` is the source. Filter to entries where `category in {"honesty", "claim_audit"}`, extract `details["player_claim"]`, count across the window, return the top 1.

**git check-ignore call** (AC-2): wrap in try/except; on any error return None for the rec-line so the diagnostic still fires. Use `--no-index` for the same reason as TASK-FIX-IGNR.

**Loop exit** (AC-3): the `honesty_collapse` Decision value should already be in the literal types (the commit message claimed "added to every Literal[...] in autobuild.py + progress.py FinalStatus + status_colors, plus FAILURE_CATEGORY_MAP, _build_summary_details, _build_error_message, _finalize_phase blocked-report check, and the next_steps block"). Verify the literal additions actually landed; if not, that's part of this task too.

The total change is ~30-50 lines + minor literal/match-arm updates. Should match what the original commit message advertised.

## Why this matters

Without HEAB actually firing, the next stale-worktree-gitignore-class incident will repeat the run-3 pattern: 5 turns of futile retries, ~12 minutes of SDK time, no actionable diagnostic. The whole point of HEAB was to make these self-evident inside one run, not via post-mortem.

The fact that `test_honesty_early_abort.py` is failing on HEAD (3 of 3) means CI did not gate this commit — the merge protected only "build" and "imports", not test results. Fixing the integration also restores the test gate.
