"""
Technical Debt Assessment mode for /task-review command.

Inventories and prioritizes technical debt using both code-reviewer and
architectural-reviewer agents.
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
            return '{"debt_items": [], "quick_wins": [], "total_debt_score": 50}'


DebtCategory = Literal["code", "design", "test", "documentation", "infrastructure"]
Priority = Literal["high", "medium", "low"]


def execute(task_context: Dict[str, Any], depth: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute technical debt assessment.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth (quick, standard, comprehensive)
        model: Optional Claude model ID to use

    Returns:
        Structured debt assessment with prioritized items
    """
    # Run both code review and architectural review
    code_debt = analyze_code_debt(task_context, depth, model)
    design_debt = analyze_design_debt(task_context, depth, model)

    # Merge and prioritize debt items
    all_debt = merge_debt_items(code_debt, design_debt)
    prioritized = prioritize_debt(all_debt)
    quick_wins = identify_quick_wins(prioritized)

    return {
        "mode": "technical-debt",
        "depth": depth,
        "total_debt_score": calculate_total_debt_score(all_debt),
        "debt_by_category": categorize_debt(all_debt),
        "debt_items": prioritized,
        "quick_wins": quick_wins,
        "paydown_estimate": estimate_paydown_effort(prioritized),
        "recommendations": generate_paydown_plan(prioritized, quick_wins)
    }


def analyze_code_debt(task_context: Dict[str, Any], depth: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze code-level technical debt using code-reviewer agent.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth
        model: Optional Claude model ID to use

    Returns:
        List of code debt items
    """
    scope = task_context.get("review_scope", [])
    task_id = task_context.get("task_id", "UNKNOWN")
    scope_str = ", ".join(scope) if scope else "entire codebase"

    prompt = f"""Code-level technical debt analysis for task {task_id}.

Review scope: {scope_str}

Identify code debt:
- Duplicate code that should be refactored
- Complex functions that need simplification
- Missing or inadequate tests
- Dead code that should be removed
- TODO/FIXME comments that need addressing
- Hard-coded values that should be configurable
- Poor naming that reduces clarity
- Missing error handling

For each debt item, provide:
- Category: "code"
- Description: What needs to be addressed
- Location: File and line number
- Impact: high/medium/low (effect on maintainability)
- Effort: low/medium/high (time to fix)
- Risk: high/medium/low (risk if not addressed)

Time budget: {"20 minutes" if depth == "quick" else "90 minutes" if depth == "standard" else "5 hours"}

Return structured JSON with:
{{
  "debt_items": [
    {{
      "category": "code",
      "description": "...",
      "location": "file.py:42",
      "impact": "high|medium|low",
      "effort": "low|medium|high",
      "risk": "high|medium|low",
      "details": "Additional context"
    }}
  ]
}}
"""

    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="code-reviewer",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "technical-debt", "depth": depth, "analysis": "code"},
        model=model
    )

    return parse_debt_response(response)


def analyze_design_debt(task_context: Dict[str, Any], depth: str, model: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze design-level technical debt using architectural-reviewer agent.

    Args:
        task_context: Task metadata including review_scope
        depth: Analysis depth
        model: Optional Claude model ID to use

    Returns:
        List of design debt items
    """
    scope = task_context.get("review_scope", [])
    task_id = task_context.get("task_id", "UNKNOWN")
    scope_str = ", ".join(scope) if scope else "entire codebase"

    prompt = f"""Design-level technical debt analysis for task {task_id}.

Review scope: {scope_str}

Identify design debt:
- SOLID violations that increase coupling
- Missing abstractions causing duplication
- Over-engineering (unnecessary complexity)
- Poor separation of concerns
- Tight coupling between modules
- Missing design patterns where beneficial
- Inconsistent architectural patterns
- Scalability bottlenecks

For each debt item, provide:
- Category: "design"
- Description: What needs to be addressed
- Location: Module/package name
- Impact: high/medium/low
- Effort: low/medium/high
- Risk: high/medium/low

Time budget: {"20 minutes" if depth == "quick" else "90 minutes" if depth == "standard" else "5 hours"}

Return structured JSON with:
{{
  "debt_items": [
    {{
      "category": "design",
      "description": "...",
      "location": "module/package",
      "impact": "high|medium|low",
      "effort": "low|medium|high",
      "risk": "high|medium|low",
      "details": "Additional context"
    }}
  ]
}}
"""

    bridge = AgentInvoker()
    response = bridge.invoke(
        agent_name="architectural-reviewer",
        prompt=prompt,
        timeout_seconds=get_timeout_for_depth(depth),
        context={"mode": "technical-debt", "depth": depth, "analysis": "design"},
        model=model
    )

    return parse_debt_response(response)


def parse_debt_response(response: str) -> List[Dict[str, Any]]:
    """
    Parse agent response into list of debt items.

    Args:
        response: JSON string from agent

    Returns:
        List of debt item dictionaries
    """
    try:
        if isinstance(response, str):
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)

            data = json.loads(response)
        else:
            data = response

        return data.get("debt_items", [])
    except (json.JSONDecodeError, ValueError):
        return []


def merge_debt_items(
    code_debt: List[Dict[str, Any]],
    design_debt: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge code and design debt items.

    Args:
        code_debt: Code-level debt items
        design_debt: Design-level debt items

    Returns:
        Combined list of all debt items
    """
    return code_debt + design_debt


def prioritize_debt(debt_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prioritize debt items using impact/effort/risk matrix.

    Args:
        debt_items: List of debt items

    Returns:
        Sorted list with priority scores
    """
    def calculate_priority_score(item: Dict[str, Any]) -> int:
        """Calculate priority score for a debt item."""
        impact_scores = {"high": 3, "medium": 2, "low": 1}
        effort_scores = {"high": 1, "medium": 2, "low": 3}  # Inverted: low effort = high priority
        risk_scores = {"high": 3, "medium": 2, "low": 1}

        impact = impact_scores.get(item.get("impact", "medium"), 2)
        effort = effort_scores.get(item.get("effort", "medium"), 2)
        risk = risk_scores.get(item.get("risk", "medium"), 2)

        # Priority = (Impact + Risk) * Effort weight
        # Higher score = higher priority
        return (impact + risk) * effort

    # Add priority score to each item
    for item in debt_items:
        item["priority_score"] = calculate_priority_score(item)

        # Determine priority label
        if item["priority_score"] >= 12:
            item["priority"] = "high"
        elif item["priority_score"] >= 8:
            item["priority"] = "medium"
        else:
            item["priority"] = "low"

    # Sort by priority score (descending)
    return sorted(debt_items, key=lambda x: x["priority_score"], reverse=True)


def identify_quick_wins(debt_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify quick win items (low effort, high impact).

    Args:
        debt_items: Prioritized list of debt items

    Returns:
        List of quick win items
    """
    quick_wins = []
    for item in debt_items:
        if item.get("effort") == "low" and item.get("impact") in ["high", "medium"]:
            quick_wins.append(item)

    return quick_wins


def categorize_debt(debt_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize debt items by type.

    Args:
        debt_items: List of debt items

    Returns:
        Dictionary mapping categories to debt items
    """
    categories: Dict[str, List[Dict[str, Any]]] = {
        "code": [],
        "design": [],
        "test": [],
        "documentation": [],
        "infrastructure": []
    }

    for item in debt_items:
        category = item.get("category", "code")
        if category in categories:
            categories[category].append(item)
        else:
            categories["code"].append(item)

    return categories


def calculate_total_debt_score(debt_items: List[Dict[str, Any]]) -> int:
    """
    Calculate total debt score (0-100, lower is better).

    Args:
        debt_items: List of debt items

    Returns:
        Total debt score
    """
    if not debt_items:
        return 0

    # Weight by impact and risk
    total_score = 0
    impact_weights = {"high": 10, "medium": 5, "low": 2}
    risk_weights = {"high": 10, "medium": 5, "low": 2}

    for item in debt_items:
        impact = impact_weights.get(item.get("impact", "medium"), 5)
        risk = risk_weights.get(item.get("risk", "medium"), 5)
        total_score += impact + risk

    # Normalize to 0-100 scale (cap at 100)
    return min(100, total_score)


def estimate_paydown_effort(debt_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate effort required to pay down technical debt.

    Args:
        debt_items: List of debt items

    Returns:
        Dictionary with effort estimates
    """
    effort_hours = {"low": 2, "medium": 8, "high": 24}

    total_hours = sum(effort_hours.get(item.get("effort", "medium"), 8) for item in debt_items)

    return {
        "total_hours": total_hours,
        "total_days": round(total_hours / 8, 1),
        "by_priority": {
            "high": sum(effort_hours.get(item.get("effort", "medium"), 8)
                       for item in debt_items if item.get("priority") == "high"),
            "medium": sum(effort_hours.get(item.get("effort", "medium"), 8)
                         for item in debt_items if item.get("priority") == "medium"),
            "low": sum(effort_hours.get(item.get("effort", "medium"), 8)
                      for item in debt_items if item.get("priority") == "low")
        }
    }


def generate_paydown_plan(
    debt_items: List[Dict[str, Any]],
    quick_wins: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate recommended paydown plan.

    Args:
        debt_items: Prioritized debt items
        quick_wins: Quick win items

    Returns:
        List of recommendations
    """
    recommendations = []

    # Phase 1: Quick wins
    if quick_wins:
        recommendations.append({
            "phase": 1,
            "name": "Quick Wins",
            "description": "Address low-effort, high-impact items first",
            "items": [item["description"] for item in quick_wins[:5]],
            "estimated_effort": estimate_paydown_effort(quick_wins[:5])
        })

    # Phase 2: High priority items
    high_priority = [item for item in debt_items if item.get("priority") == "high"]
    if high_priority:
        recommendations.append({
            "phase": 2,
            "name": "Critical Debt",
            "description": "Address high-priority technical debt",
            "items": [item["description"] for item in high_priority[:5]],
            "estimated_effort": estimate_paydown_effort(high_priority[:5])
        })

    # Phase 3: Medium priority items
    medium_priority = [item for item in debt_items if item.get("priority") == "medium"]
    if medium_priority:
        recommendations.append({
            "phase": 3,
            "name": "Moderate Debt",
            "description": "Address medium-priority items incrementally",
            "items": [item["description"] for item in medium_priority[:5]],
            "estimated_effort": estimate_paydown_effort(medium_priority[:5])
        })

    return recommendations


def get_timeout_for_depth(depth: str) -> int:
    """
    Get timeout in seconds based on depth.

    Args:
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Timeout in seconds
    """
    # Technical debt requires both agents, so double the timeout
    timeouts = {
        "quick": 3600,        # 1 hour (2x 30 min)
        "standard": 14400,    # 4 hours (2x 2 hours)
        "comprehensive": 43200  # 12 hours (2x 6 hours)
    }
    return timeouts.get(depth, 14400)
