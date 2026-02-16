---
id: TASK-REV-8976
title: Review feature-plan filename inconsistency
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T00:00:00Z
priority: high
tags: [feature-plan, autobuild, filename-mismatch, bug-analysis]
complexity: 0
review_results:
  findings_count: 4
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-8976-review-report.md
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-16
---

# Task: Review feature-plan filename inconsistency

## Description

Analyse the issue documented in `docs/reviews/autobuild-fixes/wrong_task_filenames.md` where the `/feature-plan` command generates feature YAML files (`FEAT-*.yaml`) with task `file_path` entries that don't match the actual filenames of the task markdown files created on disk.

### Observed Problem

When `/feature-plan` created a FastAPI health app feature (FEAT-F97F), the YAML referenced:
- `TASK-HLTH-003-set-up-testing-infrastructure-and-health-tests.md`
- `TASK-HLTH-004-add-dev-tooling-configuration.md`

But the actual files created on disk were:
- `TASK-HLTH-003-setup-testing-infrastructure.md`
- `TASK-HLTH-004-add-dev-tooling-config.md`

This caused `feature-build` / autobuild to fail validation with "Task file not found" errors.

### Root Cause Hypothesis

The feature YAML generation and the task file creation use different slugification logic:
1. The YAML `file_path` field is generated from the task **name** (long form)
2. The actual filename is generated from a **shorter/abbreviated** version of the task name

This suggests the slug is being computed twice independently - once when writing the YAML and once when creating the file - with different inputs or different slugification rules.

### Related Existing Tasks

Two related fix tasks already exist in `tasks/backlog/`:
- `fix-feature-plan-file-path/` (FEAT-FP-FIX) - Addresses `file_path: .` issue when `--feature-slug` is omitted
- `fix-feature-plan-paths/` (FEAT-FPP) - Addresses duplicated directory segments and filename mismatches

This review should determine whether the existing fix tasks adequately address this specific inconsistency or if additional work is needed.

## Review Objectives

1. **Trace the code paths**: Identify exactly where the YAML `file_path` and the actual filename are generated
2. **Identify the divergence**: Determine why two different slug values are produced for the same task
3. **Assess existing fixes**: Evaluate whether FEAT-FP-FIX and FEAT-FPP tasks cover this scenario
4. **Recommend solution**: Propose a fix that ensures a single source of truth for task filenames

## Acceptance Criteria

- [x] Root cause of filename divergence is identified with specific code locations
- [x] The two slugification code paths are documented
- [x] Assessment of whether existing fix tasks (FEAT-FP-FIX, FEAT-FPP) cover this issue
- [x] Recommended fix approach with specific files to change
- [x] Risk assessment for the proposed fix

## Key Files to Investigate

- `installer/core/commands/feature-plan.md` - Feature plan command spec
- `installer/core/commands/lib/generate_feature_yaml.py` - YAML generation logic (if exists)
- `guardkit/orchestrator/feature_loader.py` - Feature validation/loading
- `guardkit/orchestrator/feature_orchestrator.py` - Feature orchestration
- Any slug/filename generation utilities

## Reference

- Issue documentation: `docs/reviews/autobuild-fixes/wrong_task_filenames.md`

## Implementation Notes

### Root Cause (Finding 1 - Critical)

The `/feature-plan` command orchestrates two independent, uncoordinated steps:
- **Step 9**: Claude creates task markdown files using the Write tool with **ad-hoc** filename construction
- **Step 10**: `generate-feature-yaml` derives `file_path` using `build_task_file_path()` → `slugify_task_name()` (deterministic Python)

Claude abbreviates ("Set up" → "setup"), drops suffixes ("and health tests"), and shortens words ("configuration" → "config"). These are reasonable for human-readable filenames but break the YAML-to-disk path contract.

### Prior Fix Assessment (Finding 3)

All 9 prior fix tasks (FEAT-FPP: 5/5, FEAT-FP-FIX: 4/4) are **completed**. They correctly fixed Python-to-Python slug divergence, path doubling, missing validation, and missing `--feature-slug`. The remaining gap was architectural: Claude creates files, Python derives paths.

### Fixes Implemented

1. **R1: `--discover` flag** (Critical) - Added `discover_task_file()` to `generate_feature_yaml.py` that globs for actual task files on disk instead of deriving paths from names. 8 unit tests added.
2. **R2: Updated `feature-plan.md` Step 10** (Critical) - All `generate-feature-yaml` invocations now pass `--discover`.
3. **R3: `--strict` is now the default** (Recommended) - Path validation errors are fatal by default. Added `--lenient` for opt-out. 4 CLI tests added.
4. **R4: Unified `guardkit/cli/task.py`** (Low priority) - Replaced local `_generate_slug()` with import from `slug_utils.py`.

### Files Changed

| File | Change |
|------|--------|
| `installer/core/commands/lib/generate_feature_yaml.py` | Added `discover_task_file()`, `--discover`, `--lenient`, strict-by-default |
| `installer/core/commands/feature-plan.md` | Step 10 updated with `--discover` |
| `guardkit/cli/task.py` | Replaced `_generate_slug()` with `slugify_task_name` import |
| `tests/unit/test_generate_feature_yaml.py` | Added 12 new tests (TestDiscoverTaskFile + TestDiscoverCLI) |
| `.claude/reviews/TASK-REV-8976-review-report.md` | Full review report |

### Test Results

64 tests passing (52 existing + 12 new), 0 failures.

## Test Execution Log

All tests pass: `python -m pytest tests/unit/test_generate_feature_yaml.py -v` → 64 passed
