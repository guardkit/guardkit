# Review Report: TASK-REV-FE8A - Feature-Build Duration Analysis

## Executive Summary

This architectural review analyzes the feature-build duration after TASK-FB-FIX-013 and TASK-FB-FIX-014 were implemented, focusing on the status of recommended fixes (FB-FIX-015, 016, 017) from the previous TASK-REV-FB11 review.

**Key Findings**:

1. **TASK-FB-FIX-015, 016, 017 were NOT implemented** - They exist as task files in `tasks/backlog/feature-build-fixes/` but the code changes were not applied
2. **The 90-minute design phase duration persists** - Manual test confirmed "Brewed for 1h 29m 27s"
3. **Feature-build still times out** - Even with 60-minute (3600s) SDK timeout, the pre-loop design phase exceeds the limit
4. **Root cause confirmed** - `enable_pre_loop` still defaults to `True` for feature-build (line 910-911 in `feature_orchestrator.py`)
5. **SDK timeout still at 600s** - Both locations (`agent_invoker.py:45` and `task_work_interface.py:48`) show the old 600s default

**Architecture Score**: 65/100 (Critical fix backlog not addressed)

**Recommendation**: **Implement FB-FIX-015, 016, 017 immediately** to unblock feature-build workflow.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: ~30 minutes
- **Reviewer**: Task Review Command
- **Task ID**: TASK-REV-FE8A

---

## Findings

### Finding 1: FB-FIX Tasks Created But Not Implemented

**Status**: CRITICAL

The previous review (TASK-REV-FB11) recommended three fix tasks. Investigation shows:

| Task ID | Title | Status | Code Changed? |
|---------|-------|--------|---------------|
| TASK-FB-FIX-015 | Default `enable_pre_loop=false` for feature-build | backlog | **NO** |
| TASK-FB-FIX-016 | Increase default SDK timeout to 1800s | backlog | **NO** |
| TASK-FB-FIX-017 | Update CLAUDE.md with pre-loop guidance | backlog | **NO** |

**Evidence**:

```python
# guardkit/orchestrator/feature_orchestrator.py (lines 909-911)
# STILL shows old default:
logger.debug("enable_pre_loop using default: True")
return True

# guardkit/orchestrator/agent_invoker.py:45
# STILL shows 600s default:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))

# guardkit/orchestrator/quality_gates/task_work_interface.py:48
# STILL shows 600s default:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))
```

### Finding 2: Feature-Build Timeout Confirmed

**Status**: CRITICAL

The test output from `docs/reviews/feature-build/test_task_fix_fb013+fb014.md` shows:

```
Duration: 70m 6s
ERROR:guardkit.orchestrator.quality_gates.task_work_interface:SDK timeout after 3600s
Error: SDK timeout after 3600s during design phase
```

Even with a manually-specified 1800s (then 3600s) SDK timeout, the design phase exceeded the limit.

### Finding 3: Manual Design Phase Takes 89 Minutes

**Status**: CONFIRMED

From `docs/reviews/feature-build/stand_alone_manual_design.md`:

```
Agent Invocations Summary:
Total Duration: ~2 minutes (agent execution time)

✻ Brewed for 1h 29m 27s (total session time)
```

The 89-minute session time vs 2-minute agent time confirms the previous analysis:
- **97.8%** of time is NOT agent invocations
- Time is spent on token generation, tool execution, context loading, and content generation (1200+ lines of markdown)

### Finding 4: Pre-Loop Still Enabled by Default for Feature-Build

**Status**: CRITICAL

The code at `feature_orchestrator.py:950` shows:

```python
effective_enable_pre_loop = self._resolve_enable_pre_loop(feature, task_data)
logger.info(f"Task {task.id}: enable_pre_loop={effective_enable_pre_loop}")
```

And the log output confirms:

```
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-INFRA-001: enable_pre_loop=True
```

This means every task in a feature-build runs the full 60-90 minute design phase, even though feature tasks already have detailed specs from `/feature-plan`.

---

## Root Cause Analysis

### Why Are the Fixes Not Implemented?

1. **Task files created but not executed** - The tasks exist in `tasks/backlog/` but were never worked on
2. **No automated task execution** - Tasks require manual `/task-work` execution
3. **Potential prioritization gap** - Other fixes (FB-FIX-013, FB-FIX-014) were prioritized over performance optimization

### Why Does Feature-Build Timeout?

| Factor | Contribution | Impact |
|--------|--------------|--------|
| Pre-loop design phase | 60-90 minutes | **Primary cause** |
| SDK timeout default (600s) | Insufficient | **Exacerbates** |
| Per-task overhead | Cumulative | For 7-task feature: 7 × 90min = 10.5 hours theoretical |

The current architecture creates a fundamental mismatch:
- Feature tasks from `/feature-plan` already have detailed acceptance criteria
- The pre-loop design phase duplicates this work
- Each task adds 60-90 minutes of redundant planning

---

## Architecture Assessment

### SOLID/DRY/YAGNI Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| **Single Responsibility** | 8/10 | Clear separation: pre-loop → design, loop → implementation |
| **Open/Closed** | 7/10 | `enable_pre_loop` flag exists but defaults incorrectly |
| **Liskov Substitution** | 8/10 | TaskWorkInterface properly substitutes |
| **Interface Segregation** | 7/10 | Good interface design |
| **Dependency Inversion** | 8/10 | Proper use of interfaces |
| **DRY** | 4/10 | Feature-build duplicates feature-plan design work |
| **YAGNI** | 3/10 | Pre-loop generates extensive artifacts not needed for feature tasks |

**Overall Architecture Score**: 65/100

### Technical Debt

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| Pre-loop defaults to True for feature-build | High | 30 min | Blocks all feature builds |
| SDK timeout too low | High | 15 min | Causes premature failures |
| Documentation gap | Medium | 30 min | User confusion |

---

## Recommendations

### Recommendation 1: Implement FB-FIX-015 (CRITICAL)

**Priority**: Immediate

Change `feature_orchestrator.py:910-911`:

```python
# FROM:
logger.debug("enable_pre_loop using default: True")
return True

# TO:
logger.debug("enable_pre_loop using default for feature-build: False")
return False  # Feature tasks have detailed specs from feature-plan
```

**Expected Impact**: Eliminates 60-90 minute overhead per task for feature-build.

### Recommendation 2: Implement FB-FIX-016 (HIGH)

**Priority**: Same day as FB-FIX-015

Change both files:
- `agent_invoker.py:45`: 600 → 1800
- `task_work_interface.py:48`: 600 → 1800

**Expected Impact**: Provides adequate timeout for loop phase without pre-loop.

### Recommendation 3: Implement FB-FIX-017 (MEDIUM)

**Priority**: After FB-FIX-015 and FB-FIX-016

Add documentation to CLAUDE.md explaining:
- Default behavior differences between feature-build and task-build
- When to use `--enable-pre-loop` vs `--no-pre-loop`
- Timeout recommendations table

### Recommendation 4: Re-test Feature-Build After Fixes

After implementing FB-FIX-015 and FB-FIX-016:

```bash
# Test with default settings (pre-loop disabled for feature-build)
guardkit autobuild feature FEAT-3DEB --max-turns 5 --verbose

# Expected: ~30 minutes per task (loop phase only)
# Expected: Total for 7 tasks ≈ 3.5 hours (vs 10.5 hours with pre-loop)
```

---

## Decision Options

| Option | Description | Effort | Risk | Recommendation |
|--------|-------------|--------|------|----------------|
| **A. Implement all three fixes** | FB-FIX-015, 016, 017 | 2 hours | Low | **RECOMMENDED** |
| B. Only FB-FIX-015 | Skip pre-loop default | 30 min | Medium | If time-constrained |
| C. Only timeout increase | FB-FIX-016 | 15 min | High | Does not address root cause |
| D. No action | Accept current behavior | 0 | N/A | **NOT RECOMMENDED** |

---

## Test Plan After Implementation

### Unit Tests

```python
def test_feature_orchestrator_defaults_preloop_false():
    """FB-FIX-015: Feature-build defaults to enable_pre_loop=False."""
    orchestrator = FeatureOrchestrator(repo_root=Path.cwd())
    result = orchestrator._resolve_enable_pre_loop(feature, task_data)
    assert result is False

def test_sdk_timeout_default_1800():
    """FB-FIX-016: Default SDK timeout is 1800s."""
    from guardkit.orchestrator.agent_invoker import DEFAULT_SDK_TIMEOUT
    assert DEFAULT_SDK_TIMEOUT == 1800
```

### Integration Test

```bash
# Feature-build should complete in reasonable time
guardkit autobuild feature FEAT-TEST --max-turns 1 --verbose

# Verify pre-loop is skipped
# Should see: "Phase 2 (Pre-Loop): Skipped (enable_pre_loop=False)"
```

### Success Criteria

- [ ] Feature-build completes first task in <30 minutes
- [ ] Log shows `enable_pre_loop=False` for feature tasks
- [ ] No SDK timeout errors with default settings
- [ ] Documentation reflects new defaults

---

## Appendix

### A. Task File Locations

- TASK-FB-FIX-015: `tasks/backlog/feature-build-fixes/TASK-FB-FIX-015-default-no-preloop.md`
- TASK-FB-FIX-016: `tasks/backlog/feature-build-fixes/TASK-FB-FIX-016-increase-sdk-timeout.md`
- TASK-FB-FIX-017: `tasks/backlog/feature-build-fixes/TASK-FB-FIX-017-preloop-documentation.md`

### B. Evidence Files

- Feature-build test: `docs/reviews/feature-build/test_task_fix_fb013+fb014.md`
- Manual design-only test: `docs/reviews/feature-build/stand_alone_manual_design.md`
- Previous analysis: `.claude/reviews/TASK-REV-FB11-review-report.md`

### C. Related Issues

| Review | Finding | Status |
|--------|---------|--------|
| TASK-REV-FB11 | Recommended FB-FIX-015/016/017 | Tasks created, not implemented |
| TASK-REV-FB10 | Implementation phase failures | Fixed (FB-FIX-013, FB-FIX-014) |
| TASK-REV-FB08 | SDK timeout not propagating | Fixed (FB-FIX-009) |
| **TASK-REV-FE8A** | **Duration still problematic** | **This review** |

---

*Review completed: 2026-01-13*
*Reviewer: /task-review --mode=architectural --depth=standard*
*Duration: ~30 minutes*
