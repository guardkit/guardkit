"""Unit tests for TaskStateBridge.

Tests the state bridge between AutoBuild orchestration and task-work state machine.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from guardkit.tasks.state_bridge import TaskStateBridge, STATE_DIRECTORIES
from guardkit.tasks.task_loader import TaskNotFoundError
from guardkit.orchestrator.exceptions import (
    TaskStateError,
    PlanNotFoundError,
    StateValidationError,
)


class TestTaskStateBridge:
    """Tests for TaskStateBridge class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        # Create task directories
        for state in STATE_DIRECTORIES:
            (repo_root / "tasks" / state).mkdir(parents=True, exist_ok=True)

        # Create .claude/task-plans directory
        (repo_root / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)

        yield repo_root

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_task_content(self):
        """Return sample task markdown content."""
        return """---
id: TASK-001
title: Sample task
status: backlog
---

# Sample Task

## Requirements

Implement sample feature.

## Acceptance Criteria

- [ ] Feature works correctly
- [ ] Tests pass
"""

    @pytest.fixture
    def sample_plan_content(self):
        """Return sample implementation plan content."""
        return """# Implementation Plan for TASK-001

## Overview

This plan describes how to implement the sample feature.

## Steps

1. Create the main module
2. Add tests
3. Verify functionality

## Files to Create

- src/sample.py
- tests/test_sample.py

## Estimated Effort

Low complexity, approximately 2 hours.
"""

    def test_init(self, temp_repo):
        """Test TaskStateBridge initialization."""
        bridge = TaskStateBridge("TASK-001", temp_repo)

        assert bridge.task_id == "TASK-001"
        assert bridge.repo_root == temp_repo

    def test_get_current_state_backlog(self, temp_repo, sample_task_content):
        """Test getting current state for task in backlog."""
        # Create task in backlog
        task_path = temp_repo / "tasks" / "backlog" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        state = bridge.get_current_state()

        assert state == "backlog"

    def test_get_current_state_design_approved(self, temp_repo, sample_task_content):
        """Test getting current state for task in design_approved."""
        # Create task in design_approved
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        state = bridge.get_current_state()

        assert state == "design_approved"

    def test_get_current_state_not_found(self, temp_repo):
        """Test getting current state when task doesn't exist."""
        bridge = TaskStateBridge("TASK-NONEXISTENT", temp_repo)

        with pytest.raises(TaskNotFoundError):
            bridge.get_current_state()

    def test_get_current_state_nested_directory(self, temp_repo, sample_task_content):
        """Test getting current state for task in nested directory."""
        # Create task in nested feature directory
        nested_dir = temp_repo / "tasks" / "backlog" / "feature-auth"
        nested_dir.mkdir(parents=True, exist_ok=True)
        task_path = nested_dir / "TASK-001-auth-login.md"
        task_path.write_text(sample_task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        state = bridge.get_current_state()

        assert state == "backlog"

    def test_transition_to_design_approved(self, temp_repo, sample_task_content):
        """Test transitioning task from backlog to design_approved."""
        # Create task in backlog
        task_path = temp_repo / "tasks" / "backlog" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        new_path = bridge.transition_to_design_approved()

        # Verify file moved
        assert not task_path.exists()
        assert new_path.exists()
        assert new_path.parent.name == "design_approved"

        # Verify frontmatter updated
        content = new_path.read_text()
        assert "status: design_approved" in content

    def test_verify_implementation_plan_exists_md(self, temp_repo, sample_plan_content):
        """Test verifying implementation plan exists (markdown)."""
        # Create implementation plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        plan_path.write_text(sample_plan_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        found_path = bridge.verify_implementation_plan_exists()

        assert found_path == plan_path

    def test_verify_implementation_plan_exists_json(self, temp_repo):
        """Test verifying implementation plan exists (JSON)."""
        # Create implementation plan as JSON
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.json"
        plan_content = '{"steps": ["step1", "step2"], "files": ["file1.py"]}'
        plan_path.write_text(plan_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        found_path = bridge.verify_implementation_plan_exists()

        assert found_path == plan_path

    def test_verify_implementation_plan_not_found(self, temp_repo):
        """Test verifying implementation plan when it doesn't exist."""
        bridge = TaskStateBridge("TASK-001", temp_repo)

        with pytest.raises(PlanNotFoundError) as exc_info:
            bridge.verify_implementation_plan_exists()

        assert "TASK-001" in str(exc_info.value)
        assert "task-work --design-only" in str(exc_info.value)

    def test_verify_implementation_plan_empty(self, temp_repo):
        """Test verifying implementation plan when file is empty."""
        # Create empty implementation plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        plan_path.write_text("# Plan")  # Too short (< 50 chars)

        bridge = TaskStateBridge("TASK-001", temp_repo)

        with pytest.raises(PlanNotFoundError):
            bridge.verify_implementation_plan_exists()

    def test_ensure_design_approved_state_already_approved(
        self, temp_repo, sample_task_content, sample_plan_content
    ):
        """Test ensure_design_approved_state when task already in design_approved."""
        # Create task in design_approved
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content.replace("status: backlog", "status: design_approved"))

        # Create implementation plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        plan_path.write_text(sample_plan_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        result = bridge.ensure_design_approved_state()

        assert result is True
        # Task should not have moved
        assert task_path.exists()

    def test_ensure_design_approved_state_from_backlog(
        self, temp_repo, sample_task_content, sample_plan_content
    ):
        """Test ensure_design_approved_state transitions from backlog."""
        # Create task in backlog
        task_path = temp_repo / "tasks" / "backlog" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content)

        # Create implementation plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        plan_path.write_text(sample_plan_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        result = bridge.ensure_design_approved_state()

        assert result is True
        # Task should have moved
        assert not task_path.exists()
        new_path = temp_repo / "tasks" / "design_approved" / "TASK-001-sample.md"
        assert new_path.exists()

    def test_ensure_design_approved_state_missing_plan(
        self, temp_repo, sample_task_content
    ):
        """Test ensure_design_approved_state fails without implementation plan."""
        # Create task in design_approved but no plan
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001-sample.md"
        task_path.write_text(sample_task_content.replace("status: backlog", "status: design_approved"))

        bridge = TaskStateBridge("TASK-001", temp_repo)

        with pytest.raises(PlanNotFoundError):
            bridge.ensure_design_approved_state()

    def test_ensure_design_approved_state_task_not_found(self, temp_repo):
        """Test ensure_design_approved_state fails when task doesn't exist."""
        bridge = TaskStateBridge("TASK-NONEXISTENT", temp_repo)

        with pytest.raises(TaskNotFoundError):
            bridge.ensure_design_approved_state()


class TestTaskStateBridgeEdgeCases:
    """Edge case tests for TaskStateBridge."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        for state in STATE_DIRECTORIES:
            (repo_root / "tasks" / state).mkdir(parents=True, exist_ok=True)
        (repo_root / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)

        yield repo_root
        shutil.rmtree(temp_dir)

    def test_alternative_plan_location_docs_state(self, temp_repo):
        """Test finding plan in docs/state/ alternative location."""
        # Create plan in alternative location
        alt_plan_dir = temp_repo / "docs" / "state" / "TASK-001"
        alt_plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = alt_plan_dir / "implementation_plan.md"
        plan_path.write_text("# Implementation Plan\n\nDetailed plan with more than 50 characters of content.")

        bridge = TaskStateBridge("TASK-001", temp_repo)
        found_path = bridge.verify_implementation_plan_exists()

        assert found_path == plan_path

    def test_task_with_extended_filename(self, temp_repo):
        """Test finding task with extended descriptive filename."""
        task_content = """---
id: TASK-AUTH-001
title: Implement OAuth
status: in_progress
---

# OAuth Implementation
"""
        task_path = temp_repo / "tasks" / "in_progress" / "TASK-AUTH-001-implement-oauth-flow.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-AUTH-001", temp_repo)
        state = bridge.get_current_state()

        assert state == "in_progress"

    def test_multiple_tasks_same_prefix(self, temp_repo):
        """Test handling multiple tasks with same prefix returns first match."""
        task1_content = """---
id: TASK-001
status: backlog
---
"""
        task2_content = """---
id: TASK-0012
status: in_progress
---
"""
        # Create tasks
        (temp_repo / "tasks" / "backlog" / "TASK-001-first.md").write_text(task1_content)
        (temp_repo / "tasks" / "in_progress" / "TASK-0012-second.md").write_text(task2_content)

        # Should find TASK-001 (not TASK-0012)
        bridge = TaskStateBridge("TASK-001", temp_repo)
        state = bridge.get_current_state()

        assert state == "backlog"


class TestAgentInvokerStateBridgeIntegration:
    """Test AgentInvoker's _ensure_design_approved_state method."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        for state in STATE_DIRECTORIES:
            (repo_root / "tasks" / state).mkdir(parents=True, exist_ok=True)
        (repo_root / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)

        yield repo_root
        shutil.rmtree(temp_dir)

    def test_ensure_design_approved_state_success(self, temp_repo):
        """Test _ensure_design_approved_state succeeds with valid setup."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        # Create task in design_approved
        task_content = """---
id: TASK-001
status: design_approved
---
# Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        # Create implementation plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        plan_path.write_text("# Implementation Plan\n\nThis is a detailed plan with sufficient content for validation.")

        invoker = AgentInvoker(worktree_path=temp_repo)
        # Should not raise
        invoker._ensure_design_approved_state("TASK-001")

    def test_ensure_design_approved_state_missing_plan(self, temp_repo):
        """Test _ensure_design_approved_state fails with missing plan."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        # Create task in design_approved but no plan
        task_content = """---
id: TASK-001
status: design_approved
---
# Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        invoker = AgentInvoker(worktree_path=temp_repo)

        with pytest.raises(PlanNotFoundError):
            invoker._ensure_design_approved_state("TASK-001")

    def test_ensure_design_approved_state_task_not_found(self, temp_repo):
        """Test _ensure_design_approved_state fails with missing task."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker(worktree_path=temp_repo)

        with pytest.raises(TaskNotFoundError):
            invoker._ensure_design_approved_state("TASK-NONEXISTENT")


class TestStubCreation:
    """Tests for stub implementation plan creation logic."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        for state in STATE_DIRECTORIES:
            (repo_root / "tasks" / state).mkdir(parents=True, exist_ok=True)
        (repo_root / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)

        yield repo_root
        shutil.rmtree(temp_dir)

    def test_stub_created_for_task_with_autobuild_config(self, temp_repo):
        """Test stub creation for task with explicit autobuild configuration."""
        task_content = """---
id: TASK-001
title: Test task
status: design_approved
autobuild:
  enabled: true
---
# Test Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is not None
        assert stub_path.exists()
        assert "Implementation Plan" in stub_path.read_text()

    def test_stub_created_for_task_with_implementation_mode_task_work(self, temp_repo):
        """Test stub creation for feature task with implementation_mode: task-work."""
        task_content = """---
id: TASK-FHA-001
title: Create project structure
status: design_approved
implementation_mode: task-work
wave: 1
---
# Feature Task

Task created via /feature-plan
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-FHA-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-FHA-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is not None
        assert stub_path.exists()
        content = stub_path.read_text()
        assert "Implementation Plan" in content
        assert "TASK-FHA-001" in content

    def test_stub_created_for_task_with_autobuild_state(self, temp_repo):
        """Test stub creation for task with runtime autobuild_state."""
        task_content = """---
id: TASK-001
title: Test task
status: design_approved
autobuild_state:
  worktree_path: /tmp/test
  base_branch: main
---
# Test Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is not None
        assert stub_path.exists()

    def test_stub_not_created_for_unknown_mode(self, temp_repo):
        """Test stub is NOT created for task with unknown/invalid implementation mode.

        Note: 'manual' was a deprecated mode removed in TASK-RMM-001.
        This test verifies backward compatibility: tasks with unrecognized
        implementation_mode values don't get stubs created.
        """
        task_content = """---
id: TASK-001
title: Unknown mode task
status: design_approved
implementation_mode: unknown
---
# Unknown Mode Task

This task has an unrecognized implementation mode.
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is None

    def test_stub_not_created_for_direct_mode_without_autobuild(self, temp_repo):
        """Test stub is NOT created for direct mode without autobuild config."""
        task_content = """---
id: TASK-001
title: Direct task
status: design_approved
implementation_mode: direct
---
# Direct Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is None

    def test_stub_not_created_for_task_without_any_config(self, temp_repo):
        """Test stub is NOT created for task with no relevant configuration."""
        task_content = """---
id: TASK-001
title: Plain task
status: design_approved
---
# Plain Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        assert stub_path is None

    def test_existing_valid_plan_not_overwritten(self, temp_repo):
        """Test existing valid plan is not overwritten by stub creation."""
        task_content = """---
id: TASK-001
title: Test task
status: design_approved
implementation_mode: task-work
---
# Test Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        # Create existing plan
        plan_path = temp_repo / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        original_content = "# Existing Plan\n\nThis is an existing detailed plan with more than 50 characters."
        plan_path.write_text(original_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        result_path = bridge._create_stub_implementation_plan()

        # Should return existing path, not create new stub
        assert result_path == plan_path
        assert plan_path.read_text() == original_content

    def test_stub_content_includes_task_title(self, temp_repo):
        """Test stub content includes task title."""
        task_content = """---
id: TASK-001
title: Create authentication module
status: design_approved
implementation_mode: task-work
---
# Auth Task
"""
        task_path = temp_repo / "tasks" / "design_approved" / "TASK-001.md"
        task_path.write_text(task_content)

        bridge = TaskStateBridge("TASK-001", temp_repo)
        stub_path = bridge._create_stub_implementation_plan()

        content = stub_path.read_text()
        assert "Create authentication module" in content
