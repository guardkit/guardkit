---
id: TASK-FIX-RWOP1.3.1
title: Wire validate_agent_invocations into AgentInvoker._write_task_work_results (P1 WIRE)
status: completed
task_type: implementation
created: 2026-04-22T12:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "Task completion after all ACs verified and regression suite passed"
priority: high
complexity: 5
tags: [runner-without-producer, task-work, wire, rwop1]
parent_task: TASK-FIX-RWOP1.3
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_tasks:
  - TASK-FIX-RWOP1.3
  - TASK-FIX-3C9D
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-23T00:00:00Z
  suite: "tests/integration/autobuild/test_agent_invocations_gate.py (7 passing)"
  regression_suite: "tests/unit/test_agent_invoker*.py + tests/unit/test_coach_validator.py + tests/integration/autobuild/ + tests/integration/feature_plan/ (901 passing)"
---

# Task: Wire `validate_agent_invocations` into `AgentInvoker._write_task_work_results`

## Problem Statement

Per [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) Finding #4 and the [TASK-FIX-RWOP1.3 triage](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md) (row 23, WIRE P1):

`installer/core/commands/task-work.md:4266-4274` declares `validate_agent_invocations(tracker, workflow_mode)` as *"the ONLY checkpoint that prevents false reporting."* The module at `installer/core/commands/lib/agent_invocation_validator.py` is fully implemented and unit-tested. It has **zero non-test callers** in the `guardkit/` runtime. Consequence: the Player LLM can emit a `task_work_results.json` claiming any set of agents were invoked (or none) and no deterministic check catches it before Coach reads the file.

The producer today is Player prose. The fix shape is the TASK-FIX-3C9D pattern: fold the producer into the script the spec already shells out to. The analogue for Player-emitted results is `AgentInvoker._write_task_work_results` (and the autobuild update surface at `agent_invoker.py:2753-2789`), which is the single point at which `task_work_results.json` is finalised before Coach reads it.

## Scope

### In-scope

1. **Producer hook.** In `guardkit/orchestrator/agent_invoker.py`:
   - Add a post-write step in `_write_task_work_results` (and the autobuild-path update block at `:2753-2789`) that:
     - Reads the `agent_invocations` list that the Player wrote into `task_work_results.json` (and/or reconstructs it from the Player report).
     - Determines `workflow_mode` from task frontmatter / invocation context (default `"standard"`).
     - Calls `validate_agent_invocations(tracker_from_report, workflow_mode)` with a `ValidationError` capture.
     - Writes the result into `task_work_results["agent_invocations_validation"]` with shape `{"status": "passed" | "violation", "expected_phases": int, "actual_invocations": int, "missing_phases": [...], "violation_message": str | None}`.
   - Does NOT move the task file or mutate state on the main tree. Violation is expressed purely in the results file so Coach can gate on it.
2. **Import.** Make `validate_agent_invocations` a first-class import on `installer/core/commands/lib/__init__.py` (currently not re-exported) so `agent_invoker.py` can import it via the stable public surface.
3. **Coach gate.** In `guardkit/orchestrator/quality_gates/coach_validator.py`, extend the gate logic to reject a turn when `task_work_results["agent_invocations_validation"]["status"] == "violation"`. Treat missing-phases as a task-blocking finding, not a soft warning.
4. **End-to-end test.** Add an integration test (new file under `tests/integration/autobuild/`) that:
   - Feeds the orchestrator a mocked Player report missing (at minimum) `code-reviewer` and `test-agent` invocations.
   - Asserts `task_work_results.json` contains `agent_invocations_validation.status == "violation"`.
   - Asserts the Coach run rejects the turn with feedback naming the missing phases.
5. **Spec alignment.** Rewrite the task-work.md Step 6.5 prose (currently lines 4266-4346) to describe the deterministic post-write path instead of a Claude-runtime in-loop step. Keep the "ONLY checkpoint" framing — it is now true because the check actually runs.

### Out-of-scope

- Wiring `execute_phase_5_5_plan_audit` — that's [TASK-FIX-RWOP1.3.2](TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md).
- Deleting the `PhaseGateValidator` / `AgentInvocationTracker` / other orphan modules — that's [TASK-FIX-RWOP1.3.3](TASK-FIX-RWOP1.3.3-delete-orphan-modules.md). Note: `AgentInvocationTracker` is used transitively by `validate_agent_invocations` in the current module API; if that dependency remains after wiring, adjust RWOP1.3.3's scope accordingly.
- Softening pseudo-code prose (Phase 4.5 retry loop, `determine_next_state`, etc.) — that's [TASK-FIX-RWOP1.3.4](TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md).
- Changing the BDD / plan-audit consumer paths Coach already uses.

## Acceptance Criteria

- [ ] `grep -rn "validate_agent_invocations" guardkit/ installer/scripts/ | grep -v tests/` returns at least one hit (hook landed in `agent_invoker.py`).
- [ ] `task_work_results.json` written by an autobuild Player run contains an `agent_invocations_validation` block with `status`, `expected_phases`, `actual_invocations`, `missing_phases`.
- [ ] `coach_validator` rejects a turn with the expected feedback when `status == "violation"`; test proves it.
- [ ] End-to-end test passes: mocked Player missing two phases → Coach feedback names the missing phases → turn not approved.
- [ ] `installer/core/commands/lib/__init__.py` re-exports `validate_agent_invocations` + `ValidationError` via `agent_invocation_validator`.
- [ ] `task-work.md` Step 6.5 prose rewritten to describe the post-write deterministic path (no more "in-loop Claude checkpoint" framing).

## Implementation Notes

- The canonical fix shape reference is [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md) — a producer-script fold. The equivalent here is the `_write_task_work_results` fold.
- Watch the autobuild update surface at `agent_invoker.py:2753-2789` (the post-Player enrichment block). The check needs to run *after* that block completes, so the final on-disk results file carries the validation.
- `workflow_mode` determination: for autobuild, default to `"standard"`; if the task frontmatter has `mode: tdd` or `mode: bdd`, map accordingly. `get_expected_phases` in the validator module already returns 5 for standard / 3 for micro / design-only / implement-only.
- The Player writes `agent_invocations` as a list of `{"phase": "...", "agent": "...", "status": "completed"}` per the existing instrumentation. Build a throwaway `AgentInvocationTracker` from that list purely as the input shape for `validate_agent_invocations` — do not persist the tracker.
- Do NOT block the autobuild turn from writing its results if the validator itself raises (catch the exception, log, set `status: "validator_error"`, let Coach decide). The validator is a gate, not a blocker of artefact emission.

## Related

- Parent triage: [docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md)
- Parent review: [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) Finding #4
- Canonical fix shape: [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Sibling WIRE task: [TASK-FIX-RWOP1.3.2](TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md)
