---
complexity: 5
dependencies: []
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR4-001
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-004
task_type: feature
title: Implement KnowledgeGapAnalyzer
wave: 1
completed_at: "2026-02-01T12:00:00Z"
test_results:
  total: 49
  passed: 49
  failed: 0
  skipped: 0
---

# Implement KnowledgeGapAnalyzer

## Description

Create the `KnowledgeGapAnalyzer` class that analyzes existing knowledge in Graphiti to identify gaps and generates targeted questions to fill them.

## Acceptance Criteria

- [x] `analyze_gaps(focus, max_questions)` returns `List[KnowledgeGap]`
- [x] Queries Graphiti for existing knowledge
- [x] Compares against question templates to find gaps
- [x] Supports focus filtering by category
- [x] Sorts by importance (high/medium/low)
- [x] Includes AutoBuild categories (role_customization, quality_gates, workflow_preferences)

## Technical Details

**Location**: `guardkit/knowledge/gap_analyzer.py`

**Knowledge Categories**:
- `project_overview`, `architecture`, `domain`, `constraints`, `decisions`, `goals`
- `role_customization` (NEW - from TASK-REV-1505)
- `quality_gates` (NEW - from TASK-REV-1505)
- `workflow_preferences` (NEW - from TASK-REV-1505)

**Reference**: See FEAT-GR-004-interactive-knowledge-capture.md for question templates.