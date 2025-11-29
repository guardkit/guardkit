"""
Architectural Review mode for /task-review command.

Evaluates code against SOLID, DRY, and YAGNI principles using the
architectural-reviewer agent.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import sys
    from pathlib import Path
    # Add parent lib directory to path to import agent_bridge
    lib_path = Path(__file__).parent.parent.parent / "lib"
    if str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
    from agent_bridge.invoker import AgentBridgeInvoker as AgentInvoker
except (ImportError, ModuleNotFoundError):
    # Fallback for testing
    class AgentInvoker:
        def invoke(self, agent_name: str, prompt: str, timeout_seconds: int, context: Dict[str, Any]) -> str:
            return '{"overall_score": 75, "solid_score": 80, "dry_score": 70, "yagni_score": 75, "findings": [], "recommendations": []}'


def execute(task_context: Dict[str, Any], depth: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute architectural review.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)
        model: Optional Claude model ID to use

    Returns:
        Structured review results with architecture scores
    """
    # Build prompt based on depth
    prompt = build_architectural_prompt(task_context, depth)

    # Invoke architectural-reviewer agent
    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="architectural-reviewer",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "architectural", "depth": depth},
        model=model
    )

    # Parse response into structured format
    results = parse_architectural_response(response)

    return {
        "mode": "architectural",
        "depth": depth,
        "overall_score": results["overall_score"],  # 0-100
        "principles": {
            "solid": results["solid_score"],  # 0-100
            "dry": results["dry_score"],      # 0-100
            "yagni": results["yagni_score"]   # 0-100
        },
        "findings": results["findings"],
        "recommendations": results["recommendations"],
        "evidence_files": results.get("evidence_files", [])
    }


def build_architectural_prompt(task_context: Dict[str, Any], depth: str) -> str:
    """
    Build prompt for architectural review based on depth.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Formatted prompt string for the agent
    """
    scope = task_context.get("review_scope", [])
    task_id = task_context.get("task_id", "UNKNOWN")

    # Convert scope to file paths if needed
    scope_str = ", ".join(scope) if scope else "entire codebase"

    if depth == "quick":
        # Surface-level analysis (15-30 min)
        return f"""Quick architectural review for task {task_id}.

Review scope: {scope_str}

Focus on high-level architecture only:
- Identify major SOLID violations (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
- Check for obvious DRY (Don't Repeat Yourself) issues
- Flag over-engineering (YAGNI - You Aren't Gonna Need It)

Time budget: 20 minutes

Return structured JSON with:
{{
  "overall_score": <0-100>,
  "solid_score": <0-100>,
  "dry_score": <0-100>,
  "yagni_score": <0-100>,
  "findings": [
    {{"severity": "high|medium|low", "principle": "SOLID|DRY|YAGNI", "description": "...", "file": "path/to/file.py", "line": 42}}
  ],
  "recommendations": [
    {{"priority": "high|medium|low", "description": "...", "effort": "low|medium|high"}}
  ],
  "evidence_files": ["file1.py", "file2.py"]
}}
"""
    elif depth == "comprehensive":
        # Exhaustive analysis (4-6 hours)
        return f"""Comprehensive architectural review for task {task_id}.

Review scope: {scope_str}

Thorough analysis required:
- Detailed SOLID evaluation with specific examples:
  * Single Responsibility Principle: Each class/function has one reason to change
  * Open/Closed Principle: Open for extension, closed for modification
  * Liskov Substitution: Subtypes must be substitutable for base types
  * Interface Segregation: Clients shouldn't depend on unused interfaces
  * Dependency Inversion: Depend on abstractions, not concretions
- DRY analysis: Identify ALL code duplication and repetition
- YAGNI assessment: Find unnecessary abstractions and over-engineering
- Design pattern analysis: Identify patterns used and misused
- Scalability concerns: Bottlenecks, coupling issues
- Maintainability assessment: Code organization, modularity

Time budget: 5 hours

Return structured JSON with:
{{
  "overall_score": <0-100>,
  "solid_score": <0-100>,
  "dry_score": <0-100>,
  "yagni_score": <0-100>,
  "findings": [
    {{"severity": "high|medium|low", "principle": "SOLID|DRY|YAGNI", "description": "...", "file": "path/to/file.py", "line": 42, "code_snippet": "..."}}
  ],
  "recommendations": [
    {{"priority": "high|medium|low", "description": "...", "effort": "low|medium|high", "impact": "high|medium|low"}}
  ],
  "evidence_files": ["file1.py", "file2.py"],
  "design_patterns": [{{"pattern": "...", "usage": "correct|misused", "location": "..."}}],
  "scalability_concerns": [...],
  "maintainability_score": <0-100>
}}
"""
    else:  # standard
        # Thorough analysis (1-2 hours)
        return f"""Architectural review for task {task_id}.

Review scope: {scope_str}

Standard depth analysis:
- SOLID principle evaluation:
  * Single Responsibility: Classes/functions with single purpose
  * Open/Closed: Extension without modification
  * Liskov Substitution: Proper inheritance usage
  * Interface Segregation: Minimal interfaces
  * Dependency Inversion: Abstractions over concretions
- DRY principle check: Identify code duplication
- YAGNI assessment: Flag unnecessary complexity
- Key architectural recommendations

Time budget: 90 minutes

Return structured JSON with:
{{
  "overall_score": <0-100>,
  "solid_score": <0-100>,
  "dry_score": <0-100>,
  "yagni_score": <0-100>,
  "findings": [
    {{"severity": "high|medium|low", "principle": "SOLID|DRY|YAGNI", "description": "...", "file": "path/to/file.py", "line": 42}}
  ],
  "recommendations": [
    {{"priority": "high|medium|low", "description": "...", "effort": "low|medium|high"}}
  ],
  "evidence_files": ["file1.py", "file2.py"]
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


def parse_architectural_response(response: str) -> Dict[str, Any]:
    """
    Parse agent response into structured format.

    Args:
        response: JSON string from architectural-reviewer agent

    Returns:
        Parsed dictionary with scores, findings, and recommendations
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
        return {
            "overall_score": min(100, max(0, data.get("overall_score", 0))),
            "solid_score": min(100, max(0, data.get("solid_score", 0))),
            "dry_score": min(100, max(0, data.get("dry_score", 0))),
            "yagni_score": min(100, max(0, data.get("yagni_score", 0))),
            "findings": data.get("findings", []),
            "recommendations": data.get("recommendations", []),
            "evidence_files": data.get("evidence_files", [])
        }
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback to text parsing if JSON parsing fails
        return {
            "overall_score": 50,
            "solid_score": 50,
            "dry_score": 50,
            "yagni_score": 50,
            "findings": [
                {
                    "severity": "medium",
                    "principle": "UNKNOWN",
                    "description": f"Failed to parse response: {str(e)}",
                    "file": "",
                    "line": 0
                }
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "description": "Re-run review with properly formatted output",
                    "effort": "low"
                }
            ],
            "evidence_files": []
        }


def validate_review_scope(scope: List[str]) -> List[str]:
    """
    Validate and normalize review scope paths.

    Args:
        scope: List of file/directory paths to review

    Returns:
        Validated list of existing paths
    """
    validated = []
    for path_str in scope:
        path = Path(path_str)
        if path.exists():
            validated.append(str(path))

    return validated
