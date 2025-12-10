"""Unit tests for code quality review mode."""

import pytest
import json
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_modes import code_quality_review


def test_code_quality_review_quick():
    """Test quick code quality review."""
    task_context = {
        "task_id": "TASK-001",
        "review_scope": ["src/auth/"]
    }
    results = code_quality_review.execute(task_context, "quick")

    assert results["mode"] == "code-quality"
    assert results["depth"] == "quick"
    assert 0 <= results["quality_score"] <= 10
    assert "complexity_metrics" in results
    assert isinstance(results["code_smells"], list)
    assert isinstance(results["style_issues"], list)


def test_code_quality_review_standard():
    """Test standard code quality review."""
    task_context = {
        "task_id": "TASK-002",
        "review_scope": ["src/"]
    }
    results = code_quality_review.execute(task_context, "standard")

    assert results["mode"] == "code-quality"
    assert results["depth"] == "standard"
    assert 0 <= results["quality_score"] <= 10


def test_code_quality_review_comprehensive():
    """Test comprehensive code quality review."""
    task_context = {
        "task_id": "TASK-003",
        "review_scope": ["src/"]
    }
    results = code_quality_review.execute(task_context, "comprehensive")

    assert results["depth"] == "comprehensive"
    assert "complexity_metrics" in results
    assert "findings" in results


def test_parse_quality_response_valid():
    """Test parsing valid quality response."""
    response = json.dumps({
        "quality_score": 7.5,
        "complexity_metrics": {
            "avg_cyclomatic": 5,
            "max_cyclomatic": 15
        },
        "code_smells": [],
        "style_issues": [],
        "test_coverage": {"line_coverage": 85, "branch_coverage": 75},
        "findings": [],
        "recommendations": []
    })

    results = code_quality_review.parse_quality_response(response)

    assert results["quality_score"] == 7.5
    assert results["complexity_metrics"]["avg_cyclomatic"] == 5
    assert results["test_coverage"]["line_coverage"] == 85


def test_parse_quality_response_score_bounds():
    """Test that quality score is bounded to 0-10."""
    response = json.dumps({
        "quality_score": 15,  # Above max
        "complexity_metrics": {},
        "code_smells": [],
        "style_issues": [],
        "test_coverage": None,
        "findings": [],
        "recommendations": []
    })

    results = code_quality_review.parse_quality_response(response)

    assert results["quality_score"] == 10  # Capped at 10


def test_calculate_complexity_score():
    """Test complexity score calculation."""
    metrics = {
        "max_cyclomatic": 10,
        "max_nesting_depth": 2
    }

    score = code_quality_review.calculate_complexity_score(metrics)

    assert isinstance(score, float)
    assert 1 <= score <= 10


def test_calculate_complexity_score_empty():
    """Test complexity score with empty metrics."""
    score = code_quality_review.calculate_complexity_score({})

    assert score == 5.0  # Default middle score
