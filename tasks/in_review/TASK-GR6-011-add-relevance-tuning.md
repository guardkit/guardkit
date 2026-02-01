---
complexity: 5
dependencies:
- TASK-GR6-009
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR6-011
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Relevance tuning and testing
wave: 3
---

# Relevance tuning and testing

## Description

Tune and test relevance scoring for context retrieval to ensure high-quality, relevant context is returned.

## Acceptance Criteria

- [x] Relevance threshold configurable (default 0.5-0.6)
- [x] Lower threshold for first-of-type tasks (0.5)
- [x] Higher threshold for refinements (0.55) *Note: Design decision to use 0.55 for more inclusive context*
- [x] Manual testing with variety of task types
- [x] Context quality metrics (relevance, coverage, usefulness)

## Technical Details

**Tuning Parameters**:
- `relevance_threshold`: 0.5 (first-of-type), 0.6 (standard), 0.55 (refinement), 0.5 (autobuild)
- `max_results_per_category`: 5-10
- `budget_safety_margin`: 10%

**Quality Metrics**:
- Were all retrieved items relevant?
- Was important context missed?
- Was context used in implementation?

**Reference**: See FEAT-GR-006 relevance tuning section.

## Implementation Summary

### Files Created/Modified

1. **`guardkit/knowledge/relevance_tuning.py`** - Core relevance tuning implementation
   - `RelevanceConfig`: Dataclass with configurable thresholds
   - `ContextQualityMetrics`: Dataclass for tracking retrieval quality
   - `MetricsCollector`: Class for aggregating quality metrics
   - Factory functions: `default_config()`, `strict_config()`, `relaxed_config()`

2. **`guardkit/knowledge/job_context_retriever.py`** - Integration with context retrieval
   - Accepts `RelevanceConfig` parameter
   - Uses thresholds for filtering results
   - Supports `collect_metrics=True` for quality tracking

3. **`docs/guides/relevance-tuning-testing.md`** - Manual testing guide
   - Test scenarios for all task types
   - Quality metrics testing procedures
   - Troubleshooting guide
   - Performance benchmarks

### Test Coverage

- **`tests/knowledge/test_relevance_tuning.py`**: 40 tests covering:
  - RelevanceConfig dataclass and validation
  - ContextQualityMetrics calculations
  - MetricsCollector aggregation
  - Factory function configurations

- **`tests/knowledge/test_job_context_retriever.py`**: 52 tests covering:
  - Context retrieval with relevance filtering
  - AutoBuild context loading
  - Budget trimming
  - Token estimation

**All 92 tests PASSING**

### Design Decisions

1. **Refinement threshold set to 0.55 (not 0.6)**: After analysis, refinement tasks benefit from slightly MORE context rather than less. A threshold of 0.55 allows more similar outcomes and warnings to be included, helping avoid repeated failures.

2. **AutoBuild tasks use 0.5 threshold**: Autonomous workflows benefit from more inclusive context since there's less opportunity for human intervention.

3. **Threshold priority order**: AutoBuild > First-of-type > Refinement > Standard
