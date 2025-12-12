---
id: TASK-TI-005
title: Generate guidance files from agents in template-init
status: backlog
created: 2025-12-12T10:45:00Z
updated: 2025-12-12T10:45:00Z
priority: medium
tags: [template-init, guidance, rules-structure, python, implementation]
complexity: 5
implementation_method: task-work
development_mode: tdd
wave: 3
conductor_workspace: template-init-rules-wave3-2
parent_feature: template-init-rules-structure
---

# Task: Generate Guidance Files from Agents in template-init

## Description

Create slim guidance files in `.claude/rules/guidance/` derived from generated agent files, following the architecture documented in `rules-structure-guide.md`.

## Implementation Method

**/task-work** (TDD recommended) - New Python code for content extraction and transformation.

## Background

Per the rules structure guide:
- **Agent files** (`agents/`) are the source of truth (full content, 6-12KB)
- **Guidance files** (`rules/guidance/`) are derived summaries (slim, <3KB)
- Guidance files load automatically on path match
- Agent files load when Task tool invokes specialist

## What to Build

### Guidance Generator Module

Create `installer/core/lib/guidance_generator/`:

```
guidance_generator/
├── __init__.py
├── generator.py          # Main orchestration
├── extractor.py          # Content extraction from agents
└── path_patterns.py      # Path pattern generation
```

### Extraction Logic

From each agent file, extract:

1. **Boundaries** (ALWAYS/NEVER/ASK) - Copy directly
2. **Capability Summary** - Brief 2-3 sentence summary
3. **Reference Link** - Pointer to full agent file
4. **Path Patterns** - Generated from agent's stack/phase metadata

### Guidance File Template

```markdown
---
paths: {generated_paths}
agent: {agent_name}
---

# {Agent Display Name} - Quick Reference

{Brief capability summary from agent}

## Boundaries

### ALWAYS
{Copied from agent}

### NEVER
{Copied from agent}

### ASK
{Copied from agent}

## When to Use

{Brief 2-3 bullet points}

## Full Documentation

For detailed examples and best practices, see:
- Agent: `agents/{agent-name}.md`
- Extended: `agents/{agent-name}-ext.md`
```

### Path Pattern Generation

Generate path patterns based on agent metadata:

```python
def generate_path_patterns(agent_metadata: dict) -> str:
    """
    Generate path patterns from agent stack and capabilities.

    Examples:
        stack: python, fastapi → paths: **/api/**/*.py
        stack: react, typescript → paths: **/*.{ts,tsx}
        phase: testing → paths: **/tests/**
    """
```

**Mapping Rules**:
| Stack/Phase | Path Pattern |
|-------------|--------------|
| python | `**/*.py` |
| typescript | `**/*.{ts,tsx}` |
| react | `**/*.tsx, **/components/**` |
| fastapi | `**/api/**/*.py` |
| testing | `**/tests/**` |
| database | `**/models/**, **/repositories/**` |

### Size Validation

Guidance files must be <3KB (warning at 5KB):

```python
def validate_guidance_size(content: str, name: str) -> list[str]:
    """Validate guidance file meets size target."""
    size_kb = len(content.encode('utf-8')) / 1024
    warnings = []

    if size_kb > 5:
        warnings.append(f"Guidance '{name}' exceeds 5KB ({size_kb:.1f}KB)")
    elif size_kb > 3:
        warnings.append(f"Guidance '{name}' exceeds target 3KB ({size_kb:.1f}KB)")

    return warnings
```

### Integration Point

Call after agent generation and splitting (Phase 3.5):

```python
# In Phase 4.5 Rules Structure Generation
if not args.no_rules_structure:
    # Generate guidance files from agents
    for agent_file in agent_files:
        guidance = generate_guidance_from_agent(agent_file)
        save_guidance(
            content=guidance,
            output_dir=f"{template_dir}/.claude/rules/guidance/"
        )
```

## Acceptance Criteria

- [ ] Guidance files generated in `.claude/rules/guidance/`
- [ ] Boundaries extracted correctly from agents
- [ ] Path patterns generated from agent metadata
- [ ] File size <3KB (warning at 5KB)
- [ ] Cross-references to agent files included
- [ ] Slug names derived from agent names
- [ ] Unit tests cover extraction logic (>80% coverage)
- [ ] Integration test verifies end-to-end flow

## Files to Create/Modify

### Create
- `installer/core/lib/guidance_generator/__init__.py`
- `installer/core/lib/guidance_generator/generator.py`
- `installer/core/lib/guidance_generator/extractor.py`
- `installer/core/lib/guidance_generator/path_patterns.py`
- `tests/unit/test_guidance_generator.py`

### Modify
- Rules generator (TASK-TI-002) to call guidance generator

## Testing Strategy

### Unit Tests

```python
def test_extract_boundaries():
    """Test boundary extraction from agent content."""
    agent_content = load_test_agent("api-specialist.md")
    boundaries = extract_boundaries(agent_content)

    assert "### ALWAYS" in boundaries
    assert "### NEVER" in boundaries
    assert "### ASK" in boundaries
    assert boundaries.count("✅") >= 5  # At least 5 ALWAYS rules
    assert boundaries.count("❌") >= 5  # At least 5 NEVER rules

def test_generate_path_patterns_python():
    """Test path pattern generation for Python stack."""
    metadata = {"stack": ["python", "fastapi"], "phase": "implementation"}
    patterns = generate_path_patterns(metadata)

    assert "**/api/**/*.py" in patterns or "**/*.py" in patterns

def test_guidance_size_validation():
    """Test guidance file size validation."""
    large_content = "x" * (6 * 1024)  # 6KB
    warnings = validate_guidance_size(large_content, "test-agent")

    assert len(warnings) == 1
    assert "exceeds 5KB" in warnings[0]

def test_generate_guidance_complete():
    """Test complete guidance generation."""
    agent_content = load_test_agent("api-specialist.md")
    guidance = generate_guidance_from_agent(agent_content)

    assert "---" in guidance  # Has frontmatter
    assert "paths:" in guidance
    assert "## Boundaries" in guidance
    assert "## Full Documentation" in guidance
    assert len(guidance.encode('utf-8')) < 5 * 1024  # Under 5KB
```

### Integration Tests

```python
def test_full_guidance_generation_flow():
    """Test complete guidance generation during template-init."""
    result = run_template_init_with_qa(
        language="python",
        framework="fastapi",
        architecture="layered"
    )

    guidance_dir = Path(result.output_dir) / ".claude" / "rules" / "guidance"
    assert guidance_dir.exists()

    # Check guidance files exist for each agent
    agents_dir = Path(result.output_dir) / "agents"
    for agent_file in agents_dir.glob("*.md"):
        if not agent_file.name.endswith("-ext.md"):
            # Derive expected guidance filename
            slug = agent_file.stem.replace("-specialist", "")
            guidance_file = guidance_dir / f"{slug}.md"
            assert guidance_file.exists(), f"Missing guidance for {agent_file}"

            # Verify size
            content = guidance_file.read_text()
            assert len(content.encode('utf-8')) < 5 * 1024
```

## Dependencies

- TASK-TI-002: Rules structure generation (integration point)
- TASK-TI-003: Agent split files (input source)

## Related Tasks

- TASK-TI-004: Documentation (parallel in Wave 3)
