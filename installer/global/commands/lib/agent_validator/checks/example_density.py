"""Example density validation checks."""

import re
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class ExampleDensityChecks:
    """Validates code example density and quality."""

    WEIGHT = 0.25  # 25% of overall score

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all example density checks."""
        return {
            'code_percentage': self._check_code_percentage(content),
            'example_count': self._check_example_count(content),
            'example_format': self._check_example_format(content)
        }

    def _check_code_percentage(self, content: str) -> CheckResult:
        """Check percentage of content that is code examples."""
        lines = content.split('\n')

        # Find frontmatter end
        frontmatter_end = 0
        dash_count = 0
        for i, line in enumerate(lines):
            if line.strip() == '---':
                dash_count += 1
                if dash_count == 2:
                    frontmatter_end = i
                    break

        # Count code lines vs total
        total_lines = len([l for l in lines[frontmatter_end:] if l.strip()])
        code_lines = 0
        in_code_block = False

        for line in lines[frontmatter_end:]:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            elif in_code_block:
                code_lines += 1

        percentage = (code_lines / total_lines * 100) if total_lines > 0 else 0

        # Score based on percentage
        if 45 <= percentage <= 50:
            score = 10.0
        elif 40 <= percentage < 45:
            score = 8.0
        elif 35 <= percentage < 40:
            score = 6.0
        elif 30 <= percentage < 35:
            score = 4.0
        else:
            score = 0.0 if percentage < 30 else 2.0

        return CheckResult(
            name="Code Block Percentage",
            measured_value=percentage,
            threshold=(40, 50),
            score=score,
            weight=0.50,  # 50% of example_density category
            status="pass" if percentage >= 40 else "fail" if percentage < 30 else "warn",
            message=f"Code examples: {percentage:.1f}% of content (target: 40-50%)",
            line_number=None,
            suggestion=f"Add {int((40 - percentage) / 100 * total_lines)} more lines of code examples" if percentage < 40 else None
        )

    def _check_example_count(self, content: str) -> CheckResult:
        """Check number of code examples."""
        example_count = content.count('```') // 2

        # Score based on count
        if example_count >= 15:
            score = 10.0
        elif example_count >= 12:
            score = 8.0
        elif example_count >= 10:
            score = 6.0
        elif example_count >= 8:
            score = 4.0
        else:
            score = 0.0

        return CheckResult(
            name="Example Count",
            measured_value=example_count,
            threshold=10,
            score=score,
            weight=0.30,  # 30% of example_density category
            status="pass" if example_count >= 10 else "warn" if example_count >= 8 else "fail",
            message=f"{example_count} code examples found (target: ≥10)",
            line_number=None,
            suggestion=f"Add {10 - example_count} more code examples" if example_count < 10 else None
        )

    def _check_example_format(self, content: str) -> CheckResult:
        """Check if examples use ✅ DO / ❌ DON'T format."""
        do_count = content.count('✅ DO')
        dont_count = content.count('❌ DON')

        formatted_examples = min(do_count, dont_count) * 2
        total_examples = content.count('```') // 2

        percentage = (formatted_examples / total_examples * 100) if total_examples > 0 else 0

        # Score based on percentage
        if percentage >= 80:
            score = 10.0
        elif percentage >= 60:
            score = 8.0
        elif percentage >= 40:
            score = 6.0
        elif percentage >= 20:
            score = 4.0
        else:
            score = 0.0

        return CheckResult(
            name="Example Format (DO/DON'T)",
            measured_value=percentage,
            threshold=60,
            score=score,
            weight=0.20,  # 20% of example_density category
            status="pass" if percentage >= 60 else "warn",
            message=f"{percentage:.0f}% of examples use ✅/❌ format (target: ≥60%)",
            line_number=None,
            suggestion="Convert plain code examples to ✅ DO / ❌ DON'T comparison format" if percentage < 60 else None
        )
