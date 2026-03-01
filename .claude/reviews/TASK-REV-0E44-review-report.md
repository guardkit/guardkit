# Review Report: TASK-REV-0E44 (Revised)

## Executive Summary

FEAT-4296 (Eval Runner GuardKit vs Vanilla Pipeline) completed 8 of 10 tasks successfully before stalling on TASK-EVAL-009 (Graphiti Storage) with an `UNRECOVERABLE_STALL` decision. The feature ran for 70m 25s across 13 adversarial turns.

**Root Cause**: A failure at the **Coach Test Discovery → pytest CLI** technology seam. The Coach's `_detect_tests_from_results()` extracted workspace template test files from `task_work_results.json` and passed them as explicit arguments to pytest. When pytest receives explicit file paths, it bypasses `collect_ignore_glob` patterns — a documented pytest behaviour. The workspace tests (`test_health.py`) have a `tests/__init__.py` that creates a module name collision (`tests.test_health`) with the parent project's `tests/` package, causing `ModuleNotFoundError` at collection time. The classification path then routed through `("infrastructure", "ambiguous")` which cannot trigger `conditional_approval`, creating an unbreakable feedback loop.

**Classification**: **Preventable false negative**. Four distinct seam failures conspired to create the stall. Each alone would not have been fatal; together they formed an unbreakable chain.

---

## Review Details

- **Mode**: Decision Analysis (Revised — comprehensive depth)
- **Depth**: Comprehensive
- **Revision Reason**: Deeper analysis of technology seam failures with C4 flow tracing

---

## C4 Component Diagram: AutoBuild Test Verification Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AutoBuild Orchestrator                          │
│                        (autobuild.py)                                  │
│                                                                        │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────────┐     │
│  │  _loop_phase │───►│ _execute_turn │───►│ _invoke_coach_safely │     │
│  │              │    │               │    │                      │     │
│  │ Stall        │    │ TurnRecord    │    │ Creates              │     │
│  │ detection    │◄───│ construction  │◄───│ CoachValidator       │     │
│  └──────────────┘    └───────────────┘    └──────────┬───────────┘     │
│         │                                            │                 │
│         │ _is_feedback_stalled()                     │                 │
│         │ _count_criteria_passed()                   │                 │
└─────────┼────────────────────────────────────────────┼─────────────────┘
          │                                            │
          │                                            ▼
┌─────────┼─────────────────────────────────────────────────────────────┐
│         │              CoachValidator                                  │
│         │              (coach_validator.py)                             │
│         │                                                              │
│  ┌──────┴──────────┐    ┌───────────────────────┐                     │
│  │    validate()    │───►│ run_independent_tests │                     │
│  │                  │    │                       │                     │
│  │ quality_gates    │    │  ┌─────────────────┐  │                     │
│  │ ─────────────    │    │  │_detect_test_cmd │  │                     │
│  │ tests: PASS      │    │  │                 │  │                     │
│  │ coverage: PASS   │    │  │ Tier 1:         │  │                     │
│  │ arch: PASS       │    │  │ ─────────────── │  │                     │
│  │ audit: PASS      │    │  │_detect_tests_   │  │                     │
│  │ ALL: TRUE        │    │  │from_results()◄──┼──┼── SEAM FAILURE 1   │
│  │                  │    │  └────────┬────────┘  │                     │
│  │ conditional_     │    │           │           │                     │
│  │ approval check◄──┼───┼───────────┼───────────┼── SEAM FAILURE 3   │
│  │                  │    │           ▼           │                     │
│  │ feedback_result  │    │  ┌─────────────────┐  │                     │
│  │ construction◄────┼────┼──│_classify_test_  │  │                     │
│  │                  │    │  │failure()    ◄───┼──┼── SEAM FAILURE 2   │
│  └──────────────────┘    │  └─────────────────┘  │                     │
│                          └──────────┬────────────┘                     │
└─────────────────────────────────────┼─────────────────────────────────┘
                                      │
                          ┌───────────┼─────────────┐
                          │           ▼             │
                          │   pytest CLI            │
                          │   (subprocess/SDK)      │
                          │                         │
                          │   Explicit file args    │
                          │   bypass collect_       │
                          │   ignore_glob      ◄────┼── SEAM FAILURE 4
                          │                         │
                          │   ModuleNotFoundError   │
                          │   'tests.test_health'   │
                          └─────────────────────────┘
```

---

## C4 Sequence Diagram: The Stall Chain (Per Turn)

```
Player (SDK)      AgentInvoker          task_work_results.json    CoachValidator         pytest CLI
    │                  │                         │                      │                    │
    │  Write/Edit      │                         │                      │                    │
    │  workspace files │                         │                      │                    │
    │─────────────────►│                         │                      │                    │
    │                  │                         │                      │                    │
    │  SDK complete    │                         │                      │                    │
    │─────────────────►│                         │                      │                    │
    │                  │                         │                      │                    │
    │                  │  _write_task_work_results()                    │                    │
    │                  │  files_modified includes:                      │                    │
    │                  │  - tests/eval/test_eval_storage.py             │                    │
    │                  │  - tests/eval/test_eval_cli.py                 │                    │
    │                  │  - guardkit/eval/workspaces/                   │                    │
    │                  │    guardkit-project/tests/test_health.py ◄─────┼─ PROBLEM FILES     │
    │                  │  - guardkit/eval/workspaces/                   │                    │
    │                  │    plain-project/tests/test_health.py   ◄─────┼─ PROBLEM FILES     │
    │                  │─────────────────►│                      │                    │
    │                  │                         │                      │                    │
    │                  │  _create_player_report() │                     │                    │
    │                  │  git diff enrichment     │                     │                    │
    │                  │  adds 36 modified files  │                     │                    │
    │                  │──────── updates ────────►│                     │                    │
    │                  │                         │                      │                    │
    │                  │                         │  _detect_tests_from_results()             │
    │                  │                         │  scans files_modified/created              │
    │                  │                         │  for test_*.py pattern:                    │
    │                  │                         │  ┌──────────────────────────────────┐      │
    │                  │                         │  │ MATCHED (all basename test_*.py):│      │
    │                  │                         │  │ 1. test_eval_storage.py    ✓     │      │
    │                  │                         │  │ 2. test_eval_cli.py       ✓     │      │
    │                  │                         │  │ 3. test_health.py (gk)    ✗     │      │
    │                  │                         │  │ 4. test_health.py (plain) ✗     │      │
    │                  │                         │  └──────────────────────────────────┘      │
    │                  │                         │─────────────────────►│                    │
    │                  │                         │                      │                    │
    │                  │                         │                      │  pytest <4 files>  │
    │                  │                         │                      │  explicit args     │
    │                  │                         │                      │──────────────────►│
    │                  │                         │                      │                    │
    │                  │                         │                      │     collect_ignore_glob
    │                  │                         │                      │     BYPASSED for    │
    │                  │                         │                      │     explicit args   │
    │                  │                         │                      │                    │
    │                  │                         │                      │  ModuleNotFoundError│
    │                  │                         │                      │  'tests.test_health'│
    │                  │                         │                      │◄──────────────────│
    │                  │                         │                      │                    │
    │                  │                         │  _classify_test_failure()                  │
    │                  │                         │  missing_module = "tests"                  │
    │                  │                         │  not in _KNOWN_SERVICE_CLIENT_LIBS         │
    │                  │                         │  requires_infrastructure = []              │
    │                  │                         │  → ("infrastructure", "ambiguous")         │
    │                  │                         │                      │                    │
    │                  │                         │  conditional_approval check:               │
    │                  │                         │  failure_confidence="ambiguous" ≠ "high"   │
    │                  │                         │  requires_infra=[] → bool([])=False        │
    │                  │                         │  → conditional_approval = False            │
    │                  │                         │                      │                    │
    │                  │                         │  → FEEDBACK with                           │
    │                  │                         │    "infrastructure" remediation             │
    │                  │                         │    (mocks/SQLite/markers)                   │
    │                  │                         │                      │                    │
```

---

## The Four Seam Failures

### SEAM FAILURE 1: Coach Test Discovery → File Filtering (coach_validator.py:2569-2615)

**Technology Boundary**: `task_work_results.json` (data) → `_detect_tests_from_results()` (logic)

**What happens**: The method scans `files_created` and `files_modified` for any file whose basename matches `test_*.py` or `*_test.py`. It performs NO semantic filtering — no path-based exclusions, no checking against `conftest.py` patterns, no awareness of workspace/template directories.

**Evidence** (from `task_work_results.json` lines 50, 55):
```json
"files_modified": [
    ...
    "guardkit/eval/workspaces/guardkit-project/tests/test_health.py",  // line 50
    "guardkit/eval/workspaces/plain-project/tests/test_health.py",     // line 55
    "tests/eval/test_eval_cli.py",                                      // line 59
    "tests/eval/test_eval_storage.py"                                   // line 60
]
```

**Why these files are in `files_modified`**: Git detection (`_detect_git_changes()`, agent_invoker.py:2147-2197) uses `git diff --name-only {baseline_commit}` which returns ALL modified files in the worktree, including workspace template files that the Player created as part of TASK-EVAL-009's eval workspace setup.

**The gap**: `_detect_tests_from_results()` has no awareness of `collect_ignore_glob` patterns. It applies a purely syntactic filter (filename pattern) with no semantic context about whether the file is a "real" test or a template fixture.

```python
# Current code (coach_validator.py:2589-2605) — no path filtering
for filepath in task_work_results.get(file_list_key, []):
    normalized = self._normalize_to_relative(filepath)
    basename = Path(normalized).name
    if basename.startswith("test_") and basename.endswith(".py"):  # ← name only
        full_path = self.worktree_path / normalized
        if full_path.exists():
            test_files.append(str(normalized))
```

---

### SEAM FAILURE 2: Test Output → Failure Classification (coach_validator.py:2631-2719)

**Technology Boundary**: pytest error output (text) → `_classify_test_failure()` (classification logic)

**What happens**: The classifier extracts the missing module name from `ModuleNotFoundError: No module named 'tests.test_health'`. It extracts `"tests"` as the root module (via `.split(".")[0]`). `"tests"` is not in `_KNOWN_SERVICE_CLIENT_LIBS` and `requires_infrastructure` is empty, so it falls through to the catch-all `("infrastructure", "ambiguous")`.

**The precise error** (from `coach_turn_1.json` line 16):
```
ModuleNotFoundError: No module named 'tests.test_health'
```

**Critical nuance**: The error is NOT `No module named 'sample_project'` (the import in the test file). It's `No module named 'tests.test_health'` — a pytest module resolution collision. The workspace `tests/` directory contains `__init__.py`, making it a Python package. When pytest tries to resolve the module path for `guardkit/eval/workspaces/guardkit-project/tests/test_health.py`, it finds a `tests` package that conflicts with the parent project's `tests/` package.

**Classification flow**:
```python
# Input: "No module named 'tests.test_health'"
match = re.search(r"no module named '([^']+)'", test_output, re.IGNORECASE)
# match.group(1) = "tests.test_health"
missing_module = "tests.test_health".split(".")[0]  # = "tests"

# "tests" not in _KNOWN_SERVICE_CLIENT_LIBS → not infrastructure (high)
# requires_infrastructure is [] → not code (high)
# → ("infrastructure", "ambiguous")  ← CATCH-ALL
```

**The gap**: The classifier has no category for "test collection errors caused by pytest discovering files from a different project context". The `"tests"` module is actually the parent project's own `tests/` package — it's not an external service dependency or an infrastructure requirement. The classification is technically wrong: this isn't an infrastructure issue at all, it's a test discovery scope issue.

---

### SEAM FAILURE 3: Classification → Conditional Approval (coach_validator.py:689-695)

**Technology Boundary**: `_classify_test_failure()` result → `conditional_approval` decision logic

**What happens**: The conditional approval check requires ALL of:
1. `failure_class == "infrastructure"` → **TRUE**
2. `failure_confidence == "high"` → **FALSE** (ambiguous)
3. `bool(requires_infra)` → **FALSE** (empty list `[]`)
4. `not docker_available` → **TRUE** (docker_available=False)
5. `gates_status.all_gates_passed` → **TRUE**

Two conditions fail, so `conditional_approval = False`.

**Evidence** (from run log, line 1473):
```
conditional_approval check: failure_class=infrastructure, confidence=ambiguous,
requires_infra=[], docker_available=False, all_gates_passed=True
```

**The gap**: The conditional approval was designed for a specific scenario: "task requires external services (PostgreSQL, Redis) that need Docker, Docker is unavailable, but we trust the Player's tests because quality gates passed." It has no concept of "the test discovery scope was wrong, the tests we're trying to run don't belong to this project, and the real tests already passed."

---

### SEAM FAILURE 4: Explicit pytest Arguments → collect_ignore_glob (pytest behaviour)

**Technology Boundary**: Coach test command construction → pytest collection engine

**What happens**: The Coach constructs:
```bash
pytest guardkit/eval/workspaces/guardkit-project/tests/test_health.py \
      guardkit/eval/workspaces/plain-project/tests/test_health.py \
      tests/eval/test_eval_cli.py \
      tests/eval/test_eval_storage.py \
      -v --tb=short
```

When files are passed as explicit CLI arguments, pytest's `collect_ignore_glob` (defined in root `conftest.py`) is **not applied**. This is documented pytest behaviour: `collect_ignore_glob` only affects automatic test discovery, not explicitly specified paths.

The root `conftest.py` correctly defines:
```python
collect_ignore_glob = [
    "guardkit/eval/workspaces/*/tests/*",
    "templates/*/tests/*",
]
```

This works perfectly for `pytest tests/` (automatic discovery) but is completely bypassed when files are listed explicitly.

**The gap**: The Coach constructs its test command using explicit file paths (from Tier 1 detection), which fundamentally changes how pytest handles collection exclusions.

---

## Stall Loop Trace

```
Turn 1:
  Player: Creates 29 files including workspace template tests → SUCCESS
  Coach:  _detect_tests_from_results() finds 4 test files (2 real + 2 template)
          pytest runs with explicit args → collection error on 2 template files
          _classify: ("infrastructure", "ambiguous")
          conditional_approval: False (ambiguous ≠ high, requires_infra empty)
          → FEEDBACK (sig=85ab9aea, criteria=0/12)

Turn 2:
  Player: Modifies 37 files, tries to fix infrastructure → SUCCESS
          (But cannot fix: error is in Coach's test command, not in code)
  Coach:  SAME _detect_tests_from_results() → SAME 4 files
          SAME pytest command → SAME collection error
          SAME classification → SAME feedback
          → FEEDBACK (sig=85ab9aea, criteria=0/12)  ← IDENTICAL

Turn 3 (perspective reset):
  Player: Fresh start (no prior feedback), creates 2 files, modifies 40 → SUCCESS
  Coach:  SAME flow → SAME result
          → FEEDBACK (sig=85ab9aea, criteria=0/12)  ← IDENTICAL

Stall Detection:
  _is_feedback_stalled():
    recent = [(85ab9aea, 0), (85ab9aea, 0), (85ab9aea, 0)]
    sigs = {"85ab9aea"} → len=1 → all identical
    counts = [0, 0, 0] → all equal to 0
    → STALL DETECTED → UNRECOVERABLE_STALL
```

**Why perspective reset didn't help**: The reset clears `previous_feedback` (so the Player starts fresh), but the root cause is in the Coach's test discovery — which is deterministic and doesn't change between turns. The same `task_work_results.json` file list produces the same test command every time.

**Why criteria stayed at 0/12**: The Coach's `acceptance_criteria_verification.criteria_results` was empty (line 23-24 of `coach_turn_1.json`):
```json
"acceptance_criteria_verification": {
    "criteria_results": []
}
```
When the independent test verification fails, the Coach returns feedback immediately (coach_validator.py:737-752) without proceeding to requirements/criteria verification. So criteria are never evaluated.

---

## Root Cause Summary Table

| Seam | Components | Failure Mode | Severity |
|------|-----------|--------------|----------|
| **1** | `_detect_tests_from_results()` → pytest CLI | No path-based filtering; workspace template tests included | Critical |
| **2** | pytest error text → `_classify_test_failure()` | Module `"tests"` doesn't match any known pattern; defaults to ambiguous | Medium |
| **3** | Classification → `conditional_approval` | Requires `high` confidence + declared infra; neither present | Medium |
| **4** | Explicit pytest args → `collect_ignore_glob` | Documented pytest behaviour: explicit args bypass glob ignore | Informational |

**Failure chain**: 1 → 4 → 2 → 3 → feedback → stall

---

## Regression-Safe Fix Specifications

### Fix 1: Filter Excluded Paths in `_detect_tests_from_results()` (CRITICAL)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Method**: `_detect_tests_from_results()` (lines 2569-2615)

**Specification**: Before appending a test file to the command, check if its path matches any `collect_ignore_glob` pattern from the root `conftest.py`. If it matches, exclude it.

**Implementation approach**:
```python
def _detect_tests_from_results(self, task_work_results):
    # NEW: Load exclusion patterns from root conftest.py
    ignore_patterns = self._load_collect_ignore_glob()

    test_files = []
    for file_list_key in ("files_created", "files_modified"):
        for filepath in task_work_results.get(file_list_key, []):
            normalized = self._normalize_to_relative(filepath)
            basename = Path(normalized).name
            if basename.startswith("test_") and basename.endswith(".py"):
                # NEW: Check against ignore patterns
                if self._matches_ignore_pattern(normalized, ignore_patterns):
                    logger.debug(f"Excluding {normalized} (matches collect_ignore_glob)")
                    continue
                full_path = self.worktree_path / normalized
                if full_path.exists():
                    test_files.append(str(normalized))
    # ... rest unchanged

def _load_collect_ignore_glob(self) -> list[str]:
    """Parse collect_ignore_glob from root conftest.py."""
    conftest_path = self.worktree_path / "conftest.py"
    if not conftest_path.exists():
        return []
    try:
        import ast
        tree = ast.parse(conftest_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "collect_ignore_glob":
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return []

def _matches_ignore_pattern(self, filepath: str, patterns: list[str]) -> bool:
    """Check if filepath matches any collect_ignore_glob pattern."""
    from fnmatch import fnmatch
    return any(fnmatch(filepath, pattern) for pattern in patterns)
```

**Regression risks**:
- **Risk**: AST parsing of conftest.py could fail on complex expressions → **Mitigation**: Returns `[]` on any error, falling back to current behaviour (no filtering). Test with dynamic, conditional, and multi-line `collect_ignore_glob` definitions.
- **Risk**: `fnmatch` semantics differ from pytest glob matching → **Mitigation**: pytest uses `fnmatch` internally for `collect_ignore_glob`, so this is semantically identical.
- **Risk**: Filtering out legitimate test files → **Mitigation**: Only filters files matching user-defined `collect_ignore_glob` patterns. If the user put them there, they intended to exclude them.

**Test cases**:
1. Test file matching ignore pattern is excluded
2. Test file NOT matching ignore pattern is included
3. No conftest.py → no filtering (backward compatible)
4. conftest.py without `collect_ignore_glob` → no filtering
5. Multiple ignore patterns → all applied
6. Absolute path normalised to relative before matching

---

### Fix 2: Add Collection Error Detection to Classification (MEDIUM)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Method**: `_classify_test_failure()` (lines 2631-2719)

**Specification**: Before the generic `ModuleNotFoundError` handler, detect pytest collection errors specifically. When `Interrupted: N errors during collection` appears in the output, classify as `("collection_error", "high")`.

**Implementation approach**:
```python
def _classify_test_failure(self, test_output, requires_infrastructure=None):
    if not test_output:
        return ("code", "n/a")
    output_lower = test_output.lower()

    # NEW: Detect pytest collection errors (before ModuleNotFoundError check)
    # Collection errors (exit code 2) mean pytest couldn't even import the test
    # files. This is distinct from test execution failures.
    if "errors during collection" in output_lower or "error collecting" in output_lower:
        logger.debug(
            f"[{self.task_id}] _classify_test_failure: pytest collection error "
            f"detected → ('collection_error', 'high')"
        )
        return ("collection_error", "high")

    # ... existing ModuleNotFoundError, SDK API, infra checks unchanged
```

**New handling in `validate()`** (lines 704-752):
```python
if not conditional_approval:
    if failure_class == "collection_error":
        description = (
            "Test collection failed: pytest could not import one or more "
            "test files. This typically means test files from a different "
            "project context were included in the test command. "
            "The Coach will retry without the problematic files."
        )
        # NEW: Retry with filtered test files
        filtered_cmd = self._retry_without_collection_errors(
            test_result.test_command, test_result.raw_output
        )
        if filtered_cmd:
            retry_result = self.run_independent_tests_with_command(filtered_cmd, ...)
            if retry_result.tests_passed:
                # Treat as conditional approval
                conditional_approval = True
```

**Regression risks**:
- **Risk**: False positive on legitimate collection errors (e.g., syntax errors in test files) → **Mitigation**: Only retry with filtered files; if retry also fails, return feedback as before.
- **Risk**: Adding new `"collection_error"` class may break consumers → **Mitigation**: Add to existing classification enum. All consumers should handle unknown classes gracefully (existing `else` branches).

**Test cases**:
1. pytest collection error output correctly classified as `("collection_error", "high")`
2. Normal test failure NOT classified as collection error
3. Mixed collection errors + test failures detected
4. Retry without problematic files succeeds → approval
5. Retry without problematic files fails → feedback

---

### Fix 3: Add Approval Path for All-Gates-Passed with Test Scope Errors (MEDIUM)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Method**: `validate()` (lines 689-695)

**Specification**: Expand `conditional_approval` to include a second path: when all quality gates pass AND the independent test failure is a collection error (not an execution failure), approve with a warning.

**Implementation approach**:
```python
conditional_approval = (
    # Existing path: infrastructure dependency with Docker unavailable
    (
        failure_class == "infrastructure"
        and failure_confidence == "high"
        and bool(requires_infra)
        and not docker_available
        and gates_status.all_gates_passed
    )
    # NEW path: collection error with all gates passed
    or (
        failure_class == "collection_error"
        and gates_status.all_gates_passed
    )
)
```

**Regression risks**:
- **Risk**: Approving tasks where collection errors mask real test failures → **Mitigation**: Only applies when ALL quality gates (including Player-reported tests) passed. The Player's tests ran successfully; only the Coach's re-verification failed at collection.
- **Risk**: Silently approving broken code → **Mitigation**: Log as WARNING with full details of which files caused collection errors. Include in approval rationale.

**Test cases**:
1. Collection error + all gates passed → conditional approval
2. Collection error + some gates failed → feedback (not approved)
3. Regular test failure + all gates passed → NOT approved (must still be "infrastructure" + "high")
4. Existing infrastructure path still works unchanged

---

### Fix 4: Include Test Command and Error Details in Player Feedback (LOW)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Method**: `validate()` feedback construction (lines 717-729)

**Specification**: When providing feedback for infrastructure or collection errors, include the exact test command and the error output so the Player can understand what failed and why.

**Implementation approach**:
```python
elif failure_class in ("infrastructure", "collection_error"):
    # Include actual test command and error for actionability
    error_detail = ""
    if test_result.test_output_summary:
        error_detail = f":\n  Error detail:\n\n{test_result.test_output_summary}"
    description = (
        f"Tests failed due to infrastructure/environment issues "
        f"(not code defects). Remediation options: "
        f"(1) Add mock fixtures for external services, "
        f"(2) Use SQLite for test database, "
        f"(3) Mark integration tests with @pytest.mark.integration "
        f"and exclude via -m 'not integration'"
        f"{error_detail}"
    )
```

**Regression risks**: Minimal. Only changes feedback text content. No logic changes.

**Test cases**:
1. Feedback includes test command when available
2. Feedback includes error output when available
3. Feedback still works when test output is None/empty

---

## Impact Assessment

### TASK-EVAL-009 Status

The implementation is **complete and working**:
- 46 tests passing with 100% coverage
- All 12 acceptance criteria addressed with evidence
- 3 git checkpoints (all tests passing)
- Quality gates: tests=PASS, coverage=PASS, arch=PASS, audit=PASS
- Code review score: 95/100

The worktree is preserved at `.guardkit/worktrees/FEAT-4296` with branch `autobuild/FEAT-4296`.

### TASK-EVAL-010 (Integration Tests)

This task depends on TASK-EVAL-009 and was skipped due to `stop_on_failure=True`. It can proceed once TASK-EVAL-009 is marked complete.

### Recommended Remediation for TASK-EVAL-009

1. **Manual completion** (Recommended): Mark TASK-EVAL-009 as completed in `.guardkit/features/FEAT-4296.yaml`, then resume with `guardkit autobuild feature FEAT-4296 --resume` to execute TASK-EVAL-010.

2. **Alternative**: Cherry-pick checkpoint commit `9d2ca44f` from `autobuild/FEAT-4296` branch.

### Feature Quality Assessment

8/10 tasks completed with excellent quality:
- 6 tasks approved in 1 turn (first attempt)
- 2 tasks approved in 2 turns (with actionable feedback → recovery)
- 0 SDK ceiling hits across 9 invocations
- 100% clean execution rate

---

## Decision Matrix (Revised)

| Fix | Seam | Impact | Effort | Regression Risk | Recommendation |
|-----|------|--------|--------|-----------------|----------------|
| Fix 1: Filter excluded paths | Seam 1 | Critical | Low (2-3h) | Low (fallback to no-filter) | Implement first |
| Fix 2: Collection error class | Seam 2 | High | Medium (3-4h) | Low (additive) | Implement second |
| Fix 3: Expanded approval path | Seam 3 | High | Low (1h) | Medium (review carefully) | Implement with Fix 2 |
| Fix 4: Detailed feedback | Coach→Player | Low | Low (1h) | None | Implement with Fix 1 |
| Remediate TASK-EVAL-009 | N/A | High | Low (30min) | None | Do immediately |

---

## Appendix A: Evidence Files

| Artefact | Path | Key Lines |
|----------|------|-----------|
| Run log | `docs/reviews/eval_runner/eval_runner_1.md` | 1550-1577 (stall) |
| task_work_results.json | `.guardkit/worktrees/FEAT-4296/.guardkit/autobuild/TASK-EVAL-009/task_work_results.json` | 50, 55 (problem files) |
| coach_turn_1.json | `.guardkit/worktrees/FEAT-4296/.guardkit/autobuild/TASK-EVAL-009/coach_turn_1.json` | 15-17 (test command + error) |
| Root conftest.py | `.guardkit/worktrees/FEAT-4296/conftest.py` | 14-21 (collect_ignore_glob) |
| Coach validator | `guardkit/orchestrator/quality_gates/coach_validator.py` | 2569-2615 (detect), 2631-2719 (classify), 689-695 (approval) |
| AutoBuild orchestrator | `guardkit/orchestrator/autobuild.py` | 2698-2779 (stall detection) |
| Agent invoker | `guardkit/orchestrator/agent_invoker.py` | 2147-2197 (git detection), 4491-4647 (write results) |
| Workspace test | `.guardkit/worktrees/FEAT-4296/guardkit/eval/workspaces/guardkit-project/tests/test_health.py` | 1-14 (imports sample_project) |

## Appendix B: Verified Data Flow

```
Player SDK creates workspace files
    ↓
AgentInvoker._write_task_work_results()     [agent_invoker.py:4491]
    writes files_modified from parsed SDK output
    ↓
AgentInvoker._create_player_report()         [agent_invoker.py:1782]
    enriches with git diff (adds 36 modified files)
    writes back to task_work_results.json     [agent_invoker.py:2082-2118]
    ↓
CoachValidator._detect_tests_from_results()  [coach_validator.py:2569]
    scans files_modified for test_*.py basename match
    finds 4 files (2 real + 2 workspace templates)
    ↓
CoachValidator.run_independent_tests()        [coach_validator.py:1235]
    dispatches to _run_tests_via_sdk()        [coach_validator.py:1050]
    sends prompt with pytest command to SDK
    ↓
Claude Agent SDK → Bash tool → pytest         [subprocess in SDK session]
    pytest receives explicit file args
    collection bypasses collect_ignore_glob
    ↓
pytest collection error                        [pytest internals]
    tests/__init__.py creates module collision
    ModuleNotFoundError: 'tests.test_health'
    ↓
CoachValidator._classify_test_failure()       [coach_validator.py:2631]
    missing_module = "tests" (from "tests.test_health".split(".")[0])
    "tests" not in _KNOWN_SERVICE_CLIENT_LIBS
    requires_infrastructure = []
    → ("infrastructure", "ambiguous")
    ↓
CoachValidator.validate() conditional_approval [coach_validator.py:689]
    confidence ≠ "high" → False
    requires_infra empty → False
    → conditional_approval = False
    → FEEDBACK returned
    ↓
AutoBuild._is_feedback_stalled()              [autobuild.py:2698]
    normalise → MD5 → sig=85ab9aea
    3 identical sigs + 0 criteria → STALL
```
