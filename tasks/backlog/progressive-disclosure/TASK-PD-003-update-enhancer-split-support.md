---
id: TASK-PD-003
title: Update enhancer.py to call new applier methods
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-1, foundation, enhancer]
complexity: 5
blocked_by: [TASK-PD-002]
blocks: [TASK-PD-004]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update enhancer.py to call new applier methods

## Phase

**Phase 1: Foundation**

## Description

Update `installer/global/lib/agent_enhancement/enhancer.py` to use the new `apply_with_split()` method from the applier, enabling progressive disclosure output.

## Current State

- `enhancer.py` (576 lines) calls `self.applier.apply(agent_file, enhancement)`
- Single file output model
- No awareness of split files

## Target State

- `enhance()` method supports split output mode
- Default behavior produces split files (core + extended)
- Returns both file paths for validation
- Maintains backward compatibility option

## Implementation

### Modify enhance() Method

```python
def enhance(
    self,
    agent_file: Path,
    template_dir: Path,
    split_output: bool = True  # Default to progressive disclosure
) -> EnhancementResult:
    """Enhance agent file with template-specific content.

    Args:
        agent_file: Path to agent markdown file
        template_dir: Path to template directory for context
        split_output: If True, create separate core and extended files

    Returns:
        EnhancementResult with paths to created/modified files
    """
    # Generate enhancement content
    enhancement = self._generate_enhancement(agent_file, template_dir)

    if split_output:
        core_path, ext_path = self.applier.apply_with_split(agent_file, enhancement)
        return EnhancementResult(
            core_file=core_path,
            extended_file=ext_path,
            split_output=True
        )
    else:
        # Backward compatible single-file mode
        result_path = self.applier.apply(agent_file, enhancement)
        return EnhancementResult(
            core_file=result_path,
            extended_file=None,
            split_output=False
        )
```

### New EnhancementResult Model

```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement operation."""
    core_file: Path
    extended_file: Optional[Path]
    split_output: bool

    @property
    def files(self) -> List[Path]:
        """Return all created/modified files."""
        if self.extended_file:
            return [self.core_file, self.extended_file]
        return [self.core_file]
```

### Update Command Integration

The `/agent-enhance` command should be updated to handle the new result:

```python
# In agent-enhance command handler
result = enhancer.enhance(agent_file, template_dir)

if result.split_output:
    print(f"Core file: {result.core_file}")
    print(f"Extended file: {result.extended_file}")
else:
    print(f"Enhanced: {result.core_file}")
```

## Acceptance Criteria

- [ ] `enhance()` method supports `split_output` parameter
- [ ] Default behavior is `split_output=True` (progressive disclosure)
- [ ] `EnhancementResult` dataclass implemented
- [ ] Backward compatible mode available (`split_output=False`)
- [ ] Command output shows both files when split
- [ ] Unit tests for both modes
- [ ] Integration test: full enhancement with split output

## Test Strategy

```python
def test_enhance_with_split():
    """Test enhancement produces split output by default."""
    enhancer = AgentEnhancer()
    result = enhancer.enhance(agent_file, template_dir)

    assert result.split_output is True
    assert result.core_file.exists()
    assert result.extended_file.exists()
    assert result.extended_file.stem.endswith('-ext')

def test_enhance_single_file_mode():
    """Test backward compatible single file mode."""
    enhancer = AgentEnhancer()
    result = enhancer.enhance(agent_file, template_dir, split_output=False)

    assert result.split_output is False
    assert result.core_file.exists()
    assert result.extended_file is None
```

## Files to Modify

1. `installer/global/lib/agent_enhancement/enhancer.py` - Main changes
2. `installer/global/lib/agent_enhancement/models.py` - Add EnhancementResult
3. `installer/global/commands/agent-enhance.md` - Update output documentation

## Estimated Effort

**1 day**

## Dependencies

- TASK-PD-001 (applier refactor)
- TASK-PD-002 (loading instruction template)
