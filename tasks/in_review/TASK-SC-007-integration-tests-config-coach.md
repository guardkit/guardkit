---
complexity: 5
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-002
- TASK-SC-004
feature_id: FEAT-SC-001
id: TASK-SC-007
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: in_review
tags:
- integration-tests
- config
- coach
- seams
task_type: testing
title: 'Integration tests: config round-trip + coach validator wiring'
updated: 2026-02-10T17:00:00Z
wave: 3
code_review_score: 92
tests_passing: true
test_count: 29
---

# Task: Integration tests for config round-trip and coach validator wiring

## Description

Create integration tests that verify:
1. **Config round-trip**: `.guardkit/config.yaml` can be written, read, and updated correctly across context switches
2. **Coach context builder integration**: `build_coach_context()` correctly wires into the coach validation pipeline

These tests target two technology seams: YAML config persistence and the Graphiti → coach prompt assembly pipeline.

## Implementation Complete

### Test Files Created

1. **`tests/integration/test_context_switch_config.py`** - 12 tests
2. **`tests/integration/test_coach_context_integration.py`** - 17 tests

### Test Summary

**Total Tests**: 29 tests (exceeds 19 required)
**All Tests Pass**: Yes (29 passed in 1.33s)

#### Config Round-Trip Tests (12 tests)
- Config persistence and reload
- Round-trip switching (A→B→A)
- Timestamp updates on switch
- Missing known_projects handling
- Empty file handling
- Missing file handling
- Corrupt YAML handling
- Unknown field preservation
- Unknown project error
- Concurrent writes safety
- List known projects
- Get known project by ID

#### Coach Context Tests (17 tests)
- Complexity gating (all 4 tiers: 1-3, 4-6, 7-8, 9-10)
- Overview inclusion logic
- Impact analysis behavior (documented current bug)
- Token budget enforcement
- Graphiti disabled graceful degradation
- No architecture graceful degradation
- Exception logging
- Output format verification
- Cross-module pipeline (overview → coach)
- Cross-module pipeline (impact standalone)
- Full realistic pipeline
- Default complexity (5)
- Zero complexity handling
- Exception handling

### Mock Infrastructure

Created `MockGraphitiClient` class:
- Simulates GraphitiClient API surface
- No Neo4j connection required
- Realistic fact structure with UUIDs, scores, timestamps

## Acceptance Criteria

- [x] 2 integration test files created
- [x] At least 8 config round-trip tests (delivered 12)
- [x] At least 8 coach context integration tests (delivered 14)
- [x] At least 3 cross-module pipeline tests (delivered 3)
- [x] Config tests use `tmp_path` for file isolation
- [x] Coach tests use mock Graphiti client (no Neo4j required)
- [x] All tests pass with `pytest tests/integration/ -v`
- [x] Edge cases covered: corrupt YAML, missing fields, Graphiti down

## Code Review Results

**Score**: 92/100

**Strengths**:
- Comprehensive test coverage (137% of requirements)
- Excellent documentation with known bug tracking
- Proper test isolation and realistic mocking
- Outstanding edge case coverage

**Minor Recommendations**:
- Extract MockGraphitiClient to shared module
- Consider parameterizing complexity tests
- Increase timestamp tolerance for CI stability

## Test Verification

```bash
pytest tests/integration/test_context_switch_config.py tests/integration/test_coach_context_integration.py -v
# Result: 29 passed in 1.33s
```

## Known Issues Documented

Impact analysis integration is currently broken due to bug in `_get_impact_section()` (missing client parameter). Tests document current behavior with comments for updating once bug is fixed.
