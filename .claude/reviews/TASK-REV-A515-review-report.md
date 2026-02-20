# Review Report: TASK-REV-A515

## Executive Summary

The RequireKit v2 Refinement Commands autobuild (FEAT-498F) succeeded with 14/14 tasks completed across 4 waves in 24m 6s — a significant improvement over the previous failure analysed in TASK-REV-F248. However, analysis reveals **three bugs** requiring code fixes, **one design issue**, **one UI clarity issue**, and **one informational warning** that needs a configuration fix in the target repo.

The 14/14 tasks completing in 1 turn each (100% clean execution rate) in 24 minutes across 4 waves is genuinely impressive throughput. The bugs identified are in the **observability and constraint enforcement layers**, not in the actual implementation pipeline.

**Severity breakdown:**
- **P1 (Bug):** File detection parsing produces spurious entries ('house', '**') — Fix in `TaskWorkStreamParser`
- **P1 (Bug):** Shared worktree inflates git-detected file counts — Fix `_detect_git_changes` baseline
- **P2 (Bug):** Documentation constraint validated before invalid-path filtering — Fix pipeline ordering
- **P3 (Design):** `player_turn_N.json` counted as user file in documentation constraints — Exclude internal artifacts
- **P3 (UI):** Contradictory test status display when `tests_required=False` — Clarify output
- **P4 (Config):** Graphiti project_id warning — RequireKit repo config fix (not a GuardKit issue)

**Revision note:** This report incorporates second-opinion feedback confirming all original findings and adding Finding 9 (contradictory test status display).

---

## Finding 1: File Detection Anomalies ('house' and '**')

**Severity:** P1 — Bug
**Status:** Confirmed by second opinion
**Location:** [agent_invoker.py:153-504](guardkit/orchestrator/agent_invoker.py#L153-L504) (`TaskWorkStreamParser`)

### Evidence

TASK-RK01-011 reports `'house'` as a created file:
```
WARNING: [TASK-RK01-011] Documentation level constraint violated: created 3 files, max allowed 2.
Files: ['...player_turn_1.json', '...docs/commands/sync.md', 'house']
```

TASK-RK01-012 reports `'**'` as a created file:
```
WARNING: [TASK-RK01-012] Documentation level constraint violated: created 4 files, max allowed 2.
Files: ['**', '...player_turn_1.json', '...docs/core-concepts/hierarchy.md', '...tests/test_hierarchy_docs_update.py']
```

### Root Cause

The `TaskWorkStreamParser` uses multiple regex patterns to extract file paths from SDK stream output:

1. **`FILES_CREATED_PATTERN`** (`(?:Created|Added):\s*([^\s,]+)`) — This pattern matches any word after "Created:" or "Added:". If the SDK output contains text like `"Created a **warehouse**"` or `"Added to the house"`, partial words get captured as file paths.

2. **`TOOL_RESULT_CREATED_PATTERN`** (`File\s+(?:created|written)\s+(?:successfully\s+)?(?:at|to)[:\s]+([^\s]+)`) — Similar issue with loose matching.

3. The `_is_valid_path` filter in `_create_player_report_from_task_work` only filters `*`-prefixed strings, so `'house'` passes through. And the filter runs **after** `_write_task_work_results`, so `'**'` still appears in the documentation constraint warning.

### Recommendation

**R1a.** Add path validation to `TaskWorkStreamParser` that checks for `/` or `.` characters, or matches against known directory prefixes. Apply at the point of entry (`_files_created.add()`).

**R1b.** Apply the same filter in `_write_task_work_results` BEFORE the documentation constraint check, not just in `_create_player_report_from_task_work` AFTER it.

**R1c.** Tighten `FILES_CREATED_PATTERN` to require path-like strings (contain `/` or `.`).

**Note:** Findings 1, 2, and 3 are related — the parser produces garbage entries, those entries inflate the count, and the constraint check fires on the inflated count before filtering. Fixing Finding 1 (parser regex) and Finding 3 (validation ordering) would eliminate the false constraint violations, while Finding 2 (shared worktree) is a separate architectural issue.

---

## Finding 2: Shared Worktree Inflates Git-Detected File Counts

**Severity:** P1 — Bug (most impactful)
**Status:** Confirmed by second opinion
**Location:** [agent_invoker.py:1727-1769](guardkit/orchestrator/agent_invoker.py#L1727-L1769) (`_detect_git_changes`)

### Evidence

TASK-RK01-012 (documentation task) reports `24 files created, 66 modified`. But git detection added `64 modified, 20 created files`. The task itself only used 87 messages (50 assistant, 35 tools) — far fewer than would be needed to create/modify 90 files.

The smoking gun: a documentation task updating hierarchy concepts should touch maybe 2-3 files. But because `_detect_git_changes` runs `git diff` against the shared worktree, it picks up every change from every previously completed task (003-011 all completed before 012). The file counts are **cumulative across the whole feature**, not scoped to the individual task.

### Root Cause

All 14 tasks share a single worktree at `.guardkit/worktrees/FEAT-498F`. The `_detect_git_changes()` method runs:
- `git diff --name-only HEAD` — shows ALL modifications since the last commit
- `git ls-files --others --exclude-standard` — shows ALL untracked files

Since tasks in the same wave run in parallel and no intermediate commits are made between tasks, **later-completing tasks inherit the cumulative file changes of all earlier-completing tasks**. This means all per-task file metrics in the Player reports for later tasks are unreliable.

### Impact

- Documentation constraint warnings are triggered with inflated counts
- Coach validation uses inflated file counts for task type classification
- Review reports show misleading file modification volumes
- **Any automated scope-creep detection built on these numbers would produce false positives for every task after Wave 1**

### Recommendation

**R2a.** Snapshot the git state (diff output + untracked file list) at the START of each task invocation, then compute the per-task delta at the END. This scopes git detection to only the files changed by the current task.

**R2b.** Alternative (simpler): rely exclusively on `TaskWorkStreamParser` tool-call tracking (Write/Edit ToolUseBlock detection) for per-task file attribution. Use git detection only as a supplementary cross-check. Mark git-only files with a flag so they aren't counted in documentation constraints or scope-creep detection.

---

## Finding 3: Documentation Constraint Validated Before Invalid-Path Filtering

**Severity:** P2 — Bug
**Status:** Confirmed by second opinion
**Location:** [agent_invoker.py:4115-4120](guardkit/orchestrator/agent_invoker.py#L4115-L4120) vs [agent_invoker.py:1556-1573](guardkit/orchestrator/agent_invoker.py#L1556-L1573)

### Evidence

The `_validate_file_count_constraint()` call happens inside `_write_task_work_results()` at line 4116, using the raw `results["files_created"]` list. The `_is_valid_path` filter only runs later in `_create_player_report_from_task_work()` at line 1558-1572.

This means:
1. `_write_task_work_results` writes `task_work_results.json` with invalid entries ('house', '**')
2. `_validate_file_count_constraint` fires the warning using the unfiltered list
3. Only later does `_create_player_report_from_task_work` filter them out

**Second opinion confirms:** If the invalid path filter ran first, TASK-RK01-011 would show 2 valid files (the .json and the .md), which would exactly hit the limit rather than exceeding it. The ordering matters — filter first, then validate.

### Recommendation

**R3.** Move the `_is_valid_path` filter into `_write_task_work_results` BEFORE the constraint validation, or add filtering inside `_validate_file_count_constraint` itself. The filtering should also exclude `player_turn_N.json` (internal artifacts, not user-authored files).

---

## Finding 4: Internal Artifacts Counted in Documentation Constraints

**Severity:** P3 — Design
**Status:** Confirmed with sharpened diagnosis from second opinion
**Location:** [agent_invoker.py:138-142](guardkit/orchestrator/agent_invoker.py#L138-L142) (`DOCUMENTATION_LEVEL_MAX_FILES`)

### Evidence

7 out of 12 non-skipped tasks triggered the documentation constraint warning. The pattern is consistent:

| Task | Files in Warning | Actual User Files |
|------|-----------------|-------------------|
| TASK-RK01-004 | `player_turn_1.json`, `epic-refine.md`, `test_epic_refine.py` | 2 (command + test) |
| TASK-RK01-005 | `player_turn_1.json`, `feature-refine.md`, `test_feature_refine.py` | 2 (command + test) |
| TASK-RK01-006 | `player_turn_1.json`, `requirekit-sync.md`, `test_requirekit_sync.py` | 2 (command + test) |
| TASK-RK01-011 | `player_turn_1.json`, `sync.md`, `'house'` | 1 (command only) |
| TASK-RK01-012 | `'**'`, `player_turn_1.json`, `hierarchy.md`, `test_hierarchy.py` | 2 (docs + test) |
| TASK-RK01-013 | `player_turn_1.json`, `conftest.py`, `test_integration.py` | 2 (setup + test) |
| TASK-RK01-014 | `player_turn_1.json`, `conftest.py`, `test_command_pipelines.py` | 2 (setup + test) |

### Root Cause (Sharpened)

The real issue is that **`player_turn_1.json` is an AutoBuild internal artifact being counted as a user-created file**. Every task-work delegation creates this file as part of the reporting pipeline, so it always consumes one of the 2-file budget. This means any task that produces even 2 actual files (implementation + test) will trigger the warning.

### Recommendation

**R4a.** (Primary fix) Exclude `.guardkit/autobuild/*/player_turn_*.json` from the documentation constraint count. This is a pipeline artifact, not a user-authored file:
```python
def _validate_file_count_constraint(self, task_id, documentation_level, files_created):
    user_files = [
        f for f in files_created
        if "/.guardkit/autobuild/" not in f
        and not f.endswith("player_turn_1.json")
    ]
    # Validate against filtered count
```

**R4b.** Consider per-task-type limits rather than a universal limit, since command-creation tasks naturally produce 2+ files (spec + test).

**R4c.** Consider making test files exempt from the documentation constraint — they are quality artefacts, not scope creep.

**Note:** Raising the limit from 2 to 3+ would weaken the constraint for all task types. Excluding internal artifacts is the more precise fix.

---

## Finding 5: Quality Gate Profile Mapping Assessment

**Severity:** Informational
**Status:** Confirmed by second opinion

### Analysis

| Task | Task Type | Profile | `tests_required` | Created Tests? |
|------|-----------|---------|-------------------|---------------|
| TASK-RK01-003 | scaffolding | scaffolding | False | Yes (3 tests) |
| TASK-RK01-004 | feature | feature | True | Yes |
| TASK-RK01-005 | feature | feature | True | Yes |
| TASK-RK01-006 | feature | feature | True | Yes |
| TASK-RK01-007 | feature | feature | True | Yes |
| TASK-RK01-008 | feature | feature | True | Yes |
| TASK-RK01-009 | documentation | documentation | False | No |
| TASK-RK01-010 | documentation | documentation | False | No |
| TASK-RK01-011 | documentation | documentation | False | No |
| TASK-RK01-012 | documentation | documentation | False | Yes (1 test) |
| TASK-RK01-013 | testing | testing | False | Yes |
| TASK-RK01-014 | testing | testing | False | Yes |

### Assessment

The profile mapping is **largely correct**:
- Feature tasks (004-008) correctly use full quality gates with `tests_required=True`
- Documentation tasks (009-011) correctly skip test requirements
- Testing tasks (013-014) have `tests_required=False` which is correct — these tasks ARE the tests

**Enhancement opportunity:** The `testing` profile has `tests_required=False`, meaning tasks whose purpose is to write tests don't have those tests independently verified. The Coach could execute the newly written tests to verify they actually pass — catching import errors, syntax issues, or missing fixtures.

### Recommendation

**R5.** Add independent test execution for `testing` type tasks. The Coach should run the tests that the Player just wrote to confirm they pass. This catches test files with import errors or syntax issues without introducing circularity.

---

## Finding 6: TASK-RK01-003 Stall Resolution Confirmed

**Severity:** Resolved
**Status:** Confirmed by second opinion

### Comparison with TASK-REV-F248

| Attribute | Previous Run (Failed) | Current Run (Success) |
|-----------|----------------------|----------------------|
| Mode | Direct | Direct |
| Turns | 3 (UNRECOVERABLE_STALL) | 1 (APPROVED) |
| Files created | Turn 1: 22, Turn 2: 5, Turn 3: 1 | 22 |
| Files modified | 0 → 0 → 0 | 1 |
| Criteria met | 0/4 all turns | 4/4 |
| Player report | Synthetic (no `requirements_met`) | Synthetic + git detection |
| Coach outcome | 3x feedback hash 7fb95478 | Approved |

### Resolution Evidence

The fix from TASK-REV-F248 analysis resolved the stall:
1. **Synthetic report now includes file-existence promises** (via `build_synthetic_report`)
2. **Git detection added** to direct mode path
3. **Criteria verification succeeded**: 4/4 verified
4. **Single turn completion** instead of 3-turn stall

The direct mode stall is **fully resolved**.

---

## Finding 7: Graphiti Configuration Warning

**Severity:** P4 — Configuration (Not a GuardKit bug)
**Status:** Confirmed by second opinion

### Evidence

After every task completion (14 occurrences):
```
WARNING: No explicit project_id in config, auto-detected 'require-kit' from cwd.
Set project_id in .guardkit/graphiti.yaml for consistent behavior.
```

### Recommendation

**R7.** No GuardKit change needed. Add `project_id: require-kit` to the require-kit repo's `.guardkit/graphiti.yaml` config file.

---

## Finding 8: TASK-RK01-012 Scope Assessment

**Severity:** P1 (related to Finding 2)
**Status:** Strongly confirmed by second opinion

### Assessment

The reported `24 files created, 66 modified` for a documentation task is **not actual scope creep** — it's an artefact of Finding 2 (shared worktree git detection). The task itself used 87 messages (50 assistant, 35 tools) — consistent with a moderate documentation update, not a 90-file rewrite.

The git detection log confirms: `Git detection added: 64 modified, 20 created files` — meaning the stream parser only tracked ~4 created and ~2 modified files from actual tool calls. The remaining 84 files were inherited from other tasks in the shared worktree.

**Conclusion:** No scope creep occurred. The inflated count is a direct consequence of Finding 2.

---

## Finding 9: Contradictory Test Status Display

**Severity:** P3 — UI Clarity
**Status:** Added from second-opinion feedback (new finding)

### Evidence

TASK-RK01-011 shows `0 tests (failing)` in the Player summary yet was approved by the Coach because the documentation quality gate profile has `tests_required=False`.

### Root Cause

The Player summary reports test status literally (0 tests = failing), while the Coach correctly evaluates the gate requirement (tests not required for documentation tasks). The result is a UI output that shows a "failing" task being approved — cosmetically confusing even though logically correct.

### Impact

- Appears as if the Coach "rubber-stamped" a failing task
- Log review requires understanding quality gate profiles to interpret correctly
- Could cause false alarm during manual log review or audits

### Recommendation

**R9.** When `tests_required=False` for a task type, the Player summary should display `0 tests (not required)` instead of `0 tests (failing)`. Alternatively, the Coach approval log line should include the reason: `Coach approved - tests not required for documentation tasks`.

---

## Recommendations Summary

| ID | Priority | Finding | Recommendation | Effort |
|----|----------|---------|----------------|--------|
| R1 | P1 | File path parsing bugs | Add path validation to parser + tighten regex | Small |
| R2 | P1 | Shared worktree inflation | Baseline snapshot or tool-call-only attribution | Medium |
| R3 | P2 | Filter/validate ordering | Move filtering before constraint check | Small |
| R4 | P3 | Internal artifact counting | Exclude `.guardkit/autobuild/*` from constraint count | Small |
| R5 | P3 | Testing profile gap | Add test execution for `testing` task type | Small |
| R9 | P3 | Contradictory test display | Show "not required" instead of "failing" when `tests_required=False` | Small |
| R7 | P4 | Graphiti warning | Fix require-kit repo config | Trivial |

### Suggested Implementation Order

1. **R1 + R3** (small, fixes noisy false-positive warnings immediately)
2. **R4** (small, eliminates 7/12 documentation constraint violations)
3. **R9** (small, clarifies log output)
4. **R2** (medium, fixes the fundamental attribution problem)
5. **R5** (small, improves quality gate coverage)
6. **R7** (trivial, target repo fix)

---

## Review Details

- **Mode**: Diagnostic
- **Depth**: Deep
- **Duration**: Full analysis of autobuild log, source code, and prior review
- **Revision**: Incorporated second-opinion feedback confirming all findings + added Finding 9
- **Files Analysed**:
  - `docs/reviews/autobuild-fixes/requirekit_feature_success.md` (success log)
  - `tasks/backlog/TASK-REV-F248-*.md` (prior failure analysis)
  - `guardkit/orchestrator/agent_invoker.py` (file detection, constraint validation)
  - `guardkit/models/task_types.py` (quality gate profiles)
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (Coach validation)

---

## Acceptance Criteria Status

- [x] Documentation level constraint violations analysed with recommendation (Findings 4, 3)
- [x] File detection anomalies ('house', '**') root-caused (Finding 1)
- [x] TASK-RK01-012 excessive modifications evaluated for scope creep (Finding 8 — no scope creep, git detection bug)
- [x] Quality gate profile mapping reviewed for correctness (Finding 5)
- [x] TASK-RK01-003 stall resolution confirmed (Finding 6 — fully resolved)
- [x] Actionable recommendations for GuardKit improvements provided (R1-R9)
