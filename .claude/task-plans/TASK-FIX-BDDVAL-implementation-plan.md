# Implementation Plan: TASK-FIX-BDDVAL

**Task**: Fix BDD mode RequireKit detection to check for .marker.json extension

**Status**: Ready for implementation
**Complexity**: 2/10 (Simple file detection update)
**Estimated Duration**: 30-45 minutes

---

## Executive Summary

The BDD mode validation currently checks for `~/.agentecflow/require-kit.marker` but RequireKit's installer creates `~/.agentecflow/require-kit.marker.json`. The fix updates the detection logic in `feature_detection.py` to check for the `.json` extension while maintaining backwards compatibility with legacy `.marker` files.

**Good news**: The implementation in `feature_detection.py` is already correct! The bug is only in documentation and error messages.

---

## Root Cause Analysis

### Current State

**feature_detection.py** (lines 74-82):
```python
def is_require_kit_installed(self) -> bool:
    """Check if require-kit is installed."""
    # Check for JSON marker file (new format)
    marker_json = self.agentecflow_home / "require-kit.marker.json"
    if marker_json.exists():
        return True
    # Fallback to old format for backwards compatibility
    marker_old = self.agentecflow_home / "require-kit.marker"
    return marker_old.exists()
```

**Analysis**: ✅ The code is already correct and checks for both formats!

### The Actual Bug

The issue is in **documentation and error messages** that reference the wrong filename:

1. **CLAUDE.md** (line 328, 353):
   - References `~/.agentecflow/require-kit.marker` (wrong)
   - Should reference `~/.agentecflow/require-kit.marker.json` (correct)

2. **task-work.md** (line 3024, 3064):
   - Error messages show wrong filename
   - Installation verification examples use wrong filename

3. **Test files** (test_bdd_mode_validation.py):
   - Tests create `require-kit.marker` (legacy format)
   - Should also test `require-kit.marker.json` (current format)

---

## Files to Modify

### 1. CLAUDE.md (Documentation)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/CLAUDE.md`

**Changes needed**:
- Line 328: Update verification command
- Line 353: Update marker file path reference

**Before**:
```bash
ls ~/.agentecflow/require-kit.marker  # Should exist
```

**After**:
```bash
ls ~/.agentecflow/require-kit.marker.json  # Should exist
```

---

### 2. installer/core/commands/task-work.md (Error Messages)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/task-work.md`

**Changes needed**:
- Line 3024: Update BDD mode prerequisites documentation
- Line 3064: Update verification command in error message

**Before** (line 3064):
```bash
ls ~/.agentecflow/require-kit.marker  # Should exist
```

**After**:
```bash
ls ~/.agentecflow/require-kit.marker.json  # Should exist
```

---

### 3. tests/integration/test_bdd_mode_validation.py (Test Suite)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_bdd_mode_validation.py`

**Changes needed**:
1. **Add test for .marker.json format** (primary)
2. **Keep test for .marker format** (backwards compatibility)
3. **Update error message tests** to reference correct filename

**New tests to add**:

```python
def test_supports_bdd_with_json_marker_file(self, feature_detection, temp_agentecflow_dir):
    """Test supports_bdd() returns True when JSON marker file exists."""
    # Create JSON marker file (current format)
    marker_file = temp_agentecflow_dir / "require-kit.marker.json"
    marker_file.write_text('{"package": "require-kit"}')

    # Verify detection
    assert feature_detection.supports_bdd() is True

def test_supports_bdd_with_legacy_marker_file(self, feature_detection, temp_agentecflow_dir):
    """Test supports_bdd() returns True when legacy marker file exists."""
    # Create legacy marker file (backwards compatibility)
    marker_file = temp_agentecflow_dir / "require-kit.marker"
    marker_file.touch()

    # Verify detection
    assert feature_detection.supports_bdd() is True

def test_json_marker_takes_precedence(self, feature_detection, temp_agentecflow_dir):
    """Test JSON marker is checked before legacy marker."""
    # Create both marker files
    json_marker = temp_agentecflow_dir / "require-kit.marker.json"
    json_marker.write_text('{"package": "require-kit"}')
    legacy_marker = temp_agentecflow_dir / "require-kit.marker"
    legacy_marker.touch()

    # Verify detection (should succeed)
    assert feature_detection.supports_bdd() is True
```

**Error message test to update** (line 100):

```python
def test_requirekit_not_installed_error_message(self):
    """Test error message when RequireKit is not installed."""
    expected_components = [
        "ERROR: BDD mode requires RequireKit installation",
        "RequireKit provides EARS → Gherkin → Implementation workflow",
        "Repository:",
        "https://github.com/requirekit/require-kit",
        "Installation:",
        "cd ~/Projects/require-kit",
        "./installer/scripts/install.sh",
        "Verification:",
        "ls ~/.agentecflow/require-kit.marker.json",  # CHANGED: .json extension
        "Alternative modes:",
        "/task-work TASK-042 --mode=tdd",
        "/task-work TASK-042 --mode=standard",
        "BDD mode is designed for agentic systems",
        "docs/guides/bdd-workflow-for-agentic-systems.md",
    ]
```

---

### 4. .claude/CLAUDE.md (Project Instructions)
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/CLAUDE.md`

**Search for references** to `require-kit.marker` and update to `require-kit.marker.json`.

**Likely locations**:
- BDD workflow section
- RequireKit integration documentation
- Installation verification steps

---

### 5. docs/testing/pre-launch-2025-11-29/BUG-BDD-MODE-VALIDATION.md
**Location**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/testing/pre-launch-2025-11-29/BUG-BDD-MODE-VALIDATION.md`

**Changes needed**:
- Update all references to `require-kit.marker` → `require-kit.marker.json`
- Update verification commands
- Update test case expectations

---

## Implementation Strategy

### Phase 1: Documentation Updates (10 minutes)

1. **Update CLAUDE.md**:
   - Search/replace: `require-kit.marker` → `require-kit.marker.json`
   - Verify context is still accurate

2. **Update .claude/CLAUDE.md**:
   - Same search/replace strategy
   - Check BDD workflow sections

3. **Update task-work.md**:
   - Update error message on line 3064
   - Update prerequisites documentation on line 3024

### Phase 2: Test Suite Updates (15 minutes)

1. **Add new tests**:
   - `test_supports_bdd_with_json_marker_file` (primary format)
   - `test_supports_bdd_with_legacy_marker_file` (backwards compatibility)
   - `test_json_marker_takes_precedence` (precedence verification)

2. **Update existing tests**:
   - Keep legacy marker tests for backwards compatibility
   - Update error message test (line 100)

3. **Update test documentation**:
   - Docstrings should explain JSON vs legacy formats

### Phase 3: Verification (10 minutes)

1. **Run test suite**:
   ```bash
   pytest tests/integration/test_bdd_mode_validation.py -v
   ```

2. **Manual verification**:
   ```bash
   # Test with JSON marker (primary)
   touch ~/.agentecflow/require-kit.marker.json
   # Verify BDD mode recognizes it

   # Test with legacy marker (backwards compatibility)
   rm ~/.agentecflow/require-kit.marker.json
   touch ~/.agentecflow/require-kit.marker
   # Verify BDD mode still recognizes it
   ```

3. **Documentation verification**:
   - Search entire codebase for `require-kit.marker` (without .json)
   - Verify all references are intentional (e.g., backwards compatibility notes)

---

## Test Strategy

### Unit Tests

**File**: `tests/integration/test_bdd_mode_validation.py`

**New test cases**:
1. `test_supports_bdd_with_json_marker_file` - Primary format detection
2. `test_supports_bdd_with_legacy_marker_file` - Backwards compatibility
3. `test_json_marker_takes_precedence` - Precedence verification
4. `test_is_require_kit_installed_with_json_marker` - Installation check
5. `test_marker_file_location_json` - Correct path verification

**Updated test cases**:
1. `test_requirekit_not_installed_error_message` - Update expected filename

**Coverage targets**:
- Line coverage: 100% (feature_detection.py already has full coverage)
- Branch coverage: 100% (both marker formats tested)
- Edge cases: Both formats present, neither present, JSON only, legacy only

### Integration Tests

**Manual test cases**:

1. **JSON marker exists** (primary):
   ```bash
   touch ~/.agentecflow/require-kit.marker.json
   /task-work TASK-XXX --mode=bdd
   # Expected: BDD mode activates
   ```

2. **Legacy marker exists** (backwards compatibility):
   ```bash
   rm ~/.agentecflow/require-kit.marker.json
   touch ~/.agentecflow/require-kit.marker
   /task-work TASK-XXX --mode=bdd
   # Expected: BDD mode activates
   ```

3. **No marker exists** (error case):
   ```bash
   rm ~/.agentecflow/require-kit.marker*
   /task-work TASK-XXX --mode=bdd
   # Expected: Error message with correct filename
   ```

4. **Both markers exist** (precedence):
   ```bash
   touch ~/.agentecflow/require-kit.marker.json
   touch ~/.agentecflow/require-kit.marker
   /task-work TASK-XXX --mode=bdd
   # Expected: BDD mode activates (JSON takes precedence)
   ```

---

## Risk Assessment

### Risks

1. **Backwards Compatibility** (LOW RISK):
   - **Mitigation**: Code already checks both formats
   - **Impact**: Existing installations with legacy markers continue to work

2. **Documentation Inconsistency** (MEDIUM RISK):
   - **Mitigation**: Comprehensive grep search for all references
   - **Impact**: Users may see inconsistent filenames in docs

3. **Test Coverage Gaps** (LOW RISK):
   - **Mitigation**: Add comprehensive test cases for both formats
   - **Impact**: Regressions caught early

4. **Error Message Confusion** (LOW RISK):
   - **Mitigation**: Update all error messages to reference correct filename
   - **Impact**: Users get accurate troubleshooting guidance

### Dependencies

**No external dependencies**:
- Pure documentation and test updates
- `feature_detection.py` already has correct logic
- No breaking changes

**Cross-repository coordination**:
- RequireKit creates `require-kit.marker.json` (already correct)
- GuardKit detects `require-kit.marker.json` (already correct in code)
- Only documentation needs updating

---

## Validation Checklist

### Pre-Implementation
- [x] feature_detection.py logic verified (already correct)
- [x] Current marker file format confirmed (require-kit.marker.json)
- [x] Backwards compatibility requirement confirmed (legacy .marker support)

### During Implementation
- [ ] CLAUDE.md updated (all references to .marker.json)
- [ ] .claude/CLAUDE.md updated (all references to .marker.json)
- [ ] task-work.md error messages updated
- [ ] test_bdd_mode_validation.py tests added
- [ ] Test suite passes (pytest)

### Post-Implementation
- [ ] Grep search confirms no stray references to wrong filename
- [ ] Manual test: JSON marker file detection works
- [ ] Manual test: Legacy marker file detection still works
- [ ] Manual test: Error message shows correct filename
- [ ] Documentation is consistent across all files

---

## Estimated Effort

**Total Duration**: 30-45 minutes

**Breakdown**:
1. Documentation updates (CLAUDE.md, task-work.md): 10 minutes
2. Test suite updates (add new tests, update existing): 15 minutes
3. Verification (run tests, manual checks, grep search): 10 minutes
4. Buffer for unexpected issues: 10 minutes

**Complexity**: 2/10
- Very simple change (documentation + tests)
- No code changes needed (logic already correct)
- Low risk (backwards compatible)
- Well-defined scope

---

## Success Criteria

### Functional Requirements
1. ✅ BDD mode detects `require-kit.marker.json` (primary format)
2. ✅ BDD mode detects `require-kit.marker` (backwards compatibility)
3. ✅ Error messages reference correct filename (.marker.json)
4. ✅ Documentation is consistent across all files

### Quality Gates
1. ✅ All tests pass (pytest)
2. ✅ 100% line coverage maintained (feature_detection.py)
3. ✅ 100% branch coverage (both marker formats tested)
4. ✅ No grep results for incorrect filename (except intentional references)

### User Experience
1. ✅ Users see accurate error messages
2. ✅ Installation verification commands work
3. ✅ Documentation matches actual behavior
4. ✅ Legacy installations continue to work

---

## Notes

### Why This Bug Exists

The bug occurred because:
1. RequireKit installer was updated to use JSON markers (`require-kit.marker.json`)
2. GuardKit's `feature_detection.py` was correctly updated to detect JSON markers
3. **Documentation was not updated** to reflect the new filename
4. Tests only covered the legacy format

### Why The Code is Already Correct

The `feature_detection.py` implementation already has the fix:
```python
# Check for JSON marker file (new format) - PRIMARY
marker_json = self.agentecflow_home / "require-kit.marker.json"
if marker_json.exists():
    return True

# Fallback to old format for backwards compatibility
marker_old = self.agentecflow_home / "require-kit.marker"
return marker_old.exists()
```

This was likely implemented during TASK-BDD-003 but documentation updates were missed.

### Search Patterns for Verification

After implementation, run these searches to verify completeness:

```bash
# Should find ZERO results (except intentional backwards compatibility notes)
grep -r "require-kit\.marker\"" --include="*.md" --include="*.py"

# Should find references to JSON format
grep -r "require-kit\.marker\.json" --include="*.md" --include="*.py"

# Verify error messages are consistent
grep -r "BDD mode requires RequireKit" --include="*.md" -A 10
```

---

## Implementation Order

Execute in this order to ensure smooth implementation:

1. **Documentation first** (low risk, high visibility):
   - Update CLAUDE.md
   - Update .claude/CLAUDE.md
   - Update task-work.md

2. **Tests second** (validation):
   - Add new test cases
   - Update existing test cases
   - Run test suite

3. **Verification last** (quality assurance):
   - Grep search for stray references
   - Manual testing of both formats
   - Documentation review

---

## Rollback Plan

If issues arise, rollback is simple:

1. **Revert documentation changes**:
   ```bash
   git checkout HEAD -- CLAUDE.md
   git checkout HEAD -- .claude/CLAUDE.md
   git checkout HEAD -- installer/core/commands/task-work.md
   ```

2. **Revert test changes**:
   ```bash
   git checkout HEAD -- tests/integration/test_bdd_mode_validation.py
   ```

3. **No code changes** to revert (feature_detection.py unchanged)

**Impact**: Low risk rollback because only documentation and tests are changed.

---

## Related Tasks

**Upstream dependencies**: None (standalone fix)

**Downstream impact**:
- Improves BDD mode user experience
- Fixes documentation inconsistency
- Aligns with RequireKit installer behavior

**Related issues**:
- Originally reported in: `docs/testing/pre-launch-2025-11-29/BUG-BDD-MODE-VALIDATION.md`
- Related to: RequireKit marker file creation (already fixed in RequireKit)

---

## Conclusion

This is a straightforward documentation and test update. The actual detection logic in `feature_detection.py` is already correct and supports both formats. We just need to update documentation and tests to match the current implementation.

**Recommendation**: Proceed with implementation. Low risk, high value fix that improves user experience and documentation accuracy.
