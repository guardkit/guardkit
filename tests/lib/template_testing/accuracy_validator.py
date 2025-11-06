"""
Accuracy Validator for Template Create Integration Tests

Validates AI analysis accuracy against ground truth for template creation.
Target: 90%+ accuracy across all analysis categories.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class GroundTruth:
    """Ground truth data for a sample project."""
    
    project_name: str
    tech_stack: str
    patterns: List[str]
    key_files: List[str]
    dependencies: List[str]
    architecture_style: str
    testing_framework: Optional[str] = None
    
    
@dataclass
class AccuracyReport:
    """Report of AI analysis accuracy."""
    
    category: str
    expected: List[str]
    actual: List[str]
    matches: List[str]
    missing: List[str]
    extra: List[str]
    accuracy_percentage: float
    
    
class AccuracyValidator:
    """Validates AI analysis accuracy against ground truth."""
    
    def __init__(self, ground_truth: GroundTruth):
        self.ground_truth = ground_truth
        self.reports: List[AccuracyReport] = []
        
    def validate_tech_stack(self, detected_stack: str) -> AccuracyReport:
        """Validate detected technology stack."""
        expected = [self.ground_truth.tech_stack]
        actual = [detected_stack]
        matches = expected if detected_stack == self.ground_truth.tech_stack else []
        missing = [] if matches else expected
        extra = [] if matches else actual
        accuracy = 100.0 if matches else 0.0
        
        report = AccuracyReport(
            category="tech_stack",
            expected=expected,
            actual=actual,
            matches=matches,
            missing=missing,
            extra=extra,
            accuracy_percentage=accuracy
        )
        self.reports.append(report)
        return report
        
    def validate_patterns(self, detected_patterns: List[str]) -> AccuracyReport:
        """Validate detected design patterns."""
        expected = set(self.ground_truth.patterns)
        actual = set(detected_patterns)
        
        matches = list(expected & actual)
        missing = list(expected - actual)
        extra = list(actual - expected)
        
        if len(expected) == 0:
            accuracy = 100.0
        else:
            accuracy = (len(matches) / len(expected)) * 100.0
            
        report = AccuracyReport(
            category="patterns",
            expected=list(expected),
            actual=list(actual),
            matches=matches,
            missing=missing,
            extra=extra,
            accuracy_percentage=accuracy
        )
        self.reports.append(report)
        return report
        
    def validate_key_files(self, detected_files: List[str]) -> AccuracyReport:
        """Validate identified key files."""
        expected = set(self.ground_truth.key_files)
        actual = set(detected_files)
        
        matches = list(expected & actual)
        missing = list(expected - actual)
        extra = list(actual - expected)
        
        if len(expected) == 0:
            accuracy = 100.0
        else:
            accuracy = (len(matches) / len(expected)) * 100.0
            
        report = AccuracyReport(
            category="key_files",
            expected=list(expected),
            actual=list(actual),
            matches=matches,
            missing=missing,
            extra=extra,
            accuracy_percentage=accuracy
        )
        self.reports.append(report)
        return report
        
    def validate_dependencies(self, detected_deps: List[str]) -> AccuracyReport:
        """Validate detected dependencies."""
        expected = set(self.ground_truth.dependencies)
        actual = set(detected_deps)
        
        matches = list(expected & actual)
        missing = list(expected - actual)
        extra = list(actual - expected)
        
        if len(expected) == 0:
            accuracy = 100.0
        else:
            accuracy = (len(matches) / len(expected)) * 100.0
            
        report = AccuracyReport(
            category="dependencies",
            expected=list(expected),
            actual=list(actual),
            matches=matches,
            missing=missing,
            extra=extra,
            accuracy_percentage=accuracy
        )
        self.reports.append(report)
        return report
        
    def validate_architecture(self, detected_arch: str) -> AccuracyReport:
        """Validate detected architecture style."""
        expected = [self.ground_truth.architecture_style]
        actual = [detected_arch]
        matches = expected if detected_arch == self.ground_truth.architecture_style else []
        missing = [] if matches else expected
        extra = [] if matches else actual
        accuracy = 100.0 if matches else 0.0
        
        report = AccuracyReport(
            category="architecture",
            expected=expected,
            actual=actual,
            matches=matches,
            missing=missing,
            extra=extra,
            accuracy_percentage=accuracy
        )
        self.reports.append(report)
        return report
        
    def get_overall_accuracy(self) -> float:
        """Calculate overall accuracy across all validations."""
        if not self.reports:
            return 0.0
            
        total_accuracy = sum(report.accuracy_percentage for report in self.reports)
        return total_accuracy / len(self.reports)
        
    def get_summary(self) -> Dict:
        """Get summary of all accuracy validations."""
        return {
            "overall_accuracy": self.get_overall_accuracy(),
            "total_validations": len(self.reports),
            "reports": [
                {
                    "category": r.category,
                    "accuracy": r.accuracy_percentage,
                    "matches": len(r.matches),
                    "missing": len(r.missing),
                    "extra": len(r.extra)
                }
                for r in self.reports
            ]
        }
        
    def assert_accuracy_threshold(self, threshold: float = 90.0):
        """Assert that overall accuracy meets threshold."""
        overall = self.get_overall_accuracy()
        if overall < threshold:
            raise AssertionError(
                f"Overall accuracy {overall:.1f}% below threshold {threshold}%\n"
                f"Summary: {self.get_summary()}"
            )
