"""
Section 3: Documentation Analysis

Validates CLAUDE.md architecture, patterns, and examples.
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


class DocumentationAnalysisSection:
    """Section 3: Documentation Analysis"""

    @property
    def section_num(self) -> int:
        return 3

    @property
    def title(self) -> str:
        return "Documentation Analysis"

    @property
    def description(self) -> str:
        return "Validate CLAUDE.md architecture, patterns, and examples"

    def execute(
        self,
        template_path: Path,
        interactive: bool = True
    ) -> SectionResult:
        """Execute documentation analysis"""
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        recommendations: List[Recommendation] = []

        # Check for CLAUDE.md
        claude_md_path = template_path / "CLAUDE.md"
        if not claude_md_path.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.DOCUMENTATION,
                message="CLAUDE.md not found (required for AI-assisted development)",
                location=str(template_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=0.0,
                issues=issues,
                completed_at=datetime.now(),
            )

        # Read and analyze CLAUDE.md
        content = claude_md_path.read_text()
        score = 10.0

        # Check for key sections
        required_sections = [
            ("## Architecture", "Architecture description"),
            ("## Patterns", "Design patterns documentation"),
            ("## Project Structure", "Project structure overview"),
        ]

        for section_marker, section_name in required_sections:
            if section_marker not in content:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.DOCUMENTATION,
                    message=f"Missing section: {section_name}",
                    location=str(claude_md_path),
                ))
                score -= 2.0
            else:
                findings.append(Finding(
                    title=f"{section_name} Present",
                    description=f"Documentation includes {section_name.lower()}",
                    is_positive=True,
                    impact="Improves AI understanding of template",
                ))

        # Check length
        if len(content) < 500:
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.DOCUMENTATION,
                message="CLAUDE.md is too brief (< 500 characters)",
                location=str(claude_md_path),
            ))
            score -= 1.5
        elif len(content) > 2000:
            findings.append(Finding(
                title="Comprehensive Documentation",
                description=f"CLAUDE.md is detailed ({len(content)} characters)",
                is_positive=True,
                impact="Provides thorough context for AI agents",
            ))

        # Check for code examples
        if "```" in content:
            findings.append(Finding(
                title="Code Examples Included",
                description="Documentation includes code examples",
                is_positive=True,
                impact="Helps developers understand usage patterns",
            ))
        else:
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.DOCUMENTATION,
                message="No code examples found in CLAUDE.md",
                location=str(claude_md_path),
            ))
            score -= 1.0

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            recommendations=recommendations,
            metadata={"content_length": len(content)},
            completed_at=datetime.now(),
        )
