"""Tests for prompt engineering template section generators.

Validates the four section generators and the assembler from
installer/core/templates/langchain-deepagents/templates/other/prompts/templates.py.template
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the template module (it's a .template file but pure Python)
# ---------------------------------------------------------------------------
_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "templates"
    / "other"
    / "prompts"
    / "templates.py.template"
)


@pytest.fixture(scope="module")
def templates():
    """Load the templates module from the .template file."""
    loader = SourceFileLoader("prompt_templates", str(_TEMPLATE_PATH))
    spec = importlib.util.spec_from_loader("prompt_templates", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# ===================================================================
# critical_response_format
# ===================================================================


class TestCriticalResponseFormat:
    """Tests for the CRITICAL response format section generator."""

    def test_header_present(self, templates):
        result = templates.critical_response_format({"decision": "accept"})
        assert "## CRITICAL -- Response Format" in result

    def test_json_example_embedded(self, templates):
        example = {"score": 5, "issues": []}
        result = templates.critical_response_format(example)
        assert json.dumps(example, indent=2) in result

    def test_imperative_language(self, templates):
        result = templates.critical_response_format({"ok": True})
        assert "MUST" in result
        assert "NEVER" in result

    def test_default_negative_examples(self, templates):
        result = templates.critical_response_format({"ok": True})
        assert "Do NOT return conversational text" in result
        assert "Do NOT wrap the JSON in markdown" in result

    def test_custom_negative_examples(self, templates):
        custom = ["Do NOT include HTML tags."]
        result = templates.critical_response_format(
            {"ok": True}, negative_examples=custom
        )
        assert "Do NOT include HTML tags." in result
        assert "Do NOT return conversational text" not in result

    def test_empty_negative_examples(self, templates):
        result = templates.critical_response_format(
            {"ok": True}, negative_examples=[]
        )
        assert "NEVER Do This" not in result


# ===================================================================
# tool_usage
# ===================================================================


class TestToolUsage:
    """Tests for the tool usage section generator."""

    def test_header_present(self, templates):
        result = templates.tool_usage(tools=[])
        assert "## Tool Usage" in result

    def test_tool_name_rendered(self, templates):
        tools = [{"name": "search_data", "purpose": "Search the knowledge base"}]
        result = templates.tool_usage(tools=tools)
        assert "`search_data`" in result
        assert "Search the knowledge base" in result

    def test_call_limit_rendered(self, templates):
        tools = [
            {"name": "rag_retrieval", "purpose": "Retrieve docs", "call_limit": 1}
        ]
        result = templates.tool_usage(tools=tools)
        assert "at most 1 time(s)" in result

    def test_pre_fetched_context(self, templates):
        result = templates.tool_usage(
            tools=[],
            pre_fetched_context="Curriculum context is already provided below.",
        )
        assert "Curriculum context is already provided below." in result
        assert "Do NOT call a tool to retrieve information already provided" in result

    def test_when_to_use_and_not_to_use(self, templates):
        tools = [
            {
                "name": "write_output",
                "when_to_use": "After Coach acceptance",
                "when_not_to_use": "Before Coach evaluation",
            }
        ]
        result = templates.tool_usage(tools=tools)
        assert "After Coach acceptance" in result
        assert "Before Coach evaluation" in result

    def test_no_pre_fetched_context(self, templates):
        result = templates.tool_usage(tools=[])
        assert "Do NOT call a tool to retrieve" not in result


# ===================================================================
# quality_gates
# ===================================================================


class TestQualityGates:
    """Tests for the quality gates section generator."""

    def test_header_present(self, templates):
        result = templates.quality_gates(criteria=[])
        assert "## Quality Gates" in result

    def test_criterion_accept_reject_examples(self, templates):
        criteria = [
            {
                "name": "Accuracy",
                "description": "Factually correct content",
                "accept_example": "All claims verified against source",
                "reject_example": "Contains fabricated statistics",
            }
        ]
        result = templates.quality_gates(criteria=criteria)
        assert "### Accuracy" in result
        assert "All claims verified against source" in result
        assert "Contains fabricated statistics" in result

    def test_weighted_scoring(self, templates):
        criteria = [
            {"name": "Accuracy", "description": "Correct"},
            {"name": "Style", "description": "Well-written"},
        ]
        weights = {"Accuracy": 0.7, "Style": 0.3}
        result = templates.quality_gates(
            criteria=criteria, scoring_weights=weights
        )
        assert "(weight: 70%)" in result
        assert "(weight: 30%)" in result
        assert "Weighted Scoring" in result

    def test_scepticism_strict(self, templates):
        result = templates.quality_gates(criteria=[], scepticism="strict")
        assert "rigorously" in result
        assert "ANY deviation" in result

    def test_scepticism_lenient(self, templates):
        result = templates.quality_gates(criteria=[], scepticism="lenient")
        assert "borderline" in result

    def test_scepticism_default_moderate(self, templates):
        result = templates.quality_gates(criteria=[])
        assert "fairly" in result


# ===================================================================
# output_structure
# ===================================================================


class TestOutputStructure:
    """Tests for the output structure section generator."""

    def test_header_present(self, templates):
        result = templates.output_structure(
            json_example={"content": ""},
            field_descriptions={"content": "The generated text (string)"},
        )
        assert "## Output Structure" in result

    def test_json_example_embedded(self, templates):
        example = {"content": "hello", "score": 5}
        result = templates.output_structure(
            json_example=example,
            field_descriptions={"content": "text", "score": "int 1-5"},
        )
        assert json.dumps(example, indent=2) in result

    def test_field_descriptions_rendered(self, templates):
        result = templates.output_structure(
            json_example={"content": ""},
            field_descriptions={
                "content": "The generated output (string, required)"
            },
        )
        assert "**`content`**" in result
        assert "The generated output (string, required)" in result

    def test_common_mistakes_rendered(self, templates):
        result = templates.output_structure(
            json_example={"ok": True},
            field_descriptions={"ok": "bool"},
            common_mistakes=["Do NOT nest the response in a wrapper object."],
        )
        assert "Common Mistakes" in result
        assert "Do NOT nest the response" in result

    def test_no_common_mistakes(self, templates):
        result = templates.output_structure(
            json_example={"ok": True},
            field_descriptions={"ok": "bool"},
        )
        assert "Common Mistakes" not in result


# ===================================================================
# assemble_prompt
# ===================================================================


class TestAssemblePrompt:
    """Tests for the prompt assembler."""

    def test_preamble_first(self, templates):
        result = templates.assemble_prompt(
            preamble="You are the Coach.",
            sections=["## Section A\nContent A"],
        )
        assert result.startswith("You are the Coach.")

    def test_critical_section_last(self, templates):
        critical = templates.critical_response_format({"ok": True})
        result = templates.assemble_prompt(
            preamble="Preamble",
            sections=["## Middle\nMiddle content"],
            critical=critical,
        )
        # CRITICAL section must be the last section
        parts = result.split("\n\n")
        last_section = "\n\n".join(parts[-6:])  # critical spans multiple paragraphs
        assert "## CRITICAL -- Response Format" in last_section

    def test_sections_order_preserved(self, templates):
        result = templates.assemble_prompt(
            preamble="Preamble",
            sections=["## First\nA", "## Second\nB", "## Third\nC"],
        )
        first_pos = result.index("## First")
        second_pos = result.index("## Second")
        third_pos = result.index("## Third")
        assert first_pos < second_pos < third_pos

    def test_no_critical_section(self, templates):
        result = templates.assemble_prompt(
            preamble="Preamble",
            sections=["## Body\nContent"],
        )
        assert "CRITICAL" not in result

    def test_critical_after_all_sections(self, templates):
        """CRITICAL section positioned after ALL other sections (TRF-031)."""
        critical = templates.critical_response_format({"result": ""})
        section_a = "## Tool Usage\nSome tools"
        section_b = "## Quality Gates\nSome gates"
        result = templates.assemble_prompt(
            preamble="You are an agent.",
            sections=[section_a, section_b],
            critical=critical,
        )
        tool_pos = result.index("## Tool Usage")
        gates_pos = result.index("## Quality Gates")
        critical_pos = result.index("## CRITICAL")
        assert tool_pos < gates_pos < critical_pos


# ===================================================================
# Integration: full prompt assembly
# ===================================================================


class TestIntegrationFullPrompt:
    """Integration test: assemble a complete prompt from all sections."""

    def test_full_prompt_assembly(self, templates):
        """Assemble a complete Coach-style prompt using all four generators."""
        preamble = (
            "You are the Coach agent in an adversarial cooperation system. "
            "Your role is to evaluate content produced by the Player agent."
        )

        tool_section = templates.tool_usage(
            tools=[
                {
                    "name": "search_data",
                    "purpose": "Search the knowledge base",
                    "when_to_use": "When you need additional context",
                    "when_not_to_use": "When context is already provided",
                    "call_limit": 1,
                },
            ],
            pre_fetched_context="Curriculum context is already provided below.",
        )

        gate_section = templates.quality_gates(
            criteria=[
                {
                    "name": "Factual Accuracy",
                    "description": "All claims must be verifiable",
                    "accept_example": "Claims backed by source material",
                    "reject_example": "Fabricated or unsourced claims",
                },
                {
                    "name": "Completeness",
                    "description": "All required topics covered",
                    "accept_example": "Covers all 5 required topics",
                    "reject_example": "Missing 2 of 5 required topics",
                },
            ],
            scoring_weights={"Factual Accuracy": 0.6, "Completeness": 0.4},
            scepticism="moderate",
        )

        json_example = {
            "decision": "accept",
            "score": 5,
            "issues": [],
            "criteria_met": True,
            "quality_assessment": "high",
        }

        structure_section = templates.output_structure(
            json_example=json_example,
            field_descriptions={
                "decision": '"accept" or "reject" (string, required)',
                "score": "Integer 1-5 (required)",
                "issues": "Array of strings, empty if accepted (required)",
                "criteria_met": "Boolean (required)",
                "quality_assessment": '"high", "adequate", or "needs_revision" (required)',
            },
            common_mistakes=[
                "Do NOT return a score without a matching decision.",
                "Do NOT leave issues empty when rejecting.",
            ],
        )

        critical = templates.critical_response_format(
            json_example=json_example,
            negative_examples=[
                "Do NOT return conversational text or prose.",
                "Do NOT include explanations outside the JSON.",
            ],
        )

        full_prompt = templates.assemble_prompt(
            preamble=preamble,
            sections=[tool_section, gate_section, structure_section],
            critical=critical,
        )

        # Verify all sections are present
        assert "You are the Coach agent" in full_prompt
        assert "## Tool Usage" in full_prompt
        assert "## Quality Gates" in full_prompt
        assert "## Output Structure" in full_prompt
        assert "## CRITICAL -- Response Format" in full_prompt

        # Verify ordering: preamble < tools < gates < structure < critical
        preamble_pos = full_prompt.index("You are the Coach")
        tools_pos = full_prompt.index("## Tool Usage")
        gates_pos = full_prompt.index("## Quality Gates")
        structure_pos = full_prompt.index("## Output Structure")
        critical_pos = full_prompt.index("## CRITICAL")
        assert preamble_pos < tools_pos < gates_pos < structure_pos < critical_pos

        # Verify imperative language
        assert "MUST" in full_prompt
        assert "NEVER" in full_prompt
        assert "Do NOT" in full_prompt

        # Verify JSON example is present
        assert '"decision": "accept"' in full_prompt
