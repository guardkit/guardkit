---
id: TASK-GA-001
title: Fix generator to generate slim guidance files
status: completed
task_type: implementation
created: 2025-12-11T20:00:00Z
updated: 2025-12-11T21:30:00Z
completed: 2025-12-11T21:30:00Z
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

- [x] `_generate_guidance_rules()` extracts only boundaries and summary from enhanced agent
- [x] Generated guidance files are <3KB
- [x] Generated guidance includes "See Also" references to agent files
- [x] Existing manual guidance files are NOT overwritten (preserves current pattern)
- [x] Unit tests verify slim generation

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

## Implementation Summary

### Changes Made

1. **Added 4 new helper methods to `RulesStructureGenerator`**:
   - `_extract_boundaries()`: Parses ALWAYS/NEVER/ASK sections from enhanced agent content
   - `_extract_frontmatter_field()`: Extracts specific fields from YAML frontmatter
   - `_extract_section()`: Generic markdown section extractor
   - `_extract_capability_summary()`: Extracts first N capabilities (default 5)
   - `_create_slim_guidance()`: Assembles slim guidance file (~2-3KB) from enhanced content

2. **Modified `_generate_guidance_rules()` method**:
   - Changed from copying full enhanced content to generating slim guidance
   - Maintains backward compatibility (falls back to stub generation when no enhanced agent exists)
   - Preserves path inference logic

3. **Added comprehensive unit tests**:
   - Created `tests/unit/lib/template_generator/test_rules_structure_generator.py`
   - 10 tests covering all new functionality
   - Tests verify size constraints (<3KB), boundary extraction, and reference generation
   - All tests passing ✅

### Results

- **Coverage improvement**: `rules_structure_generator.py` coverage increased from 20% to 54%
- **Size validation**: Tests confirm generated guidance files are under 3KB
- **Structure validation**: Slim guidance includes all required sections (Purpose, Technologies, Boundaries, Capabilities, See Also)
- **Backward compatibility**: Non-enhanced agents still use stub generation

### Files Modified

1. `installer/core/lib/template_generator/rules_structure_generator.py` (+207 lines)
2. `tests/unit/lib/template_generator/test_rules_structure_generator.py` (new file, 317 lines)

### Test Results

```
10 passed in 1.71s
Coverage: 54% (was 20%)
```
