"""Unit tests for architectural review mode."""

import pytest
import json
import sys
from pathlib import Path

# Add lib path to sys.path
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_modes import architectural_review


def test_architectural_review_quick():
    """Test quick architectural review (15-30 min)."""
    task_context = {
        "task_id": "TASK-001",
        "review_scope": ["src/auth/"]
    }
    results = architectural_review.execute(task_context, "quick")

    assert results["mode"] == "architectural"
    assert results["depth"] == "quick"
    assert 0 <= results["overall_score"] <= 100
    assert "solid" in results["principles"]
    assert "dry" in results["principles"]
    assert "yagni" in results["principles"]
    assert isinstance(results["findings"], list)
    assert isinstance(results["recommendations"], list)


def test_architectural_review_standard():
    """Test standard architectural review (1-2 hours)."""
    task_context = {
        "task_id": "TASK-002",
        "review_scope": ["src/"]
    }
    results = architectural_review.execute(task_context, "standard")

    assert results["mode"] == "architectural"
    assert results["depth"] == "standard"
    assert 0 <= results["overall_score"] <= 100
    assert all(k in results["principles"] for k in ["solid", "dry", "yagni"])


def test_architectural_review_comprehensive():
    """Test comprehensive architectural review (4-6 hours)."""
    task_context = {
        "task_id": "TASK-003",
        "review_scope": ["src/"]
    }
    results = architectural_review.execute(task_context, "comprehensive")

    assert results["depth"] == "comprehensive"
    assert isinstance(results["findings"], list)
    assert isinstance(results["recommendations"], list)


def test_build_architectural_prompt_quick():
    """Test prompt building for quick mode."""
    task_context = {"task_id": "TASK-001", "review_scope": ["src/"]}
    prompt = architectural_review.build_architectural_prompt(task_context, "quick")

    assert "quick" in prompt.lower()
    assert "20 minutes" in prompt.lower()
    assert "SOLID" in prompt
    assert "DRY" in prompt
    assert "YAGNI" in prompt


def test_build_architectural_prompt_comprehensive():
    """Test prompt building for comprehensive mode."""
    task_context = {"task_id": "TASK-001", "review_scope": ["src/"]}
    prompt = architectural_review.build_architectural_prompt(task_context, "comprehensive")

    assert "comprehensive" in prompt.lower()
    assert "5 hours" in prompt.lower()
    assert "design pattern" in prompt.lower()
    assert "scalability" in prompt.lower()


def test_get_timeout_for_depth():
    """Test timeout calculation."""
    assert architectural_review.get_timeout_for_depth("quick") == 1800
    assert architectural_review.get_timeout_for_depth("standard") == 7200
    assert architectural_review.get_timeout_for_depth("comprehensive") == 21600


def test_parse_architectural_response_valid_json():
    """Test parsing valid JSON response."""
    response = json.dumps({
        "overall_score": 85,
        "solid_score": 90,
        "dry_score": 80,
        "yagni_score": 85,
        "findings": [{"severity": "medium", "description": "Test finding"}],
        "recommendations": [{"priority": "high", "description": "Test recommendation"}],
        "evidence_files": ["file1.py"]
    })

    results = architectural_review.parse_architectural_response(response)

    assert results["overall_score"] == 85
    assert results["solid_score"] == 90
    assert results["dry_score"] == 80
    assert results["yagni_score"] == 85
    assert len(results["findings"]) == 1
    assert len(results["recommendations"]) == 1


def test_parse_architectural_response_markdown_json():
    """Test parsing JSON from markdown code block."""
    response = """```json
{
  "overall_score": 75,
  "solid_score": 80,
  "dry_score": 70,
  "yagni_score": 75,
  "findings": [],
  "recommendations": []
}
```"""

    results = architectural_review.parse_architectural_response(response)

    assert results["overall_score"] == 75
    assert results["solid_score"] == 80


def test_parse_architectural_response_invalid():
    """Test parsing invalid response with fallback."""
    response = "This is not valid JSON"

    results = architectural_review.parse_architectural_response(response)

    # Should return fallback values
    assert results["overall_score"] == 50
    assert results["solid_score"] == 50
    assert isinstance(results["findings"], list)
    assert len(results["findings"]) > 0  # Should have error finding


def test_parse_architectural_response_score_bounds():
    """Test that scores are bounded to 0-100."""
    response = json.dumps({
        "overall_score": 150,  # Above max
        "solid_score": -10,    # Below min
        "dry_score": 50,
        "yagni_score": 50,
        "findings": [],
        "recommendations": []
    })

    results = architectural_review.parse_architectural_response(response)

    assert results["overall_score"] == 100  # Capped at 100
    assert results["solid_score"] == 0      # Floored at 0
    assert results["dry_score"] == 50
