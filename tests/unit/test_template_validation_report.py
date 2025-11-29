"""
Unit Tests for Template Validation Report Generator

Tests for report generation and formatting.
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))


# Use importlib to avoid 'global' keyword issue
_audit_report_generator_module = importlib.import_module('global.lib.template_validation.audit_report_generator')
AuditReportGenerator = _audit_report_generator_module.AuditReportGenerator
_audit_session_module = importlib.import_module('global.lib.template_validation.audit_session')
AuditSession = _audit_session_module.AuditSession
_models_module = importlib.import_module('global.lib.template_validation.models')
SectionResult = _models_module.SectionResult
AuditRecommendation = _models_module.AuditRecommendation
IssueSeverity = _models_module.IssueSeverity
IssueCategory = _models_module.IssueCategory
ValidationIssue = _models_module.ValidationIssue
Finding = _models_module.Finding
Recommendation = _models_module.Recommendation


class TestReportGeneratorInitialization:
    """Test report generator initialization"""

    def test_create_report_generator(self):
        """Create a report generator"""
        generator = AuditReportGenerator()
        assert generator is not None


class TestGradeCalculation:
    """Test grade calculation"""

    def test_grade_a_plus(self):
        """Score 9.5+ gets A+"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(9.5) == "A+"
        assert generator._calculate_grade(10.0) == "A+"

    def test_grade_a(self):
        """Score 9.0-9.49 gets A"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(9.0) == "A"
        assert generator._calculate_grade(9.3) == "A"

    def test_grade_a_minus(self):
        """Score 8.5-8.99 gets A-"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(8.5) == "A-"
        assert generator._calculate_grade(8.7) == "A-"

    def test_grade_b_plus(self):
        """Score 8.0-8.49 gets B+"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(8.0) == "B+"
        assert generator._calculate_grade(8.3) == "B+"

    def test_grade_b(self):
        """Score 7.0-7.99 gets B"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(7.0) == "B"
        assert generator._calculate_grade(7.5) == "B"

    def test_grade_c(self):
        """Score 6.0-6.99 gets C"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(6.0) == "C"
        assert generator._calculate_grade(6.8) == "C"

    def test_grade_d(self):
        """Score 5.0-5.99 gets D"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(5.0) == "D"
        assert generator._calculate_grade(5.5) == "D"

    def test_grade_f(self):
        """Score below 5.0 gets F"""
        generator = AuditReportGenerator()
        assert generator._calculate_grade(4.9) == "F"
        assert generator._calculate_grade(0.0) == "F"


class TestRecommendationGeneration:
    """Test recommendation generation"""

    def test_recommendation_approve(self):
        """Score 8.0+ recommends approval"""
        generator = AuditReportGenerator()
        rec = generator._generate_recommendation(8.0)
        assert rec == AuditRecommendation.APPROVE

    def test_recommendation_needs_improvement(self):
        """Score 6.0-7.99 recommends improvements"""
        generator = AuditReportGenerator()
        rec = generator._generate_recommendation(6.0)
        assert rec == AuditRecommendation.NEEDS_IMPROVEMENT
        rec = generator._generate_recommendation(7.5)
        assert rec == AuditRecommendation.NEEDS_IMPROVEMENT

    def test_recommendation_reject(self):
        """Score below 6.0 recommends rejection"""
        generator = AuditReportGenerator()
        rec = generator._generate_recommendation(5.9)
        assert rec == AuditRecommendation.REJECT


class TestOverallScoreCalculation:
    """Test overall score calculation"""

    def test_calculate_overall_score_empty(self):
        """Empty session has zero score"""
        session = AuditSession.create(Path("/templates/test"))
        generator = AuditReportGenerator()
        score = generator._calculate_overall_score(session)
        assert score == 0.0

    def test_calculate_overall_score_single(self):
        """Single section score"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=7.5)
        session.add_result(1, result)

        generator = AuditReportGenerator()
        score = generator._calculate_overall_score(session)
        assert score == 7.5

    def test_calculate_overall_score_multiple(self):
        """Multiple sections are averaged"""
        session = AuditSession.create(Path("/templates/test"))
        for i in range(1, 4):
            result = SectionResult(section_num=i, section_title=f"Section {i}", score=8.0)
            session.add_result(i, result)

        generator = AuditReportGenerator()
        score = generator._calculate_overall_score(session)
        assert score == 8.0

    def test_calculate_overall_score_ignores_none(self):
        """Optional sections with None score are ignored"""
        session = AuditSession.create(Path("/templates/test"))
        result1 = SectionResult(section_num=1, section_title="Section 1", score=8.0)
        result2 = SectionResult(section_num=2, section_title="Section 2", score=None)
        session.add_result(1, result1)
        session.add_result(2, result2)

        generator = AuditReportGenerator()
        score = generator._calculate_overall_score(session)
        assert score == 8.0


class TestReportGeneration:
    """Test complete report generation"""

    def test_generate_report(self):
        """Generate a complete report"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            session = AuditSession.create(Path("/templates/test"))

            result = SectionResult(
                section_num=1,
                section_title="Manifest Analysis",
                score=8.5
            )
            session.add_result(1, result)

            generator = AuditReportGenerator()
            report_path = generator.generate_report(
                session=session,
                template_name="test-template",
                output_path=output_dir
            )

            assert report_path.exists()
            assert report_path.name == "audit-report.md"
            content = report_path.read_text()
            assert "Template Comprehensive Audit Report" in content
            assert "test-template" in content

    def test_report_content_structure(self):
        """Report contains all expected sections"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            session = AuditSession.create(Path("/templates/test"))

            result = SectionResult(
                section_num=1,
                section_title="Test Section",
                score=7.5
            )
            session.add_result(1, result)

            generator = AuditReportGenerator()
            report_path = generator.generate_report(
                session=session,
                template_name="test",
                output_path=output_dir
            )

            content = report_path.read_text()
            assert "Executive Summary" in content
            assert "Section Scores" in content
            assert "Detailed Section Results" in content
            assert "Production Readiness Decision" in content
            assert "Pre-Release Checklist" in content
            assert "Next Steps" in content

    def test_report_creates_directory(self):
        """Report generation creates output directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "new" / "nested" / "dir"
            session = AuditSession.create(Path("/templates/test"))

            result = SectionResult(
                section_num=1,
                section_title="Test",
                score=7.0
            )
            session.add_result(1, result)

            generator = AuditReportGenerator()
            report_path = generator.generate_report(
                session=session,
                template_name="test",
                output_path=output_dir
            )

            assert report_path.exists()
            assert output_dir.exists()


class TestExecutiveSummary:
    """Test executive summary generation"""

    def test_executive_summary_basic(self):
        """Executive summary includes key metrics"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=7.5)
        session.add_result(1, result)

        generator = AuditReportGenerator()
        summary = generator._generate_executive_summary(session, 7.5)

        assert "7.5" in summary
        assert "1" in summary  # sections audited


class TestDetailedSectionFormatting:
    """Test detailed section formatting"""

    def test_format_section_with_findings(self):
        """Format section with findings"""
        result = SectionResult(section_num=1, section_title="Test", score=8.0)
        finding = Finding(
            title="Good structure",
            description="Well organized",
            is_positive=True,
            impact="Easy to maintain"
        )
        result.findings.append(finding)

        generator = AuditReportGenerator()
        formatted = generator._format_section_detail(result)

        assert "Section 1" in formatted
        assert "Test" in formatted
        assert "Good structure" in formatted

    def test_format_section_with_issues(self):
        """Format section with issues"""
        result = SectionResult(section_num=2, section_title="Test", score=6.0)
        issue = ValidationIssue(
            severity=IssueSeverity.HIGH,
            category=IssueCategory.DOCUMENTATION,
            message="Missing docs"
        )
        result.issues.append(issue)

        generator = AuditReportGenerator()
        formatted = generator._format_section_detail(result)

        assert "Section 2" in formatted
        assert "HIGH" in formatted
        assert "Missing docs" in formatted

    def test_format_section_with_recommendations(self):
        """Format section with recommendations"""
        result = SectionResult(section_num=3, section_title="Test", score=7.0)
        rec = Recommendation(
            title="Add tests",
            description="Increase coverage",
            priority=IssueSeverity.MEDIUM,
            effort="low",
            impact="Better quality"
        )
        result.recommendations.append(rec)

        generator = AuditReportGenerator()
        formatted = generator._format_section_detail(result)

        assert "Add tests" in formatted
        assert "Increase coverage" in formatted


class TestStrengthsAndWeaknesses:
    """Test strengths and weaknesses generation"""

    def test_generate_strengths(self):
        """Generate strengths list"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=8.0)

        for i in range(3):
            finding = Finding(
                title=f"Strength {i}",
                description=f"Good {i}",
                is_positive=True,
                impact="Impact"
            )
            result.findings.append(finding)

        session.add_result(1, result)

        generator = AuditReportGenerator()
        strengths = generator._generate_strengths(session)

        assert "Strength" in strengths

    def test_generate_weaknesses(self):
        """Generate weaknesses list"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=6.0)

        for i in range(3):
            finding = Finding(
                title=f"Weakness {i}",
                description=f"Bad {i}",
                is_positive=False,
                impact="Impact"
            )
            result.findings.append(finding)

        session.add_result(1, result)

        generator = AuditReportGenerator()
        weaknesses = generator._generate_weaknesses(session)

        assert "Weakness" in weaknesses


class TestCriticalIssues:
    """Test critical issues generation"""

    def test_generate_critical_issues_none(self):
        """Generate message when no critical issues"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=8.0)
        session.add_result(1, result)

        generator = AuditReportGenerator()
        issues = generator._generate_critical_issues(session)

        assert "No critical issues" in issues or issues == "✅ No critical issues found."

    def test_generate_critical_issues_with_issues(self):
        """Generate critical issues list"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(section_num=1, section_title="Test", score=6.0)

        issue = ValidationIssue(
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.PRODUCTION,
            message="Critical problem"
        )
        result.issues.append(issue)
        session.add_result(1, result)

        generator = AuditReportGenerator()
        issues = generator._generate_critical_issues(session)

        assert "Critical problem" in issues or "critical" in issues.lower()


class TestDurationCalculation:
    """Test duration calculation"""

    def test_calculate_duration_minutes(self):
        """Calculate duration in minutes"""
        session = AuditSession.create(Path("/templates/test"))
        # Set updated_at to 5 minutes after created_at
        import datetime as dt
        session.updated_at = session.created_at + dt.timedelta(minutes=5)

        generator = AuditReportGenerator()
        duration = generator._calculate_duration(session)

        assert "minute" in duration or "5" in duration

    def test_calculate_duration_hours(self):
        """Calculate duration in hours"""
        session = AuditSession.create(Path("/templates/test"))
        # Set updated_at to 2 hours after created_at
        import datetime as dt
        session.updated_at = session.created_at + dt.timedelta(hours=2)

        generator = AuditReportGenerator()
        duration = generator._calculate_duration(session)

        assert "hour" in duration or "2" in duration
