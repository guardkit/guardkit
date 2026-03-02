# AutoBuild Orchestrator Failure Fixes

**Feature ID**: FEAT-CD4C
**Parent Review**: TASK-REV-A17A
**Tasks**: 9
**Waves**: 4

## Problem Statement

Analysis of two AutoBuild feature orchestration runs (FEAT-E4F5 and FEAT-CF57) identified 7 failure modes at integration boundaries between orchestrator components. The two most critical:

1. **Dual-layer timeout inversion**: SDK timeout and feature-level timeout compete without coordination, causing multi-turn tasks to be killed mid-execution even though individual turns complete successfully
2. **task_type validation gap**: Invalid `task_type` values (e.g., `enhancement`) are only validated at Coach time, causing deterministic 3-turn stalls with no possibility of recovery

## Solution Approach

9 implementation tasks across 4 waves, addressing failures from most critical to least:

- **Wave 1** (Critical): Add missing alias, validate task_type early, fast-exit on config errors
- **Wave 2** (High): Redesign timeout to per-turn budgeting, isolate Coach tests from parallel contention
- **Wave 3** (Medium/Low): Pre-flight CLI validation, noise reduction
- **Wave 4** (Verification): Integration tests across all fixed seams

## Task Summary

| Task | Priority | Complexity | Wave |
|------|---------|-----------|------|
| TASK-ABFIX-001 — Add `enhancement` alias | Critical | 2 | 1 |
| TASK-ABFIX-002 — Validate task_type at feature load | Critical | 4 | 1 |
| TASK-ABFIX-003 — Config error fast-exit | Critical | 5 | 1 |
| TASK-ABFIX-004 — Per-turn timeout budget | Critical | 6 | 2 |
| TASK-ABFIX-005 — Coach test isolation | High | 6 | 2 |
| TASK-ABFIX-006 — Timeout logging reconciliation | Medium | 3 | 2 |
| TASK-ABFIX-007 — Feature validate CLI | Medium | 4 | 3 |
| TASK-ABFIX-008 — Doc level + bootstrap fixes | Low | 3 | 3 |
| TASK-ABFIX-009 — Integration tests | High | 6 | 4 |

## Modules Affected

- `guardkit/orchestrator/feature_orchestrator.py`
- `guardkit/orchestrator/autobuild.py`
- `guardkit/orchestrator/agent_invoker.py`
- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/orchestrator/worktree_checkpoints.py`
- `guardkit/orchestrator/feature_loader.py`
- `guardkit/orchestrator/environment_bootstrap.py`
- `guardkit/models/task_types.py`
