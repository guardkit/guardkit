# Review Report: TASK-REV-FB07

## Executive Summary

**Root Cause Identified**: The pre_loop validation checks for plan existence using a **relative path** without resolving it against the worktree directory. When `/task-work --design-only` saves the plan to `docs/state/{task_id}/implementation_plan.md` inside the worktree, the pre_loop validation fails because it checks the path relative to the **main orchestrator's working directory**, not the worktree.

**Architecture Score**: 62/100 (Requires Fix)

| Principle | Score | Assessment |
|-----------|-------|------------|
| SOLID | 58/100 | Path resolution responsibility scattered across modules |
| DRY | 55/100 | Path handling duplicated in pre_loop, task_work_interface, paths.py |
| YAGNI | 75/100 | Appropriate complexity for the problem domain |

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: ~4 hours
- **Files Analyzed**: 12 core implementation files + 6 previous review reports
- **Reviewer**: Claude Opus 4.5 (architectural-reviewer agent)

## Problem Statement

After 6 previous reviews and 6+ fixes, feature-build still fails:

```
SDK completed: turns=24  <-- PROGRESS! Skill IS loading and executing
ERROR: Quality gate 'plan_validation' blocked: Implementation plan not found at
docs/state/TASK-INFRA-001-core-configuration/implementation_plan.md
```

**Key Progress**: The SDK now executes 24 turns (vs 1 before FB-FIX-006), confirming the skill is loading. The issue is now **path validation**, not SDK configuration.

## Root Cause Analysis

### The Path Resolution Bug

**Location**: `guardkit/orchestrator/quality_gates/pre_loop.py:249-250`

```python
# CURRENT (BROKEN):
plan_file = Path(plan_path)  # plan_path is relative: "docs/state/TASK-XXX/implementation_plan.md"
if not plan_file.exists():   # Checks relative to orchestrator CWD, NOT worktree
    raise QualityGateBlocked(...)
```

**Why It Fails**:

1. SDK invokes `/task-work --design-only` with `cwd=worktree_path`
2. `plan_persistence.py:save_plan()` saves to `Path("docs/state") / task_id / "implementation_plan.md"` (relative path)
3. Plan is saved at: `{worktree}/docs/state/TASK-XXX/implementation_plan.md`
4. SDK output parsing extracts relative path: `docs/state/TASK-XXX/implementation_plan.md`
5. Pre_loop validates: `Path("docs/state/TASK-XXX/implementation_plan.md").exists()`
6. **FAILS** because this checks relative to main repo, not worktree

### Evidence Chain

| Step | Expected | Actual | Gap |
|------|----------|--------|-----|
| SDK cwd | Set to worktree | ✅ Set correctly | None |
| Plan save | In worktree | ✅ Saved in worktree | None |
| Path extraction | Relative path | ✅ Extracts relative | None |
| Path validation | Resolve to worktree | ❌ Resolves to main repo | **ROOT CAUSE** |

### Code Flow Analysis

```
AutoBuildOrchestrator (cwd: /main/repo)
    │
    ├── Creates worktree: /main/repo/.guardkit/worktrees/TASK-XXX
    │
    └── PreLoopQualityGates.execute()
            │
            └── TaskWorkInterface.execute_design_phase()
                    │
                    ├── SDK invoked with cwd=/main/repo/.guardkit/worktrees/TASK-XXX
                    │
                    └── /task-work --design-only executes
                            │
                            └── plan_persistence.save_plan()
                                    │
                                    └── Creates: docs/state/TASK-XXX/implementation_plan.md
                                        (relative to SDK cwd = worktree)

                                        ACTUAL PATH: /main/repo/.guardkit/worktrees/TASK-XXX/
                                                     docs/state/TASK-XXX/implementation_plan.md
                    │
                    └── SDK returns: plan_path = "docs/state/TASK-XXX/implementation_plan.md"
            │
            └── _extract_pre_loop_results()
                    │
                    └── plan_file = Path(plan_path)  # Still relative!
                    └── plan_file.exists()           # Checks /main/repo/docs/state/...
                                                     # NOT /main/repo/.guardkit/worktrees/...
                    └── ❌ FAILS - file not found
```

## Hypothesis Validation

| # | Hypothesis | Status | Evidence |
|---|------------|--------|----------|
| H1 | Plan saved to different location than expected | ✅ CONFIRMED | Plan saved in worktree, validation checks main repo |
| H2 | Plan saved with different filename | ❌ Ruled out | Filename is correct |
| H3 | /task-work skill doesn't save plan in worktree context | ❌ Ruled out | SDK cwd is set correctly |
| H4 | SDK output not being parsed correctly for plan path | ⚠️ Partial | Parsing works but returns relative path |
| H5 | Plan generation phase skipped or failed silently | ❌ Ruled out | 24 turns confirms phases ran |
| H6 | Worktree context missing necessary files for skill | ❌ Ruled out | Task file exists, skill executed |

## The Fix

### Option A: Fix Path Resolution in Pre_Loop (RECOMMENDED)

**Location**: `guardkit/orchestrator/quality_gates/pre_loop.py:249-259`

```python
# BEFORE (broken):
plan_file = Path(plan_path)
if not plan_file.exists():
    raise QualityGateBlocked(...)

# AFTER (fixed):
plan_file = Path(plan_path)
if not plan_file.is_absolute():
    # Resolve relative paths against worktree
    plan_file = self.worktree_path / plan_file
if not plan_file.exists():
    raise QualityGateBlocked(...)
```

**Effort**: Low (30 minutes)
**Risk**: Low
**Impact**: Critical - Fixes the root cause

### Option B: Return Absolute Paths from SDK Parsing

**Location**: `guardkit/orchestrator/quality_gates/task_work_interface.py:458-470`

Modify `_parse_sdk_output()` to always return absolute paths:

```python
if result["plan_path"]:
    plan_path = Path(result["plan_path"])
    if not plan_path.is_absolute():
        plan_path = self.worktree_path / plan_path
    result["plan_path"] = str(plan_path)  # Always absolute
```

**Note**: This is already partially implemented at lines 474-477 but only for loading content, not for the returned path.

**Effort**: Low (30 minutes)
**Risk**: Low
**Impact**: Critical - Alternative fix location

### Option C: Use TaskArtifactPaths Consistently

Ensure all code uses `TaskArtifactPaths.find_implementation_plan()` which already handles worktree paths correctly:

```python
# In pre_loop.py
from guardkit.orchestrator.paths import TaskArtifactPaths

# Instead of trusting result.plan_path, verify independently
plan_file = TaskArtifactPaths.find_implementation_plan(task_id, self.worktree_path)
if not plan_file:
    raise QualityGateBlocked(...)
```

**Effort**: Low (30 minutes)
**Risk**: Low
**Impact**: High - More robust, uses centralized path logic

## Recommended Implementation

**Single Fix Task**: Combine Options A and C for maximum robustness.

```python
# guardkit/orchestrator/quality_gates/pre_loop.py

def _extract_pre_loop_results(
    self,
    task_id: str,
    result: DesignPhaseResult,
) -> PreLoopResult:
    """Extract outputs needed for Player-Coach loop."""

    # Primary: Use SDK-reported path (may be relative)
    plan_path = result.plan_path

    # Resolve relative paths against worktree
    if plan_path:
        plan_file = Path(plan_path)
        if not plan_file.is_absolute():
            plan_file = self.worktree_path / plan_file
        plan_path = str(plan_file)

    # Fallback: Search all known locations if SDK path not found
    if not plan_path or not Path(plan_path).exists():
        from guardkit.orchestrator.paths import TaskArtifactPaths
        found_plan = TaskArtifactPaths.find_implementation_plan(
            task_id, self.worktree_path
        )
        if found_plan:
            plan_path = str(found_plan)
            logger.info(f"Found plan at fallback location: {plan_path}")

    # Final validation
    if not plan_path:
        raise QualityGateBlocked(
            reason=f"Design phase did not return plan path for {task_id}...",
            gate_name="plan_generation",
            details={"task_id": task_id, "plan_path": None},
        )

    plan_file = Path(plan_path)
    if not plan_file.exists():
        raise QualityGateBlocked(
            reason=f"Implementation plan not found at {plan_path}...",
            gate_name="plan_validation",
            details={"task_id": task_id, "plan_path": plan_path},
        )

    # Continue with rest of method...
```

## Why Previous Fixes Didn't Work

| Fix | What It Fixed | Why It Wasn't Enough |
|-----|---------------|----------------------|
| FB-FIX-001 | Replace subprocess with SDK | SDK invocation worked, but path issue remained |
| FB-FIX-002 | Add plan existence validation | Added validation but didn't fix path resolution |
| FB-FIX-003 | Centralize path logic | Created TaskArtifactPaths but pre_loop doesn't use it for validation |
| FB-FIX-004 | Pre-loop validation with plan check | Validation exists but uses wrong path context |
| FB-FIX-005 | ContentBlock extraction | Fixed output parsing but path was already correct |
| FB-FIX-006 | Add "user" to setting_sources | Fixed skill loading (24 turns!) but path resolution still broken |

**Pattern**: Each fix addressed a real issue, but all missed the path resolution bug in pre_loop validation.

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `guardkit/orchestrator/quality_gates/pre_loop.py` | Fix path resolution in `_extract_pre_loop_results()` | **P0 CRITICAL** |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Ensure `_parse_sdk_output()` returns absolute paths | P1 |
| `tests/unit/test_pre_loop_delegation.py` | Add test for relative path handling | P1 |

## Test Strategy

### Unit Tests

```python
def test_pre_loop_resolves_relative_plan_path():
    """Verify relative plan paths are resolved against worktree."""
    worktree = Path("/tmp/test-worktree")
    worktree.mkdir(parents=True, exist_ok=True)

    # Create plan in worktree
    plan_dir = worktree / "docs/state/TASK-001"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "implementation_plan.md").write_text("# Plan")

    # Mock SDK returning relative path
    mock_result = DesignPhaseResult(
        plan_path="docs/state/TASK-001/implementation_plan.md",  # Relative!
        ...
    )

    gates = PreLoopQualityGates(str(worktree))
    result = gates._extract_pre_loop_results("TASK-001", mock_result)

    # Should resolve to absolute path in worktree
    assert Path(result.plan_path).is_absolute()
    assert Path(result.plan_path).exists()
```

### Integration Test

```python
async def test_feature_build_creates_and_finds_plan():
    """End-to-end test that plan created in worktree is found."""
    # Run feature-build on test task
    # Verify plan exists in worktree
    # Verify pre_loop validation passes
```

## Decision Options

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| [A]ccept | - | - | Archive review for reference |
| [R]evise | - | - | Request additional analysis |
| [I]mplement | Low | Low | **RECOMMENDED** - Fix is straightforward |
| [C]ancel | - | - | Discard review |

**Recommended**: **[I]mplement** - Create single implementation task:

**TASK-FB-FIX-007: Fix Pre-Loop Path Resolution**
- Add worktree-aware path resolution in `_extract_pre_loop_results()`
- Use `TaskArtifactPaths.find_implementation_plan()` as fallback
- Add unit test for relative path handling
- Verify with integration test

**Estimated Effort**: 1-2 hours
**Risk**: Low - isolated change with clear test path
**Impact**: Critical - Unblocks all feature-build functionality

## Appendix A: Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Path validation (broken) | `guardkit/orchestrator/quality_gates/pre_loop.py` | 249-259 |
| SDK output parsing | `guardkit/orchestrator/quality_gates/task_work_interface.py` | 411-536 |
| Plan persistence | `installer/core/commands/lib/plan_persistence.py` | 46-126 |
| Centralized paths | `guardkit/orchestrator/paths.py` | Full file |

## Appendix B: Previous Reviews Referenced

1. TASK-REV-FB01 - Initial architecture review (approved)
2. TASK-REV-fb02 - Delegation disabled (fixed)
3. TASK-REV-fb03 - CLI command doesn't exist (SDK approach)
4. TASK-REV-FB04 - Mock data returned (SDK integration)
5. TASK-REV-FB05 - Message parsing bug (ContentBlock)
6. TASK-REV-FB06 - setting_sources fix (24 turns now!)

## Appendix C: Timeline of Progress

| Date | Fix | Result |
|------|-----|--------|
| Before FB-FIX-006 | SDK completed: 1 turn | Skill not loading |
| After FB-FIX-006 | SDK completed: 24 turns | Skill loading, plan created |
| Current | Plan validation fails | Path resolution bug |

---

**Review Completed**: 2026-01-11
**Reviewer**: Claude Opus 4.5 (architectural-reviewer agent)
**Status**: REVIEW_COMPLETE
