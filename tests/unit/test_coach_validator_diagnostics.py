"""
Unit tests for criteria matching diagnostic logging (TASK-ACR-003).

Verifies that CoachValidator logs diagnostic information at WARNING level
when criteria verification produces 0/N results.
"""

import logging
from pathlib import Path
from typing import Dict, Any

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


@pytest.fixture
def coach_validator(tmp_path: Path) -> CoachValidator:
    """Create a CoachValidator instance for testing."""
    return CoachValidator(worktree_path=str(tmp_path))


@pytest.fixture
def task_with_criteria() -> Dict[str, Any]:
    """Create a task with acceptance criteria."""
    return {
        "id": "TASK-TEST-001",
        "title": "Test Task",
        "acceptance_criteria": [
            "AC-001: OAuth2 authentication flow works correctly",
            "AC-002: Token refresh handles expiry edge case",
            "AC-003: Rate limiting prevents abuse",
        ],
    }


def test_diagnostic_logging_promises_strategy_all_incomplete(
    coach_validator: CoachValidator,
    task_with_criteria: Dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test diagnostic logging when using promises strategy with all criteria incomplete.

    Scenario: completion_promises present but all marked incomplete -> 0/3 result.
    Expected: WARNING-level diagnostic dump with AC text, promises, strategy, synthetic flag.
    """
    # Arrange
    task_work_results = {
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "OAuth2 authentication flow works correctly",
                "status": "incomplete",
                "evidence": "Not implemented yet",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Token refresh handles expiry edge case",
                "status": "incomplete",
                "evidence": "Not implemented yet",
            },
            {
                "criterion_id": "AC-003",
                "criterion_text": "Rate limiting prevents abuse",
                "status": "incomplete",
                "evidence": "Not implemented yet",
            },
        ],
        "_synthetic": False,
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task_with_criteria, task_work_results, turn=None
        )

    # Assert
    assert result.criteria_met == 0
    assert result.criteria_total == 3

    # Verify diagnostic logging
    log_text = caplog.text
    assert "Criteria verification 0/3 - diagnostic dump:" in log_text
    assert "AC text: AC-001: OAuth2 authentication flow works correctly" in log_text
    assert "AC text: AC-002: Token refresh handles expiry edge case" in log_text
    assert "AC text: AC-003: Rate limiting prevents abuse" in log_text
    assert "completion_promises:" in log_text
    assert "matching_strategy: promises" in log_text
    assert "_synthetic: False" in log_text
    assert "requirements_met: (not used)" in log_text


def test_diagnostic_logging_text_strategy_empty_requirements(
    coach_validator: CoachValidator,
    task_with_criteria: Dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test diagnostic logging when using text strategy with empty requirements_met.

    Scenario: No completion_promises, requirements_met empty -> 0/3 result.
    Expected: WARNING-level diagnostic dump showing text strategy was used.
    """
    # Arrange
    task_work_results = {
        "requirements_met": [],
        "_synthetic": False,
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task_with_criteria, task_work_results, turn=None
        )

    # Assert
    assert result.criteria_met == 0
    assert result.criteria_total == 3

    # Verify diagnostic logging
    log_text = caplog.text
    assert "Criteria verification 0/3 - diagnostic dump:" in log_text
    assert "AC text: AC-001: OAuth2 authentication flow works correctly" in log_text
    assert "requirements_met: []" in log_text
    assert "completion_promises: (not used)" in log_text
    assert "matching_strategy: text" in log_text
    assert "_synthetic: False" in log_text


def test_diagnostic_logging_synthetic_no_promises(
    coach_validator: CoachValidator,
    task_with_criteria: Dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test diagnostic logging for synthetic reports with no completion_promises.

    Scenario: Synthetic report with no promises -> 0/3 result.
    Expected: WARNING-level diagnostic dump showing synthetic path was used.
    """
    # Arrange
    task_work_results = {
        "_synthetic": True,
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task_with_criteria, task_work_results, turn=None
        )

    # Assert
    assert result.criteria_met == 0
    assert result.criteria_total == 3

    # Verify diagnostic logging
    log_text = caplog.text
    assert "Criteria verification 0/3 - diagnostic dump:" in log_text
    assert "AC text: AC-001: OAuth2 authentication flow works correctly" in log_text
    assert "completion_promises: (empty)" in log_text
    assert "requirements_met: (not used - synthetic path)" in log_text
    assert "matching_strategy: synthetic (no promises)" in log_text
    assert "_synthetic: True" in log_text


def test_no_diagnostic_logging_when_criteria_met(
    coach_validator: CoachValidator,
    task_with_criteria: Dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test that diagnostic logging does NOT occur when criteria are met.

    Scenario: completion_promises present with some/all criteria complete -> N/3 result (N>0).
    Expected: No diagnostic dump.
    """
    # Arrange
    task_work_results = {
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "OAuth2 authentication flow works correctly",
                "status": "complete",
                "evidence": "Implemented in oauth.py",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Token refresh handles expiry edge case",
                "status": "complete",
                "evidence": "Implemented in tokens.py",
            },
            {
                "criterion_id": "AC-003",
                "criterion_text": "Rate limiting prevents abuse",
                "status": "incomplete",
                "evidence": "Not implemented yet",
            },
        ],
        "_synthetic": False,
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task_with_criteria, task_work_results, turn=None
        )

    # Assert
    assert result.criteria_met == 2
    assert result.criteria_total == 3

    # Verify NO diagnostic logging (since criteria_met > 0)
    log_text = caplog.text
    assert "Criteria verification 0/" not in log_text


def test_diagnostic_logging_synthetic_with_incomplete_promises(
    coach_validator: CoachValidator,
    task_with_criteria: Dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Test diagnostic logging for synthetic reports with incomplete promises.

    Scenario: Synthetic report with completion_promises all incomplete -> 0/3 result.
    Expected: WARNING-level diagnostic dump showing synthetic promises path.
    """
    # Arrange
    task_work_results = {
        "_synthetic": True,
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "OAuth2 authentication flow works correctly",
                "status": "incomplete",
                "evidence": "Not implemented",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Token refresh handles expiry edge case",
                "status": "incomplete",
                "evidence": "Not implemented",
            },
            {
                "criterion_id": "AC-003",
                "criterion_text": "Rate limiting prevents abuse",
                "status": "incomplete",
                "evidence": "Not implemented",
            },
        ],
    }

    # Act
    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task_with_criteria, task_work_results, turn=None
        )

    # Assert
    assert result.criteria_met == 0
    assert result.criteria_total == 3

    # Verify diagnostic logging
    log_text = caplog.text
    assert "Criteria verification 0/3 - diagnostic dump:" in log_text
    assert "AC text: AC-001: OAuth2 authentication flow works correctly" in log_text
    assert "completion_promises:" in log_text
    assert "matching_strategy: promises (synthetic)" in log_text
    assert "_synthetic: True" in log_text
