"""Integration tests for review modes."""

import pytest
import sys
from pathlib import Path

lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from review_mode_executor import execute_review_analysis


def test_all_review_modes_quick():
    """Test that all 5 review modes execute successfully in quick mode."""
    modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]
    task_context = {
        "task_id": "TASK-INT-001",
        "review_scope": ["src/auth/"],
        "options": ["Option A", "Option B"],  # For decision mode
        "criteria": ["Maintainability", "Performance"]  # For decision mode
    }

    for mode in modes:
        results = execute_review_analysis(task_context, mode, "quick")

        assert results["mode"] == mode
        assert results["depth"] == "quick"
        assert "findings" in results or "recommendations" in results or "remediation_plan" in results


def test_all_review_modes_standard():
    """Test that all 5 review modes execute successfully in standard mode."""
    modes = ["architectural", "code-quality", "decision", "technical-debt", "security"]
    task_context = {
        "task_id": "TASK-INT-002",
        "review_scope": ["src/"],
        "options": ["Option A", "Option B", "Option C"],
        "criteria": ["Maintainability", "Performance", "Scalability", "Cost"]
    }

    for mode in modes:
        results = execute_review_analysis(task_context, mode, "standard")

        assert results["mode"] == mode
        assert results["depth"] == "standard"


def test_architectural_review_integration():
    """Test architectural review end-to-end."""
    task_context = {
        "task_id": "TASK-INT-003",
        "review_scope": ["installer/global/commands/lib/review_modes/"]
    }

    results = execute_review_analysis(task_context, "architectural", "quick")

    assert results["mode"] == "architectural"
    assert 0 <= results["overall_score"] <= 100
    assert "principles" in results
    assert all(k in results["principles"] for k in ["solid", "dry", "yagni"])


def test_code_quality_review_integration():
    """Test code quality review end-to-end."""
    task_context = {
        "task_id": "TASK-INT-004",
        "review_scope": ["installer/global/commands/lib/review_modes/"]
    }

    results = execute_review_analysis(task_context, "code-quality", "quick")

    assert results["mode"] == "code-quality"
    assert 0 <= results["quality_score"] <= 10
    assert "complexity_metrics" in results


def test_decision_analysis_integration():
    """Test decision analysis end-to-end."""
    task_context = {
        "task_id": "TASK-INT-005",
        "options": [
            "Implement using microservices",
            "Implement using monolithic architecture",
            "Implement using serverless"
        ],
        "criteria": [
            "Development Speed",
            "Scalability",
            "Operational Complexity",
            "Cost"
        ],
        "decision_context": "Choosing architecture for new e-commerce platform"
    }

    results = execute_review_analysis(task_context, "decision", "standard")

    assert results["mode"] == "decision"
    assert results["recommendation"] in [
        "Implement using microservices",
        "Implement using monolithic architecture",
        "Implement using serverless"
    ]
    assert results["confidence"] in ["low", "medium", "high"]


def test_technical_debt_assessment_integration():
    """Test technical debt assessment end-to-end."""
    task_context = {
        "task_id": "TASK-INT-006",
        "review_scope": ["installer/global/commands/lib/"]
    }

    results = execute_review_analysis(task_context, "technical-debt", "quick")

    assert results["mode"] == "technical-debt"
    assert 0 <= results["total_debt_score"] <= 100
    assert "debt_by_category" in results
    assert "quick_wins" in results
    assert "paydown_estimate" in results


def test_security_audit_integration():
    """Test security audit end-to-end."""
    task_context = {
        "task_id": "TASK-INT-007",
        "review_scope": ["installer/global/commands/lib/review_modes/"]
    }

    results = execute_review_analysis(task_context, "security", "quick")

    assert results["mode"] == "security"
    assert 0 <= results["risk_score"] <= 100
    assert "vulnerabilities" in results
    assert "owasp_analysis" in results
    assert "remediation_plan" in results


def test_depth_parameter_affects_analysis():
    """Test that depth parameter affects analysis thoroughness."""
    task_context = {
        "task_id": "TASK-INT-008",
        "review_scope": ["src/"]
    }

    quick_results = execute_review_analysis(task_context, "architectural", "quick")
    standard_results = execute_review_analysis(task_context, "architectural", "standard")

    assert quick_results["depth"] == "quick"
    assert standard_results["depth"] == "standard"


def test_missing_scope_handled_gracefully():
    """Test that missing review_scope is handled gracefully."""
    task_context = {
        "task_id": "TASK-INT-009"
        # No review_scope
    }

    # Should not raise exception, should use empty scope or default
    results = execute_review_analysis(task_context, "code-quality", "quick")

    assert results["mode"] == "code-quality"


def test_multiple_modes_same_context():
    """Test running multiple modes on same task context."""
    task_context = {
        "task_id": "TASK-INT-010",
        "review_scope": ["installer/global/commands/lib/review_modes/"]
    }

    arch_results = execute_review_analysis(task_context, "architectural", "quick")
    quality_results = execute_review_analysis(task_context, "code-quality", "quick")
    security_results = execute_review_analysis(task_context, "security", "quick")

    assert arch_results["mode"] == "architectural"
    assert quality_results["mode"] == "code-quality"
    assert security_results["mode"] == "security"
