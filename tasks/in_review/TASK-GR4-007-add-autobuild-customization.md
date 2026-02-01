---
complexity: 4
dependencies:
- TASK-GR4-005
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR4-007
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-004
task_type: feature
title: Add AutoBuild workflow customization questions
wave: 1
completed_at: 2025-02-01T00:00:00Z
tests_passed: 128
tests_total: 128
---

# Add AutoBuild workflow customization questions

## Description

Add interactive capture questions for AutoBuild workflow customization, addressing TASK-REV-7549 findings on role reversal and threshold drift.

## Acceptance Criteria

- [x] Role customization questions (player_ask_before, coach_escalate_when)
- [x] Quality gate questions (coverage_threshold, arch_review_threshold)
- [x] Workflow preference questions (implementation_mode, max_auto_turns)
- [x] Captured to appropriate group_ids
- [x] CLI focus options: `--focus role-customization`, `--focus quality-gates`

## Question Templates

**Role Customization**:
- "What tasks should the AI Player ALWAYS ask about before implementing?"
- "What decisions should the AI Coach escalate to humans?"
- "Are there areas where AI should NEVER make changes autonomously?"

**Quality Gates**:
- "What test coverage threshold is acceptable?" (e.g., "80% for features")
- "What architectural review score should block implementation?"

**Reference**: See FEAT-GR-004 AutoBuild workflow customization section.

## Implementation Verification

### Files Implementing Acceptance Criteria

1. **`guardkit/knowledge/gap_analyzer.py`**:
   - `KnowledgeCategory` enum includes: `ROLE_CUSTOMIZATION`, `QUALITY_GATES`, `WORKFLOW_PREFERENCES`
   - Question templates for role customization (player_ask_before, coach_escalate_when)
   - Question templates for quality gates (coverage_threshold, arch_review_threshold)
   - Question templates for workflow preferences (implementation_mode, max_auto_turns)

2. **`guardkit/knowledge/interactive_capture.py`**:
   - `_CATEGORY_GROUP_MAP` maps categories to appropriate group_ids:
     - `ROLE_CUSTOMIZATION` → `"autobuild_roles"`
     - `QUALITY_GATES` → `"autobuild_quality"`
     - `WORKFLOW_PREFERENCES` → `"autobuild_workflow"`

3. **`guardkit/cli/graphiti.py`**:
   - CLI `--focus` option supports all 9 categories including:
     - `role-customization`
     - `quality-gates`
     - `workflow-preferences`

### Test Results

**128 tests passed** across:
- `tests/knowledge/test_gap_analyzer.py` - KnowledgeCategory, focus filtering
- `tests/knowledge/test_interactive_capture.py` - 60 tests for capture session
- `tests/cli/test_graphiti_capture.py` - CLI capture command tests

### Quality Gates

| Gate | Result | Threshold |
|------|--------|-----------|
| Tests Pass | 128/128 (100%) | 100% |
| Implementation Complete | 5/5 criteria | 100% |
| Compilation | ✓ | 100% |
