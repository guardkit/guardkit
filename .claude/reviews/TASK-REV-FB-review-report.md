# Code Quality Review Report: TASK-REV-FB

## Executive Summary

**Review Mode**: Code Quality
**Review Depth**: Standard
**Reviewer**: Code Quality Analysis Agent
**Task**: Analyze feature-build regression and max_turns parameter issue
**Date**: 2026-01-25

### Overall Assessment

| Metric | Score |
|--------|-------|
| Code Quality Score | 55/100 |
| Severity | CRITICAL |
| Risk Level | HIGH |
| Immediate Action Required | YES |

Two significant code quality issues were identified:

1. **Issue 1 (CRITICAL)**: Missing `recovery_count` field in `TaskExecutionResult` dataclass causes runtime crash
2. **Issue 2 (MEDIUM)**: Hardcoded `max_turns=50` in SDK invocation ignores CLI parameter

---

## Issue 1: Missing `recovery_count` Attribute (CRITICAL)

### Root Cause Analysis

**Problem**: The code accesses `r.recovery_count` on `TaskExecutionResult` objects at [feature_orchestrator.py:937](guardkit/orchestrator/feature_orchestrator.py#L937), but the `TaskExecutionResult` dataclass (defined at [feature_orchestrator.py:59-81](guardkit/orchestrator/feature_orchestrator.py#L59-L81)) does NOT include this field.

**Error Location**:
```python
# feature_orchestrator.py:937
recovered = sum(1 for r in wave_result.results if r.recovery_count > 0)
```

**TaskExecutionResult Definition** (lines 59-81):
```python
@dataclass
class TaskExecutionResult:
    task_id: str
    success: bool
    total_turns: int
    final_decision: str
    error: Optional[str] = None
    # NOTE: No recovery_count field!
```

**OrchestrationResult Definition** (autobuild.py:240-242):
```python
@dataclass
class OrchestrationResult:
    # ... other fields ...
    recovery_count: int = 0  # This exists here but not in TaskExecutionResult
```

### Regression Introduction

The regression was introduced by **TASK-PRH-003** (commit `56bf0e63`) which added `recovery_count` tracking to `OrchestrationResult` but failed to also add it to `TaskExecutionResult`.

The task description in [TASK-PRH-003.md](tasks/completed/TASK-PRH-003/TASK-PRH-003.md) explicitly mentions updating `feature_orchestrator.py` to "Calculate and pass recovery counts from wave results" (line 97), but the implementation only updated the consumption side (line 937) without updating the dataclass definition.

### Code Quality Violations

| Principle | Violation |
|-----------|-----------|
| **DRY** | Two parallel result dataclasses (`TaskExecutionResult` vs `OrchestrationResult`) represent similar concepts but have diverged |
| **LSP** | The feature orchestrator expects a field that doesn't exist on the actual result objects |
| **Coupling** | Tight coupling between modules without proper interface contracts |
| **Testing** | Missing integration test that would have caught this mismatch |

### Affected Code Paths

1. `_wave_phase()` in feature_orchestrator.py:937 - **CRASHES**
2. All `TaskExecutionResult` creation sites (lines 1011, 1033, 1268, 1278, 1345) - Missing field

---

## Issue 2: max_turns Parameter Override (MEDIUM)

### Root Cause Analysis

**Problem**: The CLI `--max-turns 10` parameter is correctly received by the `FeatureOrchestrator` but is NOT propagated to the SDK invocation layer. Instead, a hardcoded value of 50 is used.

**Evidence from logs**:
```
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-FHE (max_turns=10, ...)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FHE-001] Max turns: 50
```

### Parameter Flow Analysis

```
CLI (--max-turns 10)
  └── feature_orchestrator.py (max_turns=10) ✓
       └── AutoBuildOrchestrator(max_turns=10) ✓
            └── AgentInvoker() - NO max_turns_per_agent passed ✗
                 └── _invoke_via_task_work_delegation()
                      └── ClaudeAgentOptions(max_turns=50) ← HARDCODED
```

**Hardcoded Location**: [agent_invoker.py:2260](guardkit/orchestrator/agent_invoker.py#L2260)
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=50,  # HARDCODED - ignores CLI parameter
    setting_sources=["user", "project"],
)
```

### AgentInvoker Initialization Gap

When `AgentInvoker` is instantiated in [autobuild.py:712-717](guardkit/orchestrator/autobuild.py#L712-L717), the `max_turns_per_agent` parameter is NOT passed:

```python
self._agent_invoker = AgentInvoker(
    worktree_path=worktree.path,
    development_mode=self.development_mode,
    sdk_timeout_seconds=self.sdk_timeout,
    use_task_work_delegation=True,
    # NOTE: max_turns_per_agent is NOT passed, defaults to 30
)
```

### Code Quality Violations

| Principle | Violation |
|-----------|-----------|
| **Single Source of Truth** | Configuration value duplicated/hardcoded instead of flowing from CLI |
| **Open/Closed** | Changing max_turns requires modifying internal code |
| **Testability** | Hardcoded value makes testing different configurations impossible |

---

## Recommendations

### Recommendation 1: Add recovery_count to TaskExecutionResult (CRITICAL)

**Priority**: P0 - Immediate
**Effort**: Low (< 1 hour)
**Risk**: Low

Add the missing field to the dataclass:

```python
@dataclass
class TaskExecutionResult:
    task_id: str
    success: bool
    total_turns: int
    final_decision: str
    error: Optional[str] = None
    recovery_count: int = 0  # ADD THIS
```

Update all creation sites (lines 1011, 1033, 1268, 1278, 1345) to pass `recovery_count`.

### Recommendation 2: Propagate max_turns through parameter chain (MEDIUM)

**Priority**: P1 - High
**Effort**: Medium (2-4 hours)
**Risk**: Low

1. Pass `max_turns_per_agent` when creating `AgentInvoker`:
   ```python
   self._agent_invoker = AgentInvoker(
       worktree_path=worktree.path,
       max_turns_per_agent=self.max_turns,  # ADD THIS
       development_mode=self.development_mode,
       sdk_timeout_seconds=self.sdk_timeout,
       use_task_work_delegation=True,
   )
   ```

2. Use `self.max_turns_per_agent` in `_invoke_via_task_work_delegation`:
   ```python
   options = ClaudeAgentOptions(
       ...
       max_turns=self.max_turns_per_agent,  # USE INSTANCE VARIABLE
   )
   ```

### Recommendation 3: Consolidate Result Dataclasses (FUTURE)

**Priority**: P2 - Medium
**Effort**: High (1-2 days)
**Risk**: Medium

Consider consolidating `TaskExecutionResult` and `OrchestrationResult` into a single shared result type to prevent future divergence. This would:
- Eliminate DRY violations
- Reduce maintenance burden
- Prevent similar regressions

### Recommendation 4: Add Integration Tests (FUTURE)

**Priority**: P2 - Medium
**Effort**: Medium (4-8 hours)
**Risk**: Low

Add integration tests that:
- Verify result objects have all expected fields
- Test max_turns parameter flows end-to-end
- Catch dataclass field mismatches early

---

## Files Requiring Changes

| File | Change Required | Priority |
|------|-----------------|----------|
| [guardkit/orchestrator/feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) | Add `recovery_count: int = 0` to `TaskExecutionResult` dataclass | P0 |
| [guardkit/orchestrator/feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) | Pass `recovery_count` in all `TaskExecutionResult` creation sites | P0 |
| [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) | Pass `max_turns` to `AgentInvoker` initialization | P1 |
| [guardkit/orchestrator/agent_invoker.py](guardkit/orchestrator/agent_invoker.py) | Use `self.max_turns_per_agent` instead of hardcoded 50 | P1 |

---

## Test Plan

1. **Unit Tests**:
   - Test `TaskExecutionResult` has `recovery_count` field
   - Test `AgentInvoker` respects `max_turns_per_agent` configuration

2. **Integration Tests**:
   - Run `/feature-build` with `--max-turns 10` and verify SDK uses 10
   - Run feature with state recovery and verify `recovery_count > 0`

3. **Regression Tests**:
   - Run the exact scenario from `orchestrator_error.md` after fix

---

## Evidence

### Error Output
- [docs/reviews/feature-build/orchestrator_error.md](docs/reviews/feature-build/orchestrator_error.md)

### Successful Previous Run
- [docs/reviews/feature-build/finally_success.md](docs/reviews/feature-build/finally_success.md) (referenced in task but not read)

### Related Tasks
- TASK-PRH-003: Introduced `recovery_count` tracking without updating `TaskExecutionResult`

---

## Conclusion

Two distinct code quality issues are causing the feature-build regression:

1. A **missing dataclass field** causes an immediate runtime crash. This is a straightforward fix requiring the addition of `recovery_count` to `TaskExecutionResult` and passing it from all creation sites.

2. A **parameter propagation gap** causes the CLI `--max-turns` to be ignored. The hardcoded value of 50 in `agent_invoker.py` should be replaced with a properly propagated configuration value.

Both issues stem from incomplete changes during feature implementation and highlight the need for better integration testing of the parameter/data flow paths.

**Recommended Next Steps**:
1. Fix Issue 1 immediately (P0) - feature-build is currently broken
2. Fix Issue 2 in follow-up (P1) - max_turns override is confusing but not blocking
3. Consider dataclass consolidation (P2) - prevent future divergence
