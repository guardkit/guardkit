---
id: TASK-REV-4402
title: Analyse successful FEAT-BA28 autobuild run for remaining issues
status: review_complete
created: 2026-02-18T23:00:00Z
updated: 2026-02-19T00:00:00Z
priority: high
task_type: review
tags: [autobuild, coach-validator, documentation-constraint, tests-required, regression-prevention]
complexity: 3
related_tasks:
  - TASK-REV-9745   # Prior regression review (completion_promises stall)
  - TASK-FIX-FFE2   # Companion fix: _find_task_file design_approved blind spot
  - TASK-FIX-4AB4   # Companion fix: completion_promises protocol mandate
evidence_file: docs/reviews/autobuild-fixes/db_finally_succeds.md
review_results:
  mode: architectural
  depth: standard
  score: 82
  findings_count: 5
  recommendations_count: 4
  decision: accept
  report_path: .claude/reviews/TASK-REV-4402-review-report.md
  completed_at: 2026-02-19T00:00:00Z
---

# Review: Analyse Successful FEAT-BA28 Autobuild Run for Remaining Issues

## Context

Following the investigation in TASK-REV-9745 (completion_promises stall regression), a fresh `--fresh` autobuild run of FEAT-BA28 (PostgreSQL Database Integration) succeeded end-to-end:

```
Feature: FEAT-BA28 - PostgreSQL Database Integration
Status: COMPLETED
Tasks: 5/5 completed
Total Turns: 5
Duration: 42m 0s
Clean executions: 5/5 (100%)
```

All 5 tasks (TASK-DB-001 through TASK-DB-005) were approved on turn 1. However, several anomalies are visible in the run log that warrant investigation to ensure the system is behaving correctly and no latent issues remain.

**Evidence file**: `docs/reviews/autobuild-fixes/db_finally_succeds.md`

## Observed Anomalies

### Anomaly 1 — Documentation Level Constraint Violated on Every Task (5/5)

Every single task triggered this warning:

```
WARNING: [TASK-DB-001] Documentation level constraint violated: created 7 files, max allowed 2 for minimal level.
WARNING: [TASK-DB-002] Documentation level constraint violated: created 8 files, max allowed 2 for minimal level.
WARNING: [TASK-DB-003] Documentation level constraint violated: created 9 files, max allowed 2 for minimal level.
WARNING: [TASK-DB-004] Documentation level constraint violated: created 7 files, max allowed 2 for minimal level.
WARNING: [TASK-DB-005] Documentation level constraint violated: created 3 files, max allowed 2 for minimal level.
```

The constraint is `minimal level: max 2 files`. These tasks legitimately create 7-9 files (source files, tests, config). The constraint was violated but the run succeeded anyway — the warning appears to be informational rather than blocking. This raises several questions:

- Is `minimal` the correct documentation level for feature tasks of this type?
- Should this be blocking or is the warning correctly non-blocking?
- Does the file count include all created files (including autobuild artifacts like `player_turn_1.json`) or just source files?
- Is the limit misconfigured for `tdd` mode?

### Anomaly 2 — `tests_required=False` for TASK-DB-001, TASK-DB-002, TASK-DB-005

Three tasks had independent test verification skipped:

```
INFO: Independent test verification skipped for TASK-DB-001 (tests_required=False)
INFO: Independent test verification skipped for TASK-DB-002 (tests_required=False)
INFO: Independent test verification skipped for TASK-DB-005 (tests_required=False)
```

TASK-DB-003 and TASK-DB-004 DID run independent tests (and passed). The distinction appears to be task type: TASK-DB-003 is `user-model-schemas-crud` and TASK-DB-004 is `api-endpoints-health-check` — both have application logic requiring tests. TASK-DB-001 (infrastructure), TASK-DB-002 (alembic migrations), and TASK-DB-005 (database tests themselves) are classified differently.

Questions:
- Is the `tests_required` classification logic correct for infrastructure/migration/test tasks?
- TASK-DB-005 is specifically "add database tests" — should this task require independent test verification?
- What quality gate profile drives this decision?

### Anomaly 3 — High SDK Turn Counts (63, 61, 54, 66, 42 turns)

SDK turn counts were high across all tasks:

| Task | SDK turns | Max |
|------|-----------|-----|
| TASK-DB-001 | 63 | 50? |
| TASK-DB-002 | 61 | 50? |
| TASK-DB-003 | 54 | 50? |
| TASK-DB-004 | 66 | 50? |
| TASK-DB-005 | 42 | 50? |

Notably TASK-DB-001 used 63 turns and TASK-DB-004 used 66 turns — both above the previously observed max_turns=50. The SDK timeout was scaled upward (`SDK timeout: 2880s (base=1200s, mode=task-work x1.5, complexity=6 x1.6)`). It is unclear whether `max_turns` was also scaled or if the 50-turn limit seen in previous runs was raised.

Questions:
- Was `max_turns` increased from 50 in this run? The log shows `Max turns: 50` for TASK-DB-005 but the actual turn count is 42 — consistent. But TASK-DB-001 shows 63 turns — inconsistent with max_turns=50.
- Is `max_turns` per-task dynamically scaled like the SDK timeout?
- If `max_turns` is now scaled by complexity, does the prior regression scenario (turn exhaustion causing missing completion_promises) remain possible?

### Anomaly 4 — Graphiti Project ID Auto-Detection Warning (repeated 5 times)

```
WARNING: No explicit project_id in config, auto-detected 'fastapi' from cwd.
Set project_id in .guardkit/graphiti.yaml for consistent behavior.
```

This appeared after every task's Coach validation. While low severity, it suggests the Graphiti configuration for the fastapi example project is incomplete.

### Anomaly 5 — completion_promises Recovered (Not Directly Written) on All Tasks

All tasks used Fix 2 recovery rather than having the agent write promises directly to `task_work_results.json`:

```
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-001
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-002
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-003
INFO: Recovered 7 completion_promises from agent-written player report for TASK-DB-004
INFO: Recovered 6 completion_promises from agent-written player report for TASK-DB-005
```

The recovery mechanism (Fix 2) is working correctly. However, the fact that `completion_promises` always needs to be recovered (never present in `task_work_results.json` directly) confirms the structural gap identified in TASK-REV-9745 Finding 1: `TaskWorkStreamParser` has no pattern for `completion_promises`. This is expected and benign here, but confirms that the system is always one agent-behaviour-fluctuation away from 0/6 if Fix 2 fails.

## Review Scope

### Question 1 — Documentation Level Constraint: Misconfiguration or Expected?

Is `minimal` the correct documentation level for tasks run in `tdd` mode as part of a feature build? If the constraint is always violated and never blocking, is it providing any value, or is it noise that should be fixed?

Examine:
- How is the documentation level selected? (task type? feature config? hardcoded?)
- Is the file count logic correct — does it count autobuild artifact files (`player_turn_1.json`) that shouldn't count against the limit?
- Should the level be `standard` for `tdd` mode tasks?

**File**: `guardkit/orchestrator/agent_invoker.py` (documentation level constraint logic)

### Question 2 — `tests_required` Classification: Is TASK-DB-005 Correctly Classified?

TASK-DB-005 ("add database tests") had `tests_required=False`. This seems questionable — a task that adds tests should probably verify those tests pass independently.

Examine:
- What determines the quality gate profile (tests_required=True/False) for a task?
- Is it driven by `task_type` in the task frontmatter?
- Should `task_type: testing` tasks have `tests_required=True`?

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py` (quality gate profile selection)

### Question 3 — Was `max_turns` Scaled Beyond 50 in This Run?

The previous failing run had `max_turns=50`. In this run, TASK-DB-001 used 63 turns and TASK-DB-004 used 66 — both above 50. Was `max_turns` also scaled (like the SDK timeout), and if so, does this mean the turn-exhaustion risk has been mitigated?

Examine:
- Is `max_turns` dynamically scaled by complexity in the current code?
- What was the actual `max_turns` value passed to the SDK for each task in this run?

**File**: `guardkit/orchestrator/agent_invoker.py` (SDK invocation, max_turns calculation)

### Question 4 — Graphiti Configuration: Fix for fastapi Example Project?

The `project_id` warning is a minor but persistent noise source. Should `.guardkit/graphiti.yaml` be added to the fastapi example project?

**Directory**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/fastapi/.guardkit/`

## Files to Examine

- `guardkit/orchestrator/agent_invoker.py` — documentation level constraint, max_turns scaling
- `guardkit/orchestrator/quality_gates/coach_validator.py` — quality gate profile selection, `tests_required` logic
- `guardkit-examples/fastapi/.guardkit/` — Graphiti config presence
- `docs/reviews/autobuild-fixes/db_finally_succeds.md` — the run log itself

## Acceptance Criteria

- [ ] Documentation level constraint: determined whether `minimal` level is misconfigured for tdd/feature tasks and whether it should be blocking
- [ ] `tests_required=False` for TASK-DB-005: determined whether this is correct or whether testing tasks should require independent verification
- [ ] `max_turns` scaling: confirmed whether max_turns is now dynamically scaled (explaining the 63/66 turn counts) or whether those were under-reported/measured differently
- [ ] Graphiti warning: recommendation made (fix config or suppress warning)
- [ ] Residual risk assessment: any remaining issues that need a fix task
