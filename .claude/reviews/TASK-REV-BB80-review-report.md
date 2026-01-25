# Review Report: TASK-REV-BB80 (REVISED)

## Executive Summary

**ROOT CAUSE IDENTIFIED**: Commit `14327137` ("Apply feature-build-regression-fix") introduced a bug by changing the SDK `max_turns` from **50** to **5**. The Player now only gets 5 internal SDK turns to complete its implementation, which is insufficient for `/task-work` which needs ~50+ turns to run all its phases.

**Architecture Score**: 85/100 - The orchestration infrastructure is correct. This is a simple configuration regression.

**Severity**: HIGH - Single-line fix required.

**Fix Location**: [agent_invoker.py:2260](guardkit/orchestrator/agent_invoker.py#L2260)

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard (1-2 hours)
- **Reviewer**: Claude Opus 4.5
- **Status**: REVISED - Root cause isolated to specific commit

## Regression Timeline

| Commit | Date | Change | Impact |
|--------|------|--------|--------|
| `09f39976` | Jan 25 09:33 | Add direct mode routing | Working - `max_turns=50` preserved |
| `82ee50a9` | Jan 25 09:38 | Handle direct mode in player-coach | Working |
| `14327137` | Jan 25 11:45 | Apply feature-build-regression-fix | **REGRESSION** - changed `max_turns=50` → `max_turns=self.max_turns_per_agent` (5) |

## Root Cause (CONFIRMED)

**Commit**: `14327137` ("Apply feature-build-regression-fix")

**File**: [guardkit/orchestrator/agent_invoker.py:2260](guardkit/orchestrator/agent_invoker.py#L2260)

**Before (Working)**:
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=50,  # task-work can take many turns  ← CORRECT
    setting_sources=["user", "project"],
)
```

**After (Broken)**:
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=self.max_turns_per_agent,  # TASK-FBR-002: Use configured value  ← BUG
    setting_sources=["user", "project"],
)
```

**Why This Broke It**:
- `self.max_turns_per_agent` is passed from `AutoBuildOrchestrator.max_turns`
- `AutoBuildOrchestrator.max_turns` defaults to **5** (the number of Player↔Coach adversarial turns)
- The SDK's `max_turns` controls internal agent turns within a single invocation
- `/task-work` needs ~50+ internal turns to run all phases (planning, review, implementation, testing)
- With only 5 turns, the Player can barely read files, let alone implement anything

**Evidence**:
- Working runs: 73-113 tool invocations per task
- Failing runs: 9-10 tool invocations per task (5 turns × ~2 tools/turn)

## Findings

### Finding 1: Massive Tool Usage Disparity (CRITICAL)

**Evidence**:
- **SUCCESS (FEAT-A96D)**: TASK-FHA-001 used `total=162, assistant=84, tools=73`
- **FAILURE (FEAT-FHE)**: TASK-FHE-002 used `total=24-25, assistant=13-14, tools=9-10`

The working task executed **7-8x more tool invocations** than the failing one. The Player in the failing case is completing its conversation (10 SDK turns) but **not actually taking implementation actions**.

**Impact**: The Player reports "success" but creates no files, leading to infinite coaching loops.

### Finding 2: Coach Detection Working Correctly (POSITIVE)

**Evidence**:
```
WARNING:guardkit.orchestrator.worktree_checkpoints:Context pollution detected: 2 consecutive test failures in turns [1, 2]
WARNING:guardkit.orchestrator.worktree_checkpoints:No passing checkpoints found in history
```

The adversarial cooperation pattern correctly identifies lack of progress. Context pollution detection and state recovery are functioning as designed.

**Impact**: None - this is expected behavior.

### Finding 3: Perspective Resets Ineffective (CONCERNING)

**Evidence**:
```
INFO:guardkit.orchestrator.autobuild:Perspective reset triggered at turn 3 (scheduled reset)
INFO:guardkit.orchestrator.autobuild:Perspective reset triggered at turn 5 (scheduled reset)
```

Perspective resets at turns 3 and 5 did not change Player behavior. This suggests the problem is not "accumulated confusion" but rather a fundamental misunderstanding from turn 1.

**Impact**: Perspective resets are ineffective for this class of failure.

### Finding 4: Quality Gate Profiles Working Correctly (POSITIVE)

**Evidence**:
- TASK-FHE-001 (scaffolding): `tests_required=False` → Approved
- TASK-FHE-002 (feature): `tests_required=True` → Feedback loop

The system correctly identified task types and applied appropriate quality gate profiles.

**Impact**: None - this is expected behavior.

### Finding 5: State Recovery Working After Timeout (POSITIVE)

**Evidence**:
```
INFO:guardkit.orchestrator.autobuild:State recovery succeeded via git_only: 4 files, 0 tests (failing)
```

When turn 4 timed out after 900s, state recovery correctly captured the (empty) worktree state.

**Impact**: None - this is expected behavior.

### Finding 6: Stub Implementation Plan Content May Be Insufficient

**Evidence** (from [state_bridge.py:407-423](guardkit/tasks/state_bridge.py#L407-L423)):
```markdown
# Implementation Plan: {task_id}
## Task
{title}
## Plan Status
**Auto-generated stub** - Pre-loop was skipped for this feature task.
## Implementation
Follow acceptance criteria in task file.
```

The stub plan provides minimal context. When the Player reads this, it may interpret "Follow acceptance criteria in task file" as insufficient guidance, especially if:
1. The task file isn't being read
2. The acceptance criteria are ambiguous
3. The Player is confused about what files already exist in the worktree

**Impact**: The Player may be "completing" without actually implementing because the stub plan doesn't provide actionable steps.

## Root Cause Analysis

### Primary Root Cause: Player Not Reading Task Context

The Player is executing 10 SDK turns with only 9-10 tool invocations total. A proper implementation would require:
- Reading the task file
- Reading the stub implementation plan
- Creating/modifying files
- Running tests

With only 9-10 tools across 10 turns (~1 tool per turn), the Player is likely:
1. Only performing read operations (no writes)
2. Getting stuck in a reasoning loop
3. Misinterpreting the `--implement-only` flag

### Secondary Root Cause: Worktree State Confusion

When TASK-FHE-002 starts (Wave 2), TASK-FHE-001 has already completed in the shared worktree. The worktree contains:
- Project structure from TASK-FHE-001
- Completed task file for TASK-FHE-001

The Player for TASK-FHE-002 may be:
1. Confused about what already exists
2. Thinking "the work is done" because files exist
3. Not understanding its specific task within the feature

### Comparison: Why SUCCESS Worked

In FEAT-A96D, all Wave 1 tasks ran in **parallel** (3 tasks simultaneously), each with its own context. The successful runs showed:
- Higher tool counts (73-113 tools)
- Longer execution times (360-540s vs 30-60s in failure)
- Actual file creation/modification

## The Fix

### Single Line Change Required

**File**: [guardkit/orchestrator/agent_invoker.py:2260](guardkit/orchestrator/agent_invoker.py#L2260)

**Change**:
```python
# FROM (broken):
max_turns=self.max_turns_per_agent,  # TASK-FBR-002: Use configured value

# TO (fixed):
max_turns=50,  # task-work needs many internal turns for all phases
```

**Or better, add a separate constant**:
```python
# At module level:
TASK_WORK_SDK_MAX_TURNS = 50  # Internal turns for /task-work (not adversarial turns)

# In _invoke_task_work_implement():
max_turns=TASK_WORK_SDK_MAX_TURNS,  # task-work needs ~50 turns for all phases
```

### Why This Happened

The original fix in TASK-FBR-002 was well-intentioned: make `max_turns` configurable. However, it conflated two different concepts:

1. **Adversarial turns** (`AutoBuildOrchestrator.max_turns`): How many Player↔Coach rounds (default: 5)
2. **SDK internal turns**: How many internal tool calls the SDK allows per invocation (needs: ~50)

The `/task-work` command runs multiple phases internally (planning, review, implementation, testing), each requiring many tool calls. It needs significantly more internal turns than a simple agent invocation.

### Verification

After applying the fix, verify:
- Message count returns to ~150-250 per task (not 24-25)
- Tool count returns to ~70-110 per task (not 9-10)
- Files are actually created/modified

## Decision Matrix

| Option | Effort | Risk | Recommendation |
|--------|--------|------|----------------|
| Revert to `max_turns=50` | 1 line | Very Low | **FIX NOW** |
| Add `TASK_WORK_SDK_MAX_TURNS` constant | 3 lines | Very Low | Cleaner |
| Make it configurable separately | Medium | Low | Future enhancement |

## Appendix

### Key File Locations

| File | Purpose |
|------|---------|
| [agent_invoker.py:2260](guardkit/orchestrator/agent_invoker.py#L2260) | **BUG LOCATION** - SDK max_turns |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | Main orchestration loop |

### Git Diff of Regression

```bash
git show 14327137 -- guardkit/orchestrator/agent_invoker.py
```

```diff
-                max_turns=50,  # task-work can take many turns
+                max_turns=self.max_turns_per_agent,  # TASK-FBR-002: Use configured value
```

### Evidence Files

- SUCCESS: `docs/reviews/feature-build/finally_success.md`
- REGRESSION: `docs/reviews/feature-build/serious_regression.md`

### Message Count Comparison (Explains 7-8x Tool Disparity)

| Task | Total | Tools | Max Turns | Result |
|------|-------|-------|-----------|--------|
| SUCCESS: TASK-FHA-001 | 162 | 73 | 50 | 1 file created |
| SUCCESS: TASK-FHA-002 | 220 | 99 | 50 | 1 file modified |
| SUCCESS: TASK-FHA-003 | 249 | 113 | 50 | 1 file created |
| FAILURE: TASK-FHE-002 | 24-25 | 9-10 | **5** | 0 files |

The 7-8x reduction in tool usage directly corresponds to the 10x reduction in allowed SDK turns (50 → 5).
