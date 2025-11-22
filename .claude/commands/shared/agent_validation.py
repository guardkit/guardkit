"""
Shared validation logic for agent content quality.

Used by:
- agent-content-enhancer.md (during enhancement)
- /agent-validate command (standalone validation)

Based on GitHub best practices analysis of 2,500+ repositories.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class CheckResult:
    """Result of individual quality check."""
    name: str
    measured_value: any
    threshold: any
    status: str  # "PASS" | "WARN" | "FAIL"
    message: str


@dataclass
class ValidationReport:
    """Complete validation report."""
    checks: Dict[str, CheckResult]
    overall_status: str  # "PASSED" | "FAILED"
    warnings: List[str]
    iterations_required: int = 1


def validate_enhanced_content(content: str) -> ValidationReport:
    """
    Validates agent content against GitHub best practices.

    Args:
        content: Full agent file content (including YAML frontmatter)

    Returns:
        ValidationReport with all check results
    """
    lines = content.split('\n')

    # Find frontmatter end
    frontmatter_end = _find_frontmatter_end(lines)

    # Run all checks
    checks = {}
    warnings = []

    # Check 1: Time to first example
    first_example_line = _find_first_code_block(lines, frontmatter_end)
    checks['time_to_first_example'] = CheckResult(
        name="Time to First Example",
        measured_value=first_example_line,
        threshold=50,
        status="PASS" if first_example_line <= 50 else "FAIL",
        message=f"First example at line {first_example_line} (target: ≤50)"
    )

    # Check 2: Example density
    density = _calculate_example_density(content, frontmatter_end)
    checks['example_density'] = CheckResult(
        name="Example Density",
        measured_value=density,
        threshold=(40, 50),
        status="PASS" if density >= 40 else "WARN" if density >= 30 else "FAIL",
        message=f"Example density: {density:.1f}% (target: 40-50%)"
    )
    if 30 <= density < 40:
        warnings.append(f"Example density {density:.1f}% below 40% target")

    # Check 3: Boundary sections
    boundaries = _check_boundary_sections(content)
    checks['boundary_sections'] = CheckResult(
        name="Boundary Sections",
        measured_value=boundaries,
        threshold=["ALWAYS", "NEVER", "ASK"],
        status="PASS" if len(boundaries) == 3 else "FAIL",
        message=f"Boundary sections: {boundaries} (target: ALWAYS, NEVER, ASK)"
    )

    # Check 4: Commands-first
    first_command_line = _find_first_command(lines, frontmatter_end)
    checks['commands_first'] = CheckResult(
        name="Commands-First",
        measured_value=first_command_line,
        threshold=50,
        status="PASS" if first_command_line <= 50 else "FAIL",
        message=f"First command at line {first_command_line} (target: ≤50)"
    )

    # Check 5: Specificity score
    role_statement = _extract_role_statement(content)
    specificity = _score_specificity(role_statement)
    checks['specificity_score'] = CheckResult(
        name="Specificity Score",
        measured_value=specificity,
        threshold=8,
        status="PASS" if specificity >= 8 else "FAIL",
        message=f"Specificity: {specificity}/10 (target: ≥8)"
    )

    # Check 6: Code-to-text ratio
    ratio = _calculate_code_to_text_ratio(content, frontmatter_end)
    checks['code_to_text_ratio'] = CheckResult(
        name="Code-to-Text Ratio",
        measured_value=ratio,
        threshold=1.0,
        status="PASS" if ratio >= 1.0 else "WARN",
        message=f"Code-to-text ratio: {ratio:.1f}:1 (target: ≥1:1)"
    )
    if ratio < 1.0:
        warnings.append(f"Code-to-text ratio {ratio:.1f}:1 below 1:1 target")

    # Determine overall status
    overall = "PASSED" if all(c.status == "PASS" for c in checks.values()) else "FAILED"

    return ValidationReport(
        checks=checks,
        overall_status=overall,
        warnings=warnings
    )


def _find_frontmatter_end(lines: List[str]) -> int:
    """Find line number where YAML frontmatter ends."""
    count = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            count += 1
            if count == 2:
                return i
    return 0


def _find_first_code_block(lines: List[str], start_line: int) -> int:
    """Find first fenced code block after frontmatter."""
    for i in range(start_line, len(lines)):
        if lines[i].strip().startswith('```'):
            return i - start_line
    return len(lines)


def _calculate_example_density(content: str, frontmatter_end: int) -> float:
    """Calculate percentage of content that is code examples."""
    lines = content.split('\n')[frontmatter_end:]
    total_lines = len([l for l in lines if l.strip()])

    # Count lines inside code blocks
    code_lines = 0
    in_code_block = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        elif in_code_block:
            code_lines += 1

    if total_lines == 0:
        return 0.0
    return (code_lines / total_lines) * 100


def _check_boundary_sections(content: str) -> List[str]:
    """Check which boundary sections are present."""
    sections = []
    if re.search(r'###?\s+ALWAYS', content, re.IGNORECASE):
        sections.append("ALWAYS")
    if re.search(r'###?\s+NEVER', content, re.IGNORECASE):
        sections.append("NEVER")
    if re.search(r'###?\s+ASK', content, re.IGNORECASE):
        sections.append("ASK")
    return sections


def _find_first_command(lines: List[str], start_line: int) -> int:
    """Find first command example (bash/shell code block)."""
    in_bash_block = False
    for i in range(start_line, len(lines)):
        if lines[i].strip().startswith('```bash') or lines[i].strip().startswith('```shell'):
            return i - start_line
    return len(lines)


def _extract_role_statement(content: str) -> str:
    """Extract role statement from first non-frontmatter heading or description."""
    lines = content.split('\n')
    frontmatter_end = _find_frontmatter_end(lines)

    # Look for first # heading or description field in frontmatter
    for line in lines[frontmatter_end:frontmatter_end + 20]:
        if line.startswith('# '):
            return line[2:].strip()
        if line.startswith('description:'):
            return line.split(':', 1)[1].strip()
    return ""


def _score_specificity(role_statement: str) -> int:
    """Score role statement specificity (0-10)."""
    score = 0

    # Check for technology mentions (React, Python, TypeScript, etc.)
    tech_keywords = ['react', 'python', 'typescript', 'javascript', 'java', 'c#', 'go', 'rust']
    if any(tech.lower() in role_statement.lower() for tech in tech_keywords):
        score += 3

    # Check for domain mentions (security, performance, testing, etc.)
    domain_keywords = ['security', 'performance', 'testing', 'review', 'audit', 'optimization']
    if any(domain.lower() in role_statement.lower() for domain in domain_keywords):
        score += 3

    # Check for standard mentions (WCAG, OWASP, SOLID, etc.)
    standard_keywords = ['wcag', 'owasp', 'solid', 'dry', 'kiss']
    if any(std.lower() in role_statement.lower() for std in standard_keywords):
        score += 2

    # Check length (10-25 words is ideal)
    word_count = len(role_statement.split())
    if 10 <= word_count <= 25:
        score += 2

    return min(score, 10)


def _calculate_code_to_text_ratio(content: str, frontmatter_end: int) -> float:
    """Calculate ratio of code blocks to prose paragraphs."""
    lines = content.split('\n')[frontmatter_end:]

    # Count code blocks
    code_block_count = content.count('```') // 2

    # Count prose paragraphs (non-empty lines that aren't headers or code)
    prose_count = 0
    in_code_block = False
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        elif not in_code_block and line.strip() and not line.startswith('#'):
            prose_count += 1

    # Approximate paragraphs (group consecutive prose lines)
    paragraph_count = max(prose_count // 3, 1)

    if paragraph_count == 0:
        return 0.0
    return code_block_count / paragraph_count
