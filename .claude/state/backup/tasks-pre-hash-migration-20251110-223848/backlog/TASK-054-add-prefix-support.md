---
id: TASK-054
title: Add prefix support and inference
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: medium
tags: [infrastructure, hash-ids, prefixes]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add prefix support and inference

## Description

Implement intelligent prefix support for task IDs, including automatic inference from epic links, tags, and task titles. This makes hash IDs more organized and human-friendly by grouping related tasks.

## Acceptance Criteria

- [ ] Manual prefix specification via `prefix:` parameter
- [ ] Automatic prefix inference from epic (epic:EPIC-001 → prefix:E01)
- [ ] Automatic prefix inference from tags (tags:[docs] → prefix:DOC)
- [ ] Automatic prefix inference from title keywords
- [ ] Prefix validation (2-4 uppercase alphanumeric)
- [ ] Prefix registry for consistency
- [ ] User override of inferred prefix
- [ ] Clear messaging when prefix is inferred

## Test Requirements

- [ ] Unit tests for manual prefix specification
- [ ] Unit tests for epic-based inference
- [ ] Unit tests for tag-based inference
- [ ] Unit tests for title-based inference
- [ ] Unit tests for prefix validation
- [ ] Integration tests with /task-create
- [ ] Test coverage ≥85%

## Implementation Notes

### File Location
Add to: `installer/global/lib/id_generator.py`

### Inference Rules (Priority Order)

1. **Manual Override** (highest priority)
   ```bash
   /task-create "Add authentication" prefix:AUTH
   # Generated: TASK-AUTH-b2c4
   ```

2. **Epic Inference**
   ```bash
   /task-create "Add authentication" epic:EPIC-001
   # Inferred: prefix:E01
   # Generated: TASK-E01-b2c4
   ```

3. **Tag Inference**
   ```bash
   /task-create "Update installation guide" tags:[docs]
   # Inferred: prefix:DOC
   # Generated: TASK-DOC-f1a3
   ```

4. **Title Keyword Inference**
   ```bash
   /task-create "Fix login validation bug"
   # Inferred: prefix:FIX (from "Fix")
   # Generated: TASK-FIX-a3f8
   ```

5. **No Prefix** (default)
   ```bash
   /task-create "Refactor authentication module"
   # No inference
   # Generated: TASK-a3f8
   ```

### Prefix Registry

**Standard Prefixes**:
```python
STANDARD_PREFIXES = {
    # Epic-based
    "E01": "Epic 001",
    "E02": "Epic 002",
    # ... (generated dynamically from epics)

    # Domain-based
    "DOC": "Documentation",
    "TEST": "Testing",
    "FIX": "Bug fixes",
    "FEAT": "Features",
    "REFAC": "Refactoring",  # Note: truncated to REFA (4 chars)

    # Stack-based
    "API": "API/Backend",
    "UI": "User interface",
    "DB": "Database",
    "INFRA": "Infrastructure",  # Note: truncated to INFR
}
```

### Tag → Prefix Mapping

```python
TAG_PREFIX_MAP = {
    "docs": "DOC",
    "documentation": "DOC",
    "test": "TEST",
    "testing": "TEST",
    "bug": "FIX",
    "bugfix": "FIX",
    "fix": "FIX",
    "feature": "FEAT",
    "api": "API",
    "backend": "API",
    "ui": "UI",
    "frontend": "UI",
    "database": "DB",
    "db": "DB",
    "infra": "INFR",
    "infrastructure": "INFR",
}
```

### Title Keyword Detection

```python
TITLE_KEYWORDS = {
    r"^fix\b": "FIX",
    r"^bug\b": "FIX",
    r"\bdocument": "DOC",
    r"\btest": "TEST",
    r"\bapi\b": "API",
    r"\bui\b": "UI",
    r"\bdatabase\b": "DB",
}
```

### Key Functions

```python
def infer_prefix(
    epic: Optional[str] = None,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    manual_prefix: Optional[str] = None
) -> Optional[str]:
    """
    Infer prefix from task context.

    Priority:
    1. Manual override
    2. Epic inference (EPIC-001 → E01)
    3. Tag inference (docs → DOC)
    4. Title keyword (Fix... → FIX)
    5. None
    """
    if manual_prefix:
        return validate_prefix(manual_prefix)

    if epic:
        # EPIC-001 → E01
        epic_num = re.search(r'EPIC-(\d+)', epic)
        if epic_num:
            return f"E{epic_num.group(1)}"

    if tags:
        for tag in tags:
            if tag.lower() in TAG_PREFIX_MAP:
                return TAG_PREFIX_MAP[tag.lower()]

    if title:
        title_lower = title.lower()
        for pattern, prefix in TITLE_KEYWORDS.items():
            if re.search(pattern, title_lower):
                return prefix

    return None


def validate_prefix(prefix: str) -> str:
    """
    Validate and normalize prefix.

    Rules:
    - 2-4 characters
    - Uppercase alphanumeric only
    - Auto-uppercase if needed
    - Truncate if >4 chars
    """
    if not prefix:
        raise ValueError("Prefix cannot be empty")

    # Uppercase
    prefix = prefix.upper()

    # Remove invalid chars
    prefix = re.sub(r'[^A-Z0-9]', '', prefix)

    # Truncate to 4 chars
    if len(prefix) > 4:
        prefix = prefix[:4]

    # Check length
    if len(prefix) < 2:
        raise ValueError(f"Prefix too short: {prefix} (min 2 chars)")

    return prefix


def register_prefix(prefix: str, description: str) -> None:
    """Register custom prefix in registry."""
    STANDARD_PREFIXES[prefix] = description
```

### User Feedback

When prefix is inferred, inform the user:

```
✅ Task Created: TASK-E01-b2c4

ℹ️  Prefix Inferred: E01 (from epic:EPIC-001)
   To override, use: prefix:CUSTOM

📋 Task Details
Title: Add user authentication
...
```

### Override Example

```bash
# Inferred prefix
/task-create "Fix login bug" epic:EPIC-001
# Generated: TASK-E01-a3f8
# Inferred: E01 from epic

# Manual override
/task-create "Fix login bug" epic:EPIC-001 prefix:FIX
# Generated: TASK-FIX-a3f8
# Using manual prefix: FIX (overrides epic inference)
```

### Prefix Consistency

Maintain consistency across related tasks:

```bash
# All tasks in Epic 001 use E01 prefix
/task-create "Task 1" epic:EPIC-001  # TASK-E01-b2c4
/task-create "Task 2" epic:EPIC-001  # TASK-E01-f1a3
/task-create "Task 3" epic:EPIC-001  # TASK-E01-a3f8

# Easy filtering
grep "TASK-E01-" tasks/**/*.md
```

## Dependencies

- TASK-046: Hash ID generator (must have prefix support)
- TASK-048: Update /task-create (to add prefix parameter)

## Related Tasks

- TASK-053: Documentation (explain prefix usage)
- TASK-052: Migration (infer prefixes for old tasks)

## Test Execution Log

[Automatically populated by /task-work]
