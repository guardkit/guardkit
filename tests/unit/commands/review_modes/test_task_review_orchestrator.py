"""Unit tests for task review orchestrator."""

import pytest
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

import review_mode_executor


def test_execute_review_analysis_architectural():
    """Test orchestrator with architectural mode."""
    task_context = {
        "task_id": "TASK-001",
        "review_scope": ["src/"]
    }

    results = review_mode_executor.execute_review_analysis(
        task_context, "architectural", "standard"
    )

    assert results["mode"] == "architectural"
    assert results["depth"] == "standard"


def test_execute_review_analysis_code_quality():
    """Test orchestrator with code-quality mode."""
    task_context = {
        "task_id": "TASK-002",
        "review_scope": ["src/"]
    }

    results = review_mode_executor.execute_review_analysis(
        task_context, "code-quality", "quick"
    )

    assert results["mode"] == "code-quality"
    assert results["depth"] == "quick"


def test_execute_review_analysis_decision():
    """Test orchestrator with decision mode."""
    task_context = {
        "task_id": "TASK-003",
        "options": ["A", "B"]
    }

    results = review_mode_executor.execute_review_analysis(
        task_context, "decision", "standard"
    )

    assert results["mode"] == "decision"


def test_execute_review_analysis_technical_debt():
    """Test orchestrator with technical-debt mode."""
    task_context = {
        "task_id": "TASK-004",
        "review_scope": ["src/"]
    }

    results = review_mode_executor.execute_review_analysis(
        task_context, "technical-debt", "comprehensive"
    )

    assert results["mode"] == "technical-debt"


def test_execute_review_analysis_security():
    """Test orchestrator with security mode."""
    task_context = {
        "task_id": "TASK-005",
        "review_scope": ["src/"]
    }

    results = review_mode_executor.execute_review_analysis(
        task_context, "security", "standard"
    )

    assert results["mode"] == "security"


def test_execute_review_analysis_invalid_mode():
    """Test orchestrator with invalid mode."""
    task_context = {"task_id": "TASK-006"}

    with pytest.raises(ValueError, match="Invalid mode"):
        review_mode_executor.execute_review_analysis(
            task_context, "invalid-mode", "standard"
        )


def test_execute_review_analysis_invalid_depth():
    """Test orchestrator with invalid depth."""
    task_context = {"task_id": "TASK-007"}

    with pytest.raises(ValueError, match="Invalid depth"):
        review_mode_executor.execute_review_analysis(
            task_context, "architectural", "invalid-depth"
        )


def test_execute_review_analysis_missing_context():
    """Test orchestrator with missing context."""
    with pytest.raises(ValueError, match="task_context is required"):
        review_mode_executor.execute_review_analysis(
            None, "architectural", "standard"
        )


def test_get_supported_modes():
    """Test getting supported modes."""
    modes = review_mode_executor.get_supported_modes()

    assert len(modes) == 5
    assert "architectural" in modes
    assert "code-quality" in modes
    assert "decision" in modes
    assert "technical-debt" in modes
    assert "security" in modes


def test_get_mode_description():
    """Test getting mode descriptions."""
    desc = review_mode_executor.get_mode_description("architectural")

    assert "SOLID" in desc
    assert "0-100" in desc


def test_get_mode_description_invalid():
    """Test getting description for invalid mode."""
    with pytest.raises(ValueError, match="Unknown mode"):
        review_mode_executor.get_mode_description("invalid")


def test_get_mode_agents():
    """Test getting agents for each mode."""
    assert review_mode_executor.get_mode_agents("architectural") == ["architectural-reviewer"]
    assert review_mode_executor.get_mode_agents("code-quality") == ["code-reviewer"]
    assert review_mode_executor.get_mode_agents("decision") == ["software-architect"]
    assert review_mode_executor.get_mode_agents("technical-debt") == ["code-reviewer", "architectural-reviewer"]
    assert review_mode_executor.get_mode_agents("security") == ["security-specialist"]


def test_estimate_analysis_time():
    """Test analysis time estimation."""
    quick_time = review_mode_executor.estimate_analysis_time("architectural", "quick")
    assert quick_time["min_minutes"] == 15
    assert quick_time["max_minutes"] == 30

    standard_time = review_mode_executor.estimate_analysis_time("code-quality", "standard")
    assert standard_time["min_minutes"] == 60
    assert standard_time["max_minutes"] == 120

    # Technical debt should be double (uses 2 agents)
    debt_time = review_mode_executor.estimate_analysis_time("technical-debt", "standard")
    assert debt_time["min_minutes"] == 120
    assert debt_time["max_minutes"] == 240
