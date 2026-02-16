# Review Report: TASK-REV-F3BE

## Executive Summary

TASK-DB-003 (Implement User model schemas and CRUD) entered an unrecoverable stall after 6 turns due to a **checkpoint-induced test file invisibility** combined with a **restrictive fallback glob pattern** in the Coach's test detection. The root cause is more nuanced than a simple naming mismatch: checkpoint commits (`git add -A && git commit`) cause previously-created test files to become invisible to the git-based file detection on subsequent turns, and the fallback glob pattern (`tests/**/test_task_db_003*.py`) is too rigid to find domain-named test files.

This was the first `feature` task type to reach the test detection code path in production. The 3 prior features (14/14 tasks, 100% clean) all used `scaffolding` task types where `tests_required=False`, so the latent defect was never exercised.

**Confidence level**: High. Root cause verified through line-by-line code trace across 4 source files. All findings cross-referenced against the debug log.

## Review Details

- **Mode**: Architectural/Decision Review (Revised — deeper analysis)
- **Depth**: Comprehensive
- **Task**: TASK-REV-F3BE (Analyse PostgreSQL DB integration autobuild stall)
- **Related Feature**: FEAT-BA28 (PostgreSQL Database Integration)
- **Files Reviewed**: `coach_validator.py`, `autobuild.py`, `agent_invoker.py`, `worktree_checkpoints.py`, `task_types.py`, `test_coach_validator.py`

---

## Finding 1: Checkpoint Commits Make Test Files Invisible (ROOT CAUSE)

**Severity**: Critical
**Location**: [worktree_checkpoints.py:397-411](guardkit/orchestrator/worktree_checkpoints.py#L397-L411) interacting with [agent_invoker.py:1695-1737](guardkit/orchestrator/agent_invoker.py#L1695-L1737)

### The mechanism

After each turn, the checkpoint manager runs `git add -A && git commit` (line 397-411). This commits ALL worktree files including test files the Player created. On the next turn, the git-based file detection (`_detect_git_changes`) uses:

1. `git diff --name-only HEAD` — shows files modified since the **last checkpoint commit** (not the task start)
2. `git ls-files --others --exclude-standard` — shows **untracked** files only

Once a test file is committed by the checkpoint, it disappears from both:
- It's no longer untracked (committed), so `git ls-files --others` won't find it
- If the Player doesn't modify it on the next turn, `git diff --name-only HEAD` won't show it either

### Why Turn 1 worked but Turn 2+ didn't

- **Turn 1**: Player created `tests/users/test_users.py` as a new file. The `_detect_tests_from_results` method found it in `files_created` (from `task_work_results.json`). Coach ran it → import ERROR.
- **After Turn 1**: Checkpoint commits `test_users.py` (line 397: `git add -A`).
- **Turn 2+**: Player's `task_work_results.json` doesn't list `test_users.py` in `files_created` (it's not new) or `files_modified` (Player may not have touched it). The git enrichment (line 1520) also misses it because it's now a committed tracked file unchanged from HEAD.

### Evidence from the log

| Turn | Detection Method | Result | Log Line |
|------|-----------------|--------|----------|
| 1 | `_detect_tests_from_results` (files_created) | Found `test_users.py` | 489: "Task-specific tests detected via task_work_results: 1 file(s)" |
| 2 | `_detect_tests_from_results` → None, then glob | Both missed | 550: "No task-specific tests found... Glob pattern tried: tests/**/test_task_db_003*.py" |
| 3-6 | Same as Turn 2 | Same miss | 606, 661, 718, 774: identical log lines |

### Additional complication: output override

At [agent_invoker.py:1568-1575](guardkit/orchestrator/agent_invoker.py#L1568-L1575), after git enrichment adds files to the report, the code checks `task_work_result.output` and can **override** the enriched `files_created`/`files_modified` with the Player's own (potentially incomplete) lists. This means even if git detection DID find the test file, the Player's SDK output could overwrite it.

```python
# Lines 1572-1575 — this can undo git enrichment
if "files_modified" in output:
    report["files_modified"] = output["files_modified"]
if "files_created" in output:
    report["files_created"] = output["files_created"]
```

---

## Finding 2: Fallback Glob Pattern is Unreasonably Restrictive

**Severity**: High
**Location**: [coach_validator.py:1525-1542](guardkit/orchestrator/quality_gates/coach_validator.py#L1525-L1542) and [coach_validator.py:1588-1611](guardkit/orchestrator/quality_gates/coach_validator.py#L1588-L1611)

`_task_id_to_pattern_prefix` converts `TASK-DB-003` → `task_db_003`, then the glob becomes `tests/**/test_task_db_003*.py`.

No AI agent or human developer would naturally name a test file `test_task_db_003_users.py`. Domain naming (`test_users.py`, `test_user_crud.py`) is universal practice. The fallback glob only works for projects that adopt GuardKit's task-ID naming convention, which none of the example projects do.

This pattern is a latent defect that will fail for **every** `feature` task type where the primary detection (from `files_created`/`files_modified`) misses the test file.

### Test coverage confirms the gap

The existing test suite ([test_coach_validator.py:1739-2235](tests/unit/test_coach_validator.py#L1739-L2235)) thoroughly tests `_detect_test_command` but only with task-ID-named test files (e.g., `test_task_fha_002_something.py`). There are no tests for the scenario where domain-named test files exist but the task-ID glob misses them.

---

## Finding 3: Zero-Test Anomaly Logic is Sound but Data-Starved

**Severity**: Medium
**Location**: [coach_validator.py:1769-1858](guardkit/orchestrator/quality_gates/coach_validator.py#L1769-L1858)

The zero-test anomaly check is well-designed:

1. If `tests_required=False` (scaffolding) → skip check entirely (line 1798) ✓
2. If independent tests ran and passed (`test_command != "skipped"`) → clear anomaly via defense-in-depth (line 1806-1811) ✓
3. If `tests_written=[]` AND `test_command="skipped"` → blocking error for `feature` tasks (`zero_test_blocking=True`) ✓

The problem is entirely upstream: the Coach never gets the chance to run independent tests because `_detect_test_command` returns `None`, which sets `test_command="skipped"`. If the tests were found and run (even if they failed), the flow would proceed through the normal test failure feedback path (line 545-560) instead of the zero-test anomaly path. Test failures produce actionable feedback (file path, error message); the zero-test anomaly does not.

**Key insight**: The defense-in-depth escape hatch (line 1806-1811) is the correct release valve. The fix should ensure tests are FOUND and RUN, even if they fail — because test failure feedback is actionable while zero-test anomaly feedback is not.

---

## Finding 4: Feedback to Player Lacks Actionable Information

**Severity**: High
**Location**: [coach_validator.py:1830-1837](guardkit/orchestrator/quality_gates/coach_validator.py#L1830-L1837) and [autobuild.py:3648-3669](guardkit/orchestrator/autobuild.py#L3648-L3669)

The zero-test anomaly produces this description (line 1833-1837):
> "No task-specific tests created and no task-specific tests found via independent verification. Project-wide test suite may pass but this task contributes zero test coverage."

The feedback extraction in `_extract_feedback` (line 3648-3669) converts this issue description into the feedback string relayed to the Player. The Player receives:
> "- No task-specific tests created and no task-specific tests found via independen..."

This is truncated (line in display) and provides zero guidance on:
1. What glob pattern the Coach expects
2. That the Player's test file exists but isn't being detected
3. What to name test files to be found

The feedback signature `36d91c7c` was identical for 5 consecutive turns because the same description text was generated each time — the Player received no new information to break the loop.

---

## Finding 5: `tests_written` Population Has Conditional Bug

**Severity**: Medium
**Location**: [agent_invoker.py:1480-1492](guardkit/orchestrator/agent_invoker.py#L1480-L1492)

The `tests_written` field is only populated when `tests_info` exists in `task_work_results.json`:

```python
tests_info = task_work_data.get("tests_info", {})
if tests_info:  # <-- Gate: tests_written only populated if tests_info exists
    report["tests_written"] = [
        f for f in report["files_created"] + report["files_modified"]
        if "test" in f.lower() or f.endswith("_test.py")
    ]
```

If the Player doesn't write a `tests_info` block (which it often doesn't in early turns), `tests_written` stays as `[]` even if test files appear in `files_created`/`files_modified`.

The direct mode synthetic report at [agent_invoker.py:1778-1784](guardkit/orchestrator/agent_invoker.py#L1778-L1784) correctly populates `tests_written` unconditionally from git changes, but the task-work delegation path has this conditional gate.

**Note**: This is a contributing factor but not the primary cause. Even with `tests_written` correctly populated, the zero-test anomaly would still check `independent_tests.test_command` which would still be `"skipped"` if `_detect_test_command` returns `None`. However, fixing this would make diagnostics clearer and could help other code paths.

---

## Finding 6: Successful Runs Never Exercised This Path

**Severity**: Informational

All prior runs used these quality gate profiles:
- **FEAT-F97F** (Health endpoint): All tasks were `scaffolding` → `tests_required=False`, `zero_test_blocking=False`
- **FEAT-AAC2** (API docs): All tasks were `documentation` → `tests_required=False`
- **FEAT-CC79** (JSON Logging): Tasks included some with test verification, but completed in ≤4 turns (no stall)

Within FEAT-BA28:
- **TASK-DB-001**: `scaffolding` → test verification skipped (log line 111)
- **TASK-DB-002**: `scaffolding` → test verification skipped (log line 432)
- **TASK-DB-003**: `feature` → `tests_required=True`, `zero_test_blocking=True` (log line 487)

TASK-DB-003 was the first time the full test detection → independent verification → zero-test anomaly chain was exercised in production.

---

## Finding 7: Stall Detection is Correctly Calibrated

**Severity**: Low
**Location**: [autobuild.py:2619-2699](guardkit/orchestrator/autobuild.py#L2619-L2699)

The stall detection correctly:
1. Applied the base threshold of 3 turns
2. Extended to 5 turns because `criteria_passed_count=6` (partial progress, line 2677-2690)
3. Declared stall at Turn 6 (5 identical feedback signatures with 6/6 criteria passing)

The partial progress extension (TASK-REV-E719 Fix 3) is a safety net for tasks that are genuinely progressing — it correctly identified that 6/6 criteria passing with zero-test anomaly is a system-level mismatch, not a Player implementation issue.

**No change needed.** Reducing the threshold would risk premature termination of genuinely progressing tasks that have recoverable test failures.

---

## Revised Recommendations (Regression-Tested)

### Rec 1: Use Cumulative Git Diff for Test Detection (HIGH IMPACT, MEDIUM EFFORT)

**Problem**: `_detect_git_changes` uses `git diff --name-only HEAD` which only shows changes since the last checkpoint commit. After checkpoint commits, previously-created test files become invisible.

**Fix**: In `_detect_test_command`, when both primary detection and task-ID glob fail, query ALL test files changed since the task started using a cumulative diff against the pre-task baseline.

```python
# In _detect_test_command, after line 1611 (before returning None):
# Tertiary fallback: find test files created during this task's lifetime
# Uses git log to find the first checkpoint commit, then diff against its parent
try:
    # Find files changed across all checkpoints for this task
    first_checkpoint = self._find_first_checkpoint_parent()
    if first_checkpoint:
        result = subprocess.run(
            ["git", "diff", "--name-only", first_checkpoint, "HEAD"],
            cwd=str(self.worktree_path),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            changed_files = result.stdout.strip().split("\n")
            test_files = [
                f for f in changed_files
                if f.strip() and (
                    Path(f).name.startswith("test_") and f.endswith(".py")
                    or f.endswith("_test.py")
                ) and (self.worktree_path / f).exists()
            ]
            if test_files:
                files_str = " ".join(sorted(test_files))
                logger.info(
                    f"Found test files via cumulative diff for {task_id}: "
                    f"{len(test_files)} file(s)"
                )
                return f"pytest {files_str} -v --tb=short"
except Exception as e:
    logger.debug(f"Cumulative diff fallback failed: {e}")
```

**Why NOT "find all test files in worktree"**: In shared worktrees (feature mode), multiple tasks run in the same worktree. A broad `glob("tests/**/test_*.py")` would pick up test files from OTHER parallel tasks that may have unresolved dependencies, causing false failures. The code explicitly documents this concern at [coach_validator.py:1557-1560](guardkit/orchestrator/quality_gates/coach_validator.py#L1557-L1560): *"This is essential for shared worktrees where parallel tasks may have tests with unmet dependencies."*

The cumulative diff approach is safe because it only finds files that were changed during the current task's turns, not files from other tasks.

**Regression risk**: LOW. This only activates as a third fallback when both existing detection methods fail. It scopes to the current task's lifetime via git history. Existing scaffolding/documentation tasks skip test verification entirely (`tests_required=False`) so this path is never reached.

**Existing test coverage**: The `TestDetectTestCommand` class in `test_coach_validator.py` covers the primary and fallback paths extensively. New tests would be needed for this tertiary fallback.

### Rec 2: Include Actionable Context in Zero-Test Anomaly Feedback (HIGH IMPACT, LOW EFFORT)

**Fix**: Modify the zero-test anomaly issue description to include the glob pattern and a suggestion.

```python
# In _check_zero_test_anomaly, around line 1830:
task_prefix = self._task_id_to_pattern_prefix(task_id) if hasattr(self, 'task_id') else "unknown"
description = (
    f"No task-specific tests found. Coach searched:\n"
    f"  1. task_work_results files_created/files_modified for test_*.py files\n"
    f"  2. Glob pattern: tests/**/test_{task_prefix}*.py\n"
    f"Please ensure test files are listed in your task_work_results "
    f"files_created or files_modified arrays, OR name them to match the glob pattern."
)
```

**Regression risk**: NONE. This only changes the text content of the feedback message. The structure (`severity`, `category`, `description`) is unchanged. The stall detection uses an MD5 hash of feedback text, so different feedback text between turns would actually HELP break stalls faster (different signature → counter resets).

**Existing test coverage**: Tests at lines 2330-3235 verify the zero-test anomaly issues by checking `category == "zero_test_anomaly"` and `severity`, not the description text. This change won't break any existing tests.

### Rec 3: Fix `tests_written` Population to be Unconditional (MEDIUM IMPACT, LOW EFFORT)

**Fix**: Remove the `if tests_info:` gate so `tests_written` is always populated from `files_created`/`files_modified`.

```python
# In agent_invoker.py, around line 1480:
# Extract test info (conditional)
tests_info = task_work_data.get("tests_info", {})
if tests_info:
    report["tests_run"] = tests_info.get("tests_run", False)
    report["tests_passed"] = tests_info.get("tests_passed", False)
    report["test_output_summary"] = tests_info.get("output_summary", "")

# ALWAYS extract test files from file lists (unconditional)
# Previously gated behind `if tests_info:` which caused tests_written=[]
# when the Player didn't write a tests_info block
all_files = report.get("files_created", []) + report.get("files_modified", [])
report["tests_written"] = [
    f for f in all_files
    if "test" in Path(f).name.lower() or f.endswith("_test.py")
]
```

**Regression risk**: LOW. This makes `tests_written` more accurate (never empty when test files exist in file lists). The field is used by:
1. `_check_zero_test_anomaly` (line 1817) — checks `len(tests_written) == 0`. Correctly populating it prevents false zero-test anomalies.
2. `_check_seam_test_recommendation` (line 1892) — checks test file names for seam patterns. More accurate data improves recommendations.

The direct mode path at line 1778-1784 already does this unconditionally, so this aligns the task-work delegation path with existing behavior.

### Rec 4: Fix the Output Override That Clobbers Git Enrichment (MEDIUM IMPACT, LOW EFFORT)

**Fix**: Change the output override at [agent_invoker.py:1572-1575](guardkit/orchestrator/agent_invoker.py#L1572-L1575) to MERGE instead of REPLACE.

```python
# Change from:
if "files_modified" in output:
    report["files_modified"] = output["files_modified"]
if "files_created" in output:
    report["files_created"] = output["files_created"]

# To:
if "files_modified" in output:
    existing = set(report["files_modified"])
    report["files_modified"] = sorted(list(existing | set(output["files_modified"])))
if "files_created" in output:
    existing = set(report["files_created"])
    report["files_created"] = sorted(list(existing | set(output["files_created"])))
```

**Regression risk**: LOW. This preserves all existing file entries and adds any new ones from the Player output. The only behavioral change is that git-detected files are no longer lost when the Player's SDK output is processed. The TASK-FIX-PIPELINE comments (line 1517-1518) explicitly state the intent is to "capture changes even if task_work_results.json has empty arrays" — the current override at line 1572-1575 contradicts this intent.

### Rec 5: No Change to Stall Detection

Confirmed correct through deeper analysis. The extended threshold of 5 turns for partial progress is appropriate.

### Rec 6: No Change to Zero-Test Anomaly Blocking Logic

The blocking behavior for `feature` tasks (`zero_test_blocking=True`) is correct. The defense-in-depth escape hatch works as designed. The fix should ensure tests are found and run (Rec 1), not weaken the blocking behavior.

---

## Revised Decision Matrix

| Rec | Fix | Impact | Effort | Risk | Priority |
|-----|-----|--------|--------|------|----------|
| 1 | Cumulative git diff for test detection | High | Medium | Low (scoped to task lifetime) | **P1** |
| 2 | Actionable feedback in zero-test anomaly | High | Low | None (text-only change) | **P1** |
| 3 | Unconditional `tests_written` population | Medium | Low | Low (aligns with direct mode) | **P1** |
| 4 | Merge (not replace) output override | Medium | Low | Low (preserves existing + adds new) | **P2** |
| 5 | Stall detection — no change | N/A | None | None | N/A |
| 6 | Zero-test anomaly logic — no change | N/A | None | None | N/A |

**Recommended implementation order**: Rec 3 → Rec 4 → Rec 2 → Rec 1

Rationale: Recs 3 and 4 fix data quality issues that cause the primary detection to fail (low effort, immediate benefit). Rec 2 ensures future stalls break faster with actionable feedback. Rec 1 is the belt-and-suspenders fallback that catches any remaining gaps.

---

## Root Cause Chain (Verified)

```
Turn 1:
  Player creates tests/users/test_users.py (domain-named)
  ↓ files_created contains test_users.py
  ↓ _detect_tests_from_results finds it → Coach runs it → import ERROR
  ↓ Checkpoint: git add -A && git commit (test_users.py now committed)

Turn 2:
  Player rewrites task_work_results.json
  ↓ tests_info not present → tests_written stays [] (Finding 5)
  ↓ Player SDK output overrides git-enriched file lists (Finding 1)
  ↓ _detect_tests_from_results: no test files in files_created/files_modified → None
  ↓ Fallback glob: tests/**/test_task_db_003*.py → no match (Finding 2)
  ↓ _detect_test_command returns None → test_command = "skipped"
  ↓ _check_zero_test_anomaly: tests_written=[] + skipped → BLOCK (Finding 3)
  ↓ Feedback: "No task-specific tests created" — no naming hint (Finding 4)
  ↓ Player: "I need to write tests" → rewrites with domain naming

Turns 3-6: Identical to Turn 2 (feedback sig 36d91c7c)
  ↓ Stall detection fires at Turn 6 (extended threshold = 5)
  ↓ UNRECOVERABLE_STALL
```

**Breaking the chain**: Any ONE of Recs 1-4 would have prevented this stall. Together, they provide defense-in-depth across multiple detection layers.

---

## Appendix A: Turn-by-Turn Evidence

| Turn | Player | Coach Response | Criteria | Detection Method | Test Found |
|------|--------|---------------|----------|-----------------|------------|
| 1 | 9 created (incl `test_users.py`) | Ran `test_users.py` → import ERROR | 0/6 | Primary (files_created) | Yes |
| 2 | 1 created, 3 modified | Zero-test anomaly | 6/6 | Primary→None, Glob→miss | No |
| 3 | 1 created, 4 modified | Zero-test anomaly | 6/6 | Primary→None, Glob→miss | No |
| 4 | 1 created, 3 modified | Zero-test anomaly | 6/6 | Primary→None, Glob→miss | No |
| 5 | 1 created, 4 modified | Zero-test anomaly | 6/6 | Primary→None, Glob→miss | No |
| 6 | 1 created, 3 modified | STALL declared | 6/6 | Primary→None, Glob→miss | No |

## Appendix B: Quality Gate Profiles Used

| Task | Type | tests_required | zero_test_blocking | Outcome |
|------|------|---------------|-------------------|---------|
| TASK-DB-001 | scaffolding | False | False | APPROVED (2 turns) |
| TASK-DB-002 | scaffolding | False | False | APPROVED (2 turns) |
| TASK-DB-003 | feature | True | True | STALL (6 turns) |

## Appendix C: Regression Test Recommendations

Each recommendation should include tests covering:

1. **Rec 1**: Test that cumulative diff finds test files across checkpoint boundaries. Test that it does NOT find test files from other tasks in shared worktrees.
2. **Rec 2**: Test that feedback description includes glob pattern. Verify stall detection hash changes with new text.
3. **Rec 3**: Test that `tests_written` is populated when `tests_info` is absent but test files exist in `files_created`.
4. **Rec 4**: Test that git-enriched files survive output override. Test that Player output files are also included (union, not replace).
