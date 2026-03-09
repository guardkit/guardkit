---
id: TASK-REV-5E1F
title: Investigate vLLM Run 5 AutoBuild regression (TASK-FBP-007 timeout)
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
priority: high
tags: [autobuild, vllm, regression, timeout, investigation]
complexity: 6
related_tasks: [TASK-REV-F8BA, TASK-GCF-001, TASK-GCF-002, TASK-GCF-003, TASK-VOPT-001, TASK-VOPT-002, TASK-VOPT-003, TASK-REV-982B]
created: 2026-03-08T22:00:00Z
updated: 2026-03-09T00:00:00Z
review_results:
  mode: decision
  depth: standard (revised with 5 deep-dives)
  findings_count: 5
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-5E1F-review-report.md
  implementation_feature: FEAT-9db9
  implementation_tasks: [TASK-VRF-001, TASK-VRF-002, TASK-VRF-003, TASK-VRF-004, TASK-VRF-005, TASK-VRF-006, TASK-VRF-007]
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Investigate vLLM Run 5 AutoBuild Regression (TASK-FBP-007 Timeout)

## Description

AutoBuild feature build Run 5 (`docs/reviews/vllm-profiling/vllm_run_5.md`) failed with 6/7 tasks completed, regressing from Run 4 (`docs/reviews/vllm-profiling/vllm_run_4.md`) which succeeded with 7/7 tasks.

The failure is isolated to **TASK-FBP-007** (Quality gates: ruff, mypy, pytest-cov configuration) which exhausted its timeout budget after 8 turns, with every Player invocation cancelled via asyncio cancel scope.

## Context

### Run Comparison

| Metric | Run 4 (SUCCESS) | Run 5 (FAILED) |
|--------|-----------------|-----------------|
| Result | 7/7 completed | 6/7 (1 failed) |
| Duration | 227m | 409m |
| TASK-FBP-007 mode | `direct` | `direct` |
| TASK-FBP-007 turns | 1 | 8 (all cancelled) |
| TASK-FBP-007 SDK timeout | 6240s | 6240s |
| TASK-FBP-006 SDK turns | 43 | 110 (HIT) |

### Key Observations

1. **Mode routing was identical**: TASK-FBP-007 used `direct` mode in both Run 4 and Run 5 (SDK timeout 6240s in both). Mode routing was **ruled out** as a root cause — the regression is due to timeout budget exhaustion from upstream tasks (primarily TASK-FBP-006).

2. **Cancel scope pattern**: All 8 Player turns failed with `CancelledError: Cancelled via cancel scope` — this indicates the task-level or feature-level timeout budget was exhausted, not an SDK error.

3. **TASK-FBP-006 consumed more budget**: In Run 5, TASK-FBP-006 used 110 SDK turns (ceiling hit) vs 43 in Run 4, consuming significantly more of Wave 5's time budget.

4. **State recovery worked**: Turn 1 state recovery detected 9 files changed, 229 tests passing — the Player actually did meaningful work before cancellation, but the Coach couldn't converge on acceptance criteria (especially `mypy src/` strict mode with no `Any` types).

5. **Acceptance criteria gap**: The Coach repeatedly flagged missing criteria:
   - `pyproject.toml` ruff config
   - `pyproject.toml` mypy config (strict mode)
   - `mypy src/` passes with zero errors in strict mode
   - All type annotations complete — no `Any` types

### Changes Between Runs

The following task groups were implemented between Run 4 and Run 5:

1. **TASK-REV-F8BA** (Graphiti context fixes): `search()` → `search_()` API migration, circuit breaker resets, score attribution fix, namespace diagnostics
2. **TASK-GCF-001 through TASK-GCF-003**: System group prefixing fix, query error logging, dynamic group definitions
3. **TASK-VOPT-001 through TASK-VOPT-003**: vLLM optimisation tasks

## Review Scope

1. **Root cause**: ~~Why was TASK-FBP-007 routed to `task-work` mode in Run 5 vs `direct` mode in Run 4?~~ **Corrected**: Mode routing was identical (`direct` in both runs). The root cause is timeout budget exhaustion — TASK-FBP-006 consumed 110 SDK turns in Run 5 (vs 43 in Run 4), leaving insufficient budget for TASK-FBP-007.

2. **Timeout budget analysis**: Calculate the cumulative time consumed by Waves 1-4 and TASK-FBP-006, and determine if TASK-FBP-007 had sufficient remaining budget.

3. **Cancel scope investigation**: Trace the cancel scope chain to determine whether the cancellation comes from task timeout, wave timeout, or feature-level budget exhaustion.

4. **Acceptance criteria feasibility**: Assess whether the TASK-FBP-007 acceptance criteria (especially `mypy strict` with zero `Any` types) is achievable within the timeout constraints when using vLLM as the LLM backend.

5. **Regression attribution**: Determine if any of the TASK-REV-F8BA, TASK-GCF, or TASK-VOPT changes could have affected mode routing or timeout behaviour.

## Acceptance Criteria

- [x] Root cause of mode routing change identified — **Corrected**: no mode change occurred (`direct` in both runs); root cause is timeout budget exhaustion
- [ ] Timeout budget timeline reconstructed with timestamps
- [ ] Cancel scope source identified (task/wave/feature level)
- [ ] Recommendation for preventing recurrence
- [ ] Assessment of whether acceptance criteria need adjustment

## Related Files

- `docs/reviews/vllm-profiling/vllm_run_5.md` — Failed run output (560KB)
- `docs/reviews/vllm-profiling/vllm_run_4.md` — Previous successful run
- `tasks/backlog/graphiti-context-fixes/TASK-REV-F8BA-investigate-graphiti-zero-categories.md`
- `tasks/backlog/graphiti-context-fixes/TASK-GCF-004-run-seed-system-and-project.md`
- `tasks/backlog/vllm-optimisation/TASK-VOPT-004-full-run4.md`
- `guardkit/orchestrator/agent_invoker.py` — Mode routing logic
- `guardkit/orchestrator/autobuild.py` — Timeout budget management
- `guardkit/orchestrator/feature_orchestrator.py` — Wave execution and timeout allocation
