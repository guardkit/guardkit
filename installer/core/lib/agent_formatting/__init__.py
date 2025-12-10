"""
Agent Formatting Library

Pattern-based formatting of agent markdown files according to GitHub best practices.
"""

from .parser import (
    AgentStructure,
    Section,
    CodeBlock,
    parse_agent,
    extract_frontmatter,
    find_sections,
    find_code_blocks,
)
from .metrics import (
    QualityMetrics,
    calculate_metrics,
    check_time_to_first_example,
    calculate_example_density,
    check_boundary_sections,
    check_commands_first,
    calculate_code_to_text_ratio,
    calculate_specificity_score,
)
from .transformers import AgentFormatter
from .validator import FormatValidator, ValidationResult
from .reporter import ValidationReporter

__all__ = [
    # Parser
    "AgentStructure",
    "Section",
    "CodeBlock",
    "parse_agent",
    "extract_frontmatter",
    "find_sections",
    "find_code_blocks",
    # Metrics
    "QualityMetrics",
    "calculate_metrics",
    "check_time_to_first_example",
    "calculate_example_density",
    "check_boundary_sections",
    "check_commands_first",
    "calculate_code_to_text_ratio",
    "calculate_specificity_score",
    # Transformers
    "AgentFormatter",
    # Validator
    "FormatValidator",
    "ValidationResult",
    # Reporter
    "ValidationReporter",
]
