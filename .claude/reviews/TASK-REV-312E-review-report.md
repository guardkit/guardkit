# Review Report: TASK-REV-312E (Revised)

## Executive Summary

TASK-DM-008's UNRECOVERABLE_STALL is **not a false positive** and is **not the same class of bug** as TASK-FIX-CKPT. The deeper analysis reveals a **multi-layered problem**:

1. **Primary cause**: The Player's task-work session genuinely failed to complete quality gates — it consumed all 50 SDK turns without outputting "Quality gates: PASSED". This is the *upstream* problem.
2. **Secondary cause**: The Coach has no way to distinguish "quality gates not yet evaluated" (`null`) from "quality gates failed" (`false`), and treats both as failure. This is a *data modeling* issue.
3. **Tertiary cause**: The stall threshold (2 turns) leaves no room for recovery on tasks where the Player needs iterative turns.
4. **Contributing factor**: Parallel execution in a shared worktree — DM-005 created files in DM-008's scope, likely confusing DM-008's Player.

**This is NOT the same bug as TASK-FIX-CKPT.** TASK-FIX-CKPT was about the Coach misreading data that *was* there. This is about the Player *not producing* the data at all, and the system having no resilience to that.

**Root cause classification**: Combination of legitimate Player failure + insufficient tolerance in the feedback loop

## Why This Feels Like Going Backwards

The prior 120+ successful tasks all share one critical characteristic: the Player's task-work session completed quality gates and output "Quality gates: PASSED" (or similar). The `TaskWorkStreamParser` detected this and wrote `all_passed: true`. Every single successful task in `.guardkit/autobuild/` has `all_passed: true`.

DM-008 is the first case where:
- The Player ran for the full 50 SDK turns without completing quality gates
- The parser correctly wrote `all_passed: null` (it never saw the signal)
- The system had no tolerance for this state

The prior successful features (FEAT-GI, FEAT-FMT, etc.) succeeded because their parallel tasks happened to complete quality gates even when sharing a worktree. DM-008's scope overlap with DM-005 was more severe, and the Player couldn't recover.

## Review Details

- **Mode**: Decision Analysis (Comprehensive revision)
- **Depth**: Comprehensive (full data flow trace)
- **Feature**: FEAT-D4CE (Design mode for Player-Coach loops)
- **Related tasks**: TASK-REV-AB01, TASK-FIX-CKPT, TASK-AB-SD01

## Complete Data Flow Analysis

### How `all_passed` Gets Its Value

```
Player's SDK session runs /task-work TASK-DM-008
         ↓
    Output stream (text messages)
         ↓
TaskWorkStreamParser.parse_message()
  - Looks for regex: r"Quality gates: PASSED" or "all quality gates passed"
  - If found: self._quality_gates_passed = True
  - If NOT found: self._quality_gates_passed stays None (initialized at __init__)
         ↓
TaskWorkStreamParser.to_result()
  - Line 463: if self._quality_gates_passed is not None → include in dict
  - If None → key "quality_gates_passed" is ABSENT from result dict
         ↓
AgentInvoker._write_task_work_results()
  - Line 2999: quality_gates_passed = result_data.get("quality_gates_passed")
  - If absent → quality_gates_passed = None
  - Line 3037: "all_passed": quality_gates_passed → writes null to JSON
         ↓
CoachValidator.verify_quality_gates()
  - Line 726: "all_passed" in quality_gates → True (key exists with null value!)
  - Line 727: tests_passed = quality_gates["all_passed"] → tests_passed = None
  - None is falsy → QualityGateStatus(tests_passed=None) → all_gates_passed=False
         ↓
Coach returns feedback: "Tests did not pass"
```

### Key Insight: `to_result()` Conditionally Includes Keys, But `_write_task_work_results()` Always Writes Them

The parser's `to_result()` method (line 463) only includes `quality_gates_passed` if it's not None. But `_write_task_work_results()` always reads it with `.get()` (returns None for missing keys) and always writes `"all_passed": quality_gates_passed` — meaning **the null value is always written to JSON regardless**.

This design means `all_passed: null` is a valid state that represents "Player never produced a quality gate verdict." Neither the Coach nor the checkpoint system handles this state.

## Findings

### Finding 1: Player Genuinely Failed to Complete Quality Gates (ROOT CAUSE)

**Evidence**:

DM-008 Turn 1:
- SDK turns: 50 (max)
- Duration: ~690 seconds
- `task_work_results.json`: `completed: false`, `all_passed: null`, `coverage: null`
- Summary: "Implementation completed" (fallback when no metrics detected)
- Phase detected: `phase_0` only, not completed

DM-008 Turn 2:
- SDK turns: 50 (max)
- Duration: ~270 seconds (shorter — may have inherited confused state)
- `task_work_results.json`: same null/false pattern

**Contrast with DM-005** (same wave, parallel execution):
- SDK turns: 45
- Duration: ~480 seconds
- `task_work_results.json`: `completed: true`, `all_passed: true`, `coverage: 80.0`
- Summary: "80.0% coverage, all quality gates passed"

**Contrast with 120+ prior successful tasks**: ALL have `all_passed: true`. Examples:
- TASK-GI-004: `all_passed: true`, `coverage: 94.0`
- TASK-GI-005: `all_passed: true`, 301 tests passed
- TASK-GR3-001: `all_passed: true`, `coverage: 96.0`
- TASK-GR4-001: `all_passed: true`, 49 tests passed

**Assessment**: The Player exhausted its SDK turns without reaching the quality gate evaluation phase. This is NOT a parser bug — the Player genuinely didn't output the quality gates marker.

### Finding 2: Shared Worktree Parallel Execution Causes File Conflicts (CONTRIBUTING CAUSE)

**Evidence from DM-005's Player report** (completed first):
- Created: `guardkit/orchestrator/design_change_detector.py`
- Created: `tests/unit/test_design_change_detection.py`
- Created: `.claude/task-plans/TASK-DM-008-implementation-plan.md`
- Created: `tasks/design_approved/TASK-DM-008-add-design-change-detection.md`

These are all files that **belong to TASK-DM-008's scope**, not DM-005's. DM-005 (BrowserVerifier abstraction) proactively created DM-008's implementation files, likely because the Player saw DM-008's task definition and decided to "help."

**Impact**: When DM-008's Player started, it found:
- A pre-existing `design_change_detector.py` (incomplete, written by DM-005's Player for a different task)
- A pre-existing test file (not aligned with DM-008's actual requirements)
- These orphaned files likely caused test failures and confusion

**This is a known problem with shared worktrees**: Prior features (FEAT-GI) had the same pattern — GI-005's Player created GI-004's files. It worked then because both tasks completed quality gates. When one task fails (DM-008), the conflict becomes fatal.

### Finding 3: `null` is an Unhandled State in the Quality Gate Pipeline (DESIGN GAP)

**Three possible states for `all_passed`**:
1. `true` — Player completed quality gates successfully
2. `false` — Player completed quality gates but they failed
3. `null` — Player never reached quality gate evaluation

The Coach treats states 2 and 3 identically (both are "failed"). This is incorrect:
- State 2 (explicit failure) should trigger feedback with specific test failures
- State 3 (not evaluated) should trigger different feedback: "Quality gates were not evaluated — Player may have run out of SDK turns"

**Evidence**: The Coach's feedback for DM-008 is `"Tests did not pass during task-work execution"` with `failed_count: 0, total_count: 0`. This is misleading — no tests ran, so the feedback is semantically wrong. The Player gets no actionable information.

### Finding 4: Stall Threshold Interacts Badly With null States (AMPLIFIER)

The `should_rollback(consecutive_failures=2)` method treats `null` checkpoints as failing. With a threshold of 2, a task that produces `null` quality gates on its first 2 turns is immediately stalled out with no recovery path.

**However**: Even with a threshold of 3 or higher, if the Player keeps exhausting SDK turns without completing quality gates, increasing the threshold only delays the inevitable. **The real fix must be upstream** — either the Player needs to be more effective, or the system needs different handling for incomplete sessions.

### Finding 5: Feature Plan Put DM-005 and DM-008 in the Same Wave Despite Scope Overlap (DESIGN ISSUE)

FEAT-D4CE Wave 3: `[TASK-DM-005, TASK-DM-008]`

- TASK-DM-005: BrowserVerifier abstraction (browser verification, screenshots, SSIM)
- TASK-DM-008: Design change detection (cache TTL, hash comparison, state-aware handling)

These tasks have **no functional dependency** on each other (both depend on DM-003 only). They should be safe to parallelize. BUT they share modification scope on `autobuild.py` and the feature's overall design module namespace, which creates file-level conflicts in a shared worktree.

## Root Cause Chain (Revised)

```
1. Feature plan places DM-005 and DM-008 in same parallel wave
2. Both run via asyncio.gather() in shared worktree (same filesystem)
3. DM-005's Player creates files in DM-008's scope (design_change_detector.py, tests)
4. DM-008's Player finds pre-existing incomplete implementations
5. DM-008's Player spends all 50 SDK turns trying to reconcile/fix, never reaches Phase 4.5
6. TaskWorkStreamParser correctly records all_passed=null (never saw the marker)
7. Coach treats null as failure (no semantic distinction from false)
8. Checkpoint records tests_passed=null (treated as failing by should_rollback)
9. After 2 consecutive null turns → UNRECOVERABLE_STALL
10. Stall is technically correct (Player can't make progress) but could have been avoided
```

## Recommendations (Revised)

### Recommendation 1: Handle `null` quality gates as "incomplete" not "failed" (MUST FIX)

**Location**: `coach_validator.py:726-737`

Instead of just adding a None guard, create proper semantic handling:

```python
# Current:
elif "all_passed" in quality_gates:
    tests_passed = quality_gates["all_passed"]

# Proposed:
elif "all_passed" in quality_gates:
    all_passed_value = quality_gates["all_passed"]
    if all_passed_value is None:
        # Player session didn't reach quality gate evaluation
        # Fall through to tests_failed check for partial data
        if "tests_failed" in quality_gates:
            tests_failed = quality_gates["tests_failed"]
            tests_passed = tests_failed == 0
        else:
            tests_passed = False
    else:
        tests_passed = all_passed_value
```

This preserves the TASK-FIX-CKPT priority chain (check `all_passed` first) while properly handling the `null` state by falling back to test count data.

### Recommendation 2: Handle `null` in `_extract_tests_passed()` consistently (MUST FIX)

**Location**: `autobuild.py:2843-2844`

```python
# Current:
if "tests_passed" in quality_gates:
    return quality_gates.get("tests_passed", False)

# Proposed:
if "tests_passed" in quality_gates:
    value = quality_gates.get("tests_passed")
    if value is None:
        return False
    return bool(value)
```

### Recommendation 3: Increase stall threshold from 2 to 3 (SHOULD FIX)

**Location**: `worktree_checkpoints.py:475`

Change default `consecutive_failures` from 2 to 3. Rationale:
- Turn 1 is always exploratory (no prior feedback)
- Turn 2 is first correction attempt
- Turn 3 is when genuine stalls become distinguishable from slow-start tasks
- The feedback stall mechanism (Mechanism 2, 3 identical feedback turns) provides backup

### Recommendation 4: Provide better feedback for incomplete Player sessions (SHOULD FIX)

When the Coach detects `all_passed=null` with `tests_passed=0, tests_failed=0`, the feedback should say:

```
"Quality gate evaluation was not completed. The Player session may have run out of SDK turns
before reaching Phase 4.5. Focus on completing the implementation within fewer SDK turns."
```

Instead of the current misleading: `"Tests did not pass during task-work execution"`

**Location**: `coach_validator.py` `_build_gate_failure_feedback()` method

### Recommendation 5: Address scope overlap in wave planning (FUTURE)

The feature planner should detect when parallel tasks modify overlapping files in a shared worktree. This is a bigger architectural question. Options:
- a. Static analysis of task scope to detect conflicts before execution
- b. Per-task worktrees within a feature (isolate parallel tasks)
- c. Sequential fallback when scope overlap detected

This is out of scope for this fix but should be tracked.

### NOT Recommended: Changing the task definition

TASK-DM-008's definition is well-structured and appropriate. The failure was caused by the execution environment (shared worktree + parallel execution + null handling), not by task quality.

## Verification

All recommendations preserve:
- `_extract_tests_passed()` nested JSON path lookup (TASK-FIX-CKPT) - unchanged
- Approval-before-stall-detection ordering (TASK-FIX-CKPT) - unchanged
- Two-mechanism stall detection (TASK-AB-SD01) - unchanged, only threshold adjusted
- Checkpoint rollback-on-pollution behavior - unchanged

## Decision Matrix

| Option | Fixes This Stall | Prevents Similar | Effort | Risk | Preserves Arch |
|--------|-----------------|-----------------|--------|------|----------------|
| Rec 1+2+3 (null handling + threshold) | Yes | Partially | Low | Low | Yes |
| Rec 1+2+3+4 (above + better feedback) | Yes | Yes | Medium | Low | Yes |
| Rec 1-5 (all, inc. wave planning) | Yes | Yes | High | Medium | Yes |
| Fix null only (Rec 1+2) | Partial | No | Low | Low | Yes |
| Change task definition | No | No | Low | High | N/A |

**Recommended minimum**: Rec 1+2+3 (null handling + threshold increase)
**Recommended comprehensive**: Rec 1+2+3+4 (add better feedback for incomplete sessions)

## Actionable Next Steps

1. Create fix task for Rec 1+2+3 (+4 if chosen) — similar to TASK-FIX-CKPT scope
2. After fix: re-run FEAT-D4CE from Wave 3 (resume mode)
3. Track Rec 5 (wave planning scope overlap) as separate backlog item
4. Monitor: if DM-008 stalls again after fix, investigate DM-005 scope bleed further

## Comparison: This Stall vs TASK-FIX-CKPT

| Aspect | TASK-FIX-CKPT (prior) | This stall (DM-008) |
|--------|----------------------|---------------------|
| What happened | Coach approved, stall detector overrode it | Coach gave feedback (correctly), stall detector triggered |
| Data present? | Yes (tests_passed=true, but wrong JSON path) | No (all_passed=null, Player never completed gates) |
| False positive? | Yes — Coach approved but stall won | No — Player genuinely didn't complete quality gates |
| Fix location | Coach reader (JSON path + ordering) | Writer defaults + Coach null handling + threshold |
| Same bug? | No | No — different failure mode |
