"""Shared fixtures for clarification integration tests.

These fixtures provide temp directory setups and task file creation
for testing real orchestrator integration with clarification modules.
"""

import sys
import tempfile
import pytest
from pathlib import Path
from typing import Generator

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """
    Create temporary project directory with tasks structure.

    Creates:
        temp_dir/
        ├── tasks/
        │   ├── backlog/
        │   ├── in_progress/
        │   ├── in_review/
        │   ├── blocked/
        │   ├── completed/
        │   └── review_complete/
        └── .git/  (marker for git root detection)

    Yields:
        Path to temporary project root directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create tasks directory structure
        task_states = [
            "backlog",
            "in_progress",
            "in_review",
            "blocked",
            "completed",
            "review_complete",
        ]
        for state in task_states:
            (temp_path / "tasks" / state).mkdir(parents=True)

        # Create .git marker directory (for git_state_helper.get_git_root)
        (temp_path / ".git").mkdir()

        yield temp_path


@pytest.fixture
def sample_review_task(temp_project_dir: Path) -> tuple[str, Path]:
    """
    Create a sample review task file in backlog.

    Args:
        temp_project_dir: Fixture providing temp directory

    Returns:
        Tuple of (task_id, task_file_path)
    """
    task_id = "TASK-TEST-REVIEW-001"
    task_content = f"""---
id: {task_id}
title: "Review authentication architecture"
status: backlog
task_type: review
complexity: 5
priority: medium
created: 2025-12-13T10:00:00Z
updated: 2025-12-13T10:00:00Z
---

# Review: Authentication Architecture

## Description

Review the authentication architecture for the user management system.
Analyze SOLID principles compliance and security patterns.

## Review Scope

- Authentication flow
- Token management
- Session handling
- Security best practices

## Acceptance Criteria

- [ ] Review complete with findings documented
- [ ] Recommendations provided
- [ ] Decision options presented
"""

    task_file = temp_project_dir / "tasks" / "backlog" / f"{task_id}.md"
    task_file.write_text(task_content)

    return task_id, task_file


@pytest.fixture
def simple_review_task(temp_project_dir: Path) -> tuple[str, Path]:
    """
    Create a simple (low complexity) review task.

    Args:
        temp_project_dir: Fixture providing temp directory

    Returns:
        Tuple of (task_id, task_file_path)
    """
    task_id = "TASK-TEST-SIMPLE-001"
    task_content = f"""---
id: {task_id}
title: "Review logging format"
status: backlog
task_type: review
complexity: 2
priority: low
created: 2025-12-13T10:00:00Z
updated: 2025-12-13T10:00:00Z
---

# Review: Logging Format

## Description

Simple review of logging format consistency.

## Review Scope

- Log message format

## Acceptance Criteria

- [ ] Format reviewed
"""

    task_file = temp_project_dir / "tasks" / "backlog" / f"{task_id}.md"
    task_file.write_text(task_content)

    return task_id, task_file


@pytest.fixture
def complex_review_task(temp_project_dir: Path) -> tuple[str, Path]:
    """
    Create a complex (high complexity) review task.

    Args:
        temp_project_dir: Fixture providing temp directory

    Returns:
        Tuple of (task_id, task_file_path)
    """
    task_id = "TASK-TEST-COMPLEX-001"
    task_content = f"""---
id: {task_id}
title: "Security audit of payment system"
status: backlog
task_type: review
complexity: 8
priority: high
created: 2025-12-13T10:00:00Z
updated: 2025-12-13T10:00:00Z
---

# Security Audit: Payment System

## Description

Comprehensive security audit of the payment processing system including
PCI compliance, encryption standards, and access controls.

## Review Scope

- Payment flow security
- PCI DSS compliance
- Data encryption
- Access controls
- Audit logging
- Fraud detection

## Acceptance Criteria

- [ ] Security vulnerabilities identified
- [ ] Compliance gaps documented
- [ ] Remediation plan created
- [ ] Risk assessment completed
"""

    task_file = temp_project_dir / "tasks" / "backlog" / f"{task_id}.md"
    task_file.write_text(task_content)

    return task_id, task_file


def create_task_in_state(
    temp_project_dir: Path,
    task_id: str,
    state: str,
    complexity: int = 5,
    task_type: str = "review"
) -> Path:
    """
    Helper to create a task file in a specific state.

    Args:
        temp_project_dir: Temp project directory
        task_id: Task identifier
        state: Task state (backlog, in_progress, etc.)
        complexity: Complexity score (0-10)
        task_type: Task type (review, implementation)

    Returns:
        Path to created task file
    """
    task_content = f"""---
id: {task_id}
title: "Test task {task_id}"
status: {state}
task_type: {task_type}
complexity: {complexity}
priority: medium
created: 2025-12-13T10:00:00Z
updated: 2025-12-13T10:00:00Z
---

# Test Task

## Description

Test task for integration testing.

## Acceptance Criteria

- [ ] Test complete
"""

    task_file = temp_project_dir / "tasks" / state / f"{task_id}.md"
    task_file.write_text(task_content)

    return task_file
