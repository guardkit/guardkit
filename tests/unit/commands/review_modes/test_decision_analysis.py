"""Unit tests for decision analysis mode."""

import pytest
import json
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_modes import decision_analysis


def test_decision_analysis_basic():
    """Test basic decision analysis."""
    task_context = {
        "task_id": "TASK-001",
        "options": ["Option A", "Option B"],
        "criteria": ["Maintainability", "Performance"]
    }
    results = decision_analysis.execute(task_context, "standard")

    assert results["mode"] == "decision"
    assert results["depth"] == "standard"
    assert "options" in results
    assert "recommendation" in results
    assert results["confidence"] in ["low", "medium", "high"]


def test_decision_analysis_default_options():
    """Test decision analysis with default options."""
    task_context = {
        "task_id": "TASK-002"
    }
    results = decision_analysis.execute(task_context, "quick")

    # Should use default 4 options
    assert len(results["options"]) >= 0


def test_parse_decision_response_valid():
    """Test parsing valid decision response."""
    expected_options = ["Option A", "Option B"]
    response = json.dumps({
        "options": [
            {
                "name": "Option A",
                "scores": {"Maintainability": 8, "Performance": 7},
                "total_score": 15,
                "pros": ["Easy to maintain"],
                "cons": ["Slower performance"]
            },
            {
                "name": "Option B",
                "scores": {"Maintainability": 6, "Performance": 9},
                "total_score": 15,
                "pros": ["Fast"],
                "cons": ["Complex"]
            }
        ],
        "recommendation": "Option A",
        "confidence": "high",
        "criteria": ["Maintainability", "Performance"],
        "justification": "Better long-term maintainability"
    })

    results = decision_analysis.parse_decision_response(response, expected_options)

    assert len(results["options"]) == 2
    assert results["recommendation"] == "Option A"
    assert results["confidence"] == "high"


def test_parse_decision_response_invalid_confidence():
    """Test that invalid confidence is normalized."""
    response = json.dumps({
        "options": [],
        "recommendation": "A",
        "confidence": "very_high",  # Invalid
        "criteria": [],
        "justification": ""
    })

    results = decision_analysis.parse_decision_response(response, ["A"])

    assert results["confidence"] == "medium"  # Default fallback


def test_validate_option_scores():
    """Test option score validation."""
    options = [
        {
            "name": "Option A",
            "scores": {"Maintainability": 8},  # Missing Performance
            "total_score": 0
        }
    ]
    criteria = ["Maintainability", "Performance"]

    validated = decision_analysis.validate_option_scores(options, criteria)

    assert validated[0]["scores"]["Maintainability"] == 8
    assert validated[0]["scores"]["Performance"] == 5  # Default
    assert validated[0]["total_score"] == 13  # Recalculated
