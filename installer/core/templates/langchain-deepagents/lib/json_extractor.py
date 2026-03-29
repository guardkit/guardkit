"""JSON extraction utilities for LLM outputs.

Provides a 5-strategy cascade for robust JSON extraction from LLM responses
that may contain think tags, code fences, prose wrappers, literal control
characters inside string values, or structured output in reasoning_content.

Strategy 4 (repair) exists because Qwen models emit literal newlines inside
JSON string values. Strategy 5 (reasoning_content fallback) exists because
vLLM's --reasoning-parser moves <think> blocks out of .content. See
docs/reference/model-compatibility.md for the full model quirks matrix.

Dependencies: stdlib only (json, re).
"""

from __future__ import annotations

import json
import re


class JsonExtractionError(Exception):
    """Raised when all extraction strategies fail."""


class JsonExtractor:
    """Extract JSON dicts from LLM output using a 5-strategy cascade."""

    @staticmethod
    def extract(
        content: str,
        additional_kwargs: dict | None = None,
    ) -> dict:
        """Extract JSON from LLM output using a 5-strategy cascade.

        Pipeline:
        1. Normalise think tags.
        2. Strip think blocks from content.
        3. Try strategies 1-4 on normalised content.
        4. If all fail, try strategies 1-4 on additional_kwargs["reasoning_content"].
        5. Raise JsonExtractionError if everything fails.

        Args:
            content: Raw LLM output string.
            additional_kwargs: Optional metadata dict; may contain
                "reasoning_content" for vLLM providers.

        Returns:
            Parsed JSON dict.

        Raises:
            JsonExtractionError: When no strategy succeeds.
        """
        normalised = JsonExtractor.normalise_think_closing_tags(content)
        # Remove think blocks entirely — they are not useful for extraction.
        cleaned = re.sub(r"<think>.*?</think>", "", normalised, flags=re.DOTALL).strip()

        result = JsonExtractor._try_strategies(cleaned)
        if result is not None:
            return result

        # Strategy 5: fall back to reasoning_content
        if additional_kwargs:
            reasoning = additional_kwargs.get("reasoning_content", "")
            if reasoning:
                result = JsonExtractor._try_strategies(str(reasoning))
                if result is not None:
                    return result

        raise JsonExtractionError(
            "All JSON extraction strategies failed. "
            f"Content preview: {content[:200]!r}"
        )

    @staticmethod
    def normalise_think_closing_tags(text: str) -> str:
        """Fix malformed think tags in LLM output.

        Handles two patterns:
        - ``<think>...<think>`` (second tag missing slash) → ``<think>...</think>``
        - ``<think>...EOF`` (unclosed tag at end of string) → ``<think>...</think>``
        - Already-correct ``<think>...</think>`` → unchanged

        Args:
            text: Raw text possibly containing think tags.

        Returns:
            Text with well-formed think tags.
        """
        # Step 1: Fix <think>content<think> (missing slash on closing tag).
        # Only match when the inner content contains no '<' to avoid greedily
        # consuming other tags.
        fixed = re.sub(
            r"<think>([^<]*?)<think>",
            r"<think>\1</think>",
            text,
        )

        # Step 2: Fix unclosed <think> tags (no paired </think>).
        # Build a list of all tag positions and process in order.
        # For each <think> we must find a later </think>; if none exists, append one.
        tokens: list[tuple[int, str]] = []
        for m in re.finditer(r"<think>|</think>", fixed):
            tokens.append((m.start(), m.group()))

        # Count unmatched opens (opens that have no following close).
        depth = 0
        for _, tag in tokens:
            if tag == "<think>":
                depth += 1
            else:
                if depth > 0:
                    depth -= 1
                # Stray close tags (depth == 0) are harmless — leave them.

        # Append a close tag for each unmatched open.
        if depth > 0:
            fixed = fixed + "</think>" * depth

        return fixed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _try_strategies(text: str) -> dict | None:
        """Run strategies 1-4 and return the first successful result."""
        result = JsonExtractor._strategy_direct(text)
        if result is not None:
            return result

        result = JsonExtractor._strategy_code_fence(text)
        if result is not None:
            return result

        result = JsonExtractor._strategy_brace_match(text)
        if result is not None:
            return result

        result = JsonExtractor._strategy_repair(text)
        if result is not None:
            return result

        return None

    @staticmethod
    def _strategy_direct(text: str) -> dict | None:
        """Strategy 1: parse the whole string directly with json.loads."""
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _strategy_code_fence(text: str) -> dict | None:
        """Strategy 2: strip ```json ... ``` or ``` ... ``` fences then parse."""
        # Match optional language tag after opening fence.
        pattern = re.compile(
            r"```(?:[a-zA-Z0-9_+\-]*)?\s*\n?(.*?)```",
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            candidate = match.group(1).strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    @staticmethod
    def _extract_brace_substring(text: str) -> str | None:
        """Find the outermost ``{...}`` block using string-aware depth tracking."""
        depth = 0
        in_string = False
        start: int | None = None

        i = 0
        while i < len(text):
            ch = text[i]

            if in_string:
                if ch == "\\" and i + 1 < len(text):
                    # Skip the escaped character.
                    i += 2
                    continue
                if ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and start is not None:
                        return text[start: i + 1]
            i += 1

        return None

    @staticmethod
    def _strategy_brace_match(text: str) -> dict | None:
        """Strategy 3: find outermost ``{...}`` with string-aware depth tracking."""
        substring = JsonExtractor._extract_brace_substring(text)
        if substring is None:
            return None
        try:
            parsed = json.loads(substring)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _strategy_repair(text: str) -> dict | None:
        """Strategy 4: repair literal newlines/tabs inside JSON string values."""
        substring = JsonExtractor._extract_brace_substring(text)
        if substring is None:
            return None

        repaired = JsonExtractor._repair_literal_control_chars(substring)
        if repaired == substring:
            # No changes — brace match already tried this, skip.
            return None
        try:
            parsed = json.loads(repaired)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _repair_literal_control_chars(text: str) -> str:
        """Replace literal newline/tab bytes inside JSON string values with escapes."""
        result: list[str] = []
        in_string = False
        i = 0

        while i < len(text):
            ch = text[i]

            if in_string:
                if ch == "\\" and i + 1 < len(text):
                    # Pass through escape sequences unchanged.
                    result.append(ch)
                    result.append(text[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    in_string = False
                    result.append(ch)
                elif ch == "\n":
                    result.append("\\n")
                elif ch == "\t":
                    result.append("\\t")
                elif ch == "\r":
                    result.append("\\r")
                else:
                    result.append(ch)
            else:
                if ch == '"':
                    in_string = True
                result.append(ch)

            i += 1

        return "".join(result)
