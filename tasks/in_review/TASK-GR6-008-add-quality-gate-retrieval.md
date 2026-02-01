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