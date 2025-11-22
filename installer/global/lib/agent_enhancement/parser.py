"""
Enhancement Parser

Parses AI responses for agent enhancement.

TASK-PHASE-8-INCREMENTAL: Shared module for agent enhancement
"""

import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EnhancementParser:
    """Parses enhancement responses from AI."""

    def parse(self, response: str) -> Dict[str, Any]:
        """
        Parse enhancement response from AI.

        Handles multiple formats:
        1. Markdown-wrapped JSON:
           ```json
           {"sections": [...]}
           ```

        2. Bare JSON:
           {"sections": [...]}

        3. Mixed content with JSON:
           Here's the enhancement:
           ```json
           {"sections": [...]}
           ```
           Additional notes...

        Args:
            response: Raw response string from AI

        Returns:
            Dict with enhancement data

        Raises:
            ValueError: If response cannot be parsed
            json.JSONDecodeError: If JSON is malformed
        """
        # Try to extract JSON from markdown code blocks first
        json_content = self._extract_json_from_markdown(response)

        if json_content:
            # Parse extracted JSON
            try:
                enhancement = json.loads(json_content)
                self._validate_basic_structure(enhancement)
                return enhancement
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extracted JSON: {e}")
                # Fall through to try parsing entire response

        # Try parsing entire response as JSON
        try:
            enhancement = json.loads(response)
            self._validate_basic_structure(enhancement)
            return enhancement
        except json.JSONDecodeError:
            # Not valid JSON, try to extract JSON-like content
            pass

        # Last resort: Try to find JSON-like content anywhere in response
        json_pattern = r'\{[^}]*"sections"[^}]*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)

        for match in matches:
            try:
                enhancement = json.loads(match)
                self._validate_basic_structure(enhancement)
                return enhancement
            except json.JSONDecodeError:
                continue

        # If all parsing attempts fail
        raise ValueError(
            "Could not parse enhancement response. "
            "Expected JSON with 'sections' key."
        )

    def _extract_json_from_markdown(self, response: str) -> str | None:
        """
        Extract JSON from markdown code blocks.

        Looks for patterns like:
        ```json
        {...}
        ```

        or

        ```
        {...}
        ```

        Args:
            response: Response string potentially containing markdown

        Returns:
            Extracted JSON string or None if not found
        """
        # Pattern for ```json ... ``` blocks
        json_block_pattern = r'```json\s*\n(.*?)\n```'
        matches = re.findall(json_block_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Pattern for ``` ... ``` blocks (generic code blocks)
        code_block_pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        for match in matches:
            content = match.strip()
            # Check if it looks like JSON (starts with { or [)
            if content.startswith('{') or content.startswith('['):
                return content

        return None

    def _validate_basic_structure(self, enhancement: Dict[str, Any]) -> None:
        """
        Validate basic enhancement structure.

        Args:
            enhancement: Parsed enhancement dict

        Raises:
            ValueError: If structure is invalid
        """
        if not isinstance(enhancement, dict):
            raise ValueError("Enhancement must be a dictionary")

        if "sections" not in enhancement:
            raise ValueError("Enhancement must contain 'sections' key")

        if not isinstance(enhancement["sections"], list):
            raise ValueError("'sections' must be a list")

        # Validate boundaries if present (supports both old and new format)
        if "boundaries" in enhancement["sections"]:
            self._validate_boundaries(enhancement.get("boundaries", ""))

    def _validate_boundaries(self, boundaries_content: str) -> None:
        """
        Validate boundaries section structure and rule counts.

        Ensures ALWAYS/NEVER/ASK framework compliance:
        - ALWAYS: 5-7 rules with ✅ prefix
        - NEVER: 5-7 rules with ❌ prefix
        - ASK: 3-5 scenarios with ⚠️ prefix

        Args:
            boundaries_content: Markdown content of boundaries section

        Raises:
            ValueError: If boundaries structure is invalid or counts are wrong
        """
        if not boundaries_content or not boundaries_content.strip():
            raise ValueError("Boundaries section is empty")

        # Check for required subsections
        if "### ALWAYS" not in boundaries_content:
            raise ValueError("Boundaries section missing '### ALWAYS' subsection")
        if "### NEVER" not in boundaries_content:
            raise ValueError("Boundaries section missing '### NEVER' subsection")
        if "### ASK" not in boundaries_content:
            raise ValueError("Boundaries section missing '### ASK' subsection")

        # Extract sections
        always_section = self._extract_subsection(boundaries_content, "### ALWAYS", "### NEVER")
        never_section = self._extract_subsection(boundaries_content, "### NEVER", "### ASK")
        ask_section = self._extract_subsection(boundaries_content, "### ASK", None)

        # Count rules (lines starting with emoji bullets)
        always_count = self._count_rules(always_section, "✅")
        never_count = self._count_rules(never_section, "❌")
        ask_count = self._count_rules(ask_section, "⚠️")

        # Validate counts
        if not (5 <= always_count <= 7):
            raise ValueError(
                f"ALWAYS section must have 5-7 rules, found {always_count}. "
                f"Each rule should start with '- ✅'"
            )

        if not (5 <= never_count <= 7):
            raise ValueError(
                f"NEVER section must have 5-7 rules, found {never_count}. "
                f"Each rule should start with '- ❌'"
            )

        if not (3 <= ask_count <= 5):
            raise ValueError(
                f"ASK section must have 3-5 scenarios, found {ask_count}. "
                f"Each scenario should start with '- ⚠️'"
            )

        logger.info(
            f"Boundaries validation passed: ALWAYS={always_count}, "
            f"NEVER={never_count}, ASK={ask_count}"
        )

    def _extract_subsection(self, content: str, start_marker: str, end_marker: str | None) -> str:
        """
        Extract content between two section markers.

        Args:
            content: Full markdown content
            start_marker: Start section header (e.g., "### ALWAYS")
            end_marker: End section header or None for end of content

        Returns:
            Extracted subsection content
        """
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return ""

        # Start after the marker line
        start_idx = content.find('\n', start_idx) + 1

        if end_marker is None:
            return content[start_idx:]

        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            return content[start_idx:]

        return content[start_idx:end_idx]

    def _count_rules(self, section_content: str, emoji: str) -> int:
        """
        Count rules in a section by counting lines with specific emoji prefix.

        Args:
            section_content: Section markdown content
            emoji: Expected emoji prefix (✅, ❌, or ⚠️)

        Returns:
            Number of rules found
        """
        count = 0
        for line in section_content.split('\n'):
            stripped = line.strip()
            # Match: "- [emoji] ..." or "-[emoji] ..."
            if stripped.startswith(f"- {emoji}") or stripped.startswith(f"-{emoji}"):
                count += 1
        return count

    def parse_simple(self, response: str) -> Dict[str, Any]:
        """
        Simple parsing for well-formatted responses (used for testing).

        Args:
            response: JSON string

        Returns:
            Parsed dict

        Raises:
            json.JSONDecodeError: If JSON is malformed
        """
        return json.loads(response)
