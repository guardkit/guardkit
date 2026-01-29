"""
Task outcome query functions.

This module provides functionality for querying task outcomes
from Graphiti. All operations are designed for graceful degradation -
they will return empty results when Graphiti is unavailable.

Public API:
    find_similar_task_outcomes: Search for similar task outcomes
    OutcomeQueries: Class-based interface for outcome queries

Example:
    from guardkit.knowledge.outcome_queries import find_similar_task_outcomes

    similar_outcomes = await find_similar_task_outcomes(
        task_requirements="Implement OAuth2 authentication",
        limit=5
    )
"""

import logging
from typing import List, Dict, Any

from guardkit.knowledge.graphiti_client import get_graphiti

logger = logging.getLogger(__name__)

# Group ID for task outcomes in Graphiti
TASK_OUTCOMES_GROUP_ID = "task_outcomes"


async def find_similar_task_outcomes(
    task_requirements: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Search for similar task outcomes in Graphiti.

    Performs semantic search to find outcomes from similar tasks.
    Returns empty list if Graphiti is unavailable or search fails.

    Args:
        task_requirements: Task requirements to search for
        limit: Maximum number of results to return (default: 5)

    Returns:
        List of similar outcomes as dictionaries.
        Empty list if:
        - Client not initialized
        - Client disabled
        - Search fails
        - Limit is 0 or negative

    Example:
        outcomes = await find_similar_task_outcomes(
            task_requirements="Implement OAuth2 authentication",
            limit=5
        )
    """
    # Handle zero or negative limit
    if limit <= 0:
        return []

    # Get client (graceful degradation)
    client = get_graphiti()

    if client is None:
        logger.debug("Graphiti client not initialized, returning empty results")
        return []

    if not client.enabled:
        logger.debug("Graphiti client disabled, returning empty results")
        return []

    try:
        results = await client.search(
            query=task_requirements,
            group_ids=[TASK_OUTCOMES_GROUP_ID],
            num_results=limit,
        )

        # Apply limit to results (in case search returns more)
        return results[:limit] if results else []

    except Exception as e:
        logger.warning(f"Failed to search outcomes in Graphiti: {e}")
        return []


class OutcomeQueries:
    """Class-based interface for outcome queries.

    Provides a stateful interface for querying task outcomes.
    This class wraps the module-level functions for convenience.

    Example:
        queries = OutcomeQueries()
        similar = await queries.find_similar(
            task_requirements="Implement OAuth2",
            limit=5
        )
    """

    async def find_similar(
        self,
        task_requirements: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar task outcomes.

        Delegates to find_similar_task_outcomes function.

        Args:
            task_requirements: Task requirements to search for
            limit: Maximum number of results to return

        Returns:
            List of similar outcomes as dictionaries
        """
        return await find_similar_task_outcomes(
            task_requirements=task_requirements,
            limit=limit,
        )
