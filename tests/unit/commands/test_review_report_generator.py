"""
Unit tests for review_report_generator module.

Tests cover:
- Report generation in all formats (summary, detailed, presentation)
- Recommendation synthesis
- Decision checkpoint handling
- Report file operations
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"))

from review_report_generator import (
    generate_review_report,
    generate_summary_report,
    generate_detailed_report,
    generate_presentation_report,
    synthesize_recommendations,
    present_decision_checkpoint,
    handle_review_decision,
    save_review_report,
    _format_findings,
    _format_recommendations,
    _format_evidence,
    _prioritize_recommendations,
    _calculate_confidence_level
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_review_results():
    """Sample review results for testing."""
    return {
        "task_id": "TASK-001",
        "mode": "architectural",
        "overall_score": 75,
        "findings": [
            {
                "severity": "critical",
                "title": "Violation of Single Responsibility Principle",
                "description": "AuthService class handles both authentication and session management.",
                "location": "src/services/auth_service.py:45",
                "recommendation": "Split into AuthService and SessionService"
            },
            {
                "severity": "medium",
                "title": "Tight Coupling to Database Layer",
                "description": "Business logic directly depends on ORM models.",
                "location": "src/services/user_service.py:78",
                "recommendation": "Introduce repository pattern"
            },
            {
                "severity": "low",
                "title": "Missing Interface Abstractions",
                "description": "Concrete implementations used instead of interfaces.",
                "location": "src/services/notification_service.py:23",
                "recommendation": "Define INotificationService interface"
            }
        ],
        "evidence": [
            {
                "file": "src/services/auth_service.py",
                "line": "45",
                "description": "Large class with multiple responsibilities"
            }
        ],
        "architecture_assessment": {
            "solid_srp": 6,
            "solid_srp_notes": "Some violations in AuthService",
            "solid_ocp": 8,
            "solid_ocp_notes": "Good use of abstractions",
            "solid_lsp": 7,
            "solid_lsp_notes": "Minor substitution issues",
            "solid_isp": 9,
            "solid_isp_notes": "Well-segregated interfaces",
            "solid_dip": 7,
            "solid_dip_notes": "Some direct dependencies",
            "dry_score": 8,
            "dry_notes": "Minimal code duplication",
            "yagni_score": 9,
            "yagni_notes": "No over-engineering detected"
        }
    }


@pytest.fixture
def sample_recommendations():
    """Sample recommendations for testing."""
    return {
        "recommendations": [
            "Split AuthService into AuthService and SessionService",
            "Introduce repository pattern for data access",
            "Define INotificationService interface"
        ],
        "confidence": "High",
        "priority_order": [
            "Split AuthService into AuthService and SessionService",
            "Introduce repository pattern for data access",
            "Define INotificationService interface"
        ],
        "total_findings": 3,
        "critical_findings": 1,
        "mode": "architectural"
    }


# ============================================================================
# Report Generation Tests
# ============================================================================

def test_generate_summary_report(sample_review_results, sample_recommendations):
    """Test 1-page executive summary generation."""
    report = generate_summary_report(sample_review_results, sample_recommendations)

    # Check structure
    assert "# Review Summary - TASK-001" in report
    assert "Architectural" in report
    assert "75" in report  # overall score
    assert "Executive Summary" in report
    assert "Key Findings" in report
    assert "Top Recommendations" in report
    assert "Confidence Level" in report

    # Check length constraint (~50 lines)
    lines = report.split("\n")
    assert len(lines) <= 60, f"Summary report too long: {len(lines)} lines"

    # Check top 3 findings
    assert "CRITICAL" in report
    assert "Violation of Single Responsibility Principle" in report


def test_generate_detailed_report(sample_review_results, sample_recommendations):
    """Test full analysis report generation."""
    report = generate_detailed_report(
        sample_review_results,
        sample_recommendations,
        "architectural"
    )

    # Check structure
    assert "# Architectural Review Report - TASK-001" in report
    assert "Review Type" in report
    assert "Review Date" in report
    assert "Executive Summary" in report
    assert "Findings" in report
    assert "Recommendations" in report
    assert "Evidence" in report

    # Check architecture assessment
    assert "Architecture Assessment" in report or "architecture_assessment" in report

    # Check all findings included
    assert "Violation of Single Responsibility Principle" in report
    assert "Tight Coupling to Database Layer" in report
    assert "Missing Interface Abstractions" in report


def test_generate_detailed_report_fallback(sample_review_results, sample_recommendations):
    """Test detailed report generation with missing template (fallback)."""
    # Use non-existent mode to trigger fallback
    sample_review_results["mode"] = "unknown-mode"

    report = generate_detailed_report(
        sample_review_results,
        sample_recommendations,
        "unknown-mode"
    )

    # Should still generate report
    assert "# Unknown Mode Review Report - TASK-001" in report
    assert "Executive Summary" in report
    assert "Findings" in report


def test_generate_presentation_report(sample_review_results, sample_recommendations):
    """Test presentation-style report generation."""
    report = generate_presentation_report(sample_review_results, sample_recommendations)

    # Check slide structure
    assert "---" in report  # Slide separators
    assert "# Review Report" in report
    assert "# Executive Summary" in report
    assert "# Key Findings" in report
    assert "# Recommendations" in report
    assert "# Next Steps" in report

    # Check content
    assert "TASK-001" in report
    assert "75" in report  # overall score


def test_generate_review_report_router(sample_review_results, sample_recommendations):
    """Test main report generation router."""
    # Test summary format
    summary = generate_review_report(
        sample_review_results,
        sample_recommendations,
        "summary"
    )
    assert "Review Summary" in summary

    # Test detailed format
    detailed = generate_review_report(
        sample_review_results,
        sample_recommendations,
        "detailed"
    )
    assert "Review Report" in detailed

    # Test presentation format
    presentation = generate_review_report(
        sample_review_results,
        sample_recommendations,
        "presentation"
    )
    assert "---" in presentation


# ============================================================================
# Recommendation Synthesis Tests
# ============================================================================

def test_synthesize_recommendations_basic(sample_review_results):
    """Test basic recommendation synthesis."""
    recommendations = synthesize_recommendations(sample_review_results)

    assert "recommendations" in recommendations
    assert "confidence" in recommendations
    assert "priority_order" in recommendations
    assert "total_findings" in recommendations
    assert "critical_findings" in recommendations

    # Check counts
    assert recommendations["total_findings"] == 3
    assert recommendations["critical_findings"] == 1

    # Check recommendations extracted from findings
    assert len(recommendations["recommendations"]) == 3


def test_synthesize_recommendations_with_agents(sample_review_results):
    """Test recommendation synthesis with multiple agent findings."""
    agent_findings = [
        {
            "recommendations": [
                "Add integration tests for authentication flow",
                "Document API endpoints"
            ]
        },
        {
            "recommendations": [
                "Implement rate limiting",
                "Add input validation"
            ]
        }
    ]

    recommendations = synthesize_recommendations(sample_review_results, agent_findings)

    # Should merge all recommendations
    all_recs = recommendations["recommendations"]
    assert len(all_recs) >= 5  # 3 from findings + 4 from agents


def test_synthesize_recommendations_deduplication(sample_review_results):
    """Test that duplicate recommendations are removed."""
    # Add duplicate recommendation in findings
    sample_review_results["findings"].append({
        "severity": "low",
        "title": "Duplicate Finding",
        "recommendation": "Split AuthService into AuthService and SessionService"  # Duplicate
    })

    recommendations = synthesize_recommendations(sample_review_results)

    # Should have unique recommendations
    all_recs = recommendations["recommendations"]
    assert len(all_recs) == len(set(all_recs)), "Duplicate recommendations found"


def test_prioritize_recommendations():
    """Test recommendation prioritization by severity."""
    recommendations = [
        "Low priority recommendation",
        "High priority recommendation",
        "Medium priority recommendation"
    ]

    findings = [
        {"severity": "low", "recommendation": "Low priority recommendation"},
        {"severity": "critical", "recommendation": "High priority recommendation"},
        {"severity": "medium", "recommendation": "Medium priority recommendation"}
    ]

    prioritized = _prioritize_recommendations(recommendations, findings)

    # Critical should be first
    assert prioritized[0] == "High priority recommendation"


def test_calculate_confidence_level_high():
    """Test high confidence level calculation."""
    review_results = {"overall_score": 85}
    findings = [
        {"severity": "low", "title": "Minor issue"}
    ]

    confidence = _calculate_confidence_level(review_results, findings)
    assert confidence == "High"


def test_calculate_confidence_level_low():
    """Test low confidence level calculation."""
    review_results = {"overall_score": 35}
    findings = [
        {"severity": "critical", "title": "Issue 1"},
        {"severity": "critical", "title": "Issue 2"},
        {"severity": "critical", "title": "Issue 3"},
        {"severity": "high", "title": "Issue 4"}
    ]

    confidence = _calculate_confidence_level(review_results, findings)
    assert confidence == "Low"


def test_calculate_confidence_level_medium():
    """Test medium confidence level calculation."""
    review_results = {"overall_score": 65}
    findings = [
        {"severity": "medium", "title": "Issue 1"},
        {"severity": "low", "title": "Issue 2"}
    ]

    confidence = _calculate_confidence_level(review_results, findings)
    assert confidence == "Medium"


# ============================================================================
# Decision Checkpoint Tests
# ============================================================================

@patch('builtins.input', return_value='a')
def test_present_decision_checkpoint_accept(mock_input, sample_recommendations, capsys):
    """Test accept decision flow."""
    report = "# Review Report\n\nSample report content..."

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    assert decision == "accept"

    # Check output
    captured = capsys.readouterr()
    assert "REVIEW COMPLETE" in captured.out
    assert "TASK-001" in captured.out
    assert "KEY RECOMMENDATIONS" in captured.out
    assert "[A]ccept" in captured.out


@patch('builtins.input', return_value='r')
def test_present_decision_checkpoint_revise(mock_input, sample_recommendations):
    """Test revise decision flow."""
    report = "# Review Report"

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    assert decision == "revise"


@patch('builtins.input', return_value='i')
def test_present_decision_checkpoint_implement(mock_input, sample_recommendations):
    """Test implement decision flow."""
    report = "# Review Report"

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    assert decision == "implement"


@patch('builtins.input', return_value='c')
def test_present_decision_checkpoint_cancel(mock_input, sample_recommendations):
    """Test cancel decision flow."""
    report = "# Review Report"

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    assert decision == "cancel"


@patch('builtins.input', side_effect=['invalid', 'x', 'a'])
def test_present_decision_checkpoint_invalid_input(mock_input, sample_recommendations, capsys):
    """Test handling of invalid input."""
    report = "# Review Report"

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    # Should eventually get valid input
    assert decision == "accept"

    # Check error messages
    captured = capsys.readouterr()
    assert "Invalid choice" in captured.out


@patch('builtins.input', side_effect=KeyboardInterrupt())
def test_present_decision_checkpoint_keyboard_interrupt(mock_input, sample_recommendations):
    """Test handling of keyboard interrupt."""
    report = "# Review Report"

    decision = present_decision_checkpoint(report, sample_recommendations, "TASK-001")

    # Should return cancel on interrupt
    assert decision == "cancel"


# ============================================================================
# Decision Handling Tests
# ============================================================================

def test_handle_review_decision_accept(tmp_path, capsys):
    """Test accept decision handling."""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    tasks_dir = workspace / "tasks"
    in_progress_dir = tasks_dir / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file
    task_file = in_progress_dir / "TASK-001-test.md"
    task_file.write_text("# Task")

    recommendations = {"recommendations": ["Test"]}

    # Execute
    new_state, impl_task = handle_review_decision(
        "TASK-001",
        "accept",
        recommendations,
        workspace
    )

    # Verify
    assert new_state == "in_review"
    assert impl_task is None

    # Check file moved
    in_review_dir = tasks_dir / "in_review"
    assert (in_review_dir / "TASK-001-test.md").exists()
    assert not task_file.exists()

    # Check output
    captured = capsys.readouterr()
    assert "Review accepted" in captured.out
    assert "IN_REVIEW" in captured.out


def test_handle_review_decision_revise(tmp_path, capsys):
    """Test revise decision handling."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    recommendations = {"recommendations": ["Test"]}

    new_state, impl_task = handle_review_decision(
        "TASK-001",
        "revise",
        recommendations,
        workspace
    )

    assert new_state == "in_progress"
    assert impl_task is None

    captured = capsys.readouterr()
    assert "revision requested" in captured.out


def test_handle_review_decision_implement(tmp_path, capsys):
    """Test implement decision handling."""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    tasks_dir = workspace / "tasks"
    in_progress_dir = tasks_dir / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file
    task_file = in_progress_dir / "TASK-001-test.md"
    task_file.write_text("# Task")

    recommendations = {
        "recommendations": [
            "Refactor authentication",
            "Add input validation"
        ]
    }

    # Execute
    new_state, impl_task = handle_review_decision(
        "TASK-001",
        "implement",
        recommendations,
        workspace
    )

    # Verify
    assert new_state == "in_review"
    assert impl_task is not None
    assert impl_task.startswith("TASK-IMPL-")

    # Check implementation task created
    backlog_dir = tasks_dir / "backlog"
    impl_files = list(backlog_dir.glob(f"{impl_task}*.md"))
    assert len(impl_files) == 1

    # Check implementation task content
    impl_content = impl_files[0].read_text()
    assert "TASK-001" in impl_content
    assert "Refactor authentication" in impl_content
    assert "Add input validation" in impl_content

    # Check output
    captured = capsys.readouterr()
    assert "Review accepted" in captured.out
    assert "Created implementation task" in captured.out


def test_handle_review_decision_cancel(tmp_path, capsys):
    """Test cancel decision handling."""
    # Setup
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    tasks_dir = workspace / "tasks"
    in_progress_dir = tasks_dir / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file
    task_file = in_progress_dir / "TASK-001-test.md"
    task_file.write_text("# Task")

    recommendations = {"recommendations": ["Test"]}

    # Execute
    new_state, impl_task = handle_review_decision(
        "TASK-001",
        "cancel",
        recommendations,
        workspace
    )

    # Verify
    assert new_state == "backlog"
    assert impl_task is None

    # Check file moved
    backlog_dir = tasks_dir / "backlog"
    assert (backlog_dir / "TASK-001-test.md").exists()
    assert not task_file.exists()

    # Check output
    captured = capsys.readouterr()
    assert "cancelled" in captured.out


# ============================================================================
# Helper Function Tests
# ============================================================================

def test_format_findings():
    """Test findings formatting."""
    findings = [
        {
            "severity": "critical",
            "title": "Security Issue",
            "description": "SQL injection vulnerability",
            "location": "src/db.py:45",
            "recommendation": "Use parameterized queries"
        }
    ]

    formatted = _format_findings(findings)

    assert "CRITICAL" in formatted
    assert "Security Issue" in formatted
    assert "SQL injection vulnerability" in formatted
    assert "src/db.py:45" in formatted
    assert "Use parameterized queries" in formatted


def test_format_findings_empty():
    """Test empty findings formatting."""
    formatted = _format_findings([])
    assert "No findings" in formatted


def test_format_recommendations():
    """Test recommendations formatting."""
    recommendations = {
        "recommendations": [
            "Refactor authentication",
            "Add input validation",
            "Implement logging"
        ]
    }

    formatted = _format_recommendations(recommendations)

    assert "1. Refactor authentication" in formatted
    assert "2. Add input validation" in formatted
    assert "3. Implement logging" in formatted


def test_format_recommendations_empty():
    """Test empty recommendations formatting."""
    formatted = _format_recommendations({"recommendations": []})
    assert "No specific recommendations" in formatted


def test_format_evidence():
    """Test evidence formatting."""
    evidence = [
        {
            "file": "src/services/auth.py",
            "line": "45",
            "description": "Large method"
        },
        {
            "file": "src/models/user.py",
            "description": "Missing validation"
        }
    ]

    formatted = _format_evidence(evidence)

    assert "src/services/auth.py:45" in formatted
    assert "Large method" in formatted
    assert "src/models/user.py" in formatted
    assert "Missing validation" in formatted


def test_format_evidence_empty():
    """Test empty evidence formatting."""
    formatted = _format_evidence([])
    assert "No evidence" in formatted


# ============================================================================
# File Operations Tests
# ============================================================================

def test_save_review_report(tmp_path):
    """Test saving review report to file."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    report = "# Review Report\n\nTest content"

    report_path = save_review_report("TASK-001", report, workspace)

    # Check file created
    assert report_path.exists()
    assert report_path.name == "review-report.md"

    # Check directory structure
    assert report_path.parent.name == "TASK-001"
    assert report_path.parent.parent.name == "state"

    # Check content
    assert report_path.read_text() == report


def test_save_review_report_creates_directories(tmp_path):
    """Test that save_review_report creates necessary directories."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    report = "# Review Report"

    report_path = save_review_report("TASK-001", report, workspace)

    # Should create full path
    assert report_path.exists()
    assert report_path.parent.exists()
    assert report_path.parent.parent.exists()
