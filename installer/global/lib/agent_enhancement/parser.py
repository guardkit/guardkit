"""
Enhancement Parser

Parses AI responses for agent enhancement.

TASK-PHASE-8-INCREMENTAL: Shared module for agent enhancement
"""

from __future__ import annotations

import json
import re
import logging
from typing import Dict, Any, Optional

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
        Validate basic enhancement structure and enforce JSON schema requirements.

        TASK-BDRY-316A: Enforce boundaries requirement from JSON schema.
        If AI omits boundaries, raise ValueError to trigger workaround in enhancer.

        Args:
            enhancement: Parsed enhancement dict

        Raises:
            ValueError: If structure is invalid or boundaries missing/malformed
        """
        if not isinstance(enhancement, dict):
            raise ValueError("Enhancement must be a dictionary")

        if "sections" not in enhancement:
            raise ValueError("Enhancement must contain 'sections' key")

        if not isinstance(enhancement["sections"], list):
            raise ValueError("'sections' must be a list")

        # TASK-BDRY-316A: Enforce JSON schema requirement for boundaries
        # Schema specifies boundaries as REQUIRED field, so we validate:
        # 1. "boundaries" must be in sections list
        # 2. "boundaries" field must exist in enhancement dict
        # 3. Boundaries content must conform to ALWAYS/NEVER/ASK format

        has_boundaries_in_sections = "boundaries" in enhancement["sections"]
        has_boundaries_field = "boundaries" in enhancement

        # Case 1: Boundaries in sections but field missing → Schema violation
        if has_boundaries_in_sections and not has_boundaries_field:
            raise ValueError(
                "Enhancement 'sections' list includes 'boundaries' but 'boundaries' field is missing. "
                "This violates the JSON schema requirement - check prompt_builder.py schema definition."
            )

        # Case 2: Boundaries completely omitted → Schema violation (triggers workaround)
        if not has_boundaries_in_sections or not has_boundaries_field:
            logger.warning(
                "AI response missing required 'boundaries' field (schema violation). "
                "Enhancer will add generic boundaries as workaround."
            )
            raise ValueError(
                "Enhancement missing required 'boundaries' field per JSON schema"
            )

        # Case 3: Boundaries present → Validate format
        self._validate_boundaries(enhancement.get("boundaries", ""))

        # TASK-ENH-DM01: Validate metadata (graceful, non-blocking)
        self._validate_metadata(enhancement)

    def _validate_metadata(self, enhancement: Dict[str, Any]) -> None:
        """
        Validate frontmatter_metadata structure with graceful degradation.

        TASK-ENH-DM01: Discovery metadata validation (warning, not blocking).

        Does NOT raise ValueError - logs warnings for invalid/missing metadata.
        This enables graceful degradation when AI omits discovery fields.
        """
        metadata = enhancement.get("frontmatter_metadata")

        if metadata is None:
            logger.warning(
                "AI response missing 'frontmatter_metadata' field. "
                "Agent will not have discovery metadata until manually added."
            )
            return

        if not isinstance(metadata, dict):
            logger.warning(
                f"'frontmatter_metadata' must be a dict, got {type(metadata).__name__}. "
                "Ignoring invalid metadata."
            )
            return

        # Basic presence checks only (MVP validation per architectural review)
        if "stack" not in metadata:
            logger.warning("Missing 'stack' in frontmatter_metadata")
        if "phase" not in metadata:
            logger.warning("Missing 'phase' in frontmatter_metadata")

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
