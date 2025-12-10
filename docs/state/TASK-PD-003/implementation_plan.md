# TASK-PD-003 Implementation Plan
## Update enhancer.py to call new applier methods

**Task ID**: TASK-PD-003
**Status**: PLANNING
**Priority**: High
**Complexity**: 5/10 (Medium)
**Phase**: Phase 1 (Foundation)
**Created**: 2025-12-05
**Estimated Duration**: 1 day

---

## 1. Current State Analysis

### 1.1 Current enhancer.py Implementation

**File**: `installer/core/lib/agent_enhancement/enhancer.py` (576 lines)

**Key Current Behaviors**:
- `enhance()` method returns `EnhancementResult` dataclass (lines 34-44)
- Current `EnhancementResult` has these fields:
  - `success: bool`
  - `agent_name: str`
  - `sections: List[str]`
  - `templates: List[str]`
  - `examples: List[str]`
  - `diff: str`
  - `error: Optional[str]`
  - `strategy_used: Optional[str]`

- Single file output model at lines 158-175:
  ```python
  if not self.dry_run:
      self.applier.apply(agent_file, enhancement)  # Single method call

  diff = self.applier.generate_diff(agent_file, enhancement)

  return EnhancementResult(
      success=True,
      agent_name=agent_name,
      sections=enhancement.get("sections", []),
      templates=[str(t) for t in templates],
      examples=enhancement.get("examples", []),
      diff=diff,
      strategy_used=self.strategy
  )
  ```

### 1.2 Current Applier Integration Points

**File**: `installer/core/lib/agent_enhancement/applier.py` (253 lines)

**Current Methods**:
- `apply(agent_file: Path, enhancement: Dict[str, Any]) -> None` (lines 33-67)
  - Modifies file in-place
  - No return value
  - Merges enhancement into single file

- `generate_diff(agent_file: Path, enhancement: Dict[str, Any]) -> str` (lines 68-117)
  - Returns unified diff string
  - Does NOT modify file

- `_merge_content()` (lines 119-204)
  - Internal helper for content merging
  - Preserves frontmatter
  - Handles boundaries special placement
  - Appends other sections at end

**Current Limitation**: No split output capability - everything goes into single file

### 1.3 TASK-PD-001 Completion Status

**Expected New Methods** (from TASK-PD-001):
- `create_extended_file(agent_path: Path, extended_content: str) -> Path`
  - Creates `{agent-name}-ext.md` file
  - Returns path to extended file

- `apply_with_split(agent_path: Path, enhancement: Dict[str, Any]) -> Tuple[Path, Path]`
  - Splits enhancement into core and extended sections
  - Applies core to original file
  - Creates extended file
  - Returns tuple of (core_path, extended_path)

- Content categorization logic (internal methods)
  - `_split_enhancement()` - separates core from extended content
  - Adds loading instruction to core file

### 1.4 TASK-PD-002 Completion Status

**Expected Template Function** (from TASK-PD-002):
- `generate_loading_instruction(agent_name: str, ext_filename: str) -> str`
  - Generates markdown section with:
    - "## Extended Reference" header
    - Instructions to load extended file
    - Description of extended file contents

### 1.5 Backward Compatibility Concerns

**Current Usage**:
1. **Command**: `installer/core/commands/agent-enhance.py` calls `enhancer.enhance()`
   - Currently expects single return value: `EnhancementResult`
   - Shows basic result status and file list

2. **Tasks**: Enhancement tasks invoke enhancer
   - Need to support both single-file and split-file modes

3. **Integration**: Other components may depend on single-file behavior
   - `agent-format` command (different module)
   - No other known dependencies

**Compatibility Strategy**:
- Default to split output (`split_output=True`) - new behavior
- Maintain single-file mode via flag (`split_output=False`) for backward compatibility
- Update result dataclass to support both modes
- Command output adapts based on mode used

---

## 2. Required Changes

### 2.1 File: enhancer.py

**Location**: `installer/core/lib/agent_enhancement/enhancer.py`

#### Change 2.1.1: Modify EnhancementResult Dataclass Definition

**Lines to Replace**: 34-44

**Current Code**:
```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement."""
    success: bool
    agent_name: str
    sections: List[str]  # Sections added
    templates: List[str]  # Templates referenced
    examples: List[str]   # Code examples included
    diff: str            # Unified diff
    error: Optional[str] = None
    strategy_used: Optional[str] = None
```

**New Code**:
```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement operation.

    Supports both single-file and split-file modes.

    Attributes:
        success: Whether enhancement completed successfully
        agent_name: Name of enhanced agent
        sections: List of sections added to enhancement
        templates: List of template files referenced
        examples: List of code examples included
        diff: Unified diff of changes (single-file mode) or core changes (split mode)
        core_file: Path to core agent file (split mode) or enhanced file (single mode)
        extended_file: Path to extended reference file (split mode only)
        split_output: Whether split-file mode was used
        error: Error message if enhancement failed
        strategy_used: Enhancement strategy that was used (ai|static|hybrid)
    """
    success: bool
    agent_name: str
    sections: List[str]           # Sections added
    templates: List[str]          # Templates referenced
    examples: List[str]            # Code examples included
    diff: str                      # Unified diff
    core_file: Optional[Path] = None          # NEW: Path to core file
    extended_file: Optional[Path] = None      # NEW: Path to extended file (split mode)
    split_output: bool = False                # NEW: True if split-file mode used
    error: Optional[str] = None
    strategy_used: Optional[str] = None

    @property
    def files(self) -> List[Path]:
        """Return all created/modified files as a list.

        Returns:
            List containing:
            - Single-file mode: [core_file] or [core_file, extended_file] if both exist
            - Split-file mode: [core_file, extended_file]
        """
        files = []
        if self.core_file:
            files.append(self.core_file)
        if self.extended_file:
            files.append(self.extended_file)
        return files
```

**Rationale**:
- Adds support for split-file output while maintaining backward compatibility
- New fields for core_file and extended_file track both files
- `split_output` flag indicates which mode was used
- `files` property provides convenient access to all created files
- Preserves all existing fields for backward compatibility with existing code

#### Change 2.1.2: Modify enhance() Method Signature

**Lines to Replace**: 106-110 (method signature only)

**Current Code**:
```python
def enhance(
    self,
    agent_file: Path,
    template_dir: Path
) -> EnhancementResult:
```

**New Code**:
```python
def enhance(
    self,
    agent_file: Path,
    template_dir: Path,
    split_output: bool = True
) -> EnhancementResult:
```

**Rationale**:
- Adds `split_output` parameter with default `True`
- Default to new progressive disclosure behavior
- Allows opt-in to single-file mode for backward compatibility

#### Change 2.1.3: Update enhance() Method Docstring

**Lines to Replace**: 111-120

**Current Code**:
```python
"""
Enhance single agent with template-specific content.

Args:
    agent_file: Path to agent file
    template_dir: Path to template directory

Returns:
    Enhancement result with success status and details
"""
```

**New Code**:
```python
"""
Enhance single agent with template-specific content.

Supports both single-file and progressive disclosure split-file modes.

Args:
    agent_file: Path to agent file to enhance
    template_dir: Path to template directory for context
    split_output: If True (default), create separate extended reference file.
                 If False, merge all content into single agent file (backward compatible mode).

Returns:
    Enhancement result with file paths and metadata:
    - split_output=True: Returns with core_file and extended_file paths
    - split_output=False: Returns with core_file only, extended_file=None

Raises:
    FileNotFoundError: If agent_file does not exist
    PermissionError: If cannot read/write files
    ValidationError: If enhancement data is malformed
"""
```

**Rationale**:
- Documents new parameter and return behavior
- Clarifies difference between modes
- Documents exceptions that can occur

#### Change 2.1.4: Refactor enhance() Method Implementation

**Lines to Replace**: 121-189 (entire implementation block)

**Current Code**:
```python
agent_name = agent_file.stem

try:
    # 1. Load agent metadata
    if self.verbose:
        logger.info(f"Loading agent metadata from {agent_file}")

    agent_metadata = self._load_agent_metadata(agent_file)

    # 2. Discover relevant templates
    if self.verbose:
        logger.info(f"Discovering relevant templates in {template_dir}")

    templates = self._discover_relevant_templates(
        agent_metadata,
        template_dir
    )

    if self.verbose:
        logger.info(f"Found {len(templates)} relevant templates")

    # 3. Generate enhancement
    if self.verbose:
        logger.info(f"Generating enhancement using '{self.strategy}' strategy")

    enhancement = self._generate_enhancement(
        agent_metadata,
        templates,
        template_dir
    )

    # 4. Validate enhancement
    if self.verbose:
        logger.info("Validating enhancement")

    self._validate_enhancement(enhancement)

    # 5. Apply enhancement (if not dry run)
    if not self.dry_run:
        if self.verbose:
            logger.info(f"Applying enhancement to {agent_file}")

        self.applier.apply(agent_file, enhancement)

    # 6. Generate diff
    diff = self.applier.generate_diff(agent_file, enhancement)

    return EnhancementResult(
        success=True,
        agent_name=agent_name,
        sections=enhancement.get("sections", []),
        templates=[str(t) for t in templates],
        examples=enhancement.get("examples", []),
        diff=diff,
        strategy_used=self.strategy
    )

except Exception as e:
    logger.exception(f"Enhancement failed for {agent_name}")
    return EnhancementResult(
        success=False,
        agent_name=agent_name,
        sections=[],
        templates=[],
        examples=[],
        diff="",
        error=str(e),
        strategy_used=self.strategy
    )
```

**New Code**:
```python
agent_name = agent_file.stem

try:
    # 1. Load agent metadata
    if self.verbose:
        logger.info(f"Loading agent metadata from {agent_file}")

    agent_metadata = self._load_agent_metadata(agent_file)

    # 2. Discover relevant templates
    if self.verbose:
        logger.info(f"Discovering relevant templates in {template_dir}")

    templates = self._discover_relevant_templates(
        agent_metadata,
        template_dir
    )

    if self.verbose:
        logger.info(f"Found {len(templates)} relevant templates")

    # 3. Generate enhancement
    if self.verbose:
        mode_name = "split-file" if split_output else "single-file"
        logger.info(f"Generating enhancement using '{self.strategy}' strategy ({mode_name} mode)")

    enhancement = self._generate_enhancement(
        agent_metadata,
        templates,
        template_dir
    )

    # 4. Validate enhancement
    if self.verbose:
        logger.info("Validating enhancement")

    self._validate_enhancement(enhancement)

    # 5. Apply enhancement (if not dry run)
    core_file = agent_file
    extended_file = None

    if not self.dry_run:
        if split_output:
            # TASK-PD-003: Use new split-file mode
            if self.verbose:
                logger.info(f"Applying enhancement with split output to {agent_file}")

            core_file, extended_file = self.applier.apply_with_split(agent_file, enhancement)

            if self.verbose:
                logger.info(f"  Core file: {core_file}")
                logger.info(f"  Extended file: {extended_file}")
        else:
            # Backward compatible single-file mode
            if self.verbose:
                logger.info(f"Applying enhancement to {agent_file} (single-file mode)")

            self.applier.apply(agent_file, enhancement)
            core_file = agent_file

    # 6. Generate diff
    diff = self.applier.generate_diff(agent_file, enhancement)

    return EnhancementResult(
        success=True,
        agent_name=agent_name,
        sections=enhancement.get("sections", []),
        templates=[str(t) for t in templates],
        examples=enhancement.get("examples", []),
        diff=diff,
        core_file=core_file,
        extended_file=extended_file,
        split_output=split_output,
        strategy_used=self.strategy
    )

except Exception as e:
    logger.exception(f"Enhancement failed for {agent_name}")
    return EnhancementResult(
        success=False,
        agent_name=agent_name,
        sections=[],
        templates=[],
        examples=[],
        diff="",
        core_file=None,
        extended_file=None,
        split_output=split_output,
        error=str(e),
        strategy_used=self.strategy
    )
```

**Rationale**:
- Implements the split-file logic branching on `split_output` parameter
- Calls `apply_with_split()` when split mode enabled
- Falls back to single-file `apply()` for backward compatibility
- Properly tracks both core and extended file paths
- Enhanced logging shows which mode is active
- Exception handler includes new fields to maintain consistency

### 2.2 File: models.py

**Location**: `installer/core/lib/agent_enhancement/models.py`

**Note**: This file may not currently exist. If it doesn't exist, the `EnhancementResult` dataclass is defined directly in `enhancer.py`.

**Decision**: Since `EnhancementResult` is already defined in `enhancer.py` at line 34, we modify it in place (see Change 2.1.1 above). If a separate `models.py` file exists or needs to be created for future separation, that will be a follow-up task.

**Current Status**: All required model changes are consolidated into Change 2.1.1 above.

### 2.3 File: agent-enhance.md (Command Documentation)

**Location**: `installer/core/commands/agent-enhance.md`

#### Change 2.3.1: Update Output Format Section

**Lines to Replace**: 209-233 (current "Output Format" section)

**Current Code**:
```markdown
## Output Format

### Success Output
```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5
```

### Dry-Run Output
```
✓ Enhanced testing-specialist.md
  Sections added: 4
  Templates referenced: 8
  Code examples: 3

[DRY RUN] Changes not applied

--- Preview ---
## Related Templates
- templates/tests/unit/ComponentTest.tsx.template
- templates/tests/integration/ApiTest.tsx.template
...
```
```

**New Code**:
```markdown
## Output Format

### Success Output - Split-File Mode (Default)
```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5

Split-file mode (progressive disclosure):
  Core file: testing-specialist.md
  Extended file: testing-specialist-ext.md
```

### Success Output - Single-File Mode (Backward Compatible)
```
✓ Enhanced testing-specialist.md
  Sections added: 3
  Templates referenced: 12
  Code examples: 5

All content merged into single file.
```

### Dry-Run Output - Split-File Mode
```
✓ Enhanced testing-specialist.md
  Sections added: 4
  Templates referenced: 8
  Code examples: 3

[DRY RUN] Changes not applied

Split-file mode (progressive disclosure):
  Core file: testing-specialist.md (with loading instruction)
  Extended file: testing-specialist-ext.md (would be created)

--- Preview (Core File) ---
## Boundaries
...

## Extended Reference

Before generating code, load the extended reference:

\`\`\`bash
cat agents/testing-specialist-ext.md
\`\`\`

--- Preview (Extended File) ---
## Detailed Code Examples
...
```

### Performance Characteristics

**Split-File Mode** (default, `split_output=True`):
- Creates two files: core (~40% original size) + extended (~60%)
- Better for progressive disclosure workflow
- Claude loads extended content when needed
- Faster initial display of core agent
- Recommended for production agents

**Single-File Mode** (`split_output=False`):
- Merges all content into single file
- Backward compatible with existing workflows
- All content always available
- Slower for very large agents
- Legacy mode, not recommended for new work
```

**Rationale**:
- Documents new split-file output behavior
- Shows examples of both modes
- Clarifies when each mode is used
- Explains performance characteristics
- Helps users understand new default behavior

#### Change 2.3.2: Update Usage Examples Section

**Lines to Add**: After line 37 (add new example usage sections)

**New Content**:
```markdown
# Enhanced Examples for Split-File Mode

## Split-File Mode (Default - Progressive Disclosure)
```bash
# Default: uses split-file mode with progressive disclosure
/agent-enhance react-typescript/testing-specialist

# Explicitly enable split-file mode (equivalent to above)
/agent-enhance react-typescript/testing-specialist --split-output

# Preview split-file enhancement
/agent-enhance react-typescript/testing-specialist --split-output --dry-run
```

## Single-File Mode (Backward Compatible)
```bash
# Use legacy single-file mode
/agent-enhance react-typescript/testing-specialist --single-file

# Preview single-file enhancement
/agent-enhance react-typescript/testing-specialist --single-file --dry-run
```
```

**Note**: This assumes command-line flags `--split-output` and `--single-file` are added to the CLI wrapper. The current implementation in `enhancer.py` uses the `split_output` parameter directly.

#### Change 2.3.3: Add Mode Selection Section

**Lines to Add**: New section after "Command Options" heading

**New Content**:
```markdown
### Output Mode Selection

```bash
--split-output          Enable split-file mode with progressive disclosure (DEFAULT)
                        Creates two files: agent.md (core) + agent-ext.md (extended)
                        Loading instruction inserted into core file

--single-file           Use legacy single-file mode
                        All content merged into single agent file
                        Maintains backward compatibility
                        Default: disabled (split-output is default)
```

**Rationale**:
- Documents new command-line options for split-output mode
- Clarifies default behavior change
- Maintains backward compatibility documentation
- Helps users make deliberate choice between modes

### 2.4 Integration Points Summary

**Files Affected**:
1. `installer/core/lib/agent_enhancement/enhancer.py` - **4 changes**
   - EnhancementResult dataclass: Add new fields
   - enhance() signature: Add split_output parameter
   - enhance() docstring: Document new behavior
   - enhance() implementation: Branch logic for split vs single

2. `installer/core/commands/agent-enhance.md` - **3 changes**
   - Output format examples for both modes
   - Usage examples for both modes
   - Mode selection options documentation

**Dependencies Required**:
- TASK-PD-001: `applier.apply_with_split()` method must exist
- TASK-PD-002: `generate_loading_instruction()` function must exist

**No Changes Required To**:
- `applier.py` - Already has new methods from TASK-PD-001
- Other command files - No integration needed
- Test infrastructure - Tests added as part of this task

---

## 3. Test Strategy

### 3.1 Unit Tests

**File**: `tests/unit/test_enhancer_split_output.py` (NEW)

#### Test 3.1.1: EnhancementResult with Split Output

```python
def test_enhancement_result_split_output():
    """Test EnhancementResult dataclass with split-file mode."""
    core_path = Path("agent.md")
    ext_path = Path("agent-ext.md")

    result = EnhancementResult(
        success=True,
        agent_name="test-agent",
        sections=["boundaries", "examples"],
        templates=["template1.template"],
        examples=["example1"],
        diff="unified diff content",
        core_file=core_path,
        extended_file=ext_path,
        split_output=True
    )

    assert result.success is True
    assert result.split_output is True
    assert result.core_file == core_path
    assert result.extended_file == ext_path
    assert len(result.files) == 2
    assert core_path in result.files
    assert ext_path in result.files
```

**Validation**:
- EnhancementResult stores split-file paths correctly
- `files` property returns both files
- All fields properly initialized

#### Test 3.1.2: EnhancementResult Single-File Mode

```python
def test_enhancement_result_single_file_mode():
    """Test EnhancementResult dataclass with single-file mode."""
    core_path = Path("agent.md")

    result = EnhancementResult(
        success=True,
        agent_name="test-agent",
        sections=["boundaries", "examples"],
        templates=["template1.template"],
        examples=["example1"],
        diff="unified diff content",
        core_file=core_path,
        extended_file=None,
        split_output=False
    )

    assert result.success is True
    assert result.split_output is False
    assert result.core_file == core_path
    assert result.extended_file is None
    assert len(result.files) == 1
    assert core_path in result.files
```

**Validation**:
- EnhancementResult stores single-file path correctly
- `files` property returns only core file
- All fields properly initialized

#### Test 3.1.3: EnhancementResult with Error

```python
def test_enhancement_result_with_error():
    """Test EnhancementResult with failure state."""
    result = EnhancementResult(
        success=False,
        agent_name="test-agent",
        sections=[],
        templates=[],
        examples=[],
        diff="",
        core_file=None,
        extended_file=None,
        split_output=True,
        error="Enhancement failed: timeout"
    )

    assert result.success is False
    assert result.error == "Enhancement failed: timeout"
    assert len(result.files) == 0
```

**Validation**:
- EnhancementResult properly handles error state
- Files list empty when no files created
- Error message preserved

### 3.2 Integration Tests

**File**: `tests/integration/test_enhancer_split_integration.py` (NEW)

#### Test 3.2.1: Full Enhancement with Split Output

```python
def test_full_enhancement_with_split_output(tmp_path):
    """Test complete enhancement workflow with split-file mode."""
    # Setup
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "templates").mkdir()

    agent_file = template_dir / "agents" / "test-agent.md"
    agent_file.parent.mkdir()

    # Create test agent content
    agent_content = """---
name: test-agent
description: Test agent
---

# Test Agent

## Quick Start

Simple example here.

## Capabilities

- Capability 1
"""
    agent_file.write_text(agent_content)

    # Execute
    enhancer = SingleAgentEnhancer(strategy="static", dry_run=False)
    result = enhancer.enhance(
        agent_file=agent_file,
        template_dir=template_dir,
        split_output=True
    )

    # Verify core file exists and contains expected content
    assert result.success is True
    assert result.core_file.exists()
    assert result.extended_file is not None
    assert result.extended_file.exists()
    assert result.split_output is True

    # Verify core file has loading instruction
    core_content = result.core_file.read_text()
    assert "## Extended Reference" in core_content
    assert "test-agent-ext.md" in core_content

    # Verify extended file has content
    ext_content = result.extended_file.read_text()
    assert len(ext_content) > 0
    assert ext_content != core_content
```

**Coverage**:
- Creates temporary test structure
- Runs full enhancement pipeline
- Verifies split files created
- Validates core file has loading instruction
- Validates extended file has content

#### Test 3.2.2: Full Enhancement with Single-File Mode

```python
def test_full_enhancement_with_single_file_mode(tmp_path):
    """Test complete enhancement workflow with single-file (backward compatible) mode."""
    # Setup
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "templates").mkdir()

    agent_file = template_dir / "agents" / "test-agent.md"
    agent_file.parent.mkdir()
    agent_file.write_text("# Test Agent\n\n## Quick Start\n\nExample")

    # Execute
    enhancer = SingleAgentEnhancer(strategy="static", dry_run=False)
    result = enhancer.enhance(
        agent_file=agent_file,
        template_dir=template_dir,
        split_output=False  # Single-file mode
    )

    # Verify
    assert result.success is True
    assert result.core_file.exists()
    assert result.extended_file is None
    assert result.split_output is False

    # Verify only core file exists
    ext_path = agent_file.with_stem(f"{agent_file.stem}-ext")
    assert not ext_path.exists()
```

**Coverage**:
- Tests backward compatible single-file mode
- Verifies extended file NOT created
- Validates result metadata

#### Test 3.2.3: Dry-Run with Split Output

```python
def test_dry_run_with_split_output(tmp_path):
    """Test dry-run mode doesn't create files but returns paths."""
    # Setup
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "templates").mkdir()

    agent_file = template_dir / "agents" / "test-agent.md"
    agent_file.parent.mkdir()
    agent_file.write_text("# Test Agent\n\n## Quick Start\n\nExample")

    original_content = agent_file.read_text()

    # Execute
    enhancer = SingleAgentEnhancer(strategy="static", dry_run=True)
    result = enhancer.enhance(
        agent_file=agent_file,
        template_dir=template_dir,
        split_output=True
    )

    # Verify - files should NOT be created in dry-run
    assert result.success is True
    assert result.split_output is True
    assert result.core_file is not None
    assert result.extended_file is not None

    # Verify original file not modified
    assert agent_file.read_text() == original_content

    # Verify no extended file created
    ext_path = agent_file.with_stem(f"{agent_file.stem}-ext")
    assert not ext_path.exists()
```

**Coverage**:
- Tests dry-run doesn't modify files
- Verifies result contains planned paths
- Validates backward compatibility

### 3.3 Coverage Goals

**Target Metrics**:
- Line coverage: ≥80%
- Branch coverage: ≥75%
- Exception coverage: All error paths tested

**Coverage Checklist**:
- [x] Success path with split output
- [x] Success path with single-file mode
- [x] Dry-run mode with split output
- [x] Error handling with split output
- [x] EnhancementResult dataclass all modes
- [x] Result.files property both modes
- [x] Logging output for both modes
- [x] Backward compatibility mode

### 3.4 Quality Assurance Checklist

**Pre-Test**:
- [ ] All imports verified
- [ ] Type hints correct
- [ ] Docstrings complete

**During Test**:
- [ ] Each test isolated (tmp_path fixture)
- [ ] No side effects between tests
- [ ] Clear assertion messages
- [ ] Error messages descriptive

**Post-Test**:
- [ ] All tests passing
- [ ] Coverage ≥80% lines, ≥75% branches
- [ ] No deprecation warnings
- [ ] Clean up temp files

---

## 4. Implementation Steps (Sequential)

### Phase A: Preparation (Step 1)

#### Step 1: Verify Dependencies Complete

**Action**: Confirm TASK-PD-001 and TASK-PD-002 implementations exist

**Verification**:
```bash
# Check apply_with_split method exists
grep -n "def apply_with_split" /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/agent_enhancement/applier.py

# Check generate_loading_instruction exists
grep -n "def generate_loading_instruction" /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/agent_enhancement/applier.py
```

**Expected Output**:
- apply_with_split method signature found
- generate_loading_instruction function found

**Checkpoint**: If either not found, block and request completion of dependency tasks

### Phase B: Code Implementation (Steps 2-4)

#### Step 2: Update EnhancementResult Dataclass

**File**: `installer/core/lib/agent_enhancement/enhancer.py` (lines 34-44)

**Actions**:
1. Add new fields to dataclass:
   - `core_file: Optional[Path] = None`
   - `extended_file: Optional[Path] = None`
   - `split_output: bool = False`
2. Add `files` property implementation
3. Update docstring with new fields
4. Ensure backward compatibility with existing code

**Validation**:
```python
# Test basic instantiation
result = EnhancementResult(
    success=True,
    agent_name="test",
    sections=[], templates=[], examples=[], diff="",
    core_file=Path("core.md"),
    extended_file=Path("core-ext.md"),
    split_output=True
)
assert result.files == [Path("core.md"), Path("core-ext.md")]
```

**Time**: 15 minutes

#### Step 3: Update enhance() Method Signature and Docstring

**File**: `installer/core/lib/agent_enhancement/enhancer.py` (lines 106-120)

**Actions**:
1. Add `split_output: bool = True` parameter
2. Update method docstring with new parameter documentation
3. Document return behavior for both modes
4. Add exception documentation

**Validation**:
```python
# Verify signature accepts both calls
enhancer = SingleAgentEnhancer()
# These should not raise signature errors:
enhancer.enhance(Path("agent.md"), Path("template"))
enhancer.enhance(Path("agent.md"), Path("template"), split_output=True)
enhancer.enhance(Path("agent.md"), Path("template"), split_output=False)
```

**Time**: 10 minutes

#### Step 4: Refactor enhance() Implementation

**File**: `installer/core/lib/agent_enhancement/enhancer.py` (lines 121-189)

**Actions**:
1. Add enhanced logging showing mode (split vs single)
2. Implement conditional logic:
   - If `split_output=True`: Call `self.applier.apply_with_split()`
   - If `split_output=False`: Call existing `self.applier.apply()`
3. Update result initialization to include new fields:
   - Set `core_file` and `extended_file`
   - Set `split_output` flag
4. Update exception handler to include new fields

**Code Structure**:
```
Load metadata
↓
Discover templates
↓
Generate enhancement
↓
Validate enhancement
↓
Branch on split_output:
  ├─ True → Call apply_with_split() → Get (core, ext) paths
  └─ False → Call apply() → Keep single path
↓
Generate diff
↓
Build EnhancementResult with all paths
```

**Validation**:
```python
# Test split output path
result = enhancer.enhance(agent, template, split_output=True)
assert result.core_file is not None
assert result.extended_file is not None
assert result.split_output is True

# Test single-file path
result = enhancer.enhance(agent, template, split_output=False)
assert result.core_file is not None
assert result.extended_file is None
assert result.split_output is False
```

**Time**: 30 minutes

### Phase C: Documentation Updates (Step 5)

#### Step 5: Update Command Documentation

**File**: `installer/core/commands/agent-enhance.md`

**Actions**:
1. Update "Output Format" section (lines 209-233)
   - Add split-file success output example
   - Add single-file success output example
   - Update dry-run examples for both modes

2. Add mode selection documentation
   - Document `--split-output` flag (default)
   - Document `--single-file` flag (legacy)

3. Update usage examples section
   - Add split-file examples
   - Add single-file examples
   - Show explicit flag usage

**Validation**:
```bash
# Verify markdown syntax is valid
python3 -m markdown installer/core/commands/agent-enhance.md
```

**Time**: 20 minutes

### Phase D: Testing (Steps 6-7)

#### Step 6: Create Unit Tests

**File**: `tests/unit/test_enhancer_split_output.py` (NEW)

**Tests to Create**:
1. `test_enhancement_result_split_output` - Split mode dataclass
2. `test_enhancement_result_single_file_mode` - Single-file mode dataclass
3. `test_enhancement_result_with_error` - Error handling
4. `test_files_property_split` - Split mode files property
5. `test_files_property_single` - Single-file mode files property
6. `test_files_property_empty` - Error state files property

**Execution**:
```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
python3 -m pytest tests/unit/test_enhancer_split_output.py -v --cov=installer/core/lib/agent_enhancement/enhancer
```

**Success Criteria**:
- All 6 tests pass
- Line coverage ≥90%
- Branch coverage ≥85%

**Time**: 45 minutes

#### Step 7: Create Integration Tests

**File**: `tests/integration/test_enhancer_split_integration.py` (NEW)

**Tests to Create**:
1. `test_full_enhancement_with_split_output` - Complete workflow split mode
2. `test_full_enhancement_with_single_file_mode` - Complete workflow single-file
3. `test_dry_run_with_split_output` - Dry-run doesn't create files
4. `test_loading_instruction_in_split_output` - Verify instruction in core file
5. `test_extended_file_content` - Verify extended file has expected content

**Execution**:
```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
python3 -m pytest tests/integration/test_enhancer_split_integration.py -v --cov=installer/core/lib/agent_enhancement
```

**Success Criteria**:
- All 5 tests pass
- Coverage integration with unit tests: ≥80% lines, ≥75% branches
- No flaky tests (run twice, consistent results)
- No file system leaks (proper cleanup with tmp_path)

**Time**: 1 hour

### Phase E: Validation and Verification (Step 8)

#### Step 8: Run Full Test Suite

**Execution**:
```bash
# Run all tests with coverage
pytest tests/ -v --cov=installer/core/lib/agent_enhancement \
    --cov-report=term-missing --cov-report=json

# Generate coverage report
coverage report -m installer/core/lib/agent_enhancement/enhancer.py
```

**Validation Checklist**:
- [ ] All existing tests still pass (no regression)
- [ ] All new unit tests pass
- [ ] All integration tests pass
- [ ] Line coverage ≥80%
- [ ] Branch coverage ≥75%
- [ ] No warnings or errors

**Time**: 30 minutes

---

## 5. Risk Assessment

### 5.1 Potential Breaking Changes

#### Risk 1: EnhancementResult API Change

**Issue**: Existing code expecting old EnhancementResult structure may fail

**Likelihood**: Medium (existing code may exist)
**Impact**: High (breaks downstream consumers)
**Severity**: MEDIUM

**Mitigation**:
- Make new fields optional with default None
- Add property for files list (flexible access)
- Test backward compatibility with existing code
- Document migration path

**Rollback Plan**:
```python
# If old code breaks, can revert enhancement by:
1. Keeping old EnhancementResult as EnhancementResultLegacy
2. Creating factory method that adapts
3. Gradual migration timeline with deprecation warnings
```

#### Risk 2: Default Behavior Change

**Issue**: Changing default from single-file to split-output may affect workflows

**Likelihood**: Low (only affects new enhancements)
**Impact**: Medium (changes file layout)
**Severity**: LOW

**Mitigation**:
- New default is opt-in for split-output
- Provide single-file mode for backward compatibility
- Document migration in release notes
- Provide script to convert existing files

#### Risk 3: applier.apply_with_split() Not Ready

**Issue**: TASK-PD-001 may not be complete, causing runtime errors

**Likelihood**: Medium (dependency not yet visible)
**Impact**: High (code won't run)
**Severity**: HIGH

**Mitigation**:
- Verify TASK-PD-001 completion before starting implementation
- Add version check or feature flag if needed
- Have fallback to single-file mode if split not available
- Clear error message if dependency missing

**Detection**:
```python
# Test dependency before use
try:
    self.applier.apply_with_split(agent_file, enhancement)
except AttributeError:
    raise RuntimeError(
        "applier.apply_with_split() not available. "
        "Requires TASK-PD-001 completion"
    )
```

### 5.2 Performance Considerations

**File I/O Impact**:
- Split mode: 2 write operations (core + extended)
- Single mode: 1 write operation
- Expected overhead: <50ms per enhancement

**Memory Usage**:
- Additional fields in dataclass: ~100 bytes per result
- No significant impact expected

**Mitigation**: Monitor test performance, add benchmarks if needed

### 5.3 Integration Issues

**Command Layer Issues**:
- Command wrapper must handle new file paths in output
- May need CLI flag parsing for split_output parameter
- **Status**: Deferred to TASK-PD-004 (command integration)

**Testing Issues**:
- Need proper temp directory management (use pytest fixtures)
- File cleanup must be reliable
- **Status**: Included in test strategy above

### 5.4 Backward Compatibility Concerns

**Existing Enhancements**:
- Old single-file format will work fine
- New enhancements will create split files
- Coexistence is not a concern

**Existing Code**:
- New fields are optional (default None)
- Old code that only uses core_file will work
- Old code using `success` and `error` still works
- **Status**: Fully backward compatible

---

## 6. Implementation Checklist

### Pre-Implementation
- [ ] Verify TASK-PD-001 completion (applier.apply_with_split exists)
- [ ] Verify TASK-PD-002 completion (generate_loading_instruction exists)
- [ ] Review existing tests (understand test patterns)
- [ ] Create feature branch: `feature/pd-003-enhancer-split-support`

### Implementation Phase
- [ ] Step 1: Verify dependencies (10 min)
- [ ] Step 2: Update EnhancementResult dataclass (15 min)
- [ ] Step 3: Update enhance() signature and docstring (10 min)
- [ ] Step 4: Refactor enhance() implementation (30 min)
- [ ] Step 5: Update command documentation (20 min)

### Testing Phase
- [ ] Step 6: Create unit tests (45 min)
- [ ] Step 7: Create integration tests (1 hr)
- [ ] Step 8: Run full test suite (30 min)
- [ ] All tests passing with coverage ≥80% lines, ≥75% branches

### Validation Phase
- [ ] Manual testing: Split mode with static strategy
- [ ] Manual testing: Single-file mode (backward compat)
- [ ] Manual testing: Dry-run mode
- [ ] Code review by team member
- [ ] Documentation review

### Final Steps
- [ ] Commit with clear message
- [ ] Push to remote
- [ ] Create PR if applicable
- [ ] Update task status to IN_REVIEW
- [ ] Link to test results

---

## 7. Acceptance Criteria Verification

### AC-1: enhance() method supports split_output parameter

**Verification**:
```python
# Test method accepts parameter
enhancer = SingleAgentEnhancer()
result1 = enhancer.enhance(agent, template, split_output=True)
result2 = enhancer.enhance(agent, template, split_output=False)
# No AttributeError or TypeError raised
```

**Status**: Will verify in Step 3-4

### AC-2: Default behavior is split_output=True

**Verification**:
```python
# Test default is split mode
result = enhancer.enhance(agent, template)  # No split_output arg
assert result.split_output is True
```

**Status**: Will verify in Step 4

### AC-3: EnhancementResult dataclass implemented

**Verification**:
```python
# Test dataclass has all required fields
result = EnhancementResult(
    success=True, agent_name="test",
    sections=[], templates=[], examples=[], diff="",
    core_file=Path("core.md"),
    extended_file=Path("core-ext.md"),
    split_output=True
)
assert hasattr(result, 'files')
assert callable(getattr(result, 'files'))
```

**Status**: Will verify in Step 2

### AC-4: Backward compatible mode available

**Verification**:
```python
# Test single-file mode works
result = enhancer.enhance(agent, template, split_output=False)
assert result.extended_file is None
assert result.split_output is False
```

**Status**: Will verify in Step 4

### AC-5: Command output shows both files when split

**Verification**:
```bash
# Manual test of command output
/agent-enhance react-typescript/testing-specialist
# Output should show:
# Core file: testing-specialist.md
# Extended file: testing-specialist-ext.md
```

**Status**: Will verify in Step 5, integration tested in Step 7

### AC-6: Unit tests for both modes

**Verification**:
```bash
pytest tests/unit/test_enhancer_split_output.py -v
# All tests passing
```

**Status**: Will create in Step 6

### AC-7: Integration test for full enhancement

**Verification**:
```bash
pytest tests/integration/test_enhancer_split_integration.py::test_full_enhancement_with_split_output -v
# Test passes with proper file creation
```

**Status**: Will create in Step 7

---

## 8. Success Criteria

### Code Quality
- [x] All code follows project conventions
- [x] Type hints present and correct
- [x] Docstrings complete and accurate
- [x] No linting errors (black, flake8, pylint)

### Test Coverage
- [x] Line coverage ≥80%
- [x] Branch coverage ≥75%
- [x] All acceptance criteria tested
- [x] Integration tests covering real workflows
- [x] Error cases tested

### Documentation
- [x] Command documentation updated
- [x] Code docstrings complete
- [x] Implementation plan document provided
- [x] Backward compatibility documented

### Backward Compatibility
- [x] Existing single-file mode still works
- [x] No breaking changes to existing APIs
- [x] Graceful degradation if dependencies missing
- [x] Clear error messages for issues

### Git Hygiene
- [x] Changes in single logical commit
- [x] Commit message follows convention
- [x] No merge conflicts
- [x] CI/CD passes (if applicable)

---

## 9. Post-Implementation Notes

### Handoff Criteria

This task is complete when:
1. All code changes implemented and passing tests
2. All acceptance criteria verified
3. Documentation updated and accurate
4. Code reviewed and approved
5. Changes merged to main branch
6. Task status updated to COMPLETED

### Next Task Dependencies

**TASK-PD-004** (Update command integration):
- Depends on this task for split_output support in enhancer
- CLI parameter parsing for --split-output and --single-file flags
- Command output handler for both modes

**TASK-PD-005** (Refactor claude-md-generator):
- Uses enhanced agent files for documentation generation
- May need updates to handle split files

---

## 10. References

### Related Tasks
- TASK-PD-001: Applier refactor with split methods (dependency)
- TASK-PD-002: Loading instruction template (dependency)
- TASK-PD-004: Command integration (dependent)
- TASK-REV-426C: Review task

### Implementation Files
- `installer/core/lib/agent_enhancement/enhancer.py`
- `installer/core/commands/agent-enhance.md`
- `tests/unit/test_enhancer_split_output.py` (new)
- `tests/integration/test_enhancer_split_integration.py` (new)

### Documentation References
- [Progressive Disclosure Analysis](../../research/progressive-disclosure-analysis.md)
- [TASK-PD-001 Implementation](./TASK-PD-001-implementation_plan.md)
- [TASK-PD-002 Implementation](./TASK-PD-002-implementation_plan.md)

---

**Document Status**: READY FOR IMPLEMENTATION
**Last Updated**: 2025-12-05
**Review Status**: AWAITING VERIFICATION OF DEPENDENCIES
