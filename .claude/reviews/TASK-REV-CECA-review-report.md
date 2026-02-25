# Review Report: TASK-REV-CECA (Revised)

## Executive Summary

The FEAT-3CC2 (Structured JSON Logging) autobuild run failed with an UNRECOVERABLE_STALL after 3 turns on TASK-LOG-001. Deep analysis of the preserved worktree artifacts reveals the initial hypothesis (Player not populating fields) was **wrong for Turn 1**.

**The Player on Turn 1 actually reported ALL 7 requirements as addressed.** The data exists in `player_turn_1.json` under `requirements_addressed`. However, **three cascading bugs** prevent the Coach from ever seeing it:

1. **`_write_direct_mode_results` drops `requirements_addressed`** — the field is not copied to `task_work_results.json`
2. **Coach text matching reads `requirements_met`** (wrong field name) — the Player writes `requirements_addressed`
3. **`_write_player_report_for_direct_mode` drops `_synthetic` flag** — prevents synthetic fallback on turns 2-3

These are **code defects in the data pipeline**, not model quality issues. The vLLM Player performed correctly on Turn 1 — all work was done, all criteria addressed, 37 tests passing. The stall is entirely caused by the Coach being unable to read the Player's data.

**Severity**: Critical — This affects ALL direct mode autobuild runs, not just vLLM.

## Review Details

- **Mode**: Root Cause Analysis (Decision) — Revised with deep-dive
- **Depth**: Comprehensive (artifact inspection)
- **Source**: `docs/reviews/gb10_local_autobuild/logging_feature_1.md`
- **Artifacts Inspected**:
  - `api_test/.guardkit/worktrees/FEAT-3CC2/.guardkit/autobuild/TASK-LOG-001/player_turn_1.json`
  - `api_test/.guardkit/worktrees/FEAT-3CC2/.guardkit/autobuild/TASK-LOG-001/player_turn_2.json`
  - `api_test/.guardkit/worktrees/FEAT-3CC2/.guardkit/autobuild/TASK-LOG-001/player_turn_3.json`
  - `api_test/.guardkit/worktrees/FEAT-3CC2/.guardkit/autobuild/TASK-LOG-001/task_work_results.json`
  - `api_test/.guardkit/worktrees/FEAT-3CC2/.guardkit/autobuild/TASK-LOG-001/coach_turn_1.json`
- **Key Files Analysed**:
  - `guardkit/orchestrator/agent_invoker.py` — `_write_direct_mode_results`, `_write_player_report_for_direct_mode`
  - `guardkit/orchestrator/quality_gates/coach_validator.py` — `_validate_requirements`, `_match_by_text`
  - `guardkit/orchestrator/synthetic_report.py` — `build_synthetic_report`
  - `guardkit/orchestrator/autobuild.py` — stall detection, task_type loading

## Findings

### Finding 1 (ROOT CAUSE - CRITICAL): `_write_direct_mode_results` Drops `requirements_addressed`

**Severity**: Critical | **Category**: Code Defect | **File**: `agent_invoker.py:2835-2860`

The `_write_direct_mode_results` method constructs `task_work_results.json` but **does not include `requirements_addressed`** from the Player report. The Player's Turn 1 report contains:

```json
// player_turn_1.json (actual artifact)
{
  "requirements_addressed": [
    "Settings class has log_level field with default INFO",
    "Settings class has log_format field with default json",
    "log_level is configurable via LOG_LEVEL environment variable",
    "log_format is configurable via LOG_FORMAT environment variable",
    ".env.example updated with new variables",
    "structlog added to requirements/base.txt",
    "Existing tests still pass"
  ]
}
```

All 7 criteria addressed. But `task_work_results.json` (actual artifact) has:

```json
// task_work_results.json — NO requirements_addressed field
{
  "task_id": "TASK-LOG-001",
  "completed": true,
  "success": true,
  "files_modified": ["..."],
  "files_created": ["..."],
  "summary": "Direct mode implementation completed successfully"
}
```

**Root cause code** at `agent_invoker.py:2835-2860`:
```python
results: Dict[str, Any] = {
    "task_id": task_id,
    "timestamp": ...,
    "completed": ...,
    "success": ...,
    "implementation_mode": "direct",
    "phases": {...},
    "quality_gates": {...},
    "files_modified": [...],
    "files_created": [...],
    "tests_written": [...],
    "summary": ...,
}
# requirements_addressed NOT COPIED
# requirements_met NOT COPIED
```

### Finding 2 (ROOT CAUSE - CRITICAL): Coach Text Matching Uses Wrong Field Name

**Severity**: Critical | **Category**: Code Defect | **File**: `coach_validator.py:1576-1579`

The text matching fallback reads `requirements_met` but the Player writes `requirements_addressed`:

```python
# coach_validator.py:1576-1579 (text matching path)
strategy = "text"
requirements_met = task_work_results.get("requirements_met", [])  # WRONG FIELD
validation = self._match_by_text(acceptance_criteria, requirements_met)
```

The hybrid fallback at line 1566-1568 correctly checks BOTH field names:
```python
# coach_validator.py:1566-1568 (hybrid fallback - only reached via promises path)
requirements_addressed = task_work_results.get(
    "requirements_addressed",
    task_work_results.get("requirements_met", []),
)
```

But this hybrid path only activates when `completion_promises` are found, which they aren't. So the text matching path is used, and it only checks `requirements_met`.

**Combined effect of Findings 1 & 2**: Even if Finding 1 were fixed (copying `requirements_addressed` to `task_work_results.json`), the text matching path would STILL fail because it checks `requirements_met`, not `requirements_addressed`. Both bugs must be fixed together.

### Finding 3 (BUG): `_write_player_report_for_direct_mode` Drops `_synthetic` Flag

**Severity**: High | **Category**: Code Defect | **File**: `agent_invoker.py:2914-2932`

At `agent_invoker.py:2914-2932`, `_write_player_report_for_direct_mode` rebuilds the report dict but **does not include `_synthetic`**:

```python
report: Dict[str, Any] = {
    "task_id": task_id,
    "turn": turn,
    "files_modified": player_report.get("files_modified", []),
    # ... other fields ...
    "implementation_mode": "direct",
}
# completion_promises copied (line 2934-2937) -- OK
# _synthetic NOT copied -- BUG
```

`_write_direct_mode_results` at line 2871-2873 correctly propagates `_synthetic` but never sees it because the loaded report already lost the flag.

### Finding 4 (BUG): Synthetic Report Path Cannot Load Acceptance Criteria

**Severity**: High | **Category**: Code Defect | **File**: `agent_invoker.py:2662-2670`

When creating synthetic reports, `_create_synthetic_direct_mode_report` loads acceptance criteria from the task file's YAML frontmatter:

```python
metadata = self._load_task_metadata(task_file)  # Reads YAML frontmatter only
acceptance_criteria = metadata.get("acceptance_criteria")  # Returns None!
```

But acceptance criteria are stored in the **markdown body** of task files (parsed by `spec_parser.py`), not in the YAML frontmatter. `_load_task_metadata` only parses between `---` markers. Result: `acceptance_criteria = None`, so `build_synthetic_report(acceptance_criteria=None)` generates NO file-existence promises.

The autobuild orchestrator correctly gets acceptance criteria via `TaskLoader.load_task()` (which parses the full spec), but the agent_invoker's synthetic path uses the simpler `_load_task_metadata()` (YAML-only).

### Finding 5 (BUG): Player Prompt Already Has Strong Instructions

**Severity**: Info (Exonerates vLLM) | **Category**: Context

The Player prompt (from `autobuild_execution_protocol.md:358`) includes an explicit CRITICAL warning:

> **CRITICAL**: You MUST populate `completion_promises` with one entry per acceptance criterion. An empty `completion_promises` array causes the Coach to use text-based fallback matching, which always fails — the autobuild run will stall after 3 turns.

Despite this, the vLLM Player did NOT write `completion_promises` in Turn 1. However, it DID correctly populate `requirements_addressed` with all 7 criteria. The Player followed the instructions partially — it reported requirements correctly but didn't produce the preferred `completion_promises` format. This is acceptable behavior for the fallback path, but the fallback path has the bugs described in Findings 1-2.

### Finding 6 (ARTIFACT): Turns 2-3 Only Detected Internal Files

**Severity**: Medium | **Category**: Observation

The synthetic reports for turns 2-3 (via git detection) only captured internal GuardKit files:

**Turn 2 `player_turn_2.json`**: Only `.guardkit/` internal files (checkpoints.json, coach_feedback, turn_context.json) — no source code changes. The git detection caught orchestrator state changes, not Player work.

**Turn 3 `player_turn_3.json`**: Detected real changes (`src/main.py`, `src/core/logging.py`, `tests/test_logging.py`) plus `.pyc` files. However, `requirements_addressed: []` because synthetic reports don't populate this field.

### Finding 7: Stall Detection Correct But Preventable

**Severity**: Info | **Category**: Positive Finding

Stall detection correctly identified identical feedback. However, if Finding 1 were fixed, Turn 1 would have been approved (7/7 criteria met, all quality gates passed). The stall was entirely unnecessary.

## Revised Root Cause Chain

```
Turn 1: Player correctly reports requirements_addressed: [7/7]
    |
    v
_write_direct_mode_results DROPS requirements_addressed
    |
    v
task_work_results.json has NO requirements data
    |
    v
Coach _validate_requirements reads task_work_results.get("requirements_met")
    |-- Field doesn't exist → defaults to []
    |-- Text matching with [] → 0/7
    |-- (Even if requirements_addressed WERE in task_work_results,
    |    text matching checks requirements_met, not requirements_addressed)
    |
    v
Coach gives "feedback: 0/7 criteria met" (WRONG — all were met!)
    |
    v
Turns 2-3: Player re-implements, SDK doesn't write report
    |-- Synthetic report: _synthetic flag dropped, acceptance_criteria=None
    |-- No file-existence promises generated
    |-- git detection only catches internal .guardkit files (Turn 2)
    |
    v
3 identical feedback turns → UNRECOVERABLE_STALL
```

## Revised Recommendations

### Priority 1 (CRITICAL): Fix `_write_direct_mode_results` to Include Requirements

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: `_write_direct_mode_results` method (~line 2860)
**Change**: Copy `requirements_addressed` and `requirements_met` from Player report:

```python
# After tests_written line (~2855), add:
"requirements_addressed": player_report.get("requirements_addressed", []),
"requirements_met": player_report.get("requirements_met",
    player_report.get("requirements_addressed", [])),
```

**Impact**: Immediately fixes Turn 1 — the Coach would see all 7 requirements and approve.
**Effort**: Trivial (2 lines)
**Risk**: Very low

### Priority 2 (CRITICAL): Fix Coach Text Matching to Check Both Field Names

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: `_validate_requirements` text matching path (~line 1578)
**Change**: Check `requirements_addressed` with `requirements_met` fallback (matching the hybrid path pattern):

```python
# Replace line 1578:
# requirements_met = task_work_results.get("requirements_met", [])
# With:
requirements_met = task_work_results.get(
    "requirements_addressed",
    task_work_results.get("requirements_met", []),
)
```

**Impact**: Ensures Coach can read Player data regardless of which field name is used.
**Effort**: Trivial (1 line change)
**Risk**: Very low (matches existing hybrid fallback pattern)

### Priority 3: Fix `_synthetic` Flag Propagation

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: `_write_player_report_for_direct_mode` method (~line 2937)
**Change**: Add `_synthetic` propagation:

```python
# After completion_promises block (line 2937):
if player_report.get("_synthetic"):
    report["_synthetic"] = True
```

**Impact**: Enables synthetic fast-path for turns where SDK doesn't produce a report.
**Effort**: Trivial (2 lines)
**Risk**: Very low

### Priority 4: Fix Synthetic Report Acceptance Criteria Loading

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: `_create_synthetic_direct_mode_report` call site (~line 2662-2670)
**Change**: Use `TaskLoader.load_task()` (full spec parser) instead of `_load_task_metadata()` (YAML-only):

```python
# Replace:
# metadata = self._load_task_metadata(task_file)
# acceptance_criteria = metadata.get("acceptance_criteria")
# With:
from guardkit.orchestrator.autobuild import TaskLoader
task_data = TaskLoader.load_task(task_id, repo_root=self.worktree_path)
acceptance_criteria = task_data.get("acceptance_criteria")
task_type_meta = task_data.get("frontmatter", {}).get("task_type")
```

**Impact**: Enables file-existence promise generation for synthetic reports.
**Effort**: Low
**Risk**: Low (uses existing proven parser)

### Priority 5: Filter Internal Files from Git Detection

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: `_create_synthetic_direct_mode_report` / `_detect_git_changes`
**Change**: Exclude `.guardkit/` and `__pycache__/` paths from git change detection:

```python
files_created = [f for f in files_created
    if not f.startswith(".guardkit/") and "__pycache__" not in f]
files_modified = [f for f in files_modified
    if not f.startswith(".guardkit/") and "__pycache__" not in f]
```

**Impact**: Prevents synthetic reports from falsely reporting internal state changes as Player work. Turn 2's git detection would correctly show 0 changes (indicating no real Player work was done).
**Effort**: Trivial
**Risk**: Very low

### Priority 6: Add Coach-Side Codebase Verification Fallback (Design)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Change**: When BOTH `requirements_met` and `completion_promises` are empty but the task has file changes, attempt basic codebase verification:
- For criteria mentioning class/field names: grep modified files
- For criteria mentioning file updates: check if file was modified
- For criteria mentioning dependencies: check requirements files

**Impact**: Last-resort fallback for when Player reports are incomplete.
**Effort**: Medium
**Risk**: Medium

## Decision Matrix (Revised)

| # | Fix | Impact | Effort | Risk |
|---|-----|--------|--------|------|
| P1 | Copy `requirements_addressed` to `task_work_results.json` | **Critical** — Fixes Turn 1 | Trivial (2 lines) | Very Low |
| P2 | Coach text matching: check both field names | **Critical** — Enables matching | Trivial (1 line) | Very Low |
| P3 | Propagate `_synthetic` flag | High — Fixes synthetic path | Trivial (2 lines) | Very Low |
| P4 | Use full spec parser for synthetic report AC loading | High — Enables promises | Low | Low |
| P5 | Filter internal files from git detection | Medium — Cleaner reports | Trivial | Very Low |
| P6 | Codebase verification fallback | High — Defense in depth | Medium | Medium |

**P1 + P2 alone would have prevented this stall.** The Turn 1 Player did everything right (7/7 requirements addressed, 37 tests passing) — the Coach would have approved immediately.

## Revised Answers to Review Questions

1. **Root Cause**: The Coach verifies 0/7 because of TWO interacting bugs: `_write_direct_mode_results` drops `requirements_addressed`, AND the Coach text matching reads the wrong field name (`requirements_met` vs `requirements_addressed`). The Player DID correctly report all 7 criteria on Turn 1.

2. **Synthetic Reports**: Turns 2-3 synthetic reports are additionally broken by: (a) `_synthetic` flag dropped by `_write_player_report_for_direct_mode`, (b) acceptance criteria not loadable from YAML-only frontmatter parser. Both prevent file-existence promise generation.

3. **Text Matching**: The text matching algorithm is well-implemented but reads the wrong field. It checks `requirements_met` but the Player writes `requirements_addressed`. The hybrid fallback correctly checks both names but is only reached via the promises path.

4. **vLLM Backend**: **Exonerated.** The vLLM Player performed correctly on Turn 1 — all files created/modified correctly, all requirements addressed, 37 tests passing. The failure is in the data pipeline, not the model. The Player did not produce `completion_promises` (preferred format) but DID produce `requirements_addressed` (fallback format), which should have been sufficient.

5. **Task Type**: `scaffolding` classification is a minor concern. The real issue is the data pipeline bugs. With P1+P2 fixed, task type doesn't affect the outcome.

6. **Remediation**: P1 (copy requirements_addressed to task_work_results) + P2 (fix Coach field name) are the critical fixes. Both are trivial 1-2 line changes. P3-P4 fix the synthetic report path for subsequent resilience.

## Appendix: Artifact Evidence

### player_turn_1.json (Turn 1 — Player's actual output)
```json
{
  "task_id": "TASK-LOG-001",
  "turn": 1,
  "files_modified": ["src/core/config.py", ".env.example", "requirements/base.txt"],
  "files_created": ["tests/test_config.py"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "7 new tests added. All 37 tests pass.",
  "requirements_addressed": [
    "Settings class has log_level field with default INFO",
    "Settings class has log_format field with default json",
    "log_level is configurable via LOG_LEVEL environment variable",
    "log_format is configurable via LOG_FORMAT environment variable",
    ".env.example updated with new variables",
    "structlog added to requirements/base.txt",
    "Existing tests still pass"
  ],
  "requirements_remaining": []
}
```

### task_work_results.json (What the Coach reads — missing requirements data)
```json
{
  "task_id": "TASK-LOG-001",
  "completed": true,
  "success": true,
  "quality_gates": {"tests_passing": null, "all_passed": true},
  "files_modified": ["..."],
  "files_created": ["..."],
  "summary": "Direct mode implementation completed successfully"
}
```

### coach_turn_1.json (Coach's incorrect verdict)
```json
{
  "decision": "feedback",
  "criteria_verification": [
    {"criterion_id": "AC-001", "result": "rejected", "evidence": "Not found in Player requirements_met"},
    {"criterion_id": "AC-002", "result": "rejected", "evidence": "Not found in Player requirements_met"},
    // ... all 7 rejected ...
  ]
}
```
