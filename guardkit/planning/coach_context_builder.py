"""Coach Context Builder: Budget-gated context assembly for AutoBuild coach.

This module bridges system overview and impact analysis into a single context
string for the AutoBuild coach prompt. It uses complexity-based token budgets
to control how much architecture context is included.

The build_coach_context() function is the main entry point. It:
1. Gets the complexity from the task (default: 5)
2. Calls get_arch_token_budget(complexity) for the token budget
3. If budget == 0, returns "" (simple tasks get no architecture context)
4. Gets condensed overview via condense_for_injection()
5. If remaining budget > 400, gets quick impact analysis
6. Returns formatted string with sections

All operations have graceful degradation - exceptions are caught and logged,
never raised to the caller. All log messages use [Graphiti] prefix.

Public API:
    build_coach_context: Main entry point for coach context assembly

Example:
    from guardkit.planning.coach_context_builder import build_coach_context
    from guardkit.knowledge.graphiti_client import get_graphiti

    client = get_graphiti()
    task = {"complexity": 7, "title": "Major refactoring"}

    context = await build_coach_context(task, client, "my-project")
    # Returns formatted string with architecture and impact sections
"""

import logging
from typing import Any, Dict, TYPE_CHECKING

from guardkit.planning.complexity_gating import get_arch_token_budget
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
)

if TYPE_CHECKING:
    from guardkit.knowledge.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)

# Minimum remaining budget to include impact analysis
MIN_IMPACT_BUDGET = 400


async def build_coach_context(
    task: Dict[str, Any],
    client: "GraphitiClient",
    project_id: str,
) -> str:
    """Build context string for AutoBuild coach prompt.

    Assembles architecture context based on task complexity. Higher complexity
    tasks get more context (overview + impact analysis), while simple tasks
    get none.

    Token budget allocation by complexity:
        - 1-3: 0 tokens (no context)
        - 4-6: 1000 tokens (overview only)
        - 7-8: 2000 tokens (overview + impact)
        - 9-10: 3000 tokens (overview + impact)

    Args:
        task: Task dict with 'complexity' key (default: 5 if missing)
        client: GraphitiClient instance for Graphiti operations
        project_id: Project ID for namespace prefixing

    Returns:
        Formatted string with architecture context sections, or empty string if:
        - Complexity 1-3 (budget = 0)
        - Graphiti unavailable
        - No architecture context found
        - Exception occurs

    Note:
        This function never raises exceptions. All errors are logged and
        result in an empty string return for graceful degradation.
    """
    try:
        # Get complexity from task (default to 5 if missing)
        complexity = task.get("complexity", 5)

        # Get token budget based on complexity
        budget = get_arch_token_budget(complexity)

        # Simple tasks (complexity 1-3) get no architecture context
        if budget == 0:
            logger.debug(f"[Graphiti] No context for simple task (complexity {complexity})")
            return ""

        # Create SystemPlanGraphiti instance
        sp = SystemPlanGraphiti(client=client, project_id=project_id)

        # Check if Graphiti is available
        if not sp._available:
            logger.info("[Graphiti] Coach context skipped - Graphiti unavailable")
            return ""

        # Get system overview
        overview = await get_system_overview(sp, verbose=False)

        # Check if we have architecture context
        if overview.get("status") != "ok":
            logger.info("[Graphiti] Coach context skipped - no architecture context")
            return ""

        # Build result parts
        parts = []

        # Get condensed overview (uses priority ordering)
        overview_text = condense_for_injection(overview, max_tokens=budget)
        if not overview_text:
            logger.info("[Graphiti] Coach context skipped - overview condensation empty")
            return ""

        overview_tokens = _estimate_tokens(overview_text)
        remaining_budget = budget - overview_tokens

        # Add architecture context section
        parts.append("## Architecture Context")
        parts.append("")
        parts.append(overview_text)

        # For high complexity (7+), try to add impact analysis if budget allows
        if complexity >= 7 and remaining_budget > MIN_IMPACT_BUDGET:
            impact_text = await _get_impact_section(
                sp, task, remaining_budget
            )
            if impact_text:
                parts.append("")
                parts.append("## Task Impact")
                parts.append("")
                parts.append(impact_text)

        result = "\n".join(parts)
        logger.info(
            f"[Graphiti] Coach context built: {_estimate_tokens(result)} tokens "
            f"(budget: {budget}, complexity: {complexity})"
        )
        return result

    except Exception as e:
        logger.warning(f"[Graphiti] Failed to build coach context: {e}")
        return ""


async def _get_impact_section(
    sp: "SystemPlanGraphiti",
    task: Dict[str, Any],
    max_tokens: int,
) -> str:
    """Get impact analysis section for high complexity tasks.

    Args:
        sp: SystemPlanGraphiti instance
        task: Task dict with title and description
        max_tokens: Maximum tokens for impact section

    Returns:
        Condensed impact text, or empty string on failure
    """
    try:
        # Import here to avoid circular imports and handle missing module
        from guardkit.planning.impact_analysis import (
            run_impact_analysis,
            condense_impact_for_injection,
        )

        # Run impact analysis
        task_title = task.get("title", "")
        task_description = task.get("description", "")
        query = f"{task_title} {task_description}".strip()

        impact_result = await run_impact_analysis(sp, query)

        if not impact_result or impact_result.get("status") != "ok":
            logger.debug("[Graphiti] Impact analysis returned no data")
            return ""

        # Condense impact for injection
        impact_text = condense_impact_for_injection(impact_result, max_tokens=max_tokens)
        return impact_text

    except ImportError:
        # Impact analysis module not available - graceful degradation
        logger.debug("[Graphiti] Impact analysis module not available")
        return ""
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to get impact analysis: {e}")
        return ""


def _estimate_tokens(text: str) -> int:
    """Estimate token count using simple heuristic.

    Uses word count * 1.3 as approximation (common for English text).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count (0 for empty string)
    """
    if not text:
        return 0

    words = len(text.split())
    return int(words * 1.3)
