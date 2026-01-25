# Review Report: TASK-REV-FB01 - Feature-Build Timeout Analysis

## Executive Summary

This review analyzes the feature-build timeout behavior and task-work results issues observed in the evidence file. The analysis reveals **three distinct root causes** contributing to feature-build failures, with timeout being a symptom rather than the primary issue.

**Key Finding**: The feature-build IS working - Player agent successfully implements code - but fails at the reporting layer, causing every turn to be marked as failed despite real progress.

**Architecture Score**: N/A (Decision Analysis mode)

**Recommendation**: **[F]ix** - Create specific implementation tasks for two critical bugs before increasing timeout.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard (1-2 hours)
- **Duration**: ~90 minutes
- **Evidence File**: [feature-build-output.md](../../docs/reviews/feature-build/feature-build-output.md)

---

## Root Cause Analysis

### Issue 1: Player Report Not Written (CRITICAL - Root Cause)

**Severity**: Critical (Blocks all validation)

**Evidence**:
```
Error: Player report not found:
/Users/.../feature_build_cli_test/.guardkit/worktrees/FEAT-3DEB/.guardkit/autobuild/TASK-INFRA-001/player_turn_1.json
```

**Analysis**:

The Player agent completes implementation work (creates 6-7 files per turn including `src/core/config.py`, `tests/core/test_config.py`, `venv/`) but does NOT create the expected `player_turn_N.json` report file.

**Code Path Traced**:

1. [autobuild.py:792-897](guardkit/orchestrator/autobuild.py#L792-L897) - Loop expects Player report
2. [agent_invoker.py:154-316](guardkit/orchestrator/agent_invoker.py#L154-L316) - Invokes Player agent
3. [autobuild-player.md](.claude/agents/autobuild-player.md) - Agent instructions

**Root Cause**: The Player agent delegates to `task-work --implement-only`, which produces `task_work_results.json` at the end. However, the orchestrator expects the Player to write a **separate** `player_turn_N.json` report. The delegation architecture creates a mismatch:

- **Expected**: Player writes `player_turn_N.json` with structured fields
- **Actual**: task-work writes `task_work_results.json`, Player doesn't write additional report

**Impact**: Every turn is marked as "failed" even when implementation succeeds.

### Issue 2: Coach Validator Path Bug (CRITICAL)

**Severity**: Critical (Blocks validation)

**Evidence**:
```
WARNING: Task-work results not found at
/Users/.../feature_build_cli_test/.guardkit/worktrees/TASK-INFRA-001/.guardkit/autobuild/TASK-INFRA-001/task_work_results.json
```

**Analysis**:

Coach validator constructs path using task ID (`TASK-INFRA-001`) instead of feature worktree ID (`FEAT-3DEB`).

**Code Path Traced**:

1. [coach_validator.py:259-274](guardkit/orchestrator/quality_gates/coach_validator.py#L259-L274) - Path construction
2. [coach_verification.py:259](guardkit/orchestrator/coach_verification.py#L259) - Uses worktree path

**Root Cause**: When running in feature mode, the worktree is shared (`FEAT-3DEB`) but Coach constructs path using individual task ID. Path should be:
- **Wrong**: `.guardkit/worktrees/TASK-INFRA-001/.guardkit/autobuild/...`
- **Correct**: `.guardkit/worktrees/FEAT-3DEB/.guardkit/autobuild/TASK-INFRA-001/...`

**Impact**: Coach can never find task-work results, validation always fails.

### Issue 3: Default Timeout Insufficient (HIGH - But Not Root Cause)

**Severity**: High (Exacerbates failures)

**Evidence**:
```
Error: SDK timeout after 300s: Agent invocation exceeded 300s timeout
```

**Analysis**:

The 300-second default is insufficient for the multi-phase workflow:

| Phase | Typical Duration |
|-------|------------------|
| Pre-Loop (2-2.8) | 125-315s |
| Loop (3-5.5) | 180-420s |
| **Total** | 305-735s |

However, increasing timeout alone does NOT fix the issue because Issues 1 and 2 cause failures even with 1800s timeout.

**Code Reference**: [agent_invoker.py:44](guardkit/orchestrator/agent_invoker.py#L44)

```python
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "300"))
```

---

## Findings Summary

| # | Issue | Severity | Status | Fix Required |
|---|-------|----------|--------|--------------|
| 1 | Player report not written | Critical | New bug | Yes - New task |
| 2 | Coach validator path bug | Critical | Confirmed | Yes - New task |
| 3 | Default timeout too short | High | Known | Yes - TASK-SDK-e7f2 |
| 4 | Test detection outside venv | Medium | New | Optional |
| 5 | External bash timeout (137) | Low | UX | Documentation |

---

## Options Evaluation

### Option A: Increase Timeout Only (TASK-SDK-e7f2)

**Pros**:
- Quick fix (15 minutes)
- Already planned

**Cons**:
- Does NOT fix root cause
- Issues 1 & 2 still cause failures with any timeout
- Masks underlying problems

**Score**: 3/10 (treats symptom, not cause)

### Option B: Fix Critical Bugs First, Then Timeout

**Pros**:
- Addresses root causes
- Feature-build will actually work
- Timeout increase becomes effective

**Cons**:
- More work upfront (2-4 hours)

**Score**: 9/10 (correct approach)

### Option C: Architectural Refactor of Report Flow

**Pros**:
- Clean long-term solution
- Eliminates report mismatch

**Cons**:
- Significant refactor (8+ hours)
- Not necessary for MVP

**Score**: 5/10 (overkill for current needs)

---

## Recommendations

### Recommended Option: B (Fix Critical Bugs First)

**Implementation Order**:

1. **TASK-FB-RPT1** (Critical, 1-2 hours): Fix Player report writing
   - Modify Player agent to write `player_turn_N.json` after task-work delegation
   - OR modify orchestrator to read `task_work_results.json` directly
   - Location: [agent_invoker.py](guardkit/orchestrator/agent_invoker.py) + [autobuild-player.md](.claude/agents/autobuild-player.md)

2. **TASK-FB-PATH1** (Critical, 1 hour): Fix Coach validator path
   - Use feature worktree path when in feature mode
   - Pass worktree_path through to Coach validation
   - Location: [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py)

3. **TASK-SDK-e7f2** (High, 15 minutes): Increase default timeout
   - Change `DEFAULT_SDK_TIMEOUT` from 300 to 600
   - Update documentation with guidance

4. **Documentation** (Low, 30 minutes): Add note about running from terminal
   - Claude Code's 10-minute bash timeout kills long builds
   - Recommend: `guardkit autobuild feature FEAT-XXX` from terminal

### Files to Modify

| File | Change |
|------|--------|
| [guardkit/orchestrator/agent_invoker.py](guardkit/orchestrator/agent_invoker.py) | Add Player report writing after task-work delegation |
| [guardkit/orchestrator/quality_gates/coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | Fix path construction for feature mode |
| [guardkit/orchestrator/agent_invoker.py:44](guardkit/orchestrator/agent_invoker.py#L44) | Change DEFAULT_SDK_TIMEOUT to 600 |
| [CLAUDE.md](CLAUDE.md) | Document timeout recommendations |

---

## Decision Matrix

| Option | Fixes Root Cause | Effort | Risk | Impact | Score |
|--------|------------------|--------|------|--------|-------|
| A (Timeout only) | No | Low | Low | Low | 3/10 |
| **B (Bugs + Timeout)** | **Yes** | **Medium** | **Low** | **High** | **9/10** |
| C (Refactor) | Yes | High | Medium | High | 5/10 |

---

## Test Plan

After implementing fixes:

1. **Unit Tests**:
   - Test Player report is written to correct path
   - Test Coach validator uses feature worktree path
   - Test timeout configuration cascade

2. **Integration Test**:
   ```bash
   # From terminal (not Claude Code)
   guardkit autobuild feature FEAT-TEST --sdk-timeout 900 --verbose
   ```

3. **Success Criteria**:
   - Player report found at `.guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/player_turn_1.json`
   - Coach finds `task_work_results.json` at correct path
   - At least one task completes with "approve" decision

---

## Appendix

### Evidence: Player IS Working

Despite orchestration failures, the Player agent created production-ready code:

```
src/core/config.py         (222 lines) - Pydantic Settings with validation
tests/core/test_config.py  (464 lines) - 14 test classes
tests/conftest.py          (66 lines)  - Test fixtures
requirements/{base,dev,prod}.txt       - Dependencies
venv/                      (2916 files) - Full Python environment
```

### Related Tasks

| Task | Status | Relevance |
|------|--------|-----------|
| TASK-SDK-a7f3 | Completed | SDK error handling (helps diagnosis) |
| TASK-WKT-b2c4 | Completed | Worktree path issues (partial fix) |
| TASK-WKT-c5d7 | In Progress | May address path propagation |
| TASK-SDK-e7f2 | Backlog | Increase default timeout |

---

*Review completed: 2026-01-09*
*Reviewer: Decision analysis mode*
