# Implementation Guide: AutoBuild Orchestrator Failure Fixes (FEAT-CD4C)

## Parent Review

**TASK-REV-A17A** — Analyse AutoBuild feature failures in run_1
Report: `.claude/reviews/TASK-REV-A17A-review-report.md`

## Wave Breakdown

### Wave 1: Critical Fixes (3 tasks, parallel)

All three Wave 1 tasks are independent and can run in parallel. They address the two CRITICAL findings from the review.

| Task | Title | Complexity | Mode | Files Affected |
|------|-------|-----------|------|----------------|
| TASK-ABFIX-001 | Add `enhancement` alias | 2 | task-work | coach_validator.py, autobuild.py |
| TASK-ABFIX-002 | Validate task_type at feature load | 4 | task-work | feature_loader.py, task_types.py |
| TASK-ABFIX-003 | Config error fast-exit | 5 | task-work | coach_validator.py, autobuild.py |

**File conflict analysis**: TASK-ABFIX-001 and TASK-ABFIX-003 both modify `coach_validator.py` but in different sections (alias table vs validation result). Safe for parallel execution.

**Expected outcome**: After Wave 1, tasks with `task_type: enhancement` will either be validated early (ABFIX-002) or resolved correctly via alias (ABFIX-001). Configuration errors will trigger immediate exit (ABFIX-003) instead of 3-turn stalls.

### Wave 2: Timeout Architecture + Parallel Isolation (3 tasks, parallel)

| Task | Title | Complexity | Depends On | Files Affected |
|------|-------|-----------|-----------|----------------|
| TASK-ABFIX-004 | Per-turn timeout budget | 6 | ABFIX-001 | feature_orchestrator.py, autobuild.py, agent_invoker.py |
| TASK-ABFIX-005 | Coach test isolation | 6 | ABFIX-001 | coach_validator.py, autobuild.py, feature_orchestrator.py |
| TASK-ABFIX-006 | Timeout logging | 3 | ABFIX-004 | feature_orchestrator.py, autobuild.py, agent_invoker.py |

**File conflict analysis**: TASK-ABFIX-004 and TASK-ABFIX-005 overlap on `autobuild.py` and `feature_orchestrator.py` but modify different code paths (timeout logic vs Coach invocation). TASK-ABFIX-006 depends on ABFIX-004's timeout changes but operates on logging only. All three can run in parallel with Conductor.

**Expected outcome**: Multi-turn tasks get fair timeout allocation. Coach independent tests are isolated from parallel worktree mutations. Timeout events clearly log which layer fired.

### Wave 3: CLI + Cleanup (2 tasks, parallel)

| Task | Title | Complexity | Depends On | Files Affected |
|------|-------|-----------|-----------|----------------|
| TASK-ABFIX-007 | Feature validate CLI | 4 | ABFIX-002 | cli/, feature_loader.py |
| TASK-ABFIX-008 | Doc level + bootstrap fixes | 3 | — | agent_invoker.py, environment_bootstrap.py |

**File conflict analysis**: No overlapping files. Fully parallel.

**Expected outcome**: Pre-flight validation available via CLI. Reduced noise from false positive doc level warnings and fixture bootstrap failures.

### Wave 4: Integration Testing (1 task, serial)

| Task | Title | Complexity | Depends On |
|------|-------|-----------|-----------|
| TASK-ABFIX-009 | Integration tests | 6 | ABFIX-003, ABFIX-004, ABFIX-005 |

**Expected outcome**: End-to-end verification that the integration seams work correctly after all fixes.

## Execution Strategy

### Recommended: Conductor Parallel Execution

```bash
# Wave 1 (3 parallel workspaces)
conductor run TASK-ABFIX-001 --workspace abfix-wave1-1
conductor run TASK-ABFIX-002 --workspace abfix-wave1-2
conductor run TASK-ABFIX-003 --workspace abfix-wave1-3

# Wave 2 (3 parallel workspaces, after Wave 1 merge)
conductor run TASK-ABFIX-004 --workspace abfix-wave2-1
conductor run TASK-ABFIX-005 --workspace abfix-wave2-2
conductor run TASK-ABFIX-006 --workspace abfix-wave2-3

# Wave 3 (2 parallel workspaces, after Wave 2 merge)
conductor run TASK-ABFIX-007 --workspace abfix-wave3-1
conductor run TASK-ABFIX-008 --workspace abfix-wave3-2

# Wave 4 (serial, after Wave 3 merge)
conductor run TASK-ABFIX-009 --workspace abfix-wave4-1
```

### Alternative: AutoBuild Feature Build

```bash
guardkit autobuild feature FEAT-CD4C --resume
```

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| ABFIX-004 changes timeout bookkeeping in critical path | Per-turn budget is strictly additive — extends, never reduces timeout |
| ABFIX-005 introduces test isolation mechanism | Fallback to existing behavior if isolation fails |
| ABFIX-003 adds new exit path to autobuild loop | Isolated to `is_configuration_error=True` path; normal feedback loop unchanged |
| Integration tests (ABFIX-009) depend on 3 tasks | Wave 4 runs after all dependencies complete |
