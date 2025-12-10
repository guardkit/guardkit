"""
README Generator for Feature Subfolders

Generates comprehensive README.md files for feature subfolders by extracting
key information from review reports and task metadata.

Core Capabilities:
  • Extract problem statement from review findings
  • Extract solution approach from recommendations
  • Extract scope (in/out) from review sections
  • Generate subtask summary table
  • Create links to related documents
  • Provide template-based README structure

Usage:
    from lib.readme_generator import generate_feature_readme

    readme_content = generate_feature_readme(
        feature_name="Feature Workflow Streamlining",
        feature_slug="feature-workflow-streamlining",
        review_task_id="TASK-REV-FW01",
        review_report_path=".claude/reviews/TASK-REV-FW01-review-report.md",
        subtasks=[...],
        output_path="tasks/backlog/feature-workflow-streamlining/README.md"
    )
"""

from pathlib import Path
from typing import List, Dict, Optional
import re


class ReviewReportParser:
    """Parses review reports to extract key sections."""

    def __init__(self, report_path: str):
        """
        Initialize parser with review report path.

        Args:
            report_path: Path to the review report markdown file
        """
        self.report_path = Path(report_path)
        self.content = ""
        if self.report_path.exists():
            with open(self.report_path, 'r', encoding='utf-8') as f:
                self.content = f.read()

    def extract_executive_summary(self) -> str:
        """
        Extract executive summary section.

        Returns:
            Executive summary text or empty string if not found
        """
        pattern = r'## Executive Summary\s*\n(.*?)(?=\n+##[^#]|\Z)'
        match = re.search(pattern, self.content, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            # Remove metadata lines like **Review Mode**: Architectural
            # but keep subsections (###), content paragraphs, and important bold items like **Root Cause**
            lines = summary.split('\n')
            filtered_lines = []

            for line in lines:
                stripped = line.strip()
                # Always keep subsections
                if stripped.startswith('###'):
                    filtered_lines.append(line)
                    continue

                # Skip metadata lines (**Review Mode**: value, **Depth**: value, etc.)
                # These have pattern: **word(s)**: value on the same line
                if stripped.startswith('**') and ':' in line:
                    parts = stripped.split(':', 1)
                    if len(parts) == 2 and parts[0].endswith('**'):
                        # This is metadata format - skip UNLESS it's important content
                        if not any(keep in stripped for keep in ['Root Cause', 'Severity']):
                            continue

                # Keep all other lines (including empty lines for formatting)
                filtered_lines.append(line)

            return '\n'.join(filtered_lines).strip()
        return ""

    def extract_key_findings(self) -> str:
        """
        Extract key findings from executive summary.

        Returns:
            Key findings text or empty string if not found
        """
        pattern = r'### Key Findings\s*\n(.*?)(?=\n###|\n##|\Z)'
        match = re.search(pattern, self.content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def extract_problem_statement(self) -> str:
        """
        Extract problem statement from findings or root cause sections.

        Returns:
            Problem statement text or empty string if not found
        """
        # Look for root cause or problem-related sections
        patterns = [
            r'### Critical Gaps Identified\s*\n(.*?)(?=\n##|\Z)',
            r'### Problem Analysis\s*\n(.*?)(?=\n##|\Z)',
            r'\*\*Root Cause\*\*:\s*(.*?)(?=\n\n\*\*|###|\n##)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Fallback to key findings if no specific problem section found
        return self.extract_key_findings()

    def extract_recommendations(self) -> str:
        """
        Extract recommendations or solution approach.

        Returns:
            Recommendations text or empty string if not found
        """
        patterns = [
            r'## Recommendations\s*\n(.*?)(?=\n##|\Z)',
            r'### Recommendations\s*\n(.*?)(?=\n##|\Z)',
            r'## Solution\s*\n(.*?)(?=\n##|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.content, re.DOTALL)
            if match:
                return match.group(1).strip()

        return ""

    def extract_scope(self) -> tuple[str, str]:
        """
        Extract in-scope and out-of-scope sections.

        Returns:
            Tuple of (in_scope, out_of_scope) strings
        """
        in_scope = ""
        out_of_scope = ""

        # Look for explicit scope sections
        in_scope_pattern = r'### In Scope\s*\n(.*?)(?=\n###|\n##|\Z)'
        out_scope_pattern = r'### Out of Scope\s*\n(.*?)(?=\n###|\n##|\Z)'

        in_match = re.search(in_scope_pattern, self.content, re.DOTALL)
        out_match = re.search(out_scope_pattern, self.content, re.DOTALL)

        if in_match:
            in_scope = in_match.group(1).strip()
        if out_match:
            out_of_scope = out_match.group(1).strip()

        return in_scope, out_of_scope

    def extract_success_criteria(self) -> str:
        """
        Extract success criteria if present.

        Returns:
            Success criteria text or empty string if not found
        """
        patterns = [
            r'## Success Criteria\s*\n(.*?)(?=\n##|\Z)',
            r'### Success Criteria\s*\n(.*?)(?=\n##|\Z)',
            r'## Acceptance Criteria\s*\n(.*?)(?=\n##|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.content, re.DOTALL)
            if match:
                return match.group(1).strip()

        return ""


class ReadmeGenerator:
    """Generates README.md files for feature subfolders."""

    def __init__(self):
        """Initialize README generator."""
        pass

    def generate_subtask_table(self, subtasks: List[Dict]) -> str:
        """
        Generate markdown table of subtasks.

        Args:
            subtasks: List of subtask dicts with keys: id, title, method, status

        Returns:
            Markdown table string
        """
        if not subtasks:
            return "No subtasks defined yet."

        table = "| ID | Title | Method | Status |\n"
        table += "|----|-------|--------|--------|\n"

        for task in subtasks:
            task_id = task.get('id', 'N/A')
            title = task.get('title', 'Untitled')
            method = task.get('method', task.get('implementation_mode', 'direct'))
            status = task.get('status', 'backlog')
            table += f"| {task_id} | {title} | {method} | {status} |\n"

        return table

    def generate_readme(
        self,
        feature_name: str,
        feature_slug: str,
        review_task_id: str,
        review_report_path: str,
        subtasks: List[Dict],
        related_docs: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate README content for a feature subfolder.

        Args:
            feature_name: Human-readable feature name
            feature_slug: URL-safe feature slug (for folder name)
            review_task_id: ID of the parent review task
            review_report_path: Path to the review report file
            subtasks: List of subtask dictionaries
            related_docs: Optional list of related document dicts with 'title' and 'path'

        Returns:
            Complete README markdown content
        """
        # Parse review report
        parser = ReviewReportParser(review_report_path)

        # Extract sections
        overview = parser.extract_executive_summary()
        problem = parser.extract_problem_statement()
        solution = parser.extract_recommendations()
        in_scope, out_scope = parser.extract_scope()
        success_criteria = parser.extract_success_criteria()

        # Build README content
        readme = f"""# Feature: {feature_name}

## Overview

{overview if overview else f"This feature addresses improvements identified in the {review_task_id} review."}

**Parent Review**: [{review_task_id}](../{review_task_id}.md)
**Review Report**: [{review_task_id}-review-report.md]({review_report_path})

## Problem Statement

{problem if problem else "Problem statement to be extracted from review findings."}

## Solution

{solution if solution else "Solution approach to be extracted from review recommendations."}

## Scope

### In Scope
{in_scope if in_scope else "- To be defined based on review recommendations"}

### Out of Scope
{out_scope if out_scope else "- To be defined based on review analysis"}

## Success Criteria

{success_criteria if success_criteria else "Success criteria to be defined based on review findings."}

## Subtasks

{self.generate_subtask_table(subtasks)}

## Related Documents

"""

        # Add related documents
        if related_docs:
            for doc in related_docs:
                title = doc.get('title', 'Untitled')
                path = doc.get('path', '#')
                readme += f"- [{title}]({path})\n"
        else:
            readme += "- Review report (linked above)\n"
            readme += f"- Parent review task [{review_task_id}](../{review_task_id}.md)\n"

        return readme


def generate_feature_readme(
    feature_name: str,
    feature_slug: str,
    review_task_id: str,
    review_report_path: str,
    subtasks: List[Dict],
    output_path: str,
    related_docs: Optional[List[Dict]] = None
) -> str:
    """
    Generate and write README.md for a feature subfolder.

    Args:
        feature_name: Human-readable feature name
        feature_slug: URL-safe feature slug (for folder name)
        review_task_id: ID of the parent review task
        review_report_path: Path to the review report file
        subtasks: List of subtask dictionaries with id, title, method, status
        output_path: Path where README.md should be written
        related_docs: Optional list of related document dicts

    Returns:
        Generated README content (also written to output_path)

    Example:
        >>> subtasks = [
        ...     {'id': 'TASK-FW-001', 'title': 'Create feature plan', 'method': 'direct', 'status': 'backlog'},
        ...     {'id': 'TASK-FW-002', 'title': 'Auto-detect feature slug', 'method': 'direct', 'status': 'backlog'}
        ... ]
        >>> readme = generate_feature_readme(
        ...     feature_name="Feature Workflow Streamlining",
        ...     feature_slug="feature-workflow-streamlining",
        ...     review_task_id="TASK-REV-FW01",
        ...     review_report_path=".claude/reviews/TASK-REV-FW01-review-report.md",
        ...     subtasks=subtasks,
        ...     output_path="tasks/backlog/feature-workflow-streamlining/README.md"
        ... )
    """
    generator = ReadmeGenerator()

    # Generate README content
    readme_content = generator.generate_readme(
        feature_name=feature_name,
        feature_slug=feature_slug,
        review_task_id=review_task_id,
        review_report_path=review_report_path,
        subtasks=subtasks,
        related_docs=related_docs
    )

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    return readme_content
