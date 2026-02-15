# Implementation Guide: AutoBuild Stall Fixes (FEAT-ASF)

## Pre-Implementation Checklist

Before starting any phase, review:
- [ ] Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md`
- [ ] Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md`
- [ ] This guide's interaction risks section

## Dependency Graph

```
Phase 1 (zero risk):
  TASK-ASF-001 ──┐
                 ├── Phase 2 (low risk):
  TASK-ASF-002 ──┤     TASK-ASF-003 ──┐
                 │     TASK-ASF-004 ──┤
                 │                    ├── Phase 3 (medium risk):
                 │                    │     TASK-ASF-005 ──┐  (R5: scope tests)
                 │                    │                    │
                 │                    │     TASK-ASF-006 ──┘  (R4-full: MUST follow R5)
                 │                    │          │
                 │                    │          ├── Phase 4 (medium-high risk):
                 │                    │          │     TASK-ASF-007  (R6: thread cancel)
                 │                    │          │          │
                 │                    │          │     TASK-ASF-008  (R7: dynamic timeout)
```

## Phase 1: Unblock Re-Run

**Goal**: Get FEAT-AC1A re-run working with zero code changes.

### TASK-ASF-001: Switch SFT-001 to direct mode
- **Files**: `TASK-SFT-001-scaffolding.md`, `FEAT-AC1A.yaml`
- **Change**: `implementation_mode: task-work` → `implementation_mode: direct`
- **Also**: Reset statuses to `pending`, clear `autobuild_state`
- **Risk**: None
- **Verify**: Re-run FEAT-AC1A Wave 1, confirm SFT-001 uses direct path

### TASK-ASF-002: Pre-flight FalkorDB check
- **Files**: `feature_orchestrator.py`
- **Change**: Add `_preflight_check()` before wave execution
- **Risk**: None (additive)
- **Verify**: Run with FalkorDB down, confirm graceful disable + warning

## Phase 2: Fix Feedback Loop

**Goal**: Make Coach feedback actionable and add synthetic report observability.

### TASK-ASF-003: Include missing_criteria in feedback
- **File**: `autobuild.py` (~line 3124)
- **Change**: Modify `_extract_feedback()` to include `missing_criteria` items
- **Risk**: Low — only changes feedback text content
- **Verify**: Run a task that fails Coach validation, confirm Player receives specific criteria list
- **Stall detector impact**: MD5 hash will differ across turns with different missing criteria — this is *desirable*

### TASK-ASF-004: Synthetic report observability (R4-lite)
- **File**: `autobuild.py` (~line 2114)
- **Change**: Add `_synthetic: True` flag + warning logs
- **Risk**: None — informational only
- **Verify**: Trigger an SDK timeout, confirm warning appears in logs

## Phase 3: Fix Detection

**Goal**: Fix test masking and enable synthetic report approval.

### CRITICAL ORDERING: TASK-ASF-005 must complete before TASK-ASF-006

**Why**: Diagram 5 identified this interaction risk:
1. If R4-full adds file-existence promises to synthetic reports...
2. And test detection is still worktree-wide...
3. Then a scaffolding task could be approved via file-existence promises while its task-specific tests are actually failing.

Fix: Scoped test detection (R5) must be in place before synthetic reports gain promises (R4-full).

### TASK-ASF-005: Scope test detection
- **Files**: `coach_verification.py`, `state_detection.py`, `coach_validator.py`, `autobuild.py`
- **Change**: Add `test_paths` parameter to `_run_tests()`, propagate through call chain
- **Risk**: Medium — changes CoachVerifier interface
- **Verify**:
  1. Task with `test_scope`: confirm pytest runs only against specified paths
  2. Task without `test_scope`: confirm full-worktree run (backward compat)
  3. Create a worktree with failing tests outside `test_scope`, confirm they don't mask task tests

### TASK-ASF-006: Enrich synthetic reports (R4-full)
- **Files**: `autobuild.py`, `coach_validator.py`
- **Change**: Generate file-existence promises for scaffolding tasks; add Coach fast-fail for synthetic reports
- **Risk**: Medium — changes Coach validation path for recovered turns
- **Verify**:
  1. Trigger SDK timeout for a scaffolding task, confirm file-existence promises generated
  2. Confirm Coach approves when files exist and task-specific tests pass
  3. Confirm Coach rejects when files exist but task-specific tests fail (false approval prevention)
  4. Confirm non-scaffolding tasks are unaffected

## Phase 4: Fix Lifecycle

**Goal**: Prevent ghost threads and optimize timeouts.

### TASK-ASF-007: Cooperative thread cancellation
- **Files**: `feature_orchestrator.py`, `autobuild.py`
- **Change**: `threading.Event` per task, cancellation checks in `_loop_phase()` at loop top AND between Player/Coach
- **Risk**: Medium — touches main loop (most sensitive code)
- **Verify**:
  1. Trigger task timeout, confirm thread exits within one turn
  2. Confirm checkpoint saved on cancellation
  3. Confirm healthy parallel tasks are NOT cancelled by sibling timeout
  4. Run two features in sequence, confirm no ghost thread interference

### TASK-ASF-008: Dynamic SDK timeout
- **Files**: `agent_invoker.py`
- **Change**: Calculate timeout from mode + complexity
- **Risk**: Low — parameter change only
- **Verify**: Confirm task-work mode gets 1.5x timeout, complexity scales as expected

## Interaction Risks

These interaction paths were identified by the diagnostic diagrams and must be verified:

### 1. R3 + Stall Detector

**Risk**: R3 changes feedback text, which changes the MD5 hash used by `_is_feedback_stalled()`.
**Expected behavior**: Stall detection becomes more accurate — triggers only when the same *specific* criteria are stuck.
**Verification**: Run a task where the same criteria fail 3 times → stall detected. Run a task where different criteria fail each time → no stall.

### 2. R4-full + R5 (FALSE APPROVAL)

**Risk**: File-existence promises + unscoped tests = false approval.
**Mitigation**: R5 MUST be complete before R4-full.
**Verification**: After both are in place, create a scaffolding task where files exist but task-specific tests fail → must be rejected.

### 3. R6 + Parallel Tasks

**Risk**: Setting cancellation event for one task could cancel healthy parallel tasks.
**Mitigation**: Each task gets its own `threading.Event`. Only set all events on feature-level failure.
**Verification**: In a wave with 2 tasks, timeout one → confirm the other completes normally.

### 4. R6 + Coach Mid-Validation

**Risk**: Cancellation during Coach validation could leave inconsistent state.
**Mitigation**: Cancellation check between Player and Coach phases; checkpoint before exit.
**Verification**: Force cancellation during Coach phase → confirm clean checkpoint saved.

## Reference Diagrams

When implementing each task, consult these diagrams as the regression safety net:

| Diagram | Purpose | Relevant Tasks |
|---------|---------|---------------|
| 1. C4 Component | System overview, affected components | All |
| 2. Complete Execution Path | Every branch and decision point | ASF-005, ASF-006, ASF-007 |
| 3. Death Spiral Sequence | Turn-by-turn actual execution | ASF-003, ASF-004, ASF-006 |
| 4. Data Flow | Read/write paths, disconnections | ASF-003, ASF-006 |
| 5. Fix Impact Analysis | Component interactions per fix | ASF-005 + ASF-006 interaction |
| 6. Task Lifecycle State Machine | All states and transitions | ASF-007 |
| 7. Undetected Bugs | Paths not exercised | ASF-002 (Q8), ASF-007 (Q8) |
| 8. Implementation Order | Dependency-aware phasing | All (this guide) |
| 9. Feedback Contract | Coach → Player data contract | ASF-003 |
