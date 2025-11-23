# TASK-STND-783B: Fix Boundaries Placement - Add 3 Missing Fallback Strategies to applier.py

**Created**: 2025-11-23
**Priority**: HIGH
**Estimated Effort**: 2-3 hours
**Complexity**: 3/10 (LOW)
**Task Type**: bugfix
**Tags**: agent-enhancement, github-standards, boundaries-placement, bugfix

---

## Problem Statement

### Current Situation

TASK-STND-0B1A implemented boundaries section enhancement with **92% failure rate** (11/12 files) placing boundaries AFTER Code Examples instead of BEFORE.

**Impact:**
- **GitHub recommendation**: Boundaries at lines 80-150 (before Code Examples)
- **Actual placement**: Boundaries at lines 250-450 (after Code Examples and Related Templates)
- **92% of enhanced agent files violate GitHub placement guidelines**

### Root Cause Analysis

The `_find_boundaries_insertion_point()` method in [applier.py:202-237](installer/global/lib/agent_enhancement/applier.py#L202-L237) uses a **2-tier fallback strategy** that returns `None` when neither "## Capabilities" nor "## Quick Start" sections exist.

When `None` is returned, the `_merge_content()` method's fallback logic appends boundaries at the **end of file**, violating GitHub's early placement recommendation.

### Evidence

**File Analysis Results:**

| File | Has Quick Start? | Boundaries Line | Code Examples Line | Status |
|------|-----------------|----------------|-------------------|---------|
| [maui-mvvm-viewmodel-specialist.md](~/.agentecflow/templates/fix-boundaries-placement/agents/maui-mvvm-viewmodel-specialist.md#L68) | ✅ Yes | 68 | 104 | ✅ CORRECT |
| [maui-navigation-specialist.md](~/.agentecflow/templates/fix-boundaries-placement/agents/maui-navigation-specialist.md#L256) | ❌ No | 256 | 52 | ❌ WRONG |
| [xunit-nsubstitute-testing-specialist.md](~/.agentecflow/templates/fix-boundaries-placement/agents/xunit-nsubstitute-testing-specialist.md#L423) | ❌ No | 423 | ~200 | ❌ WRONG |
| [engine-orchestration-specialist.md](~/.agentecflow/templates/fix-boundaries-placement/agents/engine-orchestration-specialist.md#L394) | ❌ No | 394 | 64 | ❌ WRONG |
| (8 other files) | ❌ No | End of file | Mid-file | ❌ WRONG |

**Key Findings:**
- 0/12 files have "## Capabilities" section
- 1/12 files have "## Quick Start" section (successful case)
- 11/12 files return `None` → boundaries appended at end of file

### Current Buggy Implementation

**File**: [installer/global/lib/agent_enhancement/applier.py:202-237](installer/global/lib/agent_enhancement/applier.py#L202-L237)

```python
def _find_boundaries_insertion_point(self, lines: list[str]) -> int | None:
    """
    Find the insertion point for boundaries section.

    Looks for "## Capabilities" section and returns index before it.
    If not found, looks for "## Quick Start" and returns index after it.
    """
    # Priority 1: Find "## Capabilities" and insert before it
    for i, line in enumerate(lines):
        if line.strip().startswith("## Capabilities"):
            return i

    # Priority 2: Find "## Quick Start" and insert after its content
    quick_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Quick Start"):
            quick_start_idx = i
            break

    if quick_start_idx is not None:
        # Find next ## section after Quick Start
        for i in range(quick_start_idx + 1, len(lines)):
            if lines[i].strip().startswith("## "):
                return i

        # If no next section, append at end
        return len(lines)

    # BUG: No suitable insertion point found
    return None  # ← Returns None, triggers end-of-file append fallback
```

**Why It Fails:**
1. Looks for "## Capabilities" → **Not found** in any of 12 files
2. Looks for "## Quick Start" → **Only found** in 1/12 files
3. Returns `None` for 11/12 files
4. `_merge_content()` fallback: `if insertion_point is not None:` ... `else:` appends at end
5. **Result**: Boundaries appear at line 250-450 instead of 80-150

---

## Solution: 5-Tier Bulletproof Fallback Strategy

### Proposed Implementation

**Implement 3 NEW fallback strategies** (Priority 3, 4, 5) to ensure method NEVER returns `None`:

```python
def _find_boundaries_insertion_point(self, lines: list[str]) -> int:
    """
    Find insertion point for boundaries section with 5-tier fallback.

    NEVER returns None - always finds suitable insertion point.
    GitHub recommendation: lines 80-150, before Code Examples.

    Priority Order:
    1. Before "## Capabilities" (if exists)
    2. After "## Quick Start" (if exists)
    3. Before "## Code Examples" ← NEW (fixes 92% of failures)
    4. Before "## Related Templates" ← NEW (safety net)
    5. Frontmatter + 50 lines ← NEW (absolute last resort)

    Returns:
        int: Line index for insertion (NEVER None)
    """

    # Priority 1: Before "## Capabilities"
    for i, line in enumerate(lines):
        if line.strip().startswith("## Capabilities"):
            return i

    # Priority 2: After "## Quick Start"
    quick_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Quick Start"):
            quick_start_idx = i
            break

    if quick_start_idx is not None:
        # Find next ## section after Quick Start
        for i in range(quick_start_idx + 1, len(lines)):
            if lines[i].strip().startswith("## "):
                return i

    # Priority 3: Before "## Code Examples" ← NEW
    for i, line in enumerate(lines):
        if line.strip().startswith("## Code Examples"):
            return i

    # Priority 4: Before "## Related Templates" ← NEW
    for i, line in enumerate(lines):
        if line.strip().startswith("## Related Templates"):
            return i

    # Priority 5: Frontmatter + 50 lines ← NEW (last resort)
    frontmatter_end = 0
    frontmatter_count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            frontmatter_count += 1
            if frontmatter_count == 2:
                frontmatter_end = i + 1
                break

    insertion_point = min(frontmatter_end + 50, len(lines))

    # Find next section boundary at or after insertion_point
    for i in range(insertion_point, len(lines)):
        if lines[i].strip().startswith("## "):
            return i

    return insertion_point  # Never None
```

### Changes Summary

**Modified Lines**:
- **Line 202**: Change return type `int | None` → `int`
- **Lines 203-213**: Update docstring with 5-tier priority explanation
- **Lines 233-256**: Add Priority 3, 4, 5 implementations (23 new lines)
- **Line 237**: Change `return None` → removed (never reached)

**Total Impact**:
- **1 file** modified: `applier.py`
- **1 method** modified: `_find_boundaries_insertion_point()`
- **3 new strategies** added: Priority 3, 4, 5
- **23 lines** added
- **1 line** removed (`return None`)

---

## Acceptance Criteria

### AC-1: Functional Requirements

- [ ] **AC-1.1**: Method NEVER returns `None` (return type annotation: `int`)
- [ ] **AC-1.2**: Priority 3 (Before "## Code Examples") implemented and working
- [ ] **AC-1.3**: Priority 4 (Before "## Related Templates") implemented and working
- [ ] **AC-1.4**: Priority 5 (Frontmatter + 50 lines) implemented and working
- [ ] **AC-1.5**: All 12 test files have boundaries BEFORE Code Examples (100% success rate)
- [ ] **AC-1.6**: All 12 test files have boundaries within lines 40-180 (100% range compliance)
- [ ] **AC-1.7**: Backward compatibility preserved (files with "## Quick Start" still work)

### AC-2: Testing Requirements

- [ ] **AC-2.1**: Unit test for Priority 3 (file with "## Code Examples" only)
- [ ] **AC-2.2**: Unit test for Priority 4 (file with "## Related Templates" only)
- [ ] **AC-2.3**: Unit test for Priority 5 (file with no standard sections)
- [ ] **AC-2.4**: Unit test for regression (file with "## Quick Start" still works)
- [ ] **AC-2.5**: Integration test validates all 12 enhanced agent files
- [ ] **AC-2.6**: All existing applier.py tests pass (0 regressions)

### AC-3: Quality Gates

- [ ] **AC-3.1**: Code compiles successfully (Python syntax valid)
- [ ] **AC-3.2**: All tests pass (100% pass rate)
- [ ] **AC-3.3**: Line coverage ≥80% for modified method
- [ ] **AC-3.4**: Branch coverage ≥75% (all 5 priorities tested)
- [ ] **AC-3.5**: Code review approval (SOLID compliance)

### AC-4: Scope Compliance

- [ ] **AC-4.1**: ONLY 1 file modified: `applier.py`
- [ ] **AC-4.2**: ONLY 1 method modified: `_find_boundaries_insertion_point()`
- [ ] **AC-4.3**: NO changes to `prompt_builder.py` (boundaries generation)
- [ ] **AC-4.4**: NO changes to `parser.py` (boundaries validation)
- [ ] **AC-4.5**: NO changes to `_merge_content()` beyond semantic change from None check
- [ ] **AC-4.6**: NO changes to other section handlers (examples, related_templates)

### AC-5: Documentation Requirements

- [ ] **AC-5.1**: Method docstring updated with 5-tier priority explanation
- [ ] **AC-5.2**: Inline comments added for each new priority tier
- [ ] **AC-5.3**: Commit message documents fix with reference to TASK-STND-0B1A
- [ ] **AC-5.4**: No external documentation required (internal implementation fix)

---

## Scope Boundaries

### ✅ IN SCOPE

**File to Modify**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/lib/agent_enhancement/applier.py`
  - Lines 202-237: `_find_boundaries_insertion_point()` method
  - Update method docstring
  - Update return type annotation: `int | None` → `int`
  - Add Priority 3: Before "## Code Examples"
  - Add Priority 4: Before "## Related Templates"
  - Add Priority 5: Frontmatter + 50 lines
  - Add debug logging for each priority tier (optional)

**Files to Test**:
- All 12 enhanced agent files in `~/.agentecflow/templates/fix-boundaries-placement/agents/`

**Test File to Create**:
- `tests/lib/agent_enhancement/test_applier_boundaries_placement.py` (new file)

### ❌ OUT OF SCOPE

**DO NOT MODIFY**:
1. `installer/global/lib/agent_enhancement/prompt_builder.py`
   - Boundaries generation logic is working correctly
   - Content quality is 9.5/10
   - DO NOT touch this file

2. `installer/global/lib/agent_enhancement/parser.py`
   - Boundaries validation logic is working correctly
   - ALWAYS/NEVER/ASK validation is perfect
   - DO NOT touch this file

3. `_merge_content()` method in `applier.py`
   - Only semantic change from `if insertion_point is not None:` check
   - No functional changes to merge logic
   - DO NOT modify section merging behavior

4. Other section handlers
   - Examples, best_practices, related_templates handling unchanged
   - DO NOT modify other section placement logic

5. Any files outside `applier.py`
   - DO NOT modify test files (only add new tests)
   - DO NOT modify configuration files
   - DO NOT modify documentation

**Scope Constraints**:
- **ONLY 1 file** modified in production code
- **ONLY 1 method** modified
- **ONLY 3 new strategies** added (Priority 3, 4, 5)
- **0 behavioral changes** to existing working code paths

---

## Test Strategy

### Unit Tests (4 Required)

**Test File**: `tests/lib/agent_enhancement/test_applier_boundaries_placement.py`

#### Test 1: Priority 3 - Before Code Examples

```python
def test_boundaries_before_code_examples():
    """Priority 3: File with Code Examples but no Quick Start/Capabilities."""
    lines = [
        "---",
        "name: test-agent",
        "---",
        "# Agent",
        "## Purpose",
        "Description here",
        "## Code Examples",  # ← Boundaries should insert HERE (line 6)
        "Example code",
        "## Related Templates",
        "Templates"
    ]

    applier = EnhancementApplier()
    result = applier._find_boundaries_insertion_point(lines)

    assert result == 6, f"Expected line 6, got {result}"
    assert result is not None, "Method returned None (BUG)"
    assert isinstance(result, int), f"Expected int, got {type(result)}"
```

#### Test 2: Priority 4 - Before Related Templates

```python
def test_boundaries_before_related_templates():
    """Priority 4: File with Related Templates but no Code Examples."""
    lines = [
        "---",
        "name: test-agent",
        "---",
        "# Agent",
        "## Purpose",
        "Description here",
        "## Related Templates",  # ← Boundaries should insert HERE (line 6)
        "Template references"
    ]

    applier = EnhancementApplier()
    result = applier._find_boundaries_insertion_point(lines)

    assert result == 6, f"Expected line 6, got {result}"
    assert result is not None, "Method returned None (BUG)"
```

#### Test 3: Priority 5 - Frontmatter + 50 Lines

```python
def test_boundaries_frontmatter_fallback():
    """Priority 5: File with no standard sections."""
    lines = ["---", "name: test", "---", "# Agent"]
    lines.extend([f"Content line {i}" for i in range(60)])  # 64 total lines

    applier = EnhancementApplier()
    result = applier._find_boundaries_insertion_point(lines)

    # Should return frontmatter_end (3) + 50 = 53
    assert 50 <= result <= 60, f"Expected ~53, got {result}"
    assert result is not None, "Method returned None (BUG)"
```

#### Test 4: Regression - Quick Start Still Works

```python
def test_boundaries_after_quick_start_regression():
    """Priority 2: Existing behavior preserved for files with Quick Start."""
    lines = [
        "---",
        "name: test",
        "---",
        "# Agent",
        "## Quick Start",
        "Quick start instructions",
        "## Code Examples",  # ← Boundaries should insert HERE (line 6)
        "Examples"
    ]

    applier = EnhancementApplier()
    result = applier._find_boundaries_insertion_point(lines)

    assert result == 6, f"Expected line 6 (after Quick Start), got {result}"
    assert result is not None, "Method returned None (BUG)"
```

### Integration Test (1 Required)

#### Test 5: All 12 Enhanced Agent Files

```python
def test_all_enhanced_agents_boundaries_placement():
    """Validate all 12 agent files have correct boundaries placement."""
    template_dir = Path.home() / ".agentecflow/templates/fix-boundaries-placement/agents"
    agent_files = list(template_dir.glob("*.md"))

    assert len(agent_files) == 12, f"Expected 12 files, found {len(agent_files)}"

    failures = []
    for agent_file in agent_files:
        content = agent_file.read_text()
        lines = content.split('\n')

        # Find boundaries and code examples line numbers
        boundaries_line = None
        code_examples_line = None

        for i, line in enumerate(lines):
            if line.strip() == "## Boundaries":
                boundaries_line = i
            if line.strip().startswith("## Code Examples"):
                code_examples_line = i

        # Validate placement
        if boundaries_line is None:
            failures.append(f"{agent_file.name}: No boundaries section found")
        elif code_examples_line and boundaries_line > code_examples_line:
            failures.append(
                f"{agent_file.name}: Boundaries at line {boundaries_line}, "
                f"Code Examples at {code_examples_line} (AFTER - WRONG)"
            )
        elif boundaries_line < 40 or boundaries_line > 180:
            failures.append(
                f"{agent_file.name}: Boundaries at line {boundaries_line} "
                f"(outside recommended 40-180 range)"
            )

    assert not failures, "Placement failures:\n" + "\n".join(failures)
```

### Regression Tests

#### Test 6: Existing Test Suite

Run all existing tests in `tests/lib/agent_enhancement/` to ensure:
- No regressions in `_merge_content()` behavior
- Other section handling unchanged
- Frontmatter preservation working
- Duplicate section prevention working

---

## Validation Criteria

### Success Metrics

**Before Fix**:
- ✅ 1/12 files (8%) with correct boundaries placement
- ❌ 11/12 files (92%) with incorrect placement (after Code Examples)
- ❌ Average placement: line 300+ (should be 80-150)

**After Fix**:
- ✅ 12/12 files (100%) with correct boundaries placement
- ✅ 0/12 files with boundaries after Code Examples
- ✅ Average placement: line 60-120 (within GitHub recommendation)

### Validation Checklist

- [ ] **100% placement success**: All 12 files have boundaries BEFORE Code Examples
- [ ] **100% range compliance**: All boundaries within lines 40-180
- [ ] **0% scope creep**: Only 1 method in 1 file modified
- [ ] **100% test pass rate**: All unit + integration + regression tests pass
- [ ] **0 regressions**: Existing functionality unchanged
- [ ] **Method never returns None**: Return type is `int`, not `int | None`

---

## Implementation Plan

### Phase 1: Update Method Signature (15 minutes)

**Changes**:
1. Line 202: Change return type `int | None` → `int`
2. Lines 203-213: Update docstring with 5-tier priority explanation
3. Add example showing each priority tier in docstring

**Validation**:
- Type checker passes (mypy/pyright)
- Docstring renders correctly

### Phase 2: Implement Priority 3 - Before Code Examples (20 minutes)

**Changes**:
1. After Priority 2 logic, add:
   ```python
   # Priority 3: Before "## Code Examples"
   for i, line in enumerate(lines):
       if line.strip().startswith("## Code Examples"):
           return i
   ```
2. Add debug logging: `logger.debug("Boundaries: Priority 3 - Before Code Examples at line {i}")`

**Validation**:
- Unit test passes (test_boundaries_before_code_examples)
- Test with real file (maui-navigation-specialist.md) shows boundaries before Code Examples

### Phase 3: Implement Priority 4 - Before Related Templates (20 minutes)

**Changes**:
1. After Priority 3 logic, add:
   ```python
   # Priority 4: Before "## Related Templates"
   for i, line in enumerate(lines):
       if line.strip().startswith("## Related Templates"):
           return i
   ```
2. Add debug logging: `logger.debug("Boundaries: Priority 4 - Before Related Templates at line {i}")`

**Validation**:
- Unit test passes (test_boundaries_before_related_templates)
- Fallback logic working correctly

### Phase 4: Implement Priority 5 - Frontmatter + 50 Lines (30 minutes)

**Changes**:
1. After Priority 4 logic, add frontmatter detection and calculation:
   ```python
   # Priority 5: Frontmatter + 50 lines (last resort)
   frontmatter_end = 0
   frontmatter_count = 0
   for i, line in enumerate(lines):
       if line.strip() == "---":
           frontmatter_count += 1
           if frontmatter_count == 2:
               frontmatter_end = i + 1
               break

   insertion_point = min(frontmatter_end + 50, len(lines))

   # Find next section boundary at or after insertion_point
   for i in range(insertion_point, len(lines)):
       if lines[i].strip().startswith("## "):
           return i

   return insertion_point  # Never None
   ```
2. Add debug logging: `logger.debug(f"Boundaries: Priority 5 - Frontmatter+50 at line {insertion_point}")`
3. Remove old `return None` line

**Validation**:
- Unit test passes (test_boundaries_frontmatter_fallback)
- Method never returns None (type checker confirms)

### Phase 5: Integration Testing (30 minutes)

**Tasks**:
1. Run `/agent-enhance` on all 12 test files (fresh enhancement)
2. Run integration test (test_all_enhanced_agents_boundaries_placement)
3. Generate validation report showing before/after placement

**Validation**:
- All 12 files show boundaries BEFORE Code Examples
- All 12 files within lines 40-180 range
- Visual inspection confirms correct placement

### Phase 6: Regression Testing (15 minutes)

**Tasks**:
1. Run existing test suite: `pytest tests/lib/agent_enhancement/ -v`
2. Verify no failures
3. Check coverage report shows ≥80% for modified method

**Validation**:
- All tests pass
- No behavioral changes to other methods
- Coverage targets met

### Phase 7: Documentation & Commit (10 minutes)

**Tasks**:
1. Review and finalize docstring
2. Add inline comments for each priority tier
3. Commit with message:
   ```
   Fix TASK-STND-783B: Add 3 missing fallback strategies to boundaries placement

   Root cause: _find_boundaries_insertion_point() returned None when neither
   "## Capabilities" nor "## Quick Start" existed, causing end-of-file append.

   Fix: Added Priority 3 (Before Code Examples), Priority 4 (Before Related
   Templates), Priority 5 (Frontmatter + 50 lines) fallback strategies.

   Result: 100% placement success (was 8%), boundaries always before Code Examples.

   Closes TASK-STND-783B
   Related: TASK-STND-0B1A
   ```

---

## Risk Assessment

**Overall Risk Level**: LOW

### Risk 1: Priority 5 Places Boundaries Too Early

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Unit test validates placement with 60-line file
- Frontmatter + 50 typically lands in 60-80 range (acceptable)
- Section boundary detection prevents mid-paragraph insertion

### Risk 2: Breaking Change to Existing Files

**Likelihood**: Very Low
**Impact**: High
**Mitigation**:
- Regression test suite validates backward compatibility
- Priority 1 and 2 logic unchanged
- Only adds new fallback strategies, doesn't modify existing ones

### Risk 3: Performance Degradation

**Likelihood**: Very Low
**Impact**: Low
**Mitigation**:
- 5 simple linear scans (O(n) each)
- Typical file size: 500-700 lines
- Estimated impact: <1ms per file (negligible)

### Risk 4: Edge Case - File With No Sections

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Priority 5 handles via frontmatter + 50 lines
- Unit test validates edge case behavior
- Fallback ensures boundaries never appended at end

### Rollback Plan

If issues arise:
1. **Revert single commit** (git revert)
2. **Re-run enhancement** with previous version
3. **Zero dependencies** on changed method signature (only called internally)
4. **No data loss** - agent files can be re-enhanced

---

## Success Metrics

### Performance Metrics

**Before Fix**:
- Success rate: 8% (1/12 files)
- Failure rate: 92% (11/12 files)
- Average placement: Line 300+
- GitHub compliance: 8%

**After Fix** (Target):
- Success rate: 100% (12/12 files)
- Failure rate: 0% (0/12 files)
- Average placement: Line 60-120
- GitHub compliance: 100%

### Quality Metrics

- **Test coverage**: ≥80% line, ≥75% branch
- **Test pass rate**: 100% (0 failures)
- **Scope creep**: 0 violations (1 file, 1 method only)
- **Regressions**: 0 (existing tests pass)
- **Performance**: <1ms impact per file

---

## Backward Compatibility Guarantees

### Preserved Behavior

1. ✅ **Priority 1** (Before Capabilities): Unchanged
2. ✅ **Priority 2** (After Quick Start): Unchanged
3. ✅ **Section ordering**: Boundaries still special-cased for placement
4. ✅ **Other sections**: Examples, related_templates handling unchanged
5. ✅ **Frontmatter**: Preservation logic unchanged

### Breaking Changes

❌ **None** - This is a drop-in replacement with no API changes

### Migration Required

❌ **None** - Existing enhanced agent files do NOT need re-enhancement

---

## Definition of Done

### Code Complete

- [ ] Method signature updated (return type `int`)
- [ ] Priority 3 implemented (Before "## Code Examples")
- [ ] Priority 4 implemented (Before "## Related Templates")
- [ ] Priority 5 implemented (Frontmatter + 50 lines)
- [ ] Debug logging added for all 5 tiers
- [ ] Docstring updated with priority order
- [ ] Old `return None` line removed

### Testing Complete

- [ ] Unit tests created (4 tests)
- [ ] Integration test created (1 test)
- [ ] Regression tests pass (existing suite)
- [ ] Coverage ≥80% for modified method
- [ ] All 5 priority tiers tested

### Validation Complete

- [ ] All 12 files have boundaries BEFORE Code Examples
- [ ] All 12 files within lines 40-180 range
- [ ] Zero scope creep (only applier.py modified)
- [ ] Backward compatibility confirmed
- [ ] Visual inspection shows correct placement

### Documentation Complete

- [ ] Method docstring finalized
- [ ] Inline comments added
- [ ] Commit message written
- [ ] No external docs required (internal fix)

---

## Related Tasks

**Upstream**:
- [TASK-STND-0B1A](tasks/backlog/TASK-STND-0B1A-fix-boundaries-placement-agent-enhancer.md) - Original boundaries placement fix (incomplete)
- [TASK-STND-8B4C](tasks/completed/TASK-STND-8B4C/TASK-STND-8B4C-complete-boundaries-implementation.md) - Boundaries content implementation (working)

**Downstream**:
- None (this completes the boundaries placement feature)

**Blocks**:
- None (performance fix, not blocking other work)

**Blocked By**:
- None (can implement immediately)

---

## References

### Files to Review

1. [applier.py:202-237](installer/global/lib/agent_enhancement/applier.py#L202-L237) - Current buggy implementation
2. [TASK-STND-0B1A](tasks/backlog/TASK-STND-0B1A-fix-boundaries-placement-agent-enhancer.md) - Original fix attempt
3. [TASK-STND-8B4C Completion](tasks/completed/TASK-STND-8B4C/completion-summary.md) - Boundaries content implementation
4. [GitHub Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md) - Source of 80-150 line recommendation

### Test Files (12 Enhanced Agents)

All in `~/.agentecflow/templates/fix-boundaries-placement/agents/`:

1. ✅ maui-mvvm-viewmodel-specialist.md (line 68 - CORRECT)
2. ❌ maui-navigation-specialist.md (line 256 - WRONG)
3. ❌ xunit-nsubstitute-testing-specialist.md (line 423 - WRONG)
4. ❌ engine-orchestration-specialist.md (line 394 - WRONG)
5. ❌ realm-operation-executor-specialist.md (line 107 - WRONG ORDER)
6. ❌ erroror-pattern-specialist.md (line 200 - WRONG)
7. ❌ httpclient-api-service-specialist.md (line 105 - WRONG ORDER)
8. ❌ maui-dependency-injection-specialist.md (line 84 - WRONG ORDER)
9. ❌ domain-validation-specialist.md (line 109 - WRONG ORDER)
10. ❌ realm-repository-specialist.md (line 110 - WRONG ORDER)
11. ❌ serilog-structured-logging-specialist.md (line 112 - WRONG ORDER)
12. ❌ riok-mapperly-mapper-specialist.md (line 107 - WRONG ORDER)

---

## Notes

### Why This Fix Works

**Current Problem**:
- Method returns `None` when no "Quick Start" or "Capabilities" found
- Fallback appends boundaries at end of file
- 11/12 files affected

**Solution**:
- **Priority 3**: Catches all files with "## Code Examples" (typical case)
- **Priority 4**: Catches files with "## Related Templates" (less common)
- **Priority 5**: Mathematical fallback (frontmatter + 50 lines ≈ line 60-80)
- **Result**: Method NEVER returns `None`, always finds suitable location

### Why Scope Is Minimal

- **1 file**: `applier.py` (boundaries placement logic)
- **1 method**: `_find_boundaries_insertion_point()` (23 lines added)
- **0 breaking changes**: Existing priority tiers unchanged
- **0 dependencies**: No external libraries needed
- **0 API changes**: Only internal implementation fix

### Why This Is Low Risk

- ✅ **Isolated change**: Single method, clear boundaries
- ✅ **Additive only**: Doesn't modify existing logic, only adds fallbacks
- ✅ **Well-tested**: 5 comprehensive tests cover all scenarios
- ✅ **Reversible**: Single commit revert if issues arise
- ✅ **No data loss**: Agent files can be re-enhanced

---

**Task created by**: Claude Code (architectural analysis + software-architect agent)
**Creation date**: 2025-11-23
**Estimated completion**: 2-3 hours
**Complexity**: 3/10 (LOW)
**Priority**: HIGH (fixes 92% failure rate)
