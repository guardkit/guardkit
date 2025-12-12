# Implementation Plan: Add Path Pattern Inference from Analysis

**Task ID**: TASK-CRS-004
**Created**: 2025-12-11
**Complexity**: 5/10

## Overview

Enhance `RulesStructureGenerator` to intelligently infer path patterns from codebase analysis results rather than relying solely on agent name matching.

## Current State

The `RulesStructureGenerator._infer_agent_paths()` method uses simple name-based mapping:
- Maps keywords like 'repository' to hardcoded patterns
- Doesn't leverage `CodebaseAnalysis` data
- Misses custom folder names and project-specific patterns

## Proposed Solution

Create a new `PathPatternInferrer` class that uses `CodebaseAnalysis` to infer patterns intelligently:
1. Extract layer paths from `architecture.layers[].typical_files`
2. Build extension patterns from `technology.primary_language`
3. Use technology-specific patterns from frameworks
4. Fall back to name-based inference when needed

## Implementation Steps

### Step 1: Create PathPatternInferrer Class

**File**: `installer/core/lib/template_generator/path_pattern_inferrer.py`

**Class Structure**:
- `__init__(analysis: CodebaseAnalysis)` - Initialize with analysis data
- `_build_layer_paths()` - Extract directory patterns from layers
- `_build_extension_patterns()` - Build language-specific extensions
- `infer_for_agent(agent_name, agent_technologies)` - Main inference method
- `_matches_layer()` - Match agent to architectural layer
- `_get_technology_pattern()` - Get tech-specific patterns
- `_fallback_inference()` - Name-based fallback

**Key Logic**:
```python
def infer_for_agent(agent_name, agent_technologies):
    patterns = []

    # 1. Layer-based matching (from analysis)
    for layer in layers:
        if matches_layer(agent_name, layer):
            patterns.extend(layer_paths)

    # 2. Technology-based matching
    for tech in agent_technologies:
        if tech_pattern := get_technology_pattern(tech):
            patterns.append(tech_pattern)

    # 3. Fallback to name-based
    if not patterns:
        patterns = fallback_inference(agent_name)

    return deduplicate_and_join(patterns)
```

### Step 2: Integrate with RulesStructureGenerator

**File**: `installer/core/lib/template_generator/rules_structure_generator.py`

**Changes**:
1. Import `PathPatternInferrer`
2. Initialize inferrer in `__init__`
3. Replace `_infer_agent_paths()` call with `self.path_inferrer.infer_for_agent()`
4. Pass agent technologies to inferrer

**Modified Method**:
```python
def _generate_agent_rules(self, agent) -> str:
    # Use inferrer instead of simple mapping
    paths = self.path_inferrer.infer_for_agent(
        agent.name,
        getattr(agent, 'technologies', [])
    )
    # ... rest of method
```

### Step 3: Add Unit Tests

**File**: `tests/unit/lib/template_generator/test_path_pattern_inferrer.py`

**Test Cases**:
1. `test_infers_from_layer_paths()` - Layer-based inference
2. `test_infers_from_technology()` - Tech-specific patterns
3. `test_fallback_to_name_based()` - Fallback behavior
4. `test_deduplicates_patterns()` - No duplicate patterns
5. `test_limits_to_five_patterns()` - Pattern count limit
6. `test_multiple_layers_match()` - Multiple layer matches
7. `test_empty_analysis()` - Handles missing data

### Step 4: Integration Testing

**File**: `tests/unit/lib/template_generator/test_rules_structure_generator.py`

**Test Cases**:
1. Update existing tests to use mock `PathPatternInferrer`
2. Add test for inferrer integration
3. Verify frontmatter generation with inferred paths

## Files to Create

1. `installer/core/lib/template_generator/path_pattern_inferrer.py` (~200 lines)
2. `tests/unit/lib/template_generator/test_path_pattern_inferrer.py` (~150 lines)

## Files to Modify

1. `installer/core/lib/template_generator/rules_structure_generator.py`
   - Add import for `PathPatternInferrer`
   - Initialize `self.path_inferrer` in `__init__`
   - Modify `_generate_agent_rules()` to use inferrer
   - Keep `_infer_agent_paths()` as deprecated fallback

## Acceptance Criteria

- [x] `PathPatternInferrer` class implemented
- [x] Uses layer information from analysis
- [x] Uses technology detection for patterns
- [x] Falls back to name-based inference
- [x] Integrated with `RulesStructureGenerator`
- [x] Generated patterns are valid glob syntax
- [x] Unit tests cover inference logic
- [x] All tests pass

## Edge Cases

1. **Empty layer paths**: Fallback to name-based inference
2. **No matching technologies**: Use extension patterns only
3. **Multiple layer matches**: Include all unique patterns
4. **Very long pattern lists**: Limit to 5 patterns maximum
5. **Case sensitivity**: Normalize to lowercase for matching

## Dependencies

- Requires `CodebaseAnalysis` with populated `architecture.layers`
- Requires agent objects with `technologies` attribute

## Testing Strategy

1. Unit test `PathPatternInferrer` in isolation
2. Unit test integration with `RulesStructureGenerator`
3. Manual verification with real codebase analysis
4. Run existing test suite to ensure no regressions

## Risk Assessment

**Low Risk**:
- New class doesn't modify existing behavior
- Fallback maintains backward compatibility
- Isolated changes with clear interfaces

## Estimated Effort

- Implementation: 2 hours
- Testing: 1 hour
- Integration verification: 0.5 hours
- **Total**: 3-4 hours
