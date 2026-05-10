---
id: TASK-FIX-HEAB
title: Honesty early-abort — exit the adversarial loop when 3-turn rolling average drops below threshold instead of burning all max_turns
status: completed
previous_state: in_review
state_transition_reason: "All ACs satisfied, tests pass, light-intensity workflow complete"
completed: 2026-05-10T20:45:00Z
completed_location: tasks/completed/TASK-FIX-HEAB/
task_type: implementation
implementation_mode: task-work
parent_review: TASK-REV-F30A
external_origin: study-tutor/tasks/backlog/TASK-REV-F30A-analyse-feat-39e1-autobuild-run-3-failure.md
priority: low
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T20:00:00Z
complexity: 3
tags: [autobuild, honesty-verification, early-abort, observability, cost-control]
related_tasks:
  - TASK-FIX-IGNR
  - TASK-FIX-RBSS
dependencies: []
inputs:
  source_files:
    - guardkit/orchestrator/autobuild.py
    - guardkit/orchestrator/quality_gates/coach_validator.py
  reference: |
    autobuild.py:2150-2350 (turn loop)
    coach_validator.py:865-905 (gate short-circuit)
test_results:
  status: passed
  coverage: targeted
  last_run: 2026-05-10T20:30:00Z
  unit_tests:
    file: tests/unit/orchestrator/test_honesty_early_abort.py
    passed: 3
    failed: 0
  related_pass: 193  # honesty + quality_gates + autobuild unit tests touched-area
---

# Task: Honesty early-abort — exit when 3-turn rolling average drops below threshold

## Description

When the Coach honesty short-circuits gate evaluation due to repeated critical issues, the orchestrator currently keeps running until `max_turns` is exhausted. In FEAT-39E1 run-3 PH1-004 ([TASK-REV-F30A review](study-tutor/.claude/reviews/TASK-REV-F30A-review-report.md)), the honesty curve `0.86 → 0.66 → 0.47 → 0.11 → 0.07` was a one-bug-amplifying-itself signal that nothing the Player did would unstick — but the loop spent 5 turns and ~12 minutes of SDK time before hitting the wall.

A simple heuristic — abort when the rolling average over the most recent N turns drops below threshold — would have caught this at turn 3 (avg 0.66) or turn 4 (avg 0.41) with a clearly-named diagnostic, saving SDK cost and giving the operator an actionable error message.

This is a small targeted change, intentionally narrower than TASK-FIX-IGNR (which addresses the *cause* of the divergence). HEAB addresses the *symptom* and is useful even if IGNR ships, because honesty can degrade for reasons other than gitignore drops.

## Acceptance Criteria

- [x] **AC-1**: New `AutoBuildOrchestrator` config field `honesty_early_abort_threshold` (default `0.3`) and `honesty_early_abort_window` (default `3`). Both configurable from the autobuild CLI / feature.yaml.
- [x] **AC-2**: After each turn's honesty score is recorded (`autobuild.py` near line 2242 `_record_honesty`), compute the rolling average over the last `honesty_early_abort_window` turns. If we have at least `honesty_early_abort_window` honesty samples AND the average is `< honesty_early_abort_threshold`, return `(turn_history, "honesty_collapse")` and exit the loop.
- [x] **AC-3**: New `Decision` value `honesty_collapse` recognised by the feature orchestrator's outcome tabulation; treated similarly to `max_turns_exceeded` for stop-on-failure but with a distinct exit message.
- [x] **AC-4**: The exit message names: (a) the rolling average, (b) the threshold, (c) the most-frequently-flagged path across the window (top 1 by occurrence in `discrepancies[*].player_claim`), (d) a `git check-ignore -v <path>` recommendation if the orchestrator detects the path is in any `.gitignore`. Example:

  > Aborting TASK-NATS-PH1-004 after turn 4: 3-turn rolling honesty 0.21 < threshold 0.30. Most-flagged path: `src/study_tutor/adapters/command_router.py` (flagged 3 of last 3 turns). Run `git check-ignore -v src/study_tutor/adapters/command_router.py` to confirm a .gitignore rule isn't silently dropping it. Saved 1 turn(s) of further SDK cost.

- [x] **AC-5**: New unit test `test_honesty_early_abort_triggers_at_threshold` simulates 4 turns with honesty `[0.6, 0.4, 0.2, 0.1]` and asserts the loop exits at turn 3 with `decision="honesty_collapse"`.
- [x] **AC-6**: Test `test_honesty_early_abort_does_not_trigger_when_above_threshold` simulates `[0.9, 0.85, 0.95]` and asserts the loop continues normally.
- [x] **AC-7**: Test `test_honesty_early_abort_window_partial_data` ensures the early-abort does NOT fire when fewer than `honesty_early_abort_window` turns have completed (avoid first-turn false trips).

## Implementation Summary

**Files modified**:
- `guardkit/orchestrator/autobuild.py` — new ctor params, `_check_honesty_early_abort` helper, loop hook after `_record_honesty`, `honesty_collapse` added to all `Literal[...]` decision types, `FAILURE_CATEGORY_MAP` entry, summary/error/finalize/next_steps branches.
- `guardkit/orchestrator/feature_orchestrator.py` — propagate threshold/window from FeatureOrchestrator to per-task AutoBuildOrchestrator.
- `guardkit/orchestrator/progress.py` — `honesty_collapse` added to `FinalStatus` Literal and `status_colors` map.
- `guardkit/cli/autobuild.py` — `--honesty-early-abort-threshold` and `--honesty-early-abort-window` CLI options on both `task` and `feature` subcommands; task subcommand cascades from CLI flag → task frontmatter `autobuild.honesty_early_abort_*` → defaults.

**Tests added**:
- `tests/unit/orchestrator/test_honesty_early_abort.py` (3 tests, all passing).

**Design notes**:
- AC-5 uses test-local `threshold=0.5` so that `avg([0.6, 0.4, 0.2]) = 0.4` strictly satisfies `rolling_avg < threshold` and the abort fires at turn 3 as the AC dictates. The default threshold of 0.3 is intentionally conservative for production.
- Most-flagged path is read from `coach_result.report["issues"][*]["details"]["player_claim"]` filtered to categories `honesty` and `claim_audit` — the serialized `honesty_verification` dict only carries `discrepancy_count`, not the full discrepancy list, so the AC's pseudo-code (`t.coach_result.honesty_verification.discrepancies`) doesn't exist on the runtime side. Reading from `issues` lets HEAB land without modifying the frozen `coach_validator.py` to_dict serialization.
- `git check-ignore -v` advice is best-effort and only emitted when the path actually matches a rule (per AC-4 caveat).

## Implementation Notes

- This is a ~30-line change in `autobuild.py` plus three tests. Computing the rolling average is a one-liner over `[t.coach_result.honesty_verification.honesty_score for t in turn_history[-window:]]`.
- The "most-flagged path" calculation is straightforward: `Counter([d.player_claim for t in turn_history[-window:] for d in (t.coach_result.honesty_verification.discrepancies or [])]).most_common(1)[0][0]`.
- The `git check-ignore -v` recommendation in AC-4 should be best-effort; if the path doesn't actually match any rule, omit that line (don't print misleading advice).
- Coordinates well with TASK-FIX-IGNR: once IGNR ships, gitignored claims become `should_fix` not `critical`, so the honesty score won't drop on those alone — but HEAB still catches genuine adversarial-loop divergence (e.g. a Player consistently lying about test results).
- Lower priority than IGNR / RBSS because it's a guardrail, not a fix. Tackle after IGNR or in parallel if a separate Player has spare cycles.
