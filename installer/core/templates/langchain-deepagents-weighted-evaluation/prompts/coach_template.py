"""Coach/Evaluator prompt template for weighted adversarial cooperation.

Extends the base Coach prompt with weighted multi-criteria evaluation,
configurable scepticism tuning, explicit quality gates, and the CRITICAL
response format pattern (positioned last for recency bias).

Patterns proven across runs 4-11 (TRF-008, TRF-009, TRF-027, TRF-029).

Populated by: TASK-TI-013 (Coach Evaluator Prompt Template)
"""

from __future__ import annotations

from typing import Any


# Scepticism level definitions with distinct prompt language.
# Keys: strict, balanced (default), lenient.
# "moderate" is accepted as an alias for "balanced" for backward compatibility.
SCEPTICISM_LEVELS: dict[str, dict[str, str]] = {
    "strict": {
        "label": "STRICT",
        "directive": (
            "When uncertain, reject. Quality over quantity. "
            "Apply criteria rigorously and reject on ANY deviation from "
            "the expected standard. Borderline cases are rejections."
        ),
        "scoring_bias": (
            "Score conservatively. A criterion that is 'mostly met' should "
            "score 0.5 or below. Reserve scores above 0.8 for exemplary work."
        ),
    },
    "balanced": {
        "label": "BALANCED",
        "directive": (
            "Evaluate fairly. Accept if minimum threshold met. "
            "Apply criteria consistently and reject when issues are "
            "substantive. Minor imperfections are feedback, not grounds "
            "for rejection."
        ),
        "scoring_bias": (
            "Score proportionally. A criterion that is adequately met "
            "should score 0.6-0.7. Reserve scores above 0.9 for "
            "outstanding work."
        ),
    },
    "lenient": {
        "label": "LENIENT",
        "directive": (
            "Accept if substantially correct. Minor issues are feedback, "
            "not rejection. Only reject on clear, significant failures "
            "that undermine the core purpose of the content."
        ),
        "scoring_bias": (
            "Score generously. A criterion that is roughly met should "
            "score 0.6-0.7. Only score below 0.4 for clear failures."
        ),
    },
}

# Backward-compatibility alias
SCEPTICISM_LEVELS["moderate"] = SCEPTICISM_LEVELS["balanced"]


# --- Prompt sections (assembled in order, CRITICAL format LAST) ---

_ROLE_SECTION = """\
You are the Coach agent in a weighted adversarial cooperation system. Your role \
is to evaluate content produced by the Player agent against multiple weighted \
criteria and provide structured feedback with per-criterion scores.

You do NOT generate content yourself. You only evaluate."""

_TOOL_RESTRICTION_SECTION = """
## Tool Restrictions

You do NOT have access to any tools. Your sole responsibility is evaluation \
and feedback. Do NOT attempt to call any tools."""

_EVALUATION_PROCESS_SECTION = """
## Evaluation Process

1. Evaluate the content against EACH criterion independently.
2. Assign a score (0.0 to 1.0) for each criterion based on how well it is met.
3. Compute the weighted composite score: composite = sum(score * weight).
4. Set decision to "accept" if composite >= acceptance threshold, else "reject".
5. For rejected content, provide specific, actionable feedback for each low-scoring \
criterion so the Player can make targeted revisions."""


def _build_scepticism_section(scepticism: str) -> str:
    """Build the scepticism tuning section."""
    level = SCEPTICISM_LEVELS.get(scepticism, SCEPTICISM_LEVELS["balanced"])
    return (
        f"\n## Evaluation Stance: {level['label']}\n\n"
        f"{level['directive']}\n\n"
        f"{level['scoring_bias']}"
    )


def _build_criteria_section(criteria: list[dict[str, Any]]) -> str:
    """Build the weighted criteria section from a list of criterion dicts."""
    parts = ["\n## Weighted Criteria\n"]
    for criterion in criteria:
        name = criterion.get("name", "unnamed")
        weight = criterion.get("weight", 0.0)
        desc = criterion.get("description", "")
        accept = criterion.get("accept_example", "")
        reject = criterion.get("reject_example", "")

        parts.append(f"\n### {name} (weight: {weight:.0%})\n")
        if desc:
            parts.append(f"{desc}\n")
        if accept:
            parts.append(f"- **ACCEPT example**: {accept}\n")
        if reject:
            parts.append(f"- **REJECT example**: {reject}\n")

    return "".join(parts)


def _build_quality_gates_section(
    format_requirements: list[str] | None = None,
) -> str:
    """Build explicit quality gates with accept/reject examples.

    Args:
        format_requirements: Domain-specific format requirements from GOAL.md.
            Example: ["think_blocks_required", "json_output_required"]
    """
    parts = ["\n## Quality Gates\n"]

    parts.append(
        "The following conditions cause AUTOMATIC rejection regardless of "
        "criterion scores:\n\n"
        "- Output is not valid JSON\n"
        "- Required fields are missing from the output\n"
        "- Content is empty or placeholder text\n"
    )

    # Domain-specific gates from format_requirements
    if format_requirements:
        parts.append("\n### Domain-Specific Requirements\n\n")
        for req in format_requirements:
            if req == "think_blocks_required":
                parts.append(
                    "- **Think blocks required**: Automatically reject "
                    "(score all criteria at 0.0) any example missing "
                    "`<think>` blocks. Reasoning-type domains MUST include "
                    "explicit think blocks to demonstrate the reasoning "
                    "process.\n"
                )
            elif req == "json_output_required":
                parts.append(
                    "- **Strict JSON output**: Content field must contain "
                    "valid, parseable JSON. Malformed JSON is an automatic "
                    "rejection.\n"
                )
            else:
                # Generic format requirement
                parts.append(f"- **{req}**: Required by domain configuration.\n")

    # Explicit accept/reject scenario examples
    parts.append("\n### Accept vs Reject Scenarios\n\n")
    parts.append(
        "**ACCEPT scenario** (composite >= threshold):\n"
        "- All criteria score >= 0.5\n"
        "- Weighted composite meets acceptance threshold\n"
        "- Content addresses the core requirements\n"
        "- Minor imperfections noted as feedback, not grounds for rejection\n\n"
        "**REJECT scenario** (composite < threshold):\n"
        "- One or more critical criteria score below 0.3\n"
        "- Weighted composite falls below acceptance threshold\n"
        "- Content has structural problems (missing fields, invalid format)\n"
        "- Domain-specific quality gates violated (e.g., missing think blocks)\n"
    )

    return "".join(parts)


def _build_critical_response_format(
    acceptance_threshold: float,
) -> str:
    """Build the CRITICAL response format section.

    Positioned LAST in the prompt for recency bias (TI-002 pattern).
    The LLM pays more attention to content at the end of the prompt.
    """
    return f"""
## CRITICAL -- Response Format

You MUST respond with ONLY valid JSON. No prose, no preamble, no explanation \
outside the JSON structure. Every response MUST conform to this exact schema:

```json
{{{{
  "accepted": true,
  "scores": {{{{
    "<criterion_name>": {{{{
      "score": 0.85,
      "feedback": "Specific feedback for this criterion"
    }}}}
  }}}},
  "weighted_score": 0.82,
  "feedback": "Overall assessment summary",
  "revision_hints": []
}}}}
```

### Field Definitions

- **accepted** (bool): `true` if weighted_score >= {acceptance_threshold}, `false` otherwise.
- **scores** (object): Per-criterion evaluation. Each key is a criterion name containing:
  - **score** (float, 0.0-1.0): How well this criterion is met.
  - **feedback** (string): Specific, actionable description of the evaluation.
- **weighted_score** (float, 0.0-1.0): Composite score = sum(criterion_score * weight).
- **feedback** (string): Overall assessment summary. When rejecting, explain the primary \
reason clearly.
- **revision_hints** (array of strings): When rejecting, provide specific, actionable hints \
for the Player to improve. Must be non-empty on rejection. Empty array on acceptance.

### Example: ACCEPTED output

```json
{{{{
  "accepted": true,
  "scores": {{{{
    "accuracy": {{"score": 0.9, "feedback": "All claims supported by cited sources"}},
    "completeness": {{"score": 0.8, "feedback": "Covers all major aspects of the query"}},
    "structure": {{"score": 0.85, "feedback": "Valid JSON with all required fields"}},
    "quality": {{"score": 0.75, "feedback": "Clear writing, minor formatting issues"}}
  }}}},
  "weighted_score": 0.84,
  "feedback": "Content meets all quality thresholds. Minor formatting improvements noted.",
  "revision_hints": []
}}}}
```

### Example: REJECTED output

```json
{{{{
  "accepted": false,
  "scores": {{{{
    "accuracy": {{"score": 0.4, "feedback": "Several claims lack source references"}},
    "completeness": {{"score": 0.6, "feedback": "Missing coverage of edge cases"}},
    "structure": {{"score": 0.9, "feedback": "JSON structure is correct"}},
    "quality": {{"score": 0.5, "feedback": "Some sections are unclear"}}
  }}}},
  "weighted_score": 0.56,
  "feedback": "Content does not meet the acceptance threshold of {acceptance_threshold}. \
Primary issues: unsupported claims and incomplete coverage.",
  "revision_hints": [
    "Add source references for claims in paragraphs 2 and 4",
    "Add coverage of error handling edge cases",
    "Clarify the explanation in the configuration section"
  ]
}}}}
```

Do NOT return anything other than this JSON structure. Do NOT wrap it in \
markdown code fences. Do NOT add explanatory text before or after the JSON."""


def build_weighted_coach_prompt(
    criteria: list[dict[str, Any]],
    *,
    acceptance_threshold: float = 0.7,
    scepticism: str = "balanced",
    format_requirements: list[str] | None = None,
) -> str:
    """Build the complete Coach prompt with weighted criteria.

    Assembles prompt sections in order with the CRITICAL response format
    positioned LAST for recency bias (proven effective in runs 4-11).

    Args:
        criteria: List of criterion dicts with keys: name, weight, description,
            accept_example, reject_example.
        acceptance_threshold: Minimum composite score for acceptance (0.0-1.0).
        scepticism: Evaluation stance: strict | balanced | moderate | lenient.
        format_requirements: Domain-specific format requirements from GOAL.md.
            Example: ["think_blocks_required", "json_output_required"]

    Returns:
        Complete system prompt string for the Coach agent.
    """
    # Assemble sections in order (CRITICAL format LAST for recency bias)
    parts = [
        _ROLE_SECTION,
        _TOOL_RESTRICTION_SECTION,
        _EVALUATION_PROCESS_SECTION,
        _build_scepticism_section(scepticism),
        f"\n## Acceptance Threshold\n\nComposite score must be >= {acceptance_threshold} to accept.",
        _build_criteria_section(criteria),
        _build_quality_gates_section(format_requirements),
        _build_critical_response_format(acceptance_threshold),
    ]

    return "".join(parts)


def build_coach_prompt_from_goal(
    goal: Any,
    *,
    acceptance_threshold: float = 0.7,
    scepticism: str = "balanced",
    format_requirements: list[str] | None = None,
) -> str:
    """Build Coach prompt directly from a GoalSchema object.

    Auto-generates weighted criteria sections from the GoalSchema's
    evaluation criteria, including accept/reject examples per criterion.

    Args:
        goal: A GoalSchema instance (from scaffold/goal_schema.py.j2).
            Must have a ``criteria`` attribute (list of EvaluationCriterion).
        acceptance_threshold: Minimum composite score for acceptance (0.0-1.0).
        scepticism: Evaluation stance: strict | balanced | moderate | lenient.
        format_requirements: Domain-specific format requirements.
            If None, extracted from goal.generation_guidelines if present.

    Returns:
        Complete system prompt string for the Coach agent.

    Raises:
        ValueError: If goal has no criteria or weights don't sum to 1.0.
    """
    if not goal.criteria:
        raise ValueError("GoalSchema must have at least one evaluation criterion")

    if not goal.validate_weights():
        total = sum(c.weight for c in goal.criteria)
        raise ValueError(
            f"Criteria weights must sum to 1.0 (got {total:.3f})"
        )

    # Convert EvaluationCriterion dataclasses to dicts
    criteria_dicts = [
        {
            "name": c.name,
            "weight": c.weight,
            "description": c.description,
            "accept_example": c.accept_example,
            "reject_example": c.reject_example,
        }
        for c in goal.criteria
    ]

    return build_weighted_coach_prompt(
        criteria_dicts,
        acceptance_threshold=acceptance_threshold,
        scepticism=scepticism,
        format_requirements=format_requirements,
    )
