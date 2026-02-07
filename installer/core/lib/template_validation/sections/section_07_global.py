"""
Section 7: Global Template Validation

Validates installation test, discovery, structure, and rules path-gating.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models import (
    SectionResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
    Finding,
    Recommendation,
)

# Compiled regex for detecting paths: in YAML frontmatter
_FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)
_PATHS_KEY_PATTERN = re.compile(r'^paths:\s', re.MULTILINE)

# Filename-to-path-pattern suggestions for common rules files
_PATH_SUGGESTIONS: Dict[str, str] = {
    "code-style.md": "**/*.py, **/*.ts, **/*.tsx",
    "testing.md": "tests/**/*.py, **/*.test.ts, **/conftest.py",
    "database.md": "**/db/**/*.py, **/models.py",
    "api.md": "**/api/**/*.py, **/routes/**/*",
    "security.md": "**/*.py, **/*.ts",
    "config.md": "**/config/**/*",
    "docker.md": "**/Dockerfile, **/docker-compose.yml",
    "workflow.md": "tasks/**/*",
    "quality-gates.md": "**/*.py, **/*.ts",
    "mcp-patterns.md": "src/**/*.py, src/**/*.ts",
    "transport.md": "src/**/*.ts, config/**/*",
    "configuration.md": "config/**/*.json, *.json",
}


def has_paths_frontmatter(content: str) -> bool:
    """Check if a markdown file has paths: in its YAML frontmatter.

    Args:
        content: File content to check.

    Returns:
        True if the file has valid YAML frontmatter containing a paths: key.
    """
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return False
    frontmatter = match.group(1)
    return bool(_PATHS_KEY_PATTERN.search(frontmatter))


def suggest_paths(filename: str) -> str:
    """Suggest appropriate paths: frontmatter based on filename.

    Args:
        filename: The rules file name (e.g., 'code-style.md').

    Returns:
        A suggested glob pattern string.
    """
    return _PATH_SUGGESTIONS.get(filename, "**/*  # TODO: specify appropriate paths")


def validate_rules_path_gating(
    template_path: Path,
) -> Tuple[List[ValidationIssue], int, int, List[str]]:
    """Check that rules files have paths: frontmatter for conditional loading.

    Args:
        template_path: Root path of the template being validated.

    Returns:
        Tuple of (issues, total_count, gated_count, ungated_files).
    """
    issues: List[ValidationIssue] = []
    ungated_files: List[str] = []
    total_count = 0
    gated_count = 0

    rules_dir = template_path / ".claude" / "rules"
    if not rules_dir.exists():
        return issues, 0, 0, []

    for rules_file in sorted(rules_dir.rglob("*.md")):
        total_count += 1
        content = rules_file.read_text(encoding="utf-8")

        if has_paths_frontmatter(content):
            gated_count += 1
        else:
            rel_path = str(rules_file.relative_to(template_path))
            suggestion = suggest_paths(rules_file.name)
            ungated_files.append(rel_path)
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.PATH_GATING,
                message=(
                    f"Missing paths: frontmatter - file loads unconditionally. "
                    f"Suggested: paths: {suggestion}"
                ),
                location=rel_path,
                fixable=True,
                fix_description=f"Add YAML frontmatter with paths: {suggestion}",
            ))

    return issues, total_count, gated_count, ungated_files


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
        return "Validate installation test, discovery, structure, and path-gating"

    def execute(self, template_path: Path, interactive: bool = True) -> SectionResult:
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        recommendations: List[Recommendation] = []
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

        # Path-gating validation
        pg_issues, total, gated, ungated = validate_rules_path_gating(template_path)
        issues.extend(pg_issues)

        if total > 0:
            coverage_pct = (gated / total) * 100

            if coverage_pct == 100:
                findings.append(Finding(
                    title="Full Path-Gating Coverage",
                    description=f"All {total} rules files have paths: frontmatter",
                    is_positive=True,
                    impact="Rules load conditionally, minimizing token usage",
                ))
            else:
                # Deduct score based on ungated percentage
                ungated_count = total - gated
                deduction = min(3.0, ungated_count * 0.5)
                score -= deduction

                findings.append(Finding(
                    title="Incomplete Path-Gating Coverage",
                    description=(
                        f"{gated}/{total} rules files ({coverage_pct:.0f}%) "
                        f"have paths: frontmatter"
                    ),
                    is_positive=False,
                    impact=(
                        f"{ungated_count} file(s) load unconditionally, "
                        f"wasting ~{ungated_count * 300} tokens per conversation"
                    ),
                    evidence=", ".join(ungated),
                ))

                recommendations.append(Recommendation(
                    title="Add paths: frontmatter to all rules files",
                    description=(
                        "Add YAML frontmatter with paths: glob patterns to enable "
                        "conditional loading. Files without paths: load in every "
                        "conversation regardless of context."
                    ),
                    priority=IssueSeverity.MEDIUM,
                    effort="low",
                    impact="Reduces token usage by loading rules only when relevant",
                ))

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=max(0.0, score),
            findings=findings,
            issues=issues,
            recommendations=recommendations,
            metadata={
                "path_gating_total": total,
                "path_gating_gated": gated,
                "path_gating_coverage_pct": round((gated / total) * 100, 1) if total > 0 else 100.0,
                "path_gating_ungated_files": ungated,
            },
            completed_at=datetime.now(),
        )
