---
id: TASK-051
title: Update task frontmatter schema for external_ids
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: medium
tags: [infrastructure, hash-ids, schema]
complexity: 3
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task frontmatter schema for external_ids

## Description

Update the task markdown frontmatter schema to include the new `external_ids` field for storing PM tool mappings. Update all task creation, reading, and writing code to handle the new schema gracefully.

## Acceptance Criteria

- [ ] Add `external_ids` field to task frontmatter template
- [ ] Backward compatible: Old tasks without field still work
- [ ] Forward compatible: Field is optional, defaults to empty dict
- [ ] Update task parsing to read `external_ids`
- [ ] Update task writing to preserve `external_ids`
- [ ] Update documentation with example frontmatter
- [ ] Support all 4 PM tools (jira, azure_devops, linear, github)

## Test Requirements

- [ ] Unit tests for parsing tasks with external_ids
- [ ] Unit tests for parsing tasks without external_ids (backward compat)
- [ ] Unit tests for writing tasks with external_ids
- [ ] Integration tests creating and reading tasks
- [ ] Schema validation tests
- [ ] Test coverage ≥85%

## Implementation Notes

### Updated Frontmatter Format

**New Task (Hash ID + External IDs)**:
```yaml
---
id: TASK-E01-b2c4
title: Add user authentication
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [auth, security]
complexity: 0
external_ids:
  jira: PROJ-456
  azure_devops: 1234
  linear: TEAM-789
  github: 234
test_results:
  status: pending
  coverage: null
  last_run: null
---
```

**Migrated Task (Legacy ID Preserved)**:
```yaml
---
id: TASK-E01-b2c4
legacy_id: TASK-042
title: Add user authentication
status: in_progress
created: 2024-12-15T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [auth, security]
complexity: 5
external_ids:
  jira: PROJ-456
test_results:
  status: passed
  coverage: 85.2
  last_run: 2024-12-20T14:30:00Z
---
```

**Old Task (Backward Compatible)**:
```yaml
---
id: TASK-042
title: Add user authentication
status: completed
created: 2024-12-15T10:00:00Z
updated: 2024-12-20T15:00:00Z
priority: high
tags: [auth, security]
complexity: 5
test_results:
  status: passed
  coverage: 85.2
  last_run: 2024-12-20T14:30:00Z
---
# No external_ids field - still valid
```

### Fields to Add

1. **external_ids** (optional dict):
   - `jira`: JIRA issue key (e.g., "PROJ-456")
   - `azure_devops`: Work item ID (e.g., "1234")
   - `linear`: Linear issue ID (e.g., "TEAM-789")
   - `github`: GitHub issue number (e.g., "234")

2. **legacy_id** (optional string):
   - Preserves old ID format for migrated tasks
   - Used for cross-reference updates
   - Not displayed to users after migration

### Files to Modify

1. Task frontmatter template (wherever tasks are created)
2. Task parser (wherever YAML frontmatter is read)
3. Task writer (wherever frontmatter is updated)
4. `/task-create` command
5. `/task-status` command (display external IDs)
6. Documentation: `installer/global/commands/task-create.md`

### Parsing Logic
```python
import yaml

def parse_task_frontmatter(content: str) -> dict:
    """Parse task frontmatter with backward compatibility."""
    # Split frontmatter from body
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError("Invalid task format")

    # Parse YAML
    frontmatter = yaml.safe_load(parts[1])

    # Ensure external_ids exists (default to empty dict)
    if 'external_ids' not in frontmatter:
        frontmatter['external_ids'] = {}

    # Ensure legacy_id is handled
    if 'legacy_id' not in frontmatter:
        frontmatter['legacy_id'] = None

    return frontmatter
```

### Writing Logic
```python
def write_task_frontmatter(task_data: dict) -> str:
    """Write task frontmatter preserving all fields."""
    # Remove None values from external_ids
    if 'external_ids' in task_data:
        task_data['external_ids'] = {
            k: v for k, v in task_data['external_ids'].items()
            if v is not None
        }

    # Generate YAML
    yaml_str = yaml.dump(task_data, sort_keys=False, default_flow_style=False)

    return f"---\n{yaml_str}---\n"
```

### Display Format (/task-status)
```
✅ Task: TASK-E01-b2c4
Title: Add user authentication
Status: in_progress
Priority: high

🔗 External IDs
JIRA:        PROJ-456
Azure DevOps: 1234
Linear:      TEAM-789
GitHub:      #234

📁 File: tasks/in_progress/TASK-E01-b2c4-add-user-authentication.md
```

## Dependencies

- TASK-049: External ID mapper (defines mapping structure)

## Related Tasks

- TASK-048: Update /task-create command
- TASK-050: Persistence layer
- TASK-052: Migration script

## Test Execution Log

[Automatically populated by /task-work]
