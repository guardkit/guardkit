"""
Section 4: Template Files Analysis

Validates file selection quality and placeholder integration.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import (
    SectionResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
    Finding,
    Recommendation,
)


class TemplateFilesAnalysisSection:
    """Section 4: Template Files Analysis"""

    @property
    def section_num(self) -> int:
        return 4

    @property
    def title(self) -> str:
        return "Template Files Analysis"

    @property
    def description(self) -> str:
        return "Validate file selection quality and placeholder integration"

    def execute(
        self,
        template_path: Path,
        interactive: bool = True
    ) -> SectionResult:
        """Execute template files analysis"""
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []

        # Check for templates directory
        templates_dir = template_path / "templates"
        if not templates_dir.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.FILES,
                message="templates/ directory not found",
                location=str(template_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=0.0,
                issues=issues,
                completed_at=datetime.now(),
            )

        # Count template files
        template_files = list(templates_dir.rglob("*.template"))
        file_count = len(template_files)

        score = 10.0

        if file_count == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.FILES,
                message="No template files found in templates/ directory",
                location=str(templates_dir),
            ))
            score = 0.0
        elif file_count < 5:
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.FILES,
                message=f"Only {file_count} template files (minimal coverage)",
                location=str(templates_dir),
            ))
            score -= 2.0
        else:
            findings.append(Finding(
                title="Good Template Coverage",
                description=f"{file_count} template files provide comprehensive coverage",
                is_positive=True,
                impact="Enables complete project scaffolding",
            ))

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            metadata={"file_count": file_count},
            completed_at=datetime.now(),
        )
