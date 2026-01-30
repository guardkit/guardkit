---
id: TASK-GR6-001
title: Implement TaskAnalyzer
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies: []
---

# Implement TaskAnalyzer

## Description

Create the `TaskAnalyzer` class that analyzes task characteristics to inform context retrieval decisions, including AutoBuild-specific characteristics.

## Acceptance Criteria

- [ ] `analyze(task, phase)` returns `TaskCharacteristics`
- [ ] Classifies task type (IMPLEMENTATION, REVIEW, PLANNING, etc.)
- [ ] Determines complexity, novelty, refinement status
- [ ] Queries historical performance (avg_turns, success_rate)
- [ ] Includes AutoBuild fields: current_actor, turn_number, is_autobuild

## Technical Details

**Location**: `guardkit/knowledge/task_analyzer.py`

**TaskCharacteristics Fields**:
- Basic: task_id, description, tech_stack
- Classification: task_type, current_phase, complexity
- Novelty: is_first_of_type, similar_task_count
- Context: feature_id, is_refinement, refinement_attempt
- Performance: avg_turns_for_type, success_rate_for_type
- AutoBuild: current_actor, turn_number, is_autobuild, has_previous_turns

**Reference**: See FEAT-GR-006-job-specific-context.md TaskAnalyzer section.
