# Review Report: TASK-REV-CEE8

## Executive Summary

TASK-DOC-002 in FEAT-CEE8 run 2 was blocked by a **false positive zero-test anomaly** that rejected every turn despite the Player producing real passing tests. The root cause is a **dual bug**: (1) the direct mode results writer in `agent_invoker.py` does not propagate the actual test count from the Player's report into `quality_gates.tests_passed`, and (2) the zero-test anomaly check does not consider independently verified test results. This is primarily a **results writer bug** (not a CoachValidator bug or task_type classification issue).

## Review Details

- **Mode**: Root Cause Analysis (Decision/Technical)
- **Depth**: Comprehensive (revised with regression analysis)
- **Feature**: FEAT-CEE8 (Comprehensive API Documentation), run 2
- **Failed Task**: TASK-DOC-002 ("Configure main.py with full OpenAPI metadata")
- **Passed Task**: TASK-DOC-001 ("Create OpenAPI configuration module") — approved turn 1

## Prior Fix History (Regression Context)

This bug sits at the intersection of three prior fix chains. Each must be preserved:

### 1. TASK-REV-FB18 → FBSDK-015: `tests_passed` int/bool Type Fix

The task-work delegation path's stream parser captures `tests_passed` as an integer count. FBSDK-015 fixed this by:
- Converting `tests_passed` to boolean for `PLAYER_REPORT_SCHEMA` compliance (line 1527-1530)
- Preserving the count in a separate `tests_passed_count` field (line 1531)

The direct mode writer at line 2251 reads `tests_passed_count` — **but this field only exists on the task-work delegation path**. Direct mode Players write `PLAYER_REPORT_SCHEMA` directly, which has `tests_passed: bool` and no `tests_passed_count`.

**Regression risk**: Fix must not break the task-work path's `tests_passed_count` usage.

### 2. TASK-REV-312E → TASK-FIX-64EE: Null Quality Gates Handling

DM-008 was the first task where `all_passed: null` (Player exhausted SDK turns). Four fixes were applied:
- `verify_quality_gates()` falls through to `tests_failed` check when `all_passed` is null (lines 859-871)
- `_extract_tests_passed()` returns `False` for null values (line 3546-3548)
- Stall threshold increased from 2→3 (default, overridable)
- Incomplete session feedback mentions exhausted SDK turns

**Regression risk**: Fix must not change null-handling behavior. The zero-test anomaly intentionally does NOT fire when `all_passed is None` (only fires when `all_passed is True`). This is correct.

### 3. TASK-AQG-002: Zero-Test Anomaly Blocking

Added `zero_test_blocking` field to `QualityGateProfile`. FEATURE and REFACTOR profiles set it to `True`, making zero-test anomaly a hard blocker. The anomaly fires when: `all_passed is True AND tests_passed_count == 0 AND coverage is None`.

**Regression risk**: The anomaly check itself is correct for what it checks — the problem is that the data it receives is wrong (tests_passed=0 when it should be 2). Fix must not weaken the anomaly check for genuine zero-test cases (e.g., when a task-work Player truly produces no tests).

## Findings

### Finding 1: Direct Mode Results Writer Discards Test Count (ROOT CAUSE)

**Severity**: Critical
**File**: [agent_invoker.py:2249-2253](guardkit/orchestrator/agent_invoker.py#L2249-L2253)

The `_write_direct_mode_results()` method builds the `quality_gates` object as:

```python
"quality_gates": {
    "tests_passing": tests_passed if tests_run else None,
    "tests_passed": player_report.get("tests_passed_count", 0),  # LINE 2251
    "tests_failed": player_report.get("tests_failed_count", 0),
    "coverage": None,
    "coverage_met": True,
    "quality_gates_relaxed": True,
    "all_passed": success,
},
```

The problem is on line 2251: it reads `tests_passed_count` from the Player report. But the Player report schema (`PLAYER_REPORT_SCHEMA`, line 110-122) defines `tests_passed` as a **boolean**, not a count. The `tests_passed_count` field was added by FBSDK-015 and is **only** set by the task-work delegation path at line 1531 when the `TaskWorkStreamParser` emits integer counts. Direct mode Players follow `PLAYER_REPORT_SCHEMA` which uses `tests_passed: bool` — they never set `tests_passed_count`.

**Result**: `player_report.get("tests_passed_count", 0)` always returns `0` for direct mode, even when the Player has written and run 2 tests successfully.

**Why this wasn't caught earlier**: `_write_direct_mode_results` was created in the initial AutoBuild feature PR (commit `b7f0472a`). It assumed `tests_passed_count` would be available in the player report, likely modeled after the task-work path. But direct mode Players write their own reports using the prompt template schema, which doesn't include `tests_passed_count`. Zero-test anomaly blocking (TASK-AQG-002) was added later, turning what was a silent data gap into a hard blocker.

### Finding 2: Independent Test Verification Passes But Is Ignored

**Severity**: High

The Coach's independent test verification confirms tests pass (line 203: "Independent tests passed in 0.6s"). But the zero-test anomaly check runs **after** independent test verification (line 719-726) and does not receive the test result:

```
1. Quality gates evaluated → ALL_PASSED=True ✓
2. Task-specific tests detected → 2 files ✓
3. Independent tests run → PASSED in 0.6s ✓
4. Zero-test anomaly check → tests_passed=0, coverage=null → REJECTED ✗
```

The `_check_zero_test_anomaly()` signature only accepts `task_work_results` and `profile` — it has no parameter for independent test results. The Coach independently verified tests pass, then rejected because the results JSON says no tests ran.

### Finding 3: Task-Work Mode Results Writer Handles Counts Correctly

**Severity**: Informational
**File**: [agent_invoker.py:3139-3142](guardkit/orchestrator/agent_invoker.py#L3139-L3142)

The task-work delegation path writes `tests_passed` from the `TaskWorkStreamParser` which parses output like "12 tests passed, 0 failed" and emits an integer count. This is why TASK-DOC-001 (task-work mode) had no zero-test anomaly.

### Finding 4: TASK-DOC-002 Correctly Gets Feature Profile

**Severity**: Informational

TASK-DOC-002 doesn't have a `task_type` field in frontmatter → defaults to `feature` (line 474). The `feature` profile has `zero_test_blocking=True` (line 190 of task_types.py). This is correct — the task has testable code.

### Finding 5: `quality_gates_relaxed` Signal Is Never Consumed

**Severity**: Medium
**File**: [agent_invoker.py:2255](guardkit/orchestrator/agent_invoker.py#L2255)

The direct mode writer sets `quality_gates_relaxed: True` (line 2255), but no consumer in the entire codebase reads this field. It's a dead signal. grep confirms: no reference to `quality_gates_relaxed` exists in `coach_validator.py` or anywhere else outside the writer.

### Finding 6: file_path Fix from TASK-REV-1BE3 Is Working (AC-005)

Lines 24-29 confirm all 5 task files were successfully copied to worktree.

## Consumers of `quality_gates.tests_passed` (Full Audit)

9 distinct consumers were identified. Each must be evaluated for regression risk:

| # | Consumer | File:Line | Reads From | Impact |
|---|----------|-----------|------------|--------|
| 1 | `_write_task_work_results()` | agent_invoker.py:3141 | StreamParser result | **Writer** (task-work path) — not affected |
| 2 | `_write_direct_mode_results()` | agent_invoker.py:2251 | Player report | **Writer** (direct path) — **THE BUG** |
| 3 | `verify_quality_gates()` | coach_validator.py:857 | task_work_results.json `all_passed` | Uses `all_passed` not `tests_passed` count — not affected |
| 4 | `_check_zero_test_anomaly()` | coach_validator.py:1381 | task_work_results.json `tests_passed` | Reads the bad value — **TRIGGER POINT** |
| 5 | `_extract_tests_passed()` | autobuild.py:3547 | validation_results (Coach output) | Reads Coach boolean, not raw count — not affected |
| 6 | `WorktreeCheckpointManager` | worktree_checkpoints.py:297 | Boolean from `_extract_tests_passed` | Indirectly affected only via Coach decision |
| 7 | `StateTracker` | state_tracker.py:364 | player_turn_N.json (not task_work_results) | Different source — not affected |
| 8 | `CoachVerification` | coach_verification.py:153 | player_turn_N.json | Different source — not affected |
| 9 | `_build_validation_issues()` | coach_validator.py:1486 | task_work_results.json `tests_passed` | Only fires when `gates.tests_passed=False` — not reached here |

**Critical insight**: Only consumers #2 and #4 are involved in this bug. Consumer #3 (`verify_quality_gates`) reads `all_passed` (which is `True` for direct mode), so quality gates pass. Consumer #4 then reads the raw `tests_passed` count (which is `0`), triggering the anomaly.

## Direct Mode vs Task-Work Mode JSON Comparison (AC-002)

| Field | Task-Work Mode | Direct Mode | Issue |
|-------|---------------|-------------|-------|
| `quality_gates.tests_passed` | Integer (e.g., `12`) from stream parser | `0` (reads missing `tests_passed_count`) | **BUG** |
| `quality_gates.tests_failed` | Integer from stream parser | `0` (reads missing `tests_failed_count`) | Silent (same bug, not triggered) |
| `quality_gates.coverage` | Float (e.g., `85.5`) from parser | `None` (by design) | Expected |
| `quality_gates.all_passed` | From `quality_gates_passed` regex | `success` boolean | Different semantics |
| `quality_gates.coverage_met` | Computed `coverage >= 80` | Always `True` | Different semantics |
| `quality_gates.quality_gates_relaxed` | Not present | `True` | Dead signal (never consumed) |
| `implementation_mode` | Not present | `"direct"` | Not consumed by Coach |

## Root Cause Determination (AC-003)

**This is primarily an `agent_invoker.py` bug** (the results writer), not a CoachValidator bug or task_type classification issue.

The CoachValidator's zero-test anomaly check is working as designed — it correctly identifies that `tests_passed=0` and `coverage=null`. The problem is that the data it receives is wrong. The direct mode writer fails to propagate the actual test information from the Player's report.

There is also a **secondary CoachValidator design gap**: the zero-test anomaly check should consider the independent test verification result. If the Coach independently ran tests and they passed, the zero-test anomaly should not block approval.

## Recommendations (AC-004)

### Fix 1 (P0): Derive Test Count in Direct Mode Writer

**File**: [agent_invoker.py:2236-2257](guardkit/orchestrator/agent_invoker.py#L2236-L2257)

Replace the broken `tests_passed_count` lookup with derivation from `tests_written`:

```python
# Extract test info from Player report
tests_run = player_report.get("tests_run", False)
tests_passed = player_report.get("tests_passed", False)
tests_written = player_report.get("tests_written", [])

# Derive test count: use tests_passed_count if available (task-work path),
# otherwise derive from tests_written list length when tests_passed is True
tests_passed_count = player_report.get("tests_passed_count", 0)
if tests_passed_count == 0 and tests_passed and tests_written:
    tests_passed_count = len(tests_written)

# Then in quality_gates:
"tests_passed": tests_passed_count,
```

**Regression analysis**:
- Task-work path: `tests_passed_count` IS in the report → uses it directly (no change)
- Direct mode with tests: `tests_passed_count` missing → falls back to `len(tests_written)` (correct)
- Direct mode without tests: `tests_written=[]` → `tests_passed_count=0` (correct, anomaly fires as designed)
- TASK-FIX-64EE: Null handling unaffected (different code path in `verify_quality_gates`)
- TASK-AQG-002: Zero-test blocking unaffected for genuine zero-test cases

**Test cases needed**:
1. Direct mode Player with `tests_passed=True, tests_written=["a.py", "b.py"]` → `tests_passed=2`
2. Direct mode Player with `tests_passed=False, tests_written=["a.py"]` → `tests_passed=0` (tests exist but failed)
3. Direct mode Player with `tests_passed=True, tests_written=[]` → `tests_passed=0` (edge case: boolean says passed but no files listed)
4. Task-work path with `tests_passed_count=12` still works → `tests_passed=12`

### Fix 2 (P1): Zero-Test Anomaly Should Respect Independent Test Results

**File**: [coach_validator.py:1352-1398](guardkit/orchestrator/quality_gates/coach_validator.py#L1352-L1398)

Add `independent_tests` parameter and skip anomaly when tests verified passing:

```python
def _check_zero_test_anomaly(
    self,
    task_work_results: Dict[str, Any],
    profile: QualityGateProfile,
    independent_tests: Optional[IndependentTestResult] = None,
) -> List[Dict[str, Any]]:
    if not profile.tests_required:
        return []

    # Defense-in-depth: if independent test verification confirmed tests pass,
    # the zero-test anomaly is a results-writer data quality issue, not a real
    # missing-tests problem. Skip the anomaly check.
    if independent_tests and independent_tests.tests_passed:
        return []

    # ... existing check unchanged
```

**Update call site at line 720**:
```python
zero_test_issues = self._check_zero_test_anomaly(
    task_work_results, profile, independent_tests=test_result
)
```

**Regression analysis**:
- Genuine zero-test case (no independent tests run): `independent_tests` is `None` → check proceeds as before
- Task-work path with proper counts: `tests_passed_count > 0` → anomaly never fires anyway
- Independent tests fail: `independent_tests.tests_passed=False` → check proceeds as before
- Independent tests pass but zero count in JSON: skips anomaly → correct (verified passing)
- TASK-AQG-002: `zero_test_blocking` logic preserved (only reached when independent tests not passed)
- **Critical**: Independent tests are run at step 3 (line 670-681), before step 5 (line 719). If independent tests fail, step 3 returns feedback immediately and step 5 is never reached. So at step 5, `test_result.tests_passed` is always `True` when we get there. This means the anomaly check would effectively be bypassed whenever we reach it. **This is actually correct behavior** — if we've independently verified tests pass, the zero-test anomaly (which detects missing tests) is provably wrong.

**Test cases needed**:
1. Zero-test anomaly + independent tests passed → no anomaly (new behavior)
2. Zero-test anomaly + independent tests not run (None) → anomaly fires (preserved)
3. Zero-test anomaly + independent tests failed → anomaly fires (preserved, but unreachable in practice)
4. Non-zero tests + independent tests passed → no anomaly (preserved)
5. Existing TASK-AQG-002 tests still pass (they don't pass `independent_tests` → `None` → preserved)

### Fix 3 (DROPPED): Respect quality_gates_relaxed

Previously recommended but **dropped** after deeper analysis. The `quality_gates_relaxed` field is a dead signal never consumed by any code. Adding a consumer creates a new coupling point with unclear semantics. Fix 1 + Fix 2 are sufficient and more precise.

## Recommendation Priority

| Fix | Impact | Regression Risk | Effort | Priority |
|-----|--------|----------------|--------|----------|
| Fix 1 (test count derivation) | High — root cause | Low — task-work path preserved via `get("tests_passed_count", 0)` check | Low (5 lines) | **P0** |
| Fix 2 (independent test override) | High — defense-in-depth | Low — all existing tests pass `None` for independent_tests | Low (5 lines) | **P1** |

**Recommended approach**: Apply Fix 1 + Fix 2 together. Fix 1 corrects the data at the source. Fix 2 adds defense-in-depth so that independently verified tests can never be overridden by a stale/incorrect results JSON.

**Why both**: Fix 1 alone is sufficient for this specific bug. But Fix 2 prevents a category of future bugs where the results JSON diverges from reality. The Coach already runs independent tests — it should trust its own verification over the results file when they conflict.

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-001: Root cause identified | **PASS** | `_write_direct_mode_results()` reads `tests_passed_count` which is never set by direct mode Players (Finding 1). `tests_passed_count` was added by FBSDK-015 for the task-work path only. |
| AC-002: Direct vs task-work mode differences documented | **PASS** | See comparison table + consumer audit (9 consumers) |
| AC-003: CoachValidator vs task_type classification | **PASS** | Primary bug is in `agent_invoker.py` results writer. Secondary gap in Coach (Finding 2). NOT a task_type classification issue. |
| AC-004: Fix recommendations with file/line references | **PASS** | Two fixes with specific file:line references, regression analysis per fix, and test case specifications |
| AC-005: file_path fix from TASK-REV-1BE3 working | **PASS** | Log lines 24-29 confirm all 5 task files copied to worktree |

## Regression Test Checklist

Before merging fixes, verify all of these pass:

### Existing Tests (must not regress)
- [ ] `TestApprovalRationaleAndZeroTestAnomaly` (4 tests) — all pass
- [ ] `TestZeroTestBlockingConfiguration` (12 tests) — all pass
- [ ] `TestNullQualityGateHandling` (TASK-FIX-64EE tests) — all pass
- [ ] `test_write_direct_mode_results_*` tests — all pass

### New Tests Required
- [ ] Direct mode: `tests_passed=True, tests_written=2` → `quality_gates.tests_passed=2`
- [ ] Direct mode: `tests_passed=False, tests_written=1` → `quality_gates.tests_passed=0`
- [ ] Direct mode: `tests_passed=True, tests_written=[]` → `quality_gates.tests_passed=0`
- [ ] Task-work path: `tests_passed_count=12` → `quality_gates.tests_passed=12` (unchanged)
- [ ] Zero-test anomaly + independent tests passed → no anomaly
- [ ] Zero-test anomaly + `independent_tests=None` → anomaly fires (existing behavior)
- [ ] `all_passed=None` + zero tests → no anomaly (verify existing behavior preserved)
- [ ] Feature profile zero-test blocking still works for genuine zero-test tasks

## Appendix A: Data Flow Diagram

```
Direct Mode Path (BROKEN):
  Player SDK → player_turn_N.json (tests_passed=true, tests_written=["a.py","b.py"])
            ↓
  _write_direct_mode_results()
            ↓ reads "tests_passed_count" → NOT in schema → defaults to 0
            ↓ writes quality_gates.tests_passed = 0
            ↓
  CoachValidator.verify_quality_gates()
            ↓ reads all_passed=true → tests_passed = true ✓
            ↓
  CoachValidator.run_independent_tests()
            ↓ runs pytest → PASSED ✓
            ↓
  CoachValidator._check_zero_test_anomaly()
            ↓ reads quality_gates.tests_passed = 0 (WRONG!)
            ↓ all_passed=true AND tests_passed=0 AND coverage=null
            ↓ → BLOCKS (zero_test_blocking=true for feature profile) ✗

Direct Mode Path (FIXED):
  Player SDK → player_turn_N.json (tests_passed=true, tests_written=["a.py","b.py"])
            ↓
  _write_direct_mode_results()
            ↓ reads "tests_passed_count" → 0
            ↓ fallback: tests_passed=true AND tests_written=["a.py","b.py"] → count=2
            ↓ writes quality_gates.tests_passed = 2
            ↓
  CoachValidator._check_zero_test_anomaly()
            ↓ reads quality_gates.tests_passed = 2
            ↓ tests_passed_count > 0 → NO ANOMALY ✓

Task-Work Delegation Path (WORKS):
  Player SDK → /task-work → TaskWorkStreamParser → "12 tests passed"
            ↓
  _build_player_report() → player_report.tests_passed_count = 12
            ↓
  _write_task_work_results() → quality_gates.tests_passed = 12
            ↓
  CoachValidator._check_zero_test_anomaly()
            ↓ tests_passed_count = 12 → NO ANOMALY ✓
```

## Appendix B: Prior Fix Chain

```
TASK-REV-FB18 (schema mismatch discovery)
    ↓
FBSDK-015 (int→bool type fix, added tests_passed_count)
    ↓ ← direct mode writer assumed tests_passed_count exists
    ↓
TASK-REV-312E (null quality gates investigation)
    ↓
TASK-FIX-64EE (null handling: all_passed=None fallthrough)
    ↓
TASK-AQG-002 (zero-test blocking: error severity for feature/refactor)
    ↓ ← turned silent data gap into hard blocker
    ↓
TASK-REV-CEE8 (THIS REVIEW: direct mode + zero-test anomaly collision)
    ↓
Fix 1 + Fix 2 (proposed)
```
