---
id: TASK-ENH-DM01
title: Fix agent-enhance to generate discovery metadata in frontmatter
status: in_review
task_type: implementation
created: 2025-12-09
completed: 2025-12-09
priority: high
tags: [bug, agent-enhance, discovery, metadata, progressive-disclosure, HAI-001]
related_tasks: [TASK-REV-A36C, TASK-REV-DM01]
estimated_complexity: 4
source_review: TASK-REV-DM01
architectural_review_score: 88
code_review_score: 95
tests_passed: 12
tests_failed: 0
---

# TASK-ENH-DM01: Fix Agent-Enhance Discovery Metadata Generation

## Summary

The `/agent-enhance` command is not generating discovery metadata (`stack`, `phase`, `capabilities`, `keywords`) in agent frontmatter. This metadata is required for AI-powered agent matching during `/task-work` as documented in HAI-001.

**Source Review**: [TASK-REV-DM01 Review Report](../../.claude/reviews/TASK-REV-DM01-review-report.md)

## Root Cause (from TASK-REV-DM01)

**Primary Root Cause**: The discovery metadata fields are **never requested from the AI** in the prompt, and there is **no code path** to generate or inject these fields anywhere in the enhancement pipeline.

Specifically:
1. `prompt_builder.py` JSON schema only requires `sections`, `related_templates`, `examples`, `boundaries`
2. `parser.py` doesn't validate or extract discovery metadata
3. `applier.py` has no logic to inject metadata into YAML frontmatter
4. `agent-content-enhancer.md` doesn't mention discovery fields

## Evidence

From TASK-REV-A36C and TASK-REV-DM01 reviews:
- 6/7 kartlog agents missing all discovery metadata fields
- Only `svelte-list-view-specialist` has complete metadata (manually added)
- Output logs show AI returns JSON without metadata fields (never requested)

## Acceptance Criteria

### AC1: Prompt Builder Requests Metadata
- [ ] JSON schema in `prompt_builder.py` includes `frontmatter_metadata` object
- [ ] Schema requires `stack`, `phase`, `capabilities`, `keywords` fields
- [ ] Prompt includes instructions for AI to analyze code and derive values

### AC2: Applier Merges Metadata into Frontmatter
- [ ] New method `_merge_frontmatter_metadata()` in `applier.py`
- [ ] Parses existing YAML frontmatter using `frontmatter` library
- [ ] Merges new discovery fields without overwriting existing fields
- [ ] Serializes back to valid YAML

### AC3: Parser Validates Metadata (Graceful)
- [ ] New method `_validate_metadata()` in `parser.py`
- [ ] Validates presence of discovery fields when provided
- [ ] Logs warning for missing metadata (graceful degradation, not blocking)

### AC4: Agent Documentation Updated
- [ ] `agent-content-enhancer.md` includes discovery metadata in Enhancement Structure
- [ ] Examples show how to derive each field from template analysis

### AC5: Tests Pass
- [ ] Unit tests for prompt builder schema
- [ ] Unit tests for applier frontmatter merge
- [ ] Integration test: `/agent-enhance` produces complete metadata

## Implementation Guide

### Step 1: Update Prompt Builder (prompt_builder.py)

**File**: `installer/global/lib/agent_enhancement/prompt_builder.py`

Add to JSON schema after `boundaries` property (~line 112):

```python
"frontmatter_metadata": {
    "type": "object",
    "required": ["stack", "phase", "capabilities", "keywords"],
    "properties": {
        "stack": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "Technology stacks derived from imports/extensions (e.g., ['svelte', 'javascript', 'firebase'])"
        },
        "phase": {
            "type": "string",
            "enum": ["implementation", "review", "testing", "orchestration", "debugging"],
            "description": "Agent's primary role phase based on name/description"
        },
        "capabilities": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "description": "Specific skills (5+ items, derived from template patterns)"
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "description": "Searchable terms for agent discovery"
        }
    }
}
```

Add to `required` array (~line 89): `"frontmatter_metadata"`

Add prompt instructions (~line 127):

```
**Discovery Metadata**: Analyze the templates and agent description to generate:
- `stack`: Technology stacks from file extensions (.svelte, .js), imports, package.json
- `phase`: Agent role - "implementation" for builders, "review" for analyzers, "testing" for testers
- `capabilities`: 5-7 specific skills the agent demonstrates (from template patterns)
- `keywords`: 5-7 searchable terms users might use to find this agent
```

### Step 2: Update Applier (applier.py)

**File**: `installer/global/lib/agent_enhancement/applier.py`

Add new method after `_merge_content()` (~line 255):

```python
def _merge_frontmatter_metadata(
    self,
    original_content: str,
    new_metadata: Dict[str, Any]
) -> str:
    """
    Merge discovery metadata into existing frontmatter.

    Args:
        original_content: Original file content with frontmatter
        new_metadata: Dict with stack, phase, capabilities, keywords

    Returns:
        Content with updated frontmatter
    """
    import frontmatter

    # Parse existing frontmatter
    doc = frontmatter.loads(original_content)

    # Merge new fields (don't overwrite existing)
    for key in ['stack', 'phase', 'capabilities', 'keywords']:
        if key in new_metadata and key not in doc.metadata:
            doc.metadata[key] = new_metadata[key]

    # Serialize back
    return frontmatter.dumps(doc)
```

Update `_merge_content()` to call this when `frontmatter_metadata` present in enhancement:

```python
# At start of _merge_content(), after reading original:
if 'frontmatter_metadata' in enhancement:
    original = self._merge_frontmatter_metadata(
        original,
        enhancement['frontmatter_metadata']
    )
```

### Step 3: Update Parser (parser.py)

**File**: `installer/global/lib/agent_enhancement/parser.py`

Add validation method (~line 190):

```python
def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
    """
    Validate frontmatter_metadata structure.

    Raises ValueError if invalid, logs warning if missing optional fields.
    """
    required_fields = ['stack', 'phase', 'capabilities', 'keywords']

    for field in required_fields:
        if field not in metadata:
            logger.warning(f"Missing metadata field: {field}")
            return  # Graceful - don't block on missing metadata

    # Validate types if present
    if not isinstance(metadata.get('stack', []), list):
        raise ValueError("'stack' must be an array")

    valid_phases = ['implementation', 'review', 'testing', 'orchestration', 'debugging']
    if metadata.get('phase') and metadata['phase'] not in valid_phases:
        raise ValueError(f"Invalid phase: {metadata['phase']}")
```

Update `_validate_basic_structure()` to call when present:

```python
# After boundaries validation:
if 'frontmatter_metadata' in enhancement:
    self._validate_metadata(enhancement['frontmatter_metadata'])
```

### Step 4: Update Agent Documentation

**File**: `installer/global/agents/agent-content-enhancer.md`

Update "Enhancement Structure" section (~line 114) to show:

```yaml
---
name: agent-name
description: One-line description
priority: 7
stack:
  - svelte
  - javascript
phase: implementation
capabilities:
  - SMUI DataTable component implementation
  - Multi-property filtering with URL sync
  - Multi-column sorting with type-aware comparison
keywords:
  - datatable
  - list-view
  - filtering
  - sorting
  - smui
technologies:
  - Svelte
  - JavaScript
tools: [Read, Write, Edit, Grep, Glob]
tags: [relevant, tags]
---
```

## Files to Modify

| File | Changes |
|------|---------|
| `installer/global/lib/agent_enhancement/prompt_builder.py` | Add metadata schema + instructions |
| `installer/global/lib/agent_enhancement/applier.py` | Add `_merge_frontmatter_metadata()` |
| `installer/global/lib/agent_enhancement/parser.py` | Add `_validate_metadata()` |
| `installer/global/agents/agent-content-enhancer.md` | Update Enhancement Structure |

## Testing

1. Run `/agent-enhance kartlog/firestore-repository-specialist --hybrid`
2. Verify all 4 metadata fields generated in frontmatter
3. Run on `svelte-list-view-specialist` (has existing metadata)
4. Verify existing metadata NOT overwritten
5. Run `pytest tests/lib/agent_enhancement/` - all tests pass

## Definition of Done

- [ ] All acceptance criteria met
- [ ] `/agent-enhance` generates all 4 discovery metadata fields
- [ ] Existing metadata is preserved (not overwritten)
- [ ] Build passes
- [ ] Tests pass
- [ ] Manual test on kartlog agents produces complete metadata
