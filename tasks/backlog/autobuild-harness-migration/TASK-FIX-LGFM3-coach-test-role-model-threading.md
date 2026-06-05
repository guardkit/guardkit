---
id: TASK-FIX-LGFM3
title: Thread `_model_name` to `select_harness` for `coach_test` role in CoachValidator SDK test execution
status: backlog
task_type: bug
created: 2026-06-05T09:00:00Z
updated: 2026-06-05T09:00:00Z
priority: high
complexity: 2
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 0.5
falsifier: "After landing, run 4 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph shows zero `role='coach_test' model=None` failures in coach_validator's SDK test execution path. Regression test asserts that CoachValidator's SDK-path test execution constructs the harness with a non-None model when one is configured."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - sibling-of-f10
  - 4th-instance-of-defect-class
---

# Task: Thread model to coach_test role in CoachValidator SDK test execution

## Description

Surfaced by TASK-HMIG-010 run 3 (2026-06-05T06:36, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) line 313). Identical class-of-defect to F1, F9, F10 — a migration boundary closed for some invocation sites, missed for one more.

This is the **4th instance** of the same defect class:

| # | Finding | Boundary | Site closed | Site missed |
|---|---|---|---|---|
| 1 | F1 | claude-agent-sdk → LangGraph | Player-Coach loop | Pre-loop design phase |
| 2 | F9 | CLI `--model` → orchestrator | task subcommand | feature subcommand |
| 3 | F10 | AgentInvoker model → harness | `_invoke_with_role` | `_invoke_task_work_implement` |
| 4 | **F12** (this) | CoachValidator model → harness | (other test-exec paths?) | `coach_test` role SDK path |

The cadence — 4 instances over the migration — now strongly motivates a `.claude/rules/` seeding (proposal section at the bottom of this task and TASK-FIX-LGFM2 Notes section). Filed as a separate post-cutover task once 010 lands.

## Symptom

Run-3 log line 313:

```
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution
  failed (error_class=LangGraphHarnessError): LangGraphHarness: agent.ainvoke failed
  for role='coach_test' model=None: "Could not resolve authentication method..."
```

**Soft failure**: Line 314 shows the fallback works:

```
WARNING:guardkit.orchestrator.quality_gates.coach_validator:SDK test execution
  failed (error_class=LangGraphHarnessError), falling back to subprocess.
```

So Coach test execution still works via subprocess — the run isn't blocked. But every Coach turn pays a logged ERROR + a fallback overhead, and the LangGraph code path is dead.

## Root cause

In `guardkit/orchestrator/quality_gates/coach_validator.py`, the SDK test execution path constructs a harness via `select_harness(...)` (or equivalent) without passing `model=`. Same shape as F10 was for `_invoke_task_work_implement`. Need to grep the actual call site.

## Acceptance Criteria

- [ ] AC-001: Locate the `coach_test` role harness invocation in `coach_validator.py` (likely a `select_harness(...)` or `harness.invoke(...)` site).
- [ ] AC-002: Thread the orchestrator's `_model_name` to the harness construction at that site, mirroring [`agent_invoker.py:5756`](../../../guardkit/orchestrator/agent_invoker.py) (TASK-FIX-LGFM2 precedent).
- [ ] AC-003: Add a unit-test regression. CoachValidator with `model_name="qwen36-workhorse"` should construct the harness with `model="qwen36-workhorse"` for the `coach_test` role.
- [ ] AC-004: Live smoke (HMIG-010 run 4): the `role='coach_test' model=None` ERROR line is absent. SDK test execution path completes successfully when llama-swap is configured.

## Implementation Notes

- Soft-failure means this is not blocking by itself — the subprocess fallback works. But it's worth fixing in this round so AC-008 falsifier evaluation has a clean signal (no spurious ERRORs in the log).
- Probably one line + one test. Same effort profile as LGFM2.

## References

- Run-3 log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-3.md) line 313–316
- F10 precedent: [TASK-FIX-LGFM2](../../completed/2026-06/TASK-FIX-LGFM2-inline-implement-model-threading.md)
- F9 precedent: [TASK-FIX-LGFM](../../completed/) (commit `683823cc`)
- Class-of-defect chain: [`feature-run-analysis.md` §6 pattern table](../../../docs/state/TASK-REV-HMIG/feature-run-analysis.md)
- Sibling task: [TASK-FIX-CTOUT01](TASK-FIX-CTOUT01-coach-cancellation-timeout-race.md) (F14)
- Sibling task: [TASK-FIX-FALK01](TASK-FIX-FALK01-graphiti-falkordb-teardown-race.md) (F16)

## Notes

After this lands, the count of model-threading-class defects in the harness migration will be 4 (F1, F9, F10, F12). At 4 instances of the same shape we should seed the `.claude/rules/` meta-rule the analysis doc has been flagging since F9:

> *"When a migration moves a contract behind a substrate boundary, audit ALL invocation sites of the boundary, not just the ones the migration's stated scope covers. A grep of `select_harness(` and `harness.invoke(` is cheap; a missed site costs a full run-and-diagnose cycle."*

Post-cutover task: file as TASK-REV-HARNESS-AUDIT or similar.
