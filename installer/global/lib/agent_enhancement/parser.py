"""
Enhancement Parser

Parses AI responses for agent enhancement.

TASK-PHASE-8-INCREMENTAL: Shared module for agent enhancement
"""

import json
import re
import logging
from typing import Dict, Any

# TASK-UX-6581: Import shared boundary utilities
# Handle both package import and direct import
try:
    from .boundary_utils import validate_boundaries_format
except ImportError:
    from boundary_utils import validate_boundaries_format

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

        # TASK-D70B: Validate boundaries if present (strict validation when included)
        # Note: Boundaries are RECOMMENDED but parser is lenient (enhancer handles missing boundaries)
        if "boundaries" in enhancement["sections"]:
            if "boundaries" not in enhancement:
                raise ValueError(
                    "Enhancement 'sections' list includes 'boundaries' but 'boundaries' field is missing"
                )
            self._validate_boundaries(enhancement.get("boundaries", ""))

    def _validate_boundaries(self, boundaries_content: str) -> None:
        """
        Validate boundaries section structure and rule counts.

        TASK-UX-6581: Uses shared boundary_utils.validate_boundaries_format() for validation.

        Ensures ALWAYS/NEVER/ASK framework compliance:
        - ALWAYS: 5-7 rules with ✅ prefix
        - NEVER: 5-7 rules with ❌ prefix
        - ASK: 3-5 scenarios with ⚠️ prefix

        Args:
            boundaries_content: Markdown content of boundaries section

        Raises:
            ValueError: If boundaries structure is invalid or counts are wrong
        """
        is_valid, issues = validate_boundaries_format(boundaries_content)

        if not is_valid:
            # Combine issues into single error message
            raise ValueError("; ".join(issues))

        # Log success (matches old behavior)
        logger.info("Boundaries validation passed via shared utility")

    # TASK-UX-6581: Removed _extract_subsection() and _count_rules()
    # These methods have been moved to boundary_utils.py for shared use between
    # /agent-enhance and /agent-format commands.

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
