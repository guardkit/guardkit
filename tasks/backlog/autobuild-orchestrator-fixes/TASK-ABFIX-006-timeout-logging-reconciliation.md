---
id: TASK-ABFIX-006
title: Reconcile timeout vs cancelled logging and add timeout layer attribution
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 2
implementation_mode: task-work
complexity: 3
dependencies: [TASK-ABFIX-004]
autobuild:
  enabled: true
  max_turns: 3
  mode: tdd
status: backlog
priority: medium
tags: [autobuild, orchestrator, logging, observability]
---

# Task: Reconcile timeout vs cancelled logging and add timeout layer attribution

## Description

When a task times out, the feature summary shows "TIMEOUT" but the AutoBuild summary shows "CANCELLED" — these should be reconciled. Additionally, timeout events should log which layer fired (SDK vs feature) and the remaining budget on the other layer, enabling faster diagnosis of timeout issues.

## Review Reference

From TASK-REV-A17A Finding 1, Recommendation 1c; Finding 7, Recommendation 7b:
> 1c: Log which timeout layer fired (SDK vs feature) and the remaining budget on the other layer. Currently TASK-INST-002 shows "TIMEOUT" in the feature summary but "CANCELLED" in the AutoBuild summary — these should be reconciled.
> 7b: Report CANCELLED vs TIMEOUT distinctly in feature summary.

## Requirements

1. When a task is terminated by the feature-level timeout:
   - Log: `"TIMEOUT (feature-level): task_timeout=2400s expired. SDK had {remaining}s remaining on its {sdk_timeout}s budget."`
   - The final decision should be `"timeout"` (not `"cancelled"`)
2. When a task is cancelled by the cancellation event (set by another task's failure in `stop_on_failure` mode):
   - Log: `"CANCELLED: cancellation_event set by wave coordinator (stop_on_failure triggered by {triggering_task_id})."`
   - The final decision should be `"cancelled"`
3. When the SDK timeout fires:
   - Log: `"TIMEOUT (SDK-level): sdk_timeout={sdk_timeout}s expired. Feature task had {remaining}s remaining of its {task_timeout}s budget."`
4. Reconcile the reporting so `feature_orchestrator.py` and `autobuild.py` use the same decision string

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` — pass timeout metadata, distinguish timeout from cancellation
- `guardkit/orchestrator/autobuild.py` — report correct decision string with layer attribution
- `guardkit/orchestrator/agent_invoker.py` — include remaining budget in timeout error
- `tests/` — verify logging output for each timeout scenario

## Acceptance Criteria

- [ ] Feature-level timeout reports as "timeout" consistently (not "cancelled")
- [ ] Cancellation reports as "cancelled" consistently (not "timeout")
- [ ] Timeout events log which layer fired and remaining budget on the other layer
- [ ] All existing tests pass
