"""Boundary clarity validation checks."""

import re
from typing import Dict, List, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class BoundaryChecks:
    """Validates boundary clarity (ALWAYS/NEVER/ASK sections)."""

    WEIGHT = 0.20  # 20% of overall score

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all boundary checks."""
        return {
            'always_section': self._check_always_section(content),
            'never_section': self._check_never_section(content),
            'ask_section': self._check_ask_section(content)
        }

    def _find_section_content(
        self,
        content: str,
        section_pattern: str
    ) -> Tuple[bool, int, List[str]]:
        """
        Find section and extract its bullet points.

        Args:
            content: File content
            section_pattern: Regex pattern for section header

        Returns:
            (found, line_number, bullet_points)
        """
        lines = content.split('\n')

        section_found = False
        section_line = None
        bullet_points = []

        for i, line in enumerate(lines):
            # Check if this is the section header
            if re.match(section_pattern, line, re.IGNORECASE):
                section_found = True
                section_line = i + 1  # 1-indexed
                continue

            # If we found the section, collect bullet points until next section
            if section_found:
                # Stop at next major section (## or higher)
                if re.match(r'^##+\s', line):
                    break

                # Collect bullet points
                if re.match(r'^\s*[-*]\s+', line):
                    bullet_points.append(line.strip())

        return section_found, section_line, bullet_points

    def _check_always_section(self, content: str) -> CheckResult:
        """Check ALWAYS section presence and content."""
        found, line_num, bullets = self._find_section_content(
            content,
            r'^##\s+ALWAYS'
        )

        if not found:
            return CheckResult(
                name="ALWAYS Section",
                measured_value=0,
                threshold=(5, 7),
                score=0.0,
                weight=0.35,
                status="fail",
                message="ALWAYS section not found",
                line_number=None,
                suggestion="Add ALWAYS section with 5-7 clear rules about what agent must always do"
            )

        rule_count = len(bullets)

        if 5 <= rule_count <= 7:
            score = 10.0
            status = "pass"
            message = f"ALWAYS section has {rule_count} rules (target: 5-7)"
            suggestion = None
        elif 3 <= rule_count < 5:
            score = 6.0
            status = "warn"
            message = f"ALWAYS section has only {rule_count} rules (target: 5-7)"
            suggestion = f"Add {5 - rule_count} more ALWAYS rules"
        elif rule_count > 7:
            score = 7.0
            status = "warn"
            message = f"ALWAYS section has {rule_count} rules (target: 5-7, may be too many)"
            suggestion = "Consider consolidating or moving some rules to other sections"
        else:
            score = 3.0
            status = "fail"
            message = f"ALWAYS section has only {rule_count} rules (needs at least 5)"
            suggestion = f"Add {5 - rule_count} more ALWAYS rules"

        return CheckResult(
            name="ALWAYS Section",
            measured_value=rule_count,
            threshold=(5, 7),
            score=score,
            weight=0.35,
            status=status,
            message=message,
            line_number=line_num,
            suggestion=suggestion
        )

    def _check_never_section(self, content: str) -> CheckResult:
        """Check NEVER section presence and content."""
        found, line_num, bullets = self._find_section_content(
            content,
            r'^##\s+NEVER'
        )

        if not found:
            return CheckResult(
                name="NEVER Section",
                measured_value=0,
                threshold=(5, 7),
                score=0.0,
                weight=0.35,
                status="fail",
                message="NEVER section not found",
                line_number=None,
                suggestion="Add NEVER section with 5-7 clear rules about what agent must never do"
            )

        rule_count = len(bullets)

        if 5 <= rule_count <= 7:
            score = 10.0
            status = "pass"
            message = f"NEVER section has {rule_count} rules (target: 5-7)"
            suggestion = None
        elif 3 <= rule_count < 5:
            score = 6.0
            status = "warn"
            message = f"NEVER section has only {rule_count} rules (target: 5-7)"
            suggestion = f"Add {5 - rule_count} more NEVER rules"
        elif rule_count > 7:
            score = 7.0
            status = "warn"
            message = f"NEVER section has {rule_count} rules (target: 5-7, may be too many)"
            suggestion = "Consider consolidating or moving some rules to other sections"
        else:
            score = 3.0
            status = "fail"
            message = f"NEVER section has only {rule_count} rules (needs at least 5)"
            suggestion = f"Add {5 - rule_count} more NEVER rules"

        return CheckResult(
            name="NEVER Section",
            measured_value=rule_count,
            threshold=(5, 7),
            score=score,
            weight=0.35,
            status=status,
            message=message,
            line_number=line_num,
            suggestion=suggestion
        )

    def _check_ask_section(self, content: str) -> CheckResult:
        """Check When to Ask/ASK section presence and content."""
        # Try multiple patterns
        patterns = [
            r'^##\s+When to Ask',
            r'^##\s+ASK',
            r'^##\s+When to Ask for Help'
        ]

        found = False
        line_num = None
        bullets = []

        for pattern in patterns:
            found, line_num, bullets = self._find_section_content(content, pattern)
            if found:
                break

        if not found:
            return CheckResult(
                name="ASK Section",
                measured_value=0,
                threshold=(3, 5),
                score=0.0,
                weight=0.30,
                status="fail",
                message="ASK/When to Ask section not found",
                line_number=None,
                suggestion="Add 'When to Ask' section with 3-5 scenarios requiring human input"
            )

        scenario_count = len(bullets)

        if 3 <= scenario_count <= 5:
            score = 10.0
            status = "pass"
            message = f"ASK section has {scenario_count} scenarios (target: 3-5)"
            suggestion = None
        elif scenario_count < 3:
            score = 5.0
            status = "warn"
            message = f"ASK section has only {scenario_count} scenarios (target: 3-5)"
            suggestion = f"Add {3 - scenario_count} more scenarios requiring human input"
        else:
            score = 7.0
            status = "warn"
            message = f"ASK section has {scenario_count} scenarios (target: 3-5, may be too many)"
            suggestion = "Consider consolidating scenarios"

        return CheckResult(
            name="ASK Section",
            measured_value=scenario_count,
            threshold=(3, 5),
            score=score,
            weight=0.30,
            status=status,
            message=message,
            line_number=line_num,
            suggestion=suggestion
        )
