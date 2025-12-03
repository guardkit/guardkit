# External IDs Integration Guide

## Overview

The `external_ids` field in task frontmatter enables seamless integration with external project management tools. This field stores mappings between GuardKit tasks and tickets/issues in tools like Jira, Azure DevOps, Linear, and GitHub.

## Supported Tools

- **Jira**: Project management and issue tracking
- **Azure DevOps**: Work item tracking and boards
- **Linear**: Modern issue tracking for software teams
- **GitHub**: Issue and project management

## Field Structure

### Basic Format

```yaml
external_ids:
  jira: PROJ-456          # Jira issue key
  azure_devops: "1234"    # Azure DevOps work item ID
  linear: TEAM-789        # Linear issue ID
  github: "234"           # GitHub issue number
```

### Characteristics

1. **Optional**: Field is completely optional and backward compatible
2. **Dictionary**: Stores key-value pairs for each PM tool
3. **String Values**: All values stored as strings for consistency
4. **Null Filtering**: Null/None values are automatically removed
5. **Case Sensitive**: Tool names must be lowercase with underscores

## Usage Examples

### Creating Task with External IDs

```bash
# Via task-manager agent (when creating task)
/task-create "Add user authentication" external_ids:jira=PROJ-456,github=123
```

### Updating External IDs

External IDs can be added or updated after task creation:

```python
from installer.global.commands.lib.task_utils import update_task_frontmatter
from pathlib import Path

# Add Jira ID to existing task
update_task_frontmatter(
    Path("tasks/in_progress/TASK-001.md"),
    {"external_ids": {"jira": "PROJ-456"}},
    preserve_body=True
)

# Merge multiple external IDs
update_task_frontmatter(
    Path("tasks/in_progress/TASK-001.md"),
    {
        "external_ids": {
            "jira": "PROJ-456",
            "linear": "TEAM-789",
            "github": "234"
        }
    },
    preserve_body=True
)
```

### Reading External IDs

```python
from installer.global.commands.lib.task_utils import read_task_file
from pathlib import Path

# Read task file
frontmatter, body = read_task_file(Path("tasks/in_progress/TASK-001.md"))

# Access external IDs
if "external_ids" in frontmatter:
    jira_id = frontmatter["external_ids"].get("jira")
    github_id = frontmatter["external_ids"].get("github")

    print(f"Jira: {jira_id}")
    print(f"GitHub: {github_id}")
```

## Backward Compatibility

### Old Tasks (No external_ids)

Tasks created before the external_ids feature will:

1. **Parse successfully**: No errors when reading
2. **Default to empty dict**: `external_ids` field defaults to `{}`
3. **Preserve structure**: No modification to existing frontmatter

```yaml
# Old task format (still valid)
---
id: TASK-042
title: Old Task
status: completed
created: 2024-12-15T10:00:00Z
updated: 2024-12-20T15:00:00Z
priority: high
tags: [legacy]
complexity: 5
test_results:
  status: passed
  coverage: 85.2
  last_run: 2024-12-20T14:30:00Z
---
# No external_ids field - still valid!
```

When parsed:
```python
frontmatter = parse_task_frontmatter(content)
assert frontmatter["external_ids"] == {}  # Automatically added
```

### Migrated Tasks (Hash IDs)

Tasks migrated to hash-based IDs preserve their legacy ID:

```yaml
---
id: TASK-E01-b2c4        # New hash-based ID
legacy_id: TASK-042       # Preserved old ID
title: Migrated Task
status: in_progress
created: 2024-12-15T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [migrated]
complexity: 5
external_ids:
  jira: PROJ-456          # PM tool mapping
test_results:
  status: passed
  coverage: 85.2
  last_run: 2024-12-20T14:30:00Z
---
```

## Validation

### Supported Tool Names

Only these tool names are accepted:

- `jira`
- `azure_devops`
- `linear`
- `github`

### Validation Function

```python
from installer.global.commands.lib.task_utils import validate_external_ids

# Valid external IDs
external_ids = {
    "jira": "PROJ-456",
    "azure_devops": 1234,      # Converted to "1234"
    "linear": "TEAM-789",
    "github": 234               # Converted to "234"
}

validated = validate_external_ids(external_ids)
# Result: All values converted to strings

# Invalid tool name
invalid_ids = {
    "jira": "PROJ-456",
    "trello": "12345"  # Unsupported tool
}

# Raises: ValueError: Unsupported PM tool: trello
```

## Integration Patterns

### Pattern 1: Epic-Level Integration

External IDs inherited from epic configuration (requires require-kit):

```yaml
# Epic configuration
---
id: EPIC-001
title: User Management System
external_ids:
  jira: PROJ-123
  linear: PROJECT-456
---

# Task inherits epic's external tool configuration
/task-create "Add login" epic:EPIC-001
# Task will know about PROJ-123 and PROJECT-456 context
```

### Pattern 2: Task-Specific IDs

Direct task-to-issue mapping:

```yaml
---
id: TASK-001
title: Add user authentication
external_ids:
  jira: PROJ-456        # Task-specific Jira ticket
  github: 234           # Task-specific GitHub issue
---
```

### Pattern 3: Sync Workflow

1. Create task in GuardKit
2. Export to external tool (requires require-kit)
3. Store returned ID in external_ids
4. Use ID for bi-directional sync

```bash
# 1. Create task
/task-create "Add authentication"

# 2. Export to Jira (future feature with require-kit)
/task-export TASK-001 --tool jira
# Returns: PROJ-456

# 3. ID automatically stored in external_ids
# 4. Status syncs both ways
```

## Display in /task-status

When viewing task status, external IDs are displayed:

```
✅ Task: TASK-E01-b2c4
Title: Add user authentication
Status: in_progress
Priority: high

🔗 External IDs
JIRA:         PROJ-456
Azure DevOps: 1234
Linear:       TEAM-789
GitHub:       #234

📁 File: tasks/in_progress/TASK-E01-b2c4-add-user-authentication.md
```

## API Reference

### parse_task_frontmatter()

Parse task frontmatter with automatic external_ids initialization:

```python
def parse_task_frontmatter(content: str) -> Dict[str, Any]:
    """
    Parse task frontmatter from markdown content.

    Args:
        content: Full markdown content including YAML frontmatter

    Returns:
        Dictionary with guaranteed 'external_ids' field (empty dict if not present)

    Raises:
        ValueError: If frontmatter format is invalid
    """
```

### write_task_frontmatter()

Write task frontmatter with automatic cleanup:

```python
def write_task_frontmatter(task_data: Dict[str, Any], body: str = "") -> str:
    """
    Write task frontmatter as YAML.

    Features:
    - Removes None values from external_ids
    - Removes empty external_ids dict entirely
    - Removes None legacy_id

    Args:
        task_data: Task metadata dictionary
        body: Optional markdown body content

    Returns:
        Complete markdown with YAML frontmatter
    """
```

### update_task_frontmatter()

Update task file with external_ids merging:

```python
def update_task_frontmatter(
    file_path: Path,
    updates: Dict[str, Any],
    preserve_body: bool = True
) -> None:
    """
    Update task frontmatter with smart external_ids merging.

    Features:
    - Merges new external_ids with existing ones
    - Automatically updates timestamp
    - Preserves markdown body

    Args:
        file_path: Path to task markdown file
        updates: Dictionary of fields to update
        preserve_body: If True, preserve markdown body
    """
```

### validate_external_ids()

Validate and normalize external IDs:

```python
def validate_external_ids(external_ids: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate external_ids structure and values.

    Features:
    - Checks for supported tool names
    - Converts all values to strings
    - Filters out None values

    Args:
        external_ids: Dictionary of PM tool IDs

    Returns:
        Validated dictionary with string values

    Raises:
        ValueError: If tool name is unsupported or format is invalid
    """
```

## Testing

Comprehensive test suite ensures external_ids functionality:

```bash
# Run tests
python3 -m pytest tests/unit/test_task_utils.py -v

# Test coverage
python3 -m pytest tests/unit/test_task_utils.py --cov=task_utils --cov-report=term-missing
```

Test categories:

1. **Parsing**: With/without external_ids, backward compatibility
2. **Writing**: Adding, removing, merging external_ids
3. **Updating**: File updates with external_ids merging
4. **Validation**: Tool name validation, type conversion
5. **Integration**: End-to-end task lifecycle

## Migration Guide

### Migrating Existing Tasks

Existing tasks work without changes. To add external IDs:

```python
from installer.global.commands.lib.task_utils import update_task_frontmatter
from pathlib import Path
import glob

# Update all in_progress tasks with Jira IDs
for task_file in Path("tasks/in_progress").glob("TASK-*.md"):
    # Map task to Jira ID (your logic here)
    jira_id = get_jira_id_for_task(task_file)

    if jira_id:
        update_task_frontmatter(
            task_file,
            {"external_ids": {"jira": jira_id}},
            preserve_body=True
        )
```

## Best Practices

1. **Always validate**: Use `validate_external_ids()` before storing
2. **Store as strings**: Convert numbers to strings for consistency
3. **Merge, don't replace**: Use `update_task_frontmatter()` to merge IDs
4. **Check for None**: Filter None values before storing
5. **Use consistent naming**: Lowercase with underscores (e.g., `azure_devops`)

## Future Integration (RequireKit)

The external_ids field is designed to support future bi-directional sync with PM tools via require-kit:

- **Automatic export**: Create task → export to PM tool → store ID
- **Status sync**: Update task status ↔ PM tool status
- **Comment sync**: Link discussions between systems
- **Attachment sync**: Share files across systems
- **Progress tracking**: Aggregate progress from multiple systems

See [RequireKit Documentation](https://github.com/requirekit/require-kit) for PM tool integration.

## Troubleshooting

### Issue: external_ids not showing up

**Solution**: Ensure you're using the latest task_utils module:

```python
from installer.global.commands.lib.task_utils import parse_task_frontmatter

frontmatter = parse_task_frontmatter(content)
print(frontmatter.get("external_ids", {}))  # Should always return dict
```

### Issue: Validation error for tool name

**Solution**: Check tool name spelling and use lowercase with underscores:

```python
# Correct
external_ids = {"azure_devops": "1234"}

# Incorrect
external_ids = {"Azure_DevOps": "1234"}  # Wrong case
external_ids = {"azuredevops": "1234"}   # Missing underscore
external_ids = {"azure-devops": "1234"}  # Wrong separator
```

### Issue: IDs disappearing after update

**Solution**: Use merging update, not replacement:

```python
# Correct - merges external_ids
update_task_frontmatter(
    task_file,
    {"external_ids": {"github": "234"}},  # Merges with existing
    preserve_body=True
)

# Incorrect - might lose other IDs
frontmatter["external_ids"] = {"github": "234"}  # Replaces all
```

## Related Documentation

- [Task Create Command](../installer/global/commands/task-create.md)
- [Task Status Command](../installer/global/commands/task-status.md)
- [Task Utils API](../installer/global/commands/lib/task_utils.py)
- [RequireKit Integration](https://github.com/requirekit/require-kit)
