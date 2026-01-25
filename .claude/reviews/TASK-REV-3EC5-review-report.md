# Review Report: TASK-REV-3EC5

## Executive Summary

Analysis of the feature-build session logs (FEAT-4C22, FEAT-F392, FEAT-FHE) reveals **two distinct failure patterns**:

1. **Environmental Issue (FEAT-4C22)**: Cross-feature dependency on `TASK-DOC-001` which doesn't exist in the feature → Validation failure before execution begins.

2. **Race Condition (FEAT-F392 first attempt)**: Direct mode path writes `player_turn_1.json` but the file isn't visible to the orchestrator due to filesystem buffering.

**Critical Finding**: The race condition **only affects the direct mode path** (`_invoke_player_direct`). The task-work delegation path (`_invoke_task_work_implement`) handles file writes synchronously and works correctly.

**Evidence**: In FEAT-F392 first attempt, line 83 shows "Wrote direct mode player report" immediately followed by line 84 "Player report missing". State recovery at line 90 then **successfully loads the same file**.

**Overall Assessment**: Two separate issues need addressing:
1. Feature validation should catch cross-feature dependencies earlier
2. Direct mode needs retry/delay for file availability

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Architectural Review |
| **Depth** | Standard (1-2 hours) |
| **Duration** | ~1.5 hours |
| **Reviewer** | architectural-reviewer |
| **Files Analyzed** | 8 |

---

## Findings

### Finding 0: Cross-Feature Dependency Validation (Environmental - FEAT-4C22)

**Evidence from Session Log** (`logging_feature_fails.md`):
```
Feature validation failed for FEAT-4C22:
  - Task TASK-LOG-003 has unknown dependency: TASK-DOC-001
```

**Root Cause**: FEAT-4C22 (Structured Logging) had a task that depended on `TASK-DOC-001` which belongs to a **different feature** (FEAT-F392 - API Documentation). The feature loader correctly validates this as an error.

**This is not an orchestrator bug** - it's an incorrect feature specification. The system correctly rejected the invalid dependency.

**Resolution Applied**: The `/feature-build` agent detected this and fixed the feature file by changing the dependency from `TASK-DOC-001` to `TASK-LOG-001`.

---

### Finding 1: Race Condition in Direct Mode Path (Critical)

**Evidence from Session Log** (`open_api_docs_feature_success.md` lines 82-90):
```
INFO:agent_invoker:Wrote direct mode player report to .../player_turn_1.json
⚠ Player report missing - attempting state recovery
INFO:autobuild:Attempting state recovery... Player report not found: .../player_turn_1.json
INFO:state_tracker:Loaded Player report from .../player_turn_1.json  # SAME FILE!
```

The file was written on line 82, declared missing on line 84, but successfully loaded during state recovery on line 90 - **milliseconds apart**.

**Affected Code Path**: `_invoke_player_direct` method ([agent_invoker.py:654-665](guardkit/orchestrator/agent_invoker.py#L654-L665))

**Not Affected**: `_invoke_task_work_implement` - this path writes files synchronously and works correctly (see FEAT-FHE success).

**Root Cause Analysis**:

1. The direct mode SDK subprocess writes `player_turn_1.json`
2. The orchestrator immediately checks `report_path.exists()`
3. Filesystem buffering delays visibility of the newly written file
4. `PlayerReportNotFoundError` is raised
5. State recovery triggers moments later and **finds the file**

**Architecture Score Impact**: -15 points (robustness concern, no retry mechanism)

---

### Finding 2: Empty files_modified/files_created Despite Git Changes (High)

**Evidence from Session Log**:
```
# Player report shows empty arrays:
"files_modified": []
"files_created": []

# Yet git shows actual work:
git show --stat 9f749cc
 pyproject.toml | 1 +
 tests/test_logging.py | 45 +++
 ... +44 lines
```

**Root Cause Analysis**:

The `_create_player_report_from_task_work` method ([agent_invoker.py:1270-1393](guardkit/orchestrator/agent_invoker.py#L1270-L1393)) has a **fallback cascade** that's not being properly triggered:

1. First tries `task_work_results.json` - may be empty or malformed
2. Falls back to `task_work_result.output` - may not contain file data
3. Final fallback to `_detect_git_changes()` - **not reached** if prior steps appear to succeed

**Problem**: The method considers success if `task_work_results.json` exists, even if it contains empty arrays. Git fallback only triggers on `FileNotFoundError`.

**Architecture Score Impact**: -10 points (DRY: redundant data extraction paths, YAGNI: premature optimization of fallback cascade)

---

### Finding 3: State Recovery Ineffective for Timing Issues (Medium)

**Evidence**:
The `_attempt_state_recovery` method ([autobuild.py:1316-1401](guardkit/orchestrator/autobuild.py#L1316-L1401)) is triggered when reports are missing, but recovery fails because:

1. It runs **after** the orchestrator has already failed
2. By this point, checkpoint commits exist with actual work
3. Recovery detects work but doesn't prevent the error path

**Problem**: State recovery is a **reactive** mechanism, but the timing issue needs a **proactive** solution (e.g., polling/retry).

**Architecture Score Impact**: -5 points (SRP: recovery should be part of report loading, not a separate phase)

---

### Finding 4: SDK Timeout Doesn't Wait for File Flush (Low)

**Evidence from Code**:
```python
# Line 2292-2293: Async timeout wrapper
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
```

The SDK stream may complete its final message, but file I/O operations (writing `task_work_results.json` and `player_turn_N.json`) happen in the same event loop tick or immediately after. There's no guarantee filesystem buffers are flushed.

**Architecture Score Impact**: -5 points (robustness concern)

---

## Architecture Assessment

### SOLID Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| **S** - Single Responsibility | 7/10 | AgentInvoker has too many responsibilities (invocation, report creation, state management) |
| **O** - Open/Closed | 8/10 | Good use of strategy pattern for invocation modes |
| **L** - Liskov Substitution | 9/10 | Worktree and result abstractions are well-designed |
| **I** - Interface Segregation | 7/10 | Report interfaces could be more granular |
| **D** - Dependency Inversion | 8/10 | Good DI patterns for testing |

**SOLID Score: 78/100**

### DRY Adherence

| Issue | Severity | Location |
|-------|----------|----------|
| Report path computation duplicated | Medium | `TaskArtifactPaths` vs inline `Path()` |
| File existence check patterns | Low | Multiple variants across methods |

**DRY Score: 7/10**

### YAGNI Compliance

| Concern | Status |
|---------|--------|
| Ablation mode | Acceptable (research feature) |
| Multiple invocation paths | Some complexity could be reduced |
| Fallback cascade in report creation | Over-engineered for common case |

**YAGNI Score: 7/10**

### Overall Architecture Score: **72/100**

---

## Recommendations

### Recommendation 1: Add Retry/Polling for Report Detection (High Priority)

**Problem**: Report file may not be immediately available after SDK completion.

**Solution**: Add retry loop with exponential backoff in `_load_agent_report`:

```python
def _load_agent_report(self, task_id, turn, agent_type, max_retries=3, delay=0.5):
    report_path = self._get_report_path(task_id, turn, agent_type)

    for attempt in range(max_retries):
        if report_path.exists():
            # Add small delay for file flush
            time.sleep(0.1)
            try:
                with open(report_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(delay * (2 ** attempt))
                    continue
                raise
        elif attempt < max_retries - 1:
            time.sleep(delay * (2 ** attempt))
            continue

    raise PlayerReportNotFoundError(f"Report not found after {max_retries} retries: {report_path}")
```

**Estimated Complexity**: 3/10
**Files Affected**: 1 ([agent_invoker.py](guardkit/orchestrator/agent_invoker.py))

---

### Recommendation 2: Always Run Git Detection as Verification (High Priority)

**Problem**: `task_work_results.json` may contain empty arrays while git has actual changes.

**Solution**: After reading `task_work_results.json`, always verify against git state:

```python
def _create_player_report_from_task_work(self, task_id, turn, task_work_result):
    # ... existing report initialization ...

    # Read from task_work_results.json if exists
    if task_work_results_path.exists():
        # ... existing parsing ...

    # ALWAYS verify/enrich with git detection
    git_changes = self._detect_git_changes()
    if git_changes:
        # Merge git-detected files (union of both sources)
        report["files_modified"] = list(set(
            report["files_modified"] + git_changes.get("modified", [])
        ))
        report["files_created"] = list(set(
            report["files_created"] + git_changes.get("created", [])
        ))
```

**Estimated Complexity**: 2/10
**Files Affected**: 1 ([agent_invoker.py](guardkit/orchestrator/agent_invoker.py))

---

### Recommendation 3: Add Checkpoint Commit Synchronization (Medium Priority)

**Problem**: Checkpoint commits (`[guardkit-checkpoint]`) are created but not used to verify report consistency.

**Solution**: Before failing with "report not found", check if a recent checkpoint commit exists and extract file changes from it:

```python
def _verify_checkpoint_exists(self, worktree_path, turn):
    """Check if checkpoint commit exists for this turn."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-1", "--grep", f"Turn {turn}"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return True
    return False
```

**Estimated Complexity**: 4/10
**Files Affected**: 2 ([agent_invoker.py](guardkit/orchestrator/agent_invoker.py), [worktree_checkpoints.py](guardkit/orchestrator/worktree_checkpoints.py))

---

### Recommendation 4: Consolidate Report I/O into a ReportManager Class (Medium Priority)

**Problem**: Report reading, writing, validation, and path computation are scattered.

**Solution**: Create `ReportManager` class with:
- Single responsibility for all report I/O
- Built-in retry logic
- Atomic write operations (write to temp, rename)
- Validation on write

**Estimated Complexity**: 5/10
**Files Affected**: 3 (new file + refactor AgentInvoker + AutoBuildOrchestrator)

---

### Recommendation 5: Add Filesystem Sync After Report Write (Low Priority)

**Problem**: Python's `json.dump()` may not immediately flush to disk.

**Solution**: Explicitly flush and sync after writing:

```python
with open(player_report_path, "w") as f:
    json.dump(report, f, indent=2)
    f.flush()
    os.fsync(f.fileno())  # Force OS-level flush
```

**Estimated Complexity**: 1/10
**Files Affected**: 1 ([agent_invoker.py](guardkit/orchestrator/agent_invoker.py))

---

## Priority Matrix

| Recommendation | Impact | Effort | Priority |
|----------------|--------|--------|----------|
| 1. Retry/polling for report detection | High | Low | **P0** |
| 2. Always run git detection | High | Low | **P0** |
| 3. Checkpoint commit sync | Medium | Medium | P1 |
| 4. ReportManager class | Medium | High | P2 |
| 5. Filesystem sync | Low | Trivial | P3 |

---

## Key Questions Answered

### Q1: Why does `player_turn_1.json` not exist when expected, but appears later?

**Answer**: File system buffering and async event loop timing. The SDK subprocess completes, but file writes haven't flushed to disk. The immediate file existence check fails, but manual checks seconds later find the file.

### Q2: Is there a race condition between SDK completion and file checks?

**Answer**: Yes. The `_create_player_report_from_task_work` → `_load_agent_report` sequence has no synchronization. Both methods are called synchronously, but the underlying file I/O may not complete instantly.

### Q3: Why are `files_modified`/`files_created` empty when git shows changes?

**Answer**: The `task_work_results.json` file exists but contains empty arrays (likely because the SDK output parser didn't extract file data). The git fallback only triggers when the file is missing, not when it contains empty data.

### Q4: What causes discrepancy between checkpoint commits and orchestrator failure?

**Answer**: The checkpoint commit is created by the Player agent as part of its work. The orchestrator failure happens afterward, during report loading. The checkpoint system and report system are independent—checkpoints succeed while reports fail to be detected.

### Q5: Should there be retry/polling for report detection?

**Answer**: **Yes, absolutely.** This is the primary recommendation. A simple retry loop with exponential backoff would resolve the race condition without architectural changes.

---

## Appendix

### Files Analyzed

1. [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) - Feature-level orchestration
2. [autobuild.py](guardkit/orchestrator/autobuild.py) - Task-level orchestration
3. [agent_invoker.py](guardkit/orchestrator/agent_invoker.py) - SDK invocation and report handling
4. [paths.py](guardkit/orchestrator/paths.py) - Path computation (TaskArtifactPaths)
5. [state_tracker.py](guardkit/orchestrator/state_tracker.py) - Multi-layered state detection
6. [worktree_checkpoints.py](guardkit/orchestrator/worktree_checkpoints.py) - Checkpoint management
7. Session log: [feature_build_third_task_fails.md](docs/reviews/feature-build/feature_build_third_task_fails.md)
8. Task file: [TASK-REV-3EC5-feature-build-third-task-failures.md](tasks/backlog/TASK-REV-3EC5-feature-build-third-task-failures.md)

### Test Verification

The existing test suite does not appear to cover the race condition scenario. Recommended test additions:
- Test delayed file availability (mock file exists returning False then True)
- Test empty `task_work_results.json` with git changes present
- Test checkpoint commit detection fallback

---

*Report generated: 2026-01-25*
*Review Mode: Architectural*
*Depth: Standard*
