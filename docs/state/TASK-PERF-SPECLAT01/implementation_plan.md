# Implementation Plan — TASK-PERF-SPECLAT01

**Specialist latency exhausts the autobuild task budget.** Bound the specialist
phase (chosen scope: *bound the phase only* — no `--specialist-model`).

## Root cause (grounded in code)

Guard **asymmetry** between the two orchestrator specialists:

| Guard | Phase 4 `test-orchestrator` | Phase 5 `code-reviewer` |
|---|---|---|
| Hard duration cap | `min(sdk_timeout, 600)` (`specialist_invocations.py:924`) | **none** — full scaled value passed through (`:1048`) |
| No-activity watchdog (150s) | yes (`:947`) | **none** (`:1044-1054`) |

For complexity 6 / task-work mode, `AgentInvoker._calculate_sdk_timeout` =
`base × 1.5 (mode) × 1.6 (complexity)` ≈ **2160s**. The code-reviewer's only
bound was the wall clamp in `_cap_specialist_timeout`:
`min(scaled, remaining − COACH_GRACE)`. With `COACH_GRACE_PERIOD_SECONDS=1500`
and a (stale, start-of-turn) `phase5_remaining` ≈ 3630s →
`min(2160, 3630−1500=2130)` ≈ **2130s** = the observed 2138s SDKTimeout.

Two compounding defects:
1. **No 600s hard ceiling on the code-reviewer** (the dominant cost).
2. **Stale budget**: Phase 4/5 caps use the **start-of-turn** `remaining_budget`
   (`autobuild.py:3204`, `:3222`) instead of the freshly-computed
   `post_player_remaining`, over-allocating by the Player's turn wall.

## Changes (all in guardkit; fully offline-testable)

### A. `guardkit/orchestrator/specialist_invocations.py` (AC2, AC4)
1. New constant `_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS` (default 600,
   env `GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP`).
2. In `invoke_code_reviewer`, cap `sdk_timeout` at that ceiling (mirror the
   test-orchestrator block) with a log line.
3. Wire the no-activity watchdog into the code-reviewer's `run_specialist`
   call (reuse `_SPECIALIST_NO_ACTIVITY_WATCHDOG_SECONDS`, env
   `GUARDKIT_SPECIALIST_WATCHDOG_SECONDS`, 150s).

### B. `guardkit/orchestrator/autobuild.py` (AC1, AC3)
4. New constant `SPECIALIST_BUDGET_FRACTION` (default 0.5, env
   `GUARDKIT_SPECIALIST_BUDGET_FRACTION`, clamped to (0, 1]).
5. `_cap_specialist_timeout` gains an optional `phase_budget_remaining` kwarg
   applying an extra `min(...)` (floored 60) **after** the grace-reserved cap —
   keeps grace reserved from the *full* remaining, fraction bounds the *phase*.
6. In `_execute_turn`, base both specialist caps on `post_player_remaining`
   (fixes the stale-budget bug), compute `phase_budget =
   post_player_remaining × fraction` once, and pass the running phase budget to
   each cap (Phase 5 subtracts Phase 4 elapsed). Bounds Phase4+Phase5 wall to
   `fraction × post_player_remaining`.

### Tests
- `tests/unit/orchestrator/test_specialist_invocations.py`: code-reviewer caps
  above ceiling / passes smaller through / watchdog wired.
- `tests/unit/test_autobuild_timeout_budget.py`: `SPECIALIST_BUDGET_FRACTION`
  constant + env override; `_cap_specialist_timeout(phase_budget_remaining=...)`;
  turn-level regression that the phase total is bounded and Phase 4 uses
  `post_player_remaining` (stale-budget regression).

## AC mapping
- **AC1** — phase bounded to a configurable fraction of remaining budget → B4-B6.
- **AC2** — code-reviewer/test-orchestrator complete under allotted time
  (bounded cap) → A1-A2 (+ existing test-orch cap).
- **AC3** — specialist timeout surfaced (`validation=violation`, unchanged) and
  cannot consume the whole budget → A1-A2 + B4-B6.
- **AC4** — no SPECINVOKE01 regression: additive duration/fraction bounds only;
  activity measurement (watchdog predicate) unchanged, now also protects Phase 5.

## Out of scope (recommended follow-up)
`--specialist-model` override (cross-repo harness model-threading; depends on a
faster model served on GB10; not offline-verifiable). The ACs are satisfied
without it.
