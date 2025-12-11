---
id: TASK-FIX-STACK-B4C8
title: Stack Value Validation Sync
status: backlog
task_type: implementation
created: 2025-12-11T10:45:00Z
updated: 2025-12-11T10:45:00Z
priority: low
tags: [agent-discovery, validation, stack, consistency]
complexity: 2
parent_review: TASK-REV-D4A7
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Stack Value Validation Sync

## Problem Statement

Two different files define valid stack values with inconsistent lists, causing warnings for legitimate stacks like `maui`, `xaml`, and `realm`.

**Discrepancy:**

| Stack | agent_discovery.py | validate_agent_metadata.py |
|-------|-------------------|---------------------------|
| maui | ❌ Missing | ✅ Present |
| xaml | ❌ Missing | ✅ Present |
| csharp | ✅ Present | ❌ Missing |
| realm | ❌ Missing | ❌ Missing |

## Root Cause

**Primary Validation** (`agent_discovery.py:49-52`):
```python
VALID_STACKS = [
    'python', 'react', 'dotnet', 'typescript', 'javascript',
    'go', 'rust', 'java', 'ruby', 'php', 'cross-stack', 'csharp'
]
```

**Legacy Validation** (`scripts/validate_agent_metadata.py:84`):
```python
valid_stacks = ['cross-stack', 'python', 'react', 'dotnet', 'typescript', 'maui', 'xaml']
```

The legacy script was created for .NET MAUI projects and includes `maui`, `xaml` but the primary validator doesn't.

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/core/commands/lib/agent_discovery.py` | 49-52 | Expand VALID_STACKS |
| `scripts/validate_agent_metadata.py` | 84 | Import from agent_discovery.py |
| `tests/test_agent_discovery.py` | 881-887 | Update test to include new stacks |

## Implementation Specification

### Step 1: Expand VALID_STACKS (agent_discovery.py:49-52)

**Before:**
```python
VALID_STACKS = [
    'python', 'react', 'dotnet', 'typescript', 'javascript',
    'go', 'rust', 'java', 'ruby', 'php', 'cross-stack', 'csharp'
]
```

**After:**
```python
VALID_STACKS = [
    # Core languages
    'python', 'javascript', 'typescript', 'csharp', 'java',
    'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'dart',

    # Frameworks/Platforms
    'react', 'dotnet', 'maui', 'flutter',

    # Technologies
    'xaml', 'realm',

    # Meta
    'cross-stack'
]
```

**Rationale for additions:**
- `maui` - .NET MAUI mobile framework
- `xaml` - UI markup language for .NET
- `realm` - Mobile database (MongoDB Realm)
- `swift` - iOS/macOS development
- `kotlin` - Android/JVM development
- `flutter` - Cross-platform mobile
- `dart` - Flutter's language

### Step 2: Update Legacy Script (scripts/validate_agent_metadata.py:84)

**Option A (Recommended): Import from primary source**
```python
# At top of file
from installer.core.commands.lib.agent_discovery import VALID_STACKS

# Remove local definition (line 84)
# valid_stacks = ['cross-stack', 'python', 'react', 'dotnet', 'typescript', 'maui', 'xaml']
```

**Option B: If import not possible, sync the list**
```python
# Line 84
valid_stacks = [
    'python', 'javascript', 'typescript', 'csharp', 'java',
    'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'dart',
    'react', 'dotnet', 'maui', 'flutter',
    'xaml', 'realm',
    'cross-stack'
]
```

### Step 3: Update Tests (tests/test_agent_discovery.py:881-887)

**Before:**
```python
def test_valid_stacks_defined(self):
    """Test that VALID_STACKS contains expected values."""
    expected = ['python', 'react', 'dotnet', 'typescript', 'javascript',
                'go', 'rust', 'java', 'ruby', 'php', 'cross-stack', 'csharp']
    assert set(VALID_STACKS) == set(expected)
```

**After:**
```python
def test_valid_stacks_defined(self):
    """Test that VALID_STACKS contains expected values."""
    # Core stacks that must always be present
    required_stacks = [
        'python', 'javascript', 'typescript', 'csharp', 'java',
        'go', 'rust', 'ruby', 'php', 'react', 'dotnet', 'cross-stack'
    ]

    # Extended stacks for mobile/specialized development
    extended_stacks = [
        'maui', 'xaml', 'realm', 'swift', 'kotlin', 'flutter', 'dart'
    ]

    for stack in required_stacks:
        assert stack in VALID_STACKS, f"Required stack '{stack}' missing from VALID_STACKS"

    for stack in extended_stacks:
        assert stack in VALID_STACKS, f"Extended stack '{stack}' missing from VALID_STACKS"


def test_stack_validation_case_insensitive(self):
    """Test that stack validation is case-insensitive."""
    from installer.core.commands.lib.agent_discovery import validate_discovery_metadata

    # Should accept lowercase
    result, errors = validate_discovery_metadata({"stack": ["maui"]})
    assert "Invalid stack value: maui" not in errors

    # Should accept uppercase
    result, errors = validate_discovery_metadata({"stack": ["MAUI"]})
    assert "Invalid stack value: MAUI" not in errors
```

### Step 4: Add Stack Categories (Optional Enhancement)

For better organization and documentation:

```python
# agent_discovery.py

# Organized by category for clarity
STACK_CATEGORIES = {
    'languages': ['python', 'javascript', 'typescript', 'csharp', 'java',
                  'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'dart'],
    'frameworks': ['react', 'dotnet', 'maui', 'flutter'],
    'technologies': ['xaml', 'realm'],
    'meta': ['cross-stack']
}

# Flatten for validation
VALID_STACKS = [
    stack
    for category in STACK_CATEGORIES.values()
    for stack in category
]
```

## Acceptance Criteria

- [ ] VALID_STACKS includes: `maui`, `xaml`, `realm`, `swift`, `kotlin`, `flutter`, `dart`
- [ ] Both validation files use the same list (preferably via import)
- [ ] No warnings for valid .NET MAUI stacks (`maui`, `xaml`, `realm`, `csharp`, `dotnet`)
- [ ] Validation is case-insensitive
- [ ] Tests updated and passing

## Test Requirements

```bash
# Run stack validation tests
pytest tests/test_agent_discovery.py -k "stack" -v

# Test with real agent metadata
python3 scripts/validate_agent_metadata.py docs/reviews/progressive-disclosure/mydrive/agents/maui-mvvm-viewmodel-specialist.md

# Verify no warnings for MAUI agents
python3 -c "
from installer.core.commands.lib.agent_discovery import validate_discovery_metadata
result, errors = validate_discovery_metadata({'stack': ['csharp', 'dotnet', 'maui']})
print('Errors:', errors)
assert not any('Invalid stack' in e for e in errors), 'Stack validation failed'
print('SUCCESS: All MAUI stacks valid')
"
```

## Regression Prevention

**Potential Regressions:**
1. Existing agents using lowercase stacks might fail if we accidentally make validation case-sensitive
2. Scripts depending on the old list might break

**Mitigation:**
- Keep validation case-insensitive (existing behavior at line 607-608)
- Import from single source of truth
- Add deprecation warning to legacy script if it still defines its own list

## Notes

- This is a **low priority** fix - the warnings are informational only
- Consider deprecating `scripts/validate_agent_metadata.py` entirely
- The categorized approach (STACK_CATEGORIES) makes it easier to explain what each stack represents
