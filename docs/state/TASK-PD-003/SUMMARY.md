# TASK-PD-003 Implementation Plan - Executive Summary

## Overview
Comprehensive implementation plan for updating `enhancer.py` to call new applier methods (`apply_with_split()`) and enabling progressive disclosure output through split files.

## Key Changes

### 1. EnhancementResult Dataclass
- Add 3 new fields: `core_file`, `extended_file`, `split_output`
- Add `files` property for convenient access to all files
- Maintain full backward compatibility with existing code

### 2. enhance() Method
- Add `split_output: bool = True` parameter (default enables progressive disclosure)
- Implement branching logic:
  - `split_output=True`: Call `applier.apply_with_split()` → Returns 2 files
  - `split_output=False`: Call `applier.apply()` → Returns 1 file (legacy mode)
- Enhanced logging showing which mode is active
- Proper exception handling with all fields

### 3. Command Documentation
- Update output format examples for both modes
- Add usage examples for split-file and single-file modes
- Document `--split-output` (default) and `--single-file` (legacy) flags

## Implementation Timeline

| Phase | Step | Description | Duration |
|-------|------|-------------|----------|
| A | 1 | Verify dependencies complete | 10 min |
| B | 2 | Update EnhancementResult dataclass | 15 min |
| B | 3 | Update enhance() signature & docstring | 10 min |
| B | 4 | Refactor enhance() implementation | 30 min |
| C | 5 | Update command documentation | 20 min |
| D | 6 | Create unit tests | 45 min |
| D | 7 | Create integration tests | 1 hour |
| E | 8 | Run full test suite | 30 min |
| **Total** | | | **3.5 hours** |

## Test Coverage

### Unit Tests (6 tests)
- EnhancementResult split-file mode
- EnhancementResult single-file mode
- EnhancementResult error handling
- files property (split mode)
- files property (single mode)
- files property (empty)

### Integration Tests (5 tests)
- Full enhancement workflow with split output
- Full enhancement workflow with single-file mode
- Dry-run mode doesn't create files
- Loading instruction in split output
- Extended file content verification

**Target Coverage**: ≥80% lines, ≥75% branches

## Dependencies

### Must Complete Before Starting
1. **TASK-PD-001**: Applier refactor
   - Requires: `apply_with_split()` method
   - Status: Check with grep for method signature

2. **TASK-PD-002**: Loading instruction template
   - Requires: `generate_loading_instruction()` function
   - Status: Check with grep for function signature

### Will Enable
1. **TASK-PD-004**: Command integration
   - CLI flag parsing for split modes
   - Command output handler updates

## Backward Compatibility

✅ **Fully backward compatible**:
- New fields optional with default None
- Old code using `success` and `error` still works
- Single-file mode available via `split_output=False`
- No breaking changes to existing APIs

## Risk Assessment

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|-----------|--------|----------|-----------|
| EnhancementResult API change | Medium | High | MEDIUM | Optional fields, property access |
| Default behavior change | Low | Medium | LOW | Document, provide legacy mode |
| Dependency missing | Medium | High | HIGH | Verify before start, clear errors |
| Performance impact | Low | Low | LOW | Monitor tests, add benchmarks |

## Files to Modify

1. **enhancer.py** (4 changes)
   - EnhancementResult dataclass definition
   - enhance() method signature
   - enhance() docstring
   - enhance() implementation (branch logic)

2. **agent-enhance.md** (3 changes)
   - Output format section (both modes)
   - Usage examples (both modes)
   - Mode selection documentation

## Acceptance Criteria Checklist

- [ ] AC-1: enhance() supports split_output parameter
- [ ] AC-2: Default is split_output=True
- [ ] AC-3: EnhancementResult dataclass implemented
- [ ] AC-4: Backward compatible mode available
- [ ] AC-5: Command output shows both files
- [ ] AC-6: Unit tests for both modes
- [ ] AC-7: Integration test for full enhancement

## Implementation Checklist

### Pre-Implementation
- [ ] Verify TASK-PD-001 completion
- [ ] Verify TASK-PD-002 completion
- [ ] Review existing test patterns
- [ ] Create feature branch

### Code Phase
- [ ] Step 1-4: Implement code changes (1 hour 5 min)
- [ ] Step 5: Update documentation (20 min)

### Testing Phase
- [ ] Step 6-7: Create tests (1 hour 45 min)
- [ ] Step 8: Run full suite (30 min)

### Validation Phase
- [ ] Manual testing (split mode)
- [ ] Manual testing (single-file mode)
- [ ] Code review
- [ ] Documentation review

## Success Metrics

✅ All code follows project conventions
✅ Type hints present and correct
✅ Test coverage ≥80% lines, ≥75% branches
✅ All acceptance criteria tested
✅ Backward compatible
✅ Clear error messages
✅ Git hygiene maintained

## Next Steps

1. Verify TASK-PD-001 and TASK-PD-002 are complete
2. Follow sequential implementation steps in main plan
3. Run tests at each phase
4. Complete all acceptance criteria
5. Hand off to TASK-PD-004 (command integration)

---

**Full Plan**: See `implementation_plan.md`
**Status**: READY FOR IMPLEMENTATION
**Date**: 2025-12-05
