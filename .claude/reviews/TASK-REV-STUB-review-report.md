# Review Report: TASK-REV-STUB — Stub Generation Despite Quality Gates (REVISED)

## Executive Summary

`guardkit/planning/system_plan.py` is a 70-line file whose primary function `run_system_plan()` contains only `logger.info()` + `pass`. It was created by TASK-SP-006 during FEAT-6EDD feature build, passed all quality gates, received Coach approval on turn 1, and moved to `in_review` — all within 12 minutes.

**Revision note**: The deep dive uncovered a **critical wiring bug** (RC-1 below) that was not in the initial report. The acceptance criteria list is **never passed** from `_execute_turn()` to `_invoke_coach_safely()`. This means the Coach has **never verified acceptance criteria for any task** across all AutoBuild runs. Confirmed: every `coach_turn_*.json` in the repo shows `criteria_total: 0`. This supersedes the prior TASK-FIX-ACA7b diagnosis, which improved the matching logic but could never work because the input data was empty.

**Severity**: CRITICAL — Three independent bypass mechanisms ensure stubs pass undetected. RC-1 alone means acceptance criteria verification has been completely non-functional since AutoBuild launch.

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Architectural |
| **Depth** | Standard (revised to comprehensive after deep-dive) |
| **Task** | TASK-REV-STUB |
| **Feature** | FEAT-6EDD / FEAT-SP-001 (system-plan command) |
| **Subject** | TASK-SP-006 — "Create guardkit system-plan CLI command" |
| **Task Type** | FEATURE (`zero_test_blocking=True`) |
| **Complexity** | 6 |

---

## Forensic Evidence (Actual Artifacts)

All data below comes from `.guardkit/autobuild/TASK-SP-006/`.

### task_work_results.json
```json
{
  "task_id": "TASK-SP-006",
  "completed": true,
  "quality_gates": {
    "tests_passing": true,
    "tests_passed": 54,
    "tests_failed": 0,
    "coverage": null,
    "coverage_met": null,
    "all_passed": true
  },
  "files_modified": [],
  "files_created": []
}
```

**Key observations**:
- `files_created: []` and `files_modified: []` — the task-work delegation path **did not propagate file lists** back to the results writer. The Player actually created 5+ files but the results writer didn't capture them.
- `tests_passed: 54` — these are **all** tests in the project scope, not task-specific
- No `completion_promises`, no `requirements_met`, no `tests_written` field

### player_turn_1.json
```json
{
  "files_created": [
    ".guardkit/autobuild/TASK-SP-006/task_work_results.json",
    ".guardkit/autobuild/TASK-SP-007/checkpoints.json",
    "tasks/in_review/TASK-SP-006-cli-command.md"
  ],
  "tests_written": [],
  "tests_passed": true,
  "tests_passed_count": 54
}
```

**Key observations**:
- `tests_written: []` — Player reports writing zero tests (even though `test_system_plan_cli.py` was created by the task-work subprocess)
- `files_created` lists only autobuild artifacts and the moved task file, NOT the implementation files
- No `completion_promises` field

### coach_turn_1.json
```json
{
  "decision": "approve",
  "validation_results": {
    "quality_gates": { "all_gates_passed": true },
    "independent_tests": {
      "tests_passed": true,
      "test_command": "skipped",
      "test_output_summary": "No task-specific tests found for TASK-SP-006, skipping independent verification"
    },
    "requirements": {
      "criteria_total": 0,
      "criteria_met": 0,
      "all_criteria_met": true,
      "missing": []
    }
  },
  "rationale": "All quality gates passed. Independent verification skipped: no task-specific tests found. All acceptance criteria met."
}
```

**Key observations**:
- `criteria_total: 0` — Coach received **zero** acceptance criteria (not 15). This is the wiring bug.
- `test_command: "skipped"` — No task-specific tests found, independent verification entirely skipped
- `all_criteria_met: true` — Vacuous truth (0 out of 0 = 100%)

---

## Root Cause Analysis (Revised, Validated)

### RC-1: Acceptance Criteria Never Passed to Coach (CRITICAL — NEW FINDING)

**The bug**: `_execute_turn()` ([autobuild.py:1625](guardkit/orchestrator/autobuild.py#L1625)) does NOT accept an `acceptance_criteria` parameter. When it calls `_invoke_coach_safely()` at [line 1812](guardkit/orchestrator/autobuild.py#L1812), it passes `task_type=task_type` but NOT `acceptance_criteria`:

```python
# autobuild.py:1812-1820 — acceptance_criteria NOT passed
coach_result = self._invoke_coach_safely(
    task_id=task_id,
    turn=turn,
    requirements=requirements,
    player_report=player_result.report,
    worktree=worktree,
    task_type=task_type,          # ← passed
    skip_arch_review=skip_arch_review,
    # acceptance_criteria=???     # ← MISSING
)
```

The `acceptance_criteria` parameter in `_invoke_coach_safely()` ([line 2874](guardkit/orchestrator/autobuild.py#L2874)) defaults to `None`, which at [line 3011](guardkit/orchestrator/autobuild.py#L3011) becomes `[]`:

```python
task={
    "acceptance_criteria": acceptance_criteria or [],  # None → []
    "task_type": task_type,
}
```

Meanwhile, `_loop_phase()` DOES receive `acceptance_criteria` from `orchestrate()` and passes it to `_capture_turn_state()` and `_display_criteria_progress()` — but never to `_execute_turn()`.

**Impact**: The Coach's `validate_requirements()` always receives an empty list. With zero criteria, `_match_by_promises()` or `_match_by_text()` iterates over nothing, producing `criteria_total: 0, all_criteria_met: true`.

**Proof**: `grep -r '"criteria_total"' .guardkit/autobuild/*/coach_turn_*.json` returns `criteria_total: 0` for **every single task across all feature builds**. Acceptance criteria verification has been completely non-functional since AutoBuild was launched.

**Relationship to TASK-FIX-ACA7b**: The ACA7b fix improved the matching logic inside `validate_requirements()` (switching from text matching to ID-based `completion_promises`). However, this fix **cannot work** because the acceptance_criteria input list is always empty. ACA7b fixed the wrong layer — it's like optimizing a database query that never executes because the caller passes an empty WHERE clause.

### RC-2: Zero-Test Anomaly Should Have Fired (But Didn't Due to Data Gaps)

**The data path for SP-006**:
1. `task_work_results.json` has `tests_written: []` (field absent, defaults to `[]`) ← BUT this field was not written by the task-work results writer until TASK-FIX-93A1
2. `independent_tests.test_command = "skipped"` (no task-specific tests found)
3. `profile = FEATURE` (has `zero_test_blocking=True`)

**Expected behavior**: Lines 1574-1595 of `_check_zero_test_anomaly()` should fire:
```python
tests_written = task_work_results.get("tests_written", [])  # → []
if len(tests_written) == 0 and independent_tests.test_command == "skipped":
    severity = "error"  # zero_test_blocking=True for FEATURE
    return [{"severity": "error", "category": "zero_test_anomaly", ...}]
```

**Why it didn't fire**: The SP-006 run occurred on **Feb 9, 2026**. Let me check the timeline:
- TASK-FIX-93A1 (adding `tests_written` to results writers) was completed AFTER TASK-REV-93E1
- TASK-FIX-ACA7a (adding the `tests_written=[]` + `test_command=="skipped"` check) was also completed AFTER the ACA7 review

**Conclusion**: At the time SP-006 ran, the zero-test anomaly check only had the ORIGINAL check (lines 1597-1616): `all_passed is True AND tests_passed_count == 0 AND coverage is None`. SP-006 had `tests_passed: 54` (not 0), so the original check did NOT fire. The enhanced checks (lines 1570-1595) were added AFTER this run by TASK-FIX-ACA7a and TASK-FIX-93A1.

**Would it fire TODAY?** YES — the current code at lines 1574-1595 would catch SP-006 because:
- `tests_written` field is absent from `task_work_results.json` → `get("tests_written", [])` → `[]`
- `independent_tests.test_command == "skipped"` → TRUE
- `profile.zero_test_blocking == True` (FEATURE profile)
- Result: `severity="error"` → Coach returns feedback instead of approving

**However**: The task_work_results writer (task-work delegation path) may still not write `tests_written`. TASK-FIX-93A1 added it to `_write_task_work_results()` but SP-006 used the task-work delegation path, which writes results differently. Let me verify this is correct.

**Important caveat**: Even if the zero-test anomaly would fire today, it would be a SECONDARY defense. RC-1 (acceptance criteria wiring bug) remains the primary issue because it means the Coach never validates whether the task's stated requirements are actually met.

### RC-3: Test Discovery — Empty `files_created` + Naming Convention Mismatch (CONFIRMED)

**Primary path** (`_detect_tests_from_results`): `task_work_results.json` has `files_created: []` and `files_modified: []`. The method iterates over these empty lists and returns `None`.

**Fallback path** (glob): `_task_id_to_pattern_prefix("TASK-SP-006")` → `"task_sp_006"`. Pattern: `tests/**/test_task_sp_006*.py`. Actual file: `tests/unit/cli/test_system_plan_cli.py`. No match.

**Result**: `_detect_test_command()` returns `None` → `run_independent_tests()` returns `IndependentTestResult(tests_passed=True, test_command="skipped")`.

**Prior fix context**:
- **TASK-FIX-93B1** made the glob recursive (`tests/**/test_{prefix}*.py`). This helps for nested directories but DOES NOT help when the file name doesn't contain the task ID prefix. SP-006's test file is named by feature (`test_system_plan_cli.py`), not by task ID (`test_task_sp_006*.py`).
- **TASK-FIX-93A1** added `tests_written` to both results writers. This populates the field for future runs, enabling `_detect_tests_from_results()` to find test files via `files_created`/`files_modified`. However, the task-work delegation path's results writer also needs to populate `files_created`/`files_modified` from the subprocess output — and as SP-006 shows, it doesn't.

**Residual gap**: The test discovery mechanism has TWO assumptions that both failed for SP-006:
1. `files_created`/`files_modified` in `task_work_results.json` lists the actual files (FAILS when task-work delegation path doesn't propagate file lists)
2. Test files are named `test_{task_id_prefix}*.py` (FAILS when tests are named by feature, not by task ID)

### RC-4: No Stub Detection Gate (CONFIRMED, Unchanged)

No quality gate inspects function bodies for stub patterns. This is unchanged from the initial report. The pipeline checks compilation, test pass/fail, coverage, and claims — none of these catch a syntactically valid function containing only `pass`.

---

## Findings Summary (Revised)

| # | Finding | Severity | Category | New? |
|---|---------|----------|----------|------|
| **F-1** | `_execute_turn()` does not pass `acceptance_criteria` to Coach — criteria verification is non-functional for ALL tasks | **CRITICAL** | Wiring Bug | **NEW** |
| F-2 | TASK-FIX-ACA7b fixed matching logic but cannot work due to F-1 (empty input) | HIGH | Ineffective Fix | **NEW** |
| F-3 | `files_created`/`files_modified` empty in task-work delegation results — primary test discovery fails | HIGH | Data Gap | Refined |
| F-4 | Test discovery glob uses task-ID naming convention; fails for feature-named test files | MEDIUM | Naming Mismatch | Refined |
| F-5 | No gate detects stub function patterns (`pass`, `NotImplementedError`, `TODO`) | HIGH | Quality Gate Gap | Unchanged |
| F-6 | Zero-test anomaly check (lines 1574-1595) did not exist at time of SP-006 run; would catch it today IF `tests_written` absent | MEDIUM | Temporal | **NEW** |
| F-7 | Feature plan template has no anti-stub criteria | MEDIUM | Planning Gap | Unchanged |

---

## Recommendations (Revised, Prioritized)

### P0-A: Wire `acceptance_criteria` Through `_execute_turn()` to Coach

**The fix**: Add `acceptance_criteria: Optional[List[str]] = None` parameter to `_execute_turn()`. Pass it through to `_invoke_coach_safely()`.

**Files to change**:
1. [autobuild.py:1625](guardkit/orchestrator/autobuild.py#L1625) — Add `acceptance_criteria` parameter to `_execute_turn()` signature
2. [autobuild.py:1501-1509](guardkit/orchestrator/autobuild.py#L1501) — Pass `acceptance_criteria=acceptance_criteria` in `_loop_phase()`'s call to `_execute_turn()`
3. [autobuild.py:1812-1820](guardkit/orchestrator/autobuild.py#L1812) — Pass `acceptance_criteria=acceptance_criteria` in `_execute_turn()`'s call to `_invoke_coach_safely()`

**Lines changed**: 3 (parameter addition + 2 call sites)

**Impact**: Enables ALL downstream criteria verification logic (including ACA7b's completion_promises matching) to function. This single fix restores the entire acceptance criteria verification pipeline.

**Regression risk**: LOW — adding a parameter with default `None` is backward-compatible. Existing tests that don't pass the parameter will behave identically.

**Validation**: After fix, `coach_turn_*.json` should show `criteria_total > 0` matching the task's actual acceptance criteria count.

### P0-B: Anti-Stub Rule (`.claude/rules/anti-stub.md`)

**Purpose**: Explicit rule that makes stub detection part of the quality gate vocabulary.

**Content**:
1. **Definition**: A stub is a function whose body consists of: `pass`, `raise NotImplementedError`, `# TODO`/`# FIXME` only, `return None` / hardcoded defaults with no conditional logic, or `logger.*()` + `pass`/`return`.
2. **Rule**: For FEATURE and REFACTOR tasks, primary deliverable functions MUST NOT be stubs.
3. **Enforcement**: Coach verifies primary function contains meaningful logic (conditional branching, error handling, or calls to domain-specific dependencies).
4. **Exception**: SCAFFOLDING/INFRASTRUCTURE tasks MAY create stubs if acceptance criteria explicitly state so.

**Implementation**: Add `.claude/rules/anti-stub.md` and update Coach agent prompt.

### P1-A: Populate `files_created`/`files_modified` in Task-Work Delegation Path

**The gap**: The task-work delegation results writer does not propagate the actual files created/modified by the subprocess into `task_work_results.json`. This breaks:
1. `_detect_tests_from_results()` — can't find test files
2. Coach's independent verification — falls through to glob (which may miss feature-named tests)

**Fix location**: `agent_invoker.py` — the task-work delegation path's results writer should extract files from the subprocess output and populate `files_created`/`files_modified`.

### P1-B: Feature Plan Template Anti-Stub Criteria

**Additions to feature-plan task template**:
1. Anti-stub criterion: `Primary function(s) contain meaningful implementation logic (not stubs or TODOs)`
2. End-to-end test criterion: `At least one test exercises the primary function without mocking its core logic`
3. Task type clarity: "Create X" tasks must state "full working implementation, not scaffolding"

### P2: TASK-SP-006 Rework (Separate Implementation Task)

Replace the stub `run_system_plan()` with working orchestration logic. Out of scope for this review.

---

## Cross-Reference: Prior Fix Chain Analysis

| Fix | Original Target | Relationship to RC-1 | Status |
|-----|----------------|----------------------|--------|
| **TASK-FIX-ACA7b** | Criteria verification 0% | Fixed matching logic, but input is always empty due to RC-1. **Incomplete fix** — needs P0-A to become effective. | Needs P0-A |
| **TASK-FIX-93A1** | `tests_written` gap | Added `tests_written` to results writers. Works for zero-test anomaly check but doesn't help criteria verification. | Independent, working |
| **TASK-FIX-93B1** | Non-recursive test glob | Made glob recursive. Helps for nested dirs but NOT for naming mismatch (SP-006 pattern). | Independent, working |
| **TASK-FIX-CEE8b** | Zero-test anomaly bypass | Added independent_tests early return. Working correctly but only fires when tests were independently verified (not when skipped). | Independent, working |
| **TASK-FIX-ACA7a** | Project-wide pass bypass | Added `tests_written=[]` + `test_command=="skipped"` check. Would catch SP-006 today. | Independent, would catch |
| **TASK-AQG-001** | Structured criteria results | Added `CriterionResult` dataclass. Works correctly but produces empty results due to RC-1. | Needs P0-A |
| **TASK-AQG-002** | Zero-test blocking | Made zero-test anomaly blocking for FEATURE/REFACTOR. Working, but SP-006 pre-dated this fix. | Independent, working |

---

## Architecture Score (Revised)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Quality Gate Coverage | 3/10 | RC-1 disables entire criteria verification pipeline |
| Test Infrastructure | 5/10 | Discovery works for standard naming; task-work delegation data gap |
| Trust Model | 2/10 | Coach always sees 0 criteria → always approves on requirements |
| Planning Templates | 5/10 | Good structure but missing anti-stub criteria |
| State Transition Safety | 3/10 | No criteria verification = no transition safety on requirements |
| **Overall** | **3.5/10** | Foundational wiring bug undermines entire requirements verification |

---

## Impact Assessment (Revised)

| Impact Area | Risk | Description |
|-------------|------|-------------|
| **All prior AutoBuild runs** | CRITICAL | Every task ever approved had `criteria_total: 0`. Acceptance criteria were NEVER verified by the Coach. |
| **Current stub** | HIGH | `guardkit system-plan` silently does nothing |
| **Future features** | HIGH | Until P0-A is applied, requirements verification remains non-functional |
| **Prior ACA7b fix** | MEDIUM | Fix is correct but inert. Will "activate" once P0-A provides input data. |

---

## Appendix A: Evidence Files

| File | Description |
|------|-------------|
| [system_plan.py](guardkit/planning/system_plan.py) | The stub — 70 lines, `pass` body |
| [system_plan.py (cli)](guardkit/cli/system_plan.py) | Working CLI wrapper — 217 lines |
| [graphiti_arch.py](guardkit/planning/graphiti_arch.py) | Fully implemented persistence layer — 358 lines |
| [mode_detector.py](guardkit/planning/mode_detector.py) | Working mode detection — 106 lines |
| [TASK-SP-006-cli-command.md](tasks/in_review/TASK-SP-006-cli-command.md) | Task file — 15 AC all unchecked |
| `.guardkit/autobuild/TASK-SP-006/task_work_results.json` | Quality gate results — `files_created: []` |
| `.guardkit/autobuild/TASK-SP-006/coach_turn_1.json` | Coach decision — `criteria_total: 0` |
| `.guardkit/autobuild/TASK-SP-006/player_turn_1.json` | Player report — `tests_written: []` |

## Appendix B: The Wiring Bug Location

```
orchestrate() → _loop_phase(acceptance_criteria=[15 items])
    │
    ├→ _capture_turn_state(acceptance_criteria)     ← HAS criteria ✓
    ├→ _display_criteria_progress(acceptance_criteria) ← HAS criteria ✓
    │
    └→ _execute_turn(turn, task_id, requirements, worktree, ...)
        │                                          ← MISSING criteria ✗
        └→ _invoke_coach_safely(..., acceptance_criteria=None)
            │                                      ← None → []
            └→ CoachValidator.validate(task={"acceptance_criteria": []})
                │                                  ← EMPTY list
                └→ validate_requirements()
                    └→ criteria_total: 0, all_criteria_met: true  ← VACUOUS TRUTH
```
