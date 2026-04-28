---
id: TASK-ABSR-FRSH
title: Refresh remaining_budget post-Player before pre-specialist guard
status: backlog
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: medium
tags: [autobuild, budget-accounting, FEAT-ABSR-9C6E, R3, high]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 3
complexity: 3
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-ABSR-FRSH — Refresh `remaining_budget` post-Player before specialist guard

## Description

Recompute `remaining_budget` from `loop_start_time` immediately before the pre-specialist budget guard at `autobuild.py:2724-2742`. Currently the value passed in via `_execute_turn` parameter is the start-of-turn value computed at `autobuild.py:2125-2128`; it is never refreshed after the Player phase consumes wall. The Coach phase at `autobuild.py:2867` similarly receives the stale value (`coach_remaining_budget = remaining_budget`).

**Failure mode this prevents** (per [TASK-REV-9D13 v2 §1.5](../../../.claude/reviews/TASK-REV-9D13-report.md)): when the Player phase legitimately consumes ~1800 s of wall (no ceiling hit, real complex implementation), the start-of-turn budget guard still sees the original value (e.g., 2400 s) and admits Phase 4/5 specialists. Specialists then run on a wall that's actually ~600 s remaining. With R2 in place this is mostly survivable; with both R2 and R3 the guard fires correctly and the orchestrator writes `specialist_skipped: budget exhausted` blocks instead of attempting and failing.

**Targets**: Bug C in TASK-REV-9D13 v2 §0. **HIGH priority but secondary to R1+R2.**

## Acceptance Criteria

- [ ] AC-001: `loop_start_time` is accessible at the point of the budget guard (line 2724). Either thread it through `_execute_turn` as a parameter, or store it on `self._loop_start_time` at line 2087 (`loop_start = _time.monotonic()`). Choose the lower-impact approach (likely storing on `self`).
- [ ] AC-002: At `autobuild.py:2724`, before the `budget_ok` computation, recompute the post-Player remaining budget: `if remaining_budget is None or self._loop_start_time is None: post_player_remaining = remaining_budget; else: post_player_remaining = self._task_timeout - (time.monotonic() - self._loop_start_time)`. Then `budget_ok = (post_player_remaining is None or post_player_remaining >= MIN_TURN_BUDGET_SECONDS)`.
- [ ] AC-003: The `specialist_skipped: budget exhausted` block written at line 2747-2755 logs `post_player_remaining` (not the stale `remaining_budget`) in the error message.
- [ ] AC-004: Optionally also pass `post_player_remaining` to `_cap_specialist_timeout` (from TASK-ABSR-WALL) when both fixes are in place — coordinate with that task during integration.
- [ ] AC-005: New test in `tests/unit/test_autobuild_timeout_budget.py` named `test_post_player_budget_refresh_triggers_skip`: simulate a Player phase consuming `time.monotonic` past `MIN_TURN_BUDGET_SECONDS` of the start-of-turn budget, verify the post-Player guard correctly emits `specialist_skipped: budget exhausted` with the recomputed remaining value (not the stale start-of-turn value).
- [ ] AC-006: Existing 18 tests in `tests/unit/test_autobuild_timeout_budget.py` continue to pass; the constant assertions (`MIN_TURN_BUDGET_SECONDS=600`, `COACH_GRACE_PERIOD_SECONDS=120`) are unaffected.
- [ ] AC-007: `pytest tests/unit/test_autobuild_timeout_budget.py tests/integration/test_autobuild_phase_4_5_orchestration.py -v` passes.
- [ ] AC-008: `mypy guardkit/orchestrator/autobuild.py` strict-clean.
- [ ] AC-009: Lint/format pass.

## Implementation Notes

Exact code in [TASK-REV-9D13 v2 §4 R3](../../../.claude/reviews/TASK-REV-9D13-report.md#r3--refresh-remaining_budget-before-pre-specialist-guard-high).

The 18 mocked-monotonic tests in `test_autobuild_timeout_budget.py` already use `unittest.mock.patch("time.monotonic")` — that pattern can be reused for the new test.

**Regression risk**: The new computation is monotonic-non-increasing in `remaining_budget` — the guard fires *more* aggressively, never less. Cannot regress completed tasks. The only behaviour change is in cases where the start-of-turn value was misleadingly above `MIN_TURN_BUDGET_SECONDS`.

**Coordination**: Independent of R1 and R2. Can be parallel-developed in its own Conductor workspace.
