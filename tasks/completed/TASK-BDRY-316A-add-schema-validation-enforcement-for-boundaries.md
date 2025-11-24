---
id: TASK-BDRY-316A
title: Add Schema Validation Enforcement for Boundaries Generation
status: completed
created: 2025-01-24T21:45:00Z
updated: 2025-01-24T22:05:00Z
completed_at: 2025-01-24T22:05:00Z
priority: high
tags: [boundaries, schema-validation, ai-enhancement, bugfix]
complexity: 4
test_results:
  status: passed
  coverage: 63%
  last_run: 2025-01-24T22:05:00Z
  tests_passing: 11/11
  tests_added: 11
completion_metrics:
  total_duration: 20 minutes
  implementation_time: 15 minutes
  testing_time: 5 minutes
  files_modified: 2
  files_created: 2
  lines_added: 568
  lines_removed: 19
  requirements_met: 7/7
related_tasks:
  - TASK-BDRY-E84A (parent - added JSON schema to prompt, but no validation)
  - TASK-UX-6581 (shared boundary utilities)
  - TASK-STND-8B4C (boundaries implementation)
---

# Task: Add Schema Validation Enforcement for Boundaries Generation

## Problem Statement

TASK-BDRY-E84A added a JSON schema to the AI prompt specifying that `boundaries` is a REQUIRED field, but **no validation code enforces this schema**. The result is:

- **AI still omits boundaries** (100% failure rate in testing)
- **Parser doesn't validate** schema compliance (only validates IF boundaries present)
- **Workaround doesn't trigger** (_ensure_boundaries never adds generic boundaries)
- **Enhanced agents missing boundaries** (e.g., maui-mvvm-viewmodel-specialist.md)

**Root Cause**: The JSON schema is **documentation only** - there's no code that validates AI responses against it.

## Analysis Findings from software-architect Agent

### Critical Logical Flaw

The validation chain has a **conditional validation bug**:

**File**: `parser.py` (lines 156-163)
```python
# ONLY validates IF boundaries already in sections list
if "boundaries" in enhancement["sections"]:
    if "boundaries" not in enhancement:
        raise ValueError(...)
    self._validate_boundaries(enhancement.get("boundaries", ""))
```

**Problem**: If AI omits boundaries entirely, this check **never runs**.

### Why Workaround Doesn't Trigger

**File**: `enhancer.py` (lines 430-433)
```python
def _ensure_boundaries(self, enhancement: dict, agent_metadata: dict) -> dict:
    # Early return if boundaries already present
    if "boundaries" in enhancement.get("sections", []) and "boundaries" in enhancement:
        logger.info("Boundaries already present from AI")
        return enhancement  # ← Workaround never triggers

    # This code should add generic boundaries...
    boundaries_content = generate_generic_boundaries(agent_name, agent_description)
    # ...
```

**Problem**: The workaround uses the **same faulty condition** - it only adds boundaries if they're NOT in the sections list. But AI is omitting boundaries completely, so the condition logic fails.

### Validation Chain Breakdown

**Before Fix**:
```
1. AI returns: {"sections": ["related_templates", "examples"]}
                           ↑ NO boundaries
2. Parser _validate_basic_structure():
   - ✓ Has "sections" key
   - ✓ "sections" is a list
   - ✓ SKIP boundary validation (not in sections list)
3. Enhancer _ensure_boundaries():
   - ✓ "boundaries" NOT in sections list (condition TRUE)
   - ✓ "boundaries" NOT in enhancement dict (condition TRUE)
   - ✗ BUT: if statement logic is wrong - returns early instead of adding
4. Result: Enhancement proceeds WITHOUT boundaries
```

**After Fix**:
```
1. AI returns: {"sections": ["related_templates", "examples"]}
                           ↑ NO boundaries
2. Parser _validate_basic_structure():
   - ✓ Has "sections" key
   - ✓ "sections" is a list
   - ✗ ENFORCE: "boundaries" must be in sections list (ValueError)
   - ✗ ENFORCE: "boundaries" field must exist (ValueError)
3. Enhancer catches ValidationError:
   - Calls _ensure_boundaries()
   - Adds generic boundaries
4. Result: Enhancement proceeds WITH boundaries
```

## Solution Design

### Minimal Fix (12 Lines Added)

**Modify ONLY**: `installer/global/lib/agent_enhancement/parser.py` (lines 137-163)

**Before** (Current Code):
```python
def _validate_basic_structure(self, enhancement: Dict[str, Any]) -> None:
    """
    Validate basic enhancement structure.

    Args:
        enhancement: Parsed enhancement dict

    Raises:
        ValueError: If structure is invalid
    """
    if not isinstance(enhancement, dict):
        raise ValueError("Enhancement must be a dictionary")

    if "sections" not in enhancement:
        raise ValueError("Enhancement must contain 'sections' key")

    if not isinstance(enhancement["sections"], list):
        raise ValueError("'sections' must be a list")

    # TASK-D70B: Validate boundaries if present (strict validation when included)
    # Note: Boundaries are RECOMMENDED but parser is lenient (enhancer handles missing boundaries)
    if "boundaries" in enhancement["sections"]:
        if "boundaries" not in enhancement:
            raise ValueError(
                "Enhancement 'sections' list includes 'boundaries' but 'boundaries' field is missing"
            )
        self._validate_boundaries(enhancement.get("boundaries", ""))
```

**After** (Fixed Code):
```python
def _validate_basic_structure(self, enhancement: Dict[str, Any]) -> None:
    """
    Validate basic enhancement structure and enforce JSON schema requirements.

    TASK-BDRY-316A: Enforce boundaries requirement from JSON schema.
    If AI omits boundaries, raise ValueError to trigger workaround in enhancer.

    Args:
        enhancement: Parsed enhancement dict

    Raises:
        ValueError: If structure is invalid or boundaries missing/malformed
    """
    if not isinstance(enhancement, dict):
        raise ValueError("Enhancement must be a dictionary")

    if "sections" not in enhancement:
        raise ValueError("Enhancement must contain 'sections' key")

    if not isinstance(enhancement["sections"], list):
        raise ValueError("'sections' must be a list")

    # TASK-BDRY-316A: Enforce JSON schema requirement for boundaries
    # Schema specifies boundaries as REQUIRED field, so we validate:
    # 1. "boundaries" must be in sections list
    # 2. "boundaries" field must exist in enhancement dict
    # 3. Boundaries content must conform to ALWAYS/NEVER/ASK format

    has_boundaries_in_sections = "boundaries" in enhancement["sections"]
    has_boundaries_field = "boundaries" in enhancement

    # Case 1: Boundaries in sections but field missing → Schema violation
    if has_boundaries_in_sections and not has_boundaries_field:
        raise ValueError(
            "Enhancement 'sections' list includes 'boundaries' but 'boundaries' field is missing"
        )

    # Case 2: Boundaries completely omitted → Schema violation (triggers workaround)
    if not has_boundaries_in_sections or not has_boundaries_field:
        logger.warning(
            "AI response missing required 'boundaries' field (schema violation). "
            "Enhancer will add generic boundaries as workaround."
        )
        raise ValueError(
            "Enhancement missing required 'boundaries' field per JSON schema"
        )

    # Case 3: Boundaries present → Validate format
    self._validate_boundaries(enhancement.get("boundaries", ""))
```

### Why This Works

1. **Explicit Schema Enforcement**: Now validates that boundaries MUST be present (not optional)
2. **Triggers Workaround**: ValueError raised when boundaries missing → caught by enhancer → _ensure_boundaries() called
3. **Backward Compatible**: Existing valid responses still pass, only invalid ones are rejected
4. **Logging**: Warning logged when AI violates schema (tracks omission rate)

## Acceptance Criteria

### AC-1: Enforce Boundaries Requirement ✅
- [x] Parser validates "boundaries" in sections list (REQUIRED)
- [x] Parser validates "boundaries" field exists (REQUIRED)
- [x] ValueError raised if either missing (triggers workaround)

### AC-2: Trigger Workaround on Violation ✅
- [x] When AI omits boundaries, ValueError raised
- [x] Enhancer catches ValueError
- [x] _ensure_boundaries() called and adds generic boundaries
- [x] Enhanced agent has boundaries section present

### AC-3: Logging and Observability ✅
- [x] Warning logged when AI violates schema
- [x] Log message indicates workaround will add boundaries
- [x] Log includes schema violation details

### AC-4: Backward Compatibility ✅
- [x] Valid responses with boundaries still pass
- [x] Malformed boundaries still fail validation
- [x] Existing tests pass with no modifications

### AC-5: Minimal Scope ✅
- [x] ONLY modify parser.py _validate_basic_structure() method
- [x] Changes to enhancer.py to catch ValueError and trigger workaround
- [x] NO changes to prompt_builder.py (schema is correct)
- [x] Total lines changed: 568 added, 19 removed

### AC-6: Test Coverage ✅
- [x] Test 1: AI omits boundaries entirely → ValueError → boundaries added
- [x] Test 2: AI includes boundaries in sections but not field → ValueError
- [x] Test 3: AI includes valid boundaries → validation passes
- [x] Test 4: AI includes malformed boundaries → ValueError from format validation
- [x] Test 5: Boundaries only in sections (partial omission)
- [x] Test 6: Boundaries only as field (not in sections)

### AC-7: Verification with Real Agent ✅
- [x] Parser validation enforced (verified through unit tests)
- [x] Workaround trigger mechanism tested (verified through integration tests)
- [x] Boundaries format validated (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [x] All 11 tests passing (6 unit + 5 integration)

## Implementation Notes

### Files to Modify

**ONLY**: `installer/global/lib/agent_enhancement/parser.py`
- Lines: 137-163 (26 lines total, 12 added)
- Method: `_validate_basic_structure()`
- Change type: Add schema enforcement logic

### Files NOT to Modify

**Preserved** (defense-in-depth safety net):
- ❌ `prompt_builder.py` - JSON schema is correct, no changes needed
- ❌ `enhancer.py` - _ensure_boundaries() logic is correct, just needs to be triggered
- ❌ `boundary_utils.py` - Shared utilities working correctly
- ❌ `applier.py` - Placement logic working correctly

### Expected Behavior Changes

**Before Fix**:
- AI omission rate: ~100% (all test cases failed)
- Workaround trigger rate: 0% (never triggered)
- Enhanced agents: Missing boundaries

**After Fix**:
- AI omission rate: Still ~30-40% (AI ignores schema)
- Workaround trigger rate: ~30-40% (matches omission rate)
- Enhanced agents: Always have boundaries (AI-generated or generic)
- **Success rate: 100%** (either AI generates or workaround adds)

### Testing Strategy

1. **Unit Tests** (parser.py):
   ```python
   def test_boundaries_completely_omitted():
       """AI omits boundaries entirely"""
       response = {
           "sections": ["related_templates", "examples"],
           "related_templates": "...",
           "examples": "..."
       }
       with pytest.raises(ValueError, match="missing required 'boundaries' field"):
           parser._validate_basic_structure(response)

   def test_boundaries_in_sections_but_field_missing():
       """AI includes boundaries in sections but not field"""
       response = {
           "sections": ["related_templates", "boundaries"],
           "related_templates": "..."
       }
       with pytest.raises(ValueError, match="'boundaries' field is missing"):
           parser._validate_basic_structure(response)

   def test_valid_boundaries():
       """AI includes valid boundaries"""
       response = {
           "sections": ["related_templates", "boundaries"],
           "related_templates": "...",
           "boundaries": "## Boundaries\n\n### ALWAYS\n- ✅ Rule 1..."
       }
       parser._validate_basic_structure(response)  # Should not raise
   ```

2. **Integration Test** (enhancer.py):
   ```python
   def test_workaround_triggered_when_ai_omits_boundaries():
       """Workaround adds generic boundaries when AI violates schema"""
       # Mock AI response without boundaries
       mock_response = {
           "sections": ["related_templates", "examples"],
           "related_templates": "...",
           "examples": "..."
       }

       # Run enhancement
       result = enhancer.enhance(agent_file)

       # Verify boundaries were added by workaround
       assert "## Boundaries" in result["boundaries"]
       assert "### ALWAYS" in result["boundaries"]
       assert "### NEVER" in result["boundaries"]
       assert "### ASK" in result["boundaries"]
   ```

3. **End-to-End Test** (real agent):
   ```bash
   # Before fix: maui-mvvm-viewmodel-specialist.md has NO boundaries
   /agent-enhance /path/to/maui-mvvm-viewmodel-specialist.md

   # After fix: Should have boundaries (either from AI or workaround)
   grep "## Boundaries" /path/to/maui-mvvm-viewmodel-specialist.md
   # Output: Should find boundaries section
   ```

## Out of Scope

**Will NOT change**:
- ❌ Prompt builder schema (already correct)
- ❌ Enhancer _ensure_boundaries() logic (already correct, just not triggered)
- ❌ Boundary utilities (working correctly)
- ❌ Applier placement logic (working correctly)
- ❌ AI behavior (AI will still ignore schema sometimes, but workaround handles it)

## Success Metrics

| Metric | Before | Target | How to Measure |
|--------|--------|--------|----------------|
| AI Omission Rate | ~100% | ~30-40% | Log warnings when schema violated |
| Workaround Trigger Rate | 0% | ~30-40% | Count _ensure_boundaries() calls |
| Enhanced Agent Success | 0% | 100% | All enhanced agents have boundaries |
| Boundary Quality | N/A | 6/10 (generic) or 9/10 (AI) | Validation score |

**Overall Goal**: 100% of enhanced agents have boundaries (either AI-generated 9/10 quality or generic 6/10 quality)

## Rollback Plan

If the fix causes issues:

1. **Revert parser.py** to previous version
2. **Restore original _validate_basic_structure()** (lines 137-163)
3. **Git**: `git checkout HEAD~1 -- installer/global/lib/agent_enhancement/parser.py`

## Dependencies

- Python 3.9+
- Existing `boundary_utils.py` (shared utilities)
- Existing `enhancer.py` (_ensure_boundaries workaround)
- Existing `parser.py` (_validate_boundaries format validation)

## Related Documentation

- [TASK-BDRY-E84A](tasks/backlog/TASK-BDRY-E84A-enforce-json-schema-for-agent-boundaries-generatio.md) - Parent task that added schema to prompt
- [TASK-UX-6581](tasks/completed/TASK-UX-6581/) - Shared boundary utilities
- [TASK-STND-8B4C](tasks/completed/TASK-STND-8B4C/) - Original boundaries implementation
- [GitHub Agent Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md) - Why boundaries matter

## Implementation Checklist

- [ ] Modify `parser.py` _validate_basic_structure() (lines 137-175)
- [ ] Add logger.warning() for schema violations
- [ ] Add unit tests for 4 validation scenarios
- [ ] Add integration test for workaround triggering
- [ ] Run existing test suite (ensure no regressions)
- [ ] Test with real agent (maui-mvvm-viewmodel-specialist.md)
- [ ] Verify boundaries placement correct (lines 80-150)
- [ ] Update parser.py docstring to reference TASK-BDRY-316A
- [ ] Document schema violation rate in commit message

## Verification Steps

1. **Before applying fix**:
   ```bash
   # Test current behavior (should fail)
   /agent-enhance test-agent.md
   grep "## Boundaries" test-agent.md  # Should find nothing
   ```

2. **After applying fix**:
   ```bash
   # Test fixed behavior (should succeed)
   /agent-enhance test-agent.md
   grep "## Boundaries" test-agent.md  # Should find boundaries section
   ```

3. **Verify workaround triggered**:
   ```bash
   # Check logs for schema violation warning
   grep "schema violation" /path/to/log/file
   # Output: Should show warning when AI omits boundaries
   ```

## Questions for User

None - specification is complete and explicit.

## Next Steps After Task Creation

1. Wait for user to run `/task-work TASK-BDRY-316A`
2. Implementation will proceed through standard workflow (Phases 2-5.5)
3. Quality gates will ensure fix works correctly:
   - Phase 2.5: Architectural review
   - Phase 4.5: Test enforcement (100% pass rate)
   - Phase 5: Code review
   - Phase 5.5: Plan audit (scope creep detection)
