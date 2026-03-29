"""Comprehensive test suite for JsonExtractor.

Covers all 5 extraction strategies, normalise_think_closing_tags, pipeline
ordering, edge cases, and the full cascade.

Coverage Target: >=90%
Test Count: 40+ tests
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load module directly — directory name contains hyphens, not importable.
# ---------------------------------------------------------------------------
_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "json_extractor.py"
)

_spec = importlib.util.spec_from_file_location("json_extractor", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

JsonExtractor = _mod.JsonExtractor
JsonExtractionError = _mod.JsonExtractionError


# ===========================================================================
# Strategy 1 — Direct parse
# ===========================================================================


class TestStrategyDirect:
    """Strategy 1: json.loads on the raw content string."""

    def test_clean_json_string(self):
        result = JsonExtractor.extract('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_surrounding_whitespace(self):
        result = JsonExtractor.extract('  \n  {"score": 9}  \n  ')
        assert result == {"score": 9}

    def test_nested_dict(self):
        data = {"outer": {"inner": 42, "flag": True}}
        result = JsonExtractor.extract(json.dumps(data))
        assert result == data

    def test_json_array_not_returned_as_dict(self):
        # A top-level array should NOT satisfy strategy 1; cascade continues.
        # Wrap in prose so no strategy succeeds as a dict.
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("[1, 2, 3]")

    def test_non_json_falls_through(self):
        # Plain text, no JSON anywhere → full cascade fails.
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("this is just text")

    def test_unicode_in_values(self):
        data = {"greeting": "こんにちは", "emoji": "🎉"}
        result = JsonExtractor.extract(json.dumps(data, ensure_ascii=False))
        assert result == data


# ===========================================================================
# Strategy 2 — Code-fence strip
# ===========================================================================


class TestStrategyCodeFence:
    """Strategy 2: extract content from ```json ... ``` or ``` ... ``` blocks."""

    def test_json_language_tag(self):
        content = '```json\n{"key": "val"}\n```'
        assert JsonExtractor.extract(content) == {"key": "val"}

    def test_no_language_tag(self):
        content = '```\n{"key": "val"}\n```'
        assert JsonExtractor.extract(content) == {"key": "val"}

    def test_content_before_and_after_fence(self):
        content = 'Here is the JSON:\n```json\n{"result": true}\n```\nHope that helps!'
        assert JsonExtractor.extract(content) == {"result": True}

    def test_fence_with_extra_blank_lines(self):
        content = "```json\n\n  {\"a\": 1}\n\n```"
        assert JsonExtractor.extract(content) == {"a": 1}

    def test_non_json_in_fence_falls_through(self):
        # Fence contains prose, not JSON — strategy 2 fails, strategy 3 tries.
        content = "```\nnot json at all\n```"
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract(content)


# ===========================================================================
# Strategy 3 — String-aware brace matching
# ===========================================================================


class TestStrategyBraceMatch:
    """Strategy 3: extract outermost {...} with correct string-awareness."""

    def test_json_embedded_in_prose(self):
        content = 'Here is the result: {"key": "val"} hope that helps'
        assert JsonExtractor.extract(content) == {"key": "val"}

    def test_braces_inside_quoted_value(self):
        # The { and } inside the string must not confuse depth tracking.
        content = 'prefix {"msg": "use { and } carefully"} suffix'
        assert JsonExtractor.extract(content) == {"msg": "use { and } carefully"}

    def test_nested_objects_in_prose(self):
        content = "Answer: " + json.dumps({"outer": {"inner": 1}}) + " done."
        assert JsonExtractor.extract(content) == {"outer": {"inner": 1}}

    def test_no_valid_braces_falls_through(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("no braces here at all")

    def test_deeply_nested_json_in_prose(self):
        data = {"a": {"b": {"c": {"d": 99}}}}
        content = "result: " + json.dumps(data) + " end"
        assert JsonExtractor.extract(content) == data

    def test_escaped_quote_inside_value(self):
        # Escaped quote must not prematurely end string tracking.
        data = {"msg": 'say "hello"'}
        content = "output: " + json.dumps(data) + " done"
        assert JsonExtractor.extract(content) == data

    def test_only_strategy3_can_handle(self):
        """Input that requires brace matching (not direct or fence)."""
        content = "The agent responded: {\"decision\": \"accept\", \"score\": 5} end."
        result = JsonExtractor.extract(content)
        assert result == {"decision": "accept", "score": 5}


# ===========================================================================
# Strategy 4 — JSON string repair
# ===========================================================================


class TestStrategyRepair:
    """Strategy 4: repair literal control chars inside JSON string values."""

    def test_literal_newline_in_value(self):
        # Construct a string with an actual newline byte inside a JSON value.
        raw = '{"text": "line1\nline2"}'  # the \n here is a real newline byte
        result = JsonExtractor.extract(raw)
        assert result["text"] == "line1\nline2"

    def test_literal_tab_in_value(self):
        raw = '{"text": "col1\tcol2"}'  # real tab byte
        result = JsonExtractor.extract(raw)
        assert result["text"] == "col1\tcol2"

    def test_literal_newline_embedded_in_prose(self):
        # Literal newline AND embedded in prose (combines strategies 3 + 4).
        inner = '{"note": "first\nsecond"}'  # real newline
        content = "Result: " + inner + " done."
        result = JsonExtractor.extract(content)
        assert result["note"] == "first\nsecond"

    def test_literal_carriage_return_in_value(self):
        raw = '{"text": "before\rafter"}'  # real CR byte
        result = JsonExtractor.extract(raw)
        assert result["text"] == "before\rafter"

    def test_escaped_chars_not_double_escaped(self):
        # Already-escaped sequences must pass through unchanged.
        data = {"path": "C:\\Users\\test"}
        result = JsonExtractor.extract(json.dumps(data))
        assert result == data


# ===========================================================================
# Strategy 5 — reasoning_content fallback
# ===========================================================================


class TestStrategyReasoningContent:
    """Strategy 5: fall back to additional_kwargs["reasoning_content"]."""

    def test_reasoning_content_valid_json(self):
        result = JsonExtractor.extract(
            "not json",
            additional_kwargs={"reasoning_content": '{"key": "val"}'},
        )
        assert result == {"key": "val"}

    def test_empty_additional_kwargs_raises(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("not json", additional_kwargs={})

    def test_none_additional_kwargs_raises(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("not json", additional_kwargs=None)

    def test_reasoning_content_empty_string_raises(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract(
                "not json",
                additional_kwargs={"reasoning_content": ""},
            )

    def test_reasoning_content_with_think_tags(self):
        # reasoning_content itself may need normalisation.
        reasoning = "<think>thinking</think>{\"ok\": true}"
        result = JsonExtractor.extract(
            "not json",
            additional_kwargs={"reasoning_content": reasoning},
        )
        assert result == {"ok": True}

    def test_main_content_wins_over_reasoning(self):
        # If main content parses, reasoning_content is not consulted.
        result = JsonExtractor.extract(
            '{"source": "main"}',
            additional_kwargs={"reasoning_content": '{"source": "reasoning"}'},
        )
        assert result == {"source": "main"}


# ===========================================================================
# normalise_think_closing_tags
# ===========================================================================


class TestNormaliseThinkClosingTags:
    """Unit tests for the think-tag normalisation helper."""

    def test_missing_slash_on_closing_tag(self):
        text = "<think>reasoning<think>answer"
        result = JsonExtractor.normalise_think_closing_tags(text)
        assert "<think>reasoning</think>" in result

    def test_unclosed_at_eof(self):
        text = "<think>some reasoning"
        result = JsonExtractor.normalise_think_closing_tags(text)
        assert result.endswith("</think>")
        assert "<think>some reasoning</think>" in result

    def test_already_correct_unchanged(self):
        text = "<think>reasoning</think>answer"
        result = JsonExtractor.normalise_think_closing_tags(text)
        assert "<think>reasoning</think>" in result
        assert "answer" in result

    def test_no_think_tags_unchanged(self):
        text = "just plain text with no tags"
        result = JsonExtractor.normalise_think_closing_tags(text)
        assert result == text

    def test_multiple_think_blocks(self):
        text = "<think>block1</think>middle<think>block2</think>end"
        result = JsonExtractor.normalise_think_closing_tags(text)
        assert result.count("<think>") == result.count("</think>")

    def test_think_block_stripped_in_extract(self):
        # After normalisation, extract() removes think blocks.
        content = "<think>irrelevant reasoning</think>{\"decision\": \"accept\"}"
        result = JsonExtractor.extract(content)
        assert result == {"decision": "accept"}

    def test_think_block_with_missing_slash_then_json(self):
        content = "<think>reasoning<think>{\"ok\": true}"
        result = JsonExtractor.extract(content)
        assert result == {"ok": True}


# ===========================================================================
# Pipeline ordering
# ===========================================================================


class TestPipelineOrdering:
    """Verify that think-tag normalisation runs before extraction strategies."""

    def test_think_tags_wrapping_code_fenced_json(self):
        content = '<think>step 1: plan</think>\n```json\n{"answer": 42}\n```'
        result = JsonExtractor.extract(content)
        assert result == {"answer": 42}

    def test_think_tags_wrapping_prose_embedded_json(self):
        content = "<think>deliberation</think> The result is {\"score\": 7} done."
        result = JsonExtractor.extract(content)
        assert result == {"score": 7}

    def test_unclosed_think_then_json(self):
        content = "<think>thinking... the answer is {\"x\": 1}"
        # think block is unclosed; after normalisation and stripping it is removed.
        # The JSON inside the think block is gone — this raises.
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract(content)

    def test_think_tag_with_only_json_after(self):
        content = "<think>plan</think>{\"result\": \"done\"}"
        result = JsonExtractor.extract(content)
        assert result == {"result": "done"}


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and robustness checks."""

    def test_empty_string_raises(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("")

    def test_whitespace_only_raises(self):
        with pytest.raises(JsonExtractionError):
            JsonExtractor.extract("   \n\t  ")

    def test_all_strategies_fail_error_message(self):
        with pytest.raises(JsonExtractionError, match="All JSON extraction strategies failed"):
            JsonExtractor.extract("no json anywhere")

    def test_unicode_in_key_and_value(self):
        data = {"名前": "田中", "score": 10}
        result = JsonExtractor.extract(json.dumps(data, ensure_ascii=False))
        assert result == data

    def test_deeply_nested_json(self):
        data: dict = {}
        node = data
        for i in range(20):
            node["child"] = {}
            node = node["child"]
        node["leaf"] = "value"
        result = JsonExtractor.extract(json.dumps(data))
        assert result == data

    def test_boolean_values(self):
        result = JsonExtractor.extract('{"flag": true, "other": false}')
        assert result == {"flag": True, "other": False}

    def test_null_value(self):
        result = JsonExtractor.extract('{"key": null}')
        assert result == {"key": None}

    def test_numeric_values(self):
        result = JsonExtractor.extract('{"int": 42, "float": 3.14}')
        assert result == {"int": 42, "float": 3.14}

    def test_array_value_inside_dict(self):
        result = JsonExtractor.extract('{"items": [1, 2, 3]}')
        assert result == {"items": [1, 2, 3]}

    def test_empty_dict(self):
        result = JsonExtractor.extract("{}")
        assert result == {}

    def test_large_json(self):
        data = {f"key_{i}": f"value_{i}" for i in range(200)}
        result = JsonExtractor.extract(json.dumps(data))
        assert len(result) == 200


# ===========================================================================
# Full cascade test
# ===========================================================================


class TestFullCascade:
    """Verify the cascade reaches the correct strategy for each input type."""

    def test_only_strategy3_succeeds(self):
        """Prose wrapper prevents strategies 1 and 2; strategy 3 finds the JSON."""
        content = "Agent output follows: {\"cascade_test\": \"strategy3\"} end."
        result = JsonExtractor.extract(content)
        assert result == {"cascade_test": "strategy3"}

    def test_only_strategy4_succeeds(self):
        """Literal newline in value causes strategy 3 to fail; strategy 4 repairs."""
        # Construct content that brace-matches but has literal newlines.
        # Make it embedded in prose so strategy 1 and 2 also fail.
        inner = '{"multi": "line1\nline2"}'  # real newline byte
        content = "Prose before: " + inner + " prose after."
        result = JsonExtractor.extract(content)
        assert result["multi"] == "line1\nline2"

    def test_only_strategy5_succeeds(self):
        """Main content is unparseable; reasoning_content contains valid JSON."""
        result = JsonExtractor.extract(
            "I cannot provide JSON output.",
            additional_kwargs={"reasoning_content": '{"fallback": true}'},
        )
        assert result == {"fallback": True}

    def test_strategy1_short_circuits(self):
        """Clean JSON takes the fast path — strategy 1 — without deeper work."""
        data = {"fast": "path"}
        result = JsonExtractor.extract(json.dumps(data))
        assert result == data
