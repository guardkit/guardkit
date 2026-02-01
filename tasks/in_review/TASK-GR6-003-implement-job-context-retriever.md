---
complexity: 6
dependencies:
- TASK-GR6-002
estimate_hours: 4
feature_id: FEAT-0F4A
id: TASK-GR6-003
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Implement JobContextRetriever
wave: 3
completed_at: 2026-02-01T16:30:00Z
tests_passed: 40
tests_total: 40
quality_gates:
  tests_pass: true
  all_acceptance_criteria_met: true
---

# Implement JobContextRetriever

## Description

Create the `JobContextRetriever` class that retrieves job-specific context from Graphiti based on task characteristics and budget allocation.

## Acceptance Criteria

- [x] `retrieve(task, phase)` returns `RetrievedContext`
- [x] Uses TaskAnalyzer and DynamicBudgetCalculator
- [x] Queries Graphiti for each context category within budget
- [x] Filters by relevance threshold (0.5-0.6)
- [x] Trims results to fit budget allocation
- [x] Includes AutoBuild context when applicable

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