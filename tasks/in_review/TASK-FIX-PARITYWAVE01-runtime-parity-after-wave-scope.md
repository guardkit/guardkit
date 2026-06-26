---
id: TASK-FIX-PARITYWAVE01
title: Gate per-task runtime parity on the smoke gate's after_wave scope
task_type: feature
parent_task: TASK-AB-COACHRUNPARITY01
feature_id: FEAT-HARV
status: in_review
created: 2026-06-26T00:00:00+00:00
updated: 2026-06-26T00:00:00+00:00
previous_state: backlog
state_transition_reason: "Implemented + unit-tested 2026-06-26 (helper _per_task_smoke_command, 6 regression tests green)"
priority: high
tags:
  - autobuild
  - feature-orchestrator
  - runtime-parity
  - smoke-gate
  - cross-wave
complexity: 3
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Gate per-task runtime parity on the smoke gate's after_wave scope

## Description

The per-task runtime-parity check (TASK-AB-COACHRUNPARITY01 **arm b**) is a
*preview* of the post-wave smoke gate: before the per-task Coach approves a
single-task wave, it runs the feature `smoke_gates.command` (the deliverable's
real runtime entry point) and overrides approve→feedback on a ran-and-failed
result. But `FeatureOrchestrator._execute_wave` threads that command into the
per-task Coach for **every** single-task wave with **no check on the smoke
gate's `after_wave` scope**.

When a feature's `smoke_gates.after_wave` points at a *later* wave than the
task being checked, the per-task parity runs a CLI command whose subcommand
does not exist yet (it is a later wave's deliverable), producing an exit-2
`No such command` that the deliverable cannot fix. The task is rejected every
turn until `max_turns_exceeded`.

### Concrete incident (FEAT-HARV, validation run 2026-06-26)

`FEAT-HARV.yaml` declares:

```yaml
smoke_gates:
  after_wave: 3
  command: python -m guardkit.cli.main memory harvest --dry-run
  expected_exit: 0
```

- Wave 3 builds the `memory harvest` CLI (TASK-HARV-005).
- Wave 2 is the single-task **harvest walker** (TASK-HARV-003), a *library*
  module with no CLI.

The per-task runtime parity ran `python -m guardkit.cli.main memory harvest
--dry-run` against the wave-2 walker. Evidence (`coach_evidence_turn_4.json`):

```json
"runtime_parity": {
  "ran": true, "passed": false,
  "command": "python -m guardkit.cli.main memory harvest --dry-run",
  "exit_code": 2, "expected_exit": 0,
  "stderr_tail": "Error: No such command 'memory'."
}
"quality_gates": { "tests_passed": true, "all_gates_passed": true }
```

The walker's own quality gates passed every turn (the deterministic subprocess
pytest passed 8601/8601), yet the runtime parity blocked it to
`max_turns_exceeded`. Waves 1 (parallel, `wave_size=2`) never hit this because
arm-b parity is guarded to `wave_size == 1`.

## Acceptance Criteria

- [ ] `_execute_wave` only threads `smoke_command` / `smoke_expected_exit` to the
      per-task Coach for waves where the post-wave smoke gate fires
      (`should_fire_for_wave(feature.smoke_gates, wave_number)`); otherwise it
      passes `None` / `0` (an absent signal — the per-task parity no-ops per
      arm b's `ran=False` safety).
- [ ] All `after_wave` forms honoured: int (fires only on that wave), list
      (fires on each listed wave), `"all"` (fires every wave), and no-smoke-gate
      (always None).
- [ ] FEAT-HARV reproducer: with `after_wave: 3`, wave 2 yields
      `smoke_command=None` so the wave-3 `memory harvest` CLI is never run
      against the wave-2 walker.
- [ ] No regression to the post-wave smoke gate itself (`_run_post_wave_smoke_gate`,
      `should_fire_for_wave` at the wave-loop site) — only the per-task preview
      is gated.
- [ ] No regression to single-wave / `after_wave: all` features where parity
      *should* run.
- [ ] Unit tests cover all the above (extract the gating into a testable helper).

## Technical Context

- File: `guardkit/orchestrator/feature_orchestrator.py`
- Method: `_execute_wave` — the `smoke_command` / `smoke_expected_exit`
  derivation (~line 3343 on `main`, the block commented
  `TASK-AB-COACHRUNPARITY01 (arm b)`). `wave_number` is already a parameter of
  this method.
- `should_fire_for_wave(config, wave_number)` already exists in
  `guardkit/orchestrator/smoke_gates.py` and is used at the wave-loop site for
  the post-wave gate — reuse it for the per-task derivation.
- The per-task Coach consumes `smoke_command` via
  `coach_validator.py` (`self.smoke_command`, used only when `wave_size == 1`).

## Implemented fix sketch (validated by unit tests, then reverted pending this task)

This was implemented inline mid-session (commit `5c95dd85`) and reverted
(`0cbbe6fa`) to go through the proper task process. The fix:

1. Extract a testable static helper on `FeatureOrchestrator`:

```python
@staticmethod
def _per_task_smoke_command(
    feature: Feature, wave_number: int
) -> Tuple[Optional[str], int]:
    """Per-task runtime-parity command for wave_number, gated on the smoke
    gate's after_wave scope. Returns (None, 0) — an absent signal / no-op per
    arm b's ran=False safety — when no smoke gate is configured OR the gate does
    not fire for this wave."""
    if feature.smoke_gates is None or not should_fire_for_wave(
        feature.smoke_gates, wave_number
    ):
        return None, 0
    return feature.smoke_gates.command, feature.smoke_gates.expected_exit
```

2. Replace the inline `smoke_command = (... feature.smoke_gates.command ...)`
   derivation in `_execute_wave` with
   `smoke_command, smoke_expected_exit = self._per_task_smoke_command(feature, wave_number)`.
3. Add `Tuple` to the `typing` import.

Regression test (was `tests/unit/orchestrator/test_per_task_smoke_wave_gate.py`,
6 tests): FEAT-HARV reproducer (after_wave=3 → wave 2 None); int/list/all/none
forms; expected_exit threading. Confirmed green (32 passed including the existing
smoke/parity suites) before revert.

## Regression Risks

1. Must NOT change the post-wave gate firing (it already uses
   `should_fire_for_wave`); only the per-task preview derivation changes.
2. `after_wave` is an int by default but can be a list or `"all"` — the helper
   must delegate to `should_fire_for_wave` for ALL forms, not reimplement the
   logic.
3. Smoke-gate re-run path (`_run_post_wave_smoke_gate` re-enters the wave with
   `seed_feedback`) re-derives via `_execute_wave` — confirm it still passes the
   command on the firing wave.

## Rule / design references

- `.claude/rules/smoke-gate-is-feedback-not-terminator.md` (arm b)
- `.claude/rules/per-task-green-is-not-feature-green.md` (per-task aperture vs
  the assembled feature)
- Source: TASK-AB-COACHRUNPARITY01 (commit `a11708d0`)

## Notes

This is a *genuinely distinct* defect from the SDK independent-test reliability
work (TASK-FIX-DF44 / TASK-REV-COSE). It is the only net-new finding from the
FEAT-HARV session that is not already covered by an existing task. End-to-end
validation against FEAT-HARV is still pending (the validating run died in wave 1
on an unrelated reverted change before reaching wave 2).
