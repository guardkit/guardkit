# AutoBuild Observability Fixes (FEAT-AOF)

## Problem Statement

Analysis of the RequireKit v2 autobuild success run (FEAT-498F) revealed bugs in the observability and constraint enforcement layers that produce misleading file counts, false constraint violations, and confusing log output. These don't affect the implementation pipeline (14/14 tasks completed cleanly) but degrade trust in automated reporting.

## Source

- Review: [TASK-REV-A515](./../TASK-REV-A515-analyse-requirekit-feature-autobuild-success.md)
- Report: [Review Report](../../../.claude/reviews/TASK-REV-A515-review-report.md)

## Solution Approach

Five targeted fixes across two waves, all in `guardkit/orchestrator/agent_invoker.py` and related files.

## Tasks

### Wave 1 (Parallel — No Dependencies)

| Task | Priority | Description | Complexity | Files |
|------|----------|-------------|------------|-------|
| TASK-FIX-PV01 | P1 | Fix file path validation + constraint ordering | 4 | agent_invoker.py |
| TASK-FIX-IA03 | P3 | Exclude internal artifacts from doc constraint | 3 | agent_invoker.py |
| TASK-FIX-TS04 | P3 | Clarify test status when tests not required | 3 | agent_invoker.py, coach_validator.py |

### Wave 2 (Depends on Wave 1)

| Task | Priority | Description | Complexity | Files |
|------|----------|-------------|------------|-------|
| TASK-FIX-GD02 | P1 | Scope git detection to per-task changes | 6 | agent_invoker.py, autobuild.py |
| TASK-FIX-TP05 | P3 | Add test execution for testing task type | 4 | task_types.py, coach_validator.py |

## Execution Strategy

- Wave 1: 3 tasks in parallel (all touch different code sections of agent_invoker.py)
- Wave 2: 2 tasks in parallel (GD02 depends on PV01 for clean file lists; TP05 depends on TS04 for display consistency)

## Expected Outcomes

After implementation:
- No more spurious file paths ('house', '**') in logs
- Per-task file counts reflect actual task changes, not cumulative worktree state
- Documentation constraint violations only fire for genuine user-file overproduction
- Log output clearly distinguishes "tests not required" from "tests failing"
- Testing-type tasks verify their test files actually pass
