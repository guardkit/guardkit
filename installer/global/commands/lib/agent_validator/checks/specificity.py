"""Specificity validation checks."""

import re
from typing import Dict, List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class SpecificityChecks:
    """Validates agent specificity and role clarity."""

    WEIGHT = 0.20  # 20% of overall score

    GENERIC_PHRASES = [
        "helpful assistant",
        "best practices",
        "industry standards",
        "high quality",
        "efficient",
        "robust",
        "scalable",
        "maintainable",
        "well-structured"
    ]

    TECHNOLOGY_KEYWORDS = [
        # Languages
        "python", "javascript", "typescript", "java", "c#", "go", "rust", "ruby", "php",
        # Frameworks
        "react", "vue", "angular", "django", "flask", "fastapi", "spring", "express",
        ".net", "rails", "laravel",
        # Tools
        "docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions",
        "pytest", "jest", "junit", "mocha", "vitest",
        # Databases
        "postgresql", "mysql", "mongodb", "redis", "dynamodb", "sqlite"
    ]

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all specificity checks."""
        return {
            'generic_language': self._check_generic_language(content),
            'role_clarity': self._check_role_clarity(content),
            'tech_specificity': self._check_tech_specificity(content)
        }

    def _check_generic_language(self, content: str) -> CheckResult:
        """Detect generic/vague language."""
        content_lower = content.lower()

        # Count generic phrases
        generic_count = sum(
            content_lower.count(phrase)
            for phrase in self.GENERIC_PHRASES
        )

        # Calculate density (per 1000 words)
        word_count = len(content.split())
        generic_density = (generic_count / word_count * 1000) if word_count > 0 else 0

        if generic_density < 2:
            score = 10.0
            status = "pass"
            message = f"Low generic language density: {generic_density:.1f} per 1000 words"
            suggestion = None
        elif generic_density < 5:
            score = 7.0
            status = "warn"
            message = f"Moderate generic language: {generic_density:.1f} per 1000 words (target: <2)"
            suggestion = "Replace generic phrases with specific, actionable language"
        else:
            score = 3.0
            status = "fail"
            message = f"High generic language: {generic_density:.1f} per 1000 words (target: <2)"
            suggestion = "Remove vague phrases like 'best practices' and be specific"

        return CheckResult(
            name="Generic Language",
            measured_value=generic_density,
            threshold=2.0,
            score=score,
            weight=0.30,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )

    def _check_role_clarity(self, content: str) -> CheckResult:
        """Check if role name matches description."""
        lines = content.split('\n')

        # Extract name from frontmatter
        name = None
        in_frontmatter = False
        for line in lines:
            if line.strip() == '---':
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter and line.startswith('name:'):
                name = line.split(':', 1)[1].strip()
                break

        if not name:
            return CheckResult(
                name="Role Clarity",
                measured_value="no name",
                threshold="name matches role",
                score=0.0,
                weight=0.35,
                status="fail",
                message="Agent name not found in frontmatter",
                line_number=None,
                suggestion="Add 'name' field to frontmatter"
            )

        # Check if name components appear in content
        name_parts = re.split(r'[-_\s]+', name.lower())
        content_lower = content.lower()

        # Count how many name parts appear in first 100 lines
        first_100_lines = '\n'.join(lines[:100]).lower()
        matches = sum(1 for part in name_parts if part in first_100_lines and len(part) > 2)

        if matches >= len(name_parts) * 0.7:  # 70% of name parts mentioned
            score = 10.0
            status = "pass"
            message = "Role name clearly reflected in description"
            suggestion = None
        elif matches >= len(name_parts) * 0.5:
            score = 6.0
            status = "warn"
            message = "Role name partially reflected in description"
            suggestion = "Ensure agent description clearly explains its role"
        else:
            score = 3.0
            status = "fail"
            message = "Role name poorly reflected in description"
            suggestion = f"Explain what '{name}' does in the first 100 lines"

        return CheckResult(
            name="Role Clarity",
            measured_value=matches,
            threshold=len(name_parts),
            score=score,
            weight=0.35,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )

    def _check_tech_specificity(self, content: str) -> CheckResult:
        """Check for specific technology mentions."""
        content_lower = content.lower()

        # Count specific technology mentions
        tech_mentions = sum(
            1 for keyword in self.TECHNOLOGY_KEYWORDS
            if keyword in content_lower
        )

        if tech_mentions >= 5:
            score = 10.0
            status = "pass"
            message = f"Good tech specificity: {tech_mentions} technologies mentioned"
            suggestion = None
        elif tech_mentions >= 3:
            score = 7.0
            status = "warn"
            message = f"Moderate tech specificity: {tech_mentions} technologies (target: ≥5)"
            suggestion = "Add more specific technology references"
        else:
            score = 4.0
            status = "warn"
            message = f"Low tech specificity: {tech_mentions} technologies (target: ≥5)"
            suggestion = "Specify exact technologies, tools, and frameworks agent works with"

        return CheckResult(
            name="Technology Specificity",
            measured_value=tech_mentions,
            threshold=5,
            score=score,
            weight=0.35,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )
