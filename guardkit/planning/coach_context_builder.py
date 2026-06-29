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
from typing import Any, Dict, TYPE_CHECKING, Optional

from guardkit.planning.complexity_gating import get_arch_token_budget
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
)
from guardkit.knowledge.query_logger import log_query

if TYPE_CHECKING:
    from guardkit.knowledge.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)

# Minimum remaining budget to include impact analysis
MIN_IMPACT_BUDGET = 400


async def build_coach_context(
    task: Dict[str, Any],
    client: Optional["GraphitiClient"],
    project_id: str,
) -> str:
    """Build context string for AutoBuild coach prompt.

    Assembles architecture context based on task complexity. Higher complexity
    tasks get more context (overview + impact analysis), while simple tasks
    get none.

    Supports multiple backends:
        - graphiti: Traditional Graphiti backend (default)
        - fleet_memory: Fleet-memory backend via memory_search
        - dual: Dual-write mode (reads from Graphiti for now)

    Token budget allocation by complexity:
        - 1-3: 0 tokens (no context)
        - 4-6: 1000 tokens (overview only)
        - 7-8: 2000 tokens (overview + impact)
        - 9-10: 3000 tokens (overview + impact)

    Args:
        task: Task dict with 'complexity' key (default: 5 if missing)
        client: Memory client instance (GraphitiClient, FleetMemoryClient, or DualWriteClient)
        project_id: Project ID for namespace prefixing

    Returns:
        Formatted string with architecture context sections, or empty string if:
        - Complexity 1-3 (budget = 0)
        - Client unavailable
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
            logger.debug(f"No context for simple task (complexity {complexity})")
            return ""

        # Get the memory client (may be Graphiti, FleetMemory, or Dual)
        from guardkit.knowledge.fleet_memory_client import get_memory_client
        memory_client = get_memory_client() if client is None else client

        if memory_client is None:
            logger.info("Coach context skipped - memory client unavailable")
            return ""

        # Create SystemPlanGraphiti instance
        sp = SystemPlanGraphiti(client=memory_client, project_id=project_id)

        # Check if client is available
        if not sp._available:
            logger.info("Coach context skipped - memory client unavailable")
            return ""

        # Determine backend type for logging
        backend_type = _get_backend_type(memory_client)

        # Get system overview
        overview = await get_system_overview(sp, verbose=False)

        # Log query if using fleet-memory
        if backend_type in ["fleet_memory", "dual"]:
            _log_fleet_memory_query(
                query="system overview for coach context",
                result_count=1 if overview.get("status") == "ok" else 0,
                first_result=str(overview) if overview.get("status") == "ok" else None
            )

        # Check if we have architecture context
        if overview.get("status") != "ok":
            logger.info("Coach context skipped - no architecture context")
            return ""

        # Build result parts
        parts = []

        # Get condensed overview (uses priority ordering)
        overview_text = condense_for_injection(overview, max_tokens=budget)
        if not overview_text:
            logger.info("Coach context skipped - overview condensation empty")
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
                sp, task, remaining_budget, backend_type
            )
            if impact_text:
                parts.append("")
                parts.append("## Task Impact")
                parts.append("")
                parts.append(impact_text)

        result = "\n".join(parts)
        logger.info(
            f"Coach context built ({backend_type}): {_estimate_tokens(result)} tokens "
            f"(budget: {budget}, complexity: {complexity})"
        )
        return result

    except Exception as e:
        logger.warning(f"Failed to build coach context: {e}")
        return ""


async def _get_impact_section(
    sp: "SystemPlanGraphiti",
    task: Dict[str, Any],
    max_tokens: int,
    backend_type: str = "graphiti",
) -> str:
    """Get impact analysis section for high complexity tasks.

    Args:
        sp: SystemPlanGraphiti instance
        task: Task dict with title and description
        max_tokens: Maximum tokens for impact section
        backend_type: Backend type for logging

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

        impact_result = await run_impact_analysis(
            sp=sp,
            client=sp._client,
            task_or_topic=query,
            depth="quick",
        )

        # Log query if using fleet-memory
        if backend_type in ["fleet_memory", "dual"]:
            _log_fleet_memory_query(
                query=f"impact analysis: {query}",
                result_count=1 if impact_result and impact_result.get("status") == "ok" else 0,
                first_result=str(impact_result) if impact_result and impact_result.get("status") == "ok" else None
            )

        if not impact_result or impact_result.get("status") != "ok":
            logger.debug("Impact analysis returned no data")
            return ""

        # Condense impact for injection
        impact_text = condense_impact_for_injection(impact_result, max_tokens=max_tokens)
        return impact_text

    except ImportError:
        # Impact analysis module not available - graceful degradation
        logger.debug("Impact analysis module not available")
        return ""
    except Exception as e:
        logger.warning(f"Failed to get impact analysis: {e}")
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


def _get_backend_type(client: Any) -> str:
    """Determine backend type from client class name.

    Args:
        client: Memory client instance

    Returns:
        Backend type string: "graphiti", "fleet_memory", or "dual"
    """
    class_name = client.__class__.__name__
    if "Fleet" in class_name:
        return "fleet_memory"
    elif "Dual" in class_name:
        return "dual"
    else:
        return "graphiti"


def _log_fleet_memory_query(
    query: str,
    result_count: int,
    first_result: Optional[str] = None
) -> None:
    """Log a fleet-memory query for evidence tracking.

    Args:
        query: Query text
        result_count: Number of results returned
        first_result: Preview of first result (optional)
    """
    try:
        log_query(
            operation="search",
            query=query,
            group_ids=["coach_context"],
            result_count=result_count,
            first_result_preview=first_result,
            source="fleet_memory_client"
        )
    except Exception as e:
        logger.debug(f"Failed to log fleet-memory query: {e}")
