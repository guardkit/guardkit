"""
Unit tests for task_utils module.

Tests parsing, writing, and managing task frontmatter with backward compatibility
for external_ids field and legacy task formats.
"""

import pytest
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_utils import (
    parse_task_frontmatter,
    write_task_frontmatter,
    update_task_frontmatter,
    read_task_file,
    create_task_frontmatter,
    validate_external_ids
)


class TestParseTaskFrontmatter:
    """Test parsing task frontmatter with various formats."""

    def test_parse_task_with_external_ids(self):
        """Test parsing task that includes external_ids field."""
        content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [test]
complexity: 3
external_ids:
  jira: PROJ-456
  github: 123
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Task Body
"""
        result = parse_task_frontmatter(content)

        assert result['id'] == 'TASK-001'
        assert result['title'] == 'Test Task'
        assert result['external_ids'] == {'jira': 'PROJ-456', 'github': 123}
        assert result['legacy_id'] is None

    def test_parse_task_without_external_ids_backward_compat(self):
        """Test backward compatibility for tasks without external_ids."""
        content = """---
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
# Old task body
"""
        result = parse_task_frontmatter(content)

        assert result['id'] == 'TASK-042'
        assert result['external_ids'] == {}  # Should default to empty dict
        assert result['legacy_id'] is None

    def test_parse_task_with_legacy_id(self):
        """Test parsing migrated task with legacy_id."""
        content = """---
id: TASK-E01-b2c4
legacy_id: TASK-042
title: Migrated Task
status: in_progress
created: 2024-12-15T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [migrated]
complexity: 5
external_ids:
  jira: PROJ-456
test_results:
  status: passed
  coverage: 85.2
  last_run: 2024-12-20T14:30:00Z
---
# Migrated task
"""
        result = parse_task_frontmatter(content)

        assert result['id'] == 'TASK-E01-b2c4'
        assert result['legacy_id'] == 'TASK-042'
        assert result['external_ids'] == {'jira': 'PROJ-456'}

    def test_parse_invalid_frontmatter_missing_delimiters(self):
        """Test error handling for content without frontmatter delimiters."""
        content = "# Just a markdown file without frontmatter"

        with pytest.raises(ValueError, match="missing frontmatter delimiters"):
            parse_task_frontmatter(content)

    def test_parse_invalid_yaml(self):
        """Test error handling for invalid YAML in frontmatter."""
        content = """---
id: TASK-001
title: Test Task
  invalid_indent: broken
---
# Body
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_task_frontmatter(content)

    def test_parse_non_dict_frontmatter(self):
        """Test error handling when frontmatter is not a dictionary."""
        content = """---
- list item 1
- list item 2
---
# Body
"""
        with pytest.raises(ValueError, match="must be a YAML dictionary"):
            parse_task_frontmatter(content)

    def test_parse_external_ids_not_dict(self):
        """Test that invalid external_ids is replaced with empty dict."""
        content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: medium
tags: []
complexity: 0
external_ids: "invalid_string"
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Body
"""
        result = parse_task_frontmatter(content)

        # Should replace invalid external_ids with empty dict
        assert result['external_ids'] == {}


class TestWriteTaskFrontmatter:
    """Test writing task frontmatter to markdown format."""

    def test_write_task_with_external_ids(self):
        """Test writing task with external_ids included."""
        task_data = {
            'id': 'TASK-001',
            'title': 'Test Task',
            'status': 'backlog',
            'created': '2025-01-08T10:00:00Z',
            'updated': '2025-01-08T10:00:00Z',
            'priority': 'high',
            'tags': ['test'],
            'complexity': 3,
            'external_ids': {
                'jira': 'PROJ-456',
                'github': '123'
            },
            'test_results': {
                'status': 'pending',
                'coverage': None,
                'last_run': None
            }
        }
        body = "# Task Body\n## Description\nTest description"

        result = write_task_frontmatter(task_data, body)

        assert result.startswith('---\n')
        assert '---\n# Task Body' in result
        assert 'jira: PROJ-456' in result
        assert 'github: \'123\'' in result or 'github: "123"' in result

    def test_write_task_removes_none_from_external_ids(self):
        """Test that None values are removed from external_ids."""
        task_data = {
            'id': 'TASK-001',
            'title': 'Test Task',
            'status': 'backlog',
            'created': '2025-01-08T10:00:00Z',
            'updated': '2025-01-08T10:00:00Z',
            'priority': 'medium',
            'tags': [],
            'complexity': 0,
            'external_ids': {
                'jira': 'PROJ-456',
                'github': None,
                'linear': 'TEAM-789'
            },
            'test_results': {
                'status': 'pending',
                'coverage': None,
                'last_run': None
            }
        }

        result = write_task_frontmatter(task_data)

        assert 'jira: PROJ-456' in result
        assert 'linear: TEAM-789' in result
        assert 'github: null' not in result
        assert 'github:' not in result  # Should be completely removed

    def test_write_task_removes_empty_external_ids(self):
        """Test that empty external_ids dict is removed entirely."""
        task_data = {
            'id': 'TASK-001',
            'title': 'Test Task',
            'status': 'backlog',
            'created': '2025-01-08T10:00:00Z',
            'updated': '2025-01-08T10:00:00Z',
            'priority': 'medium',
            'tags': [],
            'complexity': 0,
            'external_ids': {},
            'test_results': {
                'status': 'pending',
                'coverage': None,
                'last_run': None
            }
        }

        result = write_task_frontmatter(task_data)

        assert 'external_ids' not in result

    def test_write_task_removes_none_legacy_id(self):
        """Test that None legacy_id is removed."""
        task_data = {
            'id': 'TASK-001',
            'title': 'Test Task',
            'status': 'backlog',
            'created': '2025-01-08T10:00:00Z',
            'updated': '2025-01-08T10:00:00Z',
            'priority': 'medium',
            'tags': [],
            'complexity': 0,
            'legacy_id': None,
            'test_results': {
                'status': 'pending',
                'coverage': None,
                'last_run': None
            }
        }

        result = write_task_frontmatter(task_data)

        assert 'legacy_id' not in result

    def test_write_task_preserves_legacy_id(self):
        """Test that non-None legacy_id is preserved."""
        task_data = {
            'id': 'TASK-E01-b2c4',
            'legacy_id': 'TASK-042',
            'title': 'Migrated Task',
            'status': 'in_progress',
            'created': '2024-12-15T10:00:00Z',
            'updated': '2025-01-08T10:00:00Z',
            'priority': 'high',
            'tags': [],
            'complexity': 5,
            'test_results': {
                'status': 'pending',
                'coverage': None,
                'last_run': None
            }
        }

        result = write_task_frontmatter(task_data)

        assert 'legacy_id: TASK-042' in result


class TestUpdateTaskFrontmatter:
    """Test updating task frontmatter in files."""

    def test_update_task_adds_external_ids(self, tmp_path):
        """Test adding external_ids to existing task."""
        task_file = tmp_path / "TASK-001.md"
        initial_content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: medium
tags: []
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Task Body
"""
        task_file.write_text(initial_content, encoding='utf-8')

        # Update with external_ids
        update_task_frontmatter(
            task_file,
            {'external_ids': {'jira': 'PROJ-456', 'github': '123'}},
            preserve_body=True
        )

        # Read back and verify
        updated_content = task_file.read_text(encoding='utf-8')
        frontmatter = parse_task_frontmatter(updated_content)

        assert frontmatter['external_ids'] == {'jira': 'PROJ-456', 'github': '123'}
        assert '# Task Body' in updated_content

    def test_update_task_merges_external_ids(self, tmp_path):
        """Test merging new external_ids with existing ones."""
        task_file = tmp_path / "TASK-001.md"
        initial_content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: medium
tags: []
complexity: 0
external_ids:
  jira: PROJ-456
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Task Body
"""
        task_file.write_text(initial_content, encoding='utf-8')

        # Merge additional external_ids
        update_task_frontmatter(
            task_file,
            {'external_ids': {'github': '123', 'linear': 'TEAM-789'}},
            preserve_body=True
        )

        # Read back and verify
        updated_content = task_file.read_text(encoding='utf-8')
        frontmatter = parse_task_frontmatter(updated_content)

        assert frontmatter['external_ids'] == {
            'jira': 'PROJ-456',
            'github': '123',
            'linear': 'TEAM-789'
        }

    def test_update_task_updates_timestamp(self, tmp_path):
        """Test that update automatically updates timestamp."""
        task_file = tmp_path / "TASK-001.md"
        initial_content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: medium
tags: []
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Task Body
"""
        task_file.write_text(initial_content, encoding='utf-8')

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        # Update task
        update_task_frontmatter(
            task_file,
            {'status': 'in_progress'},
            preserve_body=True
        )

        # Read back and verify
        updated_content = task_file.read_text(encoding='utf-8')
        frontmatter = parse_task_frontmatter(updated_content)

        assert frontmatter['updated'] != '2025-01-08T10:00:00Z'
        assert frontmatter['status'] == 'in_progress'


class TestReadTaskFile:
    """Test reading task files and separating frontmatter from body."""

    def test_read_task_file_with_external_ids(self, tmp_path):
        """Test reading task file with external_ids."""
        task_file = tmp_path / "TASK-001.md"
        content = """---
id: TASK-001
title: Test Task
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: high
tags: [test]
complexity: 3
external_ids:
  jira: PROJ-456
  github: 123
test_results:
  status: pending
  coverage: null
  last_run: null
---
# Task Body
## Description
Test description
"""
        task_file.write_text(content, encoding='utf-8')

        frontmatter, body = read_task_file(task_file)

        assert frontmatter['id'] == 'TASK-001'
        assert frontmatter['external_ids'] == {'jira': 'PROJ-456', 'github': 123}
        assert '# Task Body' in body
        assert '## Description' in body


class TestCreateTaskFrontmatter:
    """Test creating new task frontmatter dictionaries."""

    def test_create_task_with_external_ids(self):
        """Test creating task frontmatter with external_ids."""
        result = create_task_frontmatter(
            'TASK-001',
            'Test Task',
            priority='high',
            tags=['test', 'feature'],
            external_ids={'jira': 'PROJ-456', 'github': '123'}
        )

        assert result['id'] == 'TASK-001'
        assert result['title'] == 'Test Task'
        assert result['priority'] == 'high'
        assert result['tags'] == ['test', 'feature']
        assert result['external_ids'] == {'jira': 'PROJ-456', 'github': '123'}
        assert result['status'] == 'backlog'
        assert result['complexity'] == 0
        assert 'created' in result
        assert 'updated' in result

    def test_create_task_without_external_ids(self):
        """Test creating task without external_ids."""
        result = create_task_frontmatter(
            'TASK-002',
            'Simple Task'
        )

        assert result['id'] == 'TASK-002'
        assert 'external_ids' not in result  # Should not be present if not provided

    def test_create_task_with_default_values(self):
        """Test default values for optional fields."""
        result = create_task_frontmatter(
            'TASK-003',
            'Default Task'
        )

        assert result['priority'] == 'medium'
        assert result['tags'] == []
        assert result['complexity'] == 0
        assert result['status'] == 'backlog'
        assert result['test_results']['status'] == 'pending'


class TestValidateExternalIds:
    """Test validation and normalization of external_ids."""

    def test_validate_all_supported_tools(self):
        """Test validation with all supported PM tools."""
        external_ids = {
            'jira': 'PROJ-456',
            'azure_devops': '1234',
            'linear': 'TEAM-789',
            'github': 234
        }

        result = validate_external_ids(external_ids)

        assert result == {
            'jira': 'PROJ-456',
            'azure_devops': '1234',
            'linear': 'TEAM-789',
            'github': '234'  # Should be converted to string
        }

    def test_validate_converts_to_string(self):
        """Test that values are converted to strings."""
        external_ids = {
            'jira': 'PROJ-456',
            'github': 123,
            'azure_devops': 456.0
        }

        result = validate_external_ids(external_ids)

        assert result['github'] == '123'
        assert result['azure_devops'] == '456.0'

    def test_validate_unsupported_tool(self):
        """Test error for unsupported PM tool."""
        external_ids = {
            'jira': 'PROJ-456',
            'unsupported_tool': 'VALUE'
        }

        with pytest.raises(ValueError, match="Unsupported PM tool: unsupported_tool"):
            validate_external_ids(external_ids)

    def test_validate_not_dict(self):
        """Test error when external_ids is not a dictionary."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            validate_external_ids("invalid")

    def test_validate_filters_none_values(self):
        """Test that None values are filtered out."""
        external_ids = {
            'jira': 'PROJ-456',
            'github': None,
            'linear': 'TEAM-789'
        }

        result = validate_external_ids(external_ids)

        assert 'github' not in result
        assert result == {
            'jira': 'PROJ-456',
            'linear': 'TEAM-789'
        }
