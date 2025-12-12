# Implementation Guide: Guidance Architecture Formalization

## Wave Breakdown

### Wave 1: Generator Fixes (Parallel)

**TASK-GA-001** and **TASK-GA-002** can be implemented in parallel as they modify different parts of the generator.

| Task | Workspace | Method | Files |
|------|-----------|--------|-------|
| TASK-GA-001 | guidance-architecture-wave1-1 | task-work | `rules_structure_generator.py` |
| TASK-GA-002 | guidance-architecture-wave1-2 | task-work | `rules_structure_generator.py`, validation module |

**Estimated Duration**: 2-4 hours combined

### Wave 2: Documentation (Parallel)

**TASK-GA-003** and **TASK-GA-004** can be completed in parallel after Wave 1.

| Task | Workspace | Method | Files |
|------|-----------|--------|-------|
| TASK-GA-003 | guidance-architecture-wave2-1 | direct | `docs/guides/rules-structure-guide.md` |
| TASK-GA-004 | guidance-architecture-wave2-2 | direct | `CLAUDE.md`, `.claude/CLAUDE.md` |

**Estimated Duration**: 1-2 hours combined

## Execution Strategy

### Using Conductor (Recommended)

```bash
# Wave 1: Start both generator tasks in parallel
conductor run guidance-architecture-wave1-1 "/task-work TASK-GA-001"
conductor run guidance-architecture-wave1-2 "/task-work TASK-GA-002"

# Wait for Wave 1 completion

# Wave 2: Documentation tasks (can be direct edits)
# In main worktree:
# - Edit docs/guides/rules-structure-guide.md
# - Edit CLAUDE.md
```

### Sequential Execution

```bash
# Wave 1
/task-work TASK-GA-001
/task-work TASK-GA-002

# Wave 2
# Direct edits to documentation files
```

## Key Implementation Details

### TASK-GA-001: Generator Slim Guidance

The `_generate_guidance_rules()` method at line 330 should:

1. **Extract boundaries** from enhanced agent content (ALWAYS/NEVER/ASK sections)
2. **Extract capability summary** (first 5 items only)
3. **Generate reference** to full agent file
4. **Target size**: <3KB per guidance file

**Example output structure**:
```markdown
---
paths: ["**/*store*", "**/*context*"]
applies_when: "Working with state management"
agent: react-state-specialist
---

# React State Specialist

## Purpose
[1-2 sentence summary]

## Technologies
[Comma-separated list]

## Boundaries

### ALWAYS
[Extracted from agent]

### NEVER
[Extracted from agent]

### ASK
[Extracted from agent]

## When This Agent Is Used
[Brief description]

## See Also
- Full agent: `agents/react-state-specialist.md`
- Extended: `agents/react-state-specialist-ext.md`
```

### TASK-GA-002: Size Validation

Add validation to Phase 7 (Validation) of `/template-create`:

```python
def _validate_guidance_sizes(self, rules_dir: Path) -> List[ValidationIssue]:
    """Validate guidance files stay under size threshold."""
    MAX_GUIDANCE_SIZE = 5 * 1024  # 5KB
    issues = []

    guidance_dir = rules_dir / "guidance"
    if guidance_dir.exists():
        for file in guidance_dir.glob("*.md"):
            size = file.stat().st_size
            if size > MAX_GUIDANCE_SIZE:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Guidance file {file.name} exceeds 5KB ({size} bytes)",
                    suggestion="Consider extracting detailed content to agent file"
                ))
    return issues
```

### TASK-GA-003 & TASK-GA-004: Documentation

Add a new section to `rules-structure-guide.md`:

```markdown
## Guidance vs Agent Files

GuardKit templates use two complementary file types for specialist guidance:

| Aspect | agents/{name}.md | rules/guidance/{slug}.md |
|--------|------------------|--------------------------|
| Purpose | Task tool subprocess context | Path-triggered hints |
| Loading | Explicit (Task tool, @mention) | Automatic (file path match) |
| Size | Full content (6-12KB) | Slim summary (<3KB) |
| Content | Role, capabilities, examples | Boundaries, brief summary, references |

**Source of Truth**: `agents/` files are authoritative. Guidance files are derived summaries.
```

## Testing Strategy

### Unit Tests (TASK-GA-001)

```python
def test_generate_slim_guidance():
    """Guidance should be slim summary, not full copy."""
    generator = RulesStructureGenerator(...)
    guidance = generator._generate_guidance_rules(agent)

    assert len(guidance) < 3000  # Under 3KB
    assert "## Boundaries" in guidance
    assert "### ALWAYS" in guidance
    assert "## See Also" in guidance
    assert "Full agent:" in guidance

def test_guidance_not_full_copy():
    """Guidance should not contain full agent content."""
    generator = RulesStructureGenerator(...)
    guidance = generator._generate_guidance_rules(agent)

    # Should NOT contain detailed sections
    assert "## Extended Reference" not in guidance
    assert "## Common Testing Patterns" not in guidance
```

### Integration Tests (TASK-GA-002)

```python
def test_guidance_size_validation():
    """Large guidance files should trigger warning."""
    validator = TemplateValidator(template_path)
    issues = validator.validate()

    # Find size warnings
    size_warnings = [i for i in issues if "exceeds 5KB" in i.message]
    assert len(size_warnings) == 0  # All guidance files should pass
```

## Rollback Plan

If issues are discovered:
1. Generator changes are isolated to `_generate_guidance_rules()`
2. Existing manual guidance files are NOT regenerated (preserved)
3. Validation is warning-only (non-blocking)

## Success Metrics

- [ ] All new guidance files <3KB
- [ ] Zero validation warnings on existing templates
- [ ] Documentation clearly explains the two-file pattern
