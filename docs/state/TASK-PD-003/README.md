# TASK-PD-003 Implementation Planning Documentation

## Overview

This directory contains comprehensive implementation planning documentation for **TASK-PD-003: Update enhancer.py to call new applier methods**.

**Task**: Update `enhancer.py` to use the new `apply_with_split()` method from applier, enabling progressive disclosure output.

**Status**: READY FOR IMPLEMENTATION
**Created**: 2025-12-05
**Complexity**: 5/10 (Medium)
**Estimated Duration**: 1 day (3.5 hours active work)

## Documents in This Directory

### 1. implementation_plan.md (42 KB, 1505 lines)
**Comprehensive implementation guide** - Start here for full details.

**Sections**:
1. Current State Analysis (5.1.1-1.5)
   - Current enhancer.py implementation
   - Current applier integration points
   - TASK-PD-001 and TASK-PD-002 completion status
   - Backward compatibility concerns

2. Required Changes (2.1-2.4)
   - Detailed code changes for enhancer.py (4 changes)
   - Command documentation updates (3 changes)
   - Integration points summary

3. Test Strategy (3.1-3.4)
   - Unit test specifications (6 tests)
   - Integration test specifications (5 tests)
   - Coverage goals (≥80% lines, ≥75% branches)

4. Implementation Steps (4.1-4.5)
   - 8 sequential implementation steps across 5 phases
   - Each step with actions, validation, and time estimate
   - Total: 3.5 hours

5. Risk Assessment (5.1-5.4)
   - 4 potential breaking changes with mitigation
   - Performance considerations
   - Integration issues
   - Backward compatibility analysis

6. Acceptance Criteria Verification (7.1-7.7)
   - All 7 acceptance criteria mapped to implementation steps
   - Verification procedures for each

7. Success Criteria (Section 8)
   - Code quality standards
   - Test coverage requirements
   - Documentation requirements

8. Post-Implementation Notes (Section 9)
   - Handoff criteria
   - Next task dependencies

## Quick Navigation

### For Quick Overview
→ Start with **SUMMARY.md** (5 min read)

### For Day-to-Day Work
→ Use **QUICK_REFERENCE.md** (2 min lookup)

### For Detailed Implementation
→ Refer to **implementation_plan.md** (comprehensive guide)

## Key Information at a Glance

### What Gets Changed

**File 1**: `installer/global/lib/agent_enhancement/enhancer.py`
- Add 3 fields + 1 property to EnhancementResult dataclass
- Add `split_output` parameter to enhance() method
- Implement branching logic for split vs single-file modes
- Update docstring with new behavior

**File 2**: `installer/global/commands/agent-enhance.md`
- Update output format examples (split + single-file)
- Add usage examples for both modes
- Document new command-line flags

**Files 3-4**: NEW test files
- `tests/unit/test_enhancer_split_output.py` (6 unit tests)
- `tests/integration/test_enhancer_split_integration.py` (5 integration tests)

### Critical Dependencies

1. **TASK-PD-001** (Applier Refactor)
   - Must provide: `applier.apply_with_split()` method
   - Status: Verify before starting

2. **TASK-PD-002** (Loading Instruction Template)
   - Must provide: `generate_loading_instruction()` function
   - Status: Verify before starting

### Implementation Timeline

| Phase | Duration | What |
|-------|----------|------|
| A | 10 min | Verify dependencies |
| B | 55 min | Implement code changes |
| C | 20 min | Update documentation |
| D | 1 hr 45 min | Create tests |
| E | 30 min | Run full test suite |
| **TOTAL** | **~3.5 hours** | |

### Success Criteria

All 7 acceptance criteria must be met:
1. enhance() supports split_output parameter
2. Default behavior is split_output=True
3. EnhancementResult dataclass implemented
4. Backward compatible mode available
5. Command output shows both files
6. Unit tests for both modes
7. Integration test for full enhancement

**Plus**: ≥80% line coverage, ≥75% branch coverage

## How to Use These Documents

### Step 1: Initial Planning
1. Read `SUMMARY.md` (5 min) for overview
2. Review `QUICK_REFERENCE.md` (5 min) for implementation steps
3. Check dependencies are complete

### Step 2: Detailed Planning
1. Read `implementation_plan.md` Section 1 (Current State Analysis)
2. Read Section 2 (Required Changes) for code modifications
3. Read Section 3 (Test Strategy) for test specifications

### Step 3: Execution
1. Follow Implementation Steps (Section 4 of main plan)
2. Use `QUICK_REFERENCE.md` for quick lookup during coding
3. Refer to specific sections of main plan as needed

### Step 4: Testing
1. Follow Test Strategy (Section 3 of main plan)
2. Execute unit tests (Step 6)
3. Execute integration tests (Step 7)
4. Run full test suite (Step 8)

### Step 5: Verification
1. Check all acceptance criteria met (Section 7)
2. Verify coverage targets (≥80% lines, ≥75% branches)
3. Get code review
4. Mark task complete

## Dependency Verification

Before starting implementation, verify these methods exist:

```bash
# Check TASK-PD-001 completion
grep -n "def apply_with_split" /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/global/lib/agent_enhancement/applier.py

# Check TASK-PD-002 completion
grep -n "def generate_loading_instruction" /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/global/lib/agent_enhancement/applier.py
```

Both commands must return a result line number. If not found, dependencies are incomplete.

## File Locations

### Implementation Files
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/global/lib/agent_enhancement/enhancer.py`
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/global/commands/agent-enhance.md`

### Test Files to Create
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_enhancer_split_output.py`
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_enhancer_split_integration.py`

## Key Decisions

1. **Default: split_output=True** - Progressive disclosure is new default
2. **Backward Compatibility** - Single-file mode available via split_output=False
3. **New Fields Optional** - All fields have defaults for compatibility
4. **Branch on Parameter** - Implementation branches based on split_output value

## Next Steps After Completion

1. **TASK-PD-004**: Command integration
   - CLI flag parsing
   - Output handler updates

2. **TASK-PD-005**: Documentation generator updates
   - Handle split files

3. **TASK-PD-006+**: Deploy to all agents
   - Apply split formatting everywhere

## Document Statistics

| Document | Size | Lines | Purpose |
|----------|------|-------|---------|
| implementation_plan.md | 42 KB | 1505 | Comprehensive guide |
| SUMMARY.md | 5.1 KB | 159 | Executive overview |
| QUICK_REFERENCE.md | 6.1 KB | 216 | Quick lookup |
| README.md (this file) | - | - | Index and guide |

## Questions or Issues?

Refer to:
1. **For specifics**: Check implementation_plan.md Section 2 (Required Changes)
2. **For procedures**: Check implementation_plan.md Section 4 (Implementation Steps)
3. **For tests**: Check implementation_plan.md Section 3 (Test Strategy)
4. **For risks**: Check implementation_plan.md Section 5 (Risk Assessment)

## Status

✅ **READY FOR IMPLEMENTATION**
- All planning complete
- All dependencies identified
- All tests specified
- All risks assessed
- All success criteria defined

**Date**: 2025-12-05
**Prepared for**: Implementation Phase
**Next Review**: Upon completion

---

**Start with**: `SUMMARY.md` for 5-minute overview
**Then use**: `implementation_plan.md` for detailed work
**Quick ref**: `QUICK_REFERENCE.md` during coding
