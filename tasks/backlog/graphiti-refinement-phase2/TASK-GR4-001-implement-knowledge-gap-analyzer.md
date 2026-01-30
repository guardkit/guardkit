---
id: TASK-GR4-001
title: Implement KnowledgeGapAnalyzer
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies: []
---

# Implement KnowledgeGapAnalyzer

## Description

Create the `KnowledgeGapAnalyzer` class that analyzes existing knowledge in Graphiti to identify gaps and generates targeted questions to fill them.

## Acceptance Criteria

- [ ] `analyze_gaps(focus, max_questions)` returns `List[KnowledgeGap]`
- [ ] Queries Graphiti for existing knowledge
- [ ] Compares against question templates to find gaps
- [ ] Supports focus filtering by category
- [ ] Sorts by importance (high/medium/low)
- [ ] Includes AutoBuild categories (role_customization, quality_gates, workflow_preferences)

## Technical Details

**Location**: `guardkit/knowledge/gap_analyzer.py`

**Knowledge Categories**:
- `project_overview`, `architecture`, `domain`, `constraints`, `decisions`, `goals`
- `role_customization` (NEW - from TASK-REV-1505)
- `quality_gates` (NEW - from TASK-REV-1505)
- `workflow_preferences` (NEW - from TASK-REV-1505)

**Reference**: See FEAT-GR-004-interactive-knowledge-capture.md for question templates.
