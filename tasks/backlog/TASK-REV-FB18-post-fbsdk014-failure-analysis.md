---
id: TASK-REV-FB18
title: Analyze feature-build Coach validation failures after TASK-FBSDK-014
status: review_complete
created: 2026-01-21T10:00:00Z
updated: 2026-01-21T20:05:00Z
priority: critical
tags: [review, feature-build, autobuild, coach-validation, quality-gates, type-errors]
task_type: review
complexity: 6
decision_required: true
review_mode: decision
review_depth: comprehensive
prior_reviews:
  - TASK-REV-FB01  # Initial feature-build architecture approval
  - TASK-REV-FB02 through FB17  # Full history of feature-build issues
  - TASK-FBSDK-010 through FBSDK-014  # All SDK fix tasks
related_implementations:
  - TASK-FBSDK-014  # Plan generation during feature-plan - NOW WORKING
review_results:
  findings_count: 3
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB18-review-report.md
  completed_at: 2026-01-21T20:05:00Z
  implementation_tasks:
    - TASK-FBSDK-015  # Fix tests_passed type
    - TASK-FBSDK-016  # Fix schema mismatch
    - TASK-FBSDK-017  # Add debug logging
---

# TASK-REV-FB18: Analyze Feature-Build Coach Validation Failures

## Context

This is review **18** in the feature-build analysis series. After implementing TASK-FBSDK-014 and **properly running `/feature-plan` first** to generate implementation plans, `/feature-build FEAT-1D98` shows **significant progress** but fails due to **Coach validation issues**.

### Critical Update: FBSDK-014 IS Working

The re-test with a fresh `/feature-plan` run demonstrates that FBSDK-014's plan generation IS working:
- Duration: **7m 5s** (real SDK work happening, not 1s immediate failure)
- Files created: pyproject.toml, src/, tests/ with 7 passing tests
- Implementation: Actually complete for Wave 1 task

**The problem has shifted** from "SDK never invoked" to "Coach gives false negatives on completed work".

### Historical Context

| Review | Focus | Key Finding | Status |
|--------|-------|-------------|--------|
| FB01 | Architecture | Initial design approval (78/100) | ✅ Validated |
| FB17 | Root cause | SDK never invoked due to missing plan | ✅ **FIXED by FBSDK-014** |
| FB18 | **NEW** | Coach validation false negatives | 🔴 Current issue |

## Test Evidence Summary

### Run 1: FEAT-1D98 Fresh Feature Plan
```
Feature: FastAPI Health App
Tasks: 5 total, 4 waves
Duration: 7m 5s (real work!)
Result: MAX_TURNS_EXCEEDED on Wave 1
```

**What Actually Happened:**
1. ✅ Worktree created successfully
2. ✅ Task files copied to worktree (5 files)
3. ✅ Task TASK-HLTH-61B6 transitioned to design_approved
4. ✅ SDK invoked successfully (7+ minutes of real work)
5. ✅ **Implementation completed**: pyproject.toml, src/, tests/ created
6. ✅ **Tests pass**: 7/7 tests passing
7. ❌ **Coach validation fails** with false negatives

**Coach Feedback (False Negatives):**
```
Feedback: - Tests did not pass during task-work execution
        - Architectural review score b...  [truncated]
```

**Reality Check (Manual Verification):**
```bash
$ cd .guardkit/worktrees/FEAT-1D98
$ pytest tests/ -v
7 passed ✓
```

### Run 2: Resume After Manual Approval
After manually marking TASK-HLTH-61B6 as completed, Wave 2 started but hit a **different error**:

```
Player report validation failed:
Type errors: tests_passed: expected bool, got int
```

This reveals the Player is returning `tests_passed: 7` (count) instead of `tests_passed: true` (boolean).

## Identified Issues

### Issue 1: Coach False Negatives on Quality Gates (HIGH)

**Symptom**: Coach reports "Tests did not pass" when tests actually pass (7/7).

**Evidence**:
- `coach_turn_5.json` contains rejection despite actual test success
- Manual `pytest` verification shows 7 passing tests
- Implementation is complete and working

**Likely Causes**:
1. Coach is reading stale/incorrect task_work_results.json
2. task_work_results.json is not being written to the path Coach reads
3. Coach validation logic has incorrect path resolution in worktree context

### Issue 2: Player Report Type Validation Error (HIGH)

**Symptom**: `tests_passed: expected bool, got int`

**Evidence**:
```
ERROR: Player report validation failed:
Type errors: tests_passed: expected bool, got int
```

**Root Cause**: The Player agent's JSON report schema expects:
```json
{ "tests_passed": true }
```

But the Player is outputting:
```json
{ "tests_passed": 7 }  // Number of passing tests
```

**Location**: Likely in `agent_invoker.py` or Player agent prompt/schema definition.

### Issue 3: Coach Reads Wrong task_work_results.json Path (MEDIUM)

**Evidence from FB17 review**:
```
Coach Validation → ⚠ feedback (Task-work results not found at /Users/richardwoollcott...)
```

Even when results ARE written, Coach may be looking in the wrong location:
- Written to: `.guardkit/autobuild/TASK-XXX/task_work_results.json`
- Coach looking at: Different path?

## Questions to Answer

1. **Where is Coach reading task_work_results.json from?**
   - Is it the worktree path or main repo path?
   - Is there a path resolution bug in worktree context?

2. **Why does Coach report "tests did not pass" when they do?**
   - Is it reading an old/stale results file?
   - Is the results file being overwritten incorrectly?
   - Is Coach validation logic comparing wrong fields?

3. **Why is Player returning int instead of bool for tests_passed?**
   - What is the Player report schema definition?
   - Where does the Player construct its report?
   - Is there a TaskWorkStreamParser issue?

4. **Is there a worktree vs main repo path confusion?**
   - All paths should be worktree-relative during feature-build
   - Is something falling back to main repo paths?

## Files to Investigate

### Coach Validation Logic
- `guardkit/orchestrator/coach_validator.py` - Where Coach reads and validates results
- Look for: `task_work_results_path()` calls, path resolution

### Player Report Generation
- `guardkit/orchestrator/agent_invoker.py` - Where Player report is parsed/written
- Look for: `tests_passed` field handling, TaskWorkStreamParser

### Path Centralization (FBSDK-003)
- `guardkit/tasks/artifact_paths.py` - TaskArtifactPaths class
- Verify: Consistent path usage between Player write and Coach read

### Schema Definitions
- `guardkit/orchestrator/schemas.py` or similar - Player report schema
- Check: `tests_passed` field type definition

## Acceptance Criteria

1. Identify the **exact code path** where Coach reads task_work_results.json
2. Identify the **exact code path** where Player writes tests_passed field
3. Determine why Coach gets false negatives on passing tests
4. Determine why Player outputs int instead of bool for tests_passed
5. Provide **specific fix tasks** with file:line locations

## Proposed Fix Tasks (Preliminary)

### TASK-FBSDK-015: Fix tests_passed Type in Player Report
- **Location**: `agent_invoker.py` or TaskWorkStreamParser
- **Fix**: Ensure `tests_passed` is boolean, not int
- **Validation**: Player report passes schema validation

### TASK-FBSDK-016: Fix Coach Path Resolution in Worktree Context
- **Location**: `coach_validator.py`
- **Fix**: Ensure Coach reads from worktree path, not main repo
- **Validation**: Coach finds and correctly reads task_work_results.json

### TASK-FBSDK-017: Add Debug Logging for Quality Gate Evaluation
- **Location**: `coach_validator.py`, `agent_invoker.py`
- **Fix**: Log the actual values being compared in quality gate checks
- **Validation**: Can trace exactly why Coach approves/rejects

## Evidence Files

| File | Content | Status |
|------|---------|--------|
| `docs/reviews/feature-build/after_fix_TASK-FBSDK-014.md` | Full test output | Updated |
| `.guardkit/worktrees/FEAT-1D98/.guardkit/autobuild/TASK-HLTH-61B6/` | Turn artifacts | Available |
| `task_work_results.json` | Final results | Available |
| `coach_turn_*.json` | Coach decisions | Available |
| `player_turn_*.json` | Player reports | Available |

## Risk Assessment

**Risk Level**: MEDIUM (reduced from HIGH)

**Good News**:
- FBSDK-014 fix is working - SDK is being invoked
- Actual implementation work is happening
- Tests are passing
- Problem is now in validation layer, not core orchestration

**Remaining Risk**:
- Two distinct bugs need fixing (type error + path resolution)
- May be masking other issues
- Coach false negatives could undermine trust in the system

## Decision Point Preview

| Option | Description |
|--------|-------------|
| **[A] Accept** | Analysis complete, create fix tasks FBSDK-015, -016, -017 |
| **[R] Revise** | Need to inspect actual JSON files before deciding |
| **[I] Implement** | Proceed directly to implementation (reviewer has enough info) |
| **[W] Workaround** | Document manual approval process as temporary workaround |

## Progress Summary

### What's Working ✅
- Plan generation during /feature-plan (FBSDK-014)
- SDK invocation and real work execution
- Worktree creation and management
- Task file copying
- State transitions (backlog → design_approved)
- Actual code implementation
- Test execution (tests pass)

### What's Broken ❌
- Player report type validation (int vs bool)
- Coach quality gate evaluation (false negatives)
- Resume workflow (task file location after state transition)

### Next Steps
1. Execute this review to identify exact code locations
2. Create targeted fix tasks (FBSDK-015, -016, -017)
3. Implement fixes in priority order
4. Re-test with fresh /feature-plan → /feature-build cycle
