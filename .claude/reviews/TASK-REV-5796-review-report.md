# Review Report: TASK-REV-5796

## Executive Summary

All FEAT-CR01 AutoBuild failures stem from **two code defects in the AutoBuild orchestrator** and **one architectural gap in shared worktree git handling**. The feature tasks themselves are well-formed and valid. The root cause is a partially-integrated TASK-GR6-006 (Job-Specific Context Retrieval) feature where the caller was updated but the callee was not, plus a lack of git locking for parallel worktree tasks.

**Primary blocker**: A single 1-line fix (removing the `context=` parameter or adding it to the method signature) would unblock all 10 tasks.

**Why now?**: FEAT-CR01 is the **first feature run after the FEAT-0F4A merge** (Feb 1). Previous successful runs (mvp_build_1-3, phase_2_build, phase_2_resume_success) all ran FEAT-0F4A itself, which was building from a codebase *before* the TASK-GR6-006 context code existed. The init logs confirm this: successful runs log `ablation_mode=False, existing_worktree=provided` (no `enable_context`), while FEAT-CR01 logs `existing_worktree=provided, enable_context=True, verbose=False`. TASK-GR6-006 introduced the bug during its own autonomous build but couldn't self-detect it because the feature-build worktree used the pre-merge code.

## Review Details

- **Mode**: Architectural Review (debugging-focused)
- **Depth**: Standard
- **Task**: TASK-REV-5796 - Analyse FEAT-CR01 AutoBuild failure errors
- **Related**: TASK-REV-5F19 (parent review), FEAT-CR01 (feature)

---

## Findings

### Finding 1: `invoke_player()` context parameter mismatch (CRITICAL - Primary Blocker)

**Severity**: Critical
**Category**: API contract violation
**Source**: AutoBuild code, not feature conversion

**Evidence**:

The caller at [autobuild.py:2030](guardkit/orchestrator/autobuild.py#L2030) passes `context=context_prompt`:

```python
self._agent_invoker.invoke_player(
    task_id=task_id,
    turn=turn,
    requirements=requirements,
    feedback=feedback,
    max_turns=self.max_turns,
    context=context_prompt,  # Pass job-specific context (TASK-GR6-006)
)
```

But the callee at [agent_invoker.py:592](guardkit/orchestrator/agent_invoker.py#L592) does not accept `context`:

```python
async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[Union[str, Dict[str, Any]]] = None,
    mode: Optional[str] = None,
    max_turns: int = 5,
    documentation_level: str = "minimal",
) -> AgentInvocationResult:
```

**Root cause**: TASK-GR6-006 (Job-Specific Context Retrieval) was partially implemented. The call site in `autobuild.py` was updated to pass context, but the `AgentInvoker.invoke_player()` method signature was never updated to accept it.

**Impact**: 100% of Player invocations fail with `TypeError`. No work is ever executed. This affects ALL tasks, not just FEAT-CR01.

**Classification**: AutoBuild code defect (not feature conversion issue).

---

### Finding 2: Git index.lock concurrency in shared worktrees (HIGH)

**Severity**: High
**Category**: Concurrency / architectural gap
**Source**: AutoBuild feature-mode architecture

**Evidence**:

At [worktree_checkpoints.py:292](guardkit/orchestrator/worktree_checkpoints.py#L292), `create_checkpoint()` runs `git add -A` without any locking:

```python
self.git_executor.execute(
    ["git", "add", "-A"],
    cwd=self.worktree_path,
)
```

When Wave 1 runs 3 tasks in parallel (TASK-CR-001, TASK-CR-002, TASK-CR-003), all share the same worktree path (`.guardkit/worktrees/FEAT-CR01`). When TASK-CR-001's checkpoint runs `git add -A`, it creates `index.lock`. TASK-CR-002 and TASK-CR-003 attempt `git add -A` concurrently, find the lock, and fail with exit code 128.

The `GitCommandExecutor.execute()` at line 176 does not have retry logic or lock-waiting behaviour - it raises `CalledProcessError` immediately.

**Root cause**: Shared worktree architecture assumes sequential git operations, but Wave parallel execution creates concurrent git access. No locking, queuing, or retry mechanism exists.

**Impact**: Any wave with >1 parallel task sharing a worktree will have race conditions on git operations. TASK-CR-002 and TASK-CR-003 failed due to this. In the current run, this was masked by Finding 1 (Player never ran), but would be a separate blocker even after Finding 1 is fixed.

**Classification**: AutoBuild architectural gap (pre-existing, not caused by FEAT-CR01).

---

### Finding 3: `_recovery_count` attribute name mismatch (MEDIUM)

**Severity**: Medium
**Category**: Attribute naming inconsistency
**Source**: AutoBuild code defect

**Evidence**:

The `__init__` method at [autobuild.py:465](guardkit/orchestrator/autobuild.py#L465) initialises:

```python
self.recovery_count: int = 0  # Track number of state recovery attempts
```

But the turn state capture at [autobuild.py:1640](guardkit/orchestrator/autobuild.py#L1640) references:

```python
elif self._recovery_count > 0:
    mode = TurnMode.RECOVERING_STATE
```

The attribute is `self.recovery_count` (public, no underscore prefix), but the code references `self._recovery_count` (private, with underscore prefix).

**Root cause**: Naming inconsistency - the attribute was likely renamed from `_recovery_count` to `recovery_count` at some point, but the reference at line 1640 wasn't updated.

**Impact**: Turn state capture fails silently (caught by a `WARNING` handler). The turn mode is never set to `RECOVERING_STATE`, which means recovery-specific prompt context is never applied. This degrades recovery quality but doesn't block execution.

**Classification**: AutoBuild code defect (pre-existing, not caused by FEAT-CR01).

---

### Finding 4: `task_work_results.json` not found (CASCADING)

**Severity**: Low (cascading effect)
**Category**: Cascading failure
**Source**: Consequence of Finding 1

**Evidence**: At `coach_validator.py`, the Coach checks for `task_work_results.json` which should be produced by the Player's `task-work` execution. Since Finding 1 prevents the Player from ever running, no results file is created.

```
task_work_results.json not found at .guardkit/autobuild/TASK-CR-XXX/task_work_results.json
```

**Root cause**: Not an independent bug. This is a direct cascading consequence of Finding 1 (Player never executes).

**Impact**: Coach provides generic feedback ("Task-work results not found") instead of validating actual work. This wastes all 5 turns in a feedback loop that can never succeed.

**Classification**: Not a bug - cascading failure. Resolves automatically when Finding 1 is fixed.

---

### Finding 5: FEAT-CR01 task validity assessment (VALID)

**Severity**: N/A - Informational
**Category**: Task structure validation

The FEAT-CR01 feature file and task files were examined for structural issues:

| Aspect | Assessment |
|--------|-----------|
| Feature YAML structure | Valid - proper id, tasks, waves, dependencies |
| Task frontmatter | Valid - all required fields present (id, title, status, complexity, task_type) |
| Acceptance criteria | Valid - clear, measurable criteria in checklist format |
| Dependency graph | Valid - waves properly ordered with correct dependency chains |
| Implementation modes | Appropriate - task-work for complex, direct for simple |
| Wave grouping | Valid - independent tasks grouped in same wave, dependent tasks in later waves |

**Conclusion**: The FEAT-CR01 tasks are well-formed. The conversion from TASK-REV-5F19 review output did not introduce structural issues. All failures are from AutoBuild code defects, not task quality.

---

## Recommendations

### Priority 1: Fix `invoke_player()` context parameter (CRITICAL)

**Fix**: Add `context: str = ""` parameter to `AgentInvoker.invoke_player()` method signature at [agent_invoker.py:592](guardkit/orchestrator/agent_invoker.py#L592).

```python
async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[Union[str, Dict[str, Any]]] = None,
    mode: Optional[str] = None,
    max_turns: int = 5,
    documentation_level: str = "minimal",
    context: str = "",  # Job-specific context from Graphiti (TASK-GR6-006)
) -> AgentInvocationResult:
```

Then propagate the `context` value into the Player's prompt/requirements where appropriate within the method body.

**Alternative quick fix**: Remove `context=context_prompt` from the call site at [autobuild.py:2036](guardkit/orchestrator/autobuild.py#L2036) and prepend context to `requirements` instead. This avoids modifying the `invoke_player` signature but loses clean separation.

**Impact**: Unblocks ALL AutoBuild task execution (not just FEAT-CR01).

---

### Priority 2: Add git operation serialization for shared worktrees (HIGH)

**Fix**: Implement a lock/queue mechanism for git operations when multiple tasks share a worktree. Options:

1. **File-based lock with retry** (simplest): Use `fcntl.flock()` or a custom lockfile with exponential backoff before `git add -A` and `git commit`.
2. **asyncio.Lock per worktree**: Share a lock across tasks in the same wave when they use the same worktree path.
3. **Sequential checkpoint phase**: After all parallel tasks complete their Player/Coach loop for a turn, run checkpoints sequentially rather than concurrently.

Option 3 is the most architecturally clean - checkpoints are short operations and serializing them has minimal performance impact.

**Impact**: Prevents git race conditions in all parallel wave executions.

---

### Priority 3: Fix `_recovery_count` attribute name (MEDIUM)

**Fix**: Change `self._recovery_count` at [autobuild.py:1640](guardkit/orchestrator/autobuild.py#L1640) to `self.recovery_count` to match the initialisation at line 465.

**Impact**: Enables correct turn mode detection for recovery scenarios, improving recovery prompt quality.

---

### Priority 4: Re-run FEAT-CR01 after fixes (LOW)

After Priorities 1-3 are fixed, re-run:
```bash
guardkit autobuild feature FEAT-CR01 --fresh
```

The `--fresh` flag resets all task states. The feature tasks themselves are valid and should execute successfully.

---

## Decision Matrix

| Fix | Effort | Risk | Impact | Recommendation |
|-----|--------|------|--------|----------------|
| P1: invoke_player context param | ~15 min | Low | Unblocks all AutoBuild | **Fix immediately** |
| P2: Git lock for shared worktrees | ~1-2 hours | Medium | Prevents race conditions | **Fix before re-run** |
| P3: _recovery_count attribute | ~2 min | Low | Improves recovery quality | **Fix immediately** |
| P4: Re-run FEAT-CR01 | ~5 min | Low | Validates fixes | **After P1-P3** |

## Summary

| Metric | Value |
|--------|-------|
| Errors from AutoBuild code | 3 (Findings 1, 2, 3) |
| Errors from feature conversion | 0 |
| Cascading failures | 1 (Finding 4) |
| Task validity | All 10 tasks valid |
| Estimated fix effort | P1+P3: ~20 min, P2: ~1-2 hours |
