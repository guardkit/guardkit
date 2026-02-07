# Review Report: TASK-REV-AB01

## Executive Summary

Analysis of the FEAT-D4CE autobuild run reveals a **confirmed false positive** in the unrecoverable stall detection for TASK-DM-002. The Coach approved the implementation on Turn 2, but the stall detector overrode this valid approval because the checkpoint system uses a different data source than the Coach to determine test pass/fail status. The FEAT-FPP path fix is confirmed working. TASK-DM-001 succeeded correctly. The core issue is a **data source mismatch** between two subsystems that should agree but don't.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Task**: TASK-REV-AB01
- **Feature**: FEAT-D4CE (Design mode for Player-Coach loops)

---

## Finding 1: FEAT-FPP Path Fix - Confirmed Working

**Severity**: Informational | **Status**: Resolved

The autobuild output (line 18) shows `Feature validation passed`, compared to the prior `Task file not found` errors. The feature loader successfully:
- Loaded all 8 tasks from `.guardkit/features/FEAT-D4CE.yaml`
- Created the shared worktree at `.guardkit/worktrees/FEAT-D4CE`
- Copied all 8 task files to the worktree

**Verdict**: FEAT-FPP path generation fix is confirmed working. No further action needed.

---

## Finding 2: TASK-DM-001 Success Analysis

**Severity**: Informational | **Status**: Correct Behavior

TASK-DM-001 ("Extend task frontmatter for design URLs") succeeded in 1 turn with 18 files created and 3 modified. Key observations:

1. **Task type classification**: CoachValidator used `scaffolding` profile, which has `tests_required=False`
2. **Quality gates**: All gates passed immediately because scaffolding profile skips test enforcement
3. **Independent verification**: Skipped (`tests_required=False`)
4. **Checkpoint status**: `tests_passed=false, test_count=0` - marked as failing even though Coach approved

**Concern**: The checkpoint for TASK-DM-001 records `tests: fail` despite Coach approval. This is technically correct (no tests ran), but the semantic meaning is misleading. For scaffolding tasks where tests aren't required, the checkpoint should arguably record `tests: pass` (or `tests: n/a`). However, since TASK-DM-001 completed in 1 turn and was approved, this inconsistency didn't cause any issue here.

**Verdict**: Scaffolding classification was correct for a frontmatter extension task. Approval in 1 turn is expected.

---

## Finding 3: TASK-DM-002 Unrecoverable Stall - ROOT CAUSE IDENTIFIED

**Severity**: Critical (Bug) | **Status**: False Positive Confirmed

### The Bug: Data Source Mismatch Between Coach and Checkpoint System

The UNRECOVERABLE_STALL on TASK-DM-002 is a **false positive**. Here's the exact sequence:

#### Turn 2 Timeline

| Step | Subsystem | Data Source | Result |
|------|-----------|-------------|--------|
| 1 | Player | SDK execution | Created 4 files, 3 modified |
| 2 | Coach | `task_work_results.json` | `tests_passing=true`, `coverage=85.0`, `all_passed=true` |
| 3 | Coach | Quality gates | **APPROVED** (`all_gates_passed=true`) |
| 4 | Checkpoint | `_extract_tests_passed(turn_record)` | **`false`** |
| 5 | Stall detector | `should_rollback()` | 2 consecutive failures detected |
| 6 | Stall detector | `find_last_passing_checkpoint()` | No passing checkpoint found |
| 7 | Orchestrator | Exit | **UNRECOVERABLE_STALL** (overrides Coach approval) |

### Why the Checkpoint Got the Wrong Answer

The `_extract_tests_passed()` method (autobuild.py:2812-2826) reads:

```python
validation = turn_record.coach_result.report.get("validation_results", {})
return validation.get("tests_passed", False)
```

Looking at the Coach Turn 2 report (`coach_turn_2.json`):

```json
"validation_results": {
    "quality_gates": {
        "tests_passed": true,   // <-- HERE: nested under quality_gates
        ...
    },
    "independent_tests": {
        "tests_passed": true,   // <-- HERE: nested under independent_tests
        ...
    }
}
```

The extraction looks for `validation_results.tests_passed` (top-level), but the actual value is at `validation_results.quality_gates.tests_passed` (nested). Since `tests_passed` doesn't exist at the top level, it defaults to `False`.

**This is the root cause**: `_extract_tests_passed()` reads from the wrong JSON path.

### Why Turn 1 Also Failed (Correctly)

Turn 1's Coach report has `tests_passed: null` in `quality_gates` (tests hadn't run), so Coach correctly gave feedback. The checkpoint also recorded `tests_passed=false` (correct for Turn 1).

### The Race Condition in Code Flow

The critical issue is in `_loop_phase()` (autobuild.py:1002-1065). After the Coach validates:

1. **Line 1004**: Checkpoint is created using `_extract_tests_passed()` (gets **wrong** answer)
2. **Line 1019**: `should_rollback()` checks consecutive failures (sees 2 failures)
3. **Line 1020**: `find_last_passing_checkpoint()` finds nothing
4. **Line 1042-1048**: Returns `"unrecoverable_stall"` **BEFORE reaching line 1063**
5. **Line 1063**: `if turn_record.decision == "approve"` **NEVER REACHED**

The stall detection executes **before** the approval check, so a valid Coach approval is overridden.

---

## Finding 4: Test Detection Issue

**Severity**: Medium | **Status**: Contributing Factor

Both turns show "0 tests (failing)" in the progress display. The Coach Turn 2 report shows:

```json
"independent_tests": {
    "test_command": "skipped",
    "test_output_summary": "No task-specific tests found for TASK-DM-002, skipping independent verification"
}
```

The `_detect_test_command()` method searches for files matching `tests/test_dm_002*.py` (derived from task ID). Since the Player created test files with different naming (in `tests/orchestrator/` or `tests/unit/`), the pattern didn't match.

However, `task_work_results.json` reports `tests_passing=true` and `coverage=85.0`, meaning the Player **did** run tests during task-work execution. The independent verification just couldn't find them to re-run.

**Impact**: The independent verification gap means Coach relied solely on the Player's self-reported test results, but this is actually acceptable behavior (Coach approved based on `quality_gates.all_passed=true`). The real problem is that the checkpoint system doesn't use the same data.

---

## Finding 5: Stall Detection Logic Analysis

**Severity**: Critical (Design Issue) | **Status**: Needs Fix

### Problem: Checkpoint Tests vs Coach Decision Are Decoupled

The architecture has two parallel truth sources that disagree:

| Question | Coach Answer | Checkpoint Answer |
|----------|-------------|-------------------|
| "Did TASK-DM-002 Turn 2 pass?" | Yes (approve) | No (tests_passed=false) |
| "Data source" | `task_work_results.json` quality gates | `turn_record.coach_result.report["validation_results"]["tests_passed"]` |
| "Correct?" | Yes | No (wrong JSON path) |

### The Design Flaw

Even if the JSON path is fixed, there's a deeper architectural issue: **the stall detector can override a Coach approval**. The code flow is:

```
checkpoint created → stall check → approval check
```

If stall detection triggers, it returns `"unrecoverable_stall"` before ever checking `turn_record.decision == "approve"`. This means:

- A task can be **simultaneously approved by Coach AND killed by stall detector**
- The stall detector should either (a) defer to Coach approval, or (b) use the same data source as Coach

---

## Recommendations

### Recommendation 1: Fix `_extract_tests_passed()` JSON Path (Critical, Quick Fix)

**Priority**: P0 | **Effort**: Low | **Risk**: Low

Fix the extraction to check the correct nested path:

```python
def _extract_tests_passed(self, turn_record: TurnRecord) -> bool:
    if not turn_record.coach_result or not turn_record.coach_result.success:
        return False
    validation = turn_record.coach_result.report.get("validation_results", {})
    # Check nested quality_gates path first (Coach v2 format)
    qg = validation.get("quality_gates", {})
    if "tests_passed" in qg:
        return bool(qg["tests_passed"])
    # Fallback to top-level (legacy format)
    return validation.get("tests_passed", False)
```

### Recommendation 2: Short-Circuit Stall Detection on Coach Approval (Critical, Medium Fix)

**Priority**: P0 | **Effort**: Medium | **Risk**: Low

Reorder the code flow so Coach approval takes precedence over stall detection:

```python
# Check decision FIRST
if turn_record.decision == "approve":
    logger.info(f"Coach approved on turn {turn}")
    return turn_history, "approved"

# THEN check for stall (only relevant when Coach gives feedback)
if self.enable_checkpoints and self._checkpoint_manager:
    # ... checkpoint + stall detection logic ...
```

Alternatively, add a guard in the stall check:

```python
if self._checkpoint_manager.should_rollback():
    if turn_record.decision == "approve":
        logger.info("Stall detected but Coach approved - deferring to Coach")
    else:
        # ... existing stall handling ...
```

### Recommendation 3: Align Checkpoint Test Status with Coach Decision (Medium, Refactor)

**Priority**: P1 | **Effort**: Medium | **Risk**: Medium

Instead of independently extracting test status, use the Coach's decision as the source of truth:

```python
tests_passed = (turn_record.decision == "approve")
```

Or for nuance, use the Coach's quality gate evaluation directly:

```python
tests_passed = turn_record.coach_result.report
    .get("validation_results", {})
    .get("quality_gates", {})
    .get("all_gates_passed", False)
```

### Recommendation 4: Improve Test File Naming Detection (Low Priority)

**Priority**: P2 | **Effort**: Low | **Risk**: Low

The independent test verification searches for `tests/test_{task_prefix}*.py` but Player-created test files may use different naming conventions. Consider also searching for files in the Player's `files_created` list that match `test_*.py` or `*_test.py` patterns.

### Recommendation 5: Immediate Next Steps for FEAT-D4CE

**Priority**: P0 | **Effort**: Low

1. **Merge TASK-DM-001 manually**: The scaffolding changes are approved and clean
2. **Fix the two bugs (Rec 1 + Rec 2)** before re-running TASK-DM-002
3. **Re-run FEAT-D4CE with `--resume`** after fixes are applied
4. Do NOT adjust task_type classifications - they are correct

---

## Decision Matrix

| Option | Fixes Root Cause | Effort | Risk | Recommendation |
|--------|:---:|:---:|:---:|:---:|
| Fix JSON path only (Rec 1) | Partial | Low | Low | Necessary but not sufficient |
| Reorder approval/stall check (Rec 2) | Yes | Medium | Low | **Recommended** |
| Align checkpoint with Coach (Rec 3) | Yes (comprehensive) | Medium | Medium | Best long-term fix |
| Resume without fix | No | None | High | **Not recommended** |
| Adjust stall threshold to 3 | No (masks bug) | Low | Medium | Not recommended |

**Recommended approach**: Apply Rec 1 + Rec 2 together (fixes both the symptom and the architectural issue), then re-run FEAT-D4CE.

---

## Acceptance Criteria Verification

- [x] Root cause of TASK-DM-002 stall identified: `_extract_tests_passed()` reads wrong JSON path, causing checkpoint to record `tests_passed=false` even when Coach approved
- [x] Stall detection is a false positive: Coach approved Turn 2 but stall detector overrode it due to data source mismatch + code ordering
- [x] FEAT-FPP path fix confirmed working: "Feature validation passed" in output
- [x] Next steps recommended: Fix JSON path + reorder approval/stall check, then resume
- [x] Systemic issues identified: (1) Wrong JSON path in `_extract_tests_passed()`, (2) Stall detection can override valid Coach approval due to code ordering

---

## Appendix: Evidence Files Referenced

| File | Purpose |
|------|---------|
| `docs/reviews/ux_design_mode/revised_paths_output.md` | Full autobuild run output |
| `.guardkit/features/FEAT-D4CE.yaml` | Feature definition and execution results |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-001/coach_turn_1.json` | Coach approval for scaffolding task |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/coach_turn_1.json` | Coach feedback (tests not run) |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/coach_turn_2.json` | Coach approval (tests passed, 85% coverage) |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/task_work_results.json` | Player self-report (all_passed=true, 85% coverage) |
| `.guardkit/worktrees/FEAT-D4CE/.guardkit/autobuild/TASK-DM-002/checkpoints.json` | Both checkpoints showing `tests_passed=false` |
| `guardkit/orchestrator/autobuild.py:1002-1065` | Loop phase: checkpoint → stall → approval ordering |
| `guardkit/orchestrator/autobuild.py:2812-2826` | `_extract_tests_passed()` method with wrong JSON path |
