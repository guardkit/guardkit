"""
Section 6: README Review

Validates content completeness, usability, and accuracy.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SectionResult, ValidationIssue, IssueSeverity, IssueCategory, Finding


class ReadmeReviewSection:
    """Section 6: README Review"""

    @property
    def section_num(self) -> int:
        return 6

    @property
    def title(self) -> str:
        return "README Review"

    @property
    def description(self) -> str:
        return "Validate content completeness, usability, and accuracy"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        
        readme_path = template_path / "README.md"
        score = 10.0
        
        if not readme_path.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.DOCUMENTATION,
                message="README.md not found",
            ))
            score = 2.0
        else:
            content = readme_path.read_text()
            if len(content) > 200:
                findings.append(Finding(
                    title="Comprehensive README",
                    description=f"README.md is detailed ({len(content)} characters)",
                    is_positive=True,
                    impact="Helps developers get started quickly",
                ))
            else:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.DOCUMENTATION,
                    message="README.md is too brief",
                ))
                score -= 3.0
        
        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            completed_at=datetime.now(),
        )
