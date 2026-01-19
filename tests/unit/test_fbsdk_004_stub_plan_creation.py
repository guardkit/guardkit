"""
Comprehensive Test Suite for TASK-FBSDK-004: Stub Implementation Plan Creation

Tests stub plan creation for feature-build tasks with pre-loop disabled.

Coverage Target: >=80%
Test Count: 12 unit tests, 3 integration tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock

from guardkit.tasks.state_bridge import TaskStateBridge
from guardkit.orchestrator.exceptions import PlanNotFoundError
from guardkit.tasks.task_loader import TaskLoader
from guardkit.orchestrator.paths import TaskArtifactPaths


class TestStubImplementationPlanCreation:
    """Test stub implementation plan creation in state bridge and orchestrator."""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        # Create required directories
        (repo_root / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)
        (repo_root / "tasks" / "backlog").mkdir(parents=True, exist_ok=True)
        (repo_root / "tasks" / "design_approved").mkdir(parents=True, exist_ok=True)
        (repo_root / ".guardkit" / "features").mkdir(parents=True, exist_ok=True)
        (repo_root / ".guardkit" / "worktrees").mkdir(parents=True, exist_ok=True)

        yield repo_root

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def feature_task_content(self):
        """Return feature task with autobuild config."""
        return """---
id: TASK-DM-001
title: Add CSS variables for dark mode
status: backlog
autobuild:
  enabled: true
  enable_pre_loop: false
---

# Add CSS Variables for Dark Mode

## Requirements

Add CSS custom properties for theming.

## Acceptance Criteria

- [ ] CSS variables defined
- [ ] Tests pass
"""

    @pytest.fixture
    def standalone_task_content(self):
        """Return standalone task without autobuild config."""
        return """---
id: TASK-XXX
title: Standalone task
status: backlog
---

# Standalone Task

## Requirements

Implement feature.
"""

    # ============================================================================
    # 1. State Bridge Stub Creation Tests (6 tests)
    # ============================================================================

    def test_state_bridge_creates_stub_for_autobuild_task(self, temp_repo, feature_task_content):
        """Test state bridge creates stub for autobuild task when plan missing."""
        # Create task file
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Create state bridge
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)

        # Should create stub automatically
        result_path = bridge.verify_implementation_plan_exists()
        assert result_path.exists()

        content = result_path.read_text()
        assert "Auto-generated stub" in content
        assert "TASK-DM-001" in content
        assert "Add CSS variables for dark mode" in content

    def test_state_bridge_stub_is_idempotent(self, temp_repo, feature_task_content):
        """Test stub creation doesn't overwrite existing valid plans."""
        # Create task file
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Create valid plan first
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-DM-001-implementation-plan.md"
        original_content = "# Valid Implementation Plan\n\nDetailed plan with >50 chars content."
        plan_path.write_text(original_content)

        # Create state bridge
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)

        # Verify returns existing plan without modification
        result_path = bridge.verify_implementation_plan_exists()
        assert result_path.read_text() == original_content

    def test_state_bridge_skip_stub_for_non_autobuild_task(self, temp_repo, standalone_task_content):
        """Test state bridge doesn't create stub for tasks without autobuild config."""
        # Create standalone task
        task_path = temp_repo / "tasks" / "backlog" / "TASK-XXX.md"
        task_path.write_text(standalone_task_content)

        # Create state bridge
        bridge = TaskStateBridge("TASK-XXX", temp_repo)

        # Should raise PlanNotFoundError (no autobuild config, stub not created)
        with pytest.raises(PlanNotFoundError) as exc_info:
            bridge.verify_implementation_plan_exists()

        assert "TASK-XXX" in str(exc_info.value)
        assert "Implementation plan not found" in str(exc_info.value)

    def test_state_bridge_replaces_empty_plan_with_stub(self, temp_repo, feature_task_content):
        """Test state bridge treats empty plan as invalid and creates stub."""
        # Create task file
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Create empty plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-DM-001-implementation-plan.md"
        plan_path.write_text("# Empty\n")  # Less than 50 chars threshold

        # Create state bridge
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)

        # Should replace empty plan with stub
        result_path = bridge.verify_implementation_plan_exists()
        assert result_path.exists()

        content = result_path.read_text()
        assert len(content) > 50
        assert "Auto-generated stub" in content

    def test_state_bridge_stub_content_structure(self, temp_repo, feature_task_content):
        """Test state bridge creates valid stub with all required sections."""
        # Create task file
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Create state bridge
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)

        # Create stub
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        # Verify required sections
        assert "# Implementation Plan: TASK-DM-001" in content
        assert "## Task" in content
        assert "Add CSS variables for dark mode" in content
        assert "## Plan Status" in content
        assert "Auto-generated stub" in content
        assert "## Implementation" in content
        assert "Follow acceptance criteria" in content
        assert "## Notes" in content
        assert "enable_pre_loop=" in content

    def test_state_bridge_creates_plan_directory_if_missing(self, temp_repo, feature_task_content):
        """Test stub creation creates plan directory if it doesn't exist."""
        # Create task file
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Remove plan directory
        plan_dir = temp_repo / ".claude" / "task-plans"
        if plan_dir.exists():
            shutil.rmtree(plan_dir)

        # Create state bridge
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)

        # Should create directory and stub
        result_path = bridge.verify_implementation_plan_exists()
        assert result_path.parent.exists()
        assert result_path.exists()

    # ============================================================================
    # 2. Stub Content Validation Tests (6 tests)
    # ============================================================================

    def test_stub_includes_task_id(self, temp_repo, feature_task_content):
        """Test stub includes task ID in header."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "TASK-DM-001" in content

    def test_stub_includes_task_title(self, temp_repo, feature_task_content):
        """Test stub includes task title from frontmatter."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "Add CSS variables for dark mode" in content

    def test_stub_includes_timestamp(self, temp_repo, feature_task_content):
        """Test stub includes generation timestamp."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "Generated:" in content

    def test_stub_reflects_enable_pre_loop_false(self, temp_repo, feature_task_content):
        """Test stub content reflects enable_pre_loop=False setting."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "enable_pre_loop=False" in content

    def test_stub_references_task_file_for_details(self, temp_repo, feature_task_content):
        """Test stub directs users to task file for specifications."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "task markdown file" in content.lower() or "task file" in content.lower()

    def test_stub_explains_auto_generation_reason(self, temp_repo, feature_task_content):
        """Test stub explains why it was auto-generated."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()
        content = result_path.read_text()

        assert "Pre-loop was skipped" in content
        assert "/feature-plan" in content

    # ============================================================================
    # 3. Edge Cases and Error Handling (3 tests)
    # ============================================================================

    def test_stub_creation_with_missing_task_file(self, temp_repo):
        """Test behavior when task file doesn't exist."""
        bridge = TaskStateBridge("TASK-MISSING", temp_repo)

        # Should raise error when task not found
        with pytest.raises(Exception):  # TaskNotFoundError or PlanNotFoundError
            bridge.verify_implementation_plan_exists()

    def test_stub_handles_task_without_title(self, temp_repo):
        """Test stub creation when task has no title in frontmatter."""
        task_content = """---
id: TASK-DM-001
status: backlog
autobuild:
  enabled: true
  enable_pre_loop: false
---

# Task without title

## Requirements
Feature.
"""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()

        # Should still create stub with fallback title
        assert result_path.exists()
        content = result_path.read_text()
        assert "TASK-DM-001" in content

    def test_verify_accepts_valid_stub_plan(self, temp_repo, feature_task_content):
        """Test verify method accepts existing valid stub."""
        task_path = temp_repo / "tasks" / "backlog" / "TASK-DM-001.md"
        task_path.write_text(feature_task_content)

        # Create stub plan manually
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-DM-001-implementation-plan.md"
        stub_content = "# Stub Plan\n\nAuto-generated stub with sufficient content for validation."
        plan_path.write_text(stub_content)

        # State bridge should accept it
        bridge = TaskStateBridge("TASK-DM-001", temp_repo)
        result_path = bridge.verify_implementation_plan_exists()

        assert result_path == plan_path
        assert result_path.exists()
        assert result_path.read_text() == stub_content
