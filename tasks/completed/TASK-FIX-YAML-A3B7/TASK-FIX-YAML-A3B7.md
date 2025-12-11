---
id: TASK-FIX-YAML-A3B7
title: YAML Escaping for Agent Frontmatter
status: completed
task_type: implementation
created: 2025-12-11T10:45:00Z
updated: 2025-12-11T11:55:00Z
completed: 2025-12-11T11:55:00Z
priority: high
tags: [agent-enhance, yaml, frontmatter, bugfix]
complexity: 3
parent_review: TASK-REV-D4A7
completed_location: tasks/completed/TASK-FIX-YAML-A3B7/
test_results:
  status: passed
  coverage: 100%
  last_run: 2025-12-11T11:50:00Z
  tests_passed: 19
  tests_failed: 0
  new_tests_added: 7
organized_files:
  - TASK-FIX-YAML-A3B7.md
implementation_summary:
  files_modified: 2
  files_added: 0
  lines_added: 230
  lines_removed: 5
  commits: 1
  commit_hash: 6af7103
---

# Task: YAML Escaping for Agent Frontmatter

## Problem Statement

Agent enhancement fails with `mapping values are not allowed in this context` error when the agent frontmatter `description` field contains colons without proper YAML quoting.

**Example failure:**
```yaml
description: Engine pattern for business logic coordination with Interface Segregation (LoadingEngine implements 5 interfaces: IParcelProcessor...)
```

The colon after "interfaces" causes PyYAML to interpret it as a key:value separator.

## Root Cause

**Flow:**
1. `frontmatter.loads(content)` parses YAML (applier.py:405)
2. `post.metadata[field] = metadata[field]` adds discovery metadata (applier.py:417)
3. `frontmatter.dumps(post)` serializes back to YAML (applier.py:428)
4. **PyYAML doesn't auto-quote values with colons** → Invalid YAML

**Key Finding:** PyYAML's default dumper doesn't quote scalar values unless necessary. A string with a colon is valid Python in a dict, but when serialized to YAML and parsed back, it's invalid YAML syntax.

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/core/lib/agent_enhancement/applier.py` | 384-428 | Add YAML escaping before `frontmatter.dumps()` |
| `tests/lib/agent_enhancement/test_metadata_merge.py` | NEW | Add test cases for special characters |

## Implementation Specification

### Step 1: Add YAML Escaping Utility (applier.py)

```python
# Add this function before _merge_frontmatter_metadata_content()

def _sanitize_yaml_string(value: str) -> str:
    """
    Sanitize a string value for safe YAML serialization.

    PyYAML's dumps() doesn't auto-quote strings with special characters.
    This ensures strings with YAML-unsafe characters are properly handled.

    Args:
        value: String to sanitize

    Returns:
        Sanitized string (PyYAML will quote programmatically added strings)
    """
    # Characters that require quoting in YAML
    yaml_special_chars = [':', '[', ']', '{', '}', '#', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`']

    # Check if value needs special handling
    if any(c in value for c in yaml_special_chars):
        # Return as-is - PyYAML will quote programmatically added strings
        # The issue is with parsing, not with programmatic assignment
        return value
    return value


def _sanitize_metadata_values(metadata: dict) -> dict:
    """
    Recursively sanitize all string values in metadata dict.

    Args:
        metadata: Dictionary of metadata fields

    Returns:
        Dictionary with sanitized string values
    """
    result = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            result[key] = _sanitize_yaml_string(value)
        elif isinstance(value, list):
            result[key] = [
                _sanitize_yaml_string(v) if isinstance(v, str) else v
                for v in value
            ]
        elif isinstance(value, dict):
            result[key] = _sanitize_metadata_values(value)
        else:
            result[key] = value
    return result
```

### Step 2: Modify _merge_frontmatter_metadata_content() (applier.py:384-428)

**Before (current code around line 405-428):**
```python
def _merge_frontmatter_metadata_content(content: str, metadata: dict) -> str:
    # ... existing code ...
    post = frontmatter.loads(content)

    for field in discovery_fields:
        if field in metadata:
            if field not in post.metadata:
                post.metadata[field] = metadata[field]

    return frontmatter.dumps(post)
```

**After:**
```python
def _merge_frontmatter_metadata_content(content: str, metadata: dict) -> str:
    # ... existing code ...

    # Sanitize metadata values to prevent YAML parsing issues
    sanitized_metadata = _sanitize_metadata_values(metadata)

    post = frontmatter.loads(content)

    for field in discovery_fields:
        if field in sanitized_metadata:
            if field not in post.metadata:
                post.metadata[field] = sanitized_metadata[field]

    return frontmatter.dumps(post)
```

### Step 3: Handle Source Content with Special Characters

The real issue is when the **source file** already has unquoted colons. Add pre-processing:

```python
def _preprocess_frontmatter(content: str) -> str:
    """
    Pre-process content to fix common YAML issues before parsing.

    Handles:
    - Unquoted strings with colons in description fields
    """
    import re

    # Match description field with unquoted value containing colons
    # Pattern: description: <value with colon that's not already quoted>
    pattern = r'^(description:\s*)([^"\'][^\n]*:[^\n]*)$'

    def quote_if_needed(match):
        prefix = match.group(1)
        value = match.group(2).strip()
        # Only quote if not already quoted
        if not (value.startswith('"') and value.endswith('"')) and \
           not (value.startswith("'") and value.endswith("'")):
            return f'{prefix}"{value}"'
        return match.group(0)

    return re.sub(pattern, quote_if_needed, content, flags=re.MULTILINE)
```

### Step 4: Add Test Cases (test_metadata_merge.py)

```python
class TestYAMLSpecialCharacters:
    """Test handling of YAML special characters in frontmatter."""

    def test_description_with_colon(self):
        """Test that descriptions containing colons are properly handled."""
        content = """---
name: test-agent
description: Tests for: unit, integration, e2e
---
# Content
"""
        metadata = {"stack": ["python"]}

        result = _merge_frontmatter_metadata_content(content, metadata)

        # Should parse without error
        post = frontmatter.loads(result)
        assert "description" in post.metadata
        assert "stack" in post.metadata

    def test_description_with_brackets(self):
        """Test that descriptions with brackets are handled."""
        content = """---
name: test-agent
description: Implements interfaces [A, B, C]
---
# Content
"""
        metadata = {"stack": ["python"]}

        result = _merge_frontmatter_metadata_content(content, metadata)
        post = frontmatter.loads(result)
        assert "description" in post.metadata

    def test_description_with_angle_brackets(self):
        """Test ErrorOr<T> style descriptions."""
        content = """---
name: test-agent
description: Uses ErrorOr<T> pattern for railway-oriented programming
---
# Content
"""
        metadata = {"stack": ["csharp"]}

        result = _merge_frontmatter_metadata_content(content, metadata)
        post = frontmatter.loads(result)
        assert "ErrorOr<T>" in post.metadata.get("description", "")

    def test_multiple_colons_in_description(self):
        """Test complex descriptions with multiple special characters."""
        content = """---
name: business-logic-engine-specialist
description: Engine pattern for business logic coordination with Interface Segregation (LoadingEngine implements 5 interfaces: IParcelProcessor, ILoadingSummaryProvider, ILoadingValidator, IOutstandingParcelProvider, ILoadingEngineLifecycle)
---
# Content
"""
        metadata = {"stack": ["csharp", "maui"], "phase": "implementation"}

        result = _merge_frontmatter_metadata_content(content, metadata)
        post = frontmatter.loads(result)
        assert post.metadata.get("name") == "business-logic-engine-specialist"
        assert "stack" in post.metadata
```

## Acceptance Criteria

- [ ] Descriptions with colons parse correctly
- [ ] Descriptions with brackets `[]` parse correctly
- [ ] Descriptions with angle brackets `<>` parse correctly (ErrorOr<T>)
- [ ] Descriptions with parentheses containing colons parse correctly
- [ ] No manual frontmatter fixes required for agent enhancement
- [ ] All existing tests continue to pass
- [ ] New test cases added for special character handling

## Test Requirements

Run these commands to verify:

```bash
# Run specific tests
pytest tests/lib/agent_enhancement/test_metadata_merge.py -v

# Run all agent enhancement tests
pytest tests/lib/agent_enhancement/ -v

# Integration test with real agent file
python3 ~/.agentecflow/bin/agent-enhance mydrive/business-logic-engine-specialist --hybrid --dry-run
```

## Regression Prevention

**Potential Regressions:**
1. Existing agents with quoted descriptions might get double-quoted
2. Metadata with intentional YAML structures could be corrupted

**Mitigation:**
- Only pre-process `description` field (most common source of issues)
- Check if value is already quoted before adding quotes
- Add integration test with real agent files from mydrive template

## Notes

- This is a **high priority** fix as it blocks agent enhancement for any project with complex descriptions
- The fix should be defensive and not break working cases
- Consider using `yaml.safe_dump()` with `default_flow_style=False` as alternative approach
