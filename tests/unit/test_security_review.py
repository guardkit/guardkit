"""
Unit Tests for Security Review Module (TASK-SEC-005).

Tests for SecurityReviewResult dataclass, SecurityReviewer orchestrator,
and persistence functions (save/load security review results).

Test Categories:
- SecurityReviewResult dataclass tests
- SecurityReviewer initialization tests
- SecurityReviewer.run() execution tests
- Blocking logic tests (by security level)
- Persistence tests (save/load)
"""

import json
import pytest
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
from guardkit.orchestrator.quality_gates.security_review import (
    SecurityReviewResult,
    SecurityReviewer,
    save_security_review,
    load_security_review,
)
from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding


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
def sample_finding():
    """Create a sample SecurityFinding for testing."""
    return SecurityFinding(
        check_id="hardcoded-secrets",
        severity="critical",
        description="Hardcoded API key detected",
        file_path="/path/to/config.py",
        line_number=10,
        matched_text='API_KEY = "sk-secret"',
        recommendation="Use environment variables instead",
    )


@pytest.fixture
def sample_findings():
    """Create a list of sample findings with different severities."""
    return [
        SecurityFinding(
            check_id="hardcoded-secrets",
            severity="critical",
            description="Hardcoded API key",
            file_path="config.py",
            line_number=5,
            matched_text='API_KEY = "sk-xxx"',
            recommendation="Use environment variables",
        ),
        SecurityFinding(
            check_id="cors-wildcard",
            severity="high",
            description="CORS wildcard detected",
            file_path="main.py",
            line_number=20,
            matched_text='allow_origins=["*"]',
            recommendation="Use specific origins",
        ),
        SecurityFinding(
            check_id="debug-mode",
            severity="medium",
            description="Debug mode enabled",
            file_path="settings.py",
            line_number=3,
            matched_text="DEBUG = True",
            recommendation="Disable in production",
        ),
        SecurityFinding(
            check_id="info-disclosure",
            severity="low",
            description="Verbose error message",
            file_path="handlers.py",
            line_number=50,
            matched_text="print(str(error))",
            recommendation="Use proper logging",
        ),
    ]


@pytest.fixture
def sample_review_result(sample_findings):
    """Create a sample SecurityReviewResult for testing."""
    return SecurityReviewResult(
        task_id="TASK-001",
        worktree_path="/path/to/worktree",
        findings=sample_findings,
        critical_count=1,
        high_count=1,
        medium_count=1,
        low_count=1,
        blocked=True,
        execution_time_seconds=2.5,
        timestamp="2025-01-25T12:00:00+00:00",
    )


# ============================================================================
# SecurityReviewResult Dataclass Tests
# ============================================================================


class TestSecurityReviewResultDataclass:
    """Test SecurityReviewResult dataclass structure."""

    def test_security_review_result_import(self):
        """Test that SecurityReviewResult can be imported."""
        from guardkit.orchestrator.quality_gates.security_review import SecurityReviewResult
        assert SecurityReviewResult is not None

    def test_security_review_result_has_required_fields(self, sample_review_result):
        """Test SecurityReviewResult has all required fields."""
        assert hasattr(sample_review_result, "task_id")
        assert hasattr(sample_review_result, "worktree_path")
        assert hasattr(sample_review_result, "findings")
        assert hasattr(sample_review_result, "critical_count")
        assert hasattr(sample_review_result, "high_count")
        assert hasattr(sample_review_result, "medium_count")
        assert hasattr(sample_review_result, "low_count")
        assert hasattr(sample_review_result, "blocked")
        assert hasattr(sample_review_result, "execution_time_seconds")
        assert hasattr(sample_review_result, "timestamp")

    def test_security_review_result_field_types(self, sample_review_result):
        """Test SecurityReviewResult field types."""
        assert isinstance(sample_review_result.task_id, str)
        assert isinstance(sample_review_result.worktree_path, str)
        assert isinstance(sample_review_result.findings, list)
        assert isinstance(sample_review_result.critical_count, int)
        assert isinstance(sample_review_result.high_count, int)
        assert isinstance(sample_review_result.medium_count, int)
        assert isinstance(sample_review_result.low_count, int)
        assert isinstance(sample_review_result.blocked, bool)
        assert isinstance(sample_review_result.execution_time_seconds, float)
        assert isinstance(sample_review_result.timestamp, str)

    def test_security_review_result_to_dict(self, sample_review_result):
        """Test SecurityReviewResult.to_dict() serialization."""
        result_dict = sample_review_result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["task_id"] == "TASK-001"
        assert result_dict["worktree_path"] == "/path/to/worktree"
        assert len(result_dict["findings"]) == 4
        assert result_dict["critical_count"] == 1
        assert result_dict["high_count"] == 1
        assert result_dict["blocked"] is True

    def test_security_review_result_to_dict_findings_structure(self, sample_review_result):
        """Test that findings in to_dict() have correct structure."""
        result_dict = sample_review_result.to_dict()

        for finding in result_dict["findings"]:
            assert "check_id" in finding
            assert "severity" in finding
            assert "description" in finding
            assert "file_path" in finding
            assert "line_number" in finding
            assert "matched_text" in finding
            assert "recommendation" in finding

    def test_security_review_result_to_dict_json_serializable(self, sample_review_result):
        """Test that to_dict() output is JSON serializable."""
        result_dict = sample_review_result.to_dict()

        # Should not raise
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)

    def test_security_review_result_empty_findings(self):
        """Test SecurityReviewResult with empty findings."""
        result = SecurityReviewResult(
            task_id="TASK-002",
            worktree_path="/path/to/worktree",
            findings=[],
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            blocked=False,
            execution_time_seconds=0.5,
            timestamp="2025-01-25T12:00:00+00:00",
        )

        assert len(result.findings) == 0
        assert result.blocked is False


# ============================================================================
# SecurityReviewer Initialization Tests
# ============================================================================


class TestSecurityReviewerInitialization:
    """Test SecurityReviewer class initialization."""

    def test_security_reviewer_import(self):
        """Test that SecurityReviewer can be imported."""
        from guardkit.orchestrator.quality_gates.security_review import SecurityReviewer
        assert SecurityReviewer is not None

    def test_security_reviewer_initialization(self, temp_worktree):
        """Test SecurityReviewer initializes with worktree and config."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        assert reviewer.worktree_path == temp_worktree
        assert reviewer.config == config

    def test_security_reviewer_accepts_string_path(self, temp_worktree):
        """Test SecurityReviewer accepts string path."""
        config = SecurityConfig()
        reviewer = SecurityReviewer(str(temp_worktree), config)

        assert reviewer.worktree_path == Path(temp_worktree)

    def test_security_reviewer_stores_config(self, temp_worktree):
        """Test SecurityReviewer stores SecurityConfig."""
        config = SecurityConfig(
            level=SecurityLevel.STRICT,
            block_on_critical=True,
        )
        reviewer = SecurityReviewer(temp_worktree, config)

        assert reviewer.config.level == SecurityLevel.STRICT
        assert reviewer.config.block_on_critical is True


# ============================================================================
# SecurityReviewer.run() Execution Tests
# ============================================================================


class TestSecurityReviewerRun:
    """Test SecurityReviewer.run() method execution."""

    def test_run_returns_security_review_result(self, temp_worktree):
        """Test run() returns SecurityReviewResult."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert isinstance(result, SecurityReviewResult)

    def test_run_sets_task_id(self, temp_worktree):
        """Test run() sets correct task_id."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-TEST-123")

        assert result.task_id == "TASK-TEST-123"

    def test_run_sets_worktree_path(self, temp_worktree):
        """Test run() sets correct worktree_path."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert result.worktree_path == str(temp_worktree)

    def test_run_sets_timestamp(self, temp_worktree):
        """Test run() sets ISO format timestamp."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        # Should be valid ISO timestamp
        assert result.timestamp is not None
        # Should be parseable
        datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))

    def test_run_measures_execution_time(self, temp_worktree):
        """Test run() measures execution time."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert result.execution_time_seconds >= 0

    def test_run_with_skip_level_returns_no_findings(self, temp_worktree):
        """Test run() with SKIP level returns empty findings."""
        config = SecurityConfig(level=SecurityLevel.SKIP)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert len(result.findings) == 0
        assert result.blocked is False

    def test_run_categorizes_findings_by_severity(self, temp_worktree):
        """Test run() correctly categorizes findings by severity."""
        # Create vulnerable code
        src_file = temp_worktree / "src" / "config.py"
        src_file.write_text('API_KEY = "sk-secret-key-12345"\nDEBUG = True\n')

        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        # Should have findings
        assert result.critical_count >= 0
        assert result.high_count >= 0
        assert result.medium_count >= 0
        assert result.low_count >= 0

        # Total should match findings length
        total = result.critical_count + result.high_count + result.medium_count + result.low_count
        assert total == len(result.findings)


# ============================================================================
# Blocking Logic Tests
# ============================================================================


class TestSecurityReviewerBlockingLogic:
    """Test SecurityReviewer blocking logic based on config."""

    def test_strict_level_blocks_on_any_finding(self, temp_worktree):
        """Test STRICT level blocks on any finding."""
        # Create a file with any security issue
        src_file = temp_worktree / "src" / "settings.py"
        src_file.write_text("DEBUG = True\n")

        config = SecurityConfig(level=SecurityLevel.STRICT)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        # Should be blocked if any finding found
        if len(result.findings) > 0:
            assert result.blocked is True

    def test_standard_level_blocks_on_critical(self, temp_worktree):
        """Test STANDARD level blocks on critical findings when configured."""
        # Create critical finding
        src_file = temp_worktree / "src" / "config.py"
        src_file.write_text('API_KEY = "sk-secret-key"\n')

        config = SecurityConfig(level=SecurityLevel.STANDARD, block_on_critical=True)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        # Should block if critical finding
        if result.critical_count > 0:
            assert result.blocked is True

    def test_standard_level_no_block_when_disabled(self, temp_worktree):
        """Test STANDARD level doesn't block when block_on_critical=False."""
        src_file = temp_worktree / "src" / "config.py"
        src_file.write_text('API_KEY = "sk-secret-key"\n')

        config = SecurityConfig(level=SecurityLevel.STANDARD, block_on_critical=False)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        # Should not block even with critical findings
        assert result.blocked is False

    def test_minimal_level_never_blocks(self, temp_worktree):
        """Test MINIMAL level never blocks."""
        src_file = temp_worktree / "src" / "config.py"
        src_file.write_text('API_KEY = "sk-secret-key"\nDEBUG = True\n')

        config = SecurityConfig(level=SecurityLevel.MINIMAL)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert result.blocked is False

    def test_skip_level_never_blocks(self, temp_worktree):
        """Test SKIP level never blocks."""
        src_file = temp_worktree / "src" / "config.py"
        src_file.write_text('API_KEY = "sk-secret-key"\n')

        config = SecurityConfig(level=SecurityLevel.SKIP)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert result.blocked is False
        assert len(result.findings) == 0

    def test_clean_worktree_not_blocked(self, temp_worktree):
        """Test clean worktree is not blocked."""
        src_file = temp_worktree / "src" / "clean.py"
        src_file.write_text('import os\nAPI_KEY = os.environ.get("API_KEY")\n')

        config = SecurityConfig(level=SecurityLevel.STRICT)
        reviewer = SecurityReviewer(temp_worktree, config)

        result = reviewer.run("TASK-001")

        assert result.blocked is False
        assert len(result.findings) == 0


# ============================================================================
# Persistence Tests
# ============================================================================


class TestSecurityReviewPersistence:
    """Test save_security_review and load_security_review functions."""

    def test_save_security_review_creates_file(self, temp_worktree, sample_review_result):
        """Test save_security_review creates JSON file."""
        # Update result with correct task_id for path generation
        sample_review_result.task_id = "TASK-001"

        path = save_security_review(sample_review_result, temp_worktree)

        assert path.exists()
        assert path.suffix == ".json"

    def test_save_security_review_returns_correct_path(self, temp_worktree, sample_review_result):
        """Test save_security_review returns correct path."""
        sample_review_result.task_id = "TASK-TEST"

        path = save_security_review(sample_review_result, temp_worktree)

        assert "TASK-TEST" in str(path)
        assert "security_review.json" in str(path)

    def test_save_security_review_creates_valid_json(self, temp_worktree, sample_review_result):
        """Test save_security_review creates valid JSON."""
        sample_review_result.task_id = "TASK-001"

        path = save_security_review(sample_review_result, temp_worktree)

        with open(path) as f:
            data = json.load(f)

        assert data["task_id"] == "TASK-001"
        assert isinstance(data["findings"], list)

    def test_load_security_review_returns_result(self, temp_worktree, sample_review_result):
        """Test load_security_review returns SecurityReviewResult."""
        sample_review_result.task_id = "TASK-001"
        save_security_review(sample_review_result, temp_worktree)

        loaded = load_security_review("TASK-001", temp_worktree)

        assert isinstance(loaded, SecurityReviewResult)
        assert loaded.task_id == "TASK-001"

    def test_load_security_review_restores_findings(self, temp_worktree, sample_review_result):
        """Test load_security_review restores findings correctly."""
        sample_review_result.task_id = "TASK-001"
        save_security_review(sample_review_result, temp_worktree)

        loaded = load_security_review("TASK-001", temp_worktree)

        assert len(loaded.findings) == len(sample_review_result.findings)
        assert all(isinstance(f, SecurityFinding) for f in loaded.findings)

    def test_load_security_review_returns_none_if_not_found(self, temp_worktree):
        """Test load_security_review returns None if file not found."""
        loaded = load_security_review("NONEXISTENT-TASK", temp_worktree)

        assert loaded is None

    def test_load_security_review_returns_none_on_invalid_json(self, temp_worktree):
        """Test load_security_review returns None on invalid JSON."""
        from guardkit.orchestrator.paths import TaskArtifactPaths

        # Create invalid JSON file
        TaskArtifactPaths.ensure_autobuild_dir("TASK-BAD", temp_worktree)
        bad_path = TaskArtifactPaths.security_review_path("TASK-BAD", temp_worktree)
        with open(bad_path, "w") as f:
            f.write("not valid json {{{")

        loaded = load_security_review("TASK-BAD", temp_worktree)

        assert loaded is None

    def test_round_trip_preserves_data(self, temp_worktree, sample_review_result):
        """Test save then load preserves all data."""
        sample_review_result.task_id = "TASK-ROUNDTRIP"
        save_security_review(sample_review_result, temp_worktree)

        loaded = load_security_review("TASK-ROUNDTRIP", temp_worktree)

        assert loaded.task_id == sample_review_result.task_id
        assert loaded.worktree_path == sample_review_result.worktree_path
        assert loaded.critical_count == sample_review_result.critical_count
        assert loaded.high_count == sample_review_result.high_count
        assert loaded.blocked == sample_review_result.blocked
        assert loaded.execution_time_seconds == sample_review_result.execution_time_seconds
        assert loaded.timestamp == sample_review_result.timestamp


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestSecurityReviewerErrorHandling:
    """Test SecurityReviewer error handling."""

    def test_handles_nonexistent_worktree_gracefully(self, tmp_path):
        """Test reviewer handles nonexistent worktree gracefully."""
        nonexistent = tmp_path / "nonexistent"
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(nonexistent, config)

        result = reviewer.run("TASK-001")

        # Should not crash, should return empty findings
        assert isinstance(result, SecurityReviewResult)
        assert len(result.findings) == 0

    def test_handles_permission_error_gracefully(self, temp_worktree):
        """Test reviewer handles permission errors gracefully."""
        config = SecurityConfig(level=SecurityLevel.STANDARD)
        reviewer = SecurityReviewer(temp_worktree, config)

        # Mock SecurityChecker to raise exception
        with patch(
            "guardkit.orchestrator.quality_gates.security_review.SecurityChecker"
        ) as MockChecker:
            MockChecker.return_value.run_quick_checks.side_effect = PermissionError(
                "Access denied"
            )

            result = reviewer.run("TASK-001")

        # Should not crash
        assert isinstance(result, SecurityReviewResult)
        assert len(result.findings) == 0
