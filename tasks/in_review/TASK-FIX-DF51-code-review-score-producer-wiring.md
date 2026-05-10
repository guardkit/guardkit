---
id: TASK-FIX-DF51
title: Wire code-reviewer score into task_work_results.code_review.score (producer-side)
status: in_review
created: 2026-05-10T19:30:00Z
updated: 2026-05-10T15:03:29Z
previous_state: in_progress
state_transition_reason: "Producer fold landed pre-freeze; tests pass (15/15 new + 299/299 sibling); awaiting human review"
priority: high
tags: [autobuild, coach, quality-gates, runner-without-producer, gate-freeze-affected]
parent_task: TASK-OBS-ABST
complexity: 4
estimated_effort_hours: 2
---

# Task: Wire code-reviewer score into `task_work_results.code_review.score`

> **Why this exists**: Discovered while running TASK-OBS-ABST through autobuild
> on 2026-05-10. Coach kept rejecting all 5 turns with `must_fix/architectural`
> ("Architectural review score below threshold") despite the code-reviewer
> agent successfully completing in turn 5 (403s of work). Root cause: the gate
> reads a field that the producer doesn't populate.

## Symptom

In autobuild runs of *any* task with profile-required architectural review,
Coach hits an unsatisfiable gate:

- `coach_validator.py:1709` reads `task_work_results["code_review"]["score"]`
- The Player report writer in `agent_invoker.py` never writes a `code_review`
  key into `task_work_results.json` (verified for TASK-OBS-ABST: top-level
  keys were `[task_id, timestamp, completed, phases, quality_gates,
  files_modified, files_created, tests_written, summary, sdk_turns,
  agent_invocations_validation, plan_audit, ...]` — no `code_review`)
- Default fallback at `code_review.get("score", 0)` returns `0`
- `0 < 60` → `arch_review_passed = False` → gate fails forever
- Player makes more changes, Coach evaluates again, gate still fails →
  MAX_TURNS_EXCEEDED, regardless of actual implementation quality

This is the same shape as the canonical *runner-without-producer* anti-pattern
(see [`namespace-hygiene.md`](../../.claude/rules/namespace-hygiene.md) sibling
rule, Graphiti uuid `184731b0-...`): a downstream gate consumes a field that
no upstream producer writes, so the gate runs but is structurally
unsatisfiable.

## Reproducer

```bash
# Pick any task with autobuild.enabled=true and the default feature profile
# (which has arch_review_required=True). Run the build:
guardkit autobuild task <task-id> --max-turns 5

# Inspect the result:
WT=.guardkit/worktrees/<task-id>
python3 -c "
import json
d = json.load(open(f'$WT/.guardkit/autobuild/<task-id>/task_work_results.json'))
print('has code_review key:', 'code_review' in d)
"
# → has code_review key: False
```

A real-world reproducer is preserved at
`.guardkit/worktrees/TASK-OBS-ABST/.guardkit/autobuild/TASK-OBS-ABST/task_work_results.json`
(captured 2026-05-10T13:22). Inspect `agent_invocations` — phase 5
(`code-reviewer`) shows `status: "completed"` with `duration_seconds: 403.13`,
yet no score landed in the consumer key.

## Acceptance criteria

### AC-001 — Score round-trips into `code_review.score`
**WHEN** the orchestrator's code-reviewer specialist completes successfully
during phase 5, **THE SYSTEM SHALL** write
`task_work_results["code_review"]["score"]` (integer 0-100) and
`task_work_results["code_review"]["status"]` (string) into the on-disk
`task_work_results.json` *before* the file is read by the Coach validator
in the same turn.

### AC-002 — Coach reads the right field
**THE SYSTEM SHALL** keep the consumer site in `coach_validator.py:1709`
reading `task_work_results["code_review"]["score"]`. The fix is
producer-side — do not silently relocate the consumer.

### AC-003 — Stack-specific subscores preserved
**WHEN** the code-reviewer agent emits `solid: N`, `dry: N`, `yagni: N`
subscores in its prompt-marker output, **THE SYSTEM SHALL** preserve those
under `task_work_results["code_review"]["subscores"]` for diagnostic use.
This is best-effort; the gate only requires `score`.

### AC-004 — Regression test against the TASK-OBS-ABST capture
**THE SYSTEM SHALL** ship a regression test under
`tests/orchestrator/quality_gates/test_code_review_round_trip.py` that:
1. Loads a synthetic `task_work_results.json` fixture missing `code_review`,
2. Runs the producer (whichever module owns the fix),
3. Asserts the resulting dict has `code_review.score` populated,
4. Runs `CoachValidator.evaluate_quality_gates(...)` and asserts
   `arch_review_passed=True` for `score >= 60`.

### AC-005 — Validator-error fallback unchanged
**WHEN** the code-reviewer agent crashes or times out, **THE SYSTEM SHALL**
not write a `code_review` key (or write `code_review.score = null`), so
that the existing default-to-0 path still applies. The fix must not mask
genuine code-review failures.

## Implementation notes

- Likely producer is `AgentInvoker._write_task_work_results(...)` in
  `guardkit/orchestrator/agent_invoker.py` — the same function where the
  `agent_invocations_validation` and `plan_audit` blocks are folded in
  (TASK-FIX-RWOP1.3.1, TASK-FIX-RWOP1.3.2). This wiring follows the same
  pattern: a deterministic post-phase script writes the field the gate
  reads.
- The score itself is parsed from the code-reviewer agent's prose output
  by `TaskWorkStreamParser` (per the Phase 5 marker contract:
  `Architectural Score: N/100`, `SOLID: N, DRY: N, YAGNI: N`). Verify
  whether the parser already captures it and the fix is just a fold, or
  whether the parser also needs amending.
- Look at the `phases` dict in the existing on-disk
  `task_work_results.json`: it has `phase_3 -> status:None, score:None`.
  The phase-keyed structure may already be the right home, but the gate
  reads the flat `code_review` key. Decide whether to:
  - **Option A**: Mirror the score from `phases.phase_5.score` into
    `code_review.score` in the producer (defence-in-depth);
  - **Option B**: Update the consumer to read `phases.phase_5.score`
    instead — cleaner, but risks breaking other consumers (and is a
    consumer-side change, which is the wrong axis to fix this on).
- Recommendation: **Option A** (producer-side write to flat key the
  consumer already reads). Mirrors the FIX-RWOP1.3.1 / 1.3.2 fold
  pattern.

## ⚠️ Gate-stack freeze interaction

`agent_invoker.py` and `coach_validator.py` are both **frozen paths** for
2026-05-11 → 2026-05-17 (see
[`.claude/state/gate-freeze-2026-05-17.md`](../../.claude/state/gate-freeze-2026-05-17.md)).

This task's fix is producer-side wiring on `agent_invoker.py` — that's a
**new behavioural surface** in a frozen path (forbidden class 2: "new
function, new class, new method, or new public symbol"). Before merging:

- **Option 1 (recommended)**: Hold the fix until 2026-05-18 (post-freeze).
  Cost: TASK-OBS-ABST and any other arch-review-required autobuild tasks
  cannot Coach-approve during the freeze. Acceptable mitigation: run
  affected tasks with `--skip-arch-review` flag, or hold them.
- **Option 2**: Land the fix today (2026-05-10) before the freeze starts
  — there are still ~5h before midnight. Risk: rushed change to a
  load-bearing producer.
- **Option 3**: Land during the freeze via override entry per the freeze
  doc's "Exception protocol". This requires a one-line entry in
  `.claude/state/gate-freeze-2026-05-17.md` under "Granted overrides"
  *before* the commit lands. Rationale should cite this task ID and the
  fact that without the fix, no arch-review-required task can be
  evaluated by Coach.

Pick the option that matches risk tolerance. Default recommendation:
Option 1 (hold to 2026-05-18) — the freeze exists precisely to *not*
land changes to the gate stack mid-bake.

## Files likely modified

- `guardkit/orchestrator/agent_invoker.py` (producer-side fold) — frozen
- `guardkit/orchestrator/quality_gates/coach_validator.py` (only if
  validator-side adjustment chosen) — frozen
- `tests/orchestrator/quality_gates/test_code_review_round_trip.py` (new)
- Possibly `guardkit/orchestrator/agent_streams.py` or wherever
  `TaskWorkStreamParser` lives — out of scope of frozen list

## Related

- Discovered by: TASK-OBS-ABST autobuild run, 2026-05-10
  (`.guardkit/worktrees/TASK-OBS-ABST/.guardkit/autobuild/TASK-OBS-ABST/coach_turn_5.json`)
- Sibling fixes (same producer-side pattern):
  - TASK-FIX-RWOP1.3.1 (agent_invocations validator fold)
  - TASK-FIX-RWOP1.3.2 (plan_audit verdict fold)
  - TASK-FIX-3C9D (AC linter fold into generate_feature_yaml.py)
- Anti-pattern: [`namespace-hygiene.md`](../../.claude/rules/namespace-hygiene.md)
  ("runner without producer" sibling rule, Graphiti uuid `184731b0-...`)
- Originating task: TASK-OBS-ABST
