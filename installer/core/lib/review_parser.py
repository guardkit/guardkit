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
    #         "id": "TASK-FWO-001",   # prefix padded to >= 3 (see MIN_TASK_PREFIX_LEN)
    #         "title": "Create /feature-plan command",
    #         "description": "...",
    #         "files": ["installer/core/commands/feature-plan.md"],
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


# ---------------------------------------------------------------------------
# The fix-task id prefix contract (leg-invocation stage-2 design §5)
# ---------------------------------------------------------------------------
#
# A fix task minted here is dispatched by the pipeline as a work leg, and the
# pipeline recognises it by its FILE STEM against
#
#     ^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$
#
# (its home: forge/src/forge/cli/_serve_deps_stage_log.py:398 — the same shape
# guards the queue at forge/src/forge/cli/queue.py:403). The head class excludes
# ``-``, so a TWO-letter derived prefix — ``TASK-FW-001-…`` from the slug
# "feature-workflow" — fails the ``{3,12}`` head and the fix task is dropped
# SILENTLY: it never reaches tier 2 and nothing says so. That class bit the
# 2026-08-02 crossing. So the derived prefix is padded to at least three
# characters here, at the mint, rather than being repaired downstream.
#
# The regex is NOT imported from forge (separate repo, no dependency); it is
# restated in the test that proves the stem matches, with the same home named.

#: Minimum prefix length that satisfies the pipeline's ``{3,12}`` stem head.
MIN_TASK_PREFIX_LEN = 3

#: Maximum kept — well inside the pipeline's 12, unchanged from the original.
MAX_TASK_PREFIX_LEN = 4

#: The stem head's own upper bound — the ``{3,12}`` in the pipeline's regex.
#: A report-supplied head LONGER than this is the same silent-drop class as a
#: two-letter one and is truncated to it, keeping as much of the report's
#: naming as the rule admits.
MAX_TASK_HEAD_LEN = 12

#: Used when a slug yields no usable ``[A-Z0-9]`` characters at all (e.g. a
#: non-latin or punctuation-only slug). Named rather than silently empty.
FALLBACK_TASK_PREFIX = "TSK"


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

            # Ensure ID has proper prefix, and that the prefix HEAD is long
            # enough for the pipeline to recognise the stem (see
            # _pad_report_task_id and the module header): a verbatim
            # ``| FW-001 |`` row minted TASK-FW-001-…, which the dispatcher
            # drops silently.
            task_id = self._pad_report_task_id(task_id, feature_slug)

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

        The prefix is the word initials, padded to at least
        ``MIN_TASK_PREFIX_LEN`` characters so the resulting file stem passes
        the pipeline's ``^TASK-[A-Z0-9]{3,12}…`` head (see the module header:
        a two-letter prefix is dropped silently by the dispatcher). The pad
        CONTINUES the last contributing word, so it still reads as an
        abbreviation of the feature rather than as filler.

        Examples:
        - "feature-workflow" -> "FWO"   (initials "FW" + "workflow"[1])
        - "dark-mode" -> "DMO"
        - "progressive-disclosure" -> "PDI"
        - "workflow" -> "WOR"           (single word: its first three letters)
        - "auth-api-gateway-layer" -> "AAGL"  (already >= 3, unchanged)

        Args:
            feature_slug: The feature slug (e.g., "feature-workflow")

        Returns:
            Task prefix (e.g., "FWO"), guaranteed ``[A-Z0-9]`` and of length
            ``MIN_TASK_PREFIX_LEN``..``MAX_TASK_PREFIX_LEN``.
        """
        parts = self._slug_words(feature_slug)
        prefix = ''.join(word[0] for word in parts)

        # If prefix is too long (>4 chars), try to abbreviate
        if len(prefix) > MAX_TASK_PREFIX_LEN:
            # Take first 2-4 letters intelligently
            # For "feature-workflow", we want "FW" (feature + workflow)
            # For "progressive-disclosure", we want "PD" (progressive + disclosure)
            prefix = prefix[:MAX_TASK_PREFIX_LEN]

        return self._pad_task_prefix(prefix, parts)

    @staticmethod
    def _slug_words(feature_slug: str) -> List[str]:
        """The slug's words, reduced to the characters the stem head accepts."""
        parts = [
            ''.join(ch for ch in word.upper() if ch.isascii() and ch.isalnum())
            for word in (feature_slug or '').split('-')
        ]
        return [word for word in parts if word]

    @staticmethod
    def _pad_task_prefix(prefix: str, parts: List[str]) -> str:
        """Pad a fix-task prefix to :data:`MIN_TASK_PREFIX_LEN` — the ONE pad.

        Stated once and used at BOTH mints (the derived-prefix path and the
        report-table path), because a second statement of the rule is a future
        lie: the table path had no pad at all, so a report row ``| FW-001 |``
        minted ``TASK-FW-001-…``, whose two-character head fails the pipeline's
        ``^TASK-[A-Z0-9]{3,12}…`` and is dropped WITHOUT SAYING SO.

        The pad CONTINUES the last contributing word, so the result still reads
        as an abbreviation of the feature rather than as filler, and falls back
        to :data:`FALLBACK_TASK_PREFIX` when the words give nothing to continue.
        """
        if len(prefix) < MIN_TASK_PREFIX_LEN and parts:
            for word in reversed(parts):
                for ch in word[1:]:
                    prefix += ch
                    if len(prefix) >= MIN_TASK_PREFIX_LEN:
                        break
                if len(prefix) >= MIN_TASK_PREFIX_LEN:
                    break

        # Last resort: a slug with no usable characters, or one whose words are
        # all single characters ("a-b"). Pad with the named fallback rather
        # than emit a stem the pipeline will drop without saying so.
        if len(prefix) < MIN_TASK_PREFIX_LEN:
            prefix = (prefix + FALLBACK_TASK_PREFIX)[:MIN_TASK_PREFIX_LEN]

        return prefix

    def _pad_report_task_id(self, task_id: str, feature_slug: str) -> str:
        """Apply the >= 3 pad to an id the REPORT supplied verbatim.

        ``parse_subtasks_from_table`` takes the ``ID`` column as written and
        only prepends ``TASK-``. The producer's own reports write two-letter
        heads (``FW-001``), so those fix tasks never reached tier 2 during the
        2026-08-02 crossing — the dispatcher's stem regex rejected them and
        nothing said so. Pad the HEAD segment through the same
        :meth:`_pad_task_prefix`, using the feature slug's words as the pad
        material so ``FW-001`` + ``feature-workflow`` -> ``TASK-FWO-001``.

        A head that already satisfies the rule is returned UNCHANGED — the
        report's own naming is authoritative wherever it is legal.
        """
        body = task_id[len('TASK-'):] if task_id.startswith('TASK-') else task_id
        head, separator, rest = body.partition('-')

        normalized = ''.join(
            ch for ch in head.upper() if ch.isascii() and ch.isalnum()
        )
        if (
            normalized == head
            and MIN_TASK_PREFIX_LEN <= len(normalized) <= MAX_TASK_HEAD_LEN
        ):
            return f"TASK-{body}"

        if len(normalized) > MAX_TASK_HEAD_LEN:
            return f"TASK-{normalized[:MAX_TASK_HEAD_LEN]}{separator}{rest}"

        padded = self._pad_task_prefix(normalized, self._slug_words(feature_slug))
        return f"TASK-{padded}{separator}{rest}"

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
            files.append(f"installer/core/commands/{command}.md")

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
