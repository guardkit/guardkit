# Implementation Plan: TASK-PD-002 - Add Loading Instruction Template Generation

## 1. Current State Analysis

### 1.1 Existing Implementation Review

**File: `installer/core/lib/agent_enhancement/applier.py`** (253 lines)

**Current state**:
- Has `apply()` and `generate_diff()` methods for single-file enhancement
- Has `_merge_content()` for merging sections into original content
- Has `remove_sections()` utility method
- **Missing**: All split-file methods from TASK-PD-001

**File: `tests/unit/test_applier_split_methods.py`** (967 lines)

**Current state**:
- Comprehensive test suite already written for split methods
- Tests reference methods that don't exist yet: `create_extended_file()`, `apply_with_split()`, `_categorize_sections()`, `_truncate_quick_start()`, `_build_core_content()`, `_build_extended_content()`, `_format_loading_instruction()`, `_append_section()`, `_format_section_title()`
- Tests import `CORE_SECTIONS` and `EXTENDED_SECTIONS` constants that don't exist
- Tests import `SplitContent` model that may not exist

### 1.2 Gap Analysis

**Critical Finding**: TASK-PD-001 marked as "completed" but implementation doesn't exist in applier.py

**Missing components**:
1. Content categorization constants (`CORE_SECTIONS`, `EXTENDED_SECTIONS`)
2. `SplitContent` model class
3. All 9 methods tested in test suite
4. Loading instruction template logic

**Path forward**: Implement TASK-PD-001 AND TASK-PD-002 together since they're interdependent.

---

## 2. Required Changes

### 2.1 Constants Definition

**Location**: `installer/core/lib/agent_enhancement/applier.py`

**Add at module level** (after imports, before class):

```python
# Content categorization for progressive disclosure
CORE_SECTIONS = [
    'quick_start',           # Truncated to 3 examples
    'boundaries',            # ALWAYS/NEVER/ASK rules
    'capabilities',          # Condensed capabilities list
    'phase_integration',     # Which workflow phases
    'loading_instruction',   # Link to extended file (generated, not input)
]

EXTENDED_SECTIONS = [
    'detailed_examples',     # 20-50 code examples
    'best_practices',        # Full practice explanations
    'anti_patterns',         # Full anti-pattern examples
    'cross_stack',           # Cross-stack considerations
    'mcp_integration',       # MCP integration details
    'troubleshooting',       # Edge cases and debugging
    'technology_specific',   # Per-technology guidance
]
```

### 2.2 Model Class

**Location**: `installer/core/lib/agent_enhancement/models.py`

**Add SplitContent dataclass**:

```python
@dataclass
class SplitContent:
    """Result of split file enhancement."""
    core_path: Path
    extended_path: Optional[Path]
    core_sections: Dict[str, str]
    extended_sections: Dict[str, str]
```

### 2.3 EnhancementApplier Methods

All 9 methods detailed in implementation plan with full docstrings and examples.

---

## 3. Test Strategy

### 3.1 Existing Tests

All tests already written in `tests/unit/test_applier_split_methods.py`

**Coverage targets**:
- Line coverage: ≥80%
- Branch coverage: ≥75%

**Test categories**:
1. `create_extended_file()` - 4 tests
2. `_categorize_sections()` - 6 tests
3. `_truncate_quick_start()` - 5 tests
4. `_build_core_content()` - 3 tests
5. `_build_extended_content()` - 3 tests
6. `apply_with_split()` - 6 tests
7. `_format_loading_instruction()` - 2 tests (TASK-PD-002 focus)
8. `_append_section()` - 3 tests
9. `_format_section_title()` - 3 tests
10. Integration tests - 2 tests
11. Edge cases - 4 tests

**Total**: 41 tests

---

## 4. Implementation Steps

### 4.1 Step 1: Add Constants and Model (5 minutes)

1. Open `installer/core/lib/agent_enhancement/applier.py`
2. Add `CORE_SECTIONS` and `EXTENDED_SECTIONS` constants after imports
3. Open `installer/core/lib/agent_enhancement/models.py`
4. Add `SplitContent` dataclass
5. Update imports in applier.py to include `SplitContent`

### 4.2 Step 2: Add Utility Methods (10 minutes)

Implement in this order (simple to complex):

1. `_format_section_title()` - String formatting
2. `_append_section()` - String concatenation
3. `_format_loading_instruction()` - **TASK-PD-002 focus** - Template generation

### 4.3 Step 3: Add Content Processing Methods (15 minutes)

1. `_truncate_quick_start()` - Code block counting and truncation
2. `_build_extended_content()` - Extended file assembly
3. `_build_core_content()` - Core file assembly (uses _format_loading_instruction)

### 4.4 Step 4: Add Section Categorization (10 minutes)

1. `_categorize_sections()` - Core vs extended split logic

### 4.5 Step 5: Add File Creation Methods (10 minutes)

1. `create_extended_file()` - Extended file writer
2. `apply_with_split()` - Main orchestration method

### 4.6 Step 6: Run Tests (5 minutes)

```bash
python -m pytest tests/unit/test_applier_split_methods.py -v --cov=installer.core.lib.agent_enhancement.applier --cov-report=term
```

### 4.7 Step 7: Fix Test Failures (15 minutes)

Expected failures on first run:
- Import errors (if SplitContent not in right place)
- Formatting mismatches (adjust to match test expectations)
- Edge case handling (malformed input)

### 4.8 Step 8: Validate Loading Instruction Format (5 minutes)

**TASK-PD-002 specific validation**:

```python
# Test loading instruction matches specification
instruction = applier._format_loading_instruction("test-agent")

required_elements = [
    "## Extended Documentation",
    "cat agents/test-agent-ext.md",
    "Detailed code examples",
    "Comprehensive best practices",
    "anti-patterns",
    "Technology-specific",
    "Troubleshooting",
    "progressive disclosure"
]

for element in required_elements:
    assert element in instruction, f"Missing required element: {element}"
```

---

## 5. Risk Assessment

### 5.1 Breaking Changes

**Risk Level**: Low

**Reason**:
- All new methods, no modification of existing `apply()` or `_merge_content()`
- Existing functionality preserved
- Tests validate backward compatibility

**Mitigation**:
- Run existing applier tests to ensure no regression
- Feature can be optionally enabled via `apply_with_split()` vs `apply()`

### 5.2 Edge Cases

**Case 1: Empty enhancement**
- **Behavior**: `apply_with_split()` returns empty core/extended sections
- **Test**: `test_edge_case_empty_enhancement`
- **Handling**: Graceful - no extended file created

**Case 2: All sections empty**
- **Behavior**: No extended file created
- **Test**: `test_edge_case_all_empty_sections`
- **Handling**: Graceful - core file unchanged

**Case 3: No code blocks in Quick Start**
- **Behavior**: No truncation performed
- **Test**: `test_edge_case_quick_start_no_code_blocks`
- **Handling**: Return original content unchanged

**Case 4: Malformed code blocks**
- **Behavior**: Best-effort processing
- **Test**: `test_edge_case_malformed_code_blocks`
- **Handling**: Don't crash, return processed string

**Case 5: Unknown section names**
- **Behavior**: Categorize as extended with warning
- **Test**: `test_categorize_sections_unknown_section_as_extended`
- **Handling**: Log warning, include in extended sections

### 5.3 Backward Compatibility

**Compatibility Status**: 100% backward compatible

**Existing methods unchanged**:
- `apply()` - Single-file enhancement (existing behavior)
- `generate_diff()` - Diff generation (existing behavior)
- `remove_sections()` - Section removal (existing behavior)
- `_merge_content()` - Content merging (existing behavior)

**New methods additive only**:
- `apply_with_split()` - New opt-in method
- All helper methods private (`_` prefix)

---

## 6. Key Decision: Loading Instruction Format

### 6.1 Specification from TASK-PD-002

```markdown
## Extended Reference

Before generating code or performing detailed implementation, load the extended reference:

```bash
cat agents/{agent-name}-ext.md
```

**Extended file contains**:
- 30+ detailed code examples
- Template best practices with full explanations
- Common anti-patterns to avoid
- Technology-specific guidance
- MCP integration details
- Troubleshooting scenarios
```

### 6.2 Implementation Decision

**Chosen format** (in `_format_loading_instruction()`):

```markdown
## Extended Documentation

Before generating code or performing detailed implementation, load the extended reference:

```bash
cat agents/{agent-name}-ext.md
```

**Extended file contains**:
- Detailed code examples with full context
- Comprehensive best practices with explanations
- Common anti-patterns to avoid with solutions
- Technology-specific implementation guidance
- Troubleshooting scenarios and edge cases

This extended documentation follows progressive disclosure principles to keep the core agent file focused while providing comprehensive guidance when needed.
```

**Differences from spec**:
1. Header: "Extended Documentation" vs "Extended Reference" (clearer intent)
2. Bullet points: More descriptive (e.g., "with solutions", "with explanations")
3. Footer: Added progressive disclosure explanation
4. Removed "30+ detailed code examples" (varies by agent)
5. Removed "MCP integration details" (not always applicable)

**Rationale**:
- "Documentation" more accurate than "Reference"
- Descriptive bullets set clearer expectations
- Footer explains the "why" to Claude
- Dynamic content means can't promise "30+"
- MCP integration is specialist-specific

---

## 7. Success Criteria

### 7.1 Implementation Complete

- [ ] All 9 methods implemented
- [ ] Constants (`CORE_SECTIONS`, `EXTENDED_SECTIONS`) defined
- [ ] `SplitContent` model created
- [ ] Loading instruction template implemented (TASK-PD-002)
- [ ] Loading instruction includes all required elements
- [ ] All 41 unit tests passing
- [ ] Line coverage ≥80%
- [ ] Branch coverage ≥75%
- [ ] No regression in existing tests
- [ ] Integration test passes

### 7.2 Loading Instruction Quality (TASK-PD-002)

- [ ] Loading instruction has correct structure
- [ ] Includes explicit `cat agents/{filename}` command
- [ ] Lists all extended content types
- [ ] References progressive disclosure principles
- [ ] Formatting matches specification

---

## 8. Estimated Duration

**Total**: 1.5-2 hours

| Step | Duration | Notes |
|------|----------|-------|
| 1. Add constants/model | 5 min | Simple additions |
| 2. Utility methods | 10 min | Including `_format_loading_instruction` |
| 3. Content processing | 15 min | `_truncate_quick_start`, `_build_*_content` |
| 4. Categorization | 10 min | `_categorize_sections` |
| 5. File creation | 10 min | `create_extended_file`, `apply_with_split` |
| 6. Run tests | 5 min | Initial test run |
| 7. Fix failures | 15 min | Address test failures |
| 8. Validate loading instruction | 5 min | TASK-PD-002 specific |
| 9. Integration test | 10 min | End-to-end validation |
| **Buffer** | 15 min | Unexpected issues |

---

## 9. Files Modified

### 9.1 Primary Changes

**File**: `installer/core/lib/agent_enhancement/applier.py`

- Add `CORE_SECTIONS` constant (7 items)
- Add `EXTENDED_SECTIONS` constant (7 items)
- Add 9 new methods (~150 lines total)
- Import `SplitContent` from models

**File**: `installer/core/lib/agent_enhancement/models.py`

- Add `SplitContent` dataclass (~10 lines)

### 9.2 Test Files

**File**: `tests/unit/test_applier_split_methods.py`

- No changes needed (tests already written)
- Run to validate implementation

---

## Summary

This implementation plan delivers both TASK-PD-001 (split file methods) and TASK-PD-002 (loading instruction template) as an integrated solution. The `_format_loading_instruction()` method is the centerpiece of TASK-PD-002, providing a standardized template that instructs Claude to load extended documentation before detailed implementation work.

All code is test-driven (41 tests pre-written), backward compatible (no changes to existing methods), and follows progressive disclosure principles to reduce cognitive load while maintaining comprehensive guidance.

**Key deliverable for TASK-PD-002**: The `_format_loading_instruction()` method generates a standardized Markdown section with explicit `cat` command, bullet list of extended content, and progressive disclosure rationale.
