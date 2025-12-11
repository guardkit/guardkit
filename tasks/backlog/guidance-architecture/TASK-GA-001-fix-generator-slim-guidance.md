---
id: TASK-GA-001
title: Fix generator to generate slim guidance files
status: backlog
task_type: implementation
created: 2025-12-11T20:00:00Z
updated: 2025-12-11T20:00:00Z
priority: high
tags: [generator, rules-structure, guidance, progressive-disclosure]
complexity: 5
parent: TASK-REV-ARCH
related_to: [TASK-GA-002]
implementation_mode: task-work
conductor_workspace: guidance-architecture-wave1-1
wave: 1
---

# Task: Fix Generator to Generate Slim Guidance Files

## Background

The `_generate_guidance_rules()` method in `rules_structure_generator.py` currently copies full enhanced agent content to guidance files when enhanced agents exist. This creates unnecessary duplication.

The correct behavior (as demonstrated in existing manual guidance files) is to generate slim summaries (~2-3KB) with:
- Boundaries (ALWAYS/NEVER/ASK)
- Brief capability summary
- References to full agent file

## Acceptance Criteria

- [ ] `_generate_guidance_rules()` extracts only boundaries and summary from enhanced agent
- [ ] Generated guidance files are <3KB
- [ ] Generated guidance includes "See Also" references to agent files
- [ ] Existing manual guidance files are NOT overwritten (preserves current pattern)
- [ ] Unit tests verify slim generation

## Implementation Details

### File to Modify

`installer/core/lib/template_generator/rules_structure_generator.py`

### Current Code (lines 330-382)

```python
def _generate_guidance_rules(self, agent) -> str:
    # ...
    if enhanced_content:
        # PROBLEM: This copies full content
        return self._merge_paths_into_frontmatter(enhanced_content, paths_filter)
```

### Proposed Changes

1. Add `_extract_boundaries()` method to parse ALWAYS/NEVER/ASK sections
2. Add `_extract_capability_summary()` method to get first 5 capabilities
3. Add `_create_slim_guidance()` method to assemble slim file
4. Modify `_generate_guidance_rules()` to use slim generation

### Target Output Structure

```markdown
---
paths: ["**/*store*", "**/*context*"]
applies_when: "Working with state management"
agent: react-state-specialist
---

# React State Specialist

## Purpose
[1-2 sentences from agent description]

## Technologies
[Comma-separated from agent frontmatter]

## Boundaries

### ALWAYS
[Extracted from agent - keep full section]

### NEVER
[Extracted from agent - keep full section]

### ASK
[Extracted from agent - keep full section]

## When This Agent Is Used
[Brief list from agent]

## Capabilities Summary
- [First 5 capabilities only]

## See Also
- Full agent: `agents/react-state-specialist.md`
- Extended reference: `agents/react-state-specialist-ext.md`
```

## Testing

### Unit Tests to Add

```python
def test_generate_slim_guidance_size():
    """Generated guidance should be under 3KB."""
    generator = RulesStructureGenerator(...)
    guidance = generator._generate_guidance_rules(agent_with_enhanced_content)
    assert len(guidance.encode()) < 3000

def test_extract_boundaries():
    """Boundaries should be extracted from agent content."""
    content = "## Boundaries\n### ALWAYS\n- Rule 1\n### NEVER\n- Rule 2"
    boundaries = generator._extract_boundaries(content)
    assert "### ALWAYS" in boundaries
    assert "### NEVER" in boundaries

def test_slim_guidance_has_references():
    """Slim guidance should reference full agent file."""
    guidance = generator._generate_guidance_rules(agent)
    assert "agents/" in guidance
    assert "See Also" in guidance
```

## Notes

- This task focuses on the generator code only
- Documentation updates are in separate tasks (TASK-GA-003, TASK-GA-004)
- Existing template guidance files should NOT be regenerated - they demonstrate the correct pattern
