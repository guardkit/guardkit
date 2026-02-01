---
complexity: 4
dependencies:
- TASK-GR6-003
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR6-008
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Add quality_gate_configs retrieval and formatting
wave: 3
---

# Add quality_gate_configs retrieval and formatting

## Description

Add retrieval and formatting for quality_gate_configs context, addressing TASK-REV-7549 finding on threshold drift.

## Acceptance Criteria

- [x] Queries `quality_gate_configs` group
- [x] Filters by task_type (scaffolding, feature, testing, documentation)
- [x] Formats coverage_threshold, arch_review_threshold, tests_required
- [x] Clear "do NOT adjust" messaging
- [x] Emphasized in AutoBuild contexts

## Technical Details

**Group ID**: `quality_gate_configs`

**Output Format**:
```
### Quality Gate Thresholds
*Use these thresholds - do NOT adjust mid-session*

**scaffolding**:
  - Coverage: not required
  - Arch review: not required
  - Tests required: No

**feature**:
  - Coverage: ≥80%
  - Arch review: ≥60
  - Tests required: Yes
```

**Reference**: See FEAT-GR-006 quality_gate_configs formatting.

## Implementation Summary

### Files Implemented

1. **guardkit/knowledge/quality_gate_formatter.py** (29 statements, 95% coverage)
   - `format_quality_gates()`: Main formatter function for quality gate configs
   - `_format_coverage_threshold()`: Converts float to percentage format
   - `_format_arch_review_threshold()`: Formats arch review threshold
   - `_format_tests_required()`: Converts boolean to Yes/No

2. **guardkit/knowledge/job_context_retriever.py** (updated)
   - Queries `quality_gate_configs` group when `is_autobuild=True`
   - Integrates quality gates into `RetrievedContext` dataclass
   - Uses dedicated formatter in `to_prompt()` method

### Tests

17 tests passing in `tests/knowledge/test_quality_gate_retrieval.py`:
- `TestQualityGateQueries` (3 tests): Verifies Graphiti queries
- `TestQualityGateFormatting` (5 tests): Verifies output formatting
- `TestTaskTypeSpecificGates` (4 tests): Verifies task type filtering
- `TestEdgeCases` (3 tests): Handles None/empty inputs
- `TestQualityGateIntegration` (2 tests): End-to-end verification

### Quality Gates

- ✅ All tests passing (17/17)
- ✅ Coverage: 95% for quality_gate_formatter.py
- ✅ "do NOT adjust" messaging included
- ✅ AutoBuild context emphasis implemented
