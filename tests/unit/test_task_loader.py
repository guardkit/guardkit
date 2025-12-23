"""
Unit tests for TaskLoader.

This module provides comprehensive tests for task file loading and parsing,
ensuring robust YAML frontmatter handling and content extraction.
"""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch

from guardkit.tasks.task_loader import (
    TaskLoader,
    TaskNotFoundError,
    TaskParseError,
)


# ============================================================================
# Test: Task File Discovery
# ============================================================================


def test_load_task_from_backlog(tmp_path):
    """Test loading task from backlog directory."""
    # Create task file in backlog
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: Test Task
---

## Requirements
Implement feature X

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify
    assert task_data["task_id"] == "TASK-AB-001"
    assert "feature X" in task_data["requirements"]
    assert len(task_data["acceptance_criteria"]) == 2


def test_load_task_from_in_progress(tmp_path):
    """Test loading task from in_progress directory."""
    # Create task file in in_progress
    task_file = tmp_path / "tasks" / "in_progress" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
---

## Requirements
Implement feature X
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify found in in_progress
    assert task_data["task_id"] == "TASK-AB-001"


def test_load_task_not_found(tmp_path):
    """Test TaskNotFoundError when task doesn't exist."""
    # Attempt to load non-existent task
    with pytest.raises(TaskNotFoundError) as exc_info:
        TaskLoader.load_task("TASK-AB-999", repo_root=tmp_path)

    # Verify error message includes search paths
    assert "TASK-AB-999" in str(exc_info.value)
    assert "backlog" in str(exc_info.value)
    assert "in_progress" in str(exc_info.value)


def test_load_task_search_order(tmp_path):
    """Test that backlog is searched before in_progress."""
    # Create task in both locations (should find backlog first)
    backlog_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    backlog_file.parent.mkdir(parents=True, exist_ok=True)
    backlog_file.write_text(
        """---
title: From Backlog
---
Requirements from backlog
"""
    )

    in_progress_file = tmp_path / "tasks" / "in_progress" / "TASK-AB-001.md"
    in_progress_file.parent.mkdir(parents=True, exist_ok=True)
    in_progress_file.write_text(
        """---
title: From In Progress
---
Requirements from in_progress
"""
    )

    # Load task
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Should find backlog version first
    assert task_data["frontmatter"]["title"] == "From Backlog"


# ============================================================================
# Test: Frontmatter Parsing
# ============================================================================


def test_parse_task_with_frontmatter(tmp_path):
    """Test parsing task with YAML frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: OAuth Implementation
status: backlog
priority: high
requirements: Implement OAuth2 authentication
acceptance_criteria:
  - Support authorization code flow
  - Handle token refresh
  - Include tests
---

# Task Content
This is the task content.
"""
    )

    # Load and parse
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify frontmatter
    assert task_data["frontmatter"]["id"] == "TASK-AB-001"
    assert task_data["frontmatter"]["title"] == "OAuth Implementation"
    assert task_data["frontmatter"]["status"] == "backlog"
    assert task_data["frontmatter"]["priority"] == "high"

    # Verify requirements from frontmatter
    assert "OAuth2 authentication" in task_data["requirements"]

    # Verify acceptance criteria from frontmatter
    assert len(task_data["acceptance_criteria"]) == 3
    assert "authorization code flow" in task_data["acceptance_criteria"][0]


def test_parse_task_without_frontmatter(tmp_path):
    """Test parsing task without frontmatter (content-only)."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Implement feature X

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
"""
    )

    # Load and parse
    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify requirements extracted from content
    assert "feature X" in task_data["requirements"]

    # Verify acceptance criteria extracted from content
    assert len(task_data["acceptance_criteria"]) == 2


def test_parse_task_malformed_yaml(tmp_path):
    """Test TaskParseError when YAML is malformed."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
title: [invalid yaml
---

Content
"""
    )

    # Should raise TaskParseError
    with pytest.raises(TaskParseError) as exc_info:
        TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    assert "Failed to parse" in str(exc_info.value)


# ============================================================================
# Test: Requirements Extraction
# ============================================================================


def test_extract_requirements_from_frontmatter(tmp_path):
    """Test extracting requirements from frontmatter field."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
requirements: Implement OAuth2 authentication with token refresh
---

Other content
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "OAuth2 authentication" in task_data["requirements"]


def test_extract_requirements_from_content_section(tmp_path):
    """Test extracting requirements from ## Requirements section."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Implement feature X with the following:
- OAuth2 support
- Token refresh

## Other Section
Other content
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "feature X" in task_data["requirements"]
    assert "OAuth2 support" in task_data["requirements"]


def test_extract_requirements_from_first_paragraph(tmp_path):
    """Test fallback to first paragraph when no explicit requirements."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """This task implements OAuth2 authentication.

Additional details here.
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert "OAuth2 authentication" in task_data["requirements"]


def test_extract_requirements_list_from_frontmatter(tmp_path):
    """Test extracting requirements as list from frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
requirements:
  - Implement OAuth2
  - Add token refresh
  - Include tests
---
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    # Should join list into string
    assert "OAuth2" in task_data["requirements"]
    assert "token refresh" in task_data["requirements"]


# ============================================================================
# Test: Acceptance Criteria Extraction
# ============================================================================


def test_extract_acceptance_criteria_from_frontmatter(tmp_path):
    """Test extracting acceptance criteria from frontmatter."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
acceptance_criteria:
  - Support OAuth2
  - Handle refresh
  - Include tests
---
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 3
    assert "OAuth2" in task_data["acceptance_criteria"][0]


def test_extract_acceptance_criteria_from_content_section(tmp_path):
    """Test extracting acceptance criteria from ## Acceptance Criteria section."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Acceptance Criteria
- [ ] Support OAuth2
- [x] Handle refresh
- Include tests

## Other Section
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 3
    assert "OAuth2" in task_data["acceptance_criteria"][0]
    assert "refresh" in task_data["acceptance_criteria"][1]


def test_extract_acceptance_criteria_various_formats(tmp_path):
    """Test parsing various bullet/checkbox formats."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Acceptance Criteria
- [ ] Checkbox unchecked
- [x] Checkbox checked
- Bullet point
* Asterisk bullet
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    assert len(task_data["acceptance_criteria"]) == 4


def test_extract_acceptance_criteria_default(tmp_path):
    """Test default when no criteria found."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """## Requirements
Just requirements, no criteria
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)
    # Should have default message
    assert "No acceptance criteria specified" in task_data["acceptance_criteria"]


# ============================================================================
# Test: Complete Task Data Structure
# ============================================================================


def test_load_task_returns_complete_structure(tmp_path):
    """Test that load_task returns all expected fields."""
    task_file = tmp_path / "tasks" / "backlog" / "TASK-AB-001.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        """---
id: TASK-AB-001
---

## Requirements
Implement feature
"""
    )

    task_data = TaskLoader.load_task("TASK-AB-001", repo_root=tmp_path)

    # Verify all expected keys present
    assert "task_id" in task_data
    assert "requirements" in task_data
    assert "acceptance_criteria" in task_data
    assert "frontmatter" in task_data
    assert "content" in task_data
    assert "file_path" in task_data

    # Verify types
    assert isinstance(task_data["task_id"], str)
    assert isinstance(task_data["requirements"], str)
    assert isinstance(task_data["acceptance_criteria"], list)
    assert isinstance(task_data["frontmatter"], dict)
    assert isinstance(task_data["content"], str)
    assert isinstance(task_data["file_path"], Path)
