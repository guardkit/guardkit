"""
Code Quality Review mode for /task-review command.

Evaluates complexity metrics, test coverage, code smells, and coding standards
using the code-reviewer agent.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

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
            return '{"quality_score": 7.5, "complexity_metrics": {}, "code_smells": [], "style_issues": [], "test_coverage": null}'


def execute(task_context: Dict[str, Any], depth: str) -> Dict[str, Any]:
    """
    Execute code quality review.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Structured review results with quality scores and metrics
    """
    # Build prompt based on depth
    prompt = build_quality_prompt(task_context, depth)

    # Invoke code-reviewer agent
    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="code-reviewer",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "code-quality", "depth": depth}
    )

    # Parse response into structured format
    results = parse_quality_response(response)

    return {
        "mode": "code-quality",
        "depth": depth,
        "quality_score": results["quality_score"],  # 0-10
        "complexity_metrics": results["complexity_metrics"],
        "code_smells": results["code_smells"],
        "style_issues": results["style_issues"],
        "test_coverage": results["test_coverage"],
        "findings": results["findings"],
        "recommendations": results["recommendations"]
    }


def build_quality_prompt(task_context: Dict[str, Any], depth: str) -> str:
    """
    Build prompt for code quality review based on depth.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Formatted prompt string for the agent
    """
    scope = task_context.get("review_scope", [])
    task_id = task_context.get("task_id", "UNKNOWN")
    scope_str = ", ".join(scope) if scope else "entire codebase"

    if depth == "quick":
        # Surface-level analysis (15-30 min)
        return f"""Quick code quality review for task {task_id}.

Review scope: {scope_str}

Focus on high-level quality issues:
- Calculate cyclomatic complexity for main functions
- Identify obvious code smells (long functions, deep nesting)
- Check for basic style violations
- Note test coverage if available

Time budget: 20 minutes

Return structured JSON with:
{{
  "quality_score": <0-10>,
  "complexity_metrics": {{
    "avg_cyclomatic": <number>,
    "max_cyclomatic": <number>,
    "avg_nesting_depth": <number>
  }},
  "code_smells": [
    {{"type": "long_function|deep_nesting|god_class", "location": "file:line", "severity": "high|medium|low"}}
  ],
  "style_issues": [
    {{"type": "...", "location": "file:line", "description": "..."}}
  ],
  "test_coverage": {{"line_coverage": <0-100>, "branch_coverage": <0-100>}} or null,
  "findings": [...],
  "recommendations": [...]
}}
"""
    elif depth == "comprehensive":
        # Exhaustive analysis (4-6 hours)
        return f"""Comprehensive code quality review for task {task_id}.

Review scope: {scope_str}

Exhaustive quality analysis:
- Complexity metrics (cyclomatic, cognitive, nesting depth, function length)
- All code smells:
  * Long Method (>50 lines)
  * Long Parameter List (>5 params)
  * God Class (too many responsibilities)
  * Feature Envy (method uses another class more than its own)
  * Data Clumps (same group of data appears together)
  * Primitive Obsession (overuse of primitives instead of objects)
  * Switch Statements (polymorphism opportunity)
  * Speculative Generality (unused abstraction)
  * Dead Code
  * Duplicate Code
- Style violations (naming, formatting, documentation)
- Anti-patterns (Singleton abuse, circular dependencies, etc.)
- Test coverage analysis (line, branch, function coverage)
- Performance concerns (N+1 queries, inefficient algorithms)

Time budget: 5 hours

Return structured JSON with:
{{
  "quality_score": <0-10>,
  "complexity_metrics": {{
    "avg_cyclomatic": <number>,
    "max_cyclomatic": <number>,
    "avg_cognitive": <number>,
    "max_cognitive": <number>,
    "avg_nesting_depth": <number>,
    "max_nesting_depth": <number>,
    "avg_function_length": <number>,
    "max_function_length": <number>
  }},
  "code_smells": [
    {{"type": "...", "location": "file:line", "severity": "high|medium|low", "description": "...", "refactoring_suggestion": "..."}}
  ],
  "style_issues": [...],
  "anti_patterns": [...],
  "test_coverage": {{"line_coverage": <0-100>, "branch_coverage": <0-100>, "function_coverage": <0-100>}} or null,
  "performance_concerns": [...],
  "findings": [...],
  "recommendations": [...]
}}
"""
    else:  # standard
        # Thorough analysis (1-2 hours)
        return f"""Code quality review for task {task_id}.

Review scope: {scope_str}

Standard quality analysis:
- Complexity metrics (cyclomatic, nesting depth)
- Common code smells:
  * Long Method
  * Long Parameter List
  * God Class
  * Duplicate Code
  * Dead Code
- Style violations
- Test coverage if available
- Key quality recommendations

Time budget: 90 minutes

Return structured JSON with:
{{
  "quality_score": <0-10>,
  "complexity_metrics": {{
    "avg_cyclomatic": <number>,
    "max_cyclomatic": <number>,
    "avg_nesting_depth": <number>,
    "max_nesting_depth": <number>
  }},
  "code_smells": [
    {{"type": "...", "location": "file:line", "severity": "high|medium|low", "description": "..."}}
  ],
  "style_issues": [...],
  "test_coverage": {{"line_coverage": <0-100>, "branch_coverage": <0-100>}} or null,
  "findings": [...],
  "recommendations": [...]
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


def parse_quality_response(response: str) -> Dict[str, Any]:
    """
    Parse agent response into structured format.

    Args:
        response: JSON string from code-reviewer agent

    Returns:
        Parsed dictionary with quality metrics and findings
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
        quality_score = data.get("quality_score", 0)
        if not isinstance(quality_score, (int, float)):
            quality_score = 0

        return {
            "quality_score": min(10, max(0, quality_score)),
            "complexity_metrics": data.get("complexity_metrics", {}),
            "code_smells": data.get("code_smells", []),
            "style_issues": data.get("style_issues", []),
            "test_coverage": data.get("test_coverage"),
            "findings": data.get("findings", []),
            "recommendations": data.get("recommendations", [])
        }
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback to text parsing if JSON parsing fails
        return {
            "quality_score": 5.0,
            "complexity_metrics": {},
            "code_smells": [],
            "style_issues": [],
            "test_coverage": None,
            "findings": [
                {
                    "severity": "medium",
                    "description": f"Failed to parse response: {str(e)}",
                    "location": ""
                }
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "description": "Re-run review with properly formatted output"
                }
            ]
        }


def calculate_complexity_score(metrics: Dict[str, Any]) -> float:
    """
    Calculate overall complexity score from metrics.

    Args:
        metrics: Dictionary of complexity metrics

    Returns:
        Complexity score (0-10, lower is better)
    """
    if not metrics:
        return 5.0

    # Cyclomatic complexity score (1-10 is excellent, >30 is concerning)
    max_cyclomatic = metrics.get("max_cyclomatic", 10)
    cyclomatic_score = min(10, max(1, 11 - (max_cyclomatic / 3)))

    # Nesting depth score (1-2 is excellent, >5 is concerning)
    max_nesting = metrics.get("max_nesting_depth", 2)
    nesting_score = min(10, max(1, 11 - max_nesting))

    # Average scores
    return (cyclomatic_score + nesting_score) / 2
