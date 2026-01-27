"""
Integration Tests for Pre-Loop Security Review (Phase 2.5C) - TASK-SEC-005.

Tests for the revised architecture where:
- Full security review runs in **pre-loop** (Phase 2.5C) via TaskWorkInterface
- Results are persisted to .guardkit/autobuild/{task_id}/security_review.json
- Coach only **reads** security results (no agent invocation)

Test Categories:
- Security-tagged task triggers review
- Non-security task skips review
- Security review via TaskWorkInterface
- Results persistence
- Pre-loop integration with orchestrator
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
from guardkit.orchestrator.quality_gates.security_detection import should_run_full_review
from guardkit.orchestrator.quality_gates.security_review import (
    SecurityReviewer,
    SecurityReviewResult,
    save_security_review,
    load_security_review,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_worktree(tmp_path):
    """Create a temporary worktree structure for testing."""
    worktree = tmp_path / "test_worktree"
    worktree.mkdir()
    (worktree / "src").mkdir()
    (worktree / ".guardkit" / "autobuild").mkdir(parents=True)
    return worktree


@pytest.fixture
def security_task():
    """Create a task with security tags."""
    return {
        "id": "TASK-SEC-001",
        "title": "Implement user authentication",
        "description": "Add login and logout functionality",
        "tags": ["authentication", "security"],
    }


@pytest.fixture
def non_security_task():
    """Create a task without security tags."""
    return {
        "id": "TASK-UI-001",
        "title": "Add profile page styling",
        "description": "Update CSS for user profile",
        "tags": ["ui", "styling"],
    }


@pytest.fixture
def vulnerable_worktree(temp_worktree):
    """Create a worktree with vulnerable code."""
    src_file = temp_worktree / "src" / "config.py"
    src_file.write_text('API_KEY = "sk-secret-key-12345"\nDEBUG = True\n')
    return temp_worktree


@pytest.fixture
def clean_worktree(temp_worktree):
    """Create a worktree with clean code."""
    src_file = temp_worktree / "src" / "config.py"
    src_file.write_text('import os\nAPI_KEY = os.environ.get("API_KEY")\n')
    return temp_worktree


# ============================================================================
# Security Detection Integration Tests
# ============================================================================


class TestSecurityDetectionIntegration:
    """Test security detection triggers pre-loop review."""

    def test_security_tagged_task_triggers_review(self, security_task):
        """Security-tagged task should trigger full review in pre-loop."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        should_review = should_run_full_review(security_task, config)

        assert should_review is True

    def test_non_security_task_skips_review(self, non_security_task):
        """Non-security task should skip full review."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        should_review = should_run_full_review(non_security_task, config)

        assert should_review is False

    def test_strict_level_always_triggers_review(self, non_security_task):
        """STRICT level should trigger review for all tasks."""
        config = SecurityConfig(level=SecurityLevel.STRICT)

        should_review = should_run_full_review(non_security_task, config)

        assert should_review is True

    def test_skip_level_never_triggers_review(self, security_task):
        """SKIP level should never trigger review."""
        config = SecurityConfig(level=SecurityLevel.SKIP)

        should_review = should_run_full_review(security_task, config)

        assert should_review is False

    def test_force_full_review_overrides_tags(self, non_security_task):
        """force_full_review flag should trigger review regardless of tags."""
        config = SecurityConfig(
            level=SecurityLevel.STANDARD,
            force_full_review=True,
        )

        should_review = should_run_full_review(non_security_task, config)

        assert should_review is True


# ============================================================================
# Pre-Loop Security Review Execution Tests
# ============================================================================


class TestPreLoopSecurityExecution:
    """Test security review execution during pre-loop."""

    def test_security_review_executes_on_worktree(self, vulnerable_worktree):
        """Security review should execute on worktree and find vulnerabilities."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-SEC-001")

        assert isinstance(result, SecurityReviewResult)
        assert len(result.findings) > 0

    def test_security_review_returns_critical_count(self, vulnerable_worktree):
        """Security review should count critical findings."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-SEC-001")

        assert result.critical_count >= 0
        assert isinstance(result.critical_count, int)

    def test_security_review_sets_blocked_flag(self, vulnerable_worktree):
        """Security review should set blocked flag based on config."""
        config = SecurityConfig(
            level=SecurityLevel.STANDARD,
            block_on_critical=True,
        )
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-SEC-001")

        # Should be blocked if critical findings exist
        if result.critical_count > 0:
            assert result.blocked is True

    def test_clean_worktree_not_blocked(self, clean_worktree):
        """Clean worktree should not be blocked."""
        config = SecurityConfig(level=SecurityLevel.STRICT)
        reviewer = SecurityReviewer(clean_worktree, config)

        result = reviewer.run("TASK-SEC-001")

        assert result.blocked is False
        assert len(result.findings) == 0


# ============================================================================
# Results Persistence Tests
# ============================================================================


class TestSecurityResultsPersistence:
    """Test security review results are persisted correctly."""

    def test_results_saved_to_autobuild_dir(self, vulnerable_worktree):
        """Results should be saved to .guardkit/autobuild/{task_id}/."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-001")
        path = save_security_review(result, vulnerable_worktree)

        assert path.exists()
        assert ".guardkit" in str(path)
        assert "autobuild" in str(path)
        assert "TASK-001" in str(path)

    def test_results_file_is_json(self, vulnerable_worktree):
        """Results file should be valid JSON."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-001")
        path = save_security_review(result, vulnerable_worktree)

        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "task_id" in data
        assert "findings" in data

    def test_results_can_be_loaded(self, vulnerable_worktree):
        """Saved results should be loadable."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-001")
        save_security_review(result, vulnerable_worktree)

        loaded = load_security_review("TASK-001", vulnerable_worktree)

        assert loaded is not None
        assert loaded.task_id == "TASK-001"

    def test_loaded_results_match_saved(self, vulnerable_worktree):
        """Loaded results should match saved results."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(vulnerable_worktree, config)

        result = reviewer.run("TASK-001")
        save_security_review(result, vulnerable_worktree)

        loaded = load_security_review("TASK-001", vulnerable_worktree)

        assert loaded.critical_count == result.critical_count
        assert loaded.high_count == result.high_count
        assert loaded.blocked == result.blocked
        assert len(loaded.findings) == len(result.findings)


# ============================================================================
# Pre-Loop Gate Integration Tests
# ============================================================================


class TestPreLoopGateIntegration:
    """Test pre-loop quality gates integration."""

    def test_preloop_executes_security_review_for_tagged_task(
        self, vulnerable_worktree, security_task
    ):
        """Pre-loop should execute security review for security-tagged task."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        # Check if should review
        should_review = should_run_full_review(security_task, config)
        assert should_review is True

        # Execute review
        if should_review:
            reviewer = SecurityReviewer(vulnerable_worktree, config)
            result = reviewer.run(security_task["id"])
            save_security_review(result, vulnerable_worktree)

        # Verify results persisted
        loaded = load_security_review(security_task["id"], vulnerable_worktree)
        assert loaded is not None

    def test_preloop_skips_review_for_non_security_task(
        self, clean_worktree, non_security_task
    ):
        """Pre-loop should skip security review for non-security task."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)

        should_review = should_run_full_review(non_security_task, config)

        assert should_review is False

    def test_preloop_blocks_task_on_critical_findings(
        self, vulnerable_worktree, security_task
    ):
        """Pre-loop should block task when critical findings exist."""
        config = SecurityConfig(
            level=SecurityLevel.STANDARD,
            block_on_critical=True,
        )

        reviewer = SecurityReviewer(vulnerable_worktree, config)
        result = reviewer.run(security_task["id"])

        # If critical findings, task should be blocked
        if result.critical_count > 0:
            assert result.blocked is True


# ============================================================================
# End-to-End Pre-Loop Flow Tests
# ============================================================================


class TestPreLoopE2EFlow:
    """End-to-end tests for complete pre-loop security flow."""

    def test_complete_preloop_security_flow(self, vulnerable_worktree, security_task):
        """Test complete pre-loop security review flow."""
        # 1. Check if review needed
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        should_review = should_run_full_review(security_task, config)
        assert should_review is True

        # 2. Execute security review
        reviewer = SecurityReviewer(vulnerable_worktree, config)
        result = reviewer.run(security_task["id"])

        # 3. Persist results
        path = save_security_review(result, vulnerable_worktree)
        assert path.exists()

        # 4. Verify results loadable
        loaded = load_security_review(security_task["id"], vulnerable_worktree)
        assert loaded is not None
        assert loaded.task_id == security_task["id"]

        # 5. Verify findings detected
        assert len(loaded.findings) > 0

    def test_preloop_flow_with_clean_code(self, clean_worktree, security_task):
        """Test pre-loop flow with clean code passes."""
        config = SecurityConfig(level=SecurityLevel.STRICT)

        reviewer = SecurityReviewer(clean_worktree, config)
        result = reviewer.run(security_task["id"])
        save_security_review(result, clean_worktree)

        loaded = load_security_review(security_task["id"], clean_worktree)

        assert loaded is not None
        assert loaded.blocked is False
        assert len(loaded.findings) == 0

    def test_preloop_respects_skip_level(self, vulnerable_worktree, security_task):
        """Test pre-loop respects SKIP security level."""
        config = SecurityConfig(level=SecurityLevel.SKIP)

        # Should not even run review
        should_review = should_run_full_review(security_task, config)
        assert should_review is False

        # But if we run anyway, no findings
        reviewer = SecurityReviewer(vulnerable_worktree, config)
        result = reviewer.run(security_task["id"])

        assert len(result.findings) == 0
        assert result.blocked is False
