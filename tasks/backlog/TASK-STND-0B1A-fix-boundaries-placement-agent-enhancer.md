# TASK-STND-0B1A: Fix Boundaries Section Placement in Agent-Content-Enhancer

**Created**: 2025-11-23
**Priority**: HIGH
**Estimated Effort**: 3-4 hours
**Task Type**: implementation
**Tags**: agent-enhancement, github-standards, placement-fix

## Problem Statement

The agent-content-enhancer (TASK-STND-8B4C) successfully generates boundaries sections with perfect content quality (9.5/10), but places them at the **end of file** (line 669) instead of after Quick Start (lines 80-150) as recommended by GitHub best practices (analysis of 2,500+ repositories).

### Evidence

**Current Behavior**:
- Enhanced agent file: `xunit-nsubstitute-testing-specialist.md` (694 lines)
- Boundaries section location: **Line 669** ❌
- Target location: **Lines 80-150** (after Quick Start, before Code Examples)

**GitHub Recommendation** (from `github-agent-best-practices-analysis.md`):
> "Boundaries should be visible early in the document (lines 80-150) for authority clarity and user trust."

**Impact**:
- Users must read 668 lines before seeing agent boundaries
- Reduces discoverability of ALWAYS/NEVER/ASK constraints
- Violates GitHub's "early boundaries" principle

## Motivation

**From GitHub Analysis of 2,500+ Repositories**:
1. **Authority Clarity**: Boundaries establish agent scope immediately after Quick Start
2. **Trust Building**: Users see constraints before diving into examples
3. **Reduced Misuse**: Early boundaries prevent out-of-scope requests
4. **Consistent UX**: Matches user expectations from popular open-source agents

**Current State**: Boundary discoverability = 2/10 (hidden at end)
**Target State**: Boundary discoverability = 9/10 (visible after Quick Start)

## Scope

### ✅ In Scope
- Update `applier.py` section ordering logic ONLY
- Modify `_find_boundaries_insertion_point()` method to target lines 80-150
- Add `_find_post_description_position()` fallback helper
- Comprehensive unit tests for new placement logic
- Integration test to verify correct placement

### ❌ Out of Scope (CRITICAL - Limit Scope)
- **DO NOT** modify boundaries generation logic (`prompt_builder.py`)
- **DO NOT** modify boundaries validation logic (`parser.py`)
- **DO NOT** change boundaries content format (ALWAYS/NEVER/ASK)
- **DO NOT** modify other sections (Code Examples, Best Practices, Related Templates)
- **DO NOT** re-enhance existing agent files (only affects NEW enhancements)

## Acceptance Criteria

### AC-1: Section Placement Logic
- [ ] AC-1.1: Boundaries appear at lines 80-150 in newly enhanced agents
- [ ] AC-1.2: Boundaries appear AFTER "## Quick Start" section
- [ ] AC-1.3: Boundaries appear BEFORE "## Code Examples" section
- [ ] AC-1.4: Boundaries appear BEFORE "## Capabilities" section (if exists)
- [ ] AC-1.5: Fallback logic inserts at line 50-80 when Quick Start missing

### AC-2: Backward Compatibility
- [ ] AC-2.1: Existing enhanced agents NOT affected (no re-enhancement required)
- [ ] AC-2.2: Files without Quick Start section still work (fallback logic)
- [ ] AC-2.3: API contract unchanged (same method signatures)
- [ ] AC-2.4: Other sections (examples, best_practices) placement unchanged
- [ ] AC-2.5: Duplicate boundaries prevention still works

### AC-3: Testing & Validation
- [ ] AC-3.1: Unit test: Boundaries after Quick Start, before Capabilities
- [ ] AC-3.2: Unit test: Boundaries before Code Examples when no Capabilities
- [ ] AC-3.3: Unit test: Fallback placement when no Quick Start (line 50-80)
- [ ] AC-3.4: Unit test: Complex structure with multiple sections
- [ ] AC-3.5: Integration test: Real agent enhancement shows correct placement
- [ ] AC-3.6: All existing unit tests still pass (regression check)

### AC-4: Quality Gates
- [ ] AC-4.1: All tests pass (100% pass rate)
- [ ] AC-4.2: Code coverage ≥80% for modified files
- [ ] AC-4.3: No scope creep (only `applier.py` placement logic modified)
- [ ] AC-4.4: Architectural review score ≥60/100
- [ ] AC-4.5: No performance degradation (<5ms difference)

### AC-5: Documentation
- [ ] AC-5.1: Update `_find_boundaries_insertion_point()` docstring
- [ ] AC-5.2: Add inline comments explaining new placement strategy
- [ ] AC-5.3: Document fallback behavior for missing Quick Start

## Implementation Plan

### Phase 1: Update Placement Logic (1-1.5 hours)

**File**: `installer/global/lib/agent_enhancement/applier.py`

**Method**: `_find_boundaries_insertion_point()` (lines 202-237)

**Changes**:
1. Prioritize Quick Start detection first (not Capabilities)
2. Find next ## section after Quick Start
3. Insert boundaries before that next section
4. Add fallback to `_find_post_description_position()` helper

**New Logic**:
```python
def _find_boundaries_insertion_point(self, lines: list[str]) -> int | None:
    """
    Find insertion point for boundaries section.

    Target: After "## Quick Start", before "## Code Examples"/"## Capabilities"
    GitHub recommendation: Lines 80-150 for optimal authority clarity.

    Strategy:
    1. Find "## Quick Start" section
    2. Find next ## section after Quick Start
    3. Insert boundaries before that next section
    4. Fallback: Insert at line 50-80 if no Quick Start found

    Returns:
        Line index for insertion or None if no suitable point found
    """
    # Step 1: Find Quick Start
    quick_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Quick Start"):
            quick_start_idx = i
            break

    if quick_start_idx is None:
        # Fallback: No Quick Start, insert after description
        return self._find_post_description_position(lines)

    # Step 2: Find next ## section after Quick Start
    for i in range(quick_start_idx + 1, len(lines)):
        if lines[i].strip().startswith("## "):
            return i  # Insert before this section

    # Step 3: No next section, insert at reasonable position
    # Target: ~30 lines after Quick Start (hits 80-150 range)
    target_line = quick_start_idx + 30
    return min(target_line, len(lines))
```

**Add Helper Method**:
```python
def _find_post_description_position(self, lines: list[str]) -> int | None:
    """
    Fallback: Find position after description/purpose section.

    Used when "## Quick Start" doesn't exist.
    Targets line 50-80 range.

    Returns:
        Line index for insertion or None
    """
    # Find end of frontmatter
    frontmatter_end = 0
    frontmatter_count = 0

    for i, line in enumerate(lines):
        if line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count == 2:
                frontmatter_end = i + 1
                break

    # Find first ## section after frontmatter
    for i in range(frontmatter_end, len(lines)):
        if lines[i].strip().startswith("## "):
            # Found first section, look for next ##
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("## "):
                    return j
            # No next section, return reasonable default
            return min(50, len(lines))

    # No structure found, default to line 50
    return min(50, len(lines))
```

### Phase 2: Add Unit Tests (1-1.5 hours)

**File**: `tests/lib/agent_enhancement/test_boundaries_placement.py` (new file)

**Test Cases** (4 minimum):

1. **test_boundaries_after_quick_start_before_capabilities**
   - Setup: Agent with Quick Start and Capabilities sections
   - Assert: Boundaries between Quick Start and Capabilities

2. **test_boundaries_before_examples_no_capabilities**
   - Setup: Agent with Quick Start but no Capabilities
   - Assert: Boundaries before Code Examples section

3. **test_boundaries_fallback_no_quick_start**
   - Setup: Agent without Quick Start section
   - Assert: Boundaries at lines 50-80 (fallback position)

4. **test_boundaries_complex_structure**
   - Setup: Agent with Quick Start, Capabilities, Advanced Usage sections
   - Assert: Boundaries after Quick Start, before Capabilities

### Phase 3: Integration Testing (0.5-1 hour)

**Scenario**: Enhance real agent and verify placement

```bash
# Test with actual agent
/agent-enhance .claude/agents/testing-specialist.md

# Verify boundaries position (should be 80-150)
grep -n "## Boundaries" .claude/agents/testing-specialist.md

# Verify section order
grep -n "^## " .claude/agents/testing-specialist.md
# Expected:
#   50: ## Quick Start
#   84: ## Boundaries  ← TARGET RANGE
#   156: ## Capabilities
#   210: ## Code Examples
```

### Phase 4: Validation & Review (0.5-1 hour)

1. Run full test suite and verify ≥80% coverage
2. Run architectural review (target ≥60/100)
3. Verify no scope creep (only `applier.py` modified)
4. Address any review findings

## Technical Details

### Files to Modify

1. **installer/global/lib/agent_enhancement/applier.py**
   - Lines 202-237: Replace `_find_boundaries_insertion_point()` method
   - Lines 238-280: Add `_find_post_description_position()` helper
   - Lines 116-120: Update `_merge_content()` docstring

2. **tests/lib/agent_enhancement/test_boundaries_placement.py** (new file)
   - 4 comprehensive unit tests for placement logic

### Current vs Proposed Section Ordering

**Current (WRONG)**:
```
Lines 1-20:    YAML frontmatter
Lines 21-50:   Purpose, Technologies
Lines 51-80:   Quick Start
Lines 81-400:  Code Examples
Lines 401-600: Best Practices
Lines 601-650: Related Templates
Lines 651-669: Boundaries ❌ (END OF FILE)
```

**Proposed (CORRECT)**:
```
Lines 1-20:    YAML frontmatter
Lines 21-50:   Purpose, Technologies
Lines 51-80:   Quick Start
Lines 81-150:  Boundaries ✅ (AFTER QUICK START)
Lines 151-200: Capabilities
Lines 201-400: Code Examples
Lines 401-600: Best Practices
Lines 601-650: Related Templates
```

### Backward Compatibility Strategy

**Guaranteed**:
- ✅ Existing enhanced agents NOT modified (no re-enhancement)
- ✅ Files without Quick Start still work (fallback to line 50-80)
- ✅ API contract unchanged (method signatures identical)
- ✅ Other sections (examples, best_practices) unchanged

**Migration**: NONE REQUIRED (only affects NEW enhancements)

## Risk Assessment

### Risk 1: Breaking Existing Enhanced Agents
**Likelihood**: None
**Impact**: N/A
**Mitigation**: Only affects NEW enhancements, existing files untouched

### Risk 2: Incorrect Fallback Placement
**Likelihood**: Low
**Impact**: Low
**Mitigation**: Fallback targets line 50-80 (reasonable default)

### Risk 3: Duplicate Boundaries Sections
**Likelihood**: Very Low
**Impact**: Low
**Mitigation**: Existing duplicate check at line 167 of `applier.py`

### Risk 4: Scope Creep
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Strict AC-4.3 - only `applier.py` placement logic modified

## Testing Strategy

### Unit Tests (4 test cases)
- Test boundaries after Quick Start, before Capabilities
- Test boundaries before Code Examples when no Capabilities
- Test fallback placement when no Quick Start
- Test complex structure with multiple sections

### Integration Tests
- Enhance real agent file
- Verify boundaries at lines 80-150
- Verify section ordering (Quick Start → Boundaries → Code Examples)

### Regression Tests
- All existing unit tests pass
- No breaking changes to API
- Coverage maintained at ≥80%

## Success Metrics

1. **Boundary Discoverability**: 2/10 → 9/10 (lines 80-150 placement)
2. **Test Coverage**: ≥80% for modified files
3. **Test Pass Rate**: 100%
4. **Scope Creep**: 0 violations (only `applier.py` modified)
5. **Architectural Review**: ≥60/100

## Rollback Plan

**If issues arise**:
1. Revert `_find_boundaries_insertion_point()` to original logic
2. No data loss (agent files can be re-enhanced)
3. No breaking changes to API or contract

## Related Tasks

- **TASK-STND-8B4C**: Implemented boundaries generation (content quality 9.5/10, placement 2/10)
  - This task fixes the placement issue identified in code review

## References

1. `installer/global/lib/agent_enhancement/applier.py` - Lines 202-237 (placement logic)
2. `docs/analysis/github-agent-best-practices-analysis.md` - GitHub standards source
3. Enhanced agent file: `/Users/richardwoollcott/.agentecflow/templates/maui-mydrive/agents/xunit-nsubstitute-testing-specialist.md` - Line 669 (current wrong placement)

## Notes

- This task completes the boundaries implementation by fixing the ONLY remaining issue (placement)
- Content quality is perfect (9.5/10) - DO NOT modify generation or validation logic
- Backward compatible - existing enhanced agents do NOT need re-enhancement
- Focused scope - ONLY placement logic in `applier.py`
- 3-4 hour estimate (1.5h logic + 1.5h tests + 1h validation)
