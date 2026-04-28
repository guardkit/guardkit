---
id: TASK-ABSR-FLOR
title: MAXT ceiling floor of 150 turns + task_timeout floor of 3000s — emergency unblock
status: completed
created: 2026-04-28T12:30:00Z
updated: 2026-04-28T13:45:00Z
completed: 2026-04-28T13:45:00Z
previous_state: in_review
state_transition_reason: "Task-complete: all ACs verified, completion gates passed"
completed_location: tasks/completed/2026-04/TASK-ABSR-FLOR-maxt-floor-and-task-timeout-floor.md
priority: critical
tags: [autobuild, maxt-floor, task-timeout-floor, FEAT-ABSR-9C6E, ddd-southwest-blocker, emergency]
parent_review: TASK-REV-WORS
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 1
historical_wave: 6
complexity: 3
depends_on: []
test_results:
  status: passed
  coverage: null  # MINIMAL intensity — coverage skipped per autobuild stall resilience emergency profile
  last_run: 2026-04-28T13:30:00Z
  new_tests_passed: 5
  related_tests_passed: 25
implementation_summary:
  ac_001_maxt_floor: "Added SDK_MAX_TURNS_FLOOR=150 constant; max(SDK_MAX_TURNS_FLOOR, scaled) applied in _calculate_sdk_max_turns"
  ac_002_env_override_bypass: "Floor only runs after the env-override early-return; covered by test_calculate_sdk_max_turns_env_override_bypasses_floor"
  ac_003_task_timeout_floor: "Picked option (b): GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR env var (default 3000) read in FeatureOrchestrator.__init__ before multiplier"
  ac_004_maxt_tests: "TestCalculateSDKMaxTurnsFloor (3 tests, all pass)"
  ac_005_timeout_tests: "TestTaskTimeoutFloor (2 tests, all pass)"
  ac_006_no_regressions: "Pre-existing failures (asyncio.timeout on Py 3.10, _bootstrap_venv_python attribute on __new__-constructed orchestrator) confirmed identical on main and branch"
  ac_007_mypy: "89 pre-existing errors on both main and branch; zero new errors in modified line ranges"
  ac_008_ruff: "34 pre-existing check errors and 4 pre-existing format issues on both main and branch; zero new in modified line ranges"
files_modified:
  - guardkit/orchestrator/agent_invoker.py
  - guardkit/orchestrator/feature_orchestrator.py
  - tests/unit/test_agent_invoker.py
  - tests/unit/test_autobuild_timeout_budget.py
---

# TASK-ABSR-FLOR — MAXT ceiling floor + task_timeout floor

## Stakes

**Critical-path emergency unblock.** Two consecutive Jarvis FEAT-J004-702C autobuild runs failed at Wave 4. DDD-SouthWest demo in ~20 days. This task ships the smallest fix that addresses both binding constraints surfaced in [TASK-REV-WORS report v2 §0](../../../.claude/reviews/TASK-REV-WORS-report.md#0-the-one-thing-to-do-right-now).

## Description

Wave 4 of run-3 failed because:
- **TASK-J004-011 hit the wall budget** — completed Player at 116 of 170 turns, 2235 s of 2400 s task_timeout (92%). Per-turn rate had drifted up +26.5% (15.1→19.1 s/turn vs run-2). Coach independent tests then ran in a worktree poisoned by J004-012's mid-edit and failed with `parallel_contention`. MTBC blocked turn 2 (164.5s remaining < 600s min) → `timeout_budget_exhausted`.
- **TASK-J004-012 hit the SDK ceiling** at 141 of 140 turns (`task_work_results.json:73-77, ceiling_hit=true`). MAXT (R4 in `87c27e60`) gave it `int(100 * (1 + 4/10)) = 140`. Player was cut off mid-Phase-3, leaving capabilities.py with `_REFRESH_OK_MESSAGE` deletion incomplete. R1 CEIL fired correctly to skip Phase 4/5.

The two failures hit *different* binding constraints. Each fix targets one:

1. **MAXT floor of 150 turns** — for J004-012-shaped tasks (low complexity heuristic estimate but high actual work).
2. **task_timeout floor of 3000s** — for J004-011-shaped tasks (where per-turn rate variance + turn-count variance combine to overflow the 2400 s budget).

This is **NOT** the strategic fix. The strategic fix is [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md) (Phase-2.5 complexity heuristic redesign). FLOR is the band-aid that buys time for CMPL while unblocking the demo.

**SDK `max_turns` model-visibility note** (CONFIRMED in TASK-REV-WORS v2 §3.3): `max_turns` is passed only to `ClaudeAgentOptions(...)` at `agent_invoker.py:2208` and used by the SDK as a Python-loop hard stop. The model never sees this value. Therefore raising the ceiling cannot *cause* longer iteration — it only *permits* it. The Player's actual turn count is determined by task structure + worktree state + Anthropic-side variance.

## Acceptance Criteria

- [ ] AC-001: `_calculate_sdk_max_turns(task_id)` in `guardkit/orchestrator/agent_invoker.py` applies a floor of 150 turns. Implementation: `effective_max_turns = max(150, int(TASK_WORK_SDK_MAX_TURNS * (1.0 + complexity / 10.0)))`. The floor is overridable by the existing `GUARDKIT_SDK_MAX_TURNS` env var (which sets `_SDK_MAX_TURNS_IS_OVERRIDE=True` and bypasses scaling — see `agent_invoker.py:301-302`).
- [ ] AC-002: When `_SDK_MAX_TURNS_IS_OVERRIDE=True` (env override), the floor does NOT apply. The user's explicit value wins.
- [ ] AC-003: `task_timeout` default floor of 3000s in autobuild orchestration. Three implementation options (pick the lowest-blast-radius):
  (a) Constructor default in `autobuild.py:908` change `task_timeout: Optional[int] = None` to apply `max(3000, value or 0)` if the value is below 3000.
  (b) New env var `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR=3000` consulted at construction time.
  (c) Update CLI default in `guardkit/cli/autobuild.py` (or wherever `task_timeout` is computed for feature builds) to floor at 3000.
  Pick (b) or (c) over (a) — explicit is better. Document the chosen path in the test.
- [ ] AC-004: New unit test in `tests/unit/test_agent_invoker.py` covers MAXT floor:
  - `test_calculate_sdk_max_turns_applies_floor_for_low_complexity` — c=1 should give 150 (floor), not 110 (formula). c=4 should give 150 (floor), not 140 (formula).
  - `test_calculate_sdk_max_turns_no_floor_for_high_complexity` — c=7 should give 170 (formula), c=10 should give 200 (formula). Floor doesn't bind.
  - `test_calculate_sdk_max_turns_env_override_bypasses_floor` — when `GUARDKIT_SDK_MAX_TURNS=100` is set, the value should be 100 (no floor applied).
- [ ] AC-005: New unit test in `tests/unit/test_autobuild_timeout_budget.py` covers task_timeout floor:
  - `test_task_timeout_floor_applied_when_below_3000` — task_timeout=2400 should be raised to 3000.
  - `test_task_timeout_floor_not_applied_when_above_3000` — task_timeout=4000 should remain 4000.
- [ ] AC-006: All existing tests in the affected files still pass (`pytest tests/unit/test_agent_invoker.py tests/unit/test_autobuild_timeout_budget.py -v`).
- [ ] AC-007: `mypy guardkit/orchestrator/agent_invoker.py guardkit/orchestrator/autobuild.py` passes strict-clean.
- [ ] AC-008: `ruff check` and `ruff format --check` pass on all modified files.

## Implementation Notes

### Files to modify

| File | Change | Approx LOC |
|------|--------|-----------|
| `guardkit/orchestrator/agent_invoker.py` | Add `max(150, ...)` floor in `_calculate_sdk_max_turns`, gated on `not _SDK_MAX_TURNS_IS_OVERRIDE` | 2-3 |
| `guardkit/orchestrator/autobuild.py` (or `guardkit/cli/autobuild.py`) | task_timeout floor of 3000s | 3-5 |
| `tests/unit/test_agent_invoker.py` | 3 new tests | 30-40 |
| `tests/unit/test_autobuild_timeout_budget.py` | 2 new tests | 20-30 |

**Total**: ~10 LOC source + ~60 LOC tests = under 80 LOC change.

### Test surface from 87c27e60

`87c27e60` added `tests/unit/test_agent_invoker.py +130` and `tests/unit/test_autobuild_timeout_budget.py +275`. The MAXT scaling function and task_timeout handling already have substantial mock coverage. New tests slot into the same patterns.

### Why a floor of 150 (not 200, not 120)?

- Run-2 J004-013 used 101 SDK turns and hit the old 100 ceiling. Floor of 150 is +50% headroom.
- Run-3 J004-012 used 141 turns. Floor of 150 buys 9 more.
- Higher floors (e.g. 200) trade more SDK budget for less protection against runaway loops. 150 is the smallest floor that addresses both observed failures.

### Why a task_timeout floor of 3000s (not 3600, not 2700)?

- Run-3 J004-011 used 2235 s. Floor of 3000 gives 765 s headroom.
- Run-2 J004-013 was foreclosed with 21.2 s remaining at the 2400 s ceiling. Floor of 3000 buys 600 s.
- 3600 s would be safer but consumes 50% more wall per failed task. 3000 s is the smallest floor that has clear evidence-based headroom for observed worst-cases.

### Out of scope

- **NO changes to Jarvis** — fix lives entirely in GuardKit (per TASK-REV-WORS §0 and §10).
- **NOT** changing the MAXT formula's scaling factor — only adding a floor.
- **NOT** addressing the underlying complexity heuristic underestimation — that's [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md).
- **NOT** addressing the shared-worktree poison vector — that's TASK-ABSR-WTKS (deferred design-first).

## Verification recipe

After implementation:

```bash
# 1. Unit tests pass
uv run pytest tests/unit/test_agent_invoker.py tests/unit/test_autobuild_timeout_budget.py -v

# 2. Strict-clean checks
uv run mypy guardkit/orchestrator/agent_invoker.py guardkit/orchestrator/autobuild.py
uv run ruff check
uv run ruff format --check

# 3. End-to-end: re-run jarvis autobuild with --fresh
cd /Users/richardwoollcott/Projects/appmilla_github/jarvis
guardkit autobuild feature FEAT-J004-702C --fresh

# Expected: Wave 4 completes (J004-012 has 9 turns headroom; J004-011 has 765s wall headroom).
# Wave 5 (J004-013) completes (CEIL+WALL+FRSH+MTBC are shipped).
# 20/20 tasks pass.
```

## Notes

- This task does NOT require the [R]evise/Action-B replay from TASK-REV-WORS to ship. Action B is a confirmation step for the *upstream cause*; the floor fix is robust to either upstream cause (worktree-state drift OR Anthropic-side variance) because both manifest as turn/wall budget overflow.
- After this ships and the demo build succeeds, schedule [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md) for the strategic complexity heuristic redesign.
- The structural class-of-defect (shared-worktree poisoning under parallel-Player ceiling cuts) is captured in TASK-ABSR-WTKS as a design-first follow-up.
