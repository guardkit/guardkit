"""Structure validation checks."""

import re
import yaml
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CheckResult


class StructureChecks:
    """Validates agent file structure and organization."""

    WEIGHT = 0.15  # 15% of overall score

    REQUIRED_FRONTMATTER_FIELDS = ['name', 'summary', 'category']
    EXPECTED_SECTIONS = [
        'Purpose', 'Core Responsibilities', 'ALWAYS', 'NEVER',
        'When to Ask', 'Examples', 'Integration Points'
    ]

    def run(self, content: str) -> Dict[str, CheckResult]:
        """Run all structure checks."""
        return {
            'frontmatter': self._check_frontmatter(content),
            'early_actionability': self._check_early_actionability(content),
            'file_length': self._check_file_length(content),
            'section_order': self._check_section_order(content)
        }

    def _check_frontmatter(self, content: str) -> CheckResult:
        """Validate YAML frontmatter."""
        lines = content.split('\n')

        # Extract frontmatter
        if not lines or lines[0].strip() != '---':
            return CheckResult(
                name="YAML Frontmatter",
                measured_value="missing",
                threshold="valid YAML with required fields",
                score=0.0,
                weight=0.30,
                status="fail",
                message="No YAML frontmatter found",
                line_number=1,
                suggestion="Add YAML frontmatter with name, summary, and category fields"
            )

        frontmatter_lines = []
        for i, line in enumerate(lines[1:], start=2):
            if line.strip() == '---':
                break
            frontmatter_lines.append(line)

        frontmatter_text = '\n'.join(frontmatter_lines)

        try:
            frontmatter = yaml.safe_load(frontmatter_text)

            # Check required fields
            missing_fields = [
                field for field in self.REQUIRED_FRONTMATTER_FIELDS
                if field not in frontmatter
            ]

            if missing_fields:
                score = 5.0
                status = "warn"
                message = f"Missing frontmatter fields: {', '.join(missing_fields)}"
                suggestion = f"Add required fields: {', '.join(missing_fields)}"
            else:
                score = 10.0
                status = "pass"
                message = "Valid frontmatter with all required fields"
                suggestion = None

            return CheckResult(
                name="YAML Frontmatter",
                measured_value=len(frontmatter.keys()),
                threshold=len(self.REQUIRED_FRONTMATTER_FIELDS),
                score=score,
                weight=0.30,
                status=status,
                message=message,
                line_number=1,
                suggestion=suggestion
            )

        except yaml.YAMLError as e:
            return CheckResult(
                name="YAML Frontmatter",
                measured_value="invalid",
                threshold="valid YAML",
                score=0.0,
                weight=0.30,
                status="fail",
                message=f"Invalid YAML syntax: {str(e)}",
                line_number=1,
                suggestion="Fix YAML syntax errors in frontmatter"
            )

    def _check_early_actionability(self, content: str) -> CheckResult:
        """Check if first code example appears within 50 lines."""
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

        # Find first code block
        first_example_line = None
        for i, line in enumerate(lines[frontmatter_end:], start=frontmatter_end):
            if line.strip().startswith('```'):
                first_example_line = i - frontmatter_end
                break

        if first_example_line is None:
            return CheckResult(
                name="Early Actionability",
                measured_value="no examples",
                threshold=50,
                score=0.0,
                weight=0.25,
                status="fail",
                message="No code examples found",
                line_number=None,
                suggestion="Add code examples to demonstrate agent usage"
            )

        if first_example_line <= 50:
            score = 10.0
            status = "pass"
            message = f"First example at line {first_example_line} (target: ≤50)"
            suggestion = None
        elif first_example_line <= 75:
            score = 6.0
            status = "warn"
            message = f"First example at line {first_example_line} (target: ≤50)"
            suggestion = "Move examples earlier in the file for better actionability"
        else:
            score = 2.0
            status = "fail"
            message = f"First example at line {first_example_line} (target: ≤50)"
            suggestion = "Move examples much earlier in the file"

        return CheckResult(
            name="Early Actionability",
            measured_value=first_example_line,
            threshold=50,
            score=score,
            weight=0.25,
            status=status,
            message=message,
            line_number=first_example_line,
            suggestion=suggestion
        )

    def _check_file_length(self, content: str) -> CheckResult:
        """Check if file length is within target range."""
        lines = content.split('\n')
        line_count = len(lines)

        # Target: 150-300 lines, warn if >800
        if 150 <= line_count <= 300:
            score = 10.0
            status = "pass"
            message = f"File length: {line_count} lines (target: 150-300)"
            suggestion = None
        elif line_count < 150:
            score = 7.0
            status = "warn"
            message = f"File length: {line_count} lines (target: 150-300, may need more examples)"
            suggestion = "Consider adding more examples and detail"
        elif 300 < line_count <= 500:
            score = 8.0
            status = "pass"
            message = f"File length: {line_count} lines (slightly above target but acceptable)"
            suggestion = None
        elif 500 < line_count <= 800:
            score = 6.0
            status = "warn"
            message = f"File length: {line_count} lines (consider splitting into sections)"
            suggestion = "Consider refactoring into multiple focused sections"
        else:
            score = 3.0
            status = "warn"
            message = f"File length: {line_count} lines (too long, consider splitting)"
            suggestion = "Split into multiple files or reduce verbosity"

        return CheckResult(
            name="File Length",
            measured_value=line_count,
            threshold=(150, 300),
            score=score,
            weight=0.20,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )

    def _check_section_order(self, content: str) -> CheckResult:
        """Verify logical section ordering."""
        lines = content.split('\n')

        # Find section headers (## or ###)
        sections_found = []
        for i, line in enumerate(lines):
            match = re.match(r'^##\s+(.+)$', line)
            if match:
                sections_found.append((match.group(1).strip(), i))

        if not sections_found:
            return CheckResult(
                name="Section Order",
                measured_value="no sections",
                threshold="logical ordering",
                score=0.0,
                weight=0.25,
                status="fail",
                message="No section headers found",
                line_number=None,
                suggestion="Add section headers to organize content"
            )

        # Check if key sections are present
        section_names = [name for name, _ in sections_found]
        has_purpose = any('purpose' in name.lower() for name in section_names)
        has_always = any('always' in name.lower() for name in section_names)
        has_never = any('never' in name.lower() for name in section_names)
        has_examples = any('example' in name.lower() for name in section_names)

        sections_present = sum([has_purpose, has_always, has_never, has_examples])

        if sections_present >= 3:
            score = 10.0
            status = "pass"
            message = f"{sections_present}/4 key sections present"
            suggestion = None
        elif sections_present == 2:
            score = 6.0
            status = "warn"
            message = f"Only {sections_present}/4 key sections present"
            suggestion = "Add Purpose, ALWAYS, NEVER, and Examples sections"
        else:
            score = 3.0
            status = "fail"
            message = f"Only {sections_present}/4 key sections present"
            suggestion = "Add missing key sections: Purpose, ALWAYS, NEVER, Examples"

        return CheckResult(
            name="Section Order",
            measured_value=sections_present,
            threshold=4,
            score=score,
            weight=0.25,
            status=status,
            message=message,
            line_number=None,
            suggestion=suggestion
        )
