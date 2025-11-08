"""
Unit Tests for Template Validation Models

Tests for data models, enums, and serialization in the template validation system.
"""

import pytest
import json
import tempfile
import importlib
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))

# Use importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('global.lib.template_validation.models')
IssueSeverity = _models_module.IssueSeverity
IssueCategory = _models_module.IssueCategory
ValidationIssue = _models_module.ValidationIssue
Finding = _models_module.Finding
Recommendation = _models_module.Recommendation
SectionResult = _models_module.SectionResult
AuditRecommendation = _models_module.AuditRecommendation
AuditResult = _models_module.AuditResult
ValidateConfig = _models_module.ValidateConfig
FixLog = _models_module.FixLog


class TestIssueSeverity:
    """Test IssueSeverity enum"""

    def test_severity_values(self):
        """Verify all severity levels exist"""
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.INFO.value == "info"

    def test_severity_count(self):
        """Verify correct number of severity levels"""
        assert len(IssueSeverity) == 5


class TestIssueCategory:
    """Test IssueCategory enum"""

    def test_category_values(self):
        """Verify all category types exist"""
        assert IssueCategory.METADATA.value == "metadata"
        assert IssueCategory.DOCUMENTATION.value == "documentation"
        assert IssueCategory.FILES.value == "files"
        assert IssueCategory.AGENTS.value == "agents"
        assert IssueCategory.PATTERNS.value == "patterns"
        assert IssueCategory.TESTING.value == "testing"
        assert IssueCategory.PRODUCTION.value == "production"
        assert IssueCategory.QUALITY.value == "quality"

    def test_category_count(self):
        """Verify correct number of categories"""
        assert len(IssueCategory) == 8


class TestValidationIssue:
    """Test ValidationIssue dataclass"""

    def test_create_issue(self):
        """Create a validation issue"""
        issue = ValidationIssue(
            severity=IssueSeverity.HIGH,
            category=IssueCategory.DOCUMENTATION,
            message="Missing documentation",
            location="path/to/file.md",
            fixable=True,
            fix_description="Add documentation"
        )
        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == IssueCategory.DOCUMENTATION
        assert issue.message == "Missing documentation"
        assert issue.location == "path/to/file.md"
        assert issue.fixable is True
        assert issue.fix_description == "Add documentation"
        assert issue.auto_fix is None

    def test_issue_to_dict(self):
        """Serialize issue to dictionary"""
        issue = ValidationIssue(
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.METADATA,
            message="Invalid metadata",
            location="file.txt",
            fixable=False
        )
        data = issue.to_dict()
        assert data["severity"] == "critical"
        assert data["category"] == "metadata"
        assert data["message"] == "Invalid metadata"
        assert data["location"] == "file.txt"
        assert data["fixable"] is False

    def test_issue_from_dict(self):
        """Deserialize issue from dictionary"""
        data = {
            "severity": "high",
            "category": "testing",
            "message": "Missing tests",
            "location": "test_module.py",
            "fixable": True,
            "fix_description": "Add tests"
        }
        issue = ValidationIssue.from_dict(data)
        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == IssueCategory.TESTING
        assert issue.message == "Missing tests"
        assert issue.fixable is True

    def test_issue_roundtrip(self):
        """Test serialization and deserialization"""
        original = ValidationIssue(
            severity=IssueSeverity.MEDIUM,
            category=IssueCategory.QUALITY,
            message="Code quality issue",
            fixable=False
        )
        data = original.to_dict()
        restored = ValidationIssue.from_dict(data)
        assert restored.severity == original.severity
        assert restored.category == original.category
        assert restored.message == original.message


class TestFinding:
    """Test Finding dataclass"""

    def test_create_positive_finding(self):
        """Create a positive finding"""
        finding = Finding(
            title="Well documented",
            description="Code is well documented",
            is_positive=True,
            impact="Easier maintenance"
        )
        assert finding.title == "Well documented"
        assert finding.is_positive is True

    def test_create_negative_finding(self):
        """Create a negative finding"""
        finding = Finding(
            title="No tests",
            description="Code has no test coverage",
            is_positive=False,
            impact="Quality risks",
            evidence="0% coverage"
        )
        assert finding.is_positive is False
        assert finding.evidence == "0% coverage"


class TestRecommendation:
    """Test Recommendation dataclass"""

    def test_create_recommendation(self):
        """Create a recommendation"""
        rec = Recommendation(
            title="Add documentation",
            description="Documentation is needed for public APIs",
            priority=IssueSeverity.HIGH,
            effort="low",
            impact="Improved usability"
        )
        assert rec.title == "Add documentation"
        assert rec.priority == IssueSeverity.HIGH
        assert rec.effort == "low"


class TestSectionResult:
    """Test SectionResult dataclass"""

    def test_create_section_result(self):
        """Create a section result"""
        result = SectionResult(
            section_num=1,
            section_title="Manifest Analysis",
            score=8.5
        )
        assert result.section_num == 1
        assert result.section_title == "Manifest Analysis"
        assert result.score == 8.5
        assert result.findings == []
        assert result.issues == []
        assert result.recommendations == []

    def test_has_issues(self):
        """Check if section has issues"""
        result = SectionResult(section_num=1, section_title="Test", score=7.0)
        assert result.has_issues() is False

        issue = ValidationIssue(
            severity=IssueSeverity.LOW,
            category=IssueCategory.DOCUMENTATION,
            message="Minor issue"
        )
        result.issues.append(issue)
        assert result.has_issues() is True

    def test_has_critical_issues(self):
        """Check for critical issues"""
        result = SectionResult(section_num=1, section_title="Test", score=7.0)
        assert result.has_critical_issues() is False

        # Add non-critical issue
        issue = ValidationIssue(
            severity=IssueSeverity.HIGH,
            category=IssueCategory.QUALITY,
            message="High issue"
        )
        result.issues.append(issue)
        assert result.has_critical_issues() is False

        # Add critical issue
        critical = ValidationIssue(
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.PRODUCTION,
            message="Critical issue"
        )
        result.issues.append(critical)
        assert result.has_critical_issues() is True

    def test_fixable_issues(self):
        """Get list of fixable issues"""
        result = SectionResult(section_num=1, section_title="Test", score=7.0)

        # Add non-fixable issue
        issue1 = ValidationIssue(
            severity=IssueSeverity.HIGH,
            category=IssueCategory.QUALITY,
            message="Issue 1",
            fixable=False
        )
        result.issues.append(issue1)

        # Add fixable issue
        issue2 = ValidationIssue(
            severity=IssueSeverity.MEDIUM,
            category=IssueCategory.DOCUMENTATION,
            message="Issue 2",
            fixable=True,
            fix_description="Fix it"
        )
        result.issues.append(issue2)

        fixable = result.fixable_issues()
        assert len(fixable) == 1
        assert fixable[0] == issue2

    def test_section_result_to_dict(self):
        """Serialize section result"""
        finding = Finding(
            title="Good structure",
            description="Well organized",
            is_positive=True,
            impact="Easy to maintain"
        )
        result = SectionResult(
            section_num=2,
            section_title="Settings Analysis",
            score=7.5,
            findings=[finding]
        )
        data = result.to_dict()
        assert data["section_num"] == 2
        assert data["section_title"] == "Settings Analysis"
        assert data["score"] == 7.5
        assert len(data["findings"]) == 1
        assert data["findings"][0]["title"] == "Good structure"

    def test_section_result_from_dict(self):
        """Deserialize section result"""
        data = {
            "section_num": 3,
            "section_title": "Documentation Analysis",
            "score": 8.0,
            "findings": [],
            "issues": [],
            "recommendations": [],
            "metadata": {},
            "completed_at": None
        }
        result = SectionResult.from_dict(data)
        assert result.section_num == 3
        assert result.section_title == "Documentation Analysis"
        assert result.score == 8.0


class TestAuditRecommendation:
    """Test AuditRecommendation enum"""

    def test_recommendation_values(self):
        """Verify recommendation levels"""
        assert AuditRecommendation.APPROVE.value == "approve"
        assert AuditRecommendation.NEEDS_IMPROVEMENT.value == "needs_improvement"
        assert AuditRecommendation.REJECT.value == "reject"

    def test_recommendation_count(self):
        """Verify correct number of recommendations"""
        assert len(AuditRecommendation) == 3


class TestAuditResult:
    """Test AuditResult dataclass"""

    def test_create_audit_result(self):
        """Create an audit result"""
        template_path = Path("/templates/react")
        result = AuditResult(
            template_name="react",
            template_path=template_path,
            overall_score=8.5,
            grade="A",
            recommendation=AuditRecommendation.APPROVE,
            section_results=[]
        )
        assert result.template_name == "react"
        assert result.template_path == template_path
        assert result.overall_score == 8.5
        assert result.grade == "A"
        assert result.recommendation == AuditRecommendation.APPROVE


class TestValidateConfig:
    """Test ValidateConfig dataclass"""

    def test_create_config(self):
        """Create validation config"""
        template_path = Path("/templates/python")
        config = ValidateConfig(
            template_path=template_path,
            interactive=False,
            auto_fix=True
        )
        assert config.template_path == template_path
        assert config.interactive is False
        assert config.auto_fix is True
        assert config.sections is None
        assert config.resume_session_id is None

    def test_config_with_sections(self):
        """Create config with specific sections"""
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            sections=[1, 2, 3]
        )
        assert config.sections == [1, 2, 3]

    def test_config_with_output_dir(self):
        """Create config with custom output directory"""
        output = Path("/output/reports")
        config = ValidateConfig(
            template_path=Path("/templates/test"),
            output_dir=output
        )
        assert config.output_dir == output


class TestFixLog:
    """Test FixLog dataclass"""

    def test_create_fix_log(self):
        """Create a fix log entry"""
        now = datetime.now()
        log = FixLog(
            timestamp=now,
            section_num=1,
            issue_description="Missing file",
            fix_description="Created file",
            success=True
        )
        assert log.timestamp == now
        assert log.section_num == 1
        assert log.success is True
        assert log.error_message is None

    def test_failed_fix_log(self):
        """Create a failed fix log"""
        log = FixLog(
            timestamp=datetime.now(),
            section_num=2,
            issue_description="Invalid JSON",
            fix_description="Fix JSON format",
            success=False,
            error_message="Permission denied"
        )
        assert log.success is False
        assert log.error_message == "Permission denied"

    def test_fix_log_to_dict(self):
        """Serialize fix log"""
        now = datetime.now()
        log = FixLog(
            timestamp=now,
            section_num=1,
            issue_description="Test issue",
            fix_description="Test fix",
            success=True
        )
        data = log.to_dict()
        assert data["section_num"] == 1
        assert data["issue_description"] == "Test issue"
        assert data["success"] is True
        assert "timestamp" in data

    def test_fix_log_from_dict(self):
        """Deserialize fix log"""
        now = datetime.now()
        data = {
            "timestamp": now.isoformat(),
            "section_num": 5,
            "issue_description": "Issue",
            "fix_description": "Fix",
            "success": True,
            "error_message": None
        }
        log = FixLog.from_dict(data)
        assert log.section_num == 5
        assert log.success is True

    def test_fix_log_roundtrip(self):
        """Test fix log serialization roundtrip"""
        original = FixLog(
            timestamp=datetime.now(),
            section_num=3,
            issue_description="Original issue",
            fix_description="Original fix",
            success=True
        )
        data = original.to_dict()
        restored = FixLog.from_dict(data)
        assert restored.section_num == original.section_num
        assert restored.issue_description == original.issue_description
        assert restored.success == original.success
