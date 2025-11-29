"""
Decision Analysis mode for /task-review command.

Evaluates multiple implementation options against defined criteria using the
software-architect agent.
"""

import json
import re
from typing import Dict, Any, List, Literal, Optional

try:
    import sys
    from pathlib import Path
    lib_path = Path(__file__).parent.parent.parent / "lib"
    if str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
    from agent_bridge.invoker import AgentBridgeInvoker as AgentInvoker
except (ImportError, ModuleNotFoundError):
    # Fallback for testing
    class AgentInvoker:
        def invoke(self, agent_name: str, prompt: str, timeout_seconds: int, context: Dict[str, Any]) -> str:
            return '{"options": [], "recommendation": "A", "confidence": "medium"}'


ConfidenceLevel = Literal["low", "medium", "high"]


def execute(task_context: Dict[str, Any], depth: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute decision analysis.

    Args:
        task_context: Task metadata including options to evaluate
        depth: Analysis depth (quick, standard, comprehensive)
        model: Optional Claude model ID to use

    Returns:
        Structured decision analysis with option scores and recommendation
    """
    # Extract options from task context
    options = task_context.get("options", [])
    if not options:
        # Default to 4 generic options
        options = ["Option A", "Option B", "Option C", "Option D"]

    # Build prompt based on depth
    prompt = build_decision_prompt(task_context, depth, options)

    # Invoke software-architect agent
    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="software-architect",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "decision", "depth": depth},
        model=model
    )

    # Parse response into structured format
    results = parse_decision_response(response, options)

    return {
        "mode": "decision",
        "depth": depth,
        "options": results["options"],
        "recommendation": results["recommendation"],
        "confidence": results["confidence"],
        "criteria": results["criteria"],
        "justification": results["justification"]
    }


def build_decision_prompt(
    task_context: Dict[str, Any],
    depth: str,
    options: List[str]
) -> str:
    """
    Build prompt for decision analysis based on depth.

    Args:
        task_context: Task metadata including decision context
        depth: Analysis depth (quick, standard, comprehensive)
        options: List of options to evaluate

    Returns:
        Formatted prompt string for the agent
    """
    task_id = task_context.get("task_id", "UNKNOWN")
    decision_context = task_context.get("decision_context", "")
    criteria = task_context.get("criteria", [
        "Maintainability",
        "Performance",
        "Scalability",
        "Implementation Effort"
    ])

    options_str = "\n".join([f"- {opt}" for opt in options])
    criteria_str = "\n".join([f"- {crit}" for crit in criteria])

    if depth == "quick":
        # Surface-level analysis (15-30 min)
        return f"""Quick decision analysis for task {task_id}.

{decision_context}

Options to evaluate:
{options_str}

Evaluation criteria (score each 0-10):
{criteria_str}

Provide high-level analysis:
- Score each option on each criterion
- Calculate total scores
- Recommend the highest-scoring option
- Provide brief confidence assessment

Time budget: 20 minutes

Return structured JSON with:
{{
  "options": [
    {{
      "name": "Option A",
      "scores": {{"Maintainability": 8, "Performance": 7, "Scalability": 6, "Implementation Effort": 9}},
      "total_score": 30,
      "pros": ["..."],
      "cons": ["..."]
    }}
  ],
  "recommendation": "Option A",
  "confidence": "low|medium|high",
  "criteria": ["Maintainability", "Performance", "Scalability", "Implementation Effort"],
  "justification": "Brief reasoning for the recommendation"
}}
"""
    elif depth == "comprehensive":
        # Exhaustive analysis (4-6 hours)
        return f"""Comprehensive decision analysis for task {task_id}.

{decision_context}

Options to evaluate:
{options_str}

Evaluation criteria (score each 0-10):
{criteria_str}

Exhaustive analysis required:
- Score each option on each criterion with detailed justification
- Analyze pros and cons for each option
- Consider edge cases and failure modes
- Assess long-term implications (1-2 years)
- Evaluate technical debt implications
- Consider team expertise and learning curve
- Analyze integration complexity
- Risk assessment for each option
- Provide detailed confidence assessment with reasoning

Time budget: 5 hours

Return structured JSON with:
{{
  "options": [
    {{
      "name": "Option A",
      "scores": {{"Maintainability": 8, "Performance": 7, ...}},
      "total_score": <sum>,
      "pros": ["Detailed pro 1", "Detailed pro 2", ...],
      "cons": ["Detailed con 1", "Detailed con 2", ...],
      "edge_cases": ["..."],
      "long_term_implications": "...",
      "technical_debt": "low|medium|high",
      "learning_curve": "low|medium|high",
      "integration_complexity": "low|medium|high",
      "risks": [...]
    }}
  ],
  "recommendation": "Option X",
  "confidence": "low|medium|high",
  "confidence_reasoning": "Detailed explanation of confidence level",
  "criteria": [...],
  "justification": "Comprehensive reasoning with trade-off analysis"
}}
"""
    else:  # standard
        # Thorough analysis (1-2 hours)
        return f"""Decision analysis for task {task_id}.

{decision_context}

Options to evaluate:
{options_str}

Evaluation criteria (score each 0-10):
{criteria_str}

Standard analysis:
- Score each option on each criterion
- List key pros and cons
- Identify main trade-offs
- Calculate total scores
- Recommend the best option with reasoning
- Assess confidence level

Time budget: 90 minutes

Return structured JSON with:
{{
  "options": [
    {{
      "name": "Option A",
      "scores": {{"Maintainability": 8, "Performance": 7, "Scalability": 6, "Implementation Effort": 9}},
      "total_score": 30,
      "pros": ["Key pro 1", "Key pro 2"],
      "cons": ["Key con 1", "Key con 2"],
      "trade_offs": "Main trade-offs for this option"
    }}
  ],
  "recommendation": "Option X",
  "confidence": "low|medium|high",
  "criteria": ["Maintainability", "Performance", "Scalability", "Implementation Effort"],
  "justification": "Reasoning for the recommendation with key trade-offs"
}}
"""


def get_timeout_for_depth(depth: str) -> int:
    """
    Get timeout in seconds based on depth.

    Args:
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Timeout in seconds
    """
    timeouts = {
        "quick": 1800,        # 30 minutes
        "standard": 7200,     # 2 hours
        "comprehensive": 21600  # 6 hours
    }
    return timeouts.get(depth, 7200)


def parse_decision_response(response: str, expected_options: List[str]) -> Dict[str, Any]:
    """
    Parse agent response into structured format.

    Args:
        response: JSON string from software-architect agent
        expected_options: List of option names that should be in response

    Returns:
        Parsed dictionary with decision analysis
    """
    try:
        # Try to parse as JSON first
        if isinstance(response, str):
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)

            data = json.loads(response)
        else:
            data = response

        # Validate and normalize data
        options = data.get("options", [])
        if not options:
            # Create default option structures
            options = [
                {
                    "name": opt,
                    "scores": {},
                    "total_score": 0,
                    "pros": [],
                    "cons": []
                }
                for opt in expected_options
            ]

        # Ensure confidence is valid
        confidence = data.get("confidence", "medium")
        if confidence not in ["low", "medium", "high"]:
            confidence = "medium"

        return {
            "options": options,
            "recommendation": data.get("recommendation", options[0]["name"] if options else ""),
            "confidence": confidence,
            "criteria": data.get("criteria", []),
            "justification": data.get("justification", "")
        }
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback structure
        return {
            "options": [
                {
                    "name": opt,
                    "scores": {},
                    "total_score": 0,
                    "pros": [],
                    "cons": [f"Failed to parse response: {str(e)}"]
                }
                for opt in expected_options
            ],
            "recommendation": expected_options[0] if expected_options else "Unknown",
            "confidence": "low",
            "criteria": [],
            "justification": "Analysis failed - re-run required"
        }


def validate_option_scores(options: List[Dict[str, Any]], criteria: List[str]) -> List[Dict[str, Any]]:
    """
    Validate that all options have scores for all criteria.

    Args:
        options: List of option dictionaries
        criteria: List of criteria names

    Returns:
        Validated options with complete scores
    """
    validated = []
    for option in options:
        scores = option.get("scores", {})

        # Ensure all criteria are present
        for criterion in criteria:
            if criterion not in scores:
                scores[criterion] = 5  # Default middle score

        # Recalculate total
        option["total_score"] = sum(scores.values())
        validated.append(option)

    return validated
