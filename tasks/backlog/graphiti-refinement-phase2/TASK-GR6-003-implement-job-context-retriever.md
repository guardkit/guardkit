---
id: TASK-GR6-003
title: Implement JobContextRetriever
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: task-work
complexity: 6
estimate_hours: 4
dependencies:
  - TASK-GR6-002
---

# Implement JobContextRetriever

## Description

Create the `JobContextRetriever` class that retrieves job-specific context from Graphiti based on task characteristics and budget allocation.

## Acceptance Criteria

- [ ] `retrieve(task, phase)` returns `RetrievedContext`
- [ ] Uses TaskAnalyzer and DynamicBudgetCalculator
- [ ] Queries Graphiti for each context category within budget
- [ ] Filters by relevance threshold (0.5-0.6)
- [ ] Trims results to fit budget allocation
- [ ] Includes AutoBuild context when applicable

## Technical Details

**Location**: `guardkit/knowledge/job_context_retriever.py`

**Context Categories**:
- feature_context (feature_specs group)
- similar_outcomes (task_outcomes group)
- relevant_patterns (patterns_{stack} group)
- architecture_context (project_architecture group)
- warnings (failure_patterns group)
- domain_knowledge (domain_knowledge group)
- role_constraints (AutoBuild)
- quality_gate_configs (AutoBuild)
- turn_states (AutoBuild)
- implementation_modes (AutoBuild)

**Reference**: See FEAT-GR-006 JobContextRetriever section.
