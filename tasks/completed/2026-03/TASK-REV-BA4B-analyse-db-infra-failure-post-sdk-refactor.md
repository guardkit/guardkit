---
id: TASK-REV-BA4B
title: Analyse DB task infrastructure failure after SDK refactor
status: review_complete
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: medium
tags: [autobuild, player-coach, infrastructure-failure, sdk-refactor, review]
task_type: review
complexity: 5
parent_review: TASK-REV-D7B2
related_tasks: [TASK-PCTD-5208, TASK-PCTD-9BEB, TASK-PCTD-3182]
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-BA4B-review-report.md
  completed_at: 2026-02-17
  implementation_tasks: [TASK-INFR-6D4F, TASK-INFR-1670, TASK-INFR-5922, TASK-INFR-24DB]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse DB task infrastructure failure after SDK refactor

## Description

Following the TASK-REV-D7B2 review and the subsequent implementation of fixes (TASK-PCTD-5208, TASK-PCTD-9BEB, TASK-PCTD-3182), the player-coach loop is now working significantly better:

- **TASK-DB-001** (scaffolding): APPROVED in 1 turn
- **TASK-DB-002** (scaffolding): APPROVED in 1 turn
- **Stall detection**: Now fires correctly after 3 turns (was 18 turns previously)
- **Infrastructure classification**: Coach correctly identifies "infrastructure/environment issues (not code defects)"

However, **TASK-DB-003** (User model schemas and CRUD) still fails with `UNRECOVERABLE_STALL` after 3 turns. The Coach correctly classifies the failure as infrastructure-related, but the system has no mechanism to handle this edge case — tests that require external services (PostgreSQL) will always fail in the SDK subprocess environment.

### What's working well (from the refactor)

1. Stall detection fires after 3 turns instead of 18 (TASK-PCTD-5208)
2. Infrastructure vs code failure classification works (TASK-PCTD-9BEB)
3. SDK environment parity improvements (TASK-PCTD-3182)
4. Feedback is now descriptive: "Tests failed due to infrastructure/environment issues (not code defects)"
5. Overall loop duration reduced from 45m 58s to 23m 39s

### What still needs resolution

The core issue: When tests require external infrastructure (PostgreSQL, Redis, Docker services), the Coach's independent test verification will always fail because no database is running. The system correctly identifies this as an infrastructure issue but still treats it as a blocking failure, creating an unrecoverable stall.

## Evidence

Full autobuild output: `docs/reviews/autobuild-fixes/db_failed_after_sdk_refactor.md`

### Key log lines

- Line 359: `WARNING: Independent test verification failed for TASK-DB-003 (classification=infrastructure)`
- Line 484: Same pattern repeats turn 3 - always `classification=infrastructure`
- Line 494: `WARNING: Feedback stall: identical feedback (sig=a94d191b) for 3 turns with 0 criteria passing`
- Line 495: `ERROR: Feedback stall detected for TASK-DB-003: identical feedback with no criteria progress`

### Pattern

```
Turn 1: Player implements -> Coach tests via SDK -> fails (infrastructure) -> feedback
Turn 2: Player adjusts   -> Coach tests via SDK -> fails (infrastructure) -> feedback
Turn 3: Player adjusts   -> Coach tests via SDK -> fails (infrastructure) -> STALL DETECTED
```

## Acceptance Criteria

- [ ] Analyse what options exist when Coach classifies a failure as `infrastructure` type
- [ ] Determine whether infrastructure-classified failures should bypass independent test verification
- [ ] Assess risk of auto-approving when classification=infrastructure (false positive risk)
- [ ] Review whether task_type metadata could hint that tests need external services
- [ ] Evaluate if the feature YAML or task definition could declare infrastructure dependencies
- [ ] Consider a "conditional approval" state (approved-without-tests) vs hard block
- [ ] Recommend the safest approach that prevents infinite stalls for infra-dependent tasks

## Review Focus Areas

### 1. Infrastructure failure handling strategy
Currently the Coach classifies the failure correctly but has no alternative path. Options to evaluate:
- **Auto-approve with warning**: If classification=infrastructure for N consecutive turns, approve with a flag
- **Skip independent verification**: For tasks with known infra dependencies
- **Conditional approval**: New state `approved_without_tests` that requires human sign-off
- **Task-level override**: Allow feature YAML to declare `requires_infrastructure: [postgresql]`

### 2. False positive risk assessment
If we auto-approve on infrastructure classification, could a genuine code bug be misclassified? The classification logic in TASK-PCTD-9BEB should be reviewed for edge cases where:
- Import errors look like infrastructure failures
- Missing fixtures look like missing DB connections
- Actual assertion failures contain DB-related error messages

### 3. Task/feature metadata approach
Could the feature YAML or task definition include infrastructure requirements?
```yaml
tasks:
  - id: TASK-DB-003
    requires_infrastructure: [postgresql]
    test_strategy: skip_independent_verification
```

### 4. Coach validator modifications
Review `coach_validator.py` for the decision path after `classification=infrastructure`:
- Current: Always fail and provide feedback
- Proposed: Conditional approval or skip after N infrastructure failures

## Key Files to Review

### Primary
- [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) - Infrastructure classification and decision logic
- [autobuild.py](guardkit/orchestrator/autobuild.py) - Stall detection and feedback loop
- [task_work_interface.py](guardkit/orchestrator/quality_gates/task_work_interface.py) - Quality gate profiles

### Evidence
- [db_failed_after_sdk_refactor.md](docs/reviews/autobuild-fixes/db_failed_after_sdk_refactor.md) - Full failure log

### Completed fixes (context)
- [TASK-PCTD-5208](tasks/completed/TASK-PCTD-5208/TASK-PCTD-5208.md) - Quick wins / feedback stall paths
- [TASK-PCTD-9BEB](tasks/completed/TASK-PCTD-9BEB/TASK-PCTD-9BEB-classify-infra-vs-code-failures.md) - Infrastructure vs code classification
- [TASK-PCTD-3182](tasks/completed/TASK-PCTD-3182/TASK-PCTD-3182-sdk-bash-environment-parity.md) - SDK/Bash environment parity

## Implementation Notes

Review task - analysis and recommendations only. The goal is to determine the right approach for handling infrastructure-dependent tasks in AutoBuild, where the tests genuinely require external services that aren't available in the Coach's verification environment.

This is an edge case but an important one — database integration tasks are common in real-world projects and AutoBuild needs a strategy for them.

## Test Execution Log
[Automatically populated by /task-work]
