---
id: TASK-PD-002
title: Add loading instruction template generation
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-1, foundation, loading-instruction]
complexity: 4
blocked_by: [TASK-PD-001]
blocks: [TASK-PD-003]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add loading instruction template generation

## Phase

**Phase 1: Foundation**

## Description

Create a standardized loading instruction section that gets added to core agent files, instructing Claude to load the extended reference file before detailed implementation work.

## Loading Instruction Format

```markdown
---

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

## Implementation

### Template Generator Function

```python
def generate_loading_instruction(agent_name: str, ext_filename: str) -> str:
    """Generate loading instruction section for core agent file.

    Args:
        agent_name: Human-readable agent name
        ext_filename: Name of extended file (e.g., 'task-manager-ext.md')

    Returns:
        Markdown section with loading instruction
    """
    return f'''
---

## Extended Reference

Before generating code or performing detailed implementation, load the extended reference:

```bash
cat agents/{ext_filename}
```

**Extended file contains**:
- 30+ detailed code examples
- Template best practices with full explanations
- Common anti-patterns to avoid
- Technology-specific guidance
- MCP integration details
- Troubleshooting scenarios
'''
```

### Integration with Applier

Add to `applier.py`:

```python
def _add_loading_instruction(self, core_content: str, agent_path: Path) -> str:
    """Add loading instruction to core content.

    Args:
        core_content: Core agent content
        agent_path: Path to agent file (for deriving ext filename)

    Returns:
        Core content with loading instruction appended
    """
    ext_filename = f"{agent_path.stem}-ext.md"
    instruction = generate_loading_instruction(
        agent_name=self._extract_agent_name(core_content),
        ext_filename=ext_filename
    )
    return core_content + instruction
```

## Acceptance Criteria

- [ ] `generate_loading_instruction()` function implemented
- [ ] Loading instruction follows standardized format
- [ ] Instruction includes explicit `cat` command
- [ ] Instruction lists what extended file contains
- [ ] Integration with applier's `apply_with_split()` method
- [ ] Unit tests for template generation

## Test Strategy

```python
def test_generate_loading_instruction():
    """Test loading instruction generation."""
    instruction = generate_loading_instruction(
        agent_name="Task Manager",
        ext_filename="task-manager-ext.md"
    )

    assert "## Extended Reference" in instruction
    assert "cat agents/task-manager-ext.md" in instruction
    assert "30+ detailed code examples" in instruction
    assert "anti-patterns" in instruction

def test_loading_instruction_in_split_output():
    """Test loading instruction appears in split core file."""
    applier = EnhancementApplier()
    core_path, ext_path = applier.apply_with_split(agent_path, enhancement)

    core_content = core_path.read_text()
    assert "## Extended Reference" in core_content
    assert ext_path.name in core_content
```

## Files to Modify

1. `installer/global/lib/agent_enhancement/applier.py` - Add loading instruction integration
2. `installer/global/lib/agent_enhancement/templates.py` - New file for instruction template (optional)

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-001 (applier refactor) must be complete
