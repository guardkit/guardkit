"""
Task utility functions for parsing, writing, and managing task frontmatter.

This module provides centralized functions for:
- Parsing task markdown files with YAML frontmatter
- Writing task frontmatter with proper formatting
- Handling external_ids field for PM tool integration
- Backward compatibility with legacy task formats
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def parse_task_frontmatter(content: str) -> Dict[str, Any]:
    """
    Parse task frontmatter from markdown content with backward compatibility.

    Args:
        content: Full markdown content including YAML frontmatter

    Returns:
        Dictionary containing parsed frontmatter with guaranteed fields

    Raises:
        ValueError: If content doesn't contain valid frontmatter

    Example:
        >>> content = "---\\nid: TASK-001\\ntitle: Test\\n---\\nBody"
        >>> data = parse_task_frontmatter(content)
        >>> data['external_ids']
        {}
    """
    # Split frontmatter from body
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError("Invalid task format: missing frontmatter delimiters")

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")

    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML dictionary")

    # Ensure external_ids exists (default to empty dict for backward compatibility)
    if 'external_ids' not in frontmatter:
        frontmatter['external_ids'] = {}

    # Ensure external_ids is a dict
    if not isinstance(frontmatter['external_ids'], dict):
        frontmatter['external_ids'] = {}

    # Ensure legacy_id is handled (for migrated tasks)
    if 'legacy_id' not in frontmatter:
        frontmatter['legacy_id'] = None

    return frontmatter


def write_task_frontmatter(task_data: Dict[str, Any], body: str = "") -> str:
    """
    Write task frontmatter as YAML preserving all fields.

    Args:
        task_data: Dictionary containing task metadata
        body: Optional markdown body content

    Returns:
        Complete markdown content with YAML frontmatter

    Example:
        >>> data = {'id': 'TASK-001', 'title': 'Test', 'external_ids': {'jira': 'PROJ-1'}}
        >>> content = write_task_frontmatter(data, "## Description\\nTest task")
        >>> '---' in content and 'jira: PROJ-1' in content
        True
    """
    # Create a copy to avoid modifying the original
    task_data_copy = task_data.copy()

    # Remove None values from external_ids to keep YAML clean
    if 'external_ids' in task_data_copy:
        task_data_copy['external_ids'] = {
            k: v for k, v in task_data_copy['external_ids'].items()
            if v is not None
        }
        # Remove external_ids entirely if empty (optional field)
        if not task_data_copy['external_ids']:
            del task_data_copy['external_ids']

    # Remove legacy_id if None (only show if present)
    if 'legacy_id' in task_data_copy and task_data_copy['legacy_id'] is None:
        del task_data_copy['legacy_id']

    # Generate YAML (preserve order, no inline flow style)
    yaml_str = yaml.dump(
        task_data_copy,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True
    )

    # Construct full markdown
    if body:
        return f"---\n{yaml_str}---\n{body}"
    else:
        return f"---\n{yaml_str}---\n"


def update_task_frontmatter(
    file_path: Path,
    updates: Dict[str, Any],
    preserve_body: bool = True
) -> None:
    """
    Update specific fields in task frontmatter while preserving others.

    Args:
        file_path: Path to task markdown file
        updates: Dictionary of fields to update
        preserve_body: If True, preserve markdown body content

    Example:
        >>> update_task_frontmatter(
        ...     Path('tasks/backlog/TASK-001.md'),
        ...     {'status': 'in_progress', 'external_ids': {'jira': 'PROJ-1'}}
        ... )
    """
    # Read current content
    content = file_path.read_text(encoding='utf-8')

    # Parse existing frontmatter
    frontmatter = parse_task_frontmatter(content)

    # Extract body if needed
    body = ""
    if preserve_body:
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2]

    # Apply updates
    for key, value in updates.items():
        if key == 'external_ids' and isinstance(value, dict):
            # Merge external_ids instead of replacing
            if 'external_ids' not in frontmatter:
                frontmatter['external_ids'] = {}
            frontmatter['external_ids'].update(value)
        else:
            frontmatter[key] = value

    # Update timestamp
    frontmatter['updated'] = datetime.utcnow().isoformat() + 'Z'

    # Write back
    new_content = write_task_frontmatter(frontmatter, body)
    file_path.write_text(new_content, encoding='utf-8')


def read_task_file(file_path: Path) -> tuple[Dict[str, Any], str]:
    """
    Read task file and return frontmatter and body separately.

    Args:
        file_path: Path to task markdown file

    Returns:
        Tuple of (frontmatter_dict, markdown_body)

    Example:
        >>> frontmatter, body = read_task_file(Path('tasks/backlog/TASK-001.md'))
        >>> frontmatter['id']
        'TASK-001'
        >>> '## Description' in body
        True
    """
    content = file_path.read_text(encoding='utf-8')
    frontmatter = parse_task_frontmatter(content)

    # Extract body
    parts = content.split('---', 2)
    body = parts[2] if len(parts) >= 3 else ""

    return frontmatter, body


def create_task_frontmatter(
    task_id: str,
    title: str,
    priority: str = "medium",
    tags: Optional[list] = None,
    external_ids: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new task frontmatter dictionary with all required fields.

    Args:
        task_id: Unique task identifier
        title: Task title
        priority: Task priority (low, medium, high)
        tags: Optional list of tags
        external_ids: Optional dict of PM tool IDs
        **kwargs: Additional optional fields

    Returns:
        Dictionary ready for YAML serialization

    Example:
        >>> data = create_task_frontmatter(
        ...     'TASK-001',
        ...     'Add authentication',
        ...     priority='high',
        ...     external_ids={'jira': 'PROJ-456'}
        ... )
        >>> data['external_ids']['jira']
        'PROJ-456'
    """
    now = datetime.utcnow().isoformat() + 'Z'

    frontmatter = {
        'id': task_id,
        'title': title,
        'status': 'backlog',
        'created': now,
        'updated': now,
        'priority': priority,
        'tags': tags or [],
        'complexity': kwargs.get('complexity', 0),
        'test_results': {
            'status': 'pending',
            'coverage': None,
            'last_run': None
        }
    }

    # Add external_ids if provided
    if external_ids:
        frontmatter['external_ids'] = external_ids

    # Add any additional fields from kwargs
    excluded_keys = {'complexity'}  # Already handled
    for key, value in kwargs.items():
        if key not in excluded_keys and key not in frontmatter:
            frontmatter[key] = value

    return frontmatter


def validate_external_ids(external_ids: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate and normalize external_ids field.

    Args:
        external_ids: Dictionary of PM tool IDs

    Returns:
        Validated and normalized external_ids dictionary

    Raises:
        ValueError: If external_ids format is invalid

    Example:
        >>> validate_external_ids({'jira': 'PROJ-456', 'github': 123})
        {'jira': 'PROJ-456', 'github': '123'}
    """
    if not isinstance(external_ids, dict):
        raise ValueError("external_ids must be a dictionary")

    # Supported PM tools
    supported_tools = {'jira', 'azure_devops', 'linear', 'github'}

    validated = {}
    for tool, value in external_ids.items():
        if tool not in supported_tools:
            raise ValueError(
                f"Unsupported PM tool: {tool}. "
                f"Supported tools: {', '.join(sorted(supported_tools))}"
            )

        # Convert to string for consistency
        if value is not None:
            validated[tool] = str(value)

    return validated


def move_task_to_blocked(
    task_id: str,
    reason: str,
    tasks_dir: Path = None
) -> bool:
    """
    Move task to BLOCKED state with specified reason.

    This function is used when validation fails or quality gates are not met.
    It moves the task file to the blocked directory and updates the frontmatter
    with the blocked_reason field.

    Args:
        task_id: Task identifier (e.g., 'TASK-001')
        reason: Human-readable reason for blocking
        tasks_dir: Optional custom tasks directory (defaults to ./tasks)

    Returns:
        bool: True if task was successfully moved to BLOCKED state

    Raises:
        FileNotFoundError: If task file cannot be found
        ValueError: If task_id format is invalid

    Example:
        >>> move_task_to_blocked(
        ...     'TASK-001',
        ...     'Agent invocation protocol violation - Phase 3 skipped'
        ... )
        True
    """
    import shutil
    from pathlib import Path

    # Default to ./tasks directory
    if tasks_dir is None:
        tasks_dir = Path.cwd() / 'tasks'

    # Find current task file
    task_file = None
    for state_dir in ['in_progress', 'in_review', 'backlog', 'design_approved']:
        search_dir = tasks_dir / state_dir
        if not search_dir.exists():
            continue

        # Look for task file (may be in subdirectories)
        for file_path in search_dir.rglob(f'{task_id}.md'):
            task_file = file_path
            break

        if task_file:
            break

    if not task_file:
        raise FileNotFoundError(
            f"Task file for {task_id} not found in any state directory"
        )

    # Update frontmatter
    update_task_frontmatter(
        task_file,
        {
            'status': 'blocked',
            'blocked_reason': reason
        },
        preserve_body=True
    )

    # Move to blocked directory
    blocked_dir = tasks_dir / 'blocked'
    blocked_dir.mkdir(exist_ok=True)

    # Preserve directory structure if task was in a subdirectory
    relative_path = task_file.relative_to(task_file.parent.parent)
    dest_path = blocked_dir / relative_path.name

    # Move the file
    shutil.move(str(task_file), str(dest_path))

    print(f"\n✅ Task {task_id} moved to BLOCKED state")
    print(f"Reason: {reason}")
    print(f"Location: {dest_path}")

    return True
