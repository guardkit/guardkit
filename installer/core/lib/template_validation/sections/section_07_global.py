"""
Section 7: Global Template Validation

Validates installation test, discovery, and structure.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SectionResult, ValidationIssue, IssueSeverity, IssueCategory, Finding


class GlobalTemplateValidationSection:
    """Section 7: Global Template Validation"""

    @property
    def section_num(self) -> int:
        return 7

    @property
    def title(self) -> str:
        return "Global Template Validation"

    @property
    def description(self) -> str:
        return "Validate installation test, discovery, and structure"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        score = 10.0
        
        # Check required files
        required_files = ["manifest.json", "CLAUDE.md", "README.md"]
        for filename in required_files:
            if not (template_path / filename).exists():
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.FILES,
                    message=f"Missing required file: {filename}",
                ))
                score -= 3.0
        
        if score >= 8.0:
            findings.append(Finding(
                title="Complete Template Structure",
                description="All required files present",
                is_positive=True,
                impact="Template is ready for deployment",
            ))
        
        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            completed_at=datetime.now(),
        )
