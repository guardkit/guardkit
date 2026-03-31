# Implementation Guide: vLLM Run 5 Regression Fixes (FEAT-9db9)

## Problem Statement

AutoBuild Run 5 regressed from 7/7 to 6/7 task completion. TASK-FBP-007 failed after 8 turns with `timeout_budget_exhausted`. Root cause analysis (TASK-REV-5E1F) identified 4 contributing factors: infeasible acceptance criteria, budget starvation from serialized execution, asymmetric budget handling in Player vs Coach, and lack of AC feasibility validation in feature planning.

## Execution Strategy

Sequential execution recommended — tasks have logical dependencies.

### Wave 1: Quick Fixes (Effort: LOW)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-VRF-001 | Relax FBP-007 acceptance criteria | direct | 2 |
| TASK-VRF-002 | Separate FBP-007 into Wave 6 | direct | 2 |
| TASK-VRF-007 | Correct task description | direct | 1 |

**These can be executed immediately and independently.**

### Wave 2: Budget Fix (Effort: MEDIUM)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-VRF-003 | Pass remaining_budget to invoke_player | task-work | 4 |

**Requires code changes in agent_invoker.py and autobuild.py. Run tests after.**

### Wave 3: Feature Planning (Effort: HIGH)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-VRF-004 | Backend-aware AC validation | task-work | 6 |

**New module creation. Depends on understanding from Wave 1-2.**

### Wave 4: State Recovery (Effort: MEDIUM)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-VRF-005 | Fix synthetic report corruption | task-work | 7 |

**Investigation-heavy. Depends on TASK-VRF-003 for budget context.**

### Wave 5: Exploration (Effort: MEDIUM)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-VRF-006 | Explore max_parallel=2 | task-work | 5 |

**Experimental. Depends on TASK-VRF-003 for budget improvements.**

## Key Files

| File | Tasks Affecting |
|------|----------------|
| `guardkit/orchestrator/agent_invoker.py` | VRF-003 |
| `guardkit/orchestrator/autobuild.py` | VRF-003, VRF-005 |
| `guardkit/orchestrator/feature_orchestrator.py` | VRF-006 |
| `guardkit/cli/autobuild.py` | VRF-006 |
| `guardkit/validation/ac_validator.py` (new) | VRF-004 |
| Feature plan task files (vLLM project) | VRF-001, VRF-002 |

## Verification

After completing all waves, re-run AutoBuild on the vLLM profiling feature:
```bash
guardkit autobuild feature FEAT-1637 --fresh
```

Expected outcome: 7/7 tasks completed (Run 6 = SUCCESS).

## Parent Review

[TASK-REV-5E1F Review Report](../../.claude/reviews/TASK-REV-5E1F-review-report.md)
