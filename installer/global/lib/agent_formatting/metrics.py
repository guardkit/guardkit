"""
Agent Quality Metrics Calculator

Calculates quality metrics for agent markdown files based on GitHub best practices.
"""

from dataclasses import dataclass
from typing import Optional

from .parser import AgentStructure


@dataclass
class QualityMetrics:
    """Quality metrics for an agent markdown file."""

    time_to_first_example: int  # Line number from frontmatter end (-1 if no examples)
    example_density: float  # Percentage of content that is code
    boundary_sections: dict[str, bool]  # ALWAYS/NEVER/ASK presence
    commands_first: int  # Line number of first command example (-1 if none)
    code_to_text_ratio: float  # Ratio of code blocks to prose paragraphs
    specificity_score: int  # 0-10 score for role definition clarity

    def passes_threshold(self) -> bool:
        """Check if all CRITICAL thresholds are met."""
        return (
            self.time_to_first_example < 50
            and self.example_density >= 30  # WARN at 30, PASS at 40
            and all(self.boundary_sections.values())
            and self.commands_first < 50
            and self.code_to_text_ratio >= 0.8  # WARN at 0.8, PASS at 1.0
            and self.specificity_score >= 8
        )

    def get_status(self) -> str:
        """
        Return overall quality status.

        Returns:
            "PASS", "WARN", or "FAIL"
        """
        # Critical failures
        critical_fail = (
            self.time_to_first_example >= 50
            or self.time_to_first_example == -1
            or self.example_density < 30
            or not all(self.boundary_sections.values())
            or self.commands_first >= 50
            or self.commands_first == -1
            or self.specificity_score < 8
        )

        if critical_fail:
            return "FAIL"

        # Warning conditions
        warning = (
            30 <= self.example_density < 40 or 0.8 <= self.code_to_text_ratio < 1.0
        )

        return "WARN" if warning else "PASS"


def check_time_to_first_example(agent: AgentStructure) -> int:
    """
    Calculate line number of first code example after frontmatter.

    Args:
        agent: Parsed agent structure

    Returns:
        Line number relative to frontmatter end, or -1 if no examples found
    """
    if not agent.code_blocks:
        return -1

    # Find first code block
    first_block = min(agent.code_blocks, key=lambda b: b.start_line)

    # Return line number relative to frontmatter end
    return first_block.start_line - agent.frontmatter_end_line


def calculate_example_density(agent: AgentStructure) -> float:
    """
    Calculate percentage of content that is executable code.

    Args:
        agent: Parsed agent structure

    Returns:
        Percentage (0-100) of content that is code
    """
    lines = agent.raw_content.split('\n')

    # Count content lines (after frontmatter, non-empty)
    content_lines = [
        line
        for i, line in enumerate(lines)
        if i >= agent.frontmatter_end_line and line.strip()
    ]

    if not content_lines:
        return 0.0

    # Count code lines
    code_lines = 0
    for block in agent.code_blocks:
        # Count non-empty lines in code block
        block_lines = [line for line in block.content.split('\n') if line.strip()]
        code_lines += len(block_lines)

    total_lines = len(content_lines)
    return (code_lines / total_lines * 100) if total_lines > 0 else 0.0


def check_boundary_sections(agent: AgentStructure) -> dict[str, bool]:
    """
    Check for presence of ALWAYS/NEVER/ASK boundary sections.

    Args:
        agent: Parsed agent structure

    Returns:
        Dict with keys 'ALWAYS', 'NEVER', 'ASK' and boolean values
    """
    content_upper = agent.raw_content.upper()

    return {
        'ALWAYS': '### ALWAYS' in content_upper or '## ALWAYS' in content_upper,
        'NEVER': '### NEVER' in content_upper or '## NEVER' in content_upper,
        'ASK': '### ASK' in content_upper or '## ASK' in content_upper,
    }


def check_commands_first(agent: AgentStructure) -> int:
    """
    Find line number of first bash/shell command example.

    Args:
        agent: Parsed agent structure

    Returns:
        Line number relative to frontmatter end, or -1 if no commands found
    """
    # Look for bash or shell code blocks
    command_blocks = [
        block
        for block in agent.code_blocks
        if block.language.lower() in ['bash', 'shell', 'sh']
    ]

    if not command_blocks:
        return -1

    # Find first command block
    first_command = min(command_blocks, key=lambda b: b.start_line)

    # Return line number relative to frontmatter end
    return first_command.start_line - agent.frontmatter_end_line


def calculate_code_to_text_ratio(agent: AgentStructure) -> float:
    """
    Calculate ratio of code blocks to prose paragraphs.

    Args:
        agent: Parsed agent structure

    Returns:
        Ratio (code blocks : paragraphs)
    """
    lines = agent.raw_content.split('\n')

    # Count code blocks
    code_block_count = len(agent.code_blocks)

    # Count paragraphs (non-empty, non-heading, non-list, non-code lines)
    paragraphs = 0
    in_paragraph = False
    in_code_block = False

    for i in range(agent.frontmatter_end_line, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            in_paragraph = False
            continue

        # Skip lines inside code blocks
        if in_code_block:
            continue

        # Check if this is a paragraph line
        is_paragraph_line = (
            stripped
            and not stripped.startswith('#')
            and not stripped.startswith('-')
            and not stripped.startswith('*')
            and not stripped.startswith('>')
            and not stripped.startswith('|')
        )

        if is_paragraph_line:
            if not in_paragraph:
                paragraphs += 1
                in_paragraph = True
        else:
            in_paragraph = False

    return code_block_count / paragraphs if paragraphs > 0 else 0.0


def calculate_specificity_score(agent: AgentStructure) -> int:
    """
    Calculate specificity score based on role definition clarity.

    Args:
        agent: Parsed agent structure

    Returns:
        Score from 0-10
    """
    frontmatter = agent.frontmatter
    description = frontmatter.get('description', '').lower()

    score = 0

    # Tech stack mentioned (+4 points)
    tech_keywords = [
        'react',
        'typescript',
        'python',
        'fastapi',
        'go',
        'rust',
        '.net',
        'java',
        'c#',
        'javascript',
    ]
    if any(tech in description for tech in tech_keywords):
        score += 4

    # Domain mentioned (+3 points)
    domain_keywords = [
        'testing',
        'security',
        'performance',
        'architecture',
        'database',
        'api',
        'ui',
        'frontend',
        'backend',
    ]
    if any(domain in description for domain in domain_keywords):
        score += 3

    # Standards mentioned (+3 points)
    standard_keywords = ['solid', 'dry', 'yagni', 'tdd', 'bdd', 'wcag', 'owasp']
    if any(std in description for std in standard_keywords):
        score += 3

    return min(score, 10)


def calculate_metrics(agent: AgentStructure) -> QualityMetrics:
    """
    Calculate all quality metrics for an agent.

    Args:
        agent: Parsed agent structure

    Returns:
        QualityMetrics object with all calculated metrics
    """
    return QualityMetrics(
        time_to_first_example=check_time_to_first_example(agent),
        example_density=calculate_example_density(agent),
        boundary_sections=check_boundary_sections(agent),
        commands_first=check_commands_first(agent),
        code_to_text_ratio=calculate_code_to_text_ratio(agent),
        specificity_score=calculate_specificity_score(agent),
    )
