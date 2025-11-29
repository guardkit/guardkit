"""
Agent Formatting Validator

Validates that formatting changes preserve content and improve quality.
"""

from dataclasses import dataclass
from typing import Optional
import re

from .parser import AgentStructure, parse_agent
from .metrics import QualityMetrics, calculate_metrics


@dataclass
class ValidationResult:
    """Result of validating formatting changes."""

    success: bool
    issues: list[str]
    metrics_before: QualityMetrics
    metrics_after: QualityMetrics


class FormatValidator:
    """Validates formatting changes for safety and quality improvement."""

    def validate(
        self, original: AgentStructure, formatted_content: str
    ) -> ValidationResult:
        """
        Validate formatting changes.

        Args:
            original: Original parsed agent structure
            formatted_content: Formatted markdown content

        Returns:
            ValidationResult with success status and any issues
        """
        issues = []

        # Check content preservation
        if not self._content_preserved(original.raw_content, formatted_content):
            issues.append("CRITICAL: Original content was lost during formatting")

        # Calculate metrics
        original_metrics = calculate_metrics(original)

        # Parse formatted content (we need to write it temporarily or parse from string)
        # For now, let's extract metrics from formatted content directly
        formatted_metrics = self._calculate_formatted_metrics(formatted_content, original)

        # Check metrics improved
        if formatted_metrics.get_status() == original_metrics.get_status():
            if formatted_metrics.get_status() == "FAIL":
                issues.append("WARNING: Quality status did not improve (still FAIL)")

        # Check for regressions
        if formatted_metrics.get_status() == "FAIL" and original_metrics.get_status() != "FAIL":
            issues.append("CRITICAL: Quality status regressed to FAIL")

        return ValidationResult(
            success=len([i for i in issues if 'CRITICAL' in i]) == 0,
            issues=issues,
            metrics_before=original_metrics,
            metrics_after=formatted_metrics,
        )

    def _content_preserved(self, original: str, formatted: str) -> bool:
        """
        Check that original content is preserved in formatted version.

        Allows added markers and reorganization, but no removal of original content.
        """
        # Extract meaningful content (ignore whitespace, markers, comments)
        original_content = self._extract_content(original)
        formatted_content = self._extract_content(formatted)

        # Check if all original content exists in formatted version
        # Allow for reordering by checking each original block exists somewhere
        original_blocks = original_content.split('\n\n')

        for block in original_blocks:
            block = block.strip()
            if not block:
                continue

            # Skip frontmatter
            if block.startswith('---'):
                continue

            # Check block exists in formatted content
            # Allow for minor whitespace differences
            block_normalized = ' '.join(block.split())
            formatted_normalized = ' '.join(formatted_content.split())

            if block_normalized not in formatted_normalized:
                # Allow for moved content with reference comments
                if not any(
                    marker in block
                    for marker in ['[NEEDS_CONTENT', '<!-- Example moved']
                ):
                    return False

        return True

    def _extract_content(self, markdown: str) -> str:
        """
        Extract meaningful content from markdown.

        Removes:
        - Excess whitespace
        - [NEEDS_CONTENT] markers (new additions)
        - <!-- moved --> comments (new additions)
        """
        # Remove [NEEDS_CONTENT] markers
        content = re.sub(r'\[NEEDS_CONTENT:.*?\]', '', markdown)

        # Remove movement comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

        # Normalize whitespace
        content = '\n'.join(line.strip() for line in content.split('\n'))

        return content

    def _calculate_formatted_metrics(
        self, formatted_content: str, original: AgentStructure
    ) -> QualityMetrics:
        """
        Calculate metrics for formatted content.

        Since we can't easily parse without writing to file,
        we'll create a temporary AgentStructure-like object.
        """
        from .parser import extract_frontmatter, find_sections, find_code_blocks

        # Extract components
        frontmatter, frontmatter_end = extract_frontmatter(formatted_content)
        sections = find_sections(formatted_content, frontmatter_end)
        code_blocks = find_code_blocks(formatted_content, frontmatter_end)

        # Create temporary structure
        formatted_agent = AgentStructure(
            frontmatter=frontmatter,
            sections=sections,
            code_blocks=code_blocks,
            raw_content=formatted_content,
            frontmatter_end_line=frontmatter_end,
        )

        # Calculate metrics
        return calculate_metrics(formatted_agent)
