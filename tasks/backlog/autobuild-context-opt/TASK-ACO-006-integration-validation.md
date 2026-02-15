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
status: pending
priority: high
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

Run through manually:

- [ ] Run autobuild on a complexity 4-5 task with new prompts
- [ ] Verify preamble ≤ 600s
- [ ] Verify Player report JSON schema compliance
- [ ] Verify Coach can validate Player output
- [ ] Verify `TaskWorkStreamParser` compatibility
- [ ] Verify interactive `/task-work` still works identically
- [ ] Compare quality of output (implementation completeness, test coverage)
- [ ] Verify 4-task wave completes within 7,200s total timeout

## Acceptance Criteria

- [ ] Preamble ≤ 600s (measured on real task)
- [ ] All JSON schemas unchanged and validated
- [ ] `TaskWorkStreamParser` parses new output correctly
- [ ] Interactive `/task-work` path unaffected (zero regression)
- [ ] 4-task wave (Wave 2 scenario) completes within 7,200s timeout
- [ ] No quality regression in implementation output

## Success Metrics (from spec)

1. **Preamble reduction**: ≤ 600s (down from ~1,800s)
2. **No quality regression**: Player report quality and test coverage match current
3. **Schema compatibility**: All existing JSON schemas unchanged
4. **Interactive preservation**: `/task-work` in interactive sessions works identically
5. **Wave 2 viability**: 4-task wave completes within 7,200s total timeout

## Files Created

| File | Description |
|------|-------------|
| `tests/integration/test_autobuild_context_opt.py` | End-to-end validation tests |
