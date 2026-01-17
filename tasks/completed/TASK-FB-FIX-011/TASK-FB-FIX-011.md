---
id: TASK-FB-FIX-011
title: Add config propagation integration tests
status: completed
created: 2026-01-12T00:00:00Z
updated: 2026-01-12T12:00:00Z
completed: 2026-01-12T12:30:00Z
priority: medium
complexity: 4
tags: [feature-build, testing, integration-tests, config-propagation]
parent_review: TASK-REV-FB08
depends_on: [TASK-FB-FIX-009, TASK-FB-FIX-010]
completed_location: tasks/completed/TASK-FB-FIX-011/
---

# Task: Add config propagation integration tests

## Description

Add comprehensive integration tests to verify that configuration values (`sdk_timeout` and `enable_pre_loop`) propagate correctly through the entire chain from CLI to `TaskWorkInterface`.

This task depends on TASK-FB-FIX-009 and TASK-FB-FIX-010 being completed first.

## Requirements

1. Create new test file for config propagation tests
2. Test `sdk_timeout` propagation end-to-end
3. Test `enable_pre_loop` cascade priority
4. Test combination scenarios
5. Verify values reach final destination (TaskWorkInterface)

## Acceptance Criteria

- [x] New test file `tests/integration/test_config_propagation.py` created
- [x] Tests verify `sdk_timeout` propagates from CLI to `TaskWorkInterface`
- [x] Tests verify `enable_pre_loop` cascade priority works correctly
- [x] Tests use mocks to avoid actual SDK calls
- [x] Tests cover edge cases (None values, invalid values)
- [x] All tests pass in CI

## Test Cases

### sdk_timeout Propagation Tests

```python
class TestSdkTimeoutPropagation:
    """Test sdk_timeout propagates through the full chain."""

    def test_cli_to_task_work_interface(self):
        """CLI --sdk-timeout reaches TaskWorkInterface."""
        # Arrange: Create orchestrators with sdk_timeout=1200
        # Act: Trigger pre-loop phase
        # Assert: TaskWorkInterface.sdk_timeout_seconds == 1200

    def test_task_frontmatter_override(self):
        """Task frontmatter sdk_timeout used when CLI is None."""
        # Arrange: Task with autobuild.sdk_timeout: 900
        # Act: Execute task without CLI override
        # Assert: TaskWorkInterface.sdk_timeout_seconds == 900

    def test_default_value_propagates(self):
        """Default 600s propagates when no override specified."""
        # Arrange: No CLI, no frontmatter
        # Act: Execute task
        # Assert: TaskWorkInterface.sdk_timeout_seconds == 600

    def test_cli_overrides_frontmatter(self):
        """CLI flag takes precedence over task frontmatter."""
        # Arrange: CLI=1200, frontmatter=900
        # Act: Execute task
        # Assert: TaskWorkInterface.sdk_timeout_seconds == 1200
```

### enable_pre_loop Cascade Tests

```python
class TestEnablePreLoopCascade:
    """Test enable_pre_loop configuration cascade."""

    def test_cli_flag_highest_priority(self):
        """CLI --no-pre-loop overrides all other config."""
        # Arrange: Feature YAML=true, task=true, CLI=false
        # Assert: Pre-loop skipped

    def test_task_frontmatter_overrides_feature(self):
        """Task frontmatter overrides feature YAML."""
        # Arrange: Feature YAML=true, task=false, no CLI
        # Assert: Pre-loop skipped for that task

    def test_feature_yaml_used_when_no_task_override(self):
        """Feature YAML used when task doesn't override."""
        # Arrange: Feature YAML=false, no task config, no CLI
        # Assert: Pre-loop skipped

    def test_default_true_when_no_config(self):
        """Default True used when nothing configured."""
        # Arrange: No config anywhere
        # Assert: Pre-loop runs
```

### Combination Tests

```python
class TestConfigCombinations:
    """Test various config combinations."""

    def test_both_configs_from_cli(self):
        """Both sdk_timeout and enable_pre_loop from CLI."""
        # Arrange: --sdk-timeout 1200 --no-pre-loop
        # Assert: sdk_timeout=1200, enable_pre_loop=False

    def test_mixed_sources(self):
        """sdk_timeout from CLI, enable_pre_loop from YAML."""
        # Arrange: CLI sdk_timeout=1200, YAML enable_pre_loop=false
        # Assert: Both values correct

    def test_feature_level_defaults(self):
        """Feature YAML provides defaults for all tasks."""
        # Arrange: Feature YAML with both configs
        # Assert: All tasks in feature use those values
```

## Implementation Guide

### Test Structure

```python
# tests/integration/test_config_propagation.py

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface


@pytest.fixture
def mock_worktree():
    """Create mock worktree for testing."""
    worktree = Mock()
    worktree.path = Path("/tmp/test-worktree")
    worktree.task_id = "TASK-TEST-001"
    return worktree


@pytest.fixture
def mock_sdk():
    """Mock Claude Agent SDK to avoid actual calls."""
    with patch("guardkit.orchestrator.quality_gates.task_work_interface.query") as mock:
        yield mock


class TestSdkTimeoutPropagation:
    """Test sdk_timeout propagates through the full chain."""

    def test_cli_to_task_work_interface(self, mock_worktree, mock_sdk):
        """CLI --sdk-timeout reaches TaskWorkInterface."""
        # Arrange
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            sdk_timeout=1200,
        )

        # Capture TaskWorkInterface creation
        captured_timeout = None
        original_init = TaskWorkInterface.__init__

        def capture_init(self, worktree_path, sdk_timeout_seconds=600):
            nonlocal captured_timeout
            captured_timeout = sdk_timeout_seconds
            original_init(self, worktree_path, sdk_timeout_seconds)

        with patch.object(TaskWorkInterface, "__init__", capture_init):
            # Act: Create PreLoopQualityGates through orchestrator
            orchestrator._pre_loop_gates = None  # Force creation
            orchestrator._existing_worktree = mock_worktree
            # ... trigger pre-loop phase setup

        # Assert
        assert captured_timeout == 1200
```

## Files to Create/Modify

- `tests/integration/test_config_propagation.py` (new)
- `tests/conftest.py` (add shared fixtures if needed)

## Notes

- Use mocks extensively to avoid SDK calls
- Focus on verifying parameter passing, not actual functionality
- Consider parametrized tests for cascade combinations
