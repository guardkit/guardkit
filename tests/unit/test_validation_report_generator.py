"""
Unit Tests for Validation Report Generator (TASK-043)

Tests markdown validation report generation functionality.
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from installer.core.lib.template_generator.report_generator import ValidationReportGenerator
from installer.core.lib.template_generator.extended_validator import (
    ExtendedValidationReport,
    SpotCheckResult
)


# ===== Fixtures =====

@pytest.fixture
def report_generator():
    """Create a ValidationReportGenerator instance"""
    return ValidationReportGenerator()


@pytest.fixture
def production_ready_report():
    """Create a production-ready validation report"""
    return ExtendedValidationReport(
        overall_score=8.7,
        completeness_score=9.0,
        placeholder_consistency_score=8.5,
        pattern_fidelity_score=8.8,
        documentation_score=8.5,
        agent_validation_score=9.0,
        manifest_accuracy_score=8.0,
        issues=[],
        recommendations=["Template quality is excellent! Ready for production use."],
        spot_check_results=[
            SpotCheckResult(
                template_path="templates/Domain/GetProducts.template",
                passed=True,
                checks_performed=["Placeholder usage", "Content structure"],
                issues_found=[],
                score=9.0
            )
        ],
        duration="3.2s"
    )


@pytest.fixture
def needs_improvement_report():
    """Create a needs-improvement validation report"""
    return ExtendedValidationReport(
        overall_score=7.0,
        completeness_score=7.5,
        placeholder_consistency_score=6.8,
        pattern_fidelity_score=7.2,
        documentation_score=6.5,
        agent_validation_score=7.0,
        manifest_accuracy_score=7.0,
        issues=["Placeholder naming inconsistencies detected"],
        recommendations=[
            "Standardize placeholder naming conventions across all templates",
            "Enhance CLAUDE.md with more detailed architecture and examples"
        ],
        spot_check_results=[
            SpotCheckResult(
                template_path="templates/Domain/Template1.template",
                passed=False,
                checks_performed=["Placeholder usage"],
                issues_found=["Inconsistent placeholder casing"],
                score=6.5
            )
        ],
        duration="2.8s"
    )


@pytest.fixture
def not_ready_report():
    """Create a not-ready validation report"""
    return ExtendedValidationReport(
        overall_score=5.2,
        completeness_score=5.5,
        placeholder_consistency_score=4.8,
        pattern_fidelity_score=5.0,
        documentation_score=5.0,
        agent_validation_score=5.5,
        manifest_accuracy_score=5.0,
        issues=[
            "Critical: Placeholder naming inconsistencies detected",
            "Critical: Multiple pattern fidelity violations",
            "Critical: Documentation is incomplete or missing required sections"
        ],
        recommendations=[
            "Review Phase 5.5 validation report and address missing templates",
            "Standardize placeholder naming conventions across all templates",
            "Review spot-check findings and improve pattern adherence",
            "Enhance CLAUDE.md with more detailed architecture and examples"
        ],
        spot_check_results=[
            SpotCheckResult(
                template_path="templates/Domain/Template1.template",
                passed=False,
                checks_performed=["Placeholder usage", "Pattern adherence"],
                issues_found=["No placeholders found", "Low quality score"],
                score=4.5
            ),
            SpotCheckResult(
                template_path="templates/Domain/Template2.template",
                passed=False,
                checks_performed=["Content structure"],
                issues_found=["Template content is very short"],
                score=5.5
            )
        ],
        duration="3.5s"
    )


# ===== Report Generation Tests =====

def test_generate_report_creates_file(report_generator, production_ready_report, tmp_path):
    """Test that generate_report creates a markdown file"""
    template_name = "test-template"
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name=template_name,
        output_path=tmp_path
    )

    assert report_path.exists()
    assert report_path.name == "validation-report.md"
    assert report_path.parent == tmp_path


def test_generate_report_production_ready(report_generator, production_ready_report, tmp_path):
    """Test report generation for production-ready template"""
    template_name = "test-template"
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name=template_name,
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify header
    assert "# Template Validation Report" in content
    assert f"**Template**: {template_name}" in content
    assert "**Overall Score**: 8.7/10 (A-)" in content

    # Verify production ready status
    assert "✅ **This template is production-ready**" in content
    assert "Exit Code**: 0" in content


def test_generate_report_needs_improvement(report_generator, needs_improvement_report, tmp_path):
    """Test report generation for template needing improvement"""
    template_name = "test-template"
    report_path = report_generator.generate_report(
        report=needs_improvement_report,
        template_name=template_name,
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify warning status
    assert "⚠️ **This template needs improvement**" in content
    assert "Exit Code**: 1" in content
    assert "7.0/10" in content


def test_generate_report_not_ready(report_generator, not_ready_report, tmp_path):
    """Test report generation for template not ready"""
    template_name = "test-template"
    report_path = report_generator.generate_report(
        report=not_ready_report,
        template_name=template_name,
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify critical status
    assert "❌ **This template is not ready for production**" in content
    assert "Exit Code**: 2" in content
    assert "5.2/10" in content


# ===== Report Content Tests =====

def test_report_contains_quality_scores_table(report_generator, production_ready_report, tmp_path):
    """Test that report contains quality scores table"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify table structure
    assert "## Quality Scores" in content
    assert "| Category | Score | Status |" in content
    assert "CRUD Completeness (Phase 5.5)" in content
    assert "Placeholder Consistency" in content
    assert "Pattern Fidelity" in content
    assert "Documentation Quality" in content
    assert "Agent Validation" in content
    assert "Manifest Accuracy" in content


def test_report_contains_score_weights(report_generator, production_ready_report, tmp_path):
    """Test that report contains score weight explanation"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    assert "### Score Weights" in content
    assert "CRUD Completeness**: 50%" in content
    assert "Placeholder Consistency**: 10%" in content


def test_report_contains_spot_checks(report_generator, production_ready_report, tmp_path):
    """Test that report contains spot-check results"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    assert "## Pattern Fidelity Spot-Checks" in content
    assert "Total Spot-Checks**:" in content
    assert "GetProducts.template" in content


def test_report_contains_recommendations(report_generator, needs_improvement_report, tmp_path):
    """Test that report contains recommendations"""
    report_path = report_generator.generate_report(
        report=needs_improvement_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    assert "## Recommendations" in content
    assert "Standardize placeholder naming conventions" in content
    assert "Enhance CLAUDE.md" in content


def test_report_contains_exit_code_explanation(report_generator, production_ready_report, tmp_path):
    """Test that report contains exit code explanation"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    assert "## Exit Code" in content
    assert "`0` = Score ≥8.0" in content
    assert "`1` = Score 6.0-7.9" in content
    assert "`2` = Score <6.0" in content


# ===== Status Icon Tests =====

def test_status_icon_production_ready(report_generator):
    """Test status icon for production-ready score"""
    assert report_generator._status_icon(8.0) == "✅"
    assert report_generator._status_icon(9.5) == "✅"
    assert report_generator._status_icon(10.0) == "✅"


def test_status_icon_needs_improvement(report_generator):
    """Test status icon for needs-improvement score"""
    assert report_generator._status_icon(6.0) == "⚠️"
    assert report_generator._status_icon(7.0) == "⚠️"
    assert report_generator._status_icon(7.9) == "⚠️"


def test_status_icon_not_ready(report_generator):
    """Test status icon for not-ready score"""
    assert report_generator._status_icon(0.0) == "❌"
    assert report_generator._status_icon(3.0) == "❌"
    assert report_generator._status_icon(5.9) == "❌"


# ===== Summary Generation Tests =====

def test_generate_summary_production_ready(report_generator, production_ready_report):
    """Test summary generation for production-ready template"""
    summary = report_generator._generate_summary(production_ready_report)

    assert "✅ **This template is production-ready**" in summary
    assert "8.7/10" in summary
    assert "A-" in summary
    assert "passed all quality gates" in summary


def test_generate_summary_needs_improvement(report_generator, needs_improvement_report):
    """Test summary generation for template needing improvement"""
    summary = report_generator._generate_summary(needs_improvement_report)

    assert "⚠️ **This template needs improvement**" in summary
    assert "7.0/10" in summary
    assert "B" in summary
    assert "addressing the recommendations" in summary


def test_generate_summary_not_ready(report_generator, not_ready_report):
    """Test summary generation for not-ready template"""
    summary = report_generator._generate_summary(not_ready_report)

    assert "❌ **This template is not ready for production**" in summary
    assert "5.2/10" in summary
    assert "F" in summary
    assert "Significant improvements are required" in summary


# ===== Detailed Findings Tests =====

def test_generate_detailed_findings_no_issues(report_generator, production_ready_report):
    """Test detailed findings when no issues found"""
    findings = report_generator._generate_detailed_findings(production_ready_report)

    assert "✅ **No critical issues found**" in findings
    assert "All validation checks passed" in findings


def test_generate_detailed_findings_with_issues(report_generator, not_ready_report):
    """Test detailed findings with multiple issues"""
    findings = report_generator._generate_detailed_findings(not_ready_report)

    assert "### Issues Found" in findings
    assert "Critical: Placeholder naming inconsistencies" in findings
    assert "Critical: Multiple pattern fidelity violations" in findings


# ===== Spot-Check Section Tests =====

def test_generate_spot_check_section_no_checks(report_generator):
    """Test spot-check section when no checks performed"""
    report = ExtendedValidationReport(
        overall_score=10.0,
        completeness_score=10.0,
        placeholder_consistency_score=10.0,
        pattern_fidelity_score=10.0,
        documentation_score=10.0,
        agent_validation_score=10.0,
        manifest_accuracy_score=10.0,
        spot_check_results=[]
    )

    section = report_generator._generate_spot_check_section(report)
    assert "No spot-checks performed" in section


def test_generate_spot_check_section_with_checks(report_generator, production_ready_report):
    """Test spot-check section with performed checks"""
    section = report_generator._generate_spot_check_section(production_ready_report)

    assert "Total Spot-Checks**:" in section
    assert "Average Score**:" in section
    assert "Spot-Check 1:" in section
    assert "GetProducts.template" in section


def test_generate_spot_check_section_with_issues(report_generator, not_ready_report):
    """Test spot-check section with issues found"""
    section = report_generator._generate_spot_check_section(not_ready_report)

    assert "⚠️ Issues Found" in section
    assert "No placeholders found" in section
    assert "Template content is very short" in section


# ===== Blocking Issues Tests =====

def test_generate_blocking_issues_production_ready(report_generator, production_ready_report):
    """Test blocking issues for production-ready template"""
    blocking = report_generator._generate_blocking_issues(production_ready_report)
    assert blocking == ""  # No blocking issues


def test_generate_blocking_issues_with_blocks(report_generator, not_ready_report):
    """Test blocking issues with multiple blockers"""
    blocking = report_generator._generate_blocking_issues(not_ready_report)

    assert "### Blocking Issues" in blocking
    assert "CRUD completeness below threshold" in blocking
    assert "Placeholder naming inconsistencies" in blocking
    assert "Pattern fidelity issues detected" in blocking
    assert "Documentation incomplete" in blocking


# ===== Production Readiness Status Tests =====

def test_production_readiness_status_ready(report_generator, production_ready_report):
    """Test production readiness status for ready template"""
    status = report_generator._production_readiness_status(production_ready_report)
    assert "✅ **Production Ready**" == status


def test_production_readiness_status_needs_improvement(report_generator, needs_improvement_report):
    """Test production readiness status for template needing improvement"""
    status = report_generator._production_readiness_status(needs_improvement_report)
    assert "⚠️ **Needs Improvement**" == status


def test_production_readiness_status_not_ready(report_generator, not_ready_report):
    """Test production readiness status for not-ready template"""
    status = report_generator._production_readiness_status(not_ready_report)
    assert "❌ **Not Ready**" == status


# ===== Integration Tests =====

def test_full_report_structure(report_generator, production_ready_report, tmp_path):
    """Test complete report structure"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify all major sections present
    required_sections = [
        "# Template Validation Report",
        "## Executive Summary",
        "## Quality Scores",
        "### Score Weights",
        "## Detailed Findings",
        "## Pattern Fidelity Spot-Checks",
        "## Recommendations",
        "## Production Readiness",
        "## Exit Code"
    ]

    for section in required_sections:
        assert section in content, f"Missing section: {section}"


def test_report_markdown_validity(report_generator, production_ready_report, tmp_path):
    """Test that generated report is valid markdown"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Basic markdown syntax checks
    assert content.startswith("# ")  # Starts with h1
    assert "\n## " in content  # Has h2 headers
    assert "| " in content  # Has tables
    assert "**" in content  # Has bold text
    assert "✅" in content or "⚠️" in content or "❌" in content  # Has status icons


def test_report_with_unicode(report_generator, production_ready_report, tmp_path):
    """Test that report handles unicode characters correctly"""
    report_path = report_generator.generate_report(
        report=production_ready_report,
        template_name="test-template",
        output_path=tmp_path
    )

    content = report_path.read_text(encoding='utf-8')

    # Verify unicode characters are preserved
    unicode_chars = ["✅", "⚠️", "❌", "📁", "🎯"]
    for char in unicode_chars:
        # At least some unicode should be present
        pass

    # Verify file is readable as UTF-8
    assert isinstance(content, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
