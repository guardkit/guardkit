"""
Data Models for Template Validation

Comprehensive data structures for audit results, issues, and configuration.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


class IssueSeverity(Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # Blocks production use
    HIGH = "high"  # Should be fixed before release
    MEDIUM = "medium"  # Should be addressed
    LOW = "low"  # Nice to have
    INFO = "info"  # Informational only


class IssueCategory(Enum):
    """Categories of validation issues"""
    METADATA = "metadata"
    DOCUMENTATION = "documentation"
    FILES = "files"
    AGENTS = "agents"
    PATTERNS = "patterns"
    TESTING = "testing"
    PRODUCTION = "production"
    QUALITY = "quality"


@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: IssueSeverity
    category: IssueCategory
    message: str
    location: Optional[str] = None
    fixable: bool = False
    fix_description: Optional[str] = None
    auto_fix: Optional[callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "location": self.location,
            "fixable": self.fixable,
            "fix_description": self.fix_description,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ValidationIssue':
        """Create from dictionary"""
        return ValidationIssue(
            severity=IssueSeverity(data["severity"]),
            category=IssueCategory(data["category"]),
            message=data["message"],
            location=data.get("location"),
            fixable=data.get("fixable", False),
            fix_description=data.get("fix_description"),
        )


@dataclass
class Finding:
    """A finding from audit section (positive or negative)"""
    title: str
    description: str
    is_positive: bool  # True for strengths, False for weaknesses
    impact: str  # Description of impact
    evidence: Optional[str] = None


@dataclass
class Recommendation:
    """A recommendation for improvement"""
    title: str
    description: str
    priority: IssueSeverity
    effort: str  # "low", "medium", "high"
    impact: str  # Expected impact of implementing


@dataclass
class SectionResult:
    """Result from a single audit section"""
    section_num: int
    section_title: str
    score: Optional[float]  # 0-10, or None for optional sections
    findings: List[Finding] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None

    def has_issues(self) -> bool:
        """Check if section has any issues"""
        return len(self.issues) > 0

    def has_critical_issues(self) -> bool:
        """Check if section has critical issues"""
        return any(
            issue.severity == IssueSeverity.CRITICAL
            for issue in self.issues
        )

    def fixable_issues(self) -> List[ValidationIssue]:
        """Get list of fixable issues"""
        return [issue for issue in self.issues if issue.fixable]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "section_num": self.section_num,
            "section_title": self.section_title,
            "score": self.score,
            "findings": [
                {
                    "title": f.title,
                    "description": f.description,
                    "is_positive": f.is_positive,
                    "impact": f.impact,
                    "evidence": f.evidence,
                }
                for f in self.findings
            ],
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": [
                {
                    "title": r.title,
                    "description": r.description,
                    "priority": r.priority.value,
                    "effort": r.effort,
                    "impact": r.impact,
                }
                for r in self.recommendations
            ],
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SectionResult':
        """Create from dictionary"""
        return SectionResult(
            section_num=data["section_num"],
            section_title=data["section_title"],
            score=data["score"],
            findings=[
                Finding(
                    title=f["title"],
                    description=f["description"],
                    is_positive=f["is_positive"],
                    impact=f["impact"],
                    evidence=f.get("evidence"),
                )
                for f in data.get("findings", [])
            ],
            issues=[ValidationIssue.from_dict(i) for i in data.get("issues", [])],
            recommendations=[
                Recommendation(
                    title=r["title"],
                    description=r["description"],
                    priority=IssueSeverity(r["priority"]),
                    effort=r["effort"],
                    impact=r["impact"],
                )
                for r in data.get("recommendations", [])
            ],
            metadata=data.get("metadata", {}),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


class AuditRecommendation(Enum):
    """Final audit recommendation"""
    APPROVE = "approve"  # Ready for production
    NEEDS_IMPROVEMENT = "needs_improvement"  # Requires fixes
    REJECT = "reject"  # Not suitable for production


@dataclass
class AuditResult:
    """Complete audit result"""
    template_name: str
    template_path: Path
    overall_score: float  # 0-10
    grade: str  # A, B, C, D, F
    recommendation: AuditRecommendation
    section_results: List[SectionResult]
    overall_findings: List[Finding] = field(default_factory=list)
    critical_issues: List[ValidationIssue] = field(default_factory=list)
    top_recommendations: List[Recommendation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    audit_duration_seconds: float = 0.0


@dataclass
class ValidateConfig:
    """Configuration for template validation"""
    template_path: Path
    sections: Optional[List[int]] = None  # None = all sections
    interactive: bool = True
    resume_session_id: Optional[str] = None
    output_dir: Optional[Path] = None
    auto_fix: bool = False
    verbose: bool = False


@dataclass
class FixLog:
    """Log entry for applied fix"""
    timestamp: datetime
    section_num: int
    issue_description: str
    fix_description: str
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "section_num": self.section_num,
            "issue_description": self.issue_description,
            "fix_description": self.fix_description,
            "success": self.success,
            "error_message": self.error_message,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FixLog':
        """Create from dictionary"""
        return FixLog(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            section_num=data["section_num"],
            issue_description=data["issue_description"],
            fix_description=data["fix_description"],
            success=data["success"],
            error_message=data.get("error_message"),
        )
