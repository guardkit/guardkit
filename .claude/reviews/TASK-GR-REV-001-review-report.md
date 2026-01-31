# Review Report: TASK-GR-REV-001

## Executive Summary

The AutoBuild failure for TASK-GR-PRE-003-A stems from **three cascading root causes**:

1. **Missing `manual` Mode Handling**: The agent_invoker only routes `direct` mode, treating `manual` as default `task-work`
2. **Feature Orchestrator Doesn't Route by Mode**: All tasks dispatch to AutoBuildOrchestrator regardless of implementation_mode
3. **State Bridge Stub Creation Gating**: Only creates stubs for `task-work` mode, not `manual`

The failure pattern (25 identical retries) demonstrates **missing error classification** - unrecoverable errors aren't distinguished from recoverable ones.

## Review Details

- **Mode**: Architectural Review (Revised - Deep Dive)
- **Depth**: Comprehensive
- **Duration**: ~45 minutes
- **Reviewer**: Claude (architectural-reviewer)

---

## Deep Dive 1: Race Condition Timing in Parallel Execution

### Finding: autobuild_state Written to Wrong Location

**Timeline of Events** (Wave 3 with 5 parallel tasks):

```
T+0.0s: asyncio.gather() starts all 5 tasks in parallel
T+0.1s: Each task calls TaskLoader.load_task(task_id, repo_root=self.repo_root)
        → Loads from MAIN REPO: tasks/backlog/graphiti-refinement-mvp/*.md
T+0.2s: Each task calls TaskStateBridge(task_id, repo_root=worktree.path)
        → Looks for task in WORKTREE: .guardkit/worktrees/FEAT-GR-MVP/tasks/

T+0.3s: Task files WERE copied to worktree by _copy_task_files()
        BUT: Original task files don't have autobuild_state yet

T+0.4s: state_bridge.verify_implementation_plan_exists() is called
        → Checks _create_stub_implementation_plan() eligibility:
           • has_autobuild_config = False (not set in task)
           • has_autobuild_state = False (not written yet!)
           • is_task_work_mode = False (mode is "manual")
        → Result: should_create_stub = False

T+0.5s: PlanNotFoundError raised
T+0.6s: Error caught, marked as "Unexpected error", retry triggered
T+0.7s: autobuild.py saves state to task file (autobuild_state added NOW)
        BUT: This write goes to WORKTREE task file, not main repo
        AND: state_bridge already failed before this write happened

[Repeat 24 more times]
```

**The Race Condition**:
1. `autobuild_state` is written AFTER `verify_implementation_plan_exists()` fails
2. Task loading happens from main repo, but state bridge uses worktree
3. Stub creation checks `autobuild_state` but it doesn't exist until AFTER the error

**Evidence from Build Log**:
```
INFO:state_bridge.TASK-GR-PRE-003-A:Task TASK-GR-PRE-003-A transitioned to design_approved
  ✗ Player failed: Unexpected error: Implementation plan not found for TASK-GR-PRE-003-A
INFO:state_bridge.TASK-GR-PRE-002-A:Created stub implementation plan...
```

Note: 002-A gets stub created (has autobuild context), but 003-A fails (manual mode, no autobuild context yet).

### Recommendation 1A: Pass AutoBuild Context to State Bridge

```python
# In agent_invoker.py, invoke_player():
def _ensure_design_approved_state(self, task_id: str, in_autobuild_context: bool = True) -> None:
    bridge = TaskStateBridge(task_id, self.worktree_path, in_autobuild_context=in_autobuild_context)
    bridge.ensure_design_approved_state()

# In state_bridge.py:
class TaskStateBridge:
    def __init__(self, task_id: str, repo_root: Path, in_autobuild_context: bool = False):
        self.in_autobuild_context = in_autobuild_context

    def _create_stub_implementation_plan(self) -> Optional[Path]:
        # Create stub if we're in AutoBuild context, regardless of other flags
        should_create_stub = (
            has_autobuild_config or
            has_autobuild_state or
            is_task_work_mode or
            self.in_autobuild_context  # NEW: Always true when called from AutoBuild
        )
```

---

## Deep Dive 2: Error Recovery Patterns in AutoBuild

### Current Error Classification

| Error Type | Current Handling | Should Be |
|------------|-----------------|-----------|
| `PlanNotFoundError` | Retry (generic Exception) | **Fail Fast** |
| `TaskNotFoundError` | Retry | Fail Fast |
| `StateValidationError` | Retry | Fail Fast |
| `SDKTimeoutError` | Retry | **Retry (correct)** |
| `AgentInvocationError` | Retry | Retry (correct) |

### Finding: No Error Classification in Loop Phase

**Location**: [autobuild.py:1923-1933](guardkit/orchestrator/autobuild.py#L1923-L1933)

```python
except Exception as e:
    logger.error(f"Player invocation failed: {e}", exc_info=True)
    return AgentInvocationResult(
        success=False,
        error=f"Unexpected error: {str(e)}",  # No classification!
    )
```

The error is wrapped in a generic message, losing the ability to classify it.

### Recommendation 2A: Add Error Classification

```python
from guardkit.orchestrator.exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
    StateValidationError,
)

# Unrecoverable errors that should fail immediately
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    TaskNotFoundError,
    StateValidationError,
)

def _invoke_player_safely(self, task_id, turn, requirements, feedback):
    try:
        # ... existing invocation ...

    except UNRECOVERABLE_ERRORS as e:
        logger.error(f"Unrecoverable error for {task_id}: {e}")
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=False,
            report={"unrecoverable": True},  # Signal to stop retrying
            duration_seconds=0.0,
            error=f"Unrecoverable: {str(e)}",
        )

    except Exception as e:
        # Recoverable error - allow retry
        logger.warning(f"Recoverable error for {task_id}: {e}")
        return AgentInvocationResult(
            success=False,
            error=f"Recoverable: {str(e)}",
        )
```

### Recommendation 2B: Check for Unrecoverable in Loop Phase

```python
# In autobuild.py, loop phase:
for turn in range(start_turn, self.max_turns + 1):
    player_result = self._invoke_player_safely(...)

    # Check for unrecoverable error
    if not player_result.success and player_result.report.get("unrecoverable"):
        logger.error(f"Unrecoverable error at turn {turn}, stopping orchestration")
        return AutoBuildResult(
            success=False,
            final_decision="unrecoverable_error",
            total_turns=turn,
            error=player_result.error,
        )
```

---

## Deep Dive 3: Implementation Mode Design System

### Current State

The implementation_mode system has **three components with incomplete integration**:

| Component | Location | Modes Supported | Gap |
|-----------|----------|-----------------|-----|
| Mode Analyzer | `installer/core/lib/implementation_mode_analyzer.py` | task-work, direct, manual | N/A (assigns correctly) |
| Agent Invoker | `guardkit/orchestrator/agent_invoker.py:651-664` | direct, task-work (default) | **Missing: manual** |
| Feature Orchestrator | `guardkit/orchestrator/feature_orchestrator.py:1203` | None (always AutoBuild) | **Missing: all routing** |
| State Bridge | `guardkit/tasks/state_bridge.py:388` | task-work (stub creation) | **Missing: manual, direct** |

### Flow Diagram

```
Task with implementation_mode: manual
        │
        ▼
┌───────────────────────────────────────┐
│  FeatureOrchestrator._execute_task()  │
│                                       │
│  • Loads task data                    │
│  • Does NOT check implementation_mode │  ❌ GAP
│  • Dispatches to AutoBuildOrchestrator│
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  AutoBuildOrchestrator.orchestrate()  │
│                                       │
│  • Starts loop phase                  │
│  • Calls _invoke_player_safely()      │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  AgentInvoker.invoke_player()         │
│                                       │
│  • Calls _get_implementation_mode()   │
│  • Returns "manual" (from frontmatter)│
│  • impl_mode != "direct", so...       │
│  • Falls through to task-work path    │  ❌ GAP
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  AgentInvoker._ensure_design_approved │
│                                       │
│  • Creates TaskStateBridge            │
│  • Calls verify_implementation_plan   │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  TaskStateBridge._create_stub_plan()  │
│                                       │
│  • Checks: is_task_work_mode = False  │
│  • Checks: has_autobuild_state = False│
│  • Result: should_create_stub = False │  ❌ GAP
│  • Returns None                       │
└───────────────────────────────────────┘
        │
        ▼
    PlanNotFoundError raised
        │
        ▼
    Retry 25 times (no classification)  ❌ GAP
```

### Recommendation 3A: Add Mode Routing in FeatureOrchestrator

```python
# In feature_orchestrator.py:
def _execute_task(self, task, feature, worktree) -> TaskExecutionResult:
    task_data = TaskLoader.load_task(task.id, repo_root=self.repo_root)
    task_frontmatter = task_data.get("frontmatter", {})
    implementation_mode = task_frontmatter.get("implementation_mode", "task-work")

    # Route based on implementation_mode
    if implementation_mode == "manual":
        logger.info(f"Task {task.id}: Skipping AutoBuild (implementation_mode=manual)")
        return self._handle_manual_task(task, feature, worktree)

    if implementation_mode == "direct":
        logger.info(f"Task {task.id}: Using direct SDK mode (implementation_mode=direct)")
        return self._execute_direct_task(task, feature, worktree, task_data)

    # Default: task-work mode via AutoBuildOrchestrator
    return self._execute_taskwork_task(task, feature, worktree, task_data)

def _handle_manual_task(self, task, feature, worktree) -> TaskExecutionResult:
    """Handle manual tasks that require human execution."""
    return TaskExecutionResult(
        task_id=task.id,
        success=True,  # Manual tasks auto-succeed to not block wave
        total_turns=0,
        final_decision="skipped_manual",
        error=None,
        metadata={"requires_manual_execution": True},
    )
```

### Recommendation 3B: Add Manual Mode Routing in Agent Invoker

```python
# In agent_invoker.py, invoke_player():
impl_mode = self._get_implementation_mode(task_id)

if impl_mode == "manual":
    logger.info(f"Task {task_id} is manual - should not reach AutoBuild")
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,  # Let wave proceed
        report={"skipped": True, "reason": "manual_task"},
        duration_seconds=0.0,
        error=None,
    )

if impl_mode == "direct":
    # ... existing direct handling ...
```

---

## Decision Matrix

| Fix | Effort | Impact | Risk | Priority |
|-----|--------|--------|------|----------|
| 3A: FeatureOrchestrator routing | Medium | HIGH | Low | **1 (Do First)** |
| 1A: Pass AutoBuild context to state bridge | Low | Medium | Low | 2 |
| 2A/2B: Error classification | Medium | Medium | Low | 3 |
| 3B: Agent invoker manual routing | Low | Low | Low | 4 (defensive) |

## Immediate Action for Failed Build

To unblock FEAT-GR-MVP now:

**Option A (Quickest)**: Mark TASK-GR-PRE-003-A as completed manually
```bash
# Edit task file
status: completed
autobuild_state:
  final_decision: skipped_manual
  note: "Manual research task - execute outside AutoBuild"
```

**Option B (Recommended)**: Implement Fix 3A before re-running
- Add implementation_mode routing in FeatureOrchestrator
- ~30 lines of code
- Fixes root cause for all future manual/direct tasks

**Option C (Thorough)**: Implement all 4 fixes, then re-run
- Complete solution
- Proper error classification prevents 25x retry waste
- Defense in depth at all layers

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/feature_orchestrator.py` | Add `_handle_manual_task()`, routing in `_execute_task()` |
| `guardkit/orchestrator/agent_invoker.py` | Add manual mode check in `invoke_player()` |
| `guardkit/tasks/state_bridge.py` | Add `in_autobuild_context` parameter |
| `guardkit/orchestrator/autobuild.py` | Add error classification, unrecoverable handling |

## Appendix

### Build Log Analysis Summary

| Metric | Value |
|--------|-------|
| Total execution time | ~91 seconds |
| Time wasted on retries | ~82 seconds (25 × 3.3s) |
| Percentage wasted | 90% |
| Error message repetitions | 25 (identical) |

### Related Tasks

- TASK-GR-PRE-003-A: Failed research task (manual mode)
- TASK-GR-PRE-001-A through 002-B: Succeeded (task-work mode)

### Test Coverage Gaps

No existing tests for:
- Manual mode routing in FeatureOrchestrator
- Error classification in AutoBuildOrchestrator
- State bridge stub creation with in_autobuild_context flag

---

## Addendum: Deeper Root Cause Analysis

### Finding: `manual` Mode is a Design Gap, Not a Bug

The original analysis focused on fixing the symptom (task failing in AutoBuild). The actual root cause is **the existence of `manual` implementation_mode itself**.

**Investigation Results:**

1. The task TASK-GR-PRE-003-A was created with `implementation_mode: manual` in commit 926bee57
2. This was done **intentionally** to mark a "research task" that requires human investigation
3. The feature YAML (FEAT-GR-MVP.yaml) was manually authored with this mode
4. The `implementation_mode_analyzer.py` assigns `manual` for keywords like "run script", "bulk operation", "migration script" - but NOT for "research"

**The Fundamental Question:**

> "Why does `manual` mode exist? Why not use `/task-work`?"

With GuardKit's adaptive workflow:
- `/task-work` handles complexity automatically (0-10 scale)
- `--micro` flag available for very simple tasks
- AI can research, read docs, create ADRs and documentation
- Even "bulk operations" could be automated with careful design

**Scenarios Where `manual` Was Intended:**

1. **Bulk migrations** - But these should be scripted and tested, not truly manual
2. **Infrastructure changes** - Could use `terraform plan` verification
3. **External actions** - Deploy, configure third-party services

**Recommendation:**

This is **out of scope** for TASK-GR-REV-001. Create a follow-up review task to address:

1. Should `manual` mode exist?
2. If yes: AutoBuild should skip manual tasks gracefully
3. If no: Remove `manual` from valid `implementation_mode` values
4. Alternative: Define what makes a task truly "manual" vs just complex

### Suggested Follow-Up Task

```yaml
id: TASK-GR-REV-002
title: Review implementation_mode design - should 'manual' exist?
task_type: review
decision_required: true
complexity: 5
tags: [review, architecture, implementation-mode, autobuild]
```

**Review Questions:**
1. What scenarios genuinely require human-only execution?
2. Can AI handle research/documentation tasks via `/task-work`?
3. Should `/feature-build` skip manual tasks or fail on them?
4. If `manual` is removed, what happens to existing tasks with that mode?

This review should be executed separately to avoid context window issues.
