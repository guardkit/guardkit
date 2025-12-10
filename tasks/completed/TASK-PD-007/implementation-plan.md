# Phase 2: Implementation Planning - TASK-PD-007

## Task Analysis

**Task ID**: TASK-PD-007
**Title**: Update TemplateClaude model with split fields
**Complexity**: 4/10 (Low-Moderate)
**Priority**: High

## Current State Analysis

### What Already Exists (from TASK-PD-005)

**TemplateSplitOutput** - ✅ FULLY IMPLEMENTED (lines 310-376 in models.py)
- Has fields: `core_content`, `patterns_content`, `reference_content`, `generated_at`
- Has methods:
  - `get_core_size()` → int
  - `get_patterns_size()` → int
  - `get_reference_size()` → int
  - `get_total_size()` → int
  - `get_reduction_percent()` → float
  - `validate_size_constraints()` → tuple[bool, Optional[str]]
- **Note**: Field names differ from task spec (`core_content` vs `core`, etc.) but functionally complete
- Used successfully by orchestrator (TASK-PD-006)

### What Already Works (from TASK-PD-006)

**Orchestrator Integration** - ✅ COMPLETED
- `ClaudeMdGenerator.generate_split()` method exists and works
- Writes to `docs/patterns/README.md` and `docs/reference/README.md`
- All tests passing (11/11)
- Size validation working

### What the Task Specification Asks For

1. **Extend TemplateClaude** with optional split fields:
   - `split_output: bool = False`
   - `loading_instructions: Optional[str] = None`
   - `patterns_path: Optional[str] = None`
   - `reference_path: Optional[str] = None`

2. **Add to_core_markdown() method** to TemplateClaude

3. **Create TemplateSplitOutput** (ALREADY EXISTS!)

4. **Create TemplateSplitMetadata** dataclass

## Gap Analysis

### What's Actually Missing?

1. **TemplateClaude Extensions** - NOT IMPLEMENTED
   - Current TemplateClaude (lines 114-159) has no split-awareness
   - No optional split fields
   - No `to_core_markdown()` method

2. **TemplateSplitMetadata** - NOT IMPLEMENTED
   - Current `TemplateSplitOutput` has size methods but no separate metadata object
   - Task spec wants metadata as separate dataclass

### Critical Question: Is This Necessary?

**Current Implementation Works Without Modifying TemplateClaude:**
- `generate_split()` returns `TemplateSplitOutput` directly
- Orchestrator consumes `TemplateSplitOutput` successfully
- Size validation happens in `TemplateSplitOutput.validate_size_constraints()`

**When Would TemplateClaude Extensions Matter?**
- If we need to **store split metadata in TemplateClaude objects**
- If we need to **serialize split config to manifest.json**
- If we need to **toggle between split and single-file modes at template level**

**Current Architecture Doesn't Need It:**
- Split/single mode is decided at **orchestrator level** (phase 6)
- `ClaudeMdGenerator` has both `generate()` (single-file) and `generate_split()` (split)
- No need to store split metadata in the model

## Recommendation: Minimal Implementation

### Option A: Follow Original Intent (Recommended)

**Rationale**: The original task spec was written before TASK-PD-005 implementation details were known. Now that we see how it actually works, we can implement what's genuinely needed.

**What to Implement:**

1. **Add TemplateSplitMetadata** (Useful for structured reporting)
   - Stores size metrics as structured data
   - Enables easier validation reporting
   - Can be returned alongside split output

2. **Skip TemplateClaude extensions** (Not needed in current architecture)
   - Split/single decision happens at orchestrator level
   - No need to store split metadata in TemplateClaude
   - Would create confusion about source of truth

3. **Update TemplateSplitOutput** (Enhance existing implementation)
   - Add `metadata: TemplateSplitMetadata` field
   - Keep existing field names (`core_content`, etc.) for backward compatibility
   - Enhance `validate_size_constraints()` to populate metadata

### Option B: Full Spec Implementation (Not Recommended)

**Why Not:**
- Breaking changes to working TASK-PD-005 and TASK-PD-006 code
- Architectural confusion (two sources of truth for split output)
- No clear benefit over current implementation
- Risk: Regression in working functionality

## Implementation Plan (Option A)

### File: `installer/core/lib/template_generator/models.py`

#### Change 1: Add TemplateSplitMetadata Class

**Location**: After `TemplateSplitOutput` (around line 377)

**Purpose**: Structured metadata for split output validation and reporting

```python
class TemplateSplitMetadata(BaseModel):
    """Metadata for split template output.

    Provides structured size metrics and validation results for
    progressive disclosure split CLAUDE.md generation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "core_size_bytes": 8192,
                "patterns_size_bytes": 5120,
                "reference_size_bytes": 7168,
                "total_size_bytes": 20480,
                "reduction_percent": 60.0,
                "generated_at": "2025-12-05T10:30:00Z",
                "validation_passed": True,
                "validation_errors": []
            }
        }
    )

    core_size_bytes: int = Field(description="Size of core CLAUDE.md content in bytes")
    patterns_size_bytes: int = Field(description="Size of patterns content in bytes")
    reference_size_bytes: int = Field(description="Size of reference content in bytes")
    total_size_bytes: int = Field(description="Total size of all content in bytes")
    reduction_percent: float = Field(ge=0.0, le=100.0, description="Percentage reduction from total to core")
    generated_at: str = Field(description="ISO 8601 timestamp of generation")
    validation_passed: bool = Field(description="Whether size validation passed")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors if any")
```

#### Change 2: Enhance TemplateSplitOutput

**Location**: Update existing `TemplateSplitOutput` class (lines 310-376)

**Purpose**: Add optional metadata field and factory method

```python
class TemplateSplitOutput(BaseModel):
    """Split CLAUDE.md output for progressive loading

    This model supports the transitional state where templates can generate
    both single-file (legacy) and split-file (new) CLAUDE.md outputs. Both
    formats remain fully supported to ensure backward compatibility.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "core_content": "# How to Load This Template\n...",
                "patterns_content": "# Patterns and Best Practices\n...",
                "reference_content": "# Code Examples\n...",
                "generated_at": "2025-12-05T10:30:00Z",
                "metadata": {
                    "core_size_bytes": 8192,
                    "total_size_bytes": 20480,
                    "reduction_percent": 60.0,
                    "validation_passed": True
                }
            }
        }
    )

    core_content: str = Field(description="Core CLAUDE.md content (≤10KB)")
    patterns_content: str = Field(description="Patterns and best practices section")
    reference_content: str = Field(description="Reference and examples section")
    generated_at: str = Field(description="ISO 8601 timestamp")
    metadata: Optional[TemplateSplitMetadata] = Field(None, description="Optional size and validation metadata")

    # Keep existing methods (unchanged)
    def get_core_size(self) -> int: ...
    def get_patterns_size(self) -> int: ...
    def get_reference_size(self) -> int: ...
    def get_total_size(self) -> int: ...
    def get_reduction_percent(self) -> float: ...

    def validate_size_constraints(self) -> tuple[bool, Optional[str]]:
        """Validate that core content meets size constraints

        Returns:
            Tuple of (is_valid, error_message)
            error_message is None if valid
        """
        core_size = self.get_core_size()
        max_core_size = 10 * 1024  # 10KB in bytes

        if core_size > max_core_size:
            return False, f"Core content exceeds 10KB limit: {core_size / 1024:.2f}KB"

        return True, None

    def generate_metadata(self) -> TemplateSplitMetadata:
        """Generate metadata from current content.

        Returns:
            TemplateSplitMetadata with size metrics and validation results
        """
        is_valid, error_msg = self.validate_size_constraints()

        return TemplateSplitMetadata(
            core_size_bytes=self.get_core_size(),
            patterns_size_bytes=self.get_patterns_size(),
            reference_size_bytes=self.get_reference_size(),
            total_size_bytes=self.get_total_size(),
            reduction_percent=self.get_reduction_percent(),
            generated_at=self.generated_at,
            validation_passed=is_valid,
            validation_errors=[error_msg] if error_msg else []
        )
```

### Why This Approach?

1. **Minimal Changes**: Only adds optional metadata field to existing working model
2. **Backward Compatible**: Existing code continues to work (metadata is optional)
3. **No Breaking Changes**: TASK-PD-005 and TASK-PD-006 code unchanged
4. **Useful Addition**: Structured metadata enables better validation reporting
5. **DRY**: Reuses existing size calculation methods

### What We're NOT Implementing

1. **TemplateClaude extensions** - Not needed in current architecture
   - Split/single mode decided at orchestrator level
   - No benefit to storing split metadata in TemplateClaude
   - Would create confusion about source of truth

2. **to_core_markdown() method** - Not needed
   - `ClaudeMdGenerator.generate_split()` already produces core content
   - Adding this to TemplateClaude would duplicate logic
   - Would violate SRP (model shouldn't know how to render itself differently)

## Testing Strategy

### Unit Tests (test_models.py)

**File**: `tests/lib/test_models.py`

#### Test 1: TemplateSplitMetadata Creation
```python
def test_template_split_metadata_creation():
    """Test TemplateSplitMetadata creation and validation."""
    metadata = TemplateSplitMetadata(
        core_size_bytes=8192,
        patterns_size_bytes=5120,
        reference_size_bytes=7168,
        total_size_bytes=20480,
        reduction_percent=60.0,
        generated_at="2025-12-05T10:30:00Z",
        validation_passed=True,
        validation_errors=[]
    )

    assert metadata.core_size_bytes == 8192
    assert metadata.total_size_bytes == 20480
    assert metadata.reduction_percent == 60.0
    assert metadata.validation_passed is True
    assert len(metadata.validation_errors) == 0
```

#### Test 2: Metadata with Validation Errors
```python
def test_template_split_metadata_with_errors():
    """Test TemplateSplitMetadata with validation errors."""
    metadata = TemplateSplitMetadata(
        core_size_bytes=12288,  # 12KB - over limit
        patterns_size_bytes=5120,
        reference_size_bytes=7168,
        total_size_bytes=24576,
        reduction_percent=50.0,
        generated_at="2025-12-05T10:30:00Z",
        validation_passed=False,
        validation_errors=["Core content exceeds 10KB limit: 12.00KB"]
    )

    assert metadata.validation_passed is False
    assert len(metadata.validation_errors) == 1
    assert "exceeds 10KB limit" in metadata.validation_errors[0]
```

#### Test 3: Generate Metadata from Split Output
```python
def test_template_split_output_generate_metadata():
    """Test metadata generation from TemplateSplitOutput."""
    output = TemplateSplitOutput(
        core_content="# Core\n" * 100,
        patterns_content="# Patterns\n" * 500,
        reference_content="# Reference\n" * 500,
        generated_at="2025-12-05T10:30:00Z"
    )

    metadata = output.generate_metadata()

    assert metadata.core_size_bytes == output.get_core_size()
    assert metadata.total_size_bytes == output.get_total_size()
    assert metadata.reduction_percent == output.get_reduction_percent()
    assert metadata.validation_passed is True  # Core is small enough
    assert metadata.generated_at == output.generated_at
```

#### Test 4: Metadata Populated in Split Output
```python
def test_template_split_output_with_metadata():
    """Test TemplateSplitOutput with pre-populated metadata."""
    metadata = TemplateSplitMetadata(
        core_size_bytes=8192,
        patterns_size_bytes=5120,
        reference_size_bytes=7168,
        total_size_bytes=20480,
        reduction_percent=60.0,
        generated_at="2025-12-05T10:30:00Z",
        validation_passed=True,
        validation_errors=[]
    )

    output = TemplateSplitOutput(
        core_content="# Core\n" * 100,
        patterns_content="# Patterns\n" * 500,
        reference_content="# Reference\n" * 500,
        generated_at="2025-12-05T10:30:00Z",
        metadata=metadata
    )

    assert output.metadata is not None
    assert output.metadata.validation_passed is True
    assert output.metadata.core_size_bytes == 8192
```

#### Test 5: Backward Compatibility (Optional Metadata)
```python
def test_template_split_output_backward_compatible():
    """Test that metadata is optional for backward compatibility."""
    output = TemplateSplitOutput(
        core_content="# Core\n" * 100,
        patterns_content="# Patterns\n" * 500,
        reference_content="# Reference\n" * 500,
        generated_at="2025-12-05T10:30:00Z"
        # metadata not provided
    )

    assert output.metadata is None
    # Existing methods still work
    assert output.get_core_size() > 0
    assert output.get_total_size() > 0

    # Can generate metadata on demand
    metadata = output.generate_metadata()
    assert metadata.validation_passed is True
```

### Integration Test (Optional - Already Covered by TASK-PD-006)

Since TASK-PD-006 tests already validate the orchestrator's use of `TemplateSplitOutput`, we don't need additional integration tests. The metadata field is optional, so existing tests will continue to pass.

## Files to Modify

### Primary Changes

1. **installer/core/lib/template_generator/models.py**
   - Add `TemplateSplitMetadata` class (~35 lines)
   - Update `TemplateSplitOutput` class:
     - Add `metadata: Optional[TemplateSplitMetadata]` field
     - Add `generate_metadata()` method (~15 lines)
     - Update model_config example

### Test Files

2. **tests/lib/test_models.py**
   - Add 5 test functions (~80 lines total)

### Documentation Updates (Optional)

3. **installer/core/commands/template-create.md** (if needed)
   - Document metadata structure in output

## Estimated Effort

**Original Estimate**: 0.5 days (4 hours)

**Revised Estimate**: 2 hours

**Breakdown**:
- TemplateSplitMetadata implementation: 30 minutes
- TemplateSplitOutput enhancement: 30 minutes
- Unit tests: 45 minutes
- Integration validation: 15 minutes

**Reason for Reduction**:
- No need to modify TemplateClaude (architectural decision)
- No need for to_core_markdown() method (already exists in generator)
- Simpler scope than original task specification
- Most complexity already handled by TASK-PD-005

## Lines of Code Estimate

- **Models**: ~50 new lines (TemplateSplitMetadata + enhancements)
- **Tests**: ~80 new lines (5 test functions)
- **Total**: ~130 new lines

## Dependencies

**Completed**:
- ✅ TASK-PD-005: TemplateSplitOutput exists and works
- ✅ TASK-PD-006: Orchestrator uses TemplateSplitOutput successfully

**Blocks**:
- TASK-PD-008: Documentation updates

## Acceptance Criteria (Revised)

- [x] `TemplateSplitOutput` dataclass EXISTS (from TASK-PD-005)
- [ ] `TemplateSplitMetadata` dataclass implemented
- [ ] `metadata` field added to `TemplateSplitOutput` (optional)
- [ ] `generate_metadata()` method implemented
- [ ] Size validation methods working (ALREADY WORKING from TASK-PD-005)
- [ ] Backward compatible (metadata is optional)
- [ ] Unit tests for new metadata functionality
- [ ] All existing tests still pass (no breaking changes)

## Risk Assessment

**Risks**: LOW

1. **Breaking Changes**: MINIMAL
   - Metadata field is optional
   - All existing code continues to work
   - No changes to existing methods

2. **Integration Impact**: NONE
   - TASK-PD-005 and TASK-PD-006 code unchanged
   - Orchestrator doesn't need to use metadata immediately

3. **Testing Complexity**: LOW
   - Simple dataclass tests
   - No complex integration scenarios

## Notes

### Why We Deviated from Original Task Spec

The original task specification was written before implementation details of TASK-PD-005 were known. Now that we see how the split output actually works, we're implementing what's genuinely useful:

1. **TemplateSplitMetadata**: YES - Useful for structured reporting
2. **TemplateClaude extensions**: NO - Not needed in current architecture
3. **to_core_markdown() method**: NO - Would duplicate generator logic

This approach:
- ✅ Adds value (structured metadata)
- ✅ Maintains backward compatibility
- ✅ Avoids breaking changes
- ✅ Follows SRP (separation of concerns)
- ✅ Respects existing architecture

### Future Enhancements (Out of Scope)

If we later need TemplateClaude to be split-aware:
- Add `split_config: Optional[SplitConfig]` to TemplateClaude
- Create SplitConfig dataclass with flags and paths
- Update manifest.json to include split metadata
- Add toggle in orchestrator to respect template-level split preference

But for now, orchestrator-level control is sufficient and simpler.

## Implementation Checklist

- [ ] Add TemplateSplitMetadata class to models.py
- [ ] Add metadata field to TemplateSplitOutput
- [ ] Add generate_metadata() method
- [ ] Update model_config examples
- [ ] Write test_template_split_metadata_creation
- [ ] Write test_template_split_metadata_with_errors
- [ ] Write test_template_split_output_generate_metadata
- [ ] Write test_template_split_output_with_metadata
- [ ] Write test_template_split_output_backward_compatible
- [ ] Run all tests (verify no regressions)
- [ ] Update task documentation

## Success Criteria

Implementation succeeds if:
1. ✅ All 5 new tests pass
2. ✅ All existing tests still pass (no regressions)
3. ✅ Metadata can be generated from TemplateSplitOutput
4. ✅ Metadata is optional (backward compatible)
5. ✅ Size validation continues to work
6. ✅ No changes needed to TASK-PD-005 or TASK-PD-006 code
