---
id: TASK-FIX-RWOP1.3.2
title: Wire execute_phase_5_5_plan_audit into AgentInvoker._write_task_work_results (P2 WIRE)
status: backlog
task_type: implementation
created: 2026-04-22T12:00:00Z
updated: 2026-04-22T12:00:00Z
priority: high
complexity: 5
tags: [runner-without-producer, task-work, wire, plan-audit, rwop1]
parent_task: TASK-FIX-RWOP1.3
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_tasks:
  - TASK-FIX-RWOP1.3
  - TASK-FIX-RWOP1.3.1
  - TASK-FIX-3C9D
depends_on:
  - TASK-FIX-RWOP1.3.1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Wire `execute_phase_5_5_plan_audit` as the deterministic producer for `task_work_results["plan_audit"]`

## Problem Statement

Per [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) Finding #5 and the [TASK-FIX-RWOP1.3 triage](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md) (PA-4, WIRE P2):

`guardkit/orchestrator/quality_gates/coach_validator.py:1118-1130` reads `task_work_results["plan_audit"]["violations"]` to gate turn approval. The producer of that field today is the Player LLM's self-report via the `autobuild_execution_protocol.md:307-346` prose. The Player can trivially emit `"violations": []` regardless of whether the actual implementation deviates from the approved plan.

`installer/core/commands/lib/phase_execution.py:execute_phase_5_5_plan_audit` + `installer/core/commands/lib/plan_audit.py` implement a deterministic auditor (compare saved plan vs actual files/dependencies/LOC, assign severity). Both modules are fully unit-tested and have **zero non-test callers** in `guardkit/`.

The fix shape is the same as [TASK-FIX-RWOP1.3.1](TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md): fold the deterministic producer into `AgentInvoker._write_task_work_results` so Coach sees the authoritative audit, not the Player's self-report.

## Scope

### In-scope

1. **Producer hook.** In `guardkit/orchestrator/agent_invoker.py`:
   - In the autobuild update surface at `:2753-2789`, after Player writes the results file and after the RWOP1.3.1 `agent_invocations_validation` step:
     - Load the saved implementation plan (`docs/state/{task_id}/implementation_plan.md` or `.json` — module already supports both).
     - Call `execute_phase_5_5_plan_audit(task_id, task_context)` with `task_context` assembled from the Player report.
     - **Override** any Player-supplied `task_work_results["plan_audit"]` block with the deterministic result. If the plan file doesn't exist, write `{"status": "skipped", "reason": "no plan"}` — matches current module behaviour.
   - Does NOT prompt for user decision (the module has an interactive prompt path — call the non-interactive variant, or disable the prompt in autobuild mode). Severity / violations are the data; the decision is Coach's.
2. **Module surface.** Audit `plan_audit.py` for any `input(...)` / `readline()` call; add a `non_interactive: bool = False` parameter or similar escape hatch if needed. The interactive prompt is a UX affordance for the historical `--implement-only` path, not a contract.
3. **Coach gate.** `coach_validator` already consumes `plan_audit.violations`. Verify it reads the new fields (`severity`, `extra_files`, `missing_files`, `loc_variance_pct`, etc.) and gates appropriately on severity `high`. Tighten the gate if today it only checks `violations` length.
4. **End-to-end test.** Add an integration test (new file under `tests/integration/autobuild/`) that:
   - Provides a saved plan expecting 5 files; Player actually creates 7 files (2 extras).
   - Asserts the deterministic audit in `task_work_results["plan_audit"]` reports `severity: high` + the 2 extra files.
   - Asserts Coach rejects with feedback citing the extras.
5. **Spec alignment.** Rewrite the task-work.md Phase 5.5 prose (`:4087-4200`-ish) from "Player runs the auditor" to "the deterministic auditor runs post-write and overrides the Player's self-report." Keep the severity thresholds, report format, and user-decision flow for interactive `/task-work`.

### Out-of-scope

- Wiring `validate_agent_invocations` — that's [TASK-FIX-RWOP1.3.1](TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md).
- Deleting `plan_persistence.save_plan` (the design-only plan saver) — that's [TASK-FIX-RWOP1.3.3](TASK-FIX-RWOP1.3.3-delete-orphan-modules.md). **Important dependency:** `plan_audit` reads the saved plan. If `save_plan` is deleted in RWOP1.3.3, that deletion must provide an alternative path for plan persistence OR RWOP1.3.3 must defer the `plan_persistence` deletion until the canonical plan source is decided. See RWOP1.3.3 scope for the resolution.
- Softening Phase 4.5 retry-loop prose — RWOP1.3.4.

### Dependency on RWOP1.3.1

Depends on [TASK-FIX-RWOP1.3.1](TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md) landing first so the `_write_task_work_results` hook pattern is established and the two wires are composable (P1 runs first — validate agents invoked at all; P2 runs second — validate the work done matches the plan). Order matters: if P1 catches a "no test-agent invocation" violation, running P2 afterwards is still informative but not critical.

## Acceptance Criteria

- [ ] `grep -rn "execute_phase_5_5_plan_audit\|plan_audit\." guardkit/ | grep -v tests/` returns a non-trivial hit count (wiring landed in `agent_invoker.py`).
- [ ] `task_work_results.json` `plan_audit` block is demonstrably the deterministic auditor's output, not Player prose: a Player report claiming `violations: []` while the worktree has 2 extra files is overridden to `violations: [...]` with severity.
- [ ] Coach rejects a turn with the expected feedback when a saved plan exists and the actual implementation adds ≥ 2 files not in the plan.
- [ ] End-to-end test passes with the extras scenario above.
- [ ] No interactive prompt fires in the autobuild path; interactive `/task-work` flow preserved.
- [ ] `task-work.md` Phase 5.5 prose rewritten to describe the post-write deterministic path.

## Implementation Notes

- The `plan_audit.py` module already produces a structured report with severity (`low` / `medium` / `high`). Reuse it verbatim — this task is wiring, not re-authoring.
- Plan lookup: `plan_audit` accepts both `implementation_plan.md` and `implementation_plan.json`. The saved-plan path today is `docs/state/{task_id}/`. Keep that. If RWOP1.3.3 ends up deleting `plan_persistence.save_plan`, negotiate a replacement path in that task — but until then, keep the current writer intact.
- If the autobuild Player doesn't save a plan at all (pre-loop disabled, no `--design-only`), the audit correctly emits `skipped`. That's acceptable; Coach should not reject on skipped plan audits.
- Graphiti: this is the second wire in the triage; together with RWOP1.3.1 they constitute the "task-work.md WIRE remediation". Consider updating the `guardkit__project_decisions` episode when both land.

## Related

- Parent triage: [docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md)
- Parent review: [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) Finding #5
- Canonical fix shape: [TASK-FIX-3C9D](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Sibling WIRE task: [TASK-FIX-RWOP1.3.1](TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md) (must land first)
