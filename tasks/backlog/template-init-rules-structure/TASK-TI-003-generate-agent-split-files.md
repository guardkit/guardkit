---
id: TASK-TI-003
title: Generate agent split files in template-init command
status: backlog
created: 2025-12-12T10:45:00Z
updated: 2025-12-12T10:45:00Z
priority: high
tags: [template-init, progressive-disclosure, agents, python, implementation]
complexity: 5
implementation_method: task-work
development_mode: tdd
wave: 2
conductor_workspace: template-init-rules-wave2-2
parent_feature: template-init-rules-structure
---

# Task: Generate Agent Split Files in template-init Command

## Description

Modify agent generation in `/template-init` to produce split files following the progressive disclosure pattern: a core file (`agent.md`) and an extended file (`agent-ext.md`).

## Implementation Method

**/task-work** (TDD recommended) - Modifies core agent generation logic, requires test coverage.

## What to Build

### Agent Splitter Module

Create `installer/core/lib/agent_generator/agent_splitter.py`:

```python
def split_agent_content(agent_content: str) -> tuple[str, str]:
    """
    Split agent content into core and extended parts.

    Returns:
        tuple[str, str]: (core_content, extended_content)

    Core content (~6-10KB):
        - Frontmatter
        - Overview/Purpose
        - Boundaries (ALWAYS/NEVER/ASK)
        - Quick Start (5-10 examples)
        - Capabilities summary
        - Phase integration
        - Loading instructions for extended content

    Extended content (~15-25KB):
        - Detailed code examples (30+)
        - Best practices with full explanations
        - Anti-patterns with code samples
        - Technology-specific guidance
        - Troubleshooting scenarios
    """
```

### Splitting Algorithm

1. **Parse agent content** into sections
2. **Identify core sections**:
   - Frontmatter (always core)
   - Overview/Purpose
   - Boundaries (ALWAYS/NEVER/ASK)
   - Quick Start (first 5-10 examples)
   - Capabilities (summary only)
   - Phase Integration
3. **Identify extended sections**:
   - Detailed Examples (beyond first 10)
   - Best Practices (full explanations)
   - Anti-Patterns
   - Technology-Specific Guidance
   - Troubleshooting
4. **Add cross-references**:
   - Core file: "For detailed examples, see `{agent-name}-ext.md`"
   - Extended file: Reference back to core

### Size Validation

```python
def validate_split_sizes(core: str, extended: str) -> list[str]:
    """
    Validate split file sizes against targets.

    Targets:
        Core: 6-10KB (warning at 15KB)
        Extended: 15-25KB (warning at 30KB)

    Returns:
        List of warnings (empty if all pass)
    """
```

### Integration with Agent Generator

Modify Phase 3 (Agent Generation) to:

1. Generate full agent content (existing logic)
2. Split into core + extended
3. Save both files:
   - `agents/{name}.md`
   - `agents/{name}-ext.md`
4. Log size validation warnings

### Output Structure

```
{template-name}/
├── agents/
│   ├── api-specialist.md           # Core (~8KB)
│   ├── api-specialist-ext.md       # Extended (~20KB)
│   ├── database-specialist.md      # Core (~7KB)
│   ├── database-specialist-ext.md  # Extended (~18KB)
│   └── ...
└── ...
```

## Acceptance Criteria

- [ ] Agent files split into core (`*.md`) and extended (`*-ext.md`)
- [ ] Core files contain boundaries, quick start, capabilities
- [ ] Extended files contain detailed examples, best practices
- [ ] Core files include reference to extended file
- [ ] Size validation warns when targets exceeded
- [ ] All agents properly split (no orphaned files)
- [ ] Unit tests cover splitting algorithm (>80% coverage)
- [ ] Integration test verifies end-to-end flow

## Files to Create/Modify

### Create
- `installer/core/lib/agent_generator/agent_splitter.py`
- `tests/unit/test_agent_splitter.py`

### Modify
- `installer/core/lib/agent_generator/agent_generator.py` (integrate splitter)

## Testing Strategy

### Unit Tests

```python
def test_split_agent_basic():
    """Test basic agent splitting."""
    content = load_test_agent("full-agent.md")
    core, extended = split_agent_content(content)

    assert "## Boundaries" in core
    assert "## Quick Start" in core
    assert "## Detailed Examples" in extended
    assert "## Best Practices" in extended

def test_core_size_target():
    """Test core file meets size target."""
    content = load_test_agent("full-agent.md")
    core, _ = split_agent_content(content)

    assert len(core.encode('utf-8')) <= 15 * 1024  # 15KB max

def test_cross_references_added():
    """Test cross-references between core and extended."""
    content = load_test_agent("full-agent.md")
    core, extended = split_agent_content(content)

    assert "-ext.md" in core  # Reference to extended
    assert "See core file" in extended or "main agent file" in extended

def test_size_validation_warnings():
    """Test size validation produces warnings."""
    core = "x" * (16 * 1024)  # 16KB (over 15KB warning threshold)
    extended = "y" * (31 * 1024)  # 31KB (over 30KB warning threshold)

    warnings = validate_split_sizes(core, extended)

    assert len(warnings) == 2
    assert "core" in warnings[0].lower()
    assert "extended" in warnings[1].lower()
```

### Integration Tests

```python
def test_full_agent_split_flow():
    """Test complete agent split flow during template-init."""
    result = run_template_init_with_qa(
        language="python",
        framework="fastapi",
        architecture="layered"
    )

    # Check all agents have split files
    agents_dir = Path(result.output_dir) / "agents"
    agent_files = list(agents_dir.glob("*.md"))

    # For each core file, extended should exist
    for agent_file in agent_files:
        if not agent_file.name.endswith("-ext.md"):
            ext_file = agent_file.with_name(
                agent_file.stem + "-ext.md"
            )
            assert ext_file.exists(), f"Missing extended file for {agent_file}"
```

## Dependencies

- None (can run parallel with TASK-TI-002)

## Related Tasks

- TASK-TI-002: Rules structure (parallel in Wave 2)
- TASK-TI-005: Guidance file generation (uses split agents as input)
