---
id: TASK-ENH-SIZE-LIMIT
title: Add Configurable CLAUDE.md Size Limit Flag
status: backlog
task_type: implementation
created: 2025-12-10T16:30:00Z
updated: 2025-12-10T16:30:00Z
priority: low
tags: [template-create, enhancement, configuration]
complexity: 3
implementation_mode: direct
conductor_workspace: template-fix-wave2-flag
wave: 2
parent_review: TASK-REV-TC01
---

# Add Configurable CLAUDE.md Size Limit Flag

## Problem Statement

Users with complex codebases may want to override the 10KB core content limit for CLAUDE.md during evaluation or development, without permanently modifying the codebase.

## Use Cases

1. **Evaluation**: Testing templates with large codebases before optimization
2. **Development**: Debugging size validation issues
3. **Special cases**: Codebases where full context is required in core

## Acceptance Criteria

- [ ] `--claude-md-size-limit 50KB` allows 50KB core content
- [ ] Flag accepts KB, MB suffixes (case-insensitive)
- [ ] Default remains 10KB when flag not specified
- [ ] Invalid format shows helpful error message
- [ ] Flag documented in template-create.md

## Technical Specification

### File 1: template-create.md

**Location**: `installer/global/commands/template-create.md`

#### Change: Add flag documentation (in Optional Options section)

```markdown
--claude-md-size-limit SIZE  Maximum size for core CLAUDE.md content
                             Format: NUMBER[KB|MB] (e.g., 15KB, 50KB, 1MB)
                             Default: 10KB
                             Use for complex codebases that exceed default limit
                             Example: /template-create --claude-md-size-limit 50KB
```

### File 2: template_create_orchestrator.py

**Location**: `installer/global/commands/lib/template_create_orchestrator.py`

#### Change 1: Add config field (modify `OrchestrationConfig` dataclass, ~line 105)

```python
@dataclass
class OrchestrationConfig:
    """Configuration for template creation orchestration"""
    codebase_path: Optional[Path] = None
    output_path: Optional[Path] = None
    output_location: str = 'global'
    max_templates: Optional[int] = None
    dry_run: bool = False
    save_analysis: bool = False
    no_agents: bool = False
    verbose: bool = False
    skip_validation: bool = False
    auto_fix_templates: bool = True
    interactive_validation: Optional[bool] = None
    validate: bool = False
    resume: bool = False
    custom_name: Optional[str] = None
    create_agent_tasks: bool = True
    split_claude_md: bool = True
    claude_md_size_limit: int = 10 * 1024  # NEW: Default 10KB in bytes
```

#### Change 2: Add parse method (add as static method in orchestrator)

```python
@staticmethod
def parse_size_limit(size_str: str) -> int:
    """
    Parse size limit string like '15KB' or '1MB' to bytes.

    Args:
        size_str: Size string with optional KB/MB suffix

    Returns:
        Size in bytes

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> TemplateCreateOrchestrator.parse_size_limit('15KB')
        15360
        >>> TemplateCreateOrchestrator.parse_size_limit('1MB')
        1048576
        >>> TemplateCreateOrchestrator.parse_size_limit('10240')
        10240
    """
    size_str = size_str.upper().strip()

    if size_str.endswith('KB'):
        try:
            return int(size_str[:-2]) * 1024
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}. Expected NUMBER[KB|MB]")
    elif size_str.endswith('MB'):
        try:
            return int(size_str[:-2]) * 1024 * 1024
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}. Expected NUMBER[KB|MB]")
    else:
        try:
            return int(size_str)  # Assume bytes
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}. Expected NUMBER[KB|MB]")
```

#### Change 3: Pass limit to generator (modify `_write_claude_md_split`, ~line 1656)

```python
def _write_claude_md_split(self, output_path: Path) -> bool:
    """Write split CLAUDE.md output for progressive disclosure."""
    try:
        generator = ClaudeMdGenerator(
            self.analysis,
            agents=self.agents,
            output_path=output_path
        )

        # Generate split output with configurable size limit
        split_output = generator.generate_split(
            max_core_size=self.config.claude_md_size_limit  # Pass limit
        )

        # ... rest of method unchanged
```

### File 3: models.py

**Location**: `installer/global/lib/template_generator/models.py`

#### Change: Make limit configurable in `validate_size_constraints` (lines 409-422)

```python
def validate_size_constraints(self, max_core_size: int = 10 * 1024) -> tuple[bool, Optional[str]]:
    """
    Validate that core content doesn't exceed size limit.

    Args:
        max_core_size: Maximum allowed size in bytes (default 10KB)

    Returns:
        Tuple of (is_valid, error_message)
    """
    core_size = self.get_core_size()

    if core_size > max_core_size:
        return False, (
            f"Core content exceeds {max_core_size / 1024:.0f}KB limit: "
            f"{core_size / 1024:.2f}KB. "
            f"Use --claude-md-size-limit to override."
        )

    return True, None
```

### File 4: claude_md_generator.py

**Location**: `installer/global/lib/template_generator/claude_md_generator.py`

#### Change: Accept limit in `generate_split` method

```python
def generate_split(self, max_core_size: int = 10 * 1024) -> TemplateSplitOutput:
    """
    Generate split CLAUDE.md output with size validation.

    Args:
        max_core_size: Maximum allowed core content size in bytes

    Returns:
        TemplateSplitOutput with validated core size

    Raises:
        ValueError: If core content exceeds max_core_size
    """
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    output = TemplateSplitOutput(
        core_content=self._generate_core(),
        patterns_content=self._generate_patterns_extended(),
        reference_content=self._generate_reference_extended(),
        generated_at=timestamp
    )

    # Validate size constraints with configurable limit
    is_valid, error_msg = output.validate_size_constraints(max_core_size)
    if not is_valid:
        raise ValueError(f"Size validation failed: {error_msg}")

    return output
```

## Test Cases

1. **Default**: No flag → 10KB limit enforced
2. **Override KB**: `--claude-md-size-limit 50KB` → 50KB limit
3. **Override MB**: `--claude-md-size-limit 1MB` → 1MB limit
4. **Bytes only**: `--claude-md-size-limit 51200` → 51200 bytes
5. **Invalid format**: `--claude-md-size-limit abc` → Error message
6. **Case insensitive**: `--claude-md-size-limit 50kb` → 50KB limit

## Execution

This task uses **direct implementation** (not `/task-work`):

```bash
# 1. Add config field to OrchestrationConfig
# 2. Add parse_size_limit static method
# 3. Update _write_claude_md_split to pass limit
# 4. Update models.py validate_size_constraints
# 5. Update claude_md_generator.py generate_split
# 6. Document in template-create.md
# 7. Run tests
pytest tests/unit/test_orchestrator_split_claude_md.py -v
```

## Verification

```bash
# Test with default (should fail on complex codebase)
cd ~/Projects/MyDrive
/template-create --name mydrive-test
# Expected: Size validation warning

# Test with override (should succeed)
/template-create --name mydrive-test --claude-md-size-limit 50KB
# Expected: Success with larger core content

# Test invalid format
/template-create --name mydrive-test --claude-md-size-limit invalid
# Expected: Error message about format
```

## Notes

- This is a workaround, not a solution - prefer TASK-FIX-CLMD-SIZE for proper fix
- Flag is useful for debugging and evaluation
- Default behavior unchanged (10KB limit)
