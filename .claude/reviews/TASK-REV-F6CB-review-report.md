# Review Report: TASK-REV-F6CB

## Executive Summary

The `/feature-build` command has **three distinct coordination gaps** between the AutoBuild orchestrator and the Claude Agent SDK that cause repeated failures in the Player-Coach workflow. These gaps prevent `task_work_results.json` from being written, causing Coach validation to always provide feedback instead of approving work.

**Key Findings**:
1. **Task file not copied to worktree** - Tasks not found by `_get_current_state()` in worktree
2. **task_work_results.json never written** - SDK delegation doesn't create this file
3. **State recovery succeeds but doesn't bridge SDK results** - Git-only fallback works but Coach has no quality gate data

**Impact**: 100% failure rate for feature-build on well-formed tasks. Every turn results in "Task-work results not found" feedback.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~90 minutes
- **Reviewer**: Claude Opus 4.5
- **Task**: TASK-REV-F6CB

## Findings

### Finding 1: Task Files Not Copied to Worktree (Root Cause - HIGH SEVERITY)

**Evidence**: Test trace lines 91-102
```
INFO:guardkit.tasks.state_bridge.TASK-FHA-001:Ensuring task TASK-FHA-001 is in design_approved state
...
Unexpected error: Task TASK-FHA-001 not found in any state directory.
Searched: ['.guardkit/worktrees/FEAT-FHA/tasks/backlog', ...]
```

**Root Cause**: The `FeatureOrchestrator` creates a shared worktree for the feature but doesn't copy the task files from the main repository's `tasks/backlog/{feature}/` directory to the worktree. The `TaskStateBridge.ensure_design_approved_state()` then fails because it can't find the task in any state directory within the worktree.

**Location**: `guardkit/orchestrator/feature_orchestrator.py` - Missing task file copy logic in worktree setup

**Impact**: Player can't transition task to `design_approved` state, causing immediate failure

---

### Finding 2: task_work_results.json Never Written (CRITICAL)

**Evidence**: Test trace lines 115-119
```
WARNING:guardkit.orchestrator.quality_gates.coach_validator:Task-work results not found at
.guardkit/worktrees/FEAT-FHA/.guardkit/autobuild/TASK-FHA-001/task_work_results.json
```

**Root Cause**: When `AgentInvoker.invoke_player()` delegates to task-work via SDK, the method `_invoke_task_work_implement()` streams the SDK output and parses it with `TaskWorkStreamParser`, but **never writes the parsed results to disk**. The code at `agent_invoker.py:502` calls `_create_player_report_from_task_work()` which creates `player_turn_{turn}.json`, but the intermediate `task_work_results.json` that `CoachValidator.read_quality_gate_results()` expects is never created.

**Code Flow Analysis**:
```
invoke_player()
  → _invoke_task_work_implement()           # Streams SDK output
    → TaskWorkStreamParser.to_result()       # Parses quality gates
    → Returns TaskWorkResult                 # Contains parsed data
  → _create_player_report_from_task_work()  # Creates player_turn_{turn}.json

# MISSING: Write task_work_results.json before Coach runs
```

**Location**: `guardkit/orchestrator/agent_invoker.py:489-506`

**Impact**: Coach always returns "feedback" due to missing results file, causing infinite retry loop until max_turns

---

### Finding 3: CoachValidator Reads From Wrong Location (MEDIUM)

**Evidence**: `coach_validator.py:395`
```python
results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

**Analysis**: The path is correct according to documentation, but `AgentInvoker` writes to a different artifact structure. The `TaskWorkStreamParser.to_result()` data is passed directly to `_create_player_report_from_task_work()` without intermediate persistence.

**Coordination Gap**:
- `AgentInvoker` assumes results are ephemeral (in-memory)
- `CoachValidator` assumes results are persisted (on disk)

**Impact**: Even if task-work executes successfully, Coach cannot validate it

---

### Finding 4: State Recovery Bypasses SDK Results (MEDIUM)

**Evidence**: Test trace lines 104-110
```
INFO:guardkit.orchestrator.state_tracker:Capturing state for TASK-FHA-001 turn 1
INFO:guardkit.orchestrator.state_detection:Git detection: 1 files changed (+0/-0)
INFO:guardkit.orchestrator.autobuild:State recovery succeeded via git_only: 1 files, 0 tests (failing)
```

**Analysis**: When Player fails, state recovery uses git diff to detect changes. This provides file change information but no quality gate data (tests passed, coverage, architectural review). The recovery creates `work_state_turn_1.json` but this is separate from `task_work_results.json`.

**Impact**: Coach receives "Player failed" but no quality data to verify, always provides feedback

---

### Finding 5: SDK Timeout Hides Successful Work (MEDIUM-LOW)

**Evidence**: Test traces show 15-29 tests passing when manually verified after timeout
```
cd .guardkit/worktrees/FEAT-FHA && python -m pytest tests/ -v
...
29 passed
```

**Analysis**: The 2400s timeout (40 minutes) is exceeded because task-work + TDD creates comprehensive test suites (32 tests in one case). The work is completed but the SDK invocation times out before signaling completion, so no results are captured.

**Impact**: Completed work is lost due to timeout, not SDK coordination per se

## Decision Matrix

| Option | Effort | Risk | Quality Impact | Recommendation |
|--------|--------|------|----------------|----------------|
| **A: Fix task file copy** | Low (1 day) | Low | Must fix | ✅ Implement |
| **B: Add task_work_results.json write** | Medium (2 days) | Low | Must fix | ✅ Implement |
| **C: Unify artifact paths** | Medium (2-3 days) | Medium | Should fix | ✅ Implement |
| **D: Increase SDK timeout** | Trivial | Low | Workaround | Consider |
| **E: Add SDK result passthrough** | High (1 week) | Medium | Nice to have | Defer |

## Recommendations

### Recommendation 1: Copy Task Files to Worktree (MUST FIX)
**Priority**: P0 - Blocking

Add task file copy logic to `FeatureOrchestrator._setup_worktree()`:

```python
def _copy_tasks_to_worktree(self, feature: Feature, worktree: Worktree):
    """Copy feature's task files to worktree."""
    for task in feature.tasks:
        src = self.repo_root / "tasks" / "backlog" / feature.slug / f"{task.task_id}*.md"
        dst = worktree.path / "tasks" / "backlog"
        dst.mkdir(parents=True, exist_ok=True)
        for task_file in self.repo_root.glob(str(src)):
            shutil.copy2(task_file, dst)
```

**Files to modify**:
- `guardkit/orchestrator/feature_orchestrator.py`

---

### Recommendation 2: Write task_work_results.json After SDK Parse (MUST FIX)
**Priority**: P0 - Blocking

Add result persistence to `AgentInvoker._invoke_task_work_implement()`:

```python
async def _invoke_task_work_implement(self, task_id: str, mode: str, ...):
    # ... existing SDK streaming code ...

    # Parse results
    result = parser.to_result()

    # ADDED: Persist for CoachValidator
    results_path = self._get_task_work_results_path(task_id)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(result, f, indent=2)

    return TaskWorkResult(success=True, data=result)
```

**Files to modify**:
- `guardkit/orchestrator/agent_invoker.py`

---

### Recommendation 3: Use Centralized TaskArtifactPaths (SHOULD FIX)
**Priority**: P1 - Coordination

Both `AgentInvoker` and `CoachValidator` should use `TaskArtifactPaths.task_work_results_path()` for consistent path resolution:

```python
# In AgentInvoker
results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

# In CoachValidator
results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
```

**Files to modify**:
- `guardkit/orchestrator/paths.py` (add method if missing)
- `guardkit/orchestrator/agent_invoker.py`
- `guardkit/orchestrator/quality_gates/coach_validator.py`

---

### Recommendation 4: Add Implementation Plan Stub for Feature Tasks
**Priority**: P2 - Robustness

Feature tasks from `/feature-plan` don't have implementation plans. Add stub plan creation:

```python
def _ensure_implementation_plan(self, task_id: str, worktree: Path):
    """Create stub implementation plan if missing."""
    plan_path = TaskArtifactPaths.preferred_plan_path(task_id, worktree)
    if not plan_path.exists():
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(f"# Implementation Plan: {task_id}\n\n[Auto-generated stub]")
```

**Files to modify**:
- `guardkit/orchestrator/feature_orchestrator.py`
- `guardkit/tasks/state_bridge.py` (relax validation)

---

### Recommendation 5: Adjust SDK Timeout Strategy
**Priority**: P3 - Optimization

For feature-build with pre-loop disabled, use 3600s (1 hour) base timeout:

```python
# In FeatureOrchestrator
sdk_timeout = 3600 if not enable_pre_loop else 7200  # 1hr vs 2hr
```

Alternatively, implement incremental timeout based on task complexity.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing task-work flows | Low | High | Add integration tests |
| Path inconsistencies | Medium | Medium | Use centralized paths |
| Timeout too short for complex tasks | High | Medium | Document timeout tuning |
| State recovery conflicts with SDK results | Low | Low | Clear precedence rules |

## Implementation Priority

```
Wave 1 (Blocking):
  1. Fix task file copy to worktree         [1 day]
  2. Add task_work_results.json write       [2 days]

Wave 2 (Coordination):
  3. Centralize TaskArtifactPaths usage     [1 day]
  4. Add implementation plan stub           [0.5 days]

Wave 3 (Optimization):
  5. Adjust SDK timeout strategy            [0.5 days]
  6. Add integration tests                  [1 day]
```

**Total estimated effort**: 6 days

## Appendix

### A. Test Trace Analysis Summary

| Test Run | Timeout | Turns | Result | Files Created | Tests Passing |
|----------|---------|-------|--------|---------------|---------------|
| Run 1 | 600s | 5 | max_turns | 1 | 0 |
| Run 2 | 600s | 5 | max_turns | 16 | 29 |
| Run 3 | 2400s | 1 | timeout | 15 | 29 |

### B. Code Locations

| Component | File | Key Methods |
|-----------|------|-------------|
| AutoBuild Orchestrator | `guardkit/orchestrator/autobuild.py` | `orchestrate()`, `_execute_turn()` |
| Agent Invoker | `guardkit/orchestrator/agent_invoker.py` | `invoke_player()`, `_invoke_task_work_implement()` |
| Coach Validator | `guardkit/orchestrator/quality_gates/coach_validator.py` | `validate()`, `read_quality_gate_results()` |
| Feature Orchestrator | `guardkit/orchestrator/feature_orchestrator.py` | `orchestrate()`, `_setup_worktree()` |
| Task State Bridge | `guardkit/tasks/state_bridge.py` | `ensure_design_approved_state()` |
| Artifact Paths | `guardkit/orchestrator/paths.py` | `TaskArtifactPaths` |

### C. Related Tasks

- TASK-REV-FB15: Phase 2 documentation timing analysis
- TASK-REV-FB16: Provenance-aware intensity system
- Prior implementation: `tasks/backlog/task-work-performance/`
