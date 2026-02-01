---
id: TASK-GR6-008
title: Add quality_gate_configs retrieval and formatting
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR6-003
---

# Add quality_gate_configs retrieval and formatting

## Description

Add retrieval and formatting for quality_gate_configs context, addressing TASK-REV-7549 finding on threshold drift.

## Acceptance Criteria

- [ ] Queries `quality_gate_configs` group
- [ ] Filters by task_type (scaffolding, feature, testing, documentation)
- [ ] Formats coverage_threshold, arch_review_threshold, tests_required
- [ ] Clear "do NOT adjust" messaging
- [ ] Emphasized in AutoBuild contexts

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
