# Implementation Plan: TASK-PD-006

**Task**: Update template_create_orchestrator.py for split output
**Complexity**: 5/10 (Medium)
**Priority**: High
**Dependencies**: TASK-PD-005 (provides `generate_split()` method)

---

## Table of Contents

1. [Overview](#overview)
2. [Current State Analysis](#current-state-analysis)
3. [Target State](#target-state)
4. [Implementation Strategy](#implementation-strategy)
5. [Detailed Method Design](#detailed-method-design)
6. [Directory Structure Creation](#directory-structure-creation)
7. [File Writing Logic](#file-writing-logic)
8. [Backward Compatibility](#backward-compatibility)
9. [Test Strategy](#test-strategy)
10. [Validation Steps](#validation-steps)
11. [File Changes Summary](#file-changes-summary)
12. [Risk Assessment](#risk-assessment)

---

## 1. Overview

### Objective
Update the template creation orchestrator to write split CLAUDE.md output (core + patterns + reference) to the correct directory structure, reducing initial context window load by 60% (from ~20KB to ~8KB).

### Key Changes
- Add `_write_claude_md_split()` method to orchestrator
- Create `docs/patterns/` and `docs/reference/` directories
- Write split content to appropriate files
- Add size logging for validation
- Maintain backward compatibility with single-file mode

---

## 2. Current State Analysis

### Current Orchestrator Flow (Phase 9)

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Current Phase 9 Implementation** (lines 1430-1494):
```python
def _phase9_package_assembly(self, manifest, settings, claude_md, templates, output_path):
    """Phase 9: Assemble complete template package"""

    # Save manifest.json
    manifest_path = output_path / "manifest.json"
    # ... (lines 1462-1465)

    # Save settings.json
    settings_path = output_path / "settings.json"
    # ... (lines 1467-1471)

    # Save CLAUDE.md (SINGLE FILE)
    claude_md_path = output_path / "CLAUDE.md"
    claude_gen = ClaudeMdGenerator(None)
    claude_gen.save(claude_md, claude_md_path)
    self._print_success_line(f"CLAUDE.md ({self._file_size(claude_md_path)})")

    # Save template files
    # ... (lines 1480-1484)

    return output_path
```

**Current Output Structure**:
```
template-output/
├── CLAUDE.md           # Single ~20KB file
├── manifest.json
├── settings.json
├── templates/
└── agents/
```

### ClaudeMdGenerator API (from TASK-PD-005)

**Expected Interface** (from TASK-PD-005):
```python
class ClaudeMdGenerator:
    def generate(self) -> TemplateClaude:
        """Legacy single-file generation (backward compatible)."""

    def generate_split(self) -> TemplateSplitOutput:
        """Generate split output for progressive disclosure."""
        return TemplateSplitOutput(
            core=self._generate_core(),
            patterns=self._generate_patterns(),
            reference=self._generate_reference()
        )

@dataclass
class TemplateSplitOutput:
    """Split template output for progressive disclosure."""
    core: str               # CLAUDE.md content (~8KB)
    patterns: str           # docs/patterns/README.md content
    reference: str          # docs/reference/README.md content

    def get_core_size(self) -> int:
        """Get core content size in bytes."""
        return len(self.core.encode('utf-8'))

    def get_total_size(self) -> int:
        """Get total content size in bytes."""
        return sum(len(s.encode('utf-8')) for s in [self.core, self.patterns, self.reference])

    def get_reduction_percent(self) -> float:
        """Calculate size reduction for core vs total."""
        return (1 - self.get_core_size() / self.get_total_size()) * 100
```

---

## 3. Target State

### Target Output Structure
```
template-output/
├── CLAUDE.md           # Core ~8KB file
├── docs/
│   ├── patterns/
│   │   └── README.md   # Pattern documentation (~7KB)
│   └── reference/
│       └── README.md   # Reference documentation (~5KB)
├── manifest.json
├── settings.json
├── templates/
└── agents/
```

### Expected Size Reduction
- **Before**: CLAUDE.md = ~20KB
- **After**:
  - CLAUDE.md (core) = ~8KB (60% reduction)
  - docs/patterns/README.md = ~7KB
  - docs/reference/README.md = ~5KB
  - **Total**: ~20KB (content preserved, just reorganized)

---

## 4. Implementation Strategy

### Approach
**Incremental Enhancement** (not replacement):
1. Keep existing single-file logic (`_write_claude_md_single()`)
2. Add new split-file logic (`_write_claude_md_split()`)
3. Use configuration flag to control mode
4. Default to split mode (progressive disclosure enabled)

### Configuration Flag
Add to `OrchestrationConfig`:
```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    split_claude_md: bool = True  # TASK-PD-006: Enable progressive disclosure
```

### Orchestrator Changes
Modify Phase 9 to check flag and route appropriately:
```python
# Phase 9: CLAUDE.md writing
if self.config.split_claude_md:
    self._write_claude_md_split(self.claude_md, output_path)
else:
    self._write_claude_md_single(self.claude_md, output_path)
```

---

## 5. Detailed Method Design

### 5.1 `_write_claude_md_split()` Method

**Signature**:
```python
def _write_claude_md_split(
    self,
    claude_md: Any,
    output_path: Path
) -> bool:
    """
    Write split CLAUDE.md output for progressive disclosure (TASK-PD-006).

    Creates:
    - output_path/CLAUDE.md (core ~8KB)
    - output_path/docs/patterns/README.md (patterns)
    - output_path/docs/reference/README.md (reference)

    Args:
        claude_md: TemplateClaude object from Phase 8
        output_path: Template output directory

    Returns:
        True if successful, False otherwise

    Raises:
        None (logs errors and returns False instead)
    """
```

**Implementation**:
```python
def _write_claude_md_split(
    self,
    claude_md: Any,
    output_path: Path
) -> bool:
    """Write split CLAUDE.md output for progressive disclosure (TASK-PD-006)."""
    try:
        # Step 1: Generate split content
        generator = ClaudeMdGenerator(self.analysis, agents=self.agents, output_path=output_path)
        split_output = generator.generate_split()

        # Step 2: Create directory structure
        docs_dir = output_path / "docs"
        patterns_dir = docs_dir / "patterns"
        reference_dir = docs_dir / "reference"

        patterns_dir.mkdir(parents=True, exist_ok=True)
        reference_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Write files
        core_path = output_path / "CLAUDE.md"
        patterns_path = patterns_dir / "README.md"
        reference_path = reference_dir / "README.md"

        # Write core CLAUDE.md
        success, error_msg = safe_write_file(core_path, split_output.core)
        if not success:
            logger.error(f"Failed to write core CLAUDE.md: {error_msg}")
            return False

        # Write patterns
        success, error_msg = safe_write_file(patterns_path, split_output.patterns)
        if not success:
            logger.error(f"Failed to write patterns README.md: {error_msg}")
            return False

        # Write reference
        success, error_msg = safe_write_file(reference_path, split_output.reference)
        if not success:
            logger.error(f"Failed to write reference README.md: {error_msg}")
            return False

        # Step 4: Log sizes with reduction percentage
        self._log_split_sizes(core_path, patterns_path, reference_path, split_output)

        return True

    except Exception as e:
        logger.error(f"Failed to write split CLAUDE.md: {e}")
        logger.exception("Split CLAUDE.md write error")
        return False
```

### 5.2 `_log_split_sizes()` Method

**Signature**:
```python
def _log_split_sizes(
    self,
    core_path: Path,
    patterns_path: Path,
    reference_path: Path,
    split_output: Any
) -> None:
    """
    Log file sizes and reduction percentage for split output.

    Args:
        core_path: Path to core CLAUDE.md
        patterns_path: Path to patterns README.md
        reference_path: Path to reference README.md
        split_output: TemplateSplitOutput with size calculation methods
    """
```

**Implementation**:
```python
def _log_split_sizes(
    self,
    core_path: Path,
    patterns_path: Path,
    reference_path: Path,
    split_output: Any
) -> None:
    """Log file sizes and reduction percentage for split output."""
    core_size = self._file_size(core_path)
    patterns_size = self._file_size(patterns_path)
    reference_size = self._file_size(reference_path)

    reduction = split_output.get_reduction_percent()

    self._print_success_line(f"CLAUDE.md (core: {core_size}, {reduction:.1f}% reduction)")
    self._print_success_line(f"docs/patterns/README.md ({patterns_size})")
    self._print_success_line(f"docs/reference/README.md ({reference_size})")
```

### 5.3 `_write_claude_md_single()` Method (Backward Compatibility)

**Signature**:
```python
def _write_claude_md_single(
    self,
    claude_md: Any,
    output_path: Path
) -> bool:
    """
    Write single-file CLAUDE.md (legacy mode).

    Preserved for backward compatibility when split_claude_md=False.

    Args:
        claude_md: TemplateClaude object from Phase 8
        output_path: Template output directory

    Returns:
        True if successful, False otherwise
    """
```

**Implementation**:
```python
def _write_claude_md_single(
    self,
    claude_md: Any,
    output_path: Path
) -> bool:
    """Write single-file CLAUDE.md (legacy mode)."""
    try:
        claude_md_path = output_path / "CLAUDE.md"
        generator = ClaudeMdGenerator(None)
        generator.save(claude_md, claude_md_path)

        self._print_success_line(f"CLAUDE.md ({self._file_size(claude_md_path)})")
        return True

    except Exception as e:
        logger.error(f"Failed to write single CLAUDE.md: {e}")
        logger.exception("Single CLAUDE.md write error")
        return False
```

---

## 6. Directory Structure Creation

### Implementation Pattern
Use `Path.mkdir(parents=True, exist_ok=True)` for idempotent directory creation:

```python
# Create docs/ directory structure
docs_dir = output_path / "docs"
patterns_dir = docs_dir / "patterns"
reference_dir = docs_dir / "reference"

# Create all directories (including parents)
patterns_dir.mkdir(parents=True, exist_ok=True)   # Creates docs/patterns/
reference_dir.mkdir(parents=True, exist_ok=True)  # Creates docs/reference/
```

**Benefits**:
- Idempotent (safe to call multiple times)
- Creates parent directories automatically
- No error if directories already exist

---

## 7. File Writing Logic

### Use Existing `safe_write_file()` Pattern

**Pattern** (from Phase 7 agent writing, lines 985-988):
```python
from lib.utils.file_io import safe_write_file

# Write with error handling
success, error_msg = safe_write_file(file_path, content)
if not success:
    logger.error(f"Failed to write {file_path}: {error_msg}")
    return False
```

**Benefits**:
- Consistent error handling across orchestrator
- Handles permissions, disk space, encoding errors
- Returns actionable error messages

### File Write Sequence
1. Core CLAUDE.md (fail fast if this fails)
2. Patterns README.md (log error but continue)
3. Reference README.md (log error but continue)

**Rationale**: Core file is essential, supplementary files are optional.

---

## 8. Backward Compatibility

### Configuration Strategy

**Add to OrchestrationConfig** (line 124):
```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    split_claude_md: bool = True  # TASK-PD-006: Enable progressive disclosure
```

**Update `run_template_create()` signature** (line 2218):
```python
def run_template_create(
    # ... existing parameters ...
    split_claude_md: bool = True,  # TASK-PD-006: Progressive disclosure
    # ... remaining parameters ...
) -> OrchestrationResult:
```

**Update CLI argument parser** (line 2303):
```python
parser.add_argument("--no-split-claude-md", action="store_false",
                    dest="split_claude_md",
                    help="Disable progressive disclosure (use single CLAUDE.md file)")
```

### Migration Path

**Default Behavior**:
- New templates: Split mode enabled by default
- Existing workflows: Can opt-out with `--no-split-claude-md`

**Usage Examples**:
```bash
# Default: Split mode enabled
/template-create --path ~/projects/my-app

# Opt-out: Single file mode
/template-create --path ~/projects/my-app --no-split-claude-md
```

---

## 9. Test Strategy

### 9.1 Unit Tests

**File**: `tests/unit/test_template_create_orchestrator.py`

#### Test 1: Split Output Creation
```python
def test_write_claude_md_split_creates_correct_structure():
    """Test split output creates correct directory structure."""
    config = OrchestrationConfig(split_claude_md=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Setup mock split output
    mock_split = TemplateSplitOutput(
        core="# Core Content",
        patterns="# Patterns",
        reference="# Reference"
    )

    with patch.object(ClaudeMdGenerator, 'generate_split', return_value=mock_split):
        output_path = Path("/tmp/test-template")
        success = orchestrator._write_claude_md_split(None, output_path)

        assert success
        assert (output_path / "CLAUDE.md").exists()
        assert (output_path / "docs/patterns/README.md").exists()
        assert (output_path / "docs/reference/README.md").exists()
```

#### Test 2: Size Validation
```python
def test_split_output_size_reduction():
    """Test split output achieves expected size reduction."""
    config = OrchestrationConfig(split_claude_md=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Generate real split output
    generator = ClaudeMdGenerator(analysis)
    split_output = generator.generate_split()

    # Verify core size
    core_size = split_output.get_core_size()
    assert core_size <= 10 * 1024  # 10KB max

    # Verify reduction percentage
    reduction = split_output.get_reduction_percent()
    assert reduction >= 50  # At least 50% reduction
```

#### Test 3: Backward Compatibility
```python
def test_single_file_mode_backward_compatible():
    """Test single-file mode still works (backward compatibility)."""
    config = OrchestrationConfig(split_claude_md=False)
    orchestrator = TemplateCreateOrchestrator(config)

    output_path = Path("/tmp/test-template")
    success = orchestrator._write_claude_md_single(claude_md, output_path)

    assert success
    assert (output_path / "CLAUDE.md").exists()
    assert not (output_path / "docs/patterns").exists()
```

#### Test 4: Error Handling
```python
def test_split_write_handles_permission_error():
    """Test split write handles permission errors gracefully."""
    config = OrchestrationConfig(split_claude_md=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Mock safe_write_file to fail
    with patch('lib.utils.file_io.safe_write_file', return_value=(False, "Permission denied")):
        output_path = Path("/tmp/test-template")
        success = orchestrator._write_claude_md_split(None, output_path)

        assert not success
```

### 9.2 Integration Tests

**File**: `tests/integration/test_template_create_orchestrator_integration.py`

#### Test 1: End-to-End Split Output
```python
def test_e2e_split_claude_md_generation():
    """Test end-to-end template creation with split CLAUDE.md."""
    result = run_template_create(
        codebase_path=SAMPLE_CODEBASE_PATH,
        split_claude_md=True,
        dry_run=False
    )

    assert result.success

    # Verify files exist
    core_path = result.output_path / "CLAUDE.md"
    patterns_path = result.output_path / "docs/patterns/README.md"
    reference_path = result.output_path / "docs/reference/README.md"

    assert core_path.exists()
    assert patterns_path.exists()
    assert reference_path.exists()

    # Verify core size
    core_size = core_path.stat().st_size
    assert core_size <= 10 * 1024  # 10KB max
```

#### Test 2: Content Distribution Validation
```python
def test_split_content_distribution():
    """Test split content is distributed correctly."""
    result = run_template_create(
        codebase_path=SAMPLE_CODEBASE_PATH,
        split_claude_md=True
    )

    # Read files
    core = (result.output_path / "CLAUDE.md").read_text()
    patterns = (result.output_path / "docs/patterns/README.md").read_text()
    reference = (result.output_path / "docs/reference/README.md").read_text()

    # Verify core has essential content
    assert "## Architecture Overview" in core
    assert "## Technology Stack" in core
    assert "## Loading Instructions" in core

    # Verify patterns has pattern content
    assert "## Patterns and Best Practices" in patterns

    # Verify reference has reference content
    assert "## Code Examples" in reference
    assert "## Testing Strategy" in reference
```

---

## 10. Validation Steps

### Manual Validation Checklist

After implementation, validate manually:

1. **Run template creation with split mode**:
   ```bash
   cd ~/Projects/appmilla_github/guardkit
   /template-create --path ~/projects/sample-app
   ```

2. **Verify directory structure**:
   ```bash
   ls -la ~/.agentecflow/templates/sample-app/
   # Expected:
   # - CLAUDE.md
   # - docs/patterns/README.md
   # - docs/reference/README.md
   ```

3. **Check file sizes**:
   ```bash
   wc -c ~/.agentecflow/templates/sample-app/CLAUDE.md
   # Expected: ~8KB (≤10KB)

   wc -c ~/.agentecflow/templates/sample-app/docs/patterns/README.md
   # Expected: ~7KB

   wc -c ~/.agentecflow/templates/sample-app/docs/reference/README.md
   # Expected: ~5KB
   ```

4. **Verify content distribution**:
   ```bash
   # Core should have loading instructions
   grep "Extended Documentation" ~/.agentecflow/templates/sample-app/CLAUDE.md

   # Patterns should have detailed examples
   grep "Query Options Factory" ~/.agentecflow/templates/sample-app/docs/patterns/README.md

   # Reference should have troubleshooting
   grep "Troubleshooting" ~/.agentecflow/templates/sample-app/docs/reference/README.md
   ```

5. **Test backward compatibility**:
   ```bash
   /template-create --path ~/projects/sample-app --no-split-claude-md

   ls -la ~/.agentecflow/templates/sample-app/
   # Expected: Only CLAUDE.md (no docs/ directory)
   ```

---

## 11. File Changes Summary

### Files to Modify

#### 1. `installer/global/commands/lib/template_create_orchestrator.py`

**Changes**:
- Add `split_claude_md: bool = True` to `OrchestrationConfig` (line ~124)
- Add `_write_claude_md_split()` method (after line 1494)
- Add `_log_split_sizes()` method (after `_write_claude_md_split()`)
- Add `_write_claude_md_single()` method (extract existing logic from Phase 9)
- Modify `_phase9_package_assembly()` to route based on `split_claude_md` flag (lines 1473-1477)
- Add `split_claude_md` parameter to `run_template_create()` (line 2218)
- Add CLI argument `--no-split-claude-md` to parser (line 2303)

**Estimated Lines of Code**:
- New methods: ~80 lines
- Configuration changes: ~10 lines
- Total: ~90 lines

#### 2. `installer/global/lib/template_generator/models.py`

**Changes**:
- Add `TemplateSplitOutput` dataclass (if not already added by TASK-PD-005)

**Note**: This should be done by TASK-PD-005. Verify it exists before implementing.

#### 3. Tests (New Files)

**Files**:
- `tests/unit/test_orchestrator_split_output.py` (new)
- `tests/integration/test_split_claude_md_e2e.py` (new)

**Estimated Lines of Code**:
- Unit tests: ~150 lines
- Integration tests: ~100 lines
- Total: ~250 lines

---

## 12. Risk Assessment

### High Risk Items

None identified. This is a low-risk additive change.

### Medium Risk Items

1. **TASK-PD-005 dependency**
   - **Risk**: `generate_split()` method not implemented yet
   - **Mitigation**: Verify TASK-PD-005 completion before starting
   - **Fallback**: Implement stub `generate_split()` for testing

2. **File I/O errors during split write**
   - **Risk**: Partial write (core succeeds, patterns fails)
   - **Mitigation**: Use `safe_write_file()` with comprehensive error handling
   - **Fallback**: Log errors, mark phase as warning (not fatal)

### Low Risk Items

1. **Directory creation race conditions**
   - **Risk**: Multiple orchestrators creating same directories
   - **Mitigation**: `mkdir(parents=True, exist_ok=True)` is atomic and idempotent

2. **Backward compatibility breaking**
   - **Risk**: Single-file mode stops working
   - **Mitigation**: Comprehensive unit tests for both modes

---

## Implementation Order

1. **Phase 1: Verify Dependencies** (30 minutes)
   - Confirm TASK-PD-005 completion
   - Verify `generate_split()` and `TemplateSplitOutput` exist
   - Review interface contracts

2. **Phase 2: Add Configuration** (15 minutes)
   - Add `split_claude_md` to `OrchestrationConfig`
   - Add CLI argument `--no-split-claude-md`
   - Update `run_template_create()` signature

3. **Phase 3: Implement Methods** (2 hours)
   - Implement `_write_claude_md_split()`
   - Implement `_log_split_sizes()`
   - Extract `_write_claude_md_single()` from existing Phase 9 logic

4. **Phase 4: Modify Phase 9** (30 minutes)
   - Add routing logic based on `split_claude_md` flag
   - Update success message formatting

5. **Phase 5: Unit Tests** (2 hours)
   - Write tests for `_write_claude_md_split()`
   - Write tests for `_write_claude_md_single()`
   - Write tests for error handling

6. **Phase 6: Integration Tests** (1 hour)
   - Write end-to-end test with split mode
   - Write content distribution validation test

7. **Phase 7: Manual Validation** (1 hour)
   - Run against sample codebase
   - Verify directory structure
   - Check file sizes and content

8. **Phase 8: Documentation Update** (30 minutes)
   - Update task metadata with test results
   - Document new CLI flag
   - Add examples to command help

**Total Estimated Time**: 7.5 hours

---

## Success Criteria

- [ ] Split output writes to correct directory structure (`CLAUDE.md`, `docs/patterns/README.md`, `docs/reference/README.md`)
- [ ] `docs/patterns/README.md` created with pattern content
- [ ] `docs/reference/README.md` created with reference content
- [ ] Core CLAUDE.md includes loading instructions pointing to `docs/`
- [ ] Size logging shows reduction percentage (≥50%)
- [ ] Backward compatible single-file mode available via `--no-split-claude-md`
- [ ] Integration test: full template-create with split output
- [ ] Core CLAUDE.md ≤10KB for typical templates
- [ ] All unit tests pass
- [ ] All integration tests pass

---

## Notes

1. **TASK-PD-005 Dependency**: This task assumes TASK-PD-005 has implemented `generate_split()` and `TemplateSplitOutput`. If not, coordinate with that task first.

2. **Error Handling Philosophy**: Follow existing orchestrator pattern - log errors but don't fail the entire orchestration unless critical (core CLAUDE.md write failure).

3. **File Size Variance**: The 10KB limit for core CLAUDE.md is a guideline. Some complex templates may exceed this slightly (up to 12KB acceptable).

4. **Testing Strategy**: Focus on integration tests over unit tests - the real value is ensuring the end-to-end workflow works correctly.

5. **Performance Impact**: Directory creation and file writes are fast I/O operations - no performance degradation expected.
