---
completed_at: 2025-02-01 12:00:00+00:00
complexity: 5
dependencies:
- TASK-GR6-003
- TASK-GR5-007
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR6-009
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Add turn_states retrieval for cross-turn learning
wave: 3
---

# Add turn_states retrieval for cross-turn learning

## Description

Add retrieval and formatting for turn_states context to enable cross-turn learning in feature-build workflows. This is the key feature addressing TASK-REV-7549 finding.

## Acceptance Criteria

- [x] Queries `turn_states` group for feature_id + task_id
- [x] Returns last 5 turns sorted by turn_number
- [x] Formats turn summary with decision and progress
- [x] Emphasizes REJECTED feedback (must address)
- [x] Increased allocation for later turns (15-20%)

## Technical Details

**Group ID**: `turn_states`

**Query**: `turn {feature_id} {task_id}`

**Output Format**:
```
### Previous Turn Context
*Learn from previous turns - don't repeat mistakes*

**Turn 1**: FEEDBACK
  Progress: Initial implementation incomplete

**Turn 2**: REJECTED
  Progress: Tests failing, coverage at 65%
  ⚠️ Feedback: "Coverage must be >=80%. Missing tests for error paths."
```

**Reference**: See FEAT-GR-006 turn_states retrieval section.

## Implementation Summary

### Files Implemented/Modified

1. **guardkit/knowledge/job_context_retriever.py**
   - `_query_turn_states()`: Queries turn_states group with correct format
   - `_format_turn_states()`: Formats results with decision, progress, REJECTED emphasis
   - Integration in `RetrievedContext.to_prompt()` method

2. **guardkit/knowledge/budget_calculator.py**
   - `_adjust_autobuild_allocation()`: 15-20% allocation for turn_states on later turns
   - `turn_states` field in `ContextBudget` dataclass

3. **guardkit/knowledge/turn_state_operations.py**
   - `load_turn_context()`: Cross-turn learning function
   - Sorting by turn_number ascending
   - Last 5 turns limit

4. **tests/knowledge/test_turn_states_retrieval.py** (18 tests)
5. **tests/knowledge/test_turn_state.py** (66 tests)

### Test Coverage

- **84 tests total** (18 + 66)
- All tests passing ✅
- Coverage target: ≥85% for turn states retrieval code

### Key Implementation Details

- Query format: `"turn {feature_id} {task_id}"` to turn_states group
- `num_results=5` to limit to last 5 turns
- Sorting by `turn_number` ascending ensures chronological order
- REJECTED turns get ⚠️ warning emoji emphasis with "MUST ADDRESS" label
- Budget allocation: 17.5% pre-normalization yields 15-20% post-normalization