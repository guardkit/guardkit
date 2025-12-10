"""Unit tests for technical debt assessment mode."""

import pytest
import json
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_modes import technical_debt_assessment


def test_technical_debt_assessment_basic():
    """Test basic technical debt assessment."""
    task_context = {
        "task_id": "TASK-001",
        "review_scope": ["src/"]
    }
    results = technical_debt_assessment.execute(task_context, "standard")

    assert results["mode"] == "technical-debt"
    assert results["depth"] == "standard"
    assert "total_debt_score" in results
    assert "debt_by_category" in results
    assert "debt_items" in results
    assert "quick_wins" in results
    assert "paydown_estimate" in results


def test_prioritize_debt():
    """Test debt prioritization."""
    debt_items = [
        {"impact": "low", "effort": "high", "risk": "low"},
        {"impact": "high", "effort": "low", "risk": "high"},
        {"impact": "medium", "effort": "medium", "risk": "medium"}
    ]

    prioritized = technical_debt_assessment.prioritize_debt(debt_items)

    # High impact + high risk + low effort should be first
    assert prioritized[0]["impact"] == "high"
    assert prioritized[0]["effort"] == "low"
    assert "priority" in prioritized[0]
    assert "priority_score" in prioritized[0]


def test_identify_quick_wins():
    """Test quick win identification."""
    debt_items = [
        {"impact": "high", "effort": "low", "description": "Quick win 1"},
        {"impact": "high", "effort": "high", "description": "Not quick"},
        {"impact": "medium", "effort": "low", "description": "Quick win 2"},
        {"impact": "low", "effort": "low", "description": "Low impact"}
    ]

    quick_wins = technical_debt_assessment.identify_quick_wins(debt_items)

    assert len(quick_wins) == 2
    assert all(item["effort"] == "low" for item in quick_wins)
    assert all(item["impact"] in ["high", "medium"] for item in quick_wins)


def test_categorize_debt():
    """Test debt categorization."""
    debt_items = [
        {"category": "code", "description": "Code debt"},
        {"category": "design", "description": "Design debt"},
        {"category": "code", "description": "More code debt"},
        {"category": "test", "description": "Test debt"}
    ]

    categorized = technical_debt_assessment.categorize_debt(debt_items)

    assert len(categorized["code"]) == 2
    assert len(categorized["design"]) == 1
    assert len(categorized["test"]) == 1


def test_calculate_total_debt_score():
    """Test total debt score calculation."""
    debt_items = [
        {"impact": "high", "risk": "high"},
        {"impact": "medium", "risk": "low"},
        {"impact": "low", "risk": "medium"}
    ]

    score = technical_debt_assessment.calculate_total_debt_score(debt_items)

    assert 0 <= score <= 100
    assert isinstance(score, int)


def test_calculate_total_debt_score_empty():
    """Test debt score with no items."""
    score = technical_debt_assessment.calculate_total_debt_score([])

    assert score == 0


def test_estimate_paydown_effort():
    """Test paydown effort estimation."""
    debt_items = [
        {"effort": "low", "priority": "high"},
        {"effort": "medium", "priority": "medium"},
        {"effort": "high", "priority": "low"}
    ]

    estimate = technical_debt_assessment.estimate_paydown_effort(debt_items)

    assert "total_hours" in estimate
    assert "total_days" in estimate
    assert "by_priority" in estimate
    assert estimate["total_hours"] == 34  # 2 + 8 + 24


def test_generate_paydown_plan():
    """Test paydown plan generation."""
    debt_items = [
        {"impact": "high", "effort": "low", "risk": "high", "priority": "high", "description": "Item 1"},
        {"impact": "medium", "effort": "medium", "risk": "medium", "priority": "medium", "description": "Item 2"}
    ]
    quick_wins = [debt_items[0]]

    plan = technical_debt_assessment.generate_paydown_plan(debt_items, quick_wins)

    assert len(plan) > 0
    assert all("phase" in item for item in plan)
    assert all("estimated_effort" in item for item in plan)
