---
complexity: 5
dependencies:
- TASK-GR6-005
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR6-006
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Integrate with /feature-build
wave: 3
---

# Integrate with /feature-build

## Description

Integrate the `JobContextRetriever` into the `/feature-build` command with AutoBuild-specific context retrieval.

## Acceptance Criteria

- [x] Context retrieved for each Player turn
- [x] AutoBuild context included (role_constraints, quality_gates, turn_states)
- [x] Refinement attempts get emphasized warnings
- [x] Coach receives appropriate subset of context
- [x] `--verbose` flag shows context retrieval details

## Technical Details

**Integration Points**:
- Player turn start: Full context with role_constraints
- Coach turn start: Quality gate configs, turn states

**AutoBuild Characteristics**:
- `is_autobuild: True`
- `current_actor: "player"` or `"coach"`
- `turn_number: N`
- `has_previous_turns: True` (if N > 1)

**Reference**: See FEAT-GR-006 Integration with /feature-build section.

## Implementation Summary

### Files Implemented

1. **`guardkit/knowledge/autobuild_context_loader.py`** (461 lines)
   - `AutoBuildContextLoader` class - bridges JobContextRetriever with AutoBuildOrchestrator
   - `get_player_context()` - retrieves full context for Player turns with role_constraints
   - `get_coach_context()` - retrieves subset for Coach validation
   - `AutoBuildContextResult` dataclass with prompt_text, budget info, verbose details
   - Graceful degradation when Graphiti unavailable

2. **`guardkit/orchestrator/autobuild.py`** (integration)
   - `_invoke_player_safely()` (lines 1981-2010) - context injection for Player
   - `_invoke_coach_safely()` (lines 2132-2168) - context injection for Coach
   - Dependency injection via constructor for context_loader
   - Verbose mode support for context retrieval details

### Tests

- **Unit Tests**: `tests/unit/test_autobuild_context_integration.py` (14 tests)
- **Integration Tests**: `tests/integration/test_autobuild_context_integration.py` (18 tests)
- **Total**: 32 tests, all passing

### Quality Gates

- **Tests**: 32/32 passing
- **Coverage**: Module-specific coverage included
- **Architectural Pattern**: Dependency Injection for context_loader enables graceful degradation