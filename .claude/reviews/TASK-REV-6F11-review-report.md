# Review Report: TASK-REV-6F11 (Revised)

## Executive Summary

FEAT-SC-001 (System Context Read Commands) produced substantial, well-structured code across 12 tasks. However, the review identified **2 critical bugs with 4 sub-issues**, **1 systemic AutoBuild process issue**, and **21 failing E2E tests**. The unit/integration tests (327 passing) were well-designed but the E2E layer is broken due to async/sync mismatches and missing parameters in the CLI layer. The code cannot be merged to main in its current state.

**Overall Assessment: CONDITIONAL PASS** — Requires 2 targeted fix tasks before merge.

---

## Review Details

- **Mode**: Code Quality + Integration Review
- **Depth**: Deep (revised with line-level analysis)
- **Duration**: Comprehensive (full source, test, log, and cross-module call chain analysis)
- **Feature**: FEAT-SC-001 — System Context Read Commands
- **Branch**: `autobuild/FEAT-SC-001`
- **Worktree**: `.guardkit/worktrees/FEAT-SC-001`
- **Execution**: 12/12 tasks completed, 14 turns, 89m 52s, 92% clean

---

## Findings

### FINDING-1: CLI async/sync mismatch + missing parameters (CRITICAL)

**Severity**: Critical — 21/27 E2E tests fail
**File**: `guardkit/cli/system_context.py`
**Sub-issues**: 4 (2 async + 2 parameter)

The `system_overview` and `impact_analysis` CLI commands have two compounding bugs each: (a) calling async functions without `asyncio.run()`, and (b) missing required parameters. The `context_switch` command is correct and serves as the reference implementation.

#### 1a. `system_overview` — async mismatch (line 365)

```python
# ACTUAL (line 365):
overview = get_system_overview(verbose=verbose)

# get_system_overview() signature (system_overview.py:50):
async def get_system_overview(sp: "SystemPlanGraphiti", verbose: bool = False) -> Dict[str, Any]:
```

Calling an async function without `asyncio.run()` returns a coroutine object. When line 370-374 attempts `overview.get("status")`, it raises `AttributeError: 'coroutine' object has no attribute 'get'`.

#### 1b. `system_overview` — missing `sp` parameter (line 365)

Even after wrapping in `asyncio.run()`, the call passes only `verbose=verbose` but the function requires `sp: SystemPlanGraphiti` as a mandatory first argument. This would raise `TypeError: missing 1 required positional argument: 'sp'`.

#### 1c. `impact_analysis` — async mismatch (line 422)

```python
# ACTUAL (lines 422-427):
impact = run_impact_analysis(
    task_or_topic=task_or_topic,
    depth=depth,
    include_bdd=include_bdd,
    include_tasks=include_tasks,
)

# run_impact_analysis() signature (impact_analysis.py:60-67):
async def run_impact_analysis(
    sp: "SystemPlanGraphiti",
    client: "GraphitiClient",
    task_or_topic: str,
    depth: str = "standard",
    include_bdd: bool = False,
    include_tasks: bool = False,
) -> Dict[str, Any]:
```

Same coroutine-as-dict bug. Returns coroutine, `_format_impact_display()` (line 432) fails.

#### 1d. `impact_analysis` — missing `sp` and `client` parameters (line 422)

After async fix, would raise `TypeError: missing 2 required positional arguments: 'sp' and 'client'`.

#### Why `context_switch` works (lines 489, 510)

`context_switch` correctly uses `asyncio.run()`:
```python
result = asyncio.run(execute_context_switch(
    client=None,
    target_project=current.get("id", ""),
    config=config,
))
```
All 3 required parameters passed. `client=None` triggers graceful degradation in the planning function. This is the pattern `system_overview` and `impact_analysis` should follow.

#### E2E failure categorization

| Failure mode | Count | Error |
|-------------|-------|-------|
| `'coroutine' object has no attribute 'get'` | 20 | system-overview + impact-analysis + integration tests |
| `Object of type coroutine is not JSON serializable` | 1 | `test_system_overview_json_format` (json.dumps on coroutine) |
| **Total failing** | **21** | |
| Passing (all context-switch) | 6 | |

All 21 failures trace to the same root cause. No distinct failure modes exist.

**Fix (FIX-SC-01)**: For each broken command:
1. Obtain Graphiti client via `get_graphiti()` (with graceful fallback to `None`)
2. Create `SystemPlanGraphiti(client=client, project_id=...)` instance
3. Wrap async call in `asyncio.run()`
4. Pass all required parameters
5. Handle `client=None` gracefully (return `{"status": "no_context"}`)

**Complexity**: 3 — straightforward wiring following `context_switch` as reference

---

### FINDING-2: coach_context_builder.py parameter mismatch (CRITICAL)

**Severity**: Critical — Silently skips impact analysis for high-complexity tasks
**File**: `guardkit/planning/coach_context_builder.py`

#### The call chain

```
build_coach_context(task, client, project_id)       # line 51 — client received here
    └── sp = SystemPlanGraphiti(client=client, ...)  # line 97
    └── _get_impact_section(sp, task, budget)        # line 131 — client NOT passed
            └── run_impact_analysis(sp, query)       # line 179 — client MISSING
```

#### The mismatch (line 179)

```python
# ACTUAL (coach_context_builder.py:179):
impact_result = await run_impact_analysis(sp, query)

# EXPECTED (impact_analysis.py:60-67):
async def run_impact_analysis(
    sp: "SystemPlanGraphiti",
    client: "GraphitiClient",    # ← MISSING in call
    task_or_topic: str,
    ...
) -> Dict[str, Any]:
```

`run_impact_analysis(sp, query)` passes `query` as the `client` parameter (positional). This causes `TypeError` at runtime when the function tries to use `client` for Graphiti operations.

#### Why it's silent

The `try/except` at line 193-195 catches the `TypeError`, logs `[Graphiti] Failed to get impact analysis: ...`, and returns `""`. Impact analysis is silently skipped for all complexity >= 7 tasks. The coach gets overview context but never impact analysis — a degraded but not crashed experience.

#### Root cause

`_get_impact_section()` function signature (line 152-156) accepts `(sp, task, max_tokens)` but NOT `client`. The `client` is available in `build_coach_context()` (line 53) but is never threaded through to `_get_impact_section()`.

**Fix (FIX-SC-02)**:
1. Add `client` parameter to `_get_impact_section()` signature
2. Pass `client` from `build_coach_context()` at line 131-132
3. Use keyword args in `run_impact_analysis()` call at line 179:
   ```python
   impact_result = await run_impact_analysis(
       sp=sp, client=client, task_or_topic=query
   )
   ```

**Complexity**: 1 — three-line fix (add param to signature, pass it through, use kwargs)

---

### FINDING-3: Zero acceptance criteria verified across ALL 14 turns (PROCESS)

**Severity**: High — Systemic AutoBuild quality gap
**Scope**: All 12 tasks, all 14 turns

Every turn in the log shows:
```
Criteria: 0 verified, 0 rejected, N pending
```

The Coach is approving tasks without verifying ANY acceptance criteria. This means the Coach's approval is based only on quality gates (compilation, tests) and NOT on whether the task actually does what it's supposed to do.

**Root cause**: The Coach validation flow in `coach_validator.py` evaluates quality gates (tests pass, coverage met, etc.) but does NOT cross-reference the task's acceptance criteria checklist. The "Criteria" tracking comes from `_loop_phase()` turn-level bookkeeping, which records criteria as verified only when the Coach explicitly marks them — but the Coach prompt/validator doesn't have a mechanism to do so.

**Impact**: Quality gates alone caught the TASK-SC-003 coverage failure (turn 1 fail, turn 2 self-recover), but missed:
- The CLI async bugs (FINDING-1) — unit tests pass because they mock at a different layer
- The parameter mismatch (FINDING-2) — unit tests don't exercise the cross-module call path
- Potential functional gaps where implementation doesn't match spec

**Recommendation**: This is a known AutoBuild limitation. Not blocking for this feature, but should be tracked as a process improvement (the Coach needs criteria verification prompting).

---

### FINDING-4: TASK-SC-010 zero-test anomaly (MEDIUM)

**Severity**: Medium — Tests exist but aren't detected
**Task**: TASK-SC-010 (Update exports and acceptance test sweep)

Turn 2 was approved with: `all_passed=true, tests_passed=0, coverage=null`. The Coach logged:
```
WARNING: Zero-test anomaly: all_passed=true but tests_passed=0 and coverage=null
```

Yet the Coach still approved. This happened because:
1. Turn 1 hit SDK timeout (1200s) — state recovery detected 2 created files, 0 tests
2. Turn 2 succeeded with 6 files created but the test detection pattern didn't find task-specific tests
3. The `coach_validator.py` logged `No task-specific tests found for TASK-SC-010, skipping independent verification`
4. Quality gates evaluated as `ALL_PASSED=True` because the Player reported gates as passed

**Root cause**: TASK-SC-010 is an exports/acceptance task (`implementation_mode: direct`, complexity: 3). It created test files but the test detection pattern (`test_*SC-010*` or similar) didn't match the actual test filenames. The Player's own `task_work_results.json` reported `all_passed: true` without running tests — the same null quality gate pattern identified in TASK-FIX-64EE but here the Player simply didn't reach Phase 4.5 before SDK timeout in turn 1, and in turn 2 the Player bypassed test execution.

**Impact**: Low in practice — the 327 passing unit/integration tests cover the exported functionality. But the Coach should have flagged the zero-test condition more aggressively rather than approving.

---

### FINDING-5: Graphiti duplicate_facts warnings (LOW)

**Severity**: Low — Informational
**Count**: 2 instances in the log

```
LLM returned invalid duplicate_facts idx values
```

These are benign warnings from `graphiti-core` during edge operations. The LLM's deduplication index occasionally returns invalid references. No data corruption; the operation retries and succeeds.

**Fix**: No action required for this feature. Tracked as a known graphiti-core upstream issue.

---

## Code Quality Assessment

### Source Code (guardkit/planning/)

| Module | Lines | Quality | Notes |
|--------|-------|---------|-------|
| `system_overview.py` | 555 | Excellent | Clean structure, comprehensive docstrings, proper async, no issues found |
| `context_switch.py` | 417 | Very Good | YAML config management, graceful degradation, no issues found |
| `impact_analysis.py` | 727 | Excellent | Multi-depth analysis, risk scoring, token budgeting, no issues found |
| `coach_context_builder.py` | 214 | Good | Parameter mismatch at line 179 (FINDING-2), otherwise well-structured |
| `__init__.py` | 51 | Good | All exports match actual function names |

**Strengths**:
- Comprehensive type hints and docstrings throughout
- Graceful degradation when Graphiti unavailable (`{status: "no_context"}`)
- Token-budgeted condensation for LLM injection
- `[Graphiti]` log prefix convention followed
- Clean separation of business logic and display formatting

**No additional issues found** in the planning modules beyond FINDING-2. All async/await chains are correct within the planning layer itself.

### CLI Layer (guardkit/cli/system_context.py — 540 lines)

| Aspect | Status |
|--------|--------|
| Click decorators | Correct — options, arguments, choices all well-defined |
| Display formatting | Well-implemented — `_format_risk_bar()`, `_format_overview_display()`, etc. |
| Async handling | **BROKEN** for `system_overview` (line 365) and `impact_analysis` (line 422) |
| Parameter passing | **BROKEN** — missing `sp` and/or `client` for 2/3 commands |
| Error handling | Good try/except with fallback to `{"status": "no_context"}` |
| Registration in main.py | Correct — 3 commands at lines 122-124 |
| `context_switch` | **Correct** — proper `asyncio.run()` + all params (reference implementation) |

### Test Coverage

| Category | Files | Tests | Status |
|----------|-------|-------|--------|
| Unit tests | 4 files | 118 methods | **327 PASS** |
| Integration tests | 4 files | 65 methods | **327 PASS** (included above) |
| E2E tests | 1 file | 27 methods | **6 pass, 21 FAIL** |
| **Total** | **9 files** | **210 methods** | **333 pass, 21 fail** |

The unit/integration tests are well-designed with:
- Realistic Graphiti mock fixtures
- Async test support (`@pytest.mark.asyncio`, `AsyncMock`)
- Graceful degradation paths tested
- Token budget enforcement verified
- `[Graphiti]` logging assertions

### Command Specs & Documentation

| Artifact | Status | Notes |
|----------|--------|-------|
| `installer/core/commands/system-overview.md` | Complete | 393 lines, well-structured |
| `installer/core/commands/impact-analysis.md` | Complete | 566 lines, comprehensive |
| `installer/core/commands/context-switch.md` | Complete | 542 lines, detailed |
| `docs/guides/system-overview-guide.md` | Complete | User-facing walkthrough |
| `docs/guides/impact-analysis-guide.md` | Complete | User-facing walkthrough |
| `docs/guides/context-switch-guide.md` | Complete | User-facing walkthrough |
| `mkdocs.yml` nav entries | Complete | 3 guides registered |
| `CLAUDE.md` updates | Complete | Commands and references added |

---

## Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 4 core modules reviewed for correctness | PASS (with bugs noted) | system_overview, context_switch, impact_analysis, coach_context_builder reviewed |
| Test files verified to exist and assessed for coverage | PASS | 210 test methods across 9 files, 5,659 lines of test code |
| CLI command registration confirmed | PASS | 3 commands registered in `main.py` lines 122-124 |
| Coach context builder integration verified | CONDITIONAL | Has parameter mismatch bug (FINDING-2) |
| Zero-criteria-verified issue root cause identified | PASS | Coach validator lacks criteria verification mechanism (FINDING-3) |
| Zero-test anomaly root cause identified | PASS | Test detection pattern mismatch + Player bypass (FINDING-4) |
| Report written with findings and recommended fixes | PASS | This report |

---

## Recommendations

### Must Fix Before Merge (2 fix tasks + verification)

1. **FIX-SC-01**: Fix CLI async/sync mismatch + missing parameters in `system_context.py`
   - Fix `system_overview` command (line 365): add `asyncio.run()`, create `SystemPlanGraphiti`, pass `sp` parameter
   - Fix `impact_analysis` command (line 422): add `asyncio.run()`, create `SystemPlanGraphiti` + `GraphitiClient`, pass `sp` and `client`
   - Follow `context_switch` (lines 489, 510) as reference implementation
   - Handle `client=None` / Graphiti unavailable gracefully
   - **Expected**: All 21 failing E2E tests should pass
   - **Complexity**: 3 (straightforward wiring — pattern exists in `context_switch`)

2. **FIX-SC-02**: Fix parameter mismatch in `coach_context_builder.py`
   - Add `client` parameter to `_get_impact_section()` signature (line 152)
   - Pass `client` from `build_coach_context()` at line 131
   - Fix `run_impact_analysis()` call at line 179 to use keyword args with `client`
   - **Complexity**: 1 (three-line fix)

3. **FIX-SC-03**: Verify all 27 E2E tests pass + no regressions
   - Run `pytest tests/e2e/test_system_context_commands.py -v` — expect 27/27 pass
   - Run `pytest tests/unit/planning/ tests/integration/ -v` — expect 327/327 pass (no regressions)

### Should Track (not blocking)

4. **PROCESS-01**: Coach acceptance criteria verification gap
   - The Coach never verifies task acceptance criteria — only quality gates
   - Track as AutoBuild enhancement: add criteria verification to Coach prompt
   - All 14 turns show `0 verified, 0 rejected, N pending`

5. **PROCESS-02**: Zero-test anomaly handling
   - Coach should not approve when `all_passed=true` but `tests_passed=0` for implementation tasks
   - Already has WARNING log but should be a soft-block requiring explicit Coach override

---

## Test Execution Summary

```
Unit + Integration:  327 passed, 0 failed
E2E:                   6 passed, 21 failed
Total:               333 passed, 21 failed
```

E2E failure breakdown:
- 20 tests: `AttributeError: 'coroutine' object has no attribute 'get'`
- 1 test: `TypeError: Object of type coroutine is not JSON serializable`
- 6 passing: All `context_switch` tests (correctly uses `asyncio.run()`)

All 21 failures trace to FINDING-1 (CLI async/sync mismatch + missing parameters).

---

## Decision

**CONDITIONAL PASS** — The feature implementation is solid (good code structure, comprehensive tests at unit/integration level, complete documentation). The planning modules (system_overview.py, impact_analysis.py, context_switch.py) are excellent quality with no issues. The 2 critical bugs are confined to the CLI wiring layer (`system_context.py` lines 365 and 422) and a single cross-module call (`coach_context_builder.py` line 179). These are straightforward fixes — not fundamental design problems. Fix FIX-SC-01 through FIX-SC-03, verify 27/27 E2E tests pass, then merge.
