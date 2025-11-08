"""
Section 2: Settings Analysis

Validates naming conventions, layer mappings, and code style settings.
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


class SettingsAnalysisSection:
    """Section 2: Settings Analysis"""

    @property
    def section_num(self) -> int:
        return 2

    @property
    def title(self) -> str:
        return "Settings Analysis"

    @property
    def description(self) -> str:
        return "Validate naming conventions, layer mappings, and code style"

    def execute(
        self,
        template_path: Path,
        interactive: bool = True
    ) -> SectionResult:
        """Execute settings analysis"""
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        recommendations: List[Recommendation] = []

        # Check for settings.json
        settings_path = template_path / "settings.json"
        if not settings_path.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.METADATA,
                message="settings.json not found (recommended for advanced templates)",
                location=str(template_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=7.0,  # Not critical, so partial score
                issues=issues,
                findings=findings,
                recommendations=recommendations,
                completed_at=datetime.now(),
            )

        # If settings.json exists, validate its content
        try:
            import json
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.METADATA,
                message=f"Invalid JSON in settings.json: {e}",
                location=str(settings_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=3.0,
                issues=issues,
                completed_at=datetime.now(),
            )

        score = 10.0

        # Check for naming conventions
        if 'naming_conventions' not in settings:
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.PATTERNS,
                message="Missing naming_conventions configuration",
            ))
            score -= 1.5
        else:
            findings.append(Finding(
                title="Naming Conventions Defined",
                description="Template includes naming convention standards",
                is_positive=True,
                impact="Ensures consistent code style",
            ))

        # Check for layer mappings
        if 'layer_mappings' not in settings:
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.PATTERNS,
                message="Missing layer_mappings configuration",
            ))
            score -= 1.5
        else:
            findings.append(Finding(
                title="Layer Mappings Defined",
                description="Template includes layer organization mappings",
                is_positive=True,
                impact="Improves codebase navigation",
            ))

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            recommendations=recommendations,
            completed_at=datetime.now(),
        )
