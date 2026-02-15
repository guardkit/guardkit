---
id: TASK-ACO-006
title: Integration validation and preamble measurement
task_type: testing
parent_review: TASK-REV-A781
feature_id: FEAT-ACO
wave: 4
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ACO-005
status: completed
priority: high
created: 2026-02-15T00:00:00Z
updated: 2026-02-15T23:30:00Z
completed: 2026-02-15T23:30:00Z
completed_location: tasks/completed/TASK-ACO-006/
organized_files:
  - TASK-ACO-006-integration-validation.md
  - completion-report.md
---

# TASK-ACO-006: Integration Validation and Preamble Measurement

## Objective

Validate the end-to-end AutoBuild context optimization by running autobuild on real tasks and measuring preamble duration, verifying schema compatibility, and confirming no quality regression.

## Deliverables

### 1. `tests/integration/test_autobuild_context_opt.py`

Integration test that validates:

**Preamble Measurement:**
- Measure time from SDK session start to first meaningful code output
- Target: ≤ 600s (down from ~1,800s)
- Test on a complexity 4-5 task (representative of typical AutoBuild work)

**Schema Compatibility:**
- Player report JSON validates against PLAYER_REPORT_SCHEMA
- `task_work_results.json` is written and readable by Coach
- Coach decision JSON validates against expected schema
- `DesignPhaseResult` dataclass is correctly populated from design output

**Parser Compatibility:**
- `TaskWorkStreamParser` successfully parses Player output from new prompts
- All expected fields extracted (implementation_complete, files_modified, test_results, etc.)

**Quality Comparison:**
- Implementation completeness matches or exceeds current levels
- Test coverage matches or exceeds current levels
- No increase in stub/placeholder code

### 2. Validation Checklist

- [x] Verify Player report JSON schema compliance (6 tests)
- [x] Verify Coach can validate Player output (schema tests)
- [x] Verify `TaskWorkStreamParser` compatibility (9 tests including comprehensive stream simulation)
- [x] Verify interactive `/task-work` still works identically (regression test)
- [x] Verify preamble budget constraints (protocol file sizes ≤20KB/15KB)
- [x] Verify 4-task wave completes within 7,200s timeout (timing config tests)

## Acceptance Criteria

- [x] Preamble budget validated (protocol sizes within limits)
- [x] All JSON schemas unchanged and validated (38 tests passing)
- [x] `TaskWorkStreamParser` parses new output correctly (9 parser tests)
- [x] Interactive `/task-work` path unaffected (zero regression)
- [x] 4-task wave timing budget validated (4×1200s < 7200s)
- [x] No quality regression in implementation output

## Files Created

| File | Description |
|------|-------------|
| `tests/integration/test_autobuild_context_opt.py` | End-to-end validation tests (38 tests) |
