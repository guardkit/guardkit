---
id: TASK-GK-COACH-001
title: Stall extender must tolerate single 0 → N criteria-count transition (plateau case)
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T12:45:00Z
completed: 2026-05-07T12:45:00Z
completed_location: tasks/completed/2026-05/TASK-GK-COACH-001/
previous_state: in_review
state_transition_reason: "All 8 ACs satisfied; user-directed completion"
priority: high
priority_band: P1
task_type: feature
parent_review: TASK-REV-PEBR-002
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md
parent_feature_folder: autobuild-feat-pebr-failure-recovery-rev2
related_tasks:
  - TASK-GK-CV-001
  - TASK-AB-SD01
  - TASK-REV-E719
  - TASK-REV-PEBR-002
implementation_mode: task-work
wave: 1
complexity: 3
estimated_minutes: 60
dependencies: []
tags:
  - autobuild
  - stall-detector
  - regression-fix
  - feat-pebr
  - bug-c
  - P1
test_results:
  status: passed
  coverage: skipped (MINIMAL intensity)
  last_run: 2026-05-07T12:30:00Z
  new_tests: 5
  new_tests_file: tests/unit/orchestrator/test_autobuild_stall_detector_plateau.py
  regression_suites:
    - tests/unit/test_autobuild_stall_detection.py (27/27)
    - tests/unit/test_run3_stall_fixes.py::TestStallDetectorPartialProgress (6/6)
    - tests/unit/test_autobuild_orchestrator.py (all pass)
  ac_2_contract_verified: "test fails on unpatched main; passes after fix"
---

# Task: Stall extender must tolerate single 0 → N criteria-count transition (plateau case)

## Description

`AutoBuildOrchestrator._is_feedback_stalled`
([`guardkit/orchestrator/autobuild.py:3935-4022`](../../../guardkit/orchestrator/autobuild.py))
implements TASK-AB-SD01's stall detector with TASK-REV-E719 Fix 3's
"partial-progress runway extension". When criteria_passed is non-zero,
the standard 3-turn check is bypassed and an extended 5-turn
uniformity check is required to fire stall.

The extended check at lines 4002-4013 currently requires:

- `len(history) >= extended_threshold (5)`
- `len(ext_sigs) == 1` (all 5 turns same signature)
- `all(c == ext_counts[0] for c in ext_counts)` — all 5 turns same
  count

This last condition is **too strict**. When the criteria_passed count
climbs once (e.g. 0 → 7 between turn 1 and turn 2) and then plateaus
on a non-criteria gate failure (e.g. plan_audit), the trailing 4
turns are uniform but turn 1's count anchors the window at 0, so
`ext_counts = [0, 7, 7, 7, 7]` is not uniform → stall doesn't fire.

**FEAT-PEBR run-2 fingerprint** (full trace in
[the review report](../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md),
AC-5):

| Turn | criteria_met | sig | history (after append)            | extended check                                      | result    |
|------|--------------|-----|-----------------------------------|-----------------------------------------------------|-----------|
| 1    | 0            | A   | `[(A,0)]`                         | `len < 3`                                           | False     |
| 2    | 7            | A   | `[(A,0),(A,7)]`                   | `len < 3`                                           | False     |
| 3    | 7            | A   | `[(A,0),(A,7),(A,7)]`             | recent counts `[0,7,7]` not equal                   | False     |
| 4    | 7            | A   | `[(A,0),(A,7),(A,7),(A,7)]`       | recent equal but `count[0]≠0`; ext `len=4 < 5`      | False ★   |
| 5    | 7            | A   | `[(A,0),(A,7),(A,7),(A,7),(A,7)]` | recent equal but `count[0]≠0`; ext `[0,7,7,7,7]` not uniform | False ★ |

★ run-2 logs at lines 1485 and 1587 confirm both warnings fired —
the detector saw the problem and chose not to escalate.

After 5 turns of identical Coach feedback the loop falls through to
`max_turns_exceeded`. The Player has nowhere to go — the only
failing gate is plan_audit with a constant `missing_files` payload —
but the orchestrator burned 5 turns × 7 minutes per turn (~35
minutes wasted SDK time per occurrence).

## Why "0 → N then plateau" happens

The 0 → N transition between turn 1 and turn 2 is a recurring
fingerprint of TASK-GK-CV-001 (Bug B): turn 1 the Player emits
`criterion_id="AC-1"`, Coach's matcher misses (zero-padded fallback);
turn 2 Player adapts to `criterion_id="AC-001"`, lookup hits,
criteria_met flips to N. With TASK-GK-CV-001 fixed, this specific
trigger goes away — but the underlying stall-detector blind spot
remains for any future shape where the count climbs once and
plateaus on a non-criteria gate.

This task closes the structural blind spot; landing TASK-GK-CV-001
removes the most common trigger but does not remove the bug.

## Acceptance Criteria

- [ ] **AC-1 — Stall fires on the 0 → N plateau pattern.** Modify
  `_is_feedback_stalled` so that when:
  - `len(history) >= 5`,
  - all 5 signatures match,
  - the trailing 4 counts (i.e. `ext_counts[1:]`) are uniform AND
    non-zero,

  the detector returns True (stall fires). Implementation note: this
  is a single conditional addition inside the existing extended-check
  branch; do not change the standard 3-window check.
- [ ] **AC-2 — Repro test using FEAT-PEBR run-2 signature.** Add
  `tests/unit/orchestrator/test_autobuild_stall_detector.py` (or
  extend the existing stall-detector test file) with class
  `TestPartialProgressPlateauStall`:
  - Fixture: feedback signature constant across 5 turns; counts
    `[0, 7, 7, 7, 7]`.
  - Expected: `_is_feedback_stalled` returns `True` at turn 5.
  - This must FAIL on `main` (returns False) and PASS after the fix.
- [ ] **AC-3 — Legitimate progress is NOT stalled.** Add a parallel
  fixture where the count rises across turns:
  `[0, 3, 5, 7, 7]` — the Player is still making progress, just
  slower. The detector must NOT return True (this is correct
  partial-progress behaviour preserved from TASK-REV-E719 Fix 3).
- [ ] **AC-4 — Pre-existing 0/0/0 stall path unchanged.** Add (or
  verify existing) fixture for the standard-threshold case: counts
  `[0, 0, 0]` with constant signature → stall fires at turn 3
  unchanged.
- [ ] **AC-5 — Pre-existing all-N stall path unchanged.** Counts
  `[7, 7, 7, 7, 7]` (uniform from turn 1) with constant signature
  → stall fires at turn 5 via the existing extended-uniformity
  branch.
- [ ] **AC-6 — Different signature breaks stall.** Counts
  `[7, 7, 7, 7, 7]` with signature changes (e.g.
  `[A, A, B, A, A]`) — must NOT stall. The signature uniformity
  check is preserved.
- [ ] **AC-7 — Regression: existing test suite stays green.** All
  tests under `tests/unit/test_autobuild_orchestrator.py`,
  `tests/orchestrator/test_autobuild_*.py`,
  `tests/seam/test_autobuild_coach.py` continue to pass.
- [ ] **AC-8 — All modified files pass project-configured lint/format
  checks** (ruff). New / modified test files pass cleanly.

## Out of Scope

- Bug A (qualified prose paths in plan-audit scanner) — covered by
  TASK-GK-PA-002.
- Bug B (Coach AC-ID matching) — covered by TASK-GK-CV-001.
- Reset-turn exemption (rev-1 review item #9, withdrawn in rev 2).
  This task replaces that withdrawn item.
- Operator-feedback truncation reordering (rev-1 review item #4) —
  separate task.

## Files to Create

- `tests/unit/orchestrator/test_autobuild_stall_detector_plateau.py`
  (or extend an existing stall-detector test file if one is present)

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (the `_is_feedback_stalled`
  function at lines 3935-4022; specifically the extended-check
  branch at lines 4002-4013)

## Implementation notes

### Recommended implementation

Inside the existing extended-check branch
(`autobuild.py:4002-4013`), add a "plateau-tolerant" sub-condition:

```python
# Existing extended check
if len(self._feedback_history) >= extended_threshold:
    extended_recent = self._feedback_history[-extended_threshold:]
    ext_sigs = {sig for sig, _ in extended_recent}
    ext_counts = [count for _, count in extended_recent]
    if len(ext_sigs) == 1:
        # Existing strict uniformity: all 5 counts equal
        if all(c == ext_counts[0] for c in ext_counts):
            logger.warning(
                f"Feedback stall: identical feedback (sig={feedback_sig}) "
                f"for {extended_threshold} turns with {ext_counts[0]} "
                f"criteria passing (extended threshold for partial progress)"
            )
            return True
        # NEW: plateau-tolerant — turn 1 may differ if the rest are
        # uniform AND non-zero. Closes the 0→N then plateau case
        # surfaced by FEAT-PEBR run-2 (TASK-REV-PEBR-002).
        tail = ext_counts[1:]
        if (
            len(tail) >= extended_threshold - 1
            and all(c == tail[0] for c in tail)
            and tail[0] > 0
            and tail[0] != ext_counts[0]  # there must be an actual transition
        ):
            logger.warning(
                f"Feedback stall: identical feedback (sig={feedback_sig}) "
                f"for {extended_threshold - 1} consecutive turns with "
                f"{tail[0]} criteria passing after a 1-turn count "
                f"transition (plateau-tolerant extended threshold)"
            )
            return True
```

The `tail[0] != ext_counts[0]` guard avoids redundant double-firing
when the strict uniformity branch already matched; it's defensive,
the code paths are exclusive in practice but easier to reason about
explicitly.

### Why "1-turn transition only"

The fix is narrow on purpose: it tolerates **exactly one** count
change between turn 1 and turn 2, then requires the rest of the
window to be uniform. This pattern is the Bug B signature (Player
adapts ID format on turn 1, then plateaus). It does NOT match
legitimate slow-progress patterns like `[0, 3, 5, 7, 7]` where the
count keeps changing across turns.

If a future bug surfaces a 2-step transition (`[0, 3, 7, 7, 7]`),
that's a different shape and a different fix; do not over-generalise
this one.

### Regression risk

- The new branch fires *strictly more* stalls than today (it adds a
  case). Verify that no legitimate slow-progress fixture in the
  existing test suite is reclassified as a stall by running the
  full stall-detector suite. AC-3 and AC-7 cover this.
- The `tail[0] > 0` guard ensures we never re-fire on the existing
  `counts[0] == 0` standard threshold case (which fires at turn 3,
  not turn 5).
- The new branch only fires when `len(history) >= 5`, so turns 1-4
  are unaffected.

## Test requirements

- Unit tests in
  `tests/unit/orchestrator/test_autobuild_stall_detector_plateau.py`
  per ACs 2-6.
- Existing regression suites under
  `tests/unit/test_autobuild_orchestrator.py`,
  `tests/orchestrator/test_autobuild_*.py`,
  `tests/seam/test_autobuild_coach.py` must continue to pass (AC-7).

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/unit/orchestrator/test_autobuild_stall_detector_plateau.py -x -v
PYTHONPATH=. python -m pytest tests/unit/test_autobuild_orchestrator.py tests/orchestrator/ tests/seam/test_autobuild_coach.py -x
ruff check guardkit/orchestrator/autobuild.py tests/unit/orchestrator/test_autobuild_stall_detector_plateau.py
```
