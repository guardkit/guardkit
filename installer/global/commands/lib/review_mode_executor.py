"""
Task Review Orchestrator for /task-review command.

Coordinates the execution of different review modes and manages the overall
review workflow.
"""

from typing import Dict, Any, Optional

try:
    from review_modes import (
        architectural_review,
        code_quality_review,
        decision_analysis,
        technical_debt_assessment,
        security_audit
    )
except ImportError:
    # Absolute import fallback
    import sys
    from pathlib import Path
    review_modes_path = Path(__file__).parent / "review_modes"
    if str(review_modes_path) not in sys.path:
        sys.path.insert(0, str(review_modes_path))
    import architectural_review
    import code_quality_review
    import decision_analysis
    import technical_debt_assessment
    import security_audit


def execute_review_analysis(
    task_context: Dict[str, Any],
    mode: str,
    depth: str
) -> Dict[str, Any]:
    """
    Execute review analysis based on mode and depth.

    This function serves as the main entry point for all review modes,
    routing requests to the appropriate specialized review module.

    Args:
        task_context: Task metadata including:
            - task_id: Task identifier
            - review_scope: List of files/directories to review
            - options: (decision mode only) List of options to evaluate
            - criteria: (decision mode only) Evaluation criteria
            - decision_context: (decision mode only) Decision context
        mode: Review mode (architectural, code-quality, decision, technical-debt, security)
        depth: Analysis depth (quick, standard, comprehensive)

    Returns:
        Structured review results with mode-specific findings

    Raises:
        ValueError: If mode is not recognized
        RuntimeError: If review execution fails

    Examples:
        >>> # Architectural review
        >>> context = {
        ...     "task_id": "TASK-001",
        ...     "review_scope": ["src/auth/"]
        ... }
        >>> results = execute_review_analysis(context, "architectural", "standard")
        >>> print(results["overall_score"])  # 0-100

        >>> # Decision analysis
        >>> context = {
        ...     "task_id": "TASK-002",
        ...     "options": ["Option A", "Option B"],
        ...     "criteria": ["Maintainability", "Performance"]
        ... }
        >>> results = execute_review_analysis(context, "decision", "standard")
        >>> print(results["recommendation"])  # "Option A" or "Option B"
    """
    # Validate inputs
    if not task_context:
        raise ValueError("task_context is required")

    if not mode:
        raise ValueError("mode is required")

    if depth not in ["quick", "standard", "comprehensive"]:
        raise ValueError(f"Invalid depth: {depth}. Must be quick, standard, or comprehensive")

    # Map mode to module
    mode_map = {
        "architectural": architectural_review,
        "code-quality": code_quality_review,
        "decision": decision_analysis,
        "technical-debt": technical_debt_assessment,
        "security": security_audit
    }

    # Validate mode
    if mode not in mode_map:
        valid_modes = ", ".join(mode_map.keys())
        raise ValueError(f"Invalid mode: {mode}. Valid modes: {valid_modes}")

    # Execute mode
    review_module = mode_map[mode]

    try:
        results = review_module.execute(task_context, depth)
    except Exception as e:
        raise RuntimeError(f"Review execution failed for mode '{mode}': {str(e)}") from e

    # Validate results structure
    if not isinstance(results, dict):
        raise RuntimeError(f"Review mode '{mode}' returned invalid results (expected dict)")

    if "mode" not in results:
        results["mode"] = mode

    if "depth" not in results:
        results["depth"] = depth

    return results


def validate_task_context(task_context: Dict[str, Any], mode: str) -> None:
    """
    Validate task context has required fields for the given mode.

    Args:
        task_context: Task metadata dictionary
        mode: Review mode

    Raises:
        ValueError: If required fields are missing
    """
    # Common required fields
    if "task_id" not in task_context:
        raise ValueError("task_context must include 'task_id'")

    # Mode-specific validation
    if mode == "decision":
        if "options" not in task_context:
            raise ValueError("decision mode requires 'options' in task_context")
    else:
        # Most modes need review_scope
        if "review_scope" not in task_context:
            # Provide default empty scope
            task_context["review_scope"] = []


def get_supported_modes() -> list[str]:
    """
    Get list of supported review modes.

    Returns:
        List of mode names
    """
    return [
        "architectural",
        "code-quality",
        "decision",
        "technical-debt",
        "security"
    ]


def get_mode_description(mode: str) -> str:
    """
    Get description for a review mode.

    Args:
        mode: Review mode name

    Returns:
        Human-readable description

    Raises:
        ValueError: If mode is not recognized
    """
    descriptions = {
        "architectural": "Evaluates SOLID, DRY, and YAGNI principles (score: 0-100)",
        "code-quality": "Analyzes complexity, coverage, and code smells (score: 0-10)",
        "decision": "Compares multiple options against criteria with recommendation",
        "technical-debt": "Inventories and prioritizes technical debt items",
        "security": "Audits for OWASP Top 10, CVEs, and auth/authz issues"
    }

    if mode not in descriptions:
        raise ValueError(f"Unknown mode: {mode}")

    return descriptions[mode]


def get_mode_agents(mode: str) -> list[str]:
    """
    Get list of agents used by a review mode.

    Args:
        mode: Review mode name

    Returns:
        List of agent names

    Raises:
        ValueError: If mode is not recognized
    """
    agents = {
        "architectural": ["architectural-reviewer"],
        "code-quality": ["code-reviewer"],
        "decision": ["software-architect"],
        "technical-debt": ["code-reviewer", "architectural-reviewer"],
        "security": ["security-specialist"]
    }

    if mode not in agents:
        raise ValueError(f"Unknown mode: {mode}")

    return agents[mode]


def estimate_analysis_time(mode: str, depth: str) -> Dict[str, int]:
    """
    Estimate analysis time for a mode and depth.

    Args:
        mode: Review mode
        depth: Analysis depth

    Returns:
        Dictionary with min and max time in minutes

    Examples:
        >>> estimate_analysis_time("architectural", "quick")
        {'min_minutes': 15, 'max_minutes': 30}
    """
    # Base times by depth
    depth_times = {
        "quick": (15, 30),
        "standard": (60, 120),
        "comprehensive": (240, 360)
    }

    min_time, max_time = depth_times.get(depth, (60, 120))

    # Technical debt uses 2 agents, so double the time
    if mode == "technical-debt":
        min_time *= 2
        max_time *= 2

    return {
        "min_minutes": min_time,
        "max_minutes": max_time
    }
