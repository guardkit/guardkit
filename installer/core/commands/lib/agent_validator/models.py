"""
Data models for agent validation.

Provides structured types for validation results, scores, and recommendations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class CheckStatus(Enum):
    """Status of individual validation check."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class FileStatus(Enum):
    """Overall validation status."""
    EXCELLENT = "excellent"  # >= 9.0
    GOOD = "good"            # >= 8.0
    ACCEPTABLE = "acceptable"  # >= 7.0
    BELOW_TARGET = "below_target"  # >= 6.0
    POOR = "poor"            # < 6.0


@dataclass
class CheckResult:
    """Result of a single validation check."""
    name: str
    measured_value: Any
    threshold: Any  # Can be single value or tuple (min, max)
    score: float  # 0.0-10.0
    weight: float  # Weight within category (0.0-1.0)
    status: str  # "pass" | "warn" | "fail"
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class CategoryScore:
    """Score for a validation category."""
    name: str
    score: float  # 0.0-10.0
    weight: float  # Weight in overall score (0.0-1.0)
    checks: Dict[str, CheckResult] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted contribution to overall score."""
        return self.score * self.weight


@dataclass
class Recommendation:
    """Actionable recommendation for improvement."""
    priority: str  # P1 | P2 | P3 | P4
    category: str
    action: str
    impact: str  # "+X points"
    estimated_time_minutes: int
    line_numbers: Optional[List[int]] = None
    specific_fixes: Optional[List[str]] = None


@dataclass
class ValidationReport:
    """Complete validation report for an agent file."""
    file: str
    lines: int
    overall_score: float  # 0.0-10.0
    status: str  # FileStatus enum value
    category_scores: Dict[str, CategoryScore]
    checks: Dict[str, Dict[str, CheckResult]]  # category -> check_name -> result
    recommendations: List[Recommendation]
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "lines": self.lines,
            "overall_score": round(self.overall_score, 2),
            "status": self.status,
            "timestamp": self.timestamp,
            "category_scores": {
                name: {
                    "score": round(cat.score, 2),
                    "weight": cat.weight,
                    "weighted_contribution": round(cat.weighted_score, 2),
                    "checks": {
                        check_name: {
                            "name": check.name,
                            "measured_value": check.measured_value,
                            "threshold": check.threshold,
                            "score": round(check.score, 2),
                            "weight": check.weight,
                            "status": check.status,
                            "message": check.message,
                            "line_number": check.line_number,
                            "suggestion": check.suggestion
                        }
                        for check_name, check in cat.checks.items()
                    }
                }
                for name, cat in self.category_scores.items()
            },
            "recommendations": [
                {
                    "priority": rec.priority,
                    "category": rec.category,
                    "action": rec.action,
                    "impact": rec.impact,
                    "estimated_time_minutes": rec.estimated_time_minutes,
                    "line_numbers": rec.line_numbers,
                    "specific_fixes": rec.specific_fixes
                }
                for rec in self.recommendations
            ]
        }


@dataclass
class BatchValidationResult:
    """Results from batch validation of multiple agents."""
    total_files: int
    passed: int
    failed: int
    threshold: float
    reports: List[ValidationReport]
    summary_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert batch results to dictionary."""
        return {
            "total_files": self.total_files,
            "passed": self.passed,
            "failed": self.failed,
            "threshold": self.threshold,
            "summary_stats": self.summary_stats,
            "reports": [report.to_dict() for report in self.reports]
        }
