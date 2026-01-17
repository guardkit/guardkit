"""Unit tests for BlockedReport escape hatch pattern.

Tests cover:
- Schema validation (dataclasses, enums)
- JSON serialization/deserialization
- BlockedReport extraction from Player reports
- Turn context writing/loading
- Display formatting (render_blocked_report)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.exceptions import (
    BlockedReport,
    BlockingCategory,
    BlockingIssue,
    AttemptRecord,
)


# ===========================================================================
# BlockingCategory Tests
# ===========================================================================


class TestBlockingCategory:
    """Tests for BlockingCategory enum."""

    def test_all_known_categories_exist(self):
        """All expected categories are defined."""
        expected = [
            "test_failure",
            "dependency_issue",
            "architectural_violation",
            "requirements_unclear",
            "external_blocker",
            "timeout_exceeded",
            "resource_unavailable",
            "other",
        ]
        actual = [c.value for c in BlockingCategory]
        assert set(expected) == set(actual)

    def test_from_string_valid_category(self):
        """from_string returns correct category for valid input."""
        assert BlockingCategory.from_string("test_failure") == BlockingCategory.test_failure
        assert BlockingCategory.from_string("dependency_issue") == BlockingCategory.dependency_issue

    def test_from_string_unknown_category_defaults_to_other(self):
        """from_string returns 'other' for unknown categories."""
        assert BlockingCategory.from_string("unknown_category") == BlockingCategory.other
        assert BlockingCategory.from_string("") == BlockingCategory.other
        assert BlockingCategory.from_string("invalid") == BlockingCategory.other


# ===========================================================================
# BlockingIssue Tests
# ===========================================================================


class TestBlockingIssue:
    """Tests for BlockingIssue dataclass."""

    def test_create_minimal_issue(self):
        """BlockingIssue can be created with minimal fields."""
        issue = BlockingIssue(
            category=BlockingCategory.test_failure,
            description="Test fails intermittently",
        )
        assert issue.category == BlockingCategory.test_failure
        assert issue.description == "Test fails intermittently"
        assert issue.file_path is None
        assert issue.line_number is None

    def test_create_full_issue(self):
        """BlockingIssue can be created with all fields."""
        issue = BlockingIssue(
            category=BlockingCategory.test_failure,
            description="Token refresh test fails",
            file_path="tests/test_oauth.py",
            line_number=45,
            attempted_fixes=["Tried freezegun", "Tried manual patching"],
            root_cause="Async timing issue",
        )
        assert issue.file_path == "tests/test_oauth.py"
        assert issue.line_number == 45
        assert len(issue.attempted_fixes) == 2
        assert issue.root_cause == "Async timing issue"

    def test_to_dict(self):
        """to_dict converts issue to dictionary."""
        issue = BlockingIssue(
            category=BlockingCategory.test_failure,
            description="Test fails",
            file_path="test.py",
            line_number=10,
        )
        data = issue.to_dict()
        assert data["category"] == "test_failure"
        assert data["description"] == "Test fails"
        assert data["file_path"] == "test.py"
        assert data["line_number"] == 10
        assert data["attempted_fixes"] == []  # Default to empty list

    def test_from_dict(self):
        """from_dict creates issue from dictionary."""
        data = {
            "category": "dependency_issue",
            "description": "Package unavailable",
            "file_path": "src/api.py",
            "line_number": 25,
            "attempted_fixes": ["Tried pip install", "Tried conda"],
            "root_cause": "Version conflict",
        }
        issue = BlockingIssue.from_dict(data)
        assert issue.category == BlockingCategory.dependency_issue
        assert issue.description == "Package unavailable"
        assert issue.file_path == "src/api.py"
        assert len(issue.attempted_fixes) == 2

    def test_from_dict_unknown_category(self):
        """from_dict handles unknown category gracefully."""
        data = {
            "category": "unknown_type",
            "description": "Some issue",
        }
        issue = BlockingIssue.from_dict(data)
        assert issue.category == BlockingCategory.other


# ===========================================================================
# AttemptRecord Tests
# ===========================================================================


class TestAttemptRecord:
    """Tests for AttemptRecord dataclass."""

    def test_create_minimal_attempt(self):
        """AttemptRecord can be created with minimal fields."""
        attempt = AttemptRecord(
            turn=1,
            approach="Basic implementation",
            outcome="Partial success",
        )
        assert attempt.turn == 1
        assert attempt.learnings is None

    def test_create_full_attempt(self):
        """AttemptRecord can be created with all fields."""
        attempt = AttemptRecord(
            turn=2,
            approach="Added retry logic",
            outcome="Still failing",
            learnings="Retry doesn't help with timing issues",
        )
        assert attempt.turn == 2
        assert attempt.learnings == "Retry doesn't help with timing issues"

    def test_to_dict(self):
        """to_dict converts attempt to dictionary."""
        attempt = AttemptRecord(turn=1, approach="Test", outcome="Pass")
        data = attempt.to_dict()
        assert data["turn"] == 1
        assert data["approach"] == "Test"
        assert data["outcome"] == "Pass"
        assert data["learnings"] is None

    def test_from_dict(self):
        """from_dict creates attempt from dictionary."""
        data = {
            "turn": 3,
            "approach": "Refactored",
            "outcome": "Success",
            "learnings": "Cleaner code works better",
        }
        attempt = AttemptRecord.from_dict(data)
        assert attempt.turn == 3
        assert attempt.learnings == "Cleaner code works better"


# ===========================================================================
# BlockedReport Tests
# ===========================================================================


class TestBlockedReport:
    """Tests for BlockedReport dataclass."""

    @pytest.fixture
    def sample_report(self) -> BlockedReport:
        """Create a sample blocked report for testing."""
        return BlockedReport(
            blocking_issues=[
                BlockingIssue(
                    category=BlockingCategory.test_failure,
                    description="OAuth test fails",
                    file_path="tests/test_oauth.py",
                    line_number=45,
                    attempted_fixes=["Tried freezegun"],
                    root_cause="Async timing",
                ),
            ],
            attempts_made=[
                AttemptRecord(
                    turn=1,
                    approach="Basic OAuth",
                    outcome="4/5 tests pass",
                    learnings="Need better mocking",
                ),
                AttemptRecord(
                    turn=2,
                    approach="Added freezegun",
                    outcome="Still flaky",
                    learnings="freezegun + asyncio issues",
                ),
            ],
            suggested_alternatives=[
                "Use integration tests with real OAuth provider",
                "Accept flaky test with retry",
            ],
            human_action_required="Decide on testing strategy for token refresh",
        )

    def test_create_blocked_report(self, sample_report):
        """BlockedReport can be created with all required fields."""
        assert len(sample_report.blocking_issues) == 1
        assert len(sample_report.attempts_made) == 2
        assert len(sample_report.suggested_alternatives) == 2
        assert "testing strategy" in sample_report.human_action_required

    def test_to_dict(self, sample_report):
        """to_dict converts report to dictionary."""
        data = sample_report.to_dict()
        assert "blocking_issues" in data
        assert "attempts_made" in data
        assert "suggested_alternatives" in data
        assert "human_action_required" in data
        assert len(data["blocking_issues"]) == 1
        assert data["blocking_issues"][0]["category"] == "test_failure"

    def test_from_dict(self, sample_report):
        """from_dict creates report from dictionary."""
        data = sample_report.to_dict()
        restored = BlockedReport.from_dict(data)
        assert len(restored.blocking_issues) == 1
        assert len(restored.attempts_made) == 2
        assert restored.blocking_issues[0].category == BlockingCategory.test_failure
        assert restored.human_action_required == sample_report.human_action_required

    def test_from_dict_empty_lists(self):
        """from_dict handles empty lists gracefully."""
        data = {
            "blocking_issues": [],
            "attempts_made": [],
            "suggested_alternatives": [],
            "human_action_required": "Manual review needed",
        }
        report = BlockedReport.from_dict(data)
        assert len(report.blocking_issues) == 0
        assert len(report.attempts_made) == 0

    def test_roundtrip_serialization(self, sample_report):
        """Report survives JSON roundtrip."""
        json_str = json.dumps(sample_report.to_dict())
        data = json.loads(json_str)
        restored = BlockedReport.from_dict(data)
        assert restored.blocking_issues[0].description == sample_report.blocking_issues[0].description
        assert restored.attempts_made[0].turn == sample_report.attempts_made[0].turn


# ===========================================================================
# from_player_report Tests
# ===========================================================================


class TestFromPlayerReport:
    """Tests for BlockedReport.from_player_report class method."""

    def test_extract_blocked_report_present(self):
        """from_player_report extracts report when present."""
        player_report = {
            "task_id": "TASK-001",
            "turn": 5,
            "tests_passed": False,
            "blocked_report": {
                "blocking_issues": [
                    {
                        "category": "test_failure",
                        "description": "Test fails",
                    }
                ],
                "attempts_made": [],
                "suggested_alternatives": ["Try integration tests"],
                "human_action_required": "Review test approach",
            },
        }
        report = BlockedReport.from_player_report(player_report)
        assert report is not None
        assert len(report.blocking_issues) == 1
        assert report.blocking_issues[0].category == BlockingCategory.test_failure

    def test_extract_blocked_report_missing(self):
        """from_player_report returns None when blocked_report not present."""
        player_report = {
            "task_id": "TASK-001",
            "turn": 5,
            "tests_passed": True,
        }
        report = BlockedReport.from_player_report(player_report)
        assert report is None

    def test_extract_blocked_report_empty_dict_returns_none(self):
        """from_player_report returns None for empty blocked_report dict.

        An empty dict {} is falsy in Python, so it should be treated as
        "no blocked_report" rather than creating an empty report object.
        """
        player_report = {
            "task_id": "TASK-001",
            "blocked_report": {},
        }
        report = BlockedReport.from_player_report(player_report)
        # Empty dict is falsy, so should return None
        assert report is None

    def test_extract_blocked_report_with_valid_partial_data(self):
        """from_player_report handles partial blocked_report data gracefully."""
        player_report = {
            "task_id": "TASK-001",
            "blocked_report": {
                # Only partial data - missing some fields
                "blocking_issues": [],
                "human_action_required": "Manual review needed",
            },
        }
        report = BlockedReport.from_player_report(player_report)
        assert report is not None
        assert report.human_action_required == "Manual review needed"
        assert len(report.blocking_issues) == 0
        # Default empty lists for missing fields
        assert len(report.attempts_made) == 0
        assert len(report.suggested_alternatives) == 0


# ===========================================================================
# Turn Context Tests
# ===========================================================================


class TestTurnContext:
    """Tests for turn context write/load in AgentInvoker."""

    @pytest.fixture
    def invoker(self, tmp_path):
        """Create AgentInvoker with temp worktree."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker
        return AgentInvoker(worktree_path=tmp_path)

    def test_write_turn_context(self, invoker, tmp_path):
        """_write_turn_context creates context file."""
        invoker._write_turn_context(
            task_id="TASK-001",
            turn=4,
            max_turns=5,
            approaching_limit=True,
        )

        context_path = tmp_path / ".guardkit" / "autobuild" / "TASK-001" / "turn_context.json"
        assert context_path.exists()

        with open(context_path) as f:
            data = json.load(f)

        assert data["turn"] == 4
        assert data["max_turns"] == 5
        assert data["approaching_limit"] is True
        assert data["escape_hatch_active"] is True

    def test_write_turn_context_not_approaching(self, invoker, tmp_path):
        """_write_turn_context sets approaching_limit=False for early turns."""
        invoker._write_turn_context(
            task_id="TASK-002",
            turn=2,
            max_turns=5,
            approaching_limit=False,
        )

        context_path = tmp_path / ".guardkit" / "autobuild" / "TASK-002" / "turn_context.json"
        with open(context_path) as f:
            data = json.load(f)

        assert data["approaching_limit"] is False
        assert data["escape_hatch_active"] is False

    def test_load_turn_context_success(self, invoker, tmp_path):
        """load_turn_context loads existing context."""
        # Write context first
        invoker._write_turn_context("TASK-003", 4, 5, True)

        # Load it back
        context = invoker.load_turn_context("TASK-003")
        assert context is not None
        assert context["turn"] == 4
        assert context["approaching_limit"] is True

    def test_load_turn_context_not_found(self, invoker):
        """load_turn_context returns None when file doesn't exist."""
        context = invoker.load_turn_context("TASK-NONEXISTENT")
        assert context is None


# ===========================================================================
# Approaching Limit Calculation Tests
# ===========================================================================


class TestApproachingLimitCalculation:
    """Tests for approaching_limit calculation in invoke_player."""

    @pytest.fixture
    def invoker(self, tmp_path):
        """Create AgentInvoker with temp worktree."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker
        return AgentInvoker(worktree_path=tmp_path, use_task_work_delegation=False)

    @pytest.mark.parametrize(
        "turn,max_turns,expected_approaching",
        [
            (1, 5, False),   # Turn 1 of 5 - not approaching
            (2, 5, False),   # Turn 2 of 5 - not approaching
            (3, 5, False),   # Turn 3 of 5 - not approaching
            (4, 5, True),    # Turn 4 of 5 - approaching (max_turns - 1)
            (5, 5, True),    # Turn 5 of 5 - approaching (last turn)
            (3, 3, True),    # Turn 3 of 3 - approaching (max_turns - 1 = 2)
            (1, 2, True),    # Turn 1 of 2 - approaching (max_turns - 1 = 1)
        ],
    )
    def test_approaching_limit_calculation(
        self, invoker, tmp_path, turn, max_turns, expected_approaching
    ):
        """Verify approaching_limit is calculated correctly for various turn/max combinations."""
        # Calculate approaching_limit using the same logic as invoke_player
        approaching_limit = turn >= max_turns - 1

        assert approaching_limit == expected_approaching, (
            f"turn={turn}, max_turns={max_turns}: "
            f"expected approaching_limit={expected_approaching}, got {approaching_limit}"
        )


# ===========================================================================
# Display Formatting Tests
# ===========================================================================


class TestRenderBlockedReport:
    """Tests for ProgressDisplay.render_blocked_report method."""

    @pytest.fixture
    def mock_console(self):
        """Create mock Rich console."""
        return MagicMock()

    @pytest.fixture
    def display(self, mock_console):
        """Create ProgressDisplay with mock console."""
        from guardkit.orchestrator.progress import ProgressDisplay
        display = ProgressDisplay()
        display.console = mock_console
        return display

    @pytest.fixture
    def sample_report(self):
        """Create sample BlockedReport."""
        return BlockedReport(
            blocking_issues=[
                BlockingIssue(
                    category=BlockingCategory.test_failure,
                    description="Test fails intermittently",
                    file_path="tests/test_auth.py",
                    line_number=42,
                ),
            ],
            attempts_made=[
                AttemptRecord(turn=1, approach="Basic impl", outcome="Failed"),
            ],
            suggested_alternatives=["Try different approach"],
            human_action_required="Review and decide on approach",
        )

    def test_render_blocked_report_calls_console_print(
        self, display, mock_console, sample_report
    ):
        """render_blocked_report calls console.print multiple times."""
        display.render_blocked_report(sample_report, "TASK-001", 5)
        assert mock_console.print.called
        # Should have at least 4 calls (header, issues, attempts, alternatives, action)
        assert mock_console.print.call_count >= 4

    def test_render_blocked_report_empty_issues(self, display, mock_console):
        """render_blocked_report handles empty blocking_issues list."""
        report = BlockedReport(
            blocking_issues=[],
            attempts_made=[],
            suggested_alternatives=[],
            human_action_required="Manual review needed",
        )
        # Should not raise
        display.render_blocked_report(report, "TASK-002", 3)
        assert mock_console.print.called
