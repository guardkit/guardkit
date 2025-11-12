# Implementation Plan: TASK-FDB2

**Task**: Add --name flag to /template-create command
**Complexity**: 3/10 (Simple)
**Estimated Time**: 1-2 hours

## Overview

Add optional `--name` flag to `/template-create` command allowing users to override AI-generated template names, plus cleanup of `/template-qa` documentation references.

## File Changes

### 1. Command Documentation (installer/global/commands/template-create.md)
- **Lines**: ~30
- **Changes**:
  - Add `--name` flag to flags section with examples
  - Remove `/template-qa` references (lines ~18)
  - Add usage examples with custom names

### 2. Orchestrator Logic (installer/global/commands/lib/template_create_orchestrator.py)
- **Lines**: ~35
- **Changes**:
  - Add `custom_name: Optional[str]` to `OrchestrationConfig`
  - Add `_validate_template_name()` method (pattern: `^[a-z0-9-]+$`, length: 3-50)
  - Modify Phase 2 to override manifest.name if custom_name provided
  - Add validation error handling

### 3. Unit Tests (tests/unit/test_template_create_orchestrator.py)
- **Lines**: ~25
- **Changes**:
  - Test valid name patterns (lowercase, numbers, hyphens)
  - Test invalid patterns (uppercase, underscores, special chars)
  - Test length validation (too short, too long)
  - Test name override in orchestrator

## Implementation Steps

1. **Update Documentation** (15 min)
   - Add --name flag specification
   - Remove /template-qa references
   - Add usage examples

2. **Add Validation** (20 min)
   - Create _validate_template_name() method
   - Implement regex pattern matching
   - Add length checks

3. **Implement Override** (25 min)
   - Add custom_name to OrchestrationConfig
   - Update Phase 2 manifest generation
   - Add validation call before override

4. **Write Tests** (30 min)
   - Unit tests for validation
   - Unit tests for override
   - Edge case coverage

## Testing Strategy

**Unit Tests**:
- Valid patterns: "my-template", "api-123", "react-admin"
- Invalid patterns: "MyTemplate", "my_template", "ab", "a" * 51
- Override: Verify manifest.name equals custom_name
- Empty: Verify AI generation still works

**Manual Test**:
```bash
# Should use custom name
/template-create --name test-template --validate

# Should use AI-generated name
/template-create --validate
```

## Quality Gates

- ✅ All existing tests pass (backward compatibility)
- ✅ New tests achieve ≥80% coverage on new code
- ✅ Pattern validation works correctly
- ✅ No breaking changes to existing functionality

## Risk Assessment

**Low Risk**:
- Isolated changes (3 files, ~90 LOC)
- Optional flag (existing behavior unchanged)
- Simple validation logic
- No core AI analysis changes

## Success Criteria

- ✅ `--name` flag accepts valid template names
- ✅ Invalid names show clear error messages
- ✅ AI generation works when flag not provided
- ✅ All `/template-qa` references removed
- ✅ Tests pass with ≥80% coverage
