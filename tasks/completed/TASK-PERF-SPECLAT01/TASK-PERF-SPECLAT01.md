---
id: TASK-PERF-SPECLAT01
title: code-reviewer specialist (qwen3-coder-30b) 35-min SDKTimeout exhausts the task budget → timeout_budget_exhausted before convergence
status: completed
task_type: fix
created: 2026-06-14T11:10:00Z
updated: 2026-06-14T12:35:00Z
completed: 2026-06-14T12:35:00Z
completed_location: tasks/completed/TASK-PERF-SPECLAT01/
previous_state: in_review
state_transition_reason: "Quality gates passed: all new + touched tests green, no regressions introduced"
priority: high
complexity: 6
related: [TASK-FIX-SPECINVOKE01, TASK-FIX-COACHREASON01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, specialists, latency, sdk-timeout, timeout-budget, gb10, model-selection]
---

# Task: specialist latency exhausts the autobuild task budget

## Why this task exists

FEAT-9DDE **run 6** (2026-06-14; Player=qwen3-coder-30b, Coach=gemma4-coach +
`DISABLE_THINKING=1`) was the live-validation run after the checkpoint
false-red fix (TASK-FIX-CKPTTESTRED01 / TASK-AB-CKPTGATE01). The checkpoint
fix **worked** — all 3 turns recorded `tests_passed=True`, no
`unrecoverable_stall`. But the run ended `timeout_budget_exhausted` at turn 3
because the **specialists ran far longer than the budget assumes**.

This is now the **dominant blocker** to any autobuild feature run reaching
Wave 2: a task cannot converge if a single turn's specialist phase consumes
most of the per-task time budget.

## Symptom

- `Status: TIMEOUT_BUDGET_EXHAUSTED` after N turns, where the per-task
  `--task-timeout` was not hit by *productive* turns but by specialist
  invocations running to their SDK timeout.
- Log: `run_specialist(code-reviewer) failed for TASK-XXX: SDKTimeoutError:
  Agent invocation exceeded <~2138>s timeout`, then
  `Injected orchestrator specialist records ... (merged=2, validation=violation)`.
- Budget refusal: `Timeout budget exhausted for TASK-XXX at turn N+1:
  remaining=<397>s < min=600s`.

## Evidence (run 6)

- `task_timeout=4800s` (80 min). Run duration 73m 22s; turn 4 refused at
  `remaining=397.4s < min=600s`.
- Per-turn wall clock (UTC, `.guardkit/autobuild/FEAT-9DDE-run6-stdout.log`):
  - Turn 1 Player 08:46→08:50 (3.5m); Coach 08:56→08:57 (32s).
  - Turn 2 Player 08:57→09:04 (6.7m); **specialist phase 09:04→09:48 (~44m)**;
    Coach 09:48→09:49 (90s).
  - Turn 3 Player 09:49→09:58 (8.4m); Coach 09:58→10:00 (107s).
- **The turn-2 `code-reviewer` specialist ran 2138s (35.6 min) then hit
  `SDKTimeoutError`** (log L431). The turn-2 `test-orchestrator` specialist ran
  ~510s (~8.5 min). Together ≈44 min — more than half the 80-min budget in one
  turn.
- Specialists run on `--model` (the Player model), i.e. `qwen3-coder-30b`
  (`guardkit autobuild feature --help`: "specialist invocations stay on
  --model"). The code-reviewer is an *agentic* specialist (Read/Grep/Glob),
  so it makes many tool round-trips; on the GB10-served 30B model each call is
  slow, and it never self-terminates — it runs until the SDK timeout kills it.
- SPECINVOKE01 (TASK-FIX-SPECINVOKE01) is working: this is a **real** timeout
  with real model activity, not the old false 150s hang. The problem is raw
  latency, not a false hang.

## Hypotheses to investigate

1. **Model throughput**: qwen3-coder-30b on GB10 is too slow for a
   long agentic code-reviewer pass. Consider a faster specialist model
   (separate `--specialist-model` override?) or a smaller/faster review model.
   Consult agent memory `nvidia-gb10-dgx-spark-forum` before model choice.
2. **No self-bounding**: the specialist runs to the SDK ceiling rather than
   producing a bounded review. Is there a reasoning/verbosity curtailment
   (cf. COACHREASON01 `DISABLE_THINKING`) applicable to agentic specialists,
   or a max-tool-calls / max-turns cap?
3. **Budget accounting**: a single specialist consuming 35 min against a
   4800s task budget makes convergence arithmetically impossible for
   multi-turn tasks. Should the specialist SDK timeout be a fraction of the
   *remaining* task budget, and/or should a specialist timeout degrade
   gracefully (it already injects `validation=violation`) without burning the
   whole budget?
4. **Per-turn re-run**: the code-reviewer ran on turns 1, 2, and (separately)
   3. Should specialists be skipped/cached on turns where the diff is small?

## Acceptance Criteria

- [x] A feature autobuild run with the run-6 recipe converges TASK-TSJ-001
      (Wave 1) within the per-task budget, OR the specialist phase is bounded
      so it cannot consume more than a configurable fraction of the remaining
      task budget. — **Bounded-phase branch delivered**: `SPECIALIST_BUDGET_FRACTION`
      (default 0.5, env `GUARDKIT_SPECIALIST_BUDGET_FRACTION`) caps the combined
      Phase 4+5 wall to a fraction of `post_player_remaining`, threaded through
      `_cap_specialist_timeout(phase_budget_remaining=...)`. Live convergence is
      the recommended follow-up validation (re-run recipe in the run-6 handoff).
- [x] The `code-reviewer` (and `test-orchestrator`) specialist either
      completes well under its allotted time, or is given a faster model /
      a bounded turn cap, so multi-turn convergence is arithmetically possible.
      — **code-reviewer now has a 600s hard ceiling**
      (`_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS`, env
      `GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP`), symmetric with the existing
      test-orchestrator cap. Worst-case specialist phase drops from ~44 min
      (run 6) to ≤20 min, making turn 4 reachable within an 80-min budget.
- [x] A specialist SDK timeout is surfaced clearly (it already injects
      `validation=violation`) and does NOT silently consume the whole task
      budget such that the *task* fails with `timeout_budget_exhausted`.
      — surfacing unchanged; the 600s cap + budget fraction prevent a single
      specialist from foreclosing the next turn.
- [x] No regression to SPECINVOKE01 (specialists still measured by real model
      activity; a `validation=violation` remains a real finding). — the
      no-activity watchdog (`GUARDKIT_SPECIALIST_WATCHDOG_SECONDS`, 150s) is now
      also wired into the code-reviewer; activity measurement is unchanged. The
      new bounds are additive duration/fraction ceilings only.

## Implementation summary (2026-06-14)

Scope chosen: **bound the phase only** (no `--specialist-model`; recommended as a
separate follow-up — cross-repo harness model-threading, not offline-verifiable).

Root cause: the Phase 5 `code-reviewer` had **neither** the 600s hard duration
cap **nor** the no-activity watchdog the Phase 4 `test-orchestrator` has, so on
the slow GB10-served model it ran to its scaled ~2160s ceiling (run-6: 2138s).
A latent accounting bug compounded it: the Phase 4/5 timeout caps used the
**stale start-of-turn** `remaining_budget` instead of `post_player_remaining`.

Changes:
- `specialist_invocations.py`: `_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS` (600,
  env-tunable) applied in `invoke_code_reviewer`; no-activity watchdog wired in
  (shared `_SPECIALIST_NO_ACTIVITY_WATCHDOG_SECONDS`).
- `autobuild.py`: `SPECIALIST_BUDGET_FRACTION` (0.5, clamped (0,1]);
  `_cap_specialist_timeout(phase_budget_remaining=...)`; `_execute_turn` bases
  both specialist caps on `post_player_remaining` and shares a per-turn
  specialist-phase budget across Phase 4+5 (Phase 5 subtracts Phase 4 elapsed).

Tests: +8 new (3 code-reviewer cap/watchdog, 3 constant, 5 phase-budget cap),
3 pre-existing `TestSpecialistBudgetRefresh` updated to the corrected
`post_player_remaining` basis. `test_specialist_invocations.py` +
`test_autobuild_timeout_budget.py`: **75 passed, 1 skipped**;
`test_autobuild_phase_4_5_orchestration.py`: 6 passed. No regressions
introduced (4 BDD `coach_validator` failures are pre-existing/environmental).

Plan: `docs/state/TASK-PERF-SPECLAT01/implementation_plan.md`.

## Evidence / references
- Run log: `.guardkit/autobuild/FEAT-9DDE-run6-stdout.log` (L431 SDKTimeout,
  L580 budget exhausted, L583-615 summary).
- Preserved artifacts: `docs/retro/run6-evidence/`.
- Specialist activity watchdog: TASK-FIX-SPECINVOKE01 (commit `d916cf43`).
- Coach reasoning curtailment precedent: TASK-FIX-COACHREASON01.
- GB10 model-serving reference: agent memory `nvidia-gb10-dgx-spark-forum`.
