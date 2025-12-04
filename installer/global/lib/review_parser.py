"""
Review Report Parser for Subtask Extraction

Parses review reports to automatically extract subtask definitions from recommendations.
Extends the ReviewReportParser in readme_generator.py to focus on subtask extraction.

Core Capabilities:
  • Detect recommendation sections in review reports
  • Parse various recommendation formats (numbered, bulleted, tables)
  • Extract subtask titles from recommendation text
  • Infer files to modify from recommendation context
  • Generate sequential task IDs with feature prefix
  • Handle various markdown formats gracefully

Usage:
    from lib.review_parser import extract_subtasks_from_review

    subtasks = extract_subtasks_from_review(
        review_report_path=".claude/reviews/TASK-REV-FW01-review-report.md",
        feature_slug="feature-workflow"
    )

    # Returns:
    # [
    #     {
    #         "id": "TASK-FW-001",
    #         "title": "Create /feature-plan command",
    #         "description": "...",
    #         "files": ["installer/global/commands/feature-plan.md"],
    #         "complexity": 3,
    #         "implementation_mode": None,  # Set by FW-004
    #         "parallel_group": None,  # Set by FW-005
    #     },
    #     ...
    # ]
"""

from pathlib import Path
from typing import List, Dict, Optional
import re


class SubtaskExtractor:
    """Extracts subtask definitions from review report recommendations."""

    def __init__(self, report_path: str):
        """
        Initialize extractor with review report path.

        Args:
            report_path: Path to the review report markdown file
        """
        self.report_path = Path(report_path)
        self.content = ""
        if self.report_path.exists():
            with open(self.report_path, 'r', encoding='utf-8') as f:
                self.content = f.read()

    def find_recommendations_section(self) -> Optional[str]:
        """
        Find and extract the recommendations section from the report.

        Looks for various section headers:
        - ## Recommendations
        - ## Implementation Plan
        - ## Suggested Changes
        - ## Action Items
        - ## Implementation Plan Summary (with subsections)

        Returns:
            The recommendations section content or None if not found
        """
        # Patterns to match recommendation section headers
        patterns = [
            r'## Recommendations\s*\n(.*?)(?=\n##[^#]|\Z)',
            r'## Implementation Plan Summary\s*\n(.*?)(?=\n##[^#]|\Z)',
            r'## Implementation Plan\s*\n(.*?)(?=\n##[^#]|\Z)',
            r'## Suggested Changes\s*\n(.*?)(?=\n##[^#]|\Z)',
            r'## Action Items\s*\n(.*?)(?=\n##[^#]|\Z)',
            r'### Recommendations\s*\n(.*?)(?=\n###|\n##[^#]|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.content, re.DOTALL | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    def find_phase_subtasks_table(self) -> Optional[str]:
        """
        Find and extract Phase 1 Subtasks table if present.

        Many review reports include a detailed table like:
        ### Phase 1 Subtasks (Feature Plan Command + Enhanced [I]mplement)

        | ID | Title | Method | Complexity | Effort |
        |----|-------|--------|------------|--------|
        | FW-001 | ... | Direct | 3 | 0.5d |

        Returns:
            The subtasks table section content or None if not found
        """
        # Pattern to match subtasks table
        pattern = r'### Phase \d+ Subtasks.*?\n\|(.*?)\n\n'
        match = re.search(pattern, self.content, re.DOTALL | re.MULTILINE)
        if match:
            # Return full table including header
            table_start = match.start()
            # Find table end (double newline or next section)
            table_content = self.content[table_start:]
            table_end_match = re.search(r'\n\n(?!\|)', table_content)
            if table_end_match:
                return table_content[:table_end_match.start()].strip()
            return table_content.strip()

        return None

    def parse_subtasks_from_table(self, table_content: str, feature_slug: str) -> List[Dict]:
        """
        Parse subtasks from a markdown table format.

        Expected format:
        | ID | Title | Method | Complexity | Effort |
        |----|-------|--------|------------|--------|
        | FW-001 | Create /feature-plan command | Direct | 3 | 0.5d |

        Args:
            table_content: The markdown table content
            feature_slug: Feature slug for task ID generation (e.g., "FW")

        Returns:
            List of subtask dictionaries
        """
        if not table_content:
            return []

        subtasks = []

        # Split into lines
        lines = table_content.strip().split('\n')
        if len(lines) < 3:
            return subtasks

        # Find header line (contains column names)
        header_idx = None
        separator_idx = None
        for idx, line in enumerate(lines):
            if '|' in line and ('ID' in line or 'Title' in line):
                header_idx = idx
                # Next line should be separator
                if idx + 1 < len(lines) and '---' in lines[idx + 1]:
                    separator_idx = idx + 1
                break

        # If we can't find proper header/separator, return empty
        if header_idx is None or separator_idx is None:
            return subtasks

        # Process data rows (after separator)
        for line in lines[separator_idx + 1:]:
            if not line.strip().startswith('|'):
                continue

            # Split by | and clean whitespace
            parts = [p.strip() for p in line.split('|') if p.strip()]

            if len(parts) < 3:
                continue

            # Extract fields (ID, Title, Method, Complexity, Effort)
            task_id = parts[0] if len(parts) > 0 else ""
            title = parts[1] if len(parts) > 1 else ""
            method = parts[2] if len(parts) > 2 else ""
            complexity = parts[3] if len(parts) > 3 else "5"
            effort = parts[4] if len(parts) > 4 else ""

            # Ensure ID has proper prefix
            if not task_id.startswith('TASK-'):
                task_id = f"TASK-{task_id}"

            # Extract implementation mode from method
            implementation_mode = None
            if method.lower() == 'direct':
                implementation_mode = 'direct'
            elif 'task-work' in method.lower() or '/task-work' in method.lower():
                implementation_mode = 'task-work'
            elif method.lower() == 'manual':
                implementation_mode = 'manual'

            # Try to parse complexity as int
            try:
                complexity_int = int(re.search(r'\d+', complexity).group())
            except (AttributeError, ValueError):
                complexity_int = 5

            # Extract description from title (everything before '(' or full title)
            description_match = re.match(r'([^(]+)', title)
            description = description_match.group(1).strip() if description_match else title

            subtasks.append({
                "id": task_id,
                "title": title,
                "description": description,
                "files": [],  # Will be inferred separately
                "complexity": complexity_int,
                "implementation_mode": implementation_mode,
                "parallel_group": None,  # Set by FW-005
                "effort_estimate": effort,
            })

        return subtasks

    def parse_subtasks_from_numbered_list(self, content: str, feature_slug: str) -> List[Dict]:
        """
        Parse subtasks from a numbered list format.

        Expected format:
        1. Add CSS variables for theming
        2. Create theme toggle component

        Args:
            content: The recommendations content
            feature_slug: Feature slug for task ID generation

        Returns:
            List of subtask dictionaries
        """
        subtasks = []

        # Find numbered items (1., 2., etc.)
        pattern = r'^\s*(\d+)\.\s+(.+?)(?=\n\s*\d+\.|\n\n|$)'
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

        for match in matches:
            num = int(match.group(1))
            text = match.group(2).strip()

            # Clean up text (remove excessive newlines, keep only first sentence/line)
            text = ' '.join(text.split('\n'))

            # Generate task ID
            prefix = self._extract_prefix_from_slug(feature_slug)
            task_id = f"TASK-{prefix}-{num:03d}"

            subtasks.append({
                "id": task_id,
                "title": text,
                "description": text,
                "files": self._infer_files_from_text(text),
                "complexity": 5,  # Default complexity
                "implementation_mode": None,  # Set by FW-004
                "parallel_group": None,  # Set by FW-005
            })

        return subtasks

    def parse_subtasks_from_bulleted_list(self, content: str, feature_slug: str) -> List[Dict]:
        """
        Parse subtasks from a bulleted list format.

        Expected format:
        - Add CSS variables for theming
        - Create theme toggle component

        Args:
            content: The recommendations content
            feature_slug: Feature slug for task ID generation

        Returns:
            List of subtask dictionaries
        """
        subtasks = []

        # Find bulleted items (-, *, +)
        pattern = r'^\s*[-*+]\s+(.+?)(?=\n\s*[-*+]|\n\n|$)'
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

        for idx, match in enumerate(matches, start=1):
            text = match.group(1).strip()

            # Clean up text (remove excessive newlines, keep only first sentence/line)
            text = ' '.join(text.split('\n'))

            # Generate task ID
            prefix = self._extract_prefix_from_slug(feature_slug)
            task_id = f"TASK-{prefix}-{idx:03d}"

            subtasks.append({
                "id": task_id,
                "title": text,
                "description": text,
                "files": self._infer_files_from_text(text),
                "complexity": 5,  # Default complexity
                "implementation_mode": None,  # Set by FW-004
                "parallel_group": None,  # Set by FW-005
            })

        return subtasks

    def _extract_prefix_from_slug(self, feature_slug: str) -> str:
        """
        Extract task prefix from feature slug.

        Examples:
        - "feature-workflow" -> "FW"
        - "dark-mode" -> "DM"
        - "progressive-disclosure" -> "PD"

        Args:
            feature_slug: The feature slug (e.g., "feature-workflow")

        Returns:
            Task prefix (e.g., "FW")
        """
        # Split by dash and take first letter of each word
        parts = feature_slug.split('-')
        prefix = ''.join([p[0].upper() for p in parts if p])

        # If prefix is too long (>4 chars), try to abbreviate
        if len(prefix) > 4:
            # Take first 2-4 letters intelligently
            # For "feature-workflow", we want "FW" (feature + workflow)
            # For "progressive-disclosure", we want "PD" (progressive + disclosure)
            prefix = prefix[:4]

        return prefix

    def _infer_files_from_text(self, text: str) -> List[str]:
        """
        Infer file paths from recommendation text.

        Looks for:
        - Explicit paths: src/components/Button.tsx
        - Component names: "Update the Button component"
        - Directory references: "in the styles folder"

        Args:
            text: Recommendation text

        Returns:
            List of inferred file paths
        """
        files = []

        # Pattern 1: Explicit file paths (contains / or \ and file extension)
        path_pattern = r'[a-zA-Z0-9_.-]+(?:[/\\][a-zA-Z0-9_.-]+)+\.[a-zA-Z]{2,4}'
        path_matches = re.findall(path_pattern, text)
        files.extend(path_matches)

        # Pattern 2: Component names (e.g., "Button component")
        component_pattern = r'(?:the\s+)?([A-Z][a-zA-Z]+)\s+component'
        component_matches = re.findall(component_pattern, text, re.IGNORECASE)
        for component in component_matches:
            # Infer common React/Vue component path
            files.append(f"src/components/{component}.tsx")

        # Pattern 3: Command references (e.g., "/feature-plan command")
        command_pattern = r'/([a-z-]+)\s+command'
        command_matches = re.findall(command_pattern, text, re.IGNORECASE)
        for command in command_matches:
            files.append(f"installer/global/commands/{command}.md")

        # Pattern 4: File mentions with backticks
        backtick_pattern = r'`([a-zA-Z0-9_./\\-]+\.[a-zA-Z]{2,4})`'
        backtick_matches = re.findall(backtick_pattern, text)
        files.extend(backtick_matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    def extract_subtasks(self, feature_slug: str) -> List[Dict]:
        """
        Extract all subtasks from the review report.

        Tries multiple extraction strategies in order:
        1. Phase subtasks table (most structured)
        2. Numbered list in recommendations
        3. Bulleted list in recommendations

        Args:
            feature_slug: Feature slug for task ID generation

        Returns:
            List of subtask dictionaries
        """
        # Strategy 1: Try to find Phase subtasks table
        table_content = self.find_phase_subtasks_table()
        if table_content:
            subtasks = self.parse_subtasks_from_table(table_content, feature_slug)
            if subtasks:
                return subtasks

        # Strategy 2: Try recommendations section
        recommendations = self.find_recommendations_section()
        if not recommendations:
            return []

        # Try numbered list first
        numbered_subtasks = self.parse_subtasks_from_numbered_list(recommendations, feature_slug)
        if numbered_subtasks:
            return numbered_subtasks

        # Fall back to bulleted list
        bulleted_subtasks = self.parse_subtasks_from_bulleted_list(recommendations, feature_slug)
        return bulleted_subtasks


def extract_subtasks_from_review(
    review_report_path: str,
    feature_slug: str
) -> List[Dict]:
    """
    Parse review report and extract subtasks from recommendations.

    This is the main entry point for extracting subtasks from a review report.

    Args:
        review_report_path: Path to the review report markdown file
        feature_slug: Feature slug for task ID generation (e.g., "feature-workflow")

    Returns:
        List of subtask definitions:
        [
            {
                "id": "TASK-DM-001",
                "title": "Add CSS variables for dark mode",
                "description": "...",
                "files": ["src/styles/variables.css"],
                "complexity": 3,
                "implementation_mode": None,  # Set by FW-004
                "parallel_group": None,  # Set by FW-005
            },
            ...
        ]

    Raises:
        FileNotFoundError: If review report file doesn't exist
    """
    report_path = Path(review_report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"Review report not found: {review_report_path}")

    extractor = SubtaskExtractor(review_report_path)
    return extractor.extract_subtasks(feature_slug)
